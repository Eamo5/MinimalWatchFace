#!/usr/bin/env python3
"""Generates the watch face XML for each flavour from the style definitions in styles.py.

    python3 generator/generate.py                   # write wear4 + wear5 watchface.xml
    python3 generator/generate.py --list            # list styles
    python3 generator/generate.py --preview concentric --out /tmp/wf.xml
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from palette import CLOCK, COLORS, DEFAULTS, LEFT, RIGHT, Palette  # noqa: E402
from wff import E, group, write  # noqa: E402
import styles  # noqa: E402

ROOT = os.path.dirname(HERE)
FLAVORS = {
    "wear4": {"weather": False, "right_default_provider": "SUNRISE_SUNSET"},
    "wear5": {"weather": True, "right_default_provider": "HEART_RATE"},
}
COLOR_LABELS = {
    LEFT: "left_complication_color_label",
    RIGHT: "right_complication_color_label",
    CLOCK: "clock_color_label",
}


class Ctx:
    def __init__(self, flavor, pal):
        self.flavor = flavor
        self.pal = pal
        self.weather = FLAVORS[flavor]["weather"]
        self.v2 = flavor != "wear4"


def load_template(name, pal, **subs):
    with open(os.path.join(HERE, "templates", name), encoding="utf-8") as fh:
        text = fh.read()
    for key, value in subs.items():
        text = text.replace("{" + key + "}", value)
    text = pal.substitute(text)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    return ET.fromstring(text, parser=parser)


def user_configurations(ctx, style_list):
    configs = []
    if style_list is not None:
        configs.append(E("ListConfiguration",
                         *[E("ListOption", id_=s.id, displayName=f"style_{s.key}",
                             screenReaderText=f"style_{s.key}") for s in style_list],
                         defaultValue=style_list[0].id, displayName="style_label",
                         id_="style", screenReaderText="style_label"))
    configs.append(E("BooleanConfiguration", defaultValue="TRUE",
                     displayName="show_battery_percentage_label", id_="show_battery_percentage",
                     screenReaderText="show_battery_percentage_label"))
    if ctx.weather:
        configs.append(E("BooleanConfiguration", defaultValue="TRUE",
                         displayName="show_weather_label", id_="show_weather",
                         screenReaderText="show_weather_label"))
    for config in (LEFT, RIGHT, CLOCK):
        configs.append(E("ColorConfiguration",
                         *[E("ColorOption", colors=" ".join(c.tones), displayName=c.name,
                             id_=c.id) for c in COLORS],
                         defaultValue=DEFAULTS[config], displayName=COLOR_LABELS[config],
                         id_=config, screenReaderText=COLOR_LABELS[config]))
    return E("UserConfigurations", *configs)


def style_group(ctx, s):
    return group(f"style_{s.key}", s.build(ctx))


def build(flavor, style_list, pal, preview_style=None):
    ctx = Ctx(flavor, pal)
    slots = load_template("complication_slots.xml", pal,
                          right_default_provider=FLAVORS[flavor]["right_default_provider"])
    if preview_style is not None:
        scene_children = [style_group(ctx, preview_style)]
    else:
        scene_children = [E("ListConfiguration",
                            *[E("ListOption", style_group(ctx, s), id_=s.id) for s in style_list],
                            id_="style")]
    scene = E("Scene", *scene_children, *list(slots))
    root = E("WatchFace",
             E("Metadata", key="CLOCK_TYPE", value="DIGITAL"),
             E("Metadata", key="PREVIEW_TIME", value="10:08:32"),
             user_configurations(ctx, None if preview_style is not None else style_list),
             load_template("weather_bitmap_fonts.xml", pal) if ctx.weather else None,
             scene,
             height=450, width=450)
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--preview", help="style key to render on its own with literal colours")
    parser.add_argument("--palette", help="clock,left,right colour ids for --preview")
    parser.add_argument("--flavor", default="wear5", choices=sorted(FLAVORS))
    parser.add_argument("--out")
    parser.add_argument("--preview-time", help="print the preview time for a style key")
    args = parser.parse_args()

    style_list = styles.enabled()
    if args.preview_time:
        print(styles.by_key(args.preview_time).preview_time)
        return
    if args.list:
        for s in style_list:
            print(f"{s.id:>3}  {s.key:<16} {s.category:<10} {s.name}")
        return

    if args.preview:
        s = styles.by_key(args.preview)
        ids = [int(v) for v in args.palette.split(",")] if args.palette else s.palette
        pal = Palette(dict(zip((CLOCK, LEFT, RIGHT), ids)))
        write(build(args.flavor, style_list, pal, preview_style=s), args.out)
        return

    for flavor in FLAVORS:
        out_dir = os.path.join(args.out, flavor) if args.out else os.path.join(
            ROOT, "watchface", "src", flavor, "res", "raw")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "watchface.xml")
        write(build(flavor, style_list, Palette()), out)
        print("wrote", out)


if __name__ == "__main__":
    main()
