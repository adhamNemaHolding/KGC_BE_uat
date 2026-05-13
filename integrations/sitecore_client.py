"""
Sitecore Delivery API client — fetch courses from Sitecore XMC.

Isolated integration: the rest of the codebase imports
`fetch_sitecore_courses` and `clear_cache` from here.
"""

from __future__ import annotations

import logging
import re

import requests
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

SITECORE_EDGE_URL = "https://edge.sitecorecloud.io/api/graphql/v1"
SITECORE_ITEM_ID = "{ADBD0F80-5DF5-46E2-97F1-395A901842BC}"


def _get_api_key() -> str:
    return getattr(django_settings, "SITECORE_API_KEY", "")


def _get_site() -> str:
    return getattr(django_settings, "SITECORE_SITE", "corporate-website")

GRAPHQL_QUERY = """
query {
  item(path: "%s", language: "en") {
    relatedItems: field(name: "AvailableCourses") {
      ...on MultilistField {
        targetItems {
          id
          name
          displayName
          created: field(name: "__created") { value }
          url { path }
          courseTitle: field(name: "CourseTitle") { ... on TextField { value } }
          courseDescription: field(name: "ProgramDetails") { ... on RichTextField { value } }
        }
      }
    }
  }
}
""" % SITECORE_ITEM_ID

KGC_SITE_BASE = "https://www.kgc.com"


def _strip_html(value: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()

_cache: dict = {"courses": None, "fetched": False}


def fetch_sitecore_courses(force_refresh: bool = False) -> list[dict]:
    if _cache["fetched"] and not force_refresh:
        return _cache["courses"] or []

    api_key = _get_api_key()
    if not api_key:
        logger.warning("SITECORE_API_KEY is not set — skipping Sitecore course fetch. "
                       "Add it to your .env to enable KGC course recommendations.")
        _cache["fetched"] = True
        _cache["courses"] = []
        return []

    try:
        response = requests.post(
            SITECORE_EDGE_URL,
            json={"query": GRAPHQL_QUERY},
            headers={
                "Content-Type": "application/json",
                "sc_apikey": _get_api_key(),
                "sc_site": _get_site(),
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        items = (
            data.get("data", {})
            .get("item", {})
            .get("relatedItems", {})
            .get("targetItems", [])
        )

        courses: list[dict] = []
        for item in items:
            title = ""
            course_title_field = item.get("courseTitle")
            if isinstance(course_title_field, dict):
                title = course_title_field.get("value", "")
            if not title:
                title = item.get("displayName") or item.get("name") or ""

            url_path = ""
            url_field = item.get("url")
            if isinstance(url_field, dict):
                url_path = url_field.get("path", "")

            link = f"{KGC_SITE_BASE}{url_path}" if url_path else ""

            created = ""
            created_field = item.get("created")
            if isinstance(created_field, dict):
                created = created_field.get("value", "")

            description = ""
            desc_field = item.get("courseDescription")
            if isinstance(desc_field, dict):
                raw = desc_field.get("value", "")
                description = _strip_html(raw) if raw else ""

            courses.append({
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "title": title,
                "description": description,
                "link": link,
                "created": created,
                "source": "sitecore",
            })

        _cache["courses"] = courses
        _cache["fetched"] = True
        logger.info("Fetched %d courses from Sitecore", len(courses))
        return courses

    except Exception as e:
        logger.warning("Failed to fetch Sitecore courses: %s", e)
        _cache["fetched"] = True
        _cache["courses"] = []
        return []


def clear_cache() -> None:
    _cache["courses"] = None
    _cache["fetched"] = False
