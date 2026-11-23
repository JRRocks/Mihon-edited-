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
# Tones of several images closer than this form one group (printing and lighting differ between volumes)
GROUP_RADIUS = 0.12
# An outfit is kept when its color holds at least this share of the images showing the part
OUTFIT_DOMINANCE = 0.6
# Danbooru color tags under this share of the character's pictures are noise
DANBOORU_FLOOR = 0.15

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
    """Same color for the sheet: close in OKLab, or the same (or neighboring) name and not too far apart (covers are
    printed and lit differently from one volume to the next)."""
    d = measure.delta_e(x, y)
    return d < SAME_COLOR or (d < 0.20 and words_agree(part, word_of(part, x), word_of(part, y)))


def confidence(agreeing, total):
    """Share of the images that agree, discounted when they are few: 1 image -> at most 0.5, 2 -> 0.75, 3 -> 0.88."""
    return round(agreeing / total * (1 - 0.5 ** agreeing), 2) if total else 0.0


def _tone(values):
    values = [v for v in values if v is not None]
    return np.median(np.asarray(values), axis=0) if values else None


def _entry(part, members, total, kind):
    """A sheet entry from the observations that agree, one per image (median of each tone)."""
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


def _images(observations):
    return len({o["ref"] for o in observations})


def _groups(observations):
    """Groups of close tones over the images, the most images first; an image counts once in a group.

    An image may bring several candidate tones (hair and hat): each is weighted by its share of the part.
    """
    if not observations:
        return []
    raw = measure.densest_groups([o["lab"] for o in observations], [o.get("weight", 1.0) for o in observations],
                                 radius=GROUP_RADIUS, max_groups=5)
    groups = []
    for g in raw:
        best = {}
        for i in g["members"]:
            o = observations[i]
            if o["ref"] not in best or o.get("weight", 1.0) > best[o["ref"]].get("weight", 1.0):
                best[o["ref"]] = o
        members = list(best.values())
        groups.append({"members": members, "weight": sum(o.get("weight", 1.0) for o in members),
                       "value": np.median(np.asarray([o["lab"] for o in members]), axis=0)})
    groups.sort(key=lambda g: (-len(g["members"]), -g["weight"]))
    return groups


def _choose(part, groups, words, name, doubts):
    """The densest group, unless it contradicts the control words and the next one agrees with them: the area of a
    part sometimes holds something else (a hat over the hair, the background around it)."""
    chosen = groups[0]
    if len(groups) < 2:
        return chosen
    first, second = word_of(part, groups[0]["value"]), word_of(part, groups[1]["value"])
    if words and not agrees_with_words(part, first, words) and agrees_with_main_words(part, second, words):
        doubts.append(f"{name} : deux couleurs dans la zone mesurée ({fr(first)} sur {len(groups[0]['members'])} "
                      f"image(s), {fr(second)} sur {len(groups[1]['members'])}), sans doute un chapeau ou le fond ; "
                      f"{fr(second)} retenu parce que les mots de contrôle le confirment.")
        return groups[1]
    if (len(groups[1]["members"]) >= max(2, 0.6 * len(groups[0]["members"]))
            and not words_agree(part, first, second)):
        other = groups[1]
        chosen = dict(chosen, variant={"base": measure.oklab_to_hex(other["value"]), "images": len(other["members"])})
        doubts.append(f"{name} : deux couleurs stables ({fr(first)} sur {len(groups[0]['members'])} images, "
                      f"{fr(second)} sur {len(other['members'])}).")
    return chosen


