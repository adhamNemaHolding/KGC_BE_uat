"""
Email client — wraps Django's send_mail with KGC branded templates.

Isolated integration: import `send_verification_email` from here.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str, token: str) -> bool:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    subject = "Verify your email — Knowledge Group"

    html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Public Sans',Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
          <tr>
            <td align="center" style="padding-bottom:24px;">
              <a href="{settings.FRONTEND_URL}" style="text-decoration:none;">
                <img src="https://edge.sitecorecloud.io/knowledgegr57d2-kgccorporat418f-productionec85-e740/media/KGC/Header/header-logo.svg?iar=0" alt="Knowledge Group Consulting" style="height:40px;" />
              </a>
            </td>
          </tr>
          <tr>
            <td>
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
                <tr>
                  <td style="background:linear-gradient(135deg,#066a7f,#087891);height:100px;text-align:center;vertical-align:middle;">
                    <div style="width:56px;height:56px;margin:0 auto;background:rgba(255,255,255,0.15);border-radius:12px;line-height:56px;font-size:28px;">
                      &#9993;
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:40px 40px 36px;">
                    <h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#0f172a;text-align:center;">
                      Verify your email address
                    </h1>
                    <p style="margin:0 0 28px;font-size:15px;line-height:1.7;color:#64748b;text-align:center;">
                      Welcome to Knowledge Group AI Skill Advisor! To start personalizing your
                      learning journey, please verify your email by clicking the
                      button below.
                    </p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center">
                          <a href="{verify_url}"
                             style="display:inline-block;background:#087891;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;padding:14px 40px;border-radius:10px;letter-spacing:0.2px;">
                            Verify My Email
                          </a>
                        </td>
                      </tr>
                    </table>
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin:28px 0;">
                      <tr>
                        <td><hr style="border:none;border-top:1px solid #e2e8f0;"></td>
                        <td style="padding:0 12px;white-space:nowrap;">
                          <span style="font-size:10px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Or copy link</span>
                        </td>
                        <td><hr style="border:none;border-top:1px solid #e2e8f0;"></td>
                      </tr>
                    </table>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="background:#f1f5f9;border-radius:8px;padding:12px 16px;">
                          <a href="{verify_url}" style="font-size:12px;color:#087891;word-break:break-all;text-decoration:none;font-family:monospace;">
                            {verify_url}
                          </a>
                        </td>
                      </tr>
                    </table>
                    <p style="margin:24px 0 0;font-size:13px;color:#94a3b8;text-align:center;">
                      Didn't create an account? You can safely ignore this email.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 0;text-align:center;">
              <p style="margin:0;font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;">
                &copy; 2026 Knowledge Group. All rights reserved.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    plain_message = f"""
Verify your email address

Welcome to Knowledge Group! To start personalizing your learning journey,
please verify your email by clicking the link below:

{verify_url}

