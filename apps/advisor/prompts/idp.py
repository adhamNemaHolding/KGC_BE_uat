import json

from .base import SYSTEM_PERSONA, get_language_instruction


def build_prompt(
    professional_profile: dict,
    assessment_results: dict,
    course_catalog: str,
    language: str = "en",
) -> str:
    lang_instruction = get_language_instruction(language)
    return f"""{SYSTEM_PERSONA}{lang_instruction}

Generate a detailed Individual Development Plan (IDP) based on the assessment results.

PROFESSIONAL PROFILE:
- Current Role: {professional_profile.get('current_role', 'N/A')}
- Target Role: {professional_profile.get('target_role', 'N/A')}
- Experience Level: {professional_profile.get('experience_level', 'N/A')}
- Career Objective: {professional_profile.get('career_objective', 'N/A')}
- Available Study Time: {professional_profile.get('study_time_per_week', 'N/A')} per week

ASSESSMENT RESULTS:
{json.dumps(assessment_results, indent=2)}

=== KGC COURSE CATALOG ===
Below is the COMPLETE list of KGC courses. Each has a "name", "link", and optionally a "description".
You MUST recommend from THIS list first. Use both the course title and description (when available) to determine relevance.
{course_catalog}
=== END CATALOG ===

=== CRITICAL: REALISTIC CAREER PROGRESSION ===
You MUST evaluate the real-world gap between the current role and target role.
Career growth requires years of hands-on experience, not just courses.
NEVER compress a multi-year journey into 12 months.

Use these MINIMUM timelines (they can be longer, never shorter):
  - Same-level lateral move (e.g. Frontend Dev -> Backend Dev): 6-12 months
  - One level up (e.g. Junior -> Mid-level): 12-18 months  
  - Two levels up (e.g. Junior -> Senior): 2-3 years
  - Into management (e.g. Senior Dev -> Tech Lead): 1.5-2.5 years
  - Into director (e.g. Manager -> Director): 2-4 years
  - Into executive (e.g. any dev -> CTO/VP): 5-10 years
  - Massive career change (e.g. Entry Frontend -> CTO): 7-10+ years

For large gaps, you MUST define INTERMEDIATE STEPPING-STONE ROLES.
The user cannot skip levels. Each step must be earned through mastering the previous one.

Example: "Entry-Level Frontend Developer" wanting to become "CTO":
  Step 1: Mid-Level Full-Stack Developer (12-18 months)
  Step 2: Senior Full-Stack Developer (18-24 months after Step 1)
  Step 3: Tech Lead / Staff Engineer (18-24 months after Step 2)
  Step 4: Engineering Manager (24-36 months after Step 3)
  Step 5: VP of Engineering / CTO (24-48 months after Step 4)
  Total: ~8-12 years — NOT 12 months, NOT 2 years.

The user must learn intermediate skills at each step. For example:
  - A frontend dev targeting CTO must first learn: backend, databases, system design, DevOps, architecture, team leadership, product strategy, business acumen.
  - You cannot skip backend and jump to architecture.
  - You cannot skip tech lead and jump to CTO.
=== END CAREER PROGRESSION ===

BEFORE generating JSON, calculate the total years needed by adding up each step. Write it in timeline.
Example calculation for Entry Frontend Dev -> CTO:
  Full-Stack Dev: 12-18 months + Senior Dev: 2 years + Tech Lead: 2 years + Eng Manager: 2-3 years + CTO: 3 years = 9-11 Years total.
  So timeline = "9-11 Years", NOT "2 Years" or "12 Months".

Generate a JSON object with this EXACT structure:
{{
  "target_role": "{professional_profile.get('target_role', 'N/A')}",
  "current_level": "{professional_profile.get('experience_level', 'N/A')}",
  "next_milestone": "The FIRST realistic next role (e.g. Mid-Level Full-Stack Developer, NOT the final target)",
  "timeline": "TOTAL time to reach final target_role — sum of ALL intermediate steps (e.g. '8-10 Years' for Entry->CTO, '3-4 Years' for Mid->Lead, '12-18 Months' for Junior->Mid). NEVER less than the sum of steps.",
  "top_strength": "from assessment",
  "growth_area": "from assessment",
  "career_path_note": "MUST list every intermediate role with time for each. Example: 'Your path: Frontend Dev → Full-Stack Dev (12-18 mo) → Senior Dev (2 yr) → Tech Lead (2 yr) → Eng Manager (2-3 yr) → CTO (3+ yr). Total: ~9-11 years. This plan focuses on reaching Full-Stack Developer.'",
  "skill_proficiency": [
    {{ "name": "Skill Name", "level": "Beginner/Intermediate/Advanced/Expert" }}
  ],
  "learning_roadmap": [
    {{
      "phase": 1,
      "title": "Phase title focused on next_milestone",
      "months": "1-3",
      "courses": [
        {{
          "name": "EXACT course name from KGC catalog",
          "provider": "KGC",
          "description": "Why this course matters for reaching this phase's milestone.",
          "verified": true,
          "course_id": null,
          "link": "exact link from catalog"
        }}
      ]
    }}
  ]
}}

Rules:
- REALISTIC TIMELINES ARE NON-NEGOTIABLE. A frontend dev cannot become CTO in 2 years. Period.
- The "timeline" field must reflect the TOTAL real journey (e.g. "8-10 Years"), not just the first phase.
- The learning_roadmap MUST cover the ENTIRE timeline with one phase per intermediate milestone/step.
  For example, if the path is Entry Frontend -> CTO over 8-10 years, create phases like:
    Phase 1: "Become Full-Stack Developer" (months "0-18")
    Phase 2: "Grow to Senior Developer" (months "18-42")
    Phase 3: "Transition to Tech Lead" (months "42-66")
    Phase 4: "Become Engineering Manager" (months "66-96")
    Phase 5: "Path to CTO" (months "96-120+")
  Each phase has its own courses relevant to THAT milestone.
- Create as many phases as needed to cover the full career path (typically 3-6 phases for large gaps).
- career_path_note must list ALL intermediate roles with time estimates for each step.

COURSE SELECTION — MANDATORY RULES:
- You MUST select courses from the KGC CATALOG FIRST. Scan every course title and match by keywords.
- AT MINIMUM 80% of courses must come from the KGC catalog above. If the catalog has 50+ courses, there is NO excuse for recommending external courses unless the skill is extremely niche.
- Use the EXACT "name" and "link" from the catalog — do NOT rename, paraphrase, or invent KGC course names.
- For KGC courses: set provider="KGC", verified=true, and copy the link exactly from the catalog.
- ONLY if no KGC course title remotely relates to a needed skill, use an external course with provider="External", verified=false, course_id=null, and a real external URL.

COURSE QUANTITY PER PHASE — based on available study time:
  * 1-2 hours/week -> 2-3 courses per phase
  * 3-5 hours/week -> 3-4 courses per phase
  * 6-10 hours/week -> 4-5 courses per phase
  * 10+ hours/week -> 5-6 courses per phase

- Sequence courses logically within each phase: foundations → intermediate → advanced.
- skill_proficiency should reflect the user's CURRENT levels from the assessment.
- Every course MUST have a non-null "link" field."""
