"""Doubt rules (D14) and the choice of a color over several images."""
from colorsheet import measure, rules


def obs(code, kind="volume_cover", ref="ref", volume=None):
    return {"lab": measure.hex_to_oklab(code), "shadow": None, "highlight": None, "ref": ref, "kind": kind,
            "volume": volume}


GREENS = ["#3cb043", "#40b448", "#38a83f"]


def test_single_image_is_a_doubt():
    entry, doubts = rules.settle_part("hair", [obs("#3cb043", "anime")])
    assert entry["base"] == "#3cb043" and entry["images"] == 1
    assert len(doubts) == 1 and "une image" in doubts[0]
    assert rules.character_status(doubts) == "to_review"


def test_agreeing_covers_pass_without_question():
    observations = [obs(c, ref=f"ref-{i}") for i, c in enumerate(GREENS)] + [obs("#45b84d", "anime")]
    entry, doubts = rules.settle_part("hair", observations)
    assert doubts == []
    assert entry["kind"] == "volume_cover" and entry["images"] == 3 and entry["of"] == 3
    assert entry["word"] == "green"
    assert rules.character_status(doubts) == "automatic"


def test_covers_against_anime_is_a_doubt():
    observations = [obs(c) for c in GREENS] + [obs("#3a6fd8", "anime")]
    entry, doubts = rules.settle_part("hair", observations)
    assert entry["word"] == "green"
    assert any("ne s'accordent pas" in d for d in doubts)


def test_disagreeing_images_are_a_doubt():
    entry, doubts = rules.settle_part("hair", [obs("#3cb043"), obs("#3a6fd8")])
    assert entry is not None and entry["images"] == 1
    assert any("ne s'accordent pas" in d for d in doubts)


def test_one_cover_confirmed_by_anime_is_enough():
    entry, doubts = rules.settle_part("hair", [obs("#3cb043"), obs("#40b448", "anime")])
    assert doubts == [] and entry["images"] == 2 and entry["kind"] == "volume_cover"


def test_two_stable_colors_become_a_variant_and_a_doubt():
    observations = [obs(c) for c in GREENS] + [obs("#3a6fd8"), obs("#3c72dc")]
    entry, doubts = rules.settle_part("hair", observations)
    assert entry["word"] == "green" and entry["variant"]["images"] == 2
    assert any("deux couleurs stables" in d for d in doubts)


def test_mode_of_several_images_ignores_an_odd_one():
    observations = [obs(c) for c in GREENS + ["#42b04a"]] + [obs("#d42020")]
    entry, doubts = rules.settle_part("hair", observations)
    assert entry["word"] == "green" and entry["images"] == 4 and entry["of"] == 5
    assert doubts == []


def test_control_words():
    entry = {"word": "green"}
    assert rules.check_words("hair", entry, {"danbooru": [("green", 0.72)]}) == ("accord", None)
    verdict, doubt = rules.check_words("hair", entry, {"danbooru": [("blonde", 0.64)], "wiki": [("blonde", 3)]})
    assert verdict == "désaccord" and "blond" in doubt and "64 %" in doubt
    assert rules.check_words("hair", {"word": "orange"}, {"danbooru": [("red", 0.5)]})[0] == "accord"
    assert rules.check_words("hair", entry, {})[0] == "sans mot de contrôle"
    # Tags drawn on few of the character's pictures belong to the characters next to them
    assert rules.check_words("hair", entry, {"danbooru": [("blonde", 0.10)]})[0] == "sans mot de contrôle"


def test_control_words_for_skin():
    assert rules.check_words("skin", {"word": "light"}, {})[0] == "accord"
    assert rules.check_words("skin", {"word": "light"}, {"wiki": [("tan", 2)]})[0] == "accord"
    assert rules.check_words("skin", {"word": "blue"}, {"danbooru": [("blue", 0.5)]})[0] == "accord"
    assert rules.check_words("skin", {"word": "blue"}, {"danbooru": [("colored", 0.4)]})[0] == "accord"
    assert rules.check_words("skin", {"word": "light"}, {"danbooru": [("dark", 0.6)]})[0] == "désaccord"


def test_dominant_outfit_is_kept():
    tops = [obs("#f8f8f2", volume=v) for v in ("1", "5", "9", "13")] + [obs("#d42020", volume="20")]
    outfits, note, groups = rules.settle_outfit({"top": tops})
    assert outfits and outfits[0]["parts"]["top"]["word"] == "white"
    assert note is None
    assert groups["top"][0]["volumes"] == ["1", "5", "9", "13"]


def test_outfit_that_changes_varies_with_the_arc():
    tops = [obs("#f8f8f2", volume="1"), obs("#f8f8f2", volume="5"), obs("#d42020", volume="60"),
            obs("#d42020", volume="64"), obs("#3a6fd8", volume="90")]
    outfits, note, groups = rules.settle_outfit({"top": tops})
    assert outfits == [] and note == "varie selon l'arc"
    assert len(groups["top"]) == 3


def test_identity_needs_two_databases():
    good = {"anilist_id": 1, "checks": [{"base": "mangabaka", "anilist_id": 1, "same_author": True},
                                        {"base": "mangadex", "anilist_id": 1, "same_author": True}]}
    assert rules.series_doubts(good) == []
    one = {"anilist_id": 1, "checks": [{"base": "mangadex", "anilist_id": 1, "same_author": True}]}
    assert "non recoupée" in rules.series_doubts(one)[0]
    other_author = {"anilist_id": 1, "checks": [{"base": "mangabaka", "anilist_id": 1, "same_author": False},
                                                {"base": "mangadex", "anilist_id": 1, "same_author": False}]}
    assert "auteur" in rules.series_doubts(other_author)[0]


def test_no_color_image_is_a_doubt():
    assert rules.no_image_doubt({"hair": [], "eyes": []}) == ["Aucune image en couleur trouvée pour ce personnage."]
    assert rules.no_image_doubt({"hair": [obs("#3cb043")]}) == []


def test_confidence():
    assert rules.confidence(1, 1) == 0.5
    assert rules.confidence(2, 2) == 0.75
    assert rules.confidence(4, 5) == 0.75
    assert rules.confidence(0, 0) == 0.0
