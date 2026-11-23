"""The research of a series' color sheet, end to end (task 2 of docs/PLAN.md, spec sections 2 to 4).

1. identity of the series on AniList, cross-checked on MangaBaka and MangaDex;
2. main characters (AniList, role MAIN) and their control words (Danbooru tags, the series' wiki);
3. official color images: each character's AniList picture and a sample of the Japanese volume covers (MangaDex);
   black and white images are dropped;
4. every head on the covers is matched to a character (CCIP), one character per crop;
5. the parts of each matched character are found (See-through, or rough regions) and measured (OKLab, most frequent
   tone, base / shadow / highlight), then settled over the images (densest group) with the doubt rules (D14);
6. the sheet is written as section 3 of the spec describes.
No color is asked of an AI (D2): every number comes from pixels of an official image.
"""
import os
import time
import traceback
from datetime import date

import cv2
import numpy as np

from . import measure, rules, sources, store, vision
from .net import Http

PARTS = ("hair", "eyes", "skin", "top", "bottom")
# Cover crops measured per character (the best matches, whole bodies first)
MAX_CROPS = 8


def even_sample(items, n):
    """n items spread evenly over the list (first and last included)."""
    if len(items) <= n:
        return list(items)
    idx = np.unique(np.round(np.linspace(0, len(items) - 1, n)).astype(int))
    return [items[i] for i in idx]


def crop(rgb, box):
    x0, y0, x1, y1 = box
    return rgb[y0:y1, x0:x1].copy()


def shift(box, origin):
    if box is None:
        return None
    return [box[0] - origin[0], box[1] - origin[1], box[2] - origin[0], box[3] - origin[1]]


