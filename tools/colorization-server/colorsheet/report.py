"""The page the owner reads on his phone: fiche.md, small SVG swatches and a copy of the sheet's JSON files.

Readable on GitHub. Official images are shown by their original address, never copied (D19); only measured colors,
addresses and crop boxes are written.
"""
import shutil
from pathlib import Path

from . import store

FR_PART = {"hair": "Cheveux", "eyes": "Yeux", "skin": "Peau", "top": "Haut", "bottom": "Bas"}
FR_STATUS = {"automatic": "automatique", "to_review": "à revoir", "validated": "validée",
             "provisional": "provisoire"}
FR_KIND = {"volume_cover": "couverture", "anime": "image AniList", "manga_color_page": "page couleur",
           "user": "correction"}
FR_VERDICT = {"accord": "d'accord", "désaccord": "en désaccord", "sans mot de contrôle": "aucun mot trouvé",
              "mots trop faibles": "mots trop rares pour trancher"}
FR_COLOR = {"black": "noir", "grey": "gris", "white": "blanc", "brown": "brun", "blonde": "blond", "yellow": "jaune",
            "orange": "orange", "red": "rouge", "pink": "rose", "purple": "violet", "blue": "bleu",
            "aqua": "bleu-vert", "green": "vert", "pale": "très claire", "light": "claire", "tan": "hâlée",
            "dark": "foncée", "colored": "colorée", "fair": "claire", "silver": "argent"}
FR_STAGE_ORDER = ["identité et mots de contrôle", "téléchargement des images", "reconnaissance des personnages",
                  "découpage et mesure des couleurs", "fiche"]


def fr_color(word):
    return FR_COLOR.get(word, word)


def fr_number(x, digits=2):
    return f"{x:.{digits}f}".replace(".", ",")


def duration(seconds):
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} min {s:02d} s"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min"


def swatch_svg(colors, size=22, gap=3):
    """A row of color squares with a thin gray border (readable on light and dark GitHub themes)."""
    colors = [c for c in colors if c]
    width = len(colors) * (size + gap) - gap + 2
    rects = "".join(f'<rect x="{1 + i * (size + gap)}" y="1" width="{size}" height="{size}" rx="3" fill="{c}" '
                    f'stroke="#8c8c8c" stroke-width="1"/>' for i, c in enumerate(colors))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{size + 2}" '
            f'viewBox="0 0 {width} {size + 2}">{rects}</svg>\n')


def code(hex_or_none):
    return f"`{hex_or_none}`" if hex_or_none else "—"


def source_text(entry):
    kind = FR_KIND.get(entry["kind"], entry["kind"])
    if entry["images"] == 1:
        return f"1 image ({kind})"
    return f"{entry['images']} images sur {entry['of']} ({kind}s)" if entry["kind"] == "volume_cover" \
        else f"{entry['images']} images sur {entry['of']}"


def control_text(entry):
    control = entry.get("control") or {}
    said = []
    danbooru = [(w, f) for w, f in control.get("danbooru") or [] if f >= 0.1]
    if danbooru:
        said.append("Danbooru " + ", ".join(f"{fr_color(w)} {round(f * 100)} %" for w, f in danbooru[:3]))
    if control.get("wiki"):
        said.append("wiki " + ", ".join(f"{fr_color(w)} ×{n}" for w, n in control["wiki"][:3]))
    verdict = FR_VERDICT.get(control.get("verdict"), control.get("verdict") or "")
    return f"mesure « {fr_color(entry['word'])} » : {verdict}" + (f" ({' ; '.join(said)})" if said else "")


def ref_label(ref):
    if ref["kind"] == "anime":
        return "image AniList"
    x0, y0, x1, y1 = ref["box"]
    return f"tome {ref['volume']}, cadre ({x0}, {y0}, {x1 - x0}×{y1 - y0})"


