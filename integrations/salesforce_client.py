"""
Salesforce client — create Leads via Salesforce REST API.

Isolated integration: the rest of the codebase imports
`create_salesforce_lead` from here.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


def _get_access_token() -> tuple[str, str] | None:
    """
    Authenticate via client_credentials and return (access_token, instance_url).
    Returns None on failure.
    """
    client_id = getattr(django_settings, "SALESFORCE_CLIENT_ID", "")
    client_secret = getattr(django_settings, "SALESFORCE_CLIENT_SECRET", "")
    token_url = getattr(django_settings, "SALESFORCE_TOKEN_URL", "")

    if not client_id or not client_secret or not token_url:
        logger.warning("Salesforce credentials not configured — skipping lead creation.")
        return None

    try:
        resp = requests.post(
            token_url,
            params={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        access_token = data.get("access_token")
        instance_url = data.get("instance_url")
        if not access_token or not instance_url:
            logger.error("Salesforce token response missing access_token or instance_url.")
            return None
        return access_token, instance_url
    except Exception as e:
        logger.error("Salesforce token request failed: %s", e)
        return None


def create_salesforce_lead(
    *,
    first_name: str,
    last_name: str,
    email: str,
    company: str = "",
) -> bool:
    """
    Create a Lead in Salesforce. Returns True on success, False on failure.
    Never raises — failures are logged and swallowed so signup is not blocked.
    """
    auth = _get_access_token()
    if not auth:
        return False

    access_token, instance_url = auth

    lead_url = f"{instance_url}/services/data/v66.0/sobjects/Lead/"
    payload = {
        "FirstName": first_name,
        "LastName": last_name or "(no last name)",
        "Email": email,
        "Company": company if company else "N/A",
    }

    try:
        resp = requests.post(
            lead_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info("Salesforce Lead created for %s", email)
            return True
        else:
            logger.error(
                "Salesforce Lead creation failed (%s): %s",
                resp.status_code,
                resp.text,
            )
            return False
    except Exception as e:
        logger.error("Salesforce Lead request failed: %s", e)
        return False
