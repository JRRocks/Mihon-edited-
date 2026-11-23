"""Turning measurements into sheet entries, and the doubt rules (D14). Pure functions.

A character goes to `to_review`, with the reason written out for the owner, when a color rests on a single image,
when two sources contradict each other (measure against control words, covers against the anime picture), when no
color image was found, or when the series identity isn't cross-checked by two databases. The rest passes without a
question. Outfits change with the arcs: one is kept only when it clearly dominates the covers, otherwise the sheet
says "varies with the arc" (handled later, task 8 of the plan).
"""
import numpy as np

from . import measure

LOCKED_PARTS = ("hair", "eyes", "skin")
OUTFIT_PARTS = ("top", "bottom")
# Order of trust of the sources (D3): lower is more trusted
KIND_RANK = {"user": 0, "manga_color_page": 1, "volume_cover": 2, "anime": 3}
# Two measures of the same part closer than this (OKLab) are the same color
SAME_COLOR = 0.08
# An outfit is kept when its color holds at least this share of the images showing the part
OUTFIT_DOMINANCE = 0.6

FR_PART = {"hair": "cheveux", "eyes": "yeux", "skin": "peau", "top": "haut", "bottom": "bas"}
FR_COLOR = {"black": "noir", "grey": "gris", "white": "blanc", "brown": "brun", "blonde": "blond", "yellow": "jaune",
            "orange": "orange", "red": "rouge", "pink": "rose", "purple": "violet", "blue": "bleu",
            "aqua": "bleu-vert", "green": "vert", "silver": "argent", "pale": "très claire", "light": "claire",
            "tan": "hâlée", "dark": "foncée", "colored": "colorée"}
FR_KIND = {"volume_cover": "couverture", "anime": "image AniList", "manga_color_page": "page couleur",
           "user": "correction"}


def fr(word):
    return FR_COLOR.get(word, word)


def word_of(part, lab):
    return measure.skin_word(lab) if part == "skin" else measure.color_word(lab, part)


_SKIN_NEIGHBORS = {frozenset(p) for p in [("pale", "light"), ("light", "tan"), ("tan", "dark"), ("light", "fair"),
                                          ("pale", "fair")]}


def words_agree(part, a, b):
    if part != "skin":
        return measure.words_agree(a, b)
    natural = {"pale", "light", "tan", "dark", "fair"}
    if a == b or frozenset((a, b)) in _SKIN_NEIGHBORS:
        return True
    # "colored" (Danbooru's colored_skin) goes with any skin color that isn't a natural tone
    return "colored" in (a, b) and not ({a, b} - {"colored"}) <= natural


def colors_agree(part, x, y):
    """Same color for the sheet: close in OKLab, or the same (or neighboring) name and not far apart."""
    d = measure.delta_e(x, y)
    return d < SAME_COLOR or (d < 0.15 and words_agree(part, word_of(part, x), word_of(part, y)))


def confidence(agreeing, total):
    """Share of the images that agree, discounted when they are few: 1 image -> at most 0.5, 2 -> 0.75, 3 -> 0.88."""
    return round(agreeing / total * (1 - 0.5 ** agreeing), 2) if total else 0.0


def _tone(values):
    values = [v for v in values if v is not None]
    return np.median(np.asarray(values), axis=0) if values else None


def _entry(part, members, total, kind):
    """A sheet entry from the observations that agree (median of each tone)."""
    value = np.median(np.asarray([o["lab"] for o in members]), axis=0)
    closest = min(members, key=lambda o: measure.delta_e(o["lab"], value))
    entry = {"base": measure.oklab_to_hex(value)}
    for tone in ("shadow", "highlight"):
        t = _tone([o.get(tone) for o in members])
        if t is not None:
            entry[tone] = measure.oklab_to_hex(t)
    entry.update({
        "word": word_of(part, value), "source": closest["ref"], "sources": [o["ref"] for o in members],
        "kind": kind, "images": len(members), "of": total, "confidence": confidence(len(members), total),
    })
    return entry, value


def settle_part(part, observations):
    """One locked part (hair, eyes, skin) from its measures on every image. Returns (entry or None, doubts).

    Covers come first (D3). Their densest group needs two images; a single cover or the AniList picture alone gives a
    color resting on one image, which is a doubt. Covers and the AniList picture that disagree are a doubt too.
    """
    name = FR_PART[part].capitalize()
    if not observations:
        return None, []
    doubts = []
    covers = [o for o in observations if o["kind"] == "volume_cover"]
    anime = [o for o in observations if o["kind"] == "anime"]
    if len(covers) >= 2:
        groups = measure.densest_groups([o["lab"] for o in covers], radius=SAME_COLOR)
        top = groups[0]
        if len(top["members"]) >= 2:
            members = [covers[i] for i in top["members"]]
            entry, value = _entry(part, members, len(covers), "volume_cover")
            if len(groups) > 1 and len(groups[1]["members"]) >= max(2, 0.6 * len(top["members"])):
                other = np.median(np.asarray([covers[i]["lab"] for i in groups[1]["members"]]), axis=0)
                entry["variant"] = {"base": measure.oklab_to_hex(other), "images": len(groups[1]["members"])}
                doubts.append(f"{name} : deux couleurs stables sur les couvertures ({fr(entry['word'])} sur "
                              f"{len(top['members'])} images, {fr(word_of(part, other))} sur "
                              f"{len(groups[1]['members'])}).")
            for o in anime:
                if not colors_agree(part, o["lab"], value):
                    doubts.append(f"{name} : les couvertures ({fr(entry['word'])}) et l'image AniList "
                                  f"({fr(word_of(part, o['lab']))}) ne s'accordent pas.")
            return entry, doubts
    # Fewer than two covers agree: every image counts, and the best-ranked one wins
    groups = measure.densest_groups([o["lab"] for o in observations], radius=SAME_COLOR)
    top = groups[0]
    members = [observations[i] for i in top["members"]]
    if len(members) >= 2 and all(colors_agree(part, a["lab"], b["lab"]) for a in members for b in members):
        kind = min((o["kind"] for o in members), key=lambda k: KIND_RANK.get(k, 9))
        entry, _ = _entry(part, members, len(observations), kind)
        return entry, doubts
    best = min(observations, key=lambda o: KIND_RANK.get(o["kind"], 9))
    entry, _ = _entry(part, [best], len(observations), best["kind"])
    if len(observations) == 1:
        doubts.append(f"{name} : la couleur ne repose que sur une image ({FR_KIND.get(best['kind'], best['kind'])}).")
    else:
        doubts.append(f"{name} : les {len(observations)} images ne s'accordent pas ; la couleur retenue vient "
                      f"d'une seule ({FR_KIND.get(best['kind'], best['kind'])}).")
    return entry, doubts


