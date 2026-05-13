from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from django.core import signing

from apps.assessments import selectors as assessment_selectors
from apps.assessments.serializers import AssessmentSerializer
from apps.advisor import selectors as advisor_selectors
from apps.advisor.serializers import IDPSerializer
from apps.courses import selectors as course_selectors
from apps.users.models import Customer
from apps.users.selectors import get_professional_profile
from apps.users.serializers import CustomerSerializer, ProfessionalProfileSerializer
from integrations.email_client import send_invitation_email, send_existing_user_invitation_email, send_weekly_report_email
from integrations.sitecore_client import fetch_sitecore_courses

from . import selectors
from .models import Company, CompanyMember

logger = logging.getLogger(__name__)

INVITE_SALT = "company-invite"
INVITE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

# ---------------------------------------------------------------------------
# Ordinal scale: qualitative levels ↔ numeric for aggregation
# ---------------------------------------------------------------------------
LEVEL_TO_NUM: dict[str, int] = {
    "Beginner": 1,
    "Intermediate": 2,
    "Advanced": 3,
    "Expert": 4,
}

DEFAULT_REQUIRED_LEVEL = "Advanced"


# ---------------------------------------------------------------------------
# Skill name normalization — map verbose AI-generated categories to broad
# skill domains so they can be aggregated across different employees.
# ---------------------------------------------------------------------------
_SKILL_DOMAIN_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Leadership", ["leadership", "team lead", "team building", "talent", "mentoring", "coaching"]),
    ("Communication", ["communication", "presentation", "executive presence", "storytelling", "writing"]),
    ("Strategic Thinking", ["strategic", "strategy", "decision making", "critical thinking", "problem solving"]),
    ("Stakeholder Management", ["stakeholder", "negotiation", "client", "customer relationship"]),
    ("Cross-Functional Collaboration", ["cross-functional", "collaboration", "teamwork", "interpersonal"]),
    ("Data Analytics", ["data analy", "data science", "evidence-based", "decision support", "business intelligence"]),
    ("Database & Data Modeling", ["database", "data model", "sql", "data design"]),
    ("AI & Digital Transformation", ["artificial intelligence", " ai ", "machine learning", "digital transformation", "automation", "ai solution"]),
    ("Frontend Development", ["frontend", "front-end", "front end", "ui ", "user interface", "react", "angular", "css", "html"]),
    ("Backend Development", ["backend", "back-end", "back end", "api design", "api development", "server-side"]),
    ("System Design & Architecture", ["system design", "architecture", "scalab", "microservice", "engineering architecture"]),
    ("Testing & QA", ["test", "qa ", "quality assurance", "selenium", "automation proficiency"]),
    ("Security", ["security", "access control", "cybersec", "encryption"]),
    ("Product Management", ["product strategy", "product management", "roadmap", "user-centered"]),
    ("Project Management", ["project manage", "agile", "scrum", "delivery", "execution"]),
    ("Risk Management", ["risk", "root cause", "defect management", "incident"]),
    ("Cloud & DevOps", ["cloud", "devops", "ci/cd", "deployment", "infrastructure"]),
    ("Professional Development", ["professional discipline", "work-life", "continuous learning", "ownership", "accountability"]),
]


def _normalize_skill(category: str) -> str:
    """Map a verbose AI-generated category to a standard skill domain."""
    cat_lower = category.lower()
    for domain, keywords in _SKILL_DOMAIN_KEYWORDS:
        for kw in keywords:
            if kw in cat_lower:
                return domain
    # Fallback: return the original (capped at a reasonable length)
    return category[:60]


def _avg_to_level(avg: float) -> str:
    if avg < 1.5:
        return "Beginner"
    if avg < 2.5:
        return "Intermediate"
    if avg < 3.5:
        return "Advanced"
    return "Expert"


def _gap_severity(current_num: float, required_num: int) -> str:
    diff = required_num - current_num
    if diff <= 0:
        return "none"
    if diff < 1.5:
        return "moderate"
    return "critical"


