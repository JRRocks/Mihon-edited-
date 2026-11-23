"""Where a series' color sheet is kept (spec, section 3): readable JSON files, out of the repository.

    <series folder>/<title>--al<AniList id>/
      series.json                  identity, ids, sources consulted and when, state
      characters/<id>/character.json
      characters/<id>/refs/ref-NN.png   official color crops (only on the PC, never in the repository)
      journal.jsonl                one line per change of the sheet: what, where from, when

A sheet is corrected by dated additions, never rewritten: a character the owner validated is left as it is (the new
research only goes to the journal), and every value that changes is written to the journal.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def default_series_folder():
    """%USERPROFILE%\\Documents\\Mihon colorisation\\series on Windows (D7), the same under the home folder elsewhere."""
    home = Path(os.environ.get("USERPROFILE") or Path.home()) if sys.platform == "win32" else Path.home()
    return home / "Documents" / "Mihon colorisation" / "series"


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "series"


def series_key(identity):
    return f"{slug(identity['title'])}--al{identity['anilist_id']}"


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


class Sheet:

    def __init__(self, root: Path, identity):
        self.folder = Path(root) / series_key(identity)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.journal_path = self.folder / "journal.jsonl"

    def log(self, what, value, origin, character=None):
        line = {"date": now(), "what": what, "value": value, "from": origin}
        if character:
            line["character"] = character
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def write_series(self, series):
        path = self.folder / "series.json"
        old = read_json(path)
        if old and old.get("status") == "validated":
            series["status"] = "validated"
        write_json(path, series)
        if not old:
            self.log("series", series["key"], "recherche automatique")
        elif old.get("ids") != series.get("ids"):
            self.log("series.ids", series["ids"], "recherche automatique")

    def character_folder(self, character_id):
        return self.folder / "characters" / character_id

    def write_character(self, character):
        """Writes a character unless the owner validated it; logs every value that changed."""
        path = self.character_folder(character["id"]) / "character.json"
        old = read_json(path)
        origin = "recherche automatique"
        if old and old.get("status") == "validated":
            self.log("proposal", _summary(character), origin + " (fiche validée gardée telle quelle)",
                     character["id"])
            return False
        before, after = _summary(old or {}), _summary(character)
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                self.log(key, after.get(key), origin + _sources(character, key), character["id"])
        write_json(path, character)
        return True


def _summary(character):
    """Flat view of the values worth a journal line: each part's tones, the outfits, the state."""
    flat = {}
    for part, entry in (character.get("parts") or {}).items():
        if entry:
            flat[f"parts.{part}"] = [entry.get("base"), entry.get("shadow"), entry.get("highlight")]
    for outfit in character.get("outfits") or []:
        for part, entry in outfit.get("parts", {}).items():
            flat[f"outfits.{outfit['id']}.{part}"] = [entry.get("base"), entry.get("shadow"), entry.get("highlight")]
    if character.get("outfit_note"):
        flat["outfit_note"] = character["outfit_note"]
    if character.get("status"):
        flat["status"] = character["status"]
    return flat


def _sources(character, key):
    if not key.startswith("parts."):
        return ""
    entry = character["parts"].get(key.split(".", 1)[1]) or {}
    if not entry.get("sources"):
        return ""
    return f", {entry.get('images')} image(s) sur {entry.get('of')} : " + ", ".join(entry["sources"])