def write(series_folder: Path, report_folder: Path):
    series_folder, report_folder = Path(series_folder), Path(report_folder)
    series = store.read_json(series_folder / "series.json")
    characters = []
    for path in sorted((series_folder / "characters").glob("*/character.json")):
        characters.append(store.read_json(path))
    # AniList's order (role, then relevance), kept in series.json
    order = {cid: i for i, cid in enumerate(series.get("characters") or [])}
    characters.sort(key=lambda c: order.get(c["id"], len(order)))
    report_folder.mkdir(parents=True, exist_ok=True)
    swatches = report_folder / "pastilles"
    if swatches.exists():
        shutil.rmtree(swatches)
    swatches.mkdir()

    # Copy of the sheet's JSON files, without the reference crops
    for name in ("series.json", "journal.jsonl"):
        if (series_folder / name).exists():
            shutil.copy2(series_folder / name, report_folder / name)
    if (report_folder / "characters").exists():
        shutil.rmtree(report_folder / "characters")
    for c in characters:
        store.write_json(report_folder / "characters" / c["id"] / "character.json", c)

    research = series["research"]
    in_doubt = [c for c in characters if c["status"] == "to_review"]
    lines = []
    w = lines.append
    w(f"# Fiche couleurs : {series['title']} (essai)")
    w("")
    w(f"Recherche automatique du {research['date'][:10]}, tâche 2 du [plan](../../../../docs/PLAN.md). "
      "Aucune couleur n'a été demandée à une IA : chaque couleur est mesurée sur les pixels d'images officielles "
      "(couvertures japonaises des tomes, image AniList du personnage).")
    w("")
    covers = research["covers"]
    anilist = sum(1 for c in characters for r in c["refs"] if r["kind"] == "anime" and r.get("measured"))
    crops = sum(1 for c in characters for r in c["refs"] if r["kind"] == "volume_cover" and r.get("measured"))
    cover_files = len({r["url"] for c in characters for r in c["refs"]
                       if r["kind"] == "volume_cover" and r.get("measured")})
    w("| | |")
    w("|---|---|")
    w(f"| **Temps total** | {duration(research['duration_s'])} |")
    w(f"| **Images utilisées** | {research['images_used']} : {anilist} images AniList et {cover_files} couvertures "
      f"japonaises, où {crops} personnages ont été recadrés et mesurés ({covers['sampled']} couvertures examinées "
      f"sur {covers['available']}, {research['heads_on_covers']} têtes détectées) |")
    w(f"| **Personnages en doute** | {len(in_doubt)} sur {len(characters)} |")
    ids = series["ids"]
    checks = series["identity"]["checks"]
    if series["identity"]["crosschecked"]:
        bases = " et ".join({"mangabaka": f"MangaBaka ({c['id']})", "mangadex": "MangaDex"}.get(c["base"], c["base"])
                            for c in checks)
        identity = (f"recoupée : AniList {ids['anilist']}, {bases} désignent la même série ; "
                    f"auteur {', '.join(series['authors'])}")
    else:
        identity = "**non recoupée** : " + " ".join(series["identity"]["doubts"])
    w(f"| **Identité de la série** | {identity} |")
    w(f"| **Découpage des parties** | "
      + ("modèle See-through" if research["parts_method"] == "see-through" else "repli par régions") + " |")
    w("")
    w("Lecture : chaque partie porte trois tons, comme les fiches des coloristes d'animation : **base**, **ombre**, "
      "**reflet** (dans cet ordre sur les pastilles). La base est le ton le plus fréquent, jamais une moyenne ; sur "
      "plusieurs images, c'est le groupe de couleurs le plus nombreux qui l'emporte. **Confiance** : part des images "
      "d'accord, réduite quand elles sont peu nombreuses (1 image : 0,5 au plus ; 2 : 0,75 ; 3 : 0,88). Un personnage "
      "**automatique** sert sans question ; **à revoir** veut dire que le PC doute, pour la raison écrite.")
    w("")
    if research.get("notes"):
        w("Remarques sur la recherche :")
        w("")
        for note in research["notes"]:
            w(f"- {note}")
        w("")
    w("## Personnages")
    w("")
    for c in characters:
        mark = "⚠️ à revoir" if c["status"] == "to_review" else "✅ automatique"
        w(f"- [{c['names']['main']}](#{c['id']}) : {mark}")
    w("")
    for c in characters:
        lines.extend(character_section(c, swatches))
    w("## Fichiers")
    w("")
    w("La fiche elle-même, rangée comme le prévoit le § 3 de la [spécification]"
      "(../../../../docs/specs/colorisation-fidele.md) : [`series.json`](series.json), "
      "`characters/<id>/character.json`, [`journal.jsonl`](journal.jsonl). Les recadrages (`refs/`) restent sur "
      "la machine qui a fait la recherche : ils ne sont jamais copiés dans le dépôt.")
    w("")
    stages = research.get("stages_s") or {}
    if stages:
        w("Temps par étape : " + " ; ".join(f"{k} {duration(v)}" for k, v in stages.items()) + ".")
        w("")
    (report_folder / "fiche.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def character_section(c, swatches):
    lines = []
    w = lines.append
    names = c["names"]
    w(f'<a id="{c["id"]}"></a>')
    w("")
    w(f"## {names['main']}" + (f" · {names['native']}" if names.get("native") else ""))
    w("")
    status = FR_STATUS.get(c["status"], c["status"])
    w(f"**État : {status}**" + (" ⚠️" if c["status"] == "to_review" else " ✅"))
    w("")
    if c["doubts"]:
        w("Raisons du doute :")
        w("")
        for d in c["doubts"]:
            w(f"- {d}")
        w("")
    pictures = []
    for ref in c["refs"]:
        if ref["kind"] == "anime":
            pictures.append(f'<img src="{ref["url"]}" height="150" alt="image AniList">')
    covers = [r for r in c["refs"] if r["kind"] == "volume_cover"]
    for ref in covers[:4]:
        pictures.append(f'<img src="{ref["thumbnail"]}" height="150" alt="tome {ref["volume"]}">')
    if pictures:
        w(" ".join(pictures))
        w("")
        w("Images sources (affichées depuis leur adresse d'origine) : "
          + " ; ".join(ref_label(r) for r in c["refs"]) + ".")
        w("")
    if c["parts"]:
        w("| Partie | Pastilles | Base · ombre · reflet | Source | Confiance |")
        w("|---|---|---|---|---|")
        for part in ("hair", "eyes", "skin"):
            entry = c["parts"].get(part)
            if not entry:
                continue
            name = f"{c['id']}-{part}.svg"
            (swatches / name).write_text(swatch_svg([entry.get("base"), entry.get("shadow"), entry.get("highlight")]),
                                         encoding="utf-8")
            tones = " · ".join(code(entry.get(t)) for t in ("base", "shadow", "highlight"))
            w(f"| {FR_PART[part]} | ![{FR_PART[part]}](pastilles/{name}) | {tones} | {source_text(entry)} | "
              f"{fr_number(entry['confidence'])} |")
        w("")
        for part in ("hair", "eyes", "skin"):
            entry = c["parts"].get(part)
            if entry:
                w(f"- {FR_PART[part]} : {control_text(entry)}.")
        w("")
    if c.get("not_measured"):
        w("Non mesuré : " + ", ".join(FR_PART[p].lower() for p in c["not_measured"])
          + " (trop peu de pixels nets sur les images trouvées ; le moteur choisira).")
        w("")
    w(outfit_text(c, swatches))
    w("")
    w("<details><summary>Mesures image par image</summary>")
    w("")
    w("| Image | Cheveux | Yeux | Peau | Haut | Bas |")
    w("|---|---|---|---|---|---|")
    for ref in c["refs"]:
        m = dict(ref.get("measured") or {})
        if m.get("hair_candidates"):
            m["hair"] = " / ".join(m["hair_candidates"])
        cells = " | ".join(code(m.get(p)) for p in ("hair", "eyes", "skin", "top", "bottom"))
        how = ""
        match = ref.get("match") or {}
        if match.get("by") == "official":
            how = f" — écart {fr_number(match['difference'], 3)} avec l'image AniList"
        elif match.get("by") == "crop":
            how = f" — écart {fr_number(match['difference'], 3)} avec un autre recadrage"
        w(f"| {ref['id']} : {ref_label(ref)}{how} | {cells} |")
    w("")
    w("</details>")
    w("")
    return lines


def outfit_text(c, swatches):
    parts = []
    for outfit in c.get("outfits") or []:
        for part, entry in outfit["parts"].items():
            name = f"{c['id']}-outfit-{part}.svg"
            (swatches / name).write_text(swatch_svg([entry.get("base"), entry.get("shadow"),
                                                     entry.get("highlight")]), encoding="utf-8")
            parts.append(f"{FR_PART[part].lower()} ![{part}](pastilles/{name}) {code(entry['base'])}, "
                         f"{source_text(entry)}")
    text = "Tenue courante : " + " ; ".join(parts) + "." if parts else ""
    if c.get("outfit_note"):
        seen = []
        for part, groups in (c.get("outfit_colors") or {}).items():
            if any(part in o["parts"] for o in c.get("outfits") or []):
                continue
            pieces = []
            for g in groups[:4]:
                where = ", ".join(f"t. {v}" for v in g["volumes"][:4]) or ""
                if g.get("anime"):
                    where = (where + ", " if where else "") + "AniList"
                pieces.append(f"{fr_color(g['word'])} {code(g['base'])} ({where})")
            seen.append(f"{FR_PART[part].lower()} : " + " ; ".join(pieces))
        text += (" " if text else "") + ("Tenue : **varie selon l'arc** (traité plus tard, tâche 8). Vu : "
                                         + " / ".join(seen) + ".")
    return text or "Tenue : pas assez d'images du corps entier pour la mesurer."