# ---------------------------------------------------------------------------
# Employee data builder
# ---------------------------------------------------------------------------
def join_company(*, customer: Customer, code: str) -> CompanyMember:
    if not code:
        raise ValueError("Company code is required.")

    company = selectors.get_company_by_code(code)
    if not company:
        raise ValueError("Invalid company code.")

    if selectors.is_member(company, customer):
        raise ValueError("Already a member of this company.")

    return CompanyMember.objects.create(Company=company, Customer=customer)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------
def create_invite_token(email: str, company_code: str) -> str:
    """Create a signed token containing the email and company code."""
    return signing.dumps(
        {"email": email, "company_code": company_code},
        salt=INVITE_SALT,
    )


def verify_invite_token(token: str) -> dict:
    """Verify and decode an invite token. Returns {"email": ..., "company_code": ...}."""
    return signing.loads(token, salt=INVITE_SALT, max_age=INVITE_MAX_AGE)


def send_invitations(*, company: Company, emails: list[str]) -> dict:
    """Send invitation emails for a company.

    For each email:
    - Already registered **and** already a member → skip.
    - Already registered but **not** a member → send a code-only email
      directing them to Settings to join with the company code.
    - Not registered → send a full signup invitation email.

    Returns counts of sent / failed / already_members / notified_existing.
    """
    from apps.users.selectors import get_customer_by_email

    sent = 0
    failed = []
    already_members = []
    notified_existing = []

    for email in emails:
        email = email.strip().lower()
        if not email:
            continue

        existing_customer = get_customer_by_email(email)

        if existing_customer:
            # Already a member → skip entirely
            if selectors.is_member(company, existing_customer):
                already_members.append(email)
                continue

            # Registered but not a member → send lighter "use your code" email
            ok = send_existing_user_invitation_email(
                to_email=email,
                company_name=company.Name,
                company_code=company.Code,
            )
            if ok:
                notified_existing.append(email)
            else:
                failed.append(email)
            continue

        # Not registered → full signup invitation email
        token = create_invite_token(email, company.Code)
        ok = send_invitation_email(
            to_email=email,
            company_name=company.Name,
            company_code=company.Code,
            invite_token=token,
        )
        if ok:
            sent += 1
        else:
            failed.append(email)

    return {
        "sent": sent,
        "failed": failed,
        "already_members": already_members,
        "notified_existing": notified_existing,
    }


def build_employee_data(customer: Customer) -> dict:
    profile = get_professional_profile(customer)
    assessments = assessment_selectors.list_assessments_for_customer(customer)
    idps = advisor_selectors.list_idps_for_customer(customer)

    return {
        "customer": CustomerSerializer(customer).data,
        "professional_profile": ProfessionalProfileSerializer(profile).data if profile else None,
        "assessments": AssessmentSerializer(assessments, many=True).data,
        "idps": IDPSerializer(idps, many=True).data,
    }


# ---------------------------------------------------------------------------
# Qualitative skill aggregation
# ---------------------------------------------------------------------------
def _percentage_to_level(pct: float) -> str:
    """Map a legacy 0-100 percentage to a qualitative level."""
    if pct < 30:
        return "Beginner"
    if pct < 60:
        return "Intermediate"
    if pct < 80:
        return "Advanced"
    return "Expert"