class Research:

    def __init__(self, title, out, work, models, covers=30, anilist_id=None, use_parts_model=True, save_refs=True,
                 log=print):
        self.title, self.out, self.models = title, out, models
        self.covers_wanted, self.anilist_id = covers, anilist_id
        self.use_parts_model, self.save_refs, self.log = use_parts_model, save_refs, log
        self.http = Http(work)
        self.stages = {}
        self.notes = []

    def stage(self, name, start):
        self.stages[name] = round(time.time() - start, 1)
        self.log(f"  ({self.stages[name]} s)")

    # --- 1 and 2: identity, characters, control words ------------------------------------------------------------

    def find_series(self):
        start = time.time()
        self.log(f"Series: {self.title}")
        self.identity = sources.identify(self.http, self.title, self.anilist_id)
        ident = self.identity
        self.log(f"  AniList {ident['anilist_id']} ({ident['title']}, {', '.join(ident['authors'])}); "
                 f"confirmed by {', '.join(c['base'] for c in ident['checks']) or 'nothing'}")
        self.characters = [c for c in sources.anilist_main_characters(self.http, ident["anilist_id"])
                           if c["role"] == "MAIN"]
        self.log(f"  {len(self.characters)} main characters: "
                 + ", ".join(c["name"]["full"] for c in self.characters))
        self.find_words()
        self.stage("identité et mots de contrôle", start)

    def find_words(self):
        http = self.http
        try:
            series_tag = sources.danbooru_series_tag(http, self.identity)
        except Exception as e:
            series_tag = None
            self.notes.append(f"Danbooru injoignable ({e.__class__.__name__}) : pas de mots Danbooru.")
        self.danbooru_series = series_tag
        host = sources.wiki_host(self.identity)
        pages = {}
        try:
            for c in self.characters:
                pages[c["id"]] = sources.wiki_page(http, host, c)
        except Exception as e:
            pages = {}
            self.notes.append(f"Wiki {host} injoignable ({e.__class__.__name__}) : pas de mots du wiki.")
        # A homonym's wiki would lack the main characters: half of them must have their page (spec, section 4)
        found = [p for p in pages.values() if p]
        self.wiki = host if pages and len(found) >= len(self.characters) / 2 else None
        if pages and not self.wiki:
            self.notes.append(f"Wiki {host} écarté : trop peu de personnages principaux y ont leur page.")
        for c in self.characters:
            c["words"] = {"hair": {}, "eyes": {}, "skin": {}}
            c["danbooru"] = None
            if series_tag:
                try:
                    c["danbooru"] = sources.danbooru_character(http, c, series_tag)
                    if c["danbooru"]:
                        for part, words in sources.danbooru_words(http, c["danbooru"]["tag"]).items():
                            c["words"][part]["danbooru"] = words
                except Exception as e:
                    self.notes.append(f"Danbooru, {c['name']['full']} : {e.__class__.__name__}.")
            c["wiki_page"] = pages.get(c["id"]) if self.wiki else None
            if c["wiki_page"]:
                try:
                    found_words = sources.wiki_words(http, self.wiki, c["wiki_page"]) or {}
                    for part, words in found_words.items():
                        c["words"][part]["wiki"] = words
                except Exception as e:
                    self.notes.append(f"Wiki, {c['name']['full']} : {e.__class__.__name__}.")
            tag = c["danbooru"]["tag"] if c["danbooru"] else "—"
            self.log(f"  {c['name']['full']}: danbooru {tag}, wiki {c['wiki_page'] or '—'}")

    # --- 3: images -------------------------------------------------------------------------------------------------

    def gather_images(self):
        start = time.time()
        self.bw_dropped = []
        for c in self.characters:
            url = (c.get("image") or {}).get("large")
            c["picture"] = None
            if not url or url.endswith("/default.jpg"):
                continue
            path = self.http.file(url)
            rgb = vision.load_rgb(path)
            alpha = vision.alpha_mask(path)
            if not measure.is_color_image(rgb, alpha):
                self.bw_dropped.append(url)
                continue
            c["picture"] = {"url": url, "rgb": rgb, "alpha": alpha}
        all_covers = sources.mangadex_covers(self.http, self.identity["mangadex_id"]) \
            if self.identity.get("mangadex_id") else []
        self.covers_total = len(all_covers)
        self.covers = []
        for cover in even_sample(all_covers, self.covers_wanted):
            rgb = vision.load_rgb(self.http.file(cover["url"]), max_side=2700)
            if not measure.is_color_image(rgb):
                self.bw_dropped.append(cover["url"])
                continue
            self.covers.append(dict(cover, rgb=rgb))
        self.log(f"Images: {sum(1 for c in self.characters if c['picture'])} AniList pictures, "
                 f"{len(self.covers)} covers out of {self.covers_total} (black and white dropped: "
                 f"{len(self.bw_dropped)})")
        self.stage("téléchargement des images", start)

    # --- 4: who is on the covers --------------------------------------------------------------------------------

    def match_characters(self):
        start = time.time()
        det = vision.Detectors(self.models)
        self.detectors = det
        self.instances = []
        for ci, cover in enumerate(self.covers):
            rgb = cover["rgb"]
            persons = det.person.detect(rgb)
            heads = det.head.detect(rgb)
            for inst in vision.cover_instances(persons, heads, rgb.shape):
                inst["cover"] = ci
                self.instances.append(inst)
        refs = [c for c in self.characters if c["picture"]]
        self.log(f"Matching: {len(self.instances)} heads on {len(self.covers)} covers, "
                 f"{len(refs)} official pictures")
        if not self.instances or not refs:
            for inst in self.instances:
                inst["character"] = None
            self.stage("reconnaissance des personnages", start)
            return
        head_crops, body_crops, body_of = [], [], []
        for inst in self.instances:
            rgb = self.covers[inst["cover"]]["rgb"]
            head_crops.append(crop(rgb, vision.identity_box(inst["head"], rgb.shape)))
            if inst["body"]:
                body_of.append(len(body_crops))
                body_crops.append(crop(rgb, inst["body"]))
            else:
                body_of.append(None)
        ref_feat = det.ccip.features([c["picture"]["rgb"] for c in refs])
        head_feat = det.ccip.features(head_crops)
        body_feat = det.ccip.features(body_crops) if body_crops else np.zeros((0, ref_feat.shape[1]), np.float32)
        feats = np.concatenate([ref_feat, head_feat, body_feat])
        diff = det.ccip.differences(feats)
        r, n = len(refs), len(self.instances)
        head_ref = diff[r:r + n, :r]
        head_head = diff[r:r + n, r:r + n]
        ref_diff = head_ref.copy()
        crop_diff = head_head.copy()
        b0 = r + n
        for i, bi in enumerate(body_of):
            if bi is not None:
                ref_diff[i] = np.minimum(ref_diff[i], diff[b0 + bi, :r])
                crop_diff[i] = np.minimum(crop_diff[i], diff[b0 + bi, r:r + n])
                crop_diff[:, i] = np.minimum(crop_diff[:, i], diff[r:r + n, b0 + bi])
        for i, bi in enumerate(body_of):
            for j, bj in enumerate(body_of):
                if bi is not None and bj is not None:
                    crop_diff[i, j] = min(crop_diff[i, j], diff[b0 + bi, b0 + bj])
        result = vision.assign(ref_diff, crop_diff, [inst["cover"] for inst in self.instances])
        for i, (k, how) in enumerate(result):
            inst = self.instances[i]
            inst["character"] = refs[k]["id"] if k is not None else None
            inst["match"] = how
            order = np.argsort(ref_diff[i])
            inst["nearest"] = [(refs[j]["id"], round(float(ref_diff[i, j]), 3)) for j in order[:2]]
        for c in self.characters:
            mine = [inst for inst in self.instances if inst.get("character") == c["id"]]
            self.log(f"  {c['name']['full']}: {len(mine)} crop(s) on covers "
                     + ", ".join(f"vol. {self.covers[m['cover']]['volume']}" for m in mine))
        self.stage("reconnaissance des personnages", start)

    # --- 5: parts and colors ------------------------------------------------------------------------------------

    def load_parts_model(self):
        self.parts_model = None
        self.parts_method = "regions"
        if not self.use_parts_model:
            self.notes.append("Découpage des parties par régions (modèle See-through désactivé).")
            return
        try:
            from .parts import PartsModel

            self.parts_model = PartsModel(self.models, threads=os.cpu_count())
            self.parts_method = "see-through"
        except Exception as e:
            traceback.print_exc()
            self.notes.append(f"Modèle See-through indisponible ({e.__class__.__name__}) : repli par régions.")

    def part_masks(self, rgb, head, body, restrict):
        """Checked masks of hair, eyes, skin, top and bottom for the character whose head is `head` in `rgb`."""
        from . import parts

        if self.parts_model is not None:
            try:
                return parts.checked_parts(self.parts_model.parse(rgb), head, body, restrict), "see-through"
            except Exception as e:
                self.notes.append(f"See-through a échoué sur une image ({e.__class__.__name__}) : repli par régions.")
        return (parts.region_parts(rgb, head, body), []), "regions"

    def measure_characters(self):
        start = time.time()
        self.load_parts_model()
        today = date.today().isoformat()
        for c in self.characters:
            cid = f"al-{c['id']}"
            c["sheet_id"] = cid
            observations = {p: [] for p in PARTS}
            refs = []
            images = []
            if c["picture"]:
                rgb = c["picture"]["rgb"]
                heads = self.detectors.head.detect(rgb)
                head = max(heads, key=lambda h: h[4])[:4] if heads else [0, 0, rgb.shape[1], rgb.shape[0] // 2]
                images.append({"ref": {"kind": "anime", "origin": "anilist", "url": c["picture"]["url"],
                                       "page": c.get("siteUrl"), "box": None},
                               "rgb": rgb, "head": [int(v) for v in head], "body": None, "restrict": False,
                               "alpha": c["picture"]["alpha"]})
            mine = [inst for inst in self.instances if inst.get("character") == c["id"]]
            mine.sort(key=lambda m: (m["body"] is None, dict(m["nearest"]).get(c["id"], 1)))
            for inst in mine[:MAX_CROPS]:
                cover = self.covers[inst["cover"]]
                box = vision.parse_box(inst, cover["rgb"].shape)
                images.append({"ref": {"kind": "volume_cover", "origin": "mangadex", "volume": cover["volume"],
                                       "url": cover["url"], "thumbnail": cover["small"], "box": box,
                                       "head": inst["head"], "body": inst["body"], "match": inst["match"]},
                               "rgb": crop(cover["rgb"], box), "head": shift(inst["head"], box),
                               "body": shift(inst["body"], box), "restrict": True, "alpha": None})
            for n, image in enumerate(images, 1):
                ref = dict(image["ref"], id=f"ref-{n:02d}", added=today)
                (masks, problems), method = self.part_masks(image["rgb"], image["head"], image["body"],
                                                            image["restrict"])
                ref["parts_method"] = method
                if problems:
                    ref["parts_problems"] = problems
                measured = {}
                skin = None
                # Skin first: its tone is left out of the other parts (eyelids, bare arms, forehead)
                for part in ("skin", "hair", "eyes", "top", "bottom"):
                    mask = masks[part]
                    if image["alpha"] is not None:
                        mask = mask & image["alpha"]
                    found = measure.measure_part(image["rgb"], mask, part, None if part == "skin" else skin,
                                                 candidates=part == "hair")
                    if found is None:
                        continue
                    # Hair: its main tones are all kept (a hat often shares the area), the choice is made over the
                    # images; the other parts: the most frequent tone
                    for tones in found if part == "hair" else [found]:
                        observations[part].append({"lab": tones["base"], "shadow": tones["shadow"],
                                                   "highlight": tones["highlight"], "ref": ref["id"],
                                                   "kind": ref["kind"], "volume": ref.get("volume"),
                                                   "weight": tones["share"]})
                    if part == "skin":
                        skin = found["base"]
                    first = found[0] if part == "hair" else found
                    measured[part] = measure.oklab_to_hex(first["base"])
                    if part == "hair" and len(found) > 1:
                        measured["hair_candidates"] = [measure.oklab_to_hex(t["base"]) for t in found]
                ref["measured"] = measured
                refs.append(ref)
                if self.save_refs:
                    path = self.sheet.character_folder(cid) / "refs" / f"{ref['id']}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(path), cv2.cvtColor(image["rgb"], cv2.COLOR_RGB2BGR))
            c["observations"] = observations
            c["refs"] = refs
            self.log(f"  {c['name']['full']}: {len(refs)} image(s) measured")
        self.stage("découpage et mesure des couleurs", start)

    # --- 6: the sheet --------------------------------------------------------------------------------------------

    def settle(self, c):
        doubts = list(self.series_doubts)
        if not c["refs"]:
            doubts += rules.no_image_doubt(c["observations"])
        elif not any(c["observations"][p] for p in rules.LOCKED_PARTS):
            doubts.append("Aucune couleur de cheveux, d'yeux ni de peau n'a pu être mesurée : le découpage n'a pas "
                          "trouvé de visage sur les images de ce personnage.")
        parts, missing = {}, []
        for part in rules.LOCKED_PARTS:
            words = c["words"].get(part) or {}
            entry, part_doubts = rules.settle_part(part, c["observations"][part], words)
            if entry is None:
                missing.append(part)
                continue
            verdict, word_doubt = rules.check_words(part, entry, words)
            entry["control"] = {"verdict": verdict,
                                "danbooru": [[w, round(f, 2)] for w, f in (words.get("danbooru") or [])[:4]],
                                "wiki": [[w, n] for w, n in (words.get("wiki") or [])[:4]]}
            entry["locked"] = True
            entry["measures"] = [{"ref": o["ref"], "base": measure.oklab_to_hex(o["lab"]),
                                  "word": rules.word_of(part, o["lab"]), "share": round(o.get("weight", 1.0), 2)}
                                 for o in c["observations"][part]]
            parts[part] = entry
            doubts += part_doubts + ([word_doubt] if word_doubt else [])
        outfits, note, groups = rules.settle_outfit({p: c["observations"][p] for p in rules.OUTFIT_PARTS})
        name = c["name"]
        return {
            "id": c["sheet_id"],
            "anilist_id": c["id"],
            "names": {"main": " ".join(filter(None, [name.get("last"), name.get("middle"), name.get("first")]))
                      or name["full"], "anilist": name["full"], "native": name.get("native"),
                      "aliases": name.get("alternative") or []},
            "role": "main",
            "status": rules.character_status(doubts),
            "doubts": doubts,
            "parts": parts,
            "not_measured": missing,
            "outfits": outfits,
            "outfit_note": note,
            "outfit_colors": groups,
            "words": {"danbooru_tag": (c["danbooru"] or {}).get("tag"), "wiki_page": c.get("wiki_page"),
                      "wiki": self.wiki,
                      "hair": c["words"].get("hair"), "eyes": c["words"].get("eyes"), "skin": c["words"].get("skin")},
            "refs": c["refs"],
            "updated": store.now(),
        }

    def run(self):
        t0 = time.time()
        self.find_series()
        self.sheet = store.Sheet(self.out, self.identity)
        self.gather_images()
        self.match_characters()
        self.measure_characters()
        start = time.time()
        self.series_doubts = rules.series_doubts(self.identity)
        characters = [self.settle(c) for c in self.characters]
        used = {r["url"] for ch in characters for r in ch["refs"] if r.get("measured")}
        ident = self.identity
        series = {
            "key": store.series_key(ident),
            "title": ident["title"], "titles": ident["titles"], "synonyms": ident["synonyms"],
            "authors": ident["authors"], "year": ident["year"], "has_anime": ident["has_anime"],
            "ids": {"anilist": ident["anilist_id"], "myanimelist": ident["mal_id"],
                    "mangadex": ident.get("mangadex_id"), "mangabaka": ident.get("mangabaka_id"),
                    "mangaupdates": (ident.get("mangadex_links") or {}).get("mu"),
                    "kitsu": (ident.get("mangadex_links") or {}).get("kt")},
            "identity": {"crosschecked": not self.series_doubts, "checks": ident["checks"],
                         "doubts": self.series_doubts},
            "sources": [
                {"name": "AniList", "url": ident["anilist_url"], "consulted": date.today().isoformat()},
                {"name": "MangaBaka", "url": next((c["url"] for c in ident["checks"] if c["base"] == "mangabaka"),
                                                  None), "consulted": date.today().isoformat()},
                {"name": "MangaDex", "url": next((c["url"] for c in ident["checks"] if c["base"] == "mangadex"),
                                                 None), "consulted": date.today().isoformat()},
                {"name": "Danbooru", "tag": self.danbooru_series, "consulted": date.today().isoformat()},
                {"name": "Fandom", "wiki": self.wiki, "consulted": date.today().isoformat()},
            ],
            "characters": [ch["id"] for ch in characters],
            "style": None,
            "status": "to_review" if any(ch["status"] == "to_review" for ch in characters) else "automatic",
            "research": {
                "date": store.now(), "tool": "tools/colorization-server/color_sheet.py",
                "covers": {"sampled": len(self.covers), "available": self.covers_total, "locale": "ja",
                           "volumes": [c["volume"] for c in self.covers]},
                "images_used": len(used),
                "black_and_white_dropped": self.bw_dropped,
                "heads_on_covers": len(self.instances),
                "parts_method": self.parts_method,
                "characters": len(characters),
                "to_review": sum(ch["status"] == "to_review" for ch in characters),
                "notes": self.notes,
                "models": ["deepghs/anime_person_detection person_detect_v1.3_s",
                           "deepghs/anime_head_detection head_detect_v2.0_s",
                           "deepghs/ccip_onnx ccip-caformer_b36-24",
                           "24yearsold/l2d_sam_iter2 (See-through)"],
                "requests": self.http.requests,
            },
        }
        self.sheet.write_series(series)
        for ch in characters:
            self.sheet.write_character(ch)
        self.stage("fiche", start)
        series["research"]["stages_s"] = self.stages
        series["research"]["duration_s"] = round(time.time() - t0, 1)
        store.write_json(self.sheet.folder / "series.json", series)
        self.log(f"Done in {series['research']['duration_s']} s: {self.sheet.folder}")
        return self.sheet.folder