def settle_part(part, observations, words=None):
    """One locked part (hair, eyes, skin) from its measures on every image. Returns (entry or None, doubts).

    Covers come first (D3): their densest group needs two images. Otherwise every image counts; a color resting on
    a single image is a doubt, and so are covers and the AniList picture that disagree. `words` (control words) only
    break a tie between the two densest groups, and that choice is itself reported as a doubt.
    """
    name = FR_PART[part].capitalize()
    if not observations:
        return None, []
    doubts = []
    covers = [o for o in observations if o["kind"] == "volume_cover"]
    anime = [o for o in observations if o["kind"] == "anime"]
    if _images(covers) >= 2:
        groups = [g for g in _groups(covers) if len(g["members"]) >= 2]
        if groups:
            chosen = _choose(part, groups, words, name, doubts)
            entry, value = _entry(part, chosen["members"], _images(covers), "volume_cover")
            if "variant" in chosen:
                entry["variant"] = chosen["variant"]
            for ref in sorted({o["ref"] for o in anime}):
                tones = [o["lab"] for o in anime if o["ref"] == ref]
                if not any(colors_agree(part, t, value) for t in tones):
                    doubts.append(f"{name} : les couvertures ({fr(entry['word'])}) et l'image AniList "
                                  f"({fr(word_of(part, tones[0]))}) ne s'accordent pas.")
            return entry, doubts
    total = _images(observations)
    groups = [g for g in _groups(observations) if len(g["members"]) >= 2]
    if groups:
        chosen = _choose(part, groups, words, name, doubts)
        kind = min((o["kind"] for o in chosen["members"]), key=lambda k: KIND_RANK.get(k, 9))
        entry, _ = _entry(part, chosen["members"], total, kind)
        return entry, doubts
    # No two images agree: the best-ranked image, and among its tones the one the control words confirm, if any
    ranked = sorted(observations, key=lambda o: (KIND_RANK.get(o["kind"], 9), -o.get("weight", 1.0)))
    own = [o for o in ranked if o["ref"] == ranked[0]["ref"]]
    confirmed = [o for o in own if words and agrees_with_main_words(part, word_of(part, o["lab"]), words)]
    best = (confirmed or own)[0]
    entry, _ = _entry(part, [best], total, best["kind"])
    picked = " (parmi ses tons, celui que confirment les mots de contrôle)" if confirmed and best is not own[0] else ""
    if total == 1:
        doubts.append(f"{name} : la couleur ne repose que sur une image ({FR_KIND.get(best['kind'], best['kind'])})"
                      f"{picked}.")
    else:
        doubts.append(f"{name} : les {total} images ne s'accordent pas ; la couleur retenue vient d'une seule "
                      f"({FR_KIND.get(best['kind'], best['kind'])}){picked}.")
    return entry, doubts


def control_words(part, words):
    """The control words that count: Danbooru tags frequent enough, and the wiki's words."""
    danbooru = list((words or {}).get("danbooru") or [])
    if danbooru:
        # Tags of the characters drawn next to this one ride along: keep the words close to the most frequent one
        floor = max(DANBOORU_FLOOR, 0.5 * max(f for _, f in danbooru))
        danbooru = [(w, f) for w, f in danbooru if f >= floor]
    wiki = list((words or {}).get("wiki") or [])
    if part == "skin":
        wiki = [(w, c) for w, c in wiki if w in {"pale", "light", "tan", "dark", "fair", "blue", "green", "red", "grey",
                                                 "purple", "pink"}]
    return danbooru, wiki


def agrees_with_words(part, word, words):
    danbooru, wiki = control_words(part, words)
    return any(words_agree(part, word, w) for w, _ in danbooru + wiki)


def agrees_with_main_words(part, word, words):
    """Agrees with the main control word of each source (Danbooru's most frequent tag, the wiki's most frequent
    word): only those may choose between two measures, the weaker tags often belong to other characters."""
    danbooru, wiki = control_words(part, words)
    return any(words_agree(part, word, w) for w, _ in danbooru[:1] + wiki[:1])


def check_words(part, entry, words):
    """Compares the measured color name with the control words. Returns (verdict, doubt or None).

    words: {"danbooru": [(word, frequency)], "wiki": [(word, count)]}. Danbooru tags under 15 % of the character's
    pictures, or under half the most frequent color, come from the characters drawn next to this one (Luffy's
    pictures are 67 % "black hair" and 24 % "orange hair", Nami's); a contradiction needs a clear control word.
    """
    measured = entry["word"]
    danbooru, wiki = control_words(part, words)
    if part == "skin":
        natural = {"pale", "light", "tan", "dark"}
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
        groups = measure.densest_groups([o["lab"] for o in obs], radius=GROUP_RADIUS, max_groups=4)
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
