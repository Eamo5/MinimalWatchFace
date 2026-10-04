"""Colour options and tonal palettes.

Every colour option exposes four tones, referenced as [CONFIGURATION.<id>.<tone>]:
    0  bright   - the named colour itself
    1  dark     - a darker shade (rings, secondary marks)
    2  container - a deep, low-chroma shade for filled shapes behind text
    3  light    - a pale tint for text drawn on top of containers
"""
import colorsys
import csv
import os

BRIGHT, DARK, CONTAINER, LIGHT = 0, 1, 2, 3

CLOCK = "clockText"
LEFT = "leftComplication"
RIGHT = "rightComplication"

_HERE = os.path.dirname(os.path.abspath(__file__))


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02X}" for c in rgb)


def _with_lightness(hex_color, lightness, max_saturation):
    r, g, b = _hex_to_rgb(hex_color)
    h, _, s = colorsys.rgb_to_hls(r, g, b)
    return _rgb_to_hex(colorsys.hls_to_rgb(h, lightness, min(s, max_saturation)))


class ColorOption:
    def __init__(self, cid, name, bright, dark):
        self.id = cid
        self.name = name
        self.tones = [
            bright,
            dark,
            _with_lightness(bright, 0.19, 0.55),
            _with_lightness(bright, 0.86, 0.85),
        ]


def load_colors():
    with open(os.path.join(_HERE, "templates", "colors.csv"), encoding="utf-8") as fh:
        return [ColorOption(int(r["id"]), r["name"], r["bright"], r["dark"])
                for r in csv.DictReader(fh)]


COLORS = load_colors()
COLORS_BY_ID = {c.id: c for c in COLORS}

DEFAULTS = {CLOCK: 50, LEFT: 0, RIGHT: 30}


class Palette:
    """Resolves colour tokens to configuration references, or to literal colours in previews."""

    def __init__(self, preview=None):
        # preview: {CLOCK: id, LEFT: id, RIGHT: id} or None for configuration references
        self.preview = preview

    def _get(self, config, tone):
        if self.preview is None:
            return f"[CONFIGURATION.{config}.{tone}]"
        return COLORS_BY_ID[self.preview[config]].tones[tone]

    def clock(self, tone=BRIGHT):
        return self._get(CLOCK, tone)

    def left(self, tone=BRIGHT):
        return self._get(LEFT, tone)

    def right(self, tone=BRIGHT):
        return self._get(RIGHT, tone)

    def substitute(self, xml_text):
        """Replace configuration colour references in template XML for previews."""
        if self.preview is None:
            return xml_text
        for config in (CLOCK, LEFT, RIGHT):
            for tone in range(4):
                xml_text = xml_text.replace(f"[CONFIGURATION.{config}.{tone}]",
                                            self._get(config, tone))
        return xml_text