def _aggregate_skills(employees: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Build skill_overview and skill_gaps from category_results
    across all employees' completed assessments.

    Handles both data formats:
    - New: Skills is a dict with category_results[{category, response}]
    - Legacy: Skills is a list of [{name, percentage}]
    """
    category_values: dict[str, list[int]] = defaultdict(list)

    for emp in employees:
        for assessment in emp["assessments"]:
            if assessment.get("Status") != "completed":
                continue
            skills = assessment.get("Skills")

            # New format: dict with category_results
            if isinstance(skills, dict):
                for cr in skills.get("category_results", []):
                    category = cr.get("category", "")
                    response = cr.get("response", "")
                    if category and response in LEVEL_TO_NUM:
                        domain = _normalize_skill(category)
                        category_values[domain].append(LEVEL_TO_NUM[response])

            # Legacy format: list of {name, percentage}
            elif isinstance(skills, list):
                for item in skills:
                    if isinstance(item, dict) and "name" in item and "percentage" in item:
                        name = item["name"]
                        level = _percentage_to_level(item["percentage"])
                        domain = _normalize_skill(name)
                        category_values[domain].append(LEVEL_TO_NUM[level])

    # Build overview
    skill_overview: list[dict[str, Any]] = []
    for category, values in sorted(category_values.items()):
        avg_value = sum(values) / len(values)
        skill_overview.append({
            "category": category,
            "avg_level": _avg_to_level(avg_value),
            "avg_value": round(avg_value, 1),
            "employee_count": len(values),
        })

    # Build gaps (only where current < required)
    required_num = LEVEL_TO_NUM[DEFAULT_REQUIRED_LEVEL]
    skill_gaps: list[dict[str, Any]] = []
    for item in skill_overview:
        severity = _gap_severity(item["avg_value"], required_num)
        if severity != "none":
            skill_gaps.append({
                "category": item["category"],
                "current_level": item["avg_level"],
                "required_level": DEFAULT_REQUIRED_LEVEL,
                "gap_severity": severity,
                "employees_affected": item["employee_count"],
            })

    skill_gaps.sort(key=lambda g: (0 if g["gap_severity"] == "critical" else 1))
    return skill_overview, skill_gaps


# ---------------------------------------------------------------------------
# Course catalog helper — match gap categories to KGC courses by title keyword
# ---------------------------------------------------------------------------
def _build_course_lookup() -> list[dict]:
    """Return a unified list of {name, link} from DB + Sitecore."""
    db_courses = course_selectors.get_active_courses_as_dicts()
    sitecore_courses = fetch_sitecore_courses()

    catalog: list[dict] = []
    seen: set[str] = set()

    for c in db_courses:
        name = c.get("Name", "")
        catalog.append({"name": name, "link": c.get("Link", ""), "category": c.get("Category", "")})
        seen.add(name.lower().strip())

    for sc in sitecore_courses:
        title = sc.get("title", "")
        if title.lower().strip() not in seen:
            catalog.append({"name": title, "link": sc.get("link", ""), "category": ""})

    return catalog


def _match_courses_for_gap(gap_category: str, catalog: list[dict], limit: int = 3) -> list[dict]:
    """Find courses whose title contains keywords from the gap category."""
    # Expand the gap domain with synonyms for broader matching
    _DOMAIN_EXTRA_KEYWORDS: dict[str, list[str]] = {
        "leadership": ["leadership", "lead", "management", "executive", "managing"],
        "communication": ["communication", "presenting", "presentation", "writing", "storytelling", "public speaking"],
        "strategic thinking": ["strategy", "strategic", "decision", "critical thinking", "problem solving"],
        "stakeholder management": ["stakeholder", "negotiation", "client", "relationship", "influence"],
        "cross-functional collaboration": ["collaboration", "teamwork", "interpersonal", "cross-functional"],
        "data analytics": ["data", "analytics", "analysis", "business intelligence", "dashboard", "visualization"],
        "database & data modeling": ["database", "sql", "data model", "data design"],
        "ai & digital transformation": ["artificial intelligence", "machine learning", "ai", "digital", "automation"],
        "frontend development": ["frontend", "front-end", "react", "angular", "vue", "css", "javascript", "typescript", "ui"],
        "backend development": ["backend", "back-end", "api", "server", "node", "python", "java", "django", ".net"],
        "system design & architecture": ["system design", "architecture", "scalab", "microservice", "distributed"],
        "testing & qa": ["testing", "test", "qa", "quality", "selenium", "automation"],
        "security": ["security", "cyber", "encryption", "access control", "authentication"],
        "product management": ["product", "roadmap", "user-centered", "product strategy"],
        "project management": ["project", "agile", "scrum", "delivery", "pmp", "kanban"],
        "risk management": ["risk", "compliance", "governance", "incident"],
        "cloud & devops": ["cloud", "devops", "aws", "azure", "docker", "kubernetes", "ci/cd", "infrastructure"],
        "professional development": ["professional", "career", "soft skills", "leadership", "personal development"],
    }

    domain_lower = gap_category.lower()
    # Build keyword list: domain words + extra synonyms
    keywords = [w.lower() for w in gap_category.split() if len(w) > 2]
    extra = _DOMAIN_EXTRA_KEYWORDS.get(domain_lower, [])
    all_keywords = list(set(keywords + extra))

    scored: list[tuple[int, dict]] = []
    for course in catalog:
        name_lower = course["name"].lower()
        cat_lower = course.get("category", "").lower()
        combined = f"{name_lower} {cat_lower}"

        hits = 0
        # Exact domain match gets a big boost
        if domain_lower in combined:
            hits += 5
        hits += sum(1 for kw in all_keywords if kw in combined)
        if hits > 0:
            scored.append((hits, course))

    scored.sort(key=lambda x: -x[0])
    return [{"name": c["name"], "link": c["link"]} for _, c in scored[:limit]]


# ---------------------------------------------------------------------------
# Common skill gaps — group employees who share the same gap
# ---------------------------------------------------------------------------
def _build_common_skill_gaps(
    employees: list[dict],
    threshold_pct: int = 20,
    min_group_size: int = 2,
) -> list[dict]:
    """
    Find skill gaps shared by multiple employees. For each gap skill,
    group the affected employees, compute the gap rate, and recommend
    a group course.
    """
    required_num = LEVEL_TO_NUM[DEFAULT_REQUIRED_LEVEL]
    catalog = _build_course_lookup()

    # skill -> list of {employee info, gap details}
    skill_groups: dict[str, list[dict]] = defaultdict(list)

    for emp in employees:
        customer = emp.get("customer", {})
        emp_name = customer.get("CanvasUserId") or customer.get("Email", "Unknown")
        emp_email = customer.get("Email", "")

        emp_skill_values: dict[str, list[int]] = defaultdict(list)
        for assessment in emp.get("assessments", []):
            if assessment.get("Status") != "completed":
                continue
            skills = assessment.get("Skills")
            if isinstance(skills, dict):
                for cr in skills.get("category_results", []):
                    category = cr.get("category", "")
                    response = cr.get("response", "")
                    if category and response in LEVEL_TO_NUM:
                        domain = _normalize_skill(category)
                        emp_skill_values[domain].append(LEVEL_TO_NUM[response])
            elif isinstance(skills, list):
                for item in skills:
                    if isinstance(item, dict) and "name" in item and "percentage" in item:
                        level = _percentage_to_level(item["percentage"])
                        domain = _normalize_skill(item["name"])
                        emp_skill_values[domain].append(LEVEL_TO_NUM[level])

        for category, values in emp_skill_values.items():
            avg_val = sum(values) / len(values)
            gap_pct = round(((required_num - avg_val) / required_num) * 100)
            if gap_pct >= threshold_pct:
                skill_groups[category].append({
                    "name": emp_name,
                    "email": emp_email,
                    "current_level": _avg_to_level(avg_val),
                    "gap_percentage": gap_pct,
                })

    # Only keep groups with >= min_group_size employees
    total_assessed = len([e for e in employees if any(
        a.get("Status") == "completed" for a in e.get("assessments", [])
    )]) or 1

    results: list[dict] = []
    for skill, members in skill_groups.items():
        if len(members) < min_group_size:
            continue
        gap_rate = round((len(members) / total_assessed) * 100)
        avg_gap = round(sum(m["gap_percentage"] for m in members) / len(members))
        courses = _match_courses_for_gap(skill, catalog, limit=2)

        # Build group offer based on group size
        offer = None
        count = len(members)
        if count >= 10:
            offer = {
                "discount": 30,
                "label": f"Unlock a group discount for {skill} workshops.",
            }
        elif count >= 5:
            offer = {
                "discount": 20,
                "label": f"Unlock a group discount for {skill} workshops.",
            }
        elif count >= 2:
            offer = {
                "discount": 10,
                "label": f"Unlock a group discount for {skill} workshops.",
            }

        results.append({
            "skill": skill,
            "affected_count": len(members),
            "total_assessed": total_assessed,
            "gap_rate": gap_rate,
            "avg_gap_percentage": avg_gap,
            "severity": "critical" if avg_gap >= 50 else "moderate",
            "employees": sorted(members, key=lambda m: -m["gap_percentage"]),
            "recommended_courses": courses,
            "offer": offer,
        })

    results.sort(key=lambda r: (-r["affected_count"], -r["avg_gap_percentage"]))
    return results


# ---------------------------------------------------------------------------
# Role-based employee grouping — find employees with the same current role
# ---------------------------------------------------------------------------
def _build_role_groups(employees: list[dict]) -> list[dict]:
    """Group employees by their exact current role; show shared gaps and courses."""
    required_num = LEVEL_TO_NUM[DEFAULT_REQUIRED_LEVEL]
    catalog = _build_course_lookup()
    # Map lowercased role → { "display": original-cased name, "members": [...] }
    role_map: dict[str, dict] = {}

    for emp in employees:
        customer = emp.get("customer", {})
        profile = emp.get("professional_profile")
        role = ""
        target_role = ""
        if profile and isinstance(profile, dict):
            role = profile.get("CurrentRole", "") or ""
            target_role = profile.get("TargetRole", "") or ""
        emp_name = customer.get("CanvasUserId") or customer.get("Email", "Unknown")
        emp_email = customer.get("Email", "")

        # Collect detailed skill gaps with level info
        emp_gaps_map: dict[str, dict] = {}  # domain -> {skill, current_level, required_level}
        for assessment in emp.get("assessments", []):
            if assessment.get("Status") != "completed":
                continue
            skills = assessment.get("Skills")
            if isinstance(skills, dict):
                for cr in skills.get("category_results", []):
                    category = cr.get("category", "")
                    response = cr.get("response", "")
                    if category and response in LEVEL_TO_NUM:
                        domain = _normalize_skill(category)
                        if LEVEL_TO_NUM[response] < required_num:
                            emp_gaps_map[domain] = {
                                "skill": domain,
                                "current_level": response,
                                "required_level": DEFAULT_REQUIRED_LEVEL,
                            }

        emp_gaps_list = sorted(emp_gaps_map.values(), key=lambda g: LEVEL_TO_NUM.get(g["current_level"], 0))

        # Per-employee recommended courses based on their individual gaps
        emp_courses: list[dict] = []
        seen_emp_courses: set[str] = set()
        for gap_info in emp_gaps_list[:5]:
            for c in _match_courses_for_gap(gap_info["skill"], catalog, limit=2):
                if c["name"] not in seen_emp_courses:
                    emp_courses.append(c)
                    seen_emp_courses.add(c["name"])

        role_key = role.strip().lower() or "unknown"
        if role_key not in role_map:
            role_map[role_key] = {"display": role.strip() or "Unknown", "members": []}
        role_map[role_key]["members"].append({
            "name": emp_name,
            "email": emp_email,
            "original_role": role or "N/A",
            "target_role": target_role or "",
            "gaps": emp_gaps_list,
            "recommended_courses": emp_courses[:4],
        })

    groups: list[dict] = []
    for role_key, bucket in role_map.items():
        role_name = bucket["display"]
        members = bucket["members"]
        # Collect all gaps across members and count how often each appears
        gap_counts: dict[str, int] = defaultdict(int)
        for m in members:
            for g in m["gaps"]:
                gap_counts[g["skill"]] += 1

        # Shared = appears in 2+ members; if group has 1 member, use all their gaps
        if len(members) >= 2:
            shared_gaps = [g for g, cnt in gap_counts.items() if cnt >= 2]
            # If nobody shares the same gap but all have gaps, include the most common ones
            if not shared_gaps:
                shared_gaps = list(gap_counts.keys())
        else:
            shared_gaps = list(gap_counts.keys())

        shared_gaps.sort(key=lambda g: -gap_counts.get(g, 0))

        # Match courses for the top shared gaps
        recommended_courses: list[dict] = []
        seen_course_names: set[str] = set()
        for gap in shared_gaps[:5]:
            for c in _match_courses_for_gap(gap, catalog, limit=2):
                if c["name"] not in seen_course_names:
                    recommended_courses.append(c)
                    seen_course_names.add(c["name"])

        logger.info(
            "Role group '%s': %d members, gaps=%s, shared=%s, courses=%d",
            role_name, len(members), list(gap_counts.keys()), shared_gaps, len(recommended_courses),
        )

        groups.append({
            "role": role_name,
            "count": len(members),
            "employees": members,
            "shared_gaps": shared_gaps[:8],
            "recommended_courses": recommended_courses[:6],
        })

    groups.sort(key=lambda g: -g["count"])
    return groups


# ---------------------------------------------------------------------------
# Company report builder
# ---------------------------------------------------------------------------
def build_company_report(company: Company) -> dict:
    from .serializers import CompanySerializer

    members = selectors.list_company_members(company)
    employees = []
    all_strengths: list[str] = []
    all_weaknesses: list[str] = []

    for member in members:
        # Exclude the company owner from employee calculations
        if str(member.Customer.CustomerId) == str(company.Owner_id):
            continue

        emp_data = build_employee_data(member.Customer)
        employees.append(emp_data)

        # Fixed: read from nested Skills dict (lowercase keys)
        for assessment in emp_data["assessments"]:
            skills = assessment.get("Skills")
            if isinstance(skills, dict):
                for s in skills.get("strengths", []):
                    name = s.get("name", "") if isinstance(s, dict) else str(s)
                    if name:
                        all_strengths.append(name)
                for w in skills.get("weaknesses", []):
                    name = w.get("name", "") if isinstance(w, dict) else str(w)
                    if name:
                        all_weaknesses.append(name)

    skill_overview, skill_gaps = _aggregate_skills(employees)
    common_skill_gaps = _build_common_skill_gaps(employees)
    role_groups = _build_role_groups(employees)

    return {
        "company": CompanySerializer(company).data,
        "total_employees": len(employees),
        "employees": employees,
        "aggregated_strengths": list(set(all_strengths)),
        "aggregated_weaknesses": list(set(all_weaknesses)),
        "skill_overview": skill_overview,
        "skill_gaps": skill_gaps,
        "common_skill_gaps": common_skill_gaps,
        "role_groups": role_groups,
    }


# ---------------------------------------------------------------------------
# Weekly Report — email the company owner a summary of the B2B dashboard
# ---------------------------------------------------------------------------
def send_weekly_report_for_company(company: Company) -> bool:
    """Build the report and email it to the company owner."""
    report = build_company_report(company)
    owner_email = company.Owner.Email
    return send_weekly_report_email(
        to_email=owner_email,
        company_name=company.Name,
        report=report,
    )


def send_all_weekly_reports() -> dict:
    """Send weekly reports for every company. Returns summary stats."""
    companies = Company.objects.select_related("Owner").all()
    sent = 0
    failed = []

    for company in companies:
        try:
            ok = send_weekly_report_for_company(company)
            if ok:
                sent += 1
            else:
                failed.append(company.Name)
        except Exception as e:
            logger.error("Weekly report failed for %s: %s", company.Name, e)
            failed.append(company.Name)

    logger.info("Weekly reports: %d sent, %d failed", sent, len(failed))
    return {"sent": sent, "failed": failed, "total": sent + len(failed)}
