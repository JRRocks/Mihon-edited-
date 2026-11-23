"""Public databases queried by the research, without an account (spec, section 4).

- AniList (GraphQL): the series, its staff, its main characters and their picture;
- MangaBaka and MangaDex: cross-check of the series identity (both give the AniList id) and the author;
- MangaDex: the Japanese volume covers;
- Danbooru: the tags drawn with each character (hair, eyes, skin) and how often, as control words only;
- the series' Fandom wiki: the color words of each character's "Appearance" section, as control words only.
"""
import re
import urllib.parse
from collections import Counter

ANILIST = "https://graphql.anilist.co"
MANGADEX = "https://api.mangadex.org"
MANGADEX_UPLOADS = "https://uploads.mangadex.org"
MANGABAKA = "https://api.mangabaka.org/v1"
DANBOORU = "https://danbooru.donmai.us"

# --- Series identity -----------------------------------------------------------------------------------------------

_MEDIA_FIELDS = """id idMal siteUrl format status countryOfOrigin startDate { year }
  title { romaji english native } synonyms
  staff(perPage: 10, sort: [RELEVANCE]) { edges { role node { id name { full native } } } }
  relations { edges { relationType node { id type format } } }"""


def anilist_search(http, title):
    query = f"""query ($search: String) {{ Page(perPage: 8) {{
        media(search: $search, type: MANGA, sort: [SEARCH_MATCH]) {{ {_MEDIA_FIELDS} }} }} }}"""
    return http.json(ANILIST, {"query": query, "variables": {"search": title}})["data"]["Page"]["media"]


def anilist_media(http, anilist_id):
    query = f"query ($id: Int) {{ Media(id: $id, type: MANGA) {{ {_MEDIA_FIELDS} }} }}"
    return http.json(ANILIST, {"query": query, "variables": {"id": anilist_id}})["data"]["Media"]


def anilist_main_characters(http, anilist_id):
    query = """query ($id: Int, $page: Int) { Media(id: $id) { characters(role: MAIN, perPage: 25, page: $page,
        sort: [ROLE, RELEVANCE, ID]) { pageInfo { hasNextPage } edges { role node { id siteUrl gender
        name { first middle last full native alternative } image { large } } } } } }"""
    characters, page = [], 1
    while True:
        data = http.json(ANILIST, {"query": query, "variables": {"id": anilist_id, "page": page}})
        block = data["data"]["Media"]["characters"]
        characters += [dict(e["node"], role=e["role"]) for e in block["edges"]]
        if not block["pageInfo"]["hasNextPage"] or page >= 4:
            return characters
        page += 1


def mangabaka_search(http, title):
    url = f"{MANGABAKA}/series/search?" + urllib.parse.urlencode({"q": title, "limit": 10})
    return http.json(url).get("data") or []


def mangadex_search(http, title):
    params = [("title", title), ("limit", "10"), ("includes[]", "author"), ("includes[]", "artist"),
              ("order[relevance]", "desc")] + [("contentRating[]", r) for r in ("safe", "suggestive", "erotica")]
    return http.json(f"{MANGADEX}/manga?" + urllib.parse.urlencode(params)).get("data") or []


def mangadex_covers(http, manga_id, locale="ja"):
    covers, offset = [], 0
    while True:
        params = [("manga[]", manga_id), ("locales[]", locale), ("limit", "100"), ("offset", str(offset)),
                  ("order[volume]", "asc")]
        data = http.json(f"{MANGADEX}/cover?" + urllib.parse.urlencode(params))
        for c in data["data"]:
            a = c["attributes"]
            base = f"{MANGADEX_UPLOADS}/covers/{manga_id}/{a['fileName']}"
            covers.append({"id": c["id"], "volume": a["volume"], "locale": a["locale"], "url": base,
                           "thumbnail": base + ".512.jpg", "small": base + ".256.jpg",
                           "description": a.get("description") or ""})
        offset += 100
        if offset >= data["total"]:
            return covers


def name_tokens(name):
    """Lowercase words of a person's name, without accents on the long vowels ("Eiichirou" = "Eiichiro")."""
    name = name.lower().replace("ou", "o").replace("uu", "u")
    return set(re.findall(r"[a-z]+", name))


def same_author(a, b):
    """Two author names written differently ("Eiichirou Oda", "Oda Eiichirou (尾田栄一郎)") but sharing their words."""
    ta, tb = name_tokens(a), name_tokens(b)
    return len(ta & tb) >= min(2, len(ta), len(tb))


