"""Profile store — reads/writes the local family/personal profiles JSON.

Used by the People screen (write) and the Dietitian & Safety agent + Head Chef
(read). The seam between Nate's UI and Itay's backend is this file's shape.

Storage: data/profiles.json (gitignored personal data). If it doesn't exist yet,
we seed from the committed data/profiles.example.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from shared.models import Profile

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROFILES = _DATA_DIR / "profiles.json"
_EXAMPLE = _DATA_DIR / "profiles.example.json"


def _read_json(path: Path) -> list[Profile]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Profile.model_validate(p) for p in data.get("profiles", [])]


def load_profiles() -> list[Profile]:
    """Load saved profiles, seeding from the example file on first run."""
    if _PROFILES.exists():
        return _read_json(_PROFILES)
    if _EXAMPLE.exists():
        return _read_json(_EXAMPLE)
    return []


def save_profiles(profiles: list[Profile]) -> None:
    """Persist the full profile list to data/profiles.json."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"profiles": [p.model_dump(by_alias=True) for p in profiles]}
    _PROFILES.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def find_profile(name: str) -> Profile | None:
    """Look up a profile by (case-insensitive) name — used when the cook says
    'cooking for my wife'."""
    name_low = name.strip().lower()
    for p in load_profiles():
        if p.name.strip().lower() == name_low:
            return p
    return None
