"""
Management command to send weekly reports to all B2B companies.

Usage:
    python manage.py send_weekly_report          # all companies
    python manage.py send_weekly_report --company-id <uuid>  # single company

Schedule via cron (e.g. every Sunday at 8 AM):
    0 8 * * 0  cd /path/to/backend && python manage.py send_weekly_report
"""

from django.core.management.base import BaseCommand

from apps.companies import selectors, services


class Command(BaseCommand):
    help = "Send a weekly report email to every B2B company owner."

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=str,
            default=None,
            help="Send report for a single company (by CompanyId UUID).",
        )

    def handle(self, *args, **options):
        company_id = options["company_id"]

        if company_id:
            company = selectors.get_company_by_id(company_id)
            if not company:
                self.stderr.write(self.style.ERROR(f"Company with ID {company_id} not found."))
                return
            ok = services.send_weekly_report_for_company(company)
            if ok:
                self.stdout.write(self.style.SUCCESS(f"Weekly report sent to {company.Owner.Email} for {company.Name}."))
            else:
                self.stderr.write(self.style.ERROR(f"Failed to send report for {company.Name}."))
            return

        result = services.send_all_weekly_reports()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Sent: {result['sent']}, Failed: {len(result['failed'])}, Total: {result['total']}"
            )
        )
        if result["failed"]:
            self.stderr.write(self.style.WARNING(f"Failed companies: {', '.join(result['failed'])}"))
