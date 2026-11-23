"""Color measurement on synthetic images: OKLab, most frequent tone (never the mean), three tones, groups, words."""
import cv2
import numpy as np
import pytest

from colorsheet import measure


def rgb(code):
    code = code.lstrip("#")
    return np.array([int(code[i:i + 2], 16) for i in (0, 2, 4)], np.uint8)


def cel_part(base, shadow=None, highlight=None, lines=True, size=240, seed=0):
    """A flat-colored part as drawn on a cover: base, a shadow band, highlight streaks, black line art, JPEG-like
    noise. Returns (image, mask)."""
    rng = np.random.default_rng(seed)
    image = np.full((size, size, 3), 255, np.uint8)
    mask = np.zeros((size, size), bool)
    cv2.circle(image, (size // 2, size // 2), size // 2 - 10, rgb(base).tolist(), -1)
    cv2.circle(mask.view(np.uint8), (size // 2, size // 2), size // 2 - 10, 1, -1)
    if shadow:
        band = np.zeros((size, size), np.uint8)
        cv2.ellipse(band, (size // 2 + 40, size // 2 + 30), (70, 50), 30, 0, 360, 1, -1)
        image[(band > 0) & mask] = rgb(shadow)
    if highlight:
        for k in range(3):
            cv2.line(image, (60 + 25 * k, 70), (90 + 25 * k, 110), rgb(highlight).tolist(), 5)
    if lines:
        cv2.circle(image, (size // 2, size // 2), size // 2 - 10, (0, 0, 0), 3)
        for k in range(4):
            cv2.line(image, (50 + 30 * k, 40), (70 + 30 * k, 200), (0, 0, 0), 2)
    noise = rng.normal(0, 2.0, image.shape)
    return np.clip(image + noise, 0, 255).astype(np.uint8), mask


def test_oklab_reference_values():
    assert np.allclose(measure.rgb_to_oklab(rgb("#ffffff")), [1, 0, 0], atol=1e-4)
    assert np.allclose(measure.rgb_to_oklab(rgb("#000000")), [0, 0, 0], atol=1e-6)
    # Values published with OKLab (sRGB red)
    assert np.allclose(measure.rgb_to_oklab(rgb("#ff0000")), [0.62796, 0.22486, 0.12585], atol=2e-4)
    for code in ("#2aa79b", "#1c7f78", "#f6d3bd", "#1b1b1f"):
        assert measure.oklab_to_hex(measure.hex_to_oklab(code)) == code


def test_most_frequent_tone_is_the_base_not_the_mean():
    image, mask = cel_part("#2aa79b", shadow="#1c7f78", highlight="#6fd6c8")
    tones = measure.measure_part(image, mask, "hair")
    assert measure.delta_e(tones["base"], measure.hex_to_oklab("#2aa79b")) < 0.01
    assert measure.delta_e(tones["shadow"], measure.hex_to_oklab("#1c7f78")) < 0.015
    assert measure.delta_e(tones["highlight"], measure.hex_to_oklab("#6fd6c8")) < 0.03
    # The mean mixes base, shadow, highlight and lines into a color that isn't in the drawing
    clean = measure.clean_part_mask(image, mask)
    mean = measure.rgb_to_oklab(image[clean]).mean(axis=0)
    assert measure.delta_e(mean, measure.hex_to_oklab("#2aa79b")) > 0.02


def test_line_art_is_neither_base_nor_shadow():
    image, mask = cel_part("#f39a3c", shadow="#d9762a")
    tones = measure.measure_part(image, mask, "hair")
    assert measure.color_word(tones["base"]) == "orange"
    assert measure.lch(tones["shadow"])[0] > 0.4  # the shadow tone, not the black lines


def test_black_hair_stays_black():
    image, mask = cel_part("#1d1d24", highlight="#5a6070")
    tones = measure.measure_part(image, mask, "hair")
    assert tones is not None
    assert measure.color_word(tones["base"]) == "black"
    assert measure.delta_e(tones["base"], measure.hex_to_oklab("#1d1d24")) < 0.02


def test_too_few_pixels_gives_nothing():
    image, mask = cel_part("#2aa79b", size=40)
    small = np.zeros_like(mask)
    small[18:22, 18:22] = True
    assert measure.measure_part(image, small, "hair") is None


def test_eyes_drop_the_white_of_the_eye():
    image = np.full((60, 60, 3), 250, np.uint8)
    mask = np.zeros((60, 60), bool)
    mask[10:50, 10:50] = True
    image[20:40, 22:38] = rgb("#3a6fd8")  # iris
    tones = measure.measure_part(image, mask, "eyes")
    assert measure.color_word(tones["base"], "eyes") == "blue"


def test_black_and_white_images_are_detected():
    gray = np.tile(np.linspace(0, 255, 300, dtype=np.uint8)[None, :, None], (300, 1, 3))
    assert not measure.is_color_image(gray)
    logo = gray.copy()
    logo[:40, :40] = rgb("#d42020")  # 1.8 % of the page
    assert not measure.is_color_image(logo)
    colored, _ = cel_part("#2aa79b", shadow="#1c7f78")
    assert measure.is_color_image(colored)


def test_densest_group_over_several_images():
    greens = ["#3cb043", "#40b448", "#38a83f", "#3db246", "#42b04a"]
    blues = ["#3a6fd8", "#3c72dc"]
    values = [measure.hex_to_oklab(c) for c in greens + blues]
    groups = measure.densest_groups(values)
    assert len(groups[0]["members"]) == 5
    assert measure.color_word(groups[0]["value"]) == "green"
    assert sorted(groups[1]["members"]) == [5, 6]


@pytest.mark.parametrize("code,part,word", [
    ("#111111", "hair", "black"), ("#1b1b2a", "hair", "black"), ("#f8f8f8", "hair", "white"),
    ("#8a8a8a", "hair", "grey"), ("#3cb043", "hair", "green"), ("#9dcea7", "hair", "green"),
    ("#f28c28", "hair", "orange"), ("#f39a3c", "hair", "orange"), ("#f5d76e", "hair", "blonde"),
    ("#f5d76e", "eyes", "yellow"), ("#7b4a2b", "hair", "brown"), ("#3a6fd8", "hair", "blue"),
    ("#ff9ccf", "hair", "pink"), ("#d42020", "hair", "red"), ("#8a4fc4", "hair", "purple"),
    ("#40c8d0", "hair", "aqua"),
])
def test_color_words(code, part, word):
    assert measure.color_word(measure.hex_to_oklab(code), part) == word


def test_neighboring_words():
    assert measure.words_agree("orange", "red")
    assert measure.words_agree("blonde", "yellow")
    assert not measure.words_agree("green", "blonde")
    assert not measure.words_agree("black", "orange")


def test_skin_tones():
    assert measure.is_natural_skin(measure.hex_to_oklab("#f6d3bd"))
    assert measure.skin_word(measure.hex_to_oklab("#f6d3bd")) == "light"
    assert measure.skin_word(measure.hex_to_oklab("#c98a5a")) == "tan"
    assert not measure.is_natural_skin(measure.hex_to_oklab("#5a8fd8"))
    assert measure.skin_word(measure.hex_to_oklab("#5a8fd8")) == "blue"


def test_eye_color_is_the_iris_not_the_pupil():
    image = np.full((60, 60, 3), 250, np.uint8)
    mask = np.zeros((60, 60), bool)
    mask[10:50, 10:50] = True
    image[16:44, 20:40] = rgb("#2b8fa8")  # iris
    image[22:38, 24:36] = rgb("#0d0d10")  # pupil and lashes, the larger tone
    image[10:16, 10:50] = rgb("#0d0d10")
    tones = measure.measure_part(image, mask, "eyes")
    assert measure.color_word(tones["base"], "eyes") in ("aqua", "blue")
