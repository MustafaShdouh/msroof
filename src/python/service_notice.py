"""Shared service-availability grammar, independent of institution and amount."""
import json
import re
from pathlib import Path

RULES = json.loads((Path(__file__).resolve().parents[2] / "config/contracts/service_notice.json").read_text(encoding="utf-8"))
SERVICE_NOTICE_REASON = RULES["reason"]
SERVICE = re.compile(RULES["servicePattern"], re.I | re.ASCII)
AVAILABILITY = re.compile(RULES["availabilityPattern"], re.I | re.ASCII)
COMPLETION = re.compile(RULES["completionPattern"], re.I | re.ASCII)
DIACRITICS = re.compile(r"[\u064B-\u065F\u0670]")


def is_service_notice(body):
    text = DIACRITICS.sub("", body)
    return bool(SERVICE.search(text) and AVAILABILITY.search(text) and not COMPLETION.search(text))