def identify(http, title, anilist_id=None):
    """Finds the series on AniList, then looks for the same AniList id on MangaBaka and MangaDex.

    The identity is cross-checked when at least two databases besides AniList's own search give the same id, and an
    author name is shared (spec, section 4; D14).
    """
    if anilist_id:
        media = anilist_media(http, anilist_id)
    else:
        found = [m for m in anilist_search(http, title) if m["format"] in ("MANGA", "ONE_SHOT")]
        if not found:
            raise LookupError(f"AniList has no manga called {title!r}")
        media = found[0]
    authors = [e["node"]["name"]["full"] for e in media["staff"]["edges"]
               if re.search(r"story|art|original", e["role"], re.I) and "assistant" not in e["role"].lower()]
    has_anime = any(e["node"]["type"] == "ANIME" for e in media["relations"]["edges"])
    identity = {
        "title": media["title"]["english"] or media["title"]["romaji"],
        "titles": media["title"], "synonyms": media.get("synonyms") or [],
        "anilist_id": media["id"], "mal_id": media["idMal"], "anilist_url": media["siteUrl"],
        "year": (media.get("startDate") or {}).get("year"), "authors": authors, "has_anime": has_anime,
        "checks": [],
    }
    for series in mangabaka_search(http, title):
        if ((series.get("source") or {}).get("anilist") or {}).get("id") == media["id"]:
            names = (series.get("authors") or []) + (series.get("artists") or [])
            identity["mangabaka_id"] = series["id"]
            identity["checks"].append({
                "base": "mangabaka", "id": series["id"], "anilist_id": media["id"], "url": series.get("canonical_url"),
                "authors": names, "same_author": any(same_author(a, b) for a in names for b in authors)})
            break
    for manga in mangadex_search(http, title):
        links = manga["attributes"].get("links") or {}
        if str(links.get("al")) == str(media["id"]):
            names = sorted({r["attributes"]["name"] for r in manga["relationships"]
                            if r["type"] in ("author", "artist") and "attributes" in r})
            identity["mangadex_id"] = manga["id"]
            identity["mangadex_links"] = links
            identity["checks"].append({
                "base": "mangadex", "id": manga["id"], "anilist_id": media["id"],
                "url": f"https://mangadex.org/title/{manga['id']}", "authors": names,
                "same_author": any(same_author(a, b) for a in names for b in authors)})
            break
    return identity


# --- Control words: Danbooru -------------------------------------------------------------------------------------

DANBOORU_CHARACTER, DANBOORU_COPYRIGHT = 4, 3
_COLOR_TAG = re.compile(r"^(?:(light|dark)_)?(aqua|black|blonde|blue|brown|green|grey|orange|pink|purple|red|silver|"
                        r"white|yellow)_(hair|eyes)$")
_SKIN_TAGS = {"dark_skin": "dark", "dark-skinned_male": "dark", "dark-skinned_female": "dark", "tan": "tan",
              "pale_skin": "pale", "colored_skin": "colored", "blue_skin": "blue", "green_skin": "green",
              "red_skin": "red", "grey_skin": "grey", "purple_skin": "purple", "pink_skin": "pink"}


def danbooru_wiki_titles(http, name):
    url = f"{DANBOORU}/wiki_pages.json?" + urllib.parse.urlencode({"search[other_names_match]": name, "limit": 10})
    return [w["title"] for w in http.json(url)]


def danbooru_tags(http, names):
    url = f"{DANBOORU}/tags.json?" + urllib.parse.urlencode({"search[name_comma]": ",".join(names), "limit": 50})
    return {t["name"]: t for t in http.json(url)}


def danbooru_related(http, tag, category, limit=100):
    url = f"{DANBOORU}/related_tag.json?" + urllib.parse.urlencode(
        {"query": tag, "category": category, "limit": limit})
    return [(r["tag"]["name"], float(r.get("frequency") or r.get("overlap_coefficient") or 0))
            for r in http.json(url).get("related_tags") or []]


def danbooru_series_tag(http, identity):
    """The series' copyright tag, from the titles (a wiki page naming it, or the romaji title itself)."""
    names = [identity["titles"].get(k) for k in ("native", "romaji", "english")] + identity["synonyms"]
    candidates = []
    for name in filter(None, names):
        candidates += danbooru_wiki_titles(http, name)
        candidates.append(re.sub(r"\W+", "_", name.strip().lower()).strip("_"))
    tags = danbooru_tags(http, list(dict.fromkeys(candidates))[:20])
    best = [t for t in tags.values() if t["category"] == DANBOORU_COPYRIGHT]
    return max(best, key=lambda t: t["post_count"])["name"] if best else None


def danbooru_character(http, character, series_tag):
    """The character's tag: a wiki page that names the character (Japanese name first), checked against the series.

    Homonyms are frequent ("Nami" is also a League of Legends character): a candidate is kept only when the series'
    copyright tag comes with it on at least half of its pictures.
    """
    names = [character["name"].get("native")] + (character["name"].get("alternative") or [])
    names += [character["name"].get("full")]
    candidates = []
    for name in filter(None, names[:4]):
        for title in danbooru_wiki_titles(http, name):
            if title not in candidates:
                candidates.append(title)
        if candidates:
            break
    if not candidates:
        return None
    tags = danbooru_tags(http, candidates)
    for name in candidates:
        tag = tags.get(name)
        if not tag or tag["category"] != DANBOORU_CHARACTER:
            continue
        copyrights = dict(danbooru_related(http, name, DANBOORU_COPYRIGHT, 10))
        if series_tag is None or copyrights.get(series_tag, 0) >= 0.5:
            return {"tag": name, "posts": tag["post_count"], "series_share": copyrights.get(series_tag)}
    return None