Didn't create an account? You can safely ignore this email.
"""

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Verification email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send verification email to %s: %s", to_email, e)
        return False


def send_invitation_email(to_email: str, company_name: str, company_code: str, invite_token: str) -> bool:
    """Send an HR invitation email with a direct signup link."""
    signup_url = (
        f"{settings.FRONTEND_URL}/signup"
        f"?invite={invite_token}"
        f"&email={to_email}"
        f"&company_code={company_code}"
    )

    subject = f"You're invited to join {company_name} — Knowledge Group"

    html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Public Sans',Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
        <tr><td align="center" style="padding-bottom:24px;">
          <a href="{settings.FRONTEND_URL}" style="text-decoration:none;">
            <img src="https://edge.sitecorecloud.io/knowledgegr57d2-kgccorporat418f-productionec85-e740/media/KGC/Header/header-logo.svg?iar=0" alt="Knowledge Group Consulting" style="height:40px;" />
          </a>
        </td></tr>
        <tr><td>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
            <tr><td style="background:linear-gradient(135deg,#066a7f,#087891);height:100px;text-align:center;vertical-align:middle;">
              <div style="width:56px;height:56px;margin:0 auto;background:rgba(255,255,255,0.15);border-radius:12px;line-height:56px;font-size:28px;">&#128188;</div>
            </td></tr>
            <tr><td style="padding:40px 40px 36px;">
              <h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#0f172a;text-align:center;">
                You&rsquo;re invited to join {company_name}
              </h1>
              <p style="margin:0 0 28px;font-size:15px;line-height:1.7;color:#64748b;text-align:center;">
                Your HR team has invited you to the KGC AI Skill Advisor platform.
                Click below to create your account and start your skill development journey.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr><td align="center">
                  <a href="{signup_url}"
                     style="display:inline-block;background:#087891;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;padding:14px 40px;border-radius:10px;letter-spacing:0.2px;">
                    Join {company_name}
                  </a>
                </td></tr>
              </table>
              <p style="margin:24px 0 0;font-size:13px;color:#94a3b8;text-align:center;">
                Your email will be pre-filled and your account will be automatically verified.
              </p>
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="padding:24px 0;text-align:center;">
          <p style="margin:0;font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;">
            &copy; 2026 Knowledge Group. All rights reserved.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    plain_message = f"""
You're invited to join {company_name}

Your HR team has invited you to the KGC AI Skill Advisor platform.
Click the link below to create your account:

{signup_url}

Your email will be pre-filled and your account will be automatically verified.
"""

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Invitation email sent to %s for company %s", to_email, company_name)
        return True
    except Exception as e:
        logger.error("Failed to send invitation email to %s: %s (type: %s)", to_email, e, type(e).__name__)
        import traceback
        logger.error("Traceback: %s", traceback.format_exc())
        return False


def send_existing_user_invitation_email(
    to_email: str, company_name: str, company_code: str
) -> bool:
    """Send an invitation email to a user who already has an account, with the company code."""
    settings_url = f"{settings.FRONTEND_URL}/settings"

    subject = f"You're invited to join {company_name} — Knowledge Group"

    html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Public Sans',Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
        <tr><td align="center" style="padding-bottom:24px;">
          <a href="{settings.FRONTEND_URL}" style="text-decoration:none;">
            <img src="https://edge.sitecorecloud.io/knowledgegr57d2-kgccorporat418f-productionec85-e740/media/KGC/Header/header-logo.svg?iar=0" alt="Knowledge Group Consulting" style="height:40px;" />
          </a>
        </td></tr>
        <tr><td>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
            <tr><td style="background:linear-gradient(135deg,#066a7f,#087891);height:100px;text-align:center;vertical-align:middle;">
              <div style="width:56px;height:56px;margin:0 auto;background:rgba(255,255,255,0.15);border-radius:12px;line-height:56px;font-size:28px;">&#128188;</div>
            </td></tr>
            <tr><td style="padding:40px 40px 36px;">
              <h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#0f172a;text-align:center;">
                You&rsquo;re invited to join {company_name}
              </h1>
              <p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#64748b;text-align:center;">
                Your HR team has invited you to join <strong>{company_name}</strong> on the
                KGC AI Skill Advisor platform. Since you already have an account, simply
                use the company code below in your Settings page to link your account.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                <tr><td align="center">
                  <table cellpadding="0" cellspacing="0" style="background:#f1f5f9;border-radius:12px;padding:20px 32px;">
                    <tr><td align="center">
                      <p style="margin:0 0 4px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;">Company Code</p>
                      <p style="margin:0;font-size:32px;font-weight:800;color:#087891;letter-spacing:4px;">{company_code}</p>
                    </td></tr>
                  </table>
                </td></tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr><td align="center">
                  <a href="{settings_url}"
                     style="display:inline-block;background:#087891;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;padding:14px 40px;border-radius:10px;letter-spacing:0.2px;">
                    Go to Settings
                  </a>
                </td></tr>
              </table>
              <p style="margin:24px 0 0;font-size:13px;color:#94a3b8;text-align:center;">
                Open your Settings page, paste the code above in the Company Code field,
                and click &ldquo;Join Company&rdquo;.
              </p>
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="padding:24px 0;text-align:center;">
          <p style="margin:0;font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;">
            &copy; 2026 Knowledge Group. All rights reserved.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    plain_message = f"""
