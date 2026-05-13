from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse, Http404


def translation_json(request, language_code: str) -> JsonResponse:
    translations_dir = Path(settings.BASE_DIR) / "translations"
    translation_file = translations_dir / f"{language_code}.json"

    if not translation_file.exists():
        raise Http404("Translation file not found")

    with translation_file.open("r", encoding="utf-8") as translation_handle:
        translation_data = json.load(translation_handle)

    return JsonResponse(translation_data)