def check_words(part, entry, words):
    """Compares the measured color name with the control words. Returns (verdict, doubt or None).

    words: {"danbooru": [(word, frequency)], "wiki": [(word, count)]}. Danbooru tags under 15 % of the character's
    pictures are noise (characters drawn next to them); a contradiction needs a clear control word.
    """
    measured = entry["word"]
    danbooru = [(w, f) for w, f in words.get("danbooru") or [] if f >= 0.15]
    wiki = list(words.get("wiki") or [])
    if part == "skin":
        natural = {"pale", "light", "tan", "dark"}
        wiki = [(w, c) for w, c in wiki if w in natural | {"fair", "blue", "green", "red", "grey", "purple", "pink"}]
        # Danbooru only tags unusual skins: no tag at all agrees with an ordinary skin tone
        if not danbooru and not wiki and measured in natural:
            return "accord", None
    if not danbooru and not wiki:
        return "sans mot de contrôle", None
    agree = [w for w, _ in danbooru + wiki if words_agree(part, measured, w)]
    if agree:
        return "accord", None
    clear = (danbooru and danbooru[0][1] >= 0.3) or wiki
    if not clear:
        return "mots trop faibles", None
    said = []
    if danbooru:
        said.append("Danbooru dit surtout " + ", ".join(f"« {fr(w)} » ({round(f * 100)} %)" for w, f in danbooru[:2]))
    if wiki:
        said.append("le wiki dit " + ", ".join(f"« {fr(w)} »" for w, _ in wiki[:2]))
    return "désaccord", (f"{FR_PART[part].capitalize()} : mesure « {fr(measured)} » ; " + " ; ".join(said) + ".")


def settle_outfit(observations_by_part):
    """Top and bottom colors: kept when one color dominates the images, else "varies with the arc".

    Returns (outfits, note, groups_by_part) where groups list every stable color with the volumes it was seen on.
    """
    kept, groups_by_part = {}, {}
    for part in OUTFIT_PARTS:
        obs = observations_by_part.get(part) or []
        if not obs:
            continue
        groups = measure.densest_groups([o["lab"] for o in obs], radius=SAME_COLOR, max_groups=4)
        groups_by_part[part] = [{
            "base": measure.oklab_to_hex(g["value"]), "word": measure.color_word(g["value"], part),
            "images": len(g["members"]),
            "volumes": sorted({obs[i].get("volume") for i in g["members"] if obs[i].get("volume")}, key=_volume_key),
            "anime": any(obs[i]["kind"] == "anime" for i in g["members"]),
        } for g in groups]
        top = groups[0]
        if len(top["members"]) >= 2 and len(top["members"]) / len(obs) >= OUTFIT_DOMINANCE:
            members = [obs[i] for i in top["members"]]
            entry, _ = _entry(part, members, len(obs), min((o["kind"] for o in members),
                                                           key=lambda k: KIND_RANK.get(k, 9)))
            kept[part] = entry
    if kept:
        outfits = [{"id": "default", "name": "tenue courante", "chapters": None, "parts": kept}]
    else:
        outfits = []
    missing = [p for p in OUTFIT_PARTS if p in groups_by_part and p not in kept]
    note = "varie selon l'arc" if missing else None
    return outfits, note, groups_by_part


def _volume_key(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 1e9


def character_status(doubts):
    return "to_review" if doubts else "automatic"


def series_doubts(identity):
    """Doubts that hold for every character of the series (D14: identity not cross-checked by two databases)."""
    checks = [c for c in identity.get("checks", []) if c.get("anilist_id") == identity.get("anilist_id")]
    if len(checks) < 2:
        found = ", ".join(c["base"] for c in checks) or "aucune"
        return [f"Identité de la série non recoupée par deux bases (trouvée seulement par AniList et : {found})."]
    if not any(c.get("same_author") for c in checks):
        return ["Identité de la série : l'auteur diffère d'une base à l'autre."]
    return []


def no_image_doubt(observations):
    if not any(observations.values()):
        return ["Aucune image en couleur trouvée pour ce personnage."]
    return []