You're invited to join {company_name}

Your HR team has invited you to join {company_name} on the KGC AI Skill Advisor platform.
Since you already have an account, use the company code below in your Settings page:

Company Code: {company_code}

Go to Settings: {settings_url}

Open your Settings page, paste the code in the Company Code field, and click "Join Company".
"""

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Existing-user invitation email sent to %s for company %s", to_email, company_name)
        return True
    except Exception as e:
        logger.error("Failed to send existing-user invitation email to %s: %s", to_email, e)
        return False


def send_weekly_report_email(to_email: str, company_name: str, report: dict) -> bool:
    """Send the weekly company report email summarising the B2B dashboard."""
    from datetime import date

    dashboard_url = f"{settings.FRONTEND_URL}/b2b"
    today = date.today().strftime("%B %d, %Y")

    total_employees = report.get("total_employees", 0)
    skill_overview = report.get("skill_overview", [])
    skill_gaps = report.get("skill_gaps", [])
    common_skill_gaps = report.get("common_skill_gaps", [])
    role_groups = report.get("role_groups", [])
    strengths = report.get("aggregated_strengths", [])
    weaknesses = report.get("aggregated_weaknesses", [])

    assessed_count = sum(
        1 for emp in report.get("employees", [])
        if any(a.get("Status") == "completed" for a in emp.get("assessments", []))
    )

    # ── Build HTML sections ──────────────────────────────────────
    # Skill Overview table rows
    skill_rows = ""
    for s in skill_overview[:12]:
        level_color = {
            "Beginner": "#ef4444", "Intermediate": "#f59e0b",
            "Advanced": "#22c55e", "Expert": "#0891b2",
        }.get(s["avg_level"], "#64748b")
        skill_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0f172a;">{s['category']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;">
            <span style="font-size:12px;font-weight:700;color:{level_color};">{s['avg_level']}</span>
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;font-size:13px;color:#64748b;">{s['employee_count']}</td>
        </tr>"""

    # Skill Gaps table rows
    gap_rows = ""
    for g in skill_gaps[:10]:
        severity_bg = "#fef2f2" if g["gap_severity"] == "critical" else "#fffbeb"
        severity_color = "#dc2626" if g["gap_severity"] == "critical" else "#d97706"
        gap_rows += f"""
        <tr style="background:{severity_bg};">
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0f172a;">{g['category']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;font-size:12px;color:#64748b;">{g['current_level']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;font-size:12px;color:#64748b;">{g['required_level']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;">
            <span style="font-size:11px;font-weight:700;color:{severity_color};text-transform:uppercase;">{g['gap_severity']}</span>
          </td>
        </tr>"""

    # Common Skill Gaps section
    common_gaps_html = ""
    if common_skill_gaps:
        common_items = ""
        for cg in common_skill_gaps[:6]:
            courses_html = ", ".join(
                f'<a href="{c["link"]}" style="color:#087891;text-decoration:none;">{c["name"]}</a>'
                if c.get("link") else c["name"]
                for c in cg.get("recommended_courses", [])[:2]
            ) or "—"
            common_items += f"""
            <tr>
              <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0f172a;">{cg['skill']}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;font-size:13px;color:#0f172a;font-weight:700;">{cg['affected_count']}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;font-size:12px;color:#64748b;">{cg['gap_rate']}%</td>
              <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#64748b;">{courses_html}</td>
            </tr>"""
        common_gaps_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
          <tr><td style="padding-bottom:12px;">
            <h2 style="margin:0;font-size:16px;font-weight:700;color:#0f172a;">Common Skill Gaps</h2>
            <p style="margin:4px 0 0;font-size:13px;color:#64748b;">Skills where multiple employees need improvement</p>
          </td></tr>
          <tr><td>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
              <tr style="background:#f8fafc;">
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Skill</th>
                <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Affected</th>
                <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Gap Rate</th>
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Recommended</th>
              </tr>
              {common_items}
            </table>
          </td></tr>
        </table>"""

    # Role Groups summary
    role_groups_html = ""
    if role_groups:
        role_items = ""
        for rg in role_groups[:8]:
            shared = ", ".join(rg.get("shared_gaps", [])[:3]) or "None identified"
            role_items += f"""
            <tr>
              <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0f172a;font-weight:600;">{rg['role']}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;font-size:13px;color:#0f172a;">{rg['count']}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#64748b;">{shared}</td>
            </tr>"""
        role_groups_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
          <tr><td style="padding-bottom:12px;">
            <h2 style="margin:0;font-size:16px;font-weight:700;color:#0f172a;">Role Groups</h2>
            <p style="margin:4px 0 0;font-size:13px;color:#64748b;">Employees grouped by current role</p>
          </td></tr>
          <tr><td>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
              <tr style="background:#f8fafc;">
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Role</th>
                <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Count</th>
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Shared Gaps</th>
              </tr>
              {role_items}
            </table>
          </td></tr>
        </table>"""

    # Strengths / Weaknesses
    strengths_html = ""
    if strengths:
        items = "".join(
            f'<span style="display:inline-block;background:#ecfdf5;color:#059669;font-size:12px;font-weight:600;padding:4px 10px;border-radius:6px;margin:3px 3px 3px 0;">{s}</span>'
            for s in strengths[:10]
        )
        strengths_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;">
          <tr><td>
            <h3 style="margin:0 0 8px;font-size:14px;font-weight:700;color:#0f172a;">Top Strengths</h3>
            <td style="line-height:2;">{items}</td>
          </td></tr>
        </table>"""

    weaknesses_html = ""
    if weaknesses:
        items = "".join(
            f'<span style="display:inline-block;background:#fef2f2;color:#dc2626;font-size:12px;font-weight:600;padding:4px 10px;border-radius:6px;margin:3px 3px 3px 0;">{w}</span>'
            for w in weaknesses[:10]
        )
        weaknesses_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">
          <tr><td>
            <h3 style="margin:0 0 8px;font-size:14px;font-weight:700;color:#0f172a;">Areas for Improvement</h3>
            <td style="line-height:2;">{items}</td>
          </td></tr>
        </table>"""

    subject = f"Weekly Report — {company_name} | {today}"

    html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Public Sans',Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

        <!-- Logo -->
        <tr><td align="center" style="padding-bottom:24px;">
          <a href="{settings.FRONTEND_URL}" style="text-decoration:none;">
            <img src="https://edge.sitecorecloud.io/knowledgegr57d2-kgccorporat418f-productionec85-e740/media/KGC/Header/header-logo.svg?iar=0" alt="Knowledge Group Consulting" style="height:40px;" />
          </a>
        </td></tr>

        <!-- Main Card -->
        <tr><td>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.06);">

            <!-- Header Banner -->
            <tr><td style="background:linear-gradient(135deg,#066a7f,#087891);padding:32px 40px;">
              <h1 style="margin:0 0 4px;font-size:22px;font-weight:700;color:#ffffff;">Weekly Report</h1>
              <p style="margin:0;font-size:14px;color:rgba(255,255,255,0.8);">{company_name} &mdash; {today}</p>
            </td></tr>

            <!-- Body -->
            <tr><td style="padding:32px 40px;">

              <!-- KPI Cards -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td width="33%" style="padding-right:8px;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdfa;border-radius:10px;padding:16px;text-align:center;">
                      <tr><td>
                        <p style="margin:0;font-size:28px;font-weight:800;color:#087891;">{total_employees}</p>
                        <p style="margin:4px 0 0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Employees</p>
                      </td></tr>
                    </table>
                  </td>
                  <td width="33%" style="padding:0 4px;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border-radius:10px;padding:16px;text-align:center;">
                      <tr><td>
                        <p style="margin:0;font-size:28px;font-weight:800;color:#16a34a;">{assessed_count}</p>
                        <p style="margin:4px 0 0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Assessed</p>
                      </td></tr>
                    </table>
                  </td>
                  <td width="33%" style="padding-left:8px;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef2f2;border-radius:10px;padding:16px;text-align:center;">
                      <tr><td>
                        <p style="margin:0;font-size:28px;font-weight:800;color:#dc2626;">{len(skill_gaps)}</p>
                        <p style="margin:4px 0 0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Skill Gaps</p>
                      </td></tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Skill Overview -->
              {"" if not skill_overview else f'''
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr><td style="padding-bottom:12px;">
                  <h2 style="margin:0;font-size:16px;font-weight:700;color:#0f172a;">Skill Overview</h2>
                  <p style="margin:4px 0 0;font-size:13px;color:#64748b;">Average skill levels across your team</p>
                </td></tr>
                <tr><td>
                  <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                    <tr style="background:#f8fafc;">
                      <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Skill</th>
                      <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Avg Level</th>
                      <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Employees</th>
                    </tr>
                    {skill_rows}
                  </table>
                </td></tr>
              </table>
              '''}

              <!-- Skill Gaps -->
              {"" if not skill_gaps else f'''
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
                <tr><td style="padding-bottom:12px;">
                  <h2 style="margin:0;font-size:16px;font-weight:700;color:#0f172a;">Skill Gaps</h2>
                  <p style="margin:4px 0 0;font-size:13px;color:#64748b;">Areas where employees need to upskill</p>
                </td></tr>
                <tr><td>
                  <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                    <tr style="background:#f8fafc;">
                      <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Skill</th>
                      <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Current</th>
                      <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Required</th>
                      <th style="padding:10px 12px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Severity</th>
                    </tr>
                    {gap_rows}
                  </table>
                </td></tr>
              </table>
              '''}

              {common_gaps_html}
              {role_groups_html}
              {strengths_html}
              {weaknesses_html}

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:32px;">
                <tr><td align="center">
                  <a href="{dashboard_url}"
                     style="display:inline-block;background:#087891;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;padding:14px 40px;border-radius:10px;letter-spacing:0.2px;">
                    View Full Dashboard
                  </a>
                </td></tr>
              </table>

            </td></tr>
          </table>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:24px 0;text-align:center;">
          <p style="margin:0;font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;">
            &copy; 2026 Knowledge Group. All rights reserved.
          </p>
          <p style="margin:6px 0 0;font-size:10px;color:#94a3b8;">
            This is an automated weekly report for {company_name}.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    plain_message = f"""
Weekly Report — {company_name} | {today}
{'=' * 50}

TEAM OVERVIEW
  Employees: {total_employees}
  Assessed: {assessed_count}
  Skill Gaps: {len(skill_gaps)}

SKILL OVERVIEW
""" + "\n".join(f"  {s['category']}: {s['avg_level']} ({s['employee_count']} employees)" for s in skill_overview[:12]) + f"""

SKILL GAPS
""" + "\n".join(f"  {g['category']}: {g['current_level']} → {g['required_level']} ({g['gap_severity']})" for g in skill_gaps[:10]) + f"""

View the full dashboard: {dashboard_url}
"""

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Weekly report email sent to %s for company %s", to_email, company_name)
        return True
    except Exception as e:
        logger.error("Failed to send weekly report email to %s: %s", to_email, e)
        return False