def danbooru_words(http, tag):
    """Color tags drawn with the character, with their frequency: {"hair": [("green", 0.72)], "eyes": [...]}."""
    words = {"hair": Counter(), "eyes": Counter(), "skin": Counter()}
    for name, freq in danbooru_related(http, tag, 0, 300):
        m = _COLOR_TAG.match(name)
        if m:
            color = {"silver": "grey"}.get(m.group(2), m.group(2))
            words[m.group(3)][color] = max(words[m.group(3)][color], freq)
        elif name in _SKIN_TAGS:
            words["skin"][_SKIN_TAGS[name]] = max(words["skin"][_SKIN_TAGS[name]], freq)
    return {part: sorted(c.items(), key=lambda kv: -kv[1]) for part, c in words.items()}


# --- Control words: the series' wiki --------------------------------------------------------------------------------

_WIKI_COLORS = ["black", "white", "grey", "gray", "silver", "blond", "blonde", "golden", "yellow", "orange", "ginger",
                "red", "pink", "purple", "violet", "blue", "navy", "aqua", "turquoise", "teal", "green", "brown",
                "auburn", "tan", "tanned", "pale", "fair", "dark", "light"]
_SKIN_ONLY = {"tan", "tanned", "pale", "fair", "dark", "light"}
_WIKI_NORMAL = {"gray": "grey", "silver": "grey", "blond": "blonde", "golden": "blonde", "ginger": "orange",
                "violet": "purple", "navy": "blue", "turquoise": "aqua", "teal": "aqua", "auburn": "red",
                "tanned": "tan"}


def wiki_host(identity):
    return re.sub(r"[^a-z0-9]", "", identity["title"].lower()) + ".fandom.com"


def wiki_api(http, host, **params):
    return http.json(f"https://{host}/api.php?" + urllib.parse.urlencode({**params, "format": "json"}))


def wiki_page(http, host, character):
    """The wiki page of a character: the Japanese order of the name first ("Monkey D. Luffy", "Roronoa Zoro")."""
    n = character["name"]
    tries = [" ".join(filter(None, [n.get("last"), n.get("middle"), n.get("first")])),
             " ".join(filter(None, [n.get("first"), n.get("middle"), n.get("last")])), n.get("full")]
    for title in dict.fromkeys(filter(None, tries)):
        found = wiki_api(http, host, action="query", titles=title, redirects=1)
        pages = found.get("query", {}).get("pages", {})
        if pages and not any(k.startswith("-") for k in pages):
            return next(iter(pages.values()))["title"]
    found = wiki_api(http, host, action="query", list="search", srsearch=tries[0], srlimit=3)
    results = [r["title"] for r in found.get("query", {}).get("search", []) if "/" not in r["title"]]
    return results[0] if results else None


def plain_text(wikitext):
    text = re.sub(r"\{\{[^{}]*\}\}", " ", wikitext)
    text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<[^>]+>|'''?|==+", " ", text, flags=re.S)
    return re.sub(r"\s+", " ", text)


def appearance_words(text):
    """Color words written just before "hair", "eyes" and "skin" (within three words) in a description."""
    words = {"hair": Counter(), "eyes": Counter(), "skin": Counter()}
    tokens = re.findall(r"[a-z]+(?:-[a-z]+)?", text.lower())
    for i, token in enumerate(tokens):
        part = {"hair": "hair", "eyes": "eyes", "eye": "eyes", "skin": "skin", "skinned": "skin"}.get(token)
        if not part:
            continue
        for word in tokens[max(0, i - 3):i]:
            for piece in word.split("-"):
                # "light", "dark", "pale", "fair" and "tan" describe a skin; before "hair" they only shade a color
                if piece in _WIKI_COLORS and (part == "skin" or piece not in _SKIN_ONLY):
                    words[part][_WIKI_NORMAL.get(piece, piece)] += 1
    return {part: c.most_common() for part, c in words.items()}


def wiki_words(http, host, page):
    """Color words of the "Appearance" section of a character's wiki page (and its sub-sections)."""
    sections = wiki_api(http, host, action="parse", page=page, prop="sections", redirects=1)
    sections = sections.get("parse", {}).get("sections", [])
    start = next((s for s in sections if s["line"].strip().lower() == "appearance"), None)
    if not start:
        return None
    chosen = [start]
    for s in sections[sections.index(start) + 1:]:
        if int(s["toclevel"]) <= int(start["toclevel"]):
            break
        chosen.append(s)
    text = ""
    for s in chosen:
        if not str(s["index"]).isdigit():
            continue
        parsed = wiki_api(http, host, action="parse", page=page, prop="wikitext", section=s["index"], redirects=1)
        text += " " + parsed.get("parse", {}).get("wikitext", {}).get("*", "")
    return appearance_words(plain_text(text))
