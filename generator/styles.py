"""Watch face styles. Each style renders into its own Group inside the 'style' ListConfiguration.

The two complication slots are fixed by the format (slots can't live inside a ListOption),
so every style leaves the top-left and top-right slot areas clear:
    left  slot: x 60..172,  y 40..152 (circle centre 116,96 r56)
    right slot: x 278..390, y 40..152 (circle centre 334,96 r56)
"""
import math

import components as C
from palette import BRIGHT, CONTAINER, DARK, LIGHT
from wff import (CX, CY, E, HOUR_ANGLE, MINUTE_ANGLE, SECOND_ANGLE, ambient, arc, circle,
                 circular_text, group, hand, line, part_draw, part_text, polar, rect, rrect,
                 stroke, time_text, transform)

SLOT_CENTERS = [(116, 96), (334, 96)]
HOURS_Z = "[IS_24_HOUR_MODE] ? [HOUR_0_23_Z] : [HOUR_1_12_Z]"
SLOT_RADIUS = 56


def clear_of_slots(x, y, margin=0):
    return all(math.hypot(x - sx, y - sy) > SLOT_RADIUS + margin for sx, sy in SLOT_CENTERS)


class Style:
    def __init__(self, sid, key, name, category, fn, palette, description, enabled,
                 preview_time):
        self.id = str(sid)
        self.key = key
        self.name = name
        self.category = category
        self.fn = fn
        self.palette = palette
        self.description = description
        self.enabled = enabled
        self.preview_time = preview_time

    def build(self, ctx):
        return self.fn(ctx)


_STYLES = []


def style(sid, key, name, category="classic", palette=(50, 0, 30), description="",
          enabled=True, preview_time="10:08:30"):
    def deco(fn):
        _STYLES.append(Style(sid, key, name, category, fn, palette, description, enabled,
                             preview_time))
        return fn
    return deco


def enabled():
    return sorted((s for s in _STYLES if s.enabled), key=lambda s: int(s.id))


def by_key(key):
    return next(s for s in _STYLES if s.key == key)


# =====================================================================================
# Helpers
# =====================================================================================

def _variant_host(el):
    # Ambient Variants are ignored on parts that also carry a Transform, so wrap those.
    if el.tag != "Group" and el.find("Transform") is not None:
        return group(f"{el.get('name') or el.tag.lower()}_host", el)
    return el


def active_only(el):
    el = _variant_host(el)
    el.append(ambient("alpha", 0))
    return el


def ambient_only(el):
    el = _variant_host(el)
    el.set("alpha", "0")
    el.append(ambient("alpha", 255))
    return el


def dual_time(fmt, x, y, w, h, size, color, weight, ambient_weight="LIGHT", ambient_color=None,
              align="CENTER"):
    """A bold time for interactive mode that swaps to a lighter weight in ambient."""
    return [
        active_only(time_text(fmt, x, y, w, h, size, color=color, weight=weight, align=align)),
        ambient_only(time_text(fmt, x, y, w, h, size, color=ambient_color or color,
                               weight=ambient_weight, align=align)),
    ]


def radial_ticks(count, r_in, r_out, color, thickness, skip_every=None, margin=6, cap="ROUND",
                 only_every=None):
    """Radial tick marks around the centre, dropping any that would touch a complication."""
    lines = []
    for i in range(count):
        if skip_every and i % skip_every == 0:
            continue
        if only_every and i % only_every != 0:
            continue
        deg = i * 360 / count
        x1, y1 = polar(r_in, deg)
        x2, y2 = polar(r_out, deg)
        if clear_of_slots(x1, y1, margin) and clear_of_slots(x2, y2, margin):
            lines.append(line(x1, y1, x2, y2, color, thickness, cap))
    return part_draw(*lines)


def centered_text(cx, cy, w, h, fmt, *exprs, **kw):
    return part_text(cx - w / 2, cy - h / 2, w, h, fmt, *exprs, **kw)


def dual_text(x, y, w, h, fmt, *exprs, color, weight, ambient_weight="LIGHT", ambient_color=None,
              **kw):
    return [
        active_only(part_text(x, y, w, h, fmt, *exprs, color=color, weight=weight, **kw)),
        ambient_only(part_text(x, y, w, h, fmt, *exprs, color=ambient_color or color,
                               weight=ambient_weight, **kw)),
    ]


def lookup(expr, values):
    """Nested ternary mapping integer expression values 0..n-1 to string literals."""
    out = '""'
    for i in reversed(range(len(values))):
        out = f'({expr}) == {i} ? "{values[i]}" : {out}'
    return out


def counter_rotated(name, cx, cy, orbit_r, angle_expr, size, *content):
    """Content of `size` square that orbits (cx, cy) at orbit_r but stays upright."""
    box = 2 * (orbit_r + size / 2)
    inner = group(f"{name}_body", *content,
                  transform("angle", f"-({angle_expr})"),
                  x=box / 2 - size / 2, y=box / 2 - orbit_r - size / 2, w=size, h=size)
    return group(name, inner, transform("angle", angle_expr),
                 x=cx - box / 2, y=cy - box / 2, w=box, h=box)


# =====================================================================================
# 0  Minimal - the original face, unchanged
# =====================================================================================

@style(0, "minimal", "Minimal", description="The original face: large time, date, battery.")
def minimal(ctx):
    pal = ctx.pal
    return [
        time_text("h:mm", 0, 150, 450, 155, 155, tint=pal.clock()),
        C.battery_text(0, 360, 450, 31, 31),
        C.info_line(ctx, 300, 31, h=47),
    ]


# =====================================================================================
# 1  Bold Stack - hours over minutes, heavy weight (Pixel 'Bold' / 'Big Time')
# =====================================================================================

@style(1, "bold", "Bold Stack", palette=(36, 36, 9),
       description="Huge stacked hours and minutes in two tones; thins out in ambient.")
def bold(ctx):
    pal = ctx.pal
    return [
        *dual_time("hh", 0, 160, 450, 150, 150, pal.clock(), "BLACK"),
        *dual_time("mm", 0, 290, 450, 150, 150, pal.clock(LIGHT), "BLACK",
                   ambient_color="#FFFFFF"),
        C.date_text(172, 46, 106, 34, 26, C.SHORT_DATE, color=pal.clock(), weight="BOLD"),
        C.battery_text(172, 82, 106, 28, 22, color="#C8C8C8"),
    ]


# =====================================================================================
# 2  Concentric - big hour, rotating minute ring read at 3 o'clock (Pixel 'Concentric')
# =====================================================================================

def fade_top_mask():
    """Static mask that fades a full-circle ring out where the complications sit."""
    grad = E("SweepGradient", centerX=CX, centerY=CY, startAngle=0, endAngle=360,
             colors="#00FFFFFF #00FFFFFF #FFFFFFFF #FFFFFFFF #00FFFFFF #00FFFFFF",
             positions="0 0.17 0.24 0.76 0.83 1")
    return part_draw(E("Ellipse", E("Fill", grad, color="#FFFFFFFF"), x=0, y=0, width=450,
                       height=450), renderMode="MASK")


@style(2, "concentric", "Concentric", palette=(9, 9, 26),
       description="A minute ring rotates past a fixed pill at 3 o'clock; big hour in the middle.")
def concentric(ctx):
    pal = ctx.pal
    ring = [radial_ticks(60, 205, 215, pal.clock(DARK), 3, skip_every=5, margin=-200)]
    ring.append(radial_ticks(60, 202, 217, pal.clock(), 4, only_every=5, margin=-200))
    for i in range(12):
        m = i * 5
        x, y = polar(184, m * 6)
        # hide labels as they pass under the minute pill
        near = f"abs({m} - [MINUTE] - [SECOND] / 60)"
        ring.append(centered_text(x, y, 44, 30, f"{m:02d}", size=24, weight="MEDIUM",
                                  color=pal.clock(LIGHT), angle=m * 6 - 90,
                                  extra=[transform("alpha",
                                                   f"({near} < 4.5 || {near} > 55.5) ? 0 : 255")]))
    rotating = group("minute_ring", *ring,
                     transform("angle", "90 - [MINUTE] * 6 - [SECOND] * 0.1"))
    pill = [
        active_only(part_draw(rrect(0, 0, 96, 54, 27, fill_color=pal.clock()),
                              x=350, y=198, w=96, h=54)),
        ambient_only(part_draw(rrect(2, 2, 92, 50, 25, stroke_color=pal.clock(), thickness=3),
                               x=350, y=198, w=96, h=54)),
        active_only(time_text("mm", 350, 198, 96, 54, 40, color=pal.clock(CONTAINER),
                              weight="BLACK")),
        ambient_only(time_text("mm", 350, 198, 96, 54, 40, color=pal.clock(), weight="BOLD")),
    ]
    return [
        group("ring", fade_top_mask(), rotating),
        *pill,
        *dual_time("hh", 40, 140, 300, 170, 170, pal.clock(LIGHT), "BOLD", "THIN",
                   ambient_color="#FFFFFF"),
        C.info_line(ctx, 306, 26, color=pal.clock(), x=85, w=210, full=C.WEEKDAY_DATE),
        C.battery_text(85, 345, 210, 30, 24, color="#C8C8C8"),
    ]


# =====================================================================================
# 3  Analog Bold - thick pill hands and bars (Pixel 'Pilot Bold')
# =====================================================================================

def hour_bars(r_in, r_out, color, width, dot_r=None, margin=8):
    shapes = []
    for h in range(12):
        deg = h * 30
        x1, y1 = polar(r_in, deg)
        x2, y2 = polar(r_out, deg)
        if clear_of_slots(x1, y1, margin) and clear_of_slots(x2, y2, margin):
            shapes.append(line(x1, y1, x2, y2, color, width))
        elif dot_r:
            x, y = polar(r_out + 2, deg)
            if clear_of_slots(x, y, margin):
                shapes.append(circle(x, y, dot_r, fill_color=color))
    return part_draw(*shapes)


def center_cap(outer, inner, r1=12, r2=5):
    return part_draw(circle(CX, CY, r1, fill_color=outer), circle(CX, CY, r2, fill_color=inner))


def analog_hands(pal, hour_color, minute_color, second_color, hour=(112, 24), minute=(182, 16),
                 second=(198, 4, 36), hollow_hour=False):
    hl, hw = hour
    ml, mw = minute
    kids = []
    if hollow_hour:
        kids.append(hand("hour", hl, hw, None, HOUR_ANGLE, outline=hour_color, thickness=4))
    else:
        kids.append(active_only(hand("hour", hl, hw, hour_color, HOUR_ANGLE)))
        kids.append(ambient_only(hand("hour_ambient", hl, hw, None, HOUR_ANGLE,
                                      outline=hour_color, thickness=3)))
    kids.append(active_only(hand("minute", ml, mw, minute_color, MINUTE_ANGLE)))
    kids.append(ambient_only(hand("minute_ambient", ml, mw, None, MINUTE_ANGLE,
                                  outline=minute_color, thickness=3)))
    if second:
        sl, sw, tail = second
        kids.append(active_only(hand("second", sl, sw, second_color, SECOND_ANGLE, tail=tail)))
    return kids


@style(3, "analog_bold", "Analog Bold", palette=(24, 24, 28),
       description="Chunky pill hands and bar indices; hands hollow out in ambient.")
def analog_bold(ctx):
    pal = ctx.pal
    return [
        radial_ticks(60, 210, 214, pal.clock(DARK), 4, skip_every=5, margin=6),
        hour_bars(176, 210, pal.clock(LIGHT), 14, dot_r=6),
        active_only(part_draw(rrect(0, 0, 84, 40, 20, fill_color=pal.clock(CONTAINER)),
                              x=290, y=205, w=84, h=40)),
        C.date_text(290, 205, 84, 40, 22, C.SHORT_DATE, color=pal.clock(LIGHT), weight="BOLD"),
        C.weather_if_enabled(ctx, [C.weather_icon(80, 207, 36),
                                   C.weather_temp(118, 205, 60, 40, 22, weight="BOLD",
                                                  unit=False)]),
        C.battery_text(175, 290, 100, 30, 22, color=pal.clock(LIGHT), weight="BOLD"),
        *analog_hands(pal, pal.clock(), pal.clock(LIGHT), pal.right()),
        active_only(center_cap(pal.clock(LIGHT), pal.right())),
    ]


# =====================================================================================
# 4  Typograph - big 12/3/6/9 numerals, hollow hour hand
# =====================================================================================

@style(4, "typograph", "Typograph", palette=(50, 0, 30),
       description="Oversized 12 / 3 / 6 / 9 numerals with a hollow hour hand.")
def typograph(ctx):
    pal = ctx.pal
    numerals = [centered_text(x, y, 110, 80, label, size=74, weight="BLACK", color=pal.clock())
                for label, (x, y) in (("12", (225, 76)), ("3", (398, 225)), ("6", (225, 384)),
                                      ("9", (52, 225)))]
    dots = []
    for h in range(12):
        if h % 3 == 0:
            continue
        x, y = polar(200, h * 30)
        if clear_of_slots(x, y, 10):
            dots.append(circle(x, y, 6, fill_color=pal.left()))
    return [
        *numerals,
        part_draw(*dots),
        C.info_line(ctx, 292, 24, color=pal.clock(LIGHT), x=95, w=260),
        C.battery_text(175, 118, 100, 26, 20, color="#B0B0B0"),
        *analog_hands(pal, pal.clock(LIGHT), pal.clock(LIGHT), pal.right(), hour=(110, 28),
                      minute=(178, 12), hollow_hour=True),
        active_only(center_cap(pal.clock(LIGHT), pal.right(), 9, 4)),
    ]


# =====================================================================================
# 5  Pilot - precision dial with minute track and slim hands (Pixel 'Pilot')
# =====================================================================================

@style(5, "pilot", "Pilot", palette=(50, 26, 26),
       description="Precision minute track, hour numerals and slim sword hands.")
def pilot(ctx):
    pal = ctx.pal
    numerals = []
    for h in range(1, 13):
        x, y = polar(168, h * 30)
        if clear_of_slots(x, y, 14):
            numerals.append(centered_text(x, y, 60, 40, str(h), size=32, weight="MEDIUM",
                                          color=pal.clock(LIGHT)))
    return [
        radial_ticks(60, 202, 214, pal.clock(DARK), 2, skip_every=5, margin=4),
        radial_ticks(60, 190, 214, pal.clock(), 5, only_every=5, margin=4, cap="BUTT"),
        *numerals,
        C.battery_text(175, 92, 100, 26, 20, color=pal.clock(DARK)),
        C.weather_if_enabled(ctx, [C.weather_icon(170, 276, 34),
                                   C.weather_temp(206, 274, 80, 38, 22, unit=False)]),
        active_only(part_draw(rrect(0, 0, 96, 36, 10, stroke_color=pal.clock(DARK),
                                    thickness=2), x=177, y=318, w=96, h=36)),
        C.date_text(177, 318, 96, 36, 20, C.SHORT_DATE, color=pal.clock(LIGHT), weight="BOLD"),
        *analog_hands(pal, pal.clock(LIGHT), pal.clock(LIGHT), pal.right(), hour=(104, 12),
                      minute=(172, 8), second=(196, 3, 40)),
        active_only(center_cap(pal.right(), "#000000", 8, 3)),
    ]


# =====================================================================================
# 6  Accent - hours and minutes in tonal containers (Material You)
# =====================================================================================

@style(6, "accent", "Accent", palette=(1, 47, 9),
       description="Hours and minutes sit in rounded tonal containers.")
def accent(ctx):
    pal = ctx.pal

    def tile(x, fmt, container, text, ambient_text):
        return [
            active_only(part_draw(rrect(0, 0, 152, 152, 46, fill_color=container),
                                  x=x, y=158, w=152, h=152)),
            *dual_time(fmt, x, 158, 152, 152, 112, text, "BLACK", "LIGHT",
                       ambient_color=ambient_text),
        ]
    return [
        *tile(68, "hh", pal.clock(CONTAINER), pal.clock(LIGHT), pal.clock()),
        *tile(230, "mm", pal.left(CONTAINER), pal.left(LIGHT), pal.left()),
        C.info_line(ctx, 326, 26, weight="MEDIUM", x=50, w=350, full=C.WEEKDAY_DATE),
        C.battery_text(150, 368, 150, 30, 22, color="#BDBDBD"),
    ]


# =====================================================================================
# 7  Arcs - seconds sweep around the edge, date curved along the bottom
# =====================================================================================

@style(7, "arcs", "Arcs", palette=(3, 3, 36),
       description="Seconds sweep around the bezel; curved date and a battery gauge.")
def arcs(ctx):
    pal = ctx.pal
    d = 438
    seconds = active_only(group(
        "seconds",
        part_draw(arc(CX, CY, d, 0, 360, pal.clock(CONTAINER), 6)),
        part_draw(arc(CX, CY, d, 0, 0, pal.clock(), 6,
                      kids=[transform("endAngle", "[SECOND] * 6")]))))
    battery = C.battery([
        part_draw(arc(CX, CY, 410, -16, 16, pal.clock(CONTAINER), 8)),
        part_draw(arc(CX, CY, 410, -16, -16, pal.clock(LIGHT), 8,
                      kids=[transform("endAngle", "-16 + 32 * [BATTERY_PERCENT] / 100")])),
        part_text(175, 34, 100, 30, "%s%%", "[BATTERY_PERCENT]", size=20, weight="BOLD",
                  color=pal.clock(LIGHT)),
    ])
    return [
        seconds,
        battery,
        *dual_time("h:mm", 0, 150, 450, 135, 128, "#FFFFFF", "MEDIUM", "THIN"),
        C.weather_if_enabled(ctx, [C.weather_icon(180, 290, 40),
                                   C.weather_temp(224, 290, 90, 40, 26, color=pal.clock(LIGHT),
                                                  weight="MEDIUM", unit=False)]),
        circular_text(CX, CY, 372, 240, 120, "%s", C.FULL_DATE, size=24, weight="MEDIUM",
                      color=pal.clock(), direction="COUNTER_CLOCKWISE", localize=True),
    ]


# =====================================================================================
# 8  Offset - diagonal hour / minute stack in light weights
# =====================================================================================

@style(8, "offset", "Offset", palette=(38, 38, 24),
       description="Hours and minutes offset on a diagonal, light and airy.")
def offset(ctx):
    pal = ctx.pal
    return [
        *dual_time("hh", 18, 150, 222, 140, 150, pal.clock(), "LIGHT", "THIN", align="END"),
        *dual_time("mm", 214, 258, 230, 140, 140, "#FFFFFF", "LIGHT", "THIN", align="START"),
        C.date_text(40, 300, 168, 32, 24, C.SHORT_DATE, color=pal.clock(), weight="MEDIUM",
                    align="END"),
        C.battery_text(40, 332, 168, 30, 22, color="#9E9E9E", align="END"),
        C.weather_if_enabled(ctx, [C.weather_icon(252, 186, 36),
                                   C.weather_temp(292, 184, 100, 40, 24, weight="MEDIUM")]),
    ]


# =====================================================================================
# 9  Utility - bold time over Material chips
# =====================================================================================

def chip(x, y, w, h, color, *content):
    return [active_only(part_draw(rrect(0, 0, w, h, h / 2, fill_color=color),
                                  x=x, y=y, w=w, h=h)),
            ambient_only(part_draw(rrect(1, 1, w - 2, h - 2, h / 2 - 1, stroke_color="#5A5A5A",
                                         thickness=2), x=x, y=y, w=w, h=h)),
            *content]


@style(9, "utility", "Utility", palette=(14, 38, 24),
       description="Bold time with date, battery and weather in Material chips.")
def utility(ctx):
    pal = ctx.pal
    date_chip = chip(88, 288, 132, 48, pal.clock(CONTAINER),
                     C.date_text(88, 288, 132, 48, 24, C.SHORT_DATE, color=pal.clock(LIGHT),
                                 weight="BOLD"))
    battery_chip = C.battery(chip(230, 288, 132, 48, pal.left(CONTAINER),
                                  part_text(230, 288, 132, 48, "%s%%", "[BATTERY_PERCENT]",
                                            size=24, weight="BOLD", color=pal.left(LIGHT))))
    weather_chip = C.weather_if_enabled(ctx, chip(
        159, 346, 132, 48, pal.right(CONTAINER),
        C.weather_icon(173, 352, 36),
        C.weather_temp(213, 346, 74, 48, 24, color=pal.right(LIGHT), weight="BOLD",
                       unit=False)))
    return [
        *dual_time("h:mm", 0, 152, 450, 130, 124, "#FFFFFF", "BOLD", "LIGHT"),
        *date_chip,
        battery_chip,
        weather_chip,
    ]


# =====================================================================================
# 10  Cookie - Material 3 Expressive scalloped shape, slowly turning
# =====================================================================================

def cookie_shape(cx, cy, lobes, lobe_orbit, lobe_r, color):
    shapes = [circle(cx, cy, lobe_orbit, fill_color=color)]
    for i in range(lobes):
        x, y = polar(lobe_orbit, i * 360 / lobes, cx, cy)
        shapes.append(circle(x, y, lobe_r, fill_color=color))
    return shapes


@style(10, "cookie", "Cookie", category="eccentric", palette=(23, 23, 35),
       description="A Material 3 Expressive cookie shape turns slowly behind stacked digits.")
def cookie(ctx):
    pal = ctx.pal
    lobes, orbit, lobe_r = 9, 90, 44
    size = 2 * (orbit + lobe_r)
    cy = 272
    shape = group("cookie", part_draw(*cookie_shape(size / 2, size / 2, lobes, orbit, lobe_r,
                                                    pal.clock()), w=size, h=size),
                  # one lobe-period per minute so the turn loops seamlessly
                  transform("angle", f"[SECOND] * {360 / lobes / 60:.4f}"),
                  x=CX - size / 2, y=cy - size / 2, w=size, h=size)
    return [
        active_only(shape),
        *dual_time("hh", 0, cy - 100, 450, 104, 104, pal.clock(CONTAINER), "BLACK",
                   ambient_color=pal.clock()),
        *dual_time("mm", 0, cy - 4, 450, 104, 104, pal.clock(CONTAINER), "BLACK",
                   ambient_color="#FFFFFF"),
        C.date_text(172, 48, 106, 32, 26, C.SHORT_DATE, color=pal.clock(), weight="BOLD"),
        C.battery_text(172, 82, 106, 28, 20, color="#BDBDBD"),
    ]


# =====================================================================================
# 11  Orbit - hour and minute planets circling a sun
# =====================================================================================

@style(11, "orbit", "Orbit", category="eccentric", palette=(46, 26, 9),
       description="Hours and minutes are planets orbiting the centre; digits stay upright.")
def orbit(ctx):
    pal = ctx.pal
    cx, cy = CX, 270
    hour_r, min_r = 60, 120
    hour_size, min_size = 64, 54
    tracks = part_draw(circle(cx, cy, hour_r, stroke_color=pal.clock(DARK), thickness=2),
                       circle(cx, cy, min_r, stroke_color=pal.left(DARK), thickness=2))

    def planet(name, orbit_r, angle, size, fill_color, text_color, fmt, font_size):
        body_active = active_only(part_draw(circle(size / 2, size / 2, size / 2,
                                                   fill_color=fill_color), w=size, h=size))
        body_ambient = ambient_only(part_draw(circle(size / 2, size / 2, size / 2 - 1.5,
                                                     stroke_color=fill_color, thickness=3),
                                              w=size, h=size))
        return counter_rotated(name, cx, cy, orbit_r, angle, size, body_active, body_ambient,
                               *dual_time(fmt, 0, 0, size, size, font_size, text_color, "BLACK",
                                          "MEDIUM", ambient_color=fill_color))
    return [
        tracks,
        active_only(part_draw(circle(cx, cy, 16, fill_color=pal.right()))),
        planet("minute_planet", min_r, "[MINUTE] * 6 + [SECOND] * 0.1", min_size, pal.left(),
               pal.left(CONTAINER), "mm", 28),
        planet("hour_planet", hour_r, HOUR_ANGLE, hour_size, pal.clock(), pal.clock(CONTAINER),
               "hh", 32),
        C.date_text(172, 48, 106, 32, 26, C.SHORT_DATE, color=pal.clock(LIGHT), weight="BOLD"),
        C.battery_text(172, 82, 106, 28, 20, color="#BDBDBD"),
    ]


# =====================================================================================
# 12  Rotary - hour and minute rings turn past a reading window at 6 o'clock
# =====================================================================================

@style(12, "rotary", "Rotary", category="eccentric", palette=(26, 26, 3),
       description="An hour ring and minute track turn past a reading window at 6 o'clock.")
def rotary(ctx):
    pal = ctx.pal
    minute_now = "([MINUTE] + [SECOND] / 60)"
    hour_now = "([HOUR_0_11] + [MINUTE] / 60)"
    minute_ring = [radial_ticks(60, 207, 216, pal.left(DARK), 3, skip_every=5, margin=-300),
                   radial_ticks(60, 200, 218, pal.left(), 5, only_every=5, margin=-300)]
    hour_ring = []
    for h in range(12):
        x, y = polar(140, h * 30)
        near = f"abs({h} - {hour_now})"
        hour_ring.append(centered_text(
            x, y, 56, 40, str(h if h else 12), size=32, weight="BLACK", color=pal.clock(),
            angle=h * 30 - 180,
            extra=[transform("alpha", f"({near} < 0.5 || {near} > 11.5) ? 255 : 90")]))
    window_x, window_y, window_w, window_h = 191, 330, 68, 112
    window = [
        active_only(part_draw(rrect(0, 0, window_w, window_h, 34,
                                    fill_color=pal.clock(CONTAINER)),
                              x=window_x, y=window_y, w=window_w, h=window_h)),
        part_draw(rrect(1.5, 1.5, window_w - 3, window_h - 3, 32.5, stroke_color=pal.clock(),
                        thickness=3), x=window_x, y=window_y, w=window_w, h=window_h),
    ]
    return [
        *window,
        group("rings", fade_top_mask(),
              group("minute_ring", *minute_ring, transform("angle", f"180 - {minute_now} * 6")),
              group("hour_ring", *hour_ring, transform("angle", f"180 - {hour_now} * 30"))),
        *dual_time("mm", window_x, 384, window_w, 40, 30, "#FFFFFF", "BLACK", "MEDIUM"),
        C.date_text(125, 176, 200, 40, 30, C.SHORT_DATE, color="#FFFFFF", weight="BOLD"),
        C.weather_if_enabled(ctx, [C.weather_icon(170, 220, 36),
                                   C.weather_temp(210, 218, 80, 40, 24, unit=False)]),
        C.battery_text(150, 258, 150, 28, 20, color="#BDBDBD"),
    ]


# =====================================================================================
# 13  Pie - the minute sweeps out a slice of the whole screen
# =====================================================================================

@style(13, "pie", "Pie", category="eccentric", palette=(28, 28, 50), preview_time="10:23:30",
       description="Minutes fill the face like a pie chart around a giant hour numeral.")
def pie(ctx):
    pal = ctx.pal
    sweep = "[MINUTE] * 6 + [SECOND] * 0.1"
    dots = []
    for h in range(12):
        x, y = polar(206, h * 30)
        if clear_of_slots(x, y, 8):
            dots.append(circle(x, y, 5, fill_color=pal.clock(LIGHT)))
    return [
        active_only(part_draw(arc(CX, CY, 225, 0, 0, pal.clock(CONTAINER), 225, cap="BUTT",
                                  kids=[transform("endAngle", sweep)]))),
        part_draw(*dots),
        active_only(hand("minute_edge", 225, 6, pal.clock(), sweep)),
        ambient_only(hand("minute_edge_ambient", 225, 3, pal.clock(), sweep)),
        *dual_text(0, 120, 450, 210, "%s", "[HOUR_1_12]", size=220, color="#FFFFFF",
                   weight="BLACK", ambient_weight="THIN"),
        C.date_text(150, 330, 150, 34, 26, C.SHORT_DATE, color=pal.clock(LIGHT), weight="BOLD"),
        C.battery_text(150, 364, 150, 28, 20, color="#BDBDBD"),
    ]


# =====================================================================================
# 14  Liquid - the face fills up like a glass over the hour
# =====================================================================================

@style(14, "liquid", "Liquid", category="eccentric", palette=(3, 3, 26), preview_time="10:37:30",
       description="Water rises minute by minute; digits change colour below the surface.")
def liquid(ctx):
    pal = ctx.pal
    surface = "450 - 450 * ([MINUTE] + [SECOND] / 60) / 60"

    def water(color):
        return rect(0, 450, 450, 450, fill_color=color, kids=[transform("y", surface)])

    def digits(color, weight="BLACK"):
        # Masks only clip sibling parts, so these are PartTexts, not a DigitalClock or Group
        return [part_text(0, 112, 450, 150, "%s", HOURS_Z, size=150, color=color, weight=weight),
                part_text(0, 248, 450, 150, "%s", "[MINUTE_Z]", size=150, color=color,
                          weight=weight)]
    flooded = group("flooded",
                    part_draw(water("#FFFFFFFF"), renderMode="MASK"),
                    part_draw(water(pal.clock())),
                    *digits(pal.clock(CONTAINER)))
    return [
        active_only(group("dry", *digits(pal.clock()))),
        active_only(flooded),
        ambient_only(group("ambient_digits", *digits(pal.clock(), "LIGHT"))),
        C.date_text(172, 48, 106, 32, 26, C.SHORT_DATE, color=pal.clock(LIGHT), weight="BOLD"),
        C.battery_text(172, 82, 106, 28, 20, color="#BDBDBD"),
    ]


# =====================================================================================
# 15  Words - the time spelled out
# =====================================================================================

_UNITS = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_TEENS = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
          "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty"]


def _minute_words(m):
    if m == 0:
        return "o'clock", ""
    if m < 10:
        return "oh", _UNITS[m]
    if m < 20:
        return _TEENS[m - 10], ""
    return _TENS[m // 10], _UNITS[m % 10]


@style(15, "words", "Words", category="eccentric", palette=(19, 19, 36),
       description="The time written out in words (English only).")
def words(ctx):
    pal = ctx.pal
    hours = ["twelve"] + _UNITS[1:] + _TEENS[:2]
    first = lookup("[MINUTE]", [_minute_words(m)[0] for m in range(60)])
    second = lookup("[MINUTE]", [_minute_words(m)[1] for m in range(60)])
    return [
        *dual_text(0, 156, 450, 76, "%s", lookup("[HOUR_0_11]", hours), size=70,
                   color=pal.clock(), weight="BLACK"),
        *dual_text(0, 232, 450, 62, "%s", first, size=56, color="#FFFFFF", weight="LIGHT",
                   ambient_weight="THIN"),
        *dual_text(0, 294, 450, 62, "%s", second, size=56, color="#FFFFFF", weight="LIGHT",
                   ambient_weight="THIN"),
        C.date_text(125, 362, 200, 32, 24, C.SHORT_DATE, color=pal.clock(), weight="BOLD"),
        C.battery_text(150, 394, 150, 26, 20, color="#9E9E9E"),
    ]


# =====================================================================================
# 16  Split - duo-tone face split on a slight tilt
# =====================================================================================

@style(16, "split", "Split", category="eccentric", palette=(44, 44, 26),
       description="A tilted two-tone split: hours on colour, minutes on black.")
def split(ctx):
    pal = ctx.pal
    tint = active_only(part_draw(rect(-400, -300, 625, 1050, fill_color=pal.clock(CONTAINER)),
                                 angle=8))
    seam = ambient_only(part_draw(line(225, -100, 225, 550, pal.clock(DARK), 2), angle=8))
    return [
        tint,
        seam,
        *dual_time("hh", 10, 160, 205, 150, 150, pal.clock(), "BLACK", align="END"),
        *dual_time("mm", 235, 160, 205, 150, 150, "#FFFFFF", "BLACK", align="START"),
        C.date_text(40, 316, 175, 34, 26, C.WEEKDAY, color=pal.clock(LIGHT), weight="BOLD",
                    align="END"),
        C.date_text(235, 316, 175, 34, 26, C.DAY_NUMBER, color="#FFFFFF", weight="BOLD",
                    align="START"),
        C.battery_text(150, 360, 150, 28, 20, color="#BDBDBD"),
    ]


# =====================================================================================
# 17  Poster - a giant cropped hour numeral as the backdrop
# =====================================================================================

@style(17, "poster", "Poster", category="eccentric", palette=(35, 35, 23),
       description="A giant hour fills the screen like a poster, minutes overlaid.")
def poster(ctx):
    pal = ctx.pal
    return [
        active_only(part_text(-80, 92, 520, 380, "%s", "[HOUR_1_12]", size=380, weight="BLACK",
                              color=pal.clock(CONTAINER))),
        ambient_only(part_text(-80, 92, 520, 380, "%s", "[HOUR_1_12]", size=380, weight="THIN",
                               color=pal.clock(DARK))),
        *dual_time("mm", 200, 244, 220, 150, 150, pal.clock(), "BLACK", ambient_color="#FFFFFF",
                   align="END"),
        C.date_text(250, 180, 160, 34, 26, C.SHORT_DATE, color=pal.clock(LIGHT), weight="BOLD",
                    align="END"),
        C.battery_text(250, 214, 160, 26, 20, color="#BDBDBD", align="END"),
    ]


# =====================================================================================
# 18  Sunburst - rays light up as the hour passes
# =====================================================================================

def clear_radius(deg, r_in, r_max, margin=6, step=2):
    """Largest radius along a ray from r_in that stays clear of the complications."""
    r = r_in
    while r + step <= r_max:
        x, y = polar(r + step, deg)
        if not clear_of_slots(x, y, margin):
            break
        r += step
    return r


@style(18, "sunburst", "Sunburst", category="eccentric", palette=(24, 24, 28),
       preview_time="10:38:30",
       description="Sixty rays around the time; rays light up as the minutes pass.")
def sunburst(ctx):
    pal = ctx.pal
    r_in, r_max = 96, 184

    def rays(color, width):
        lines = []
        for i in range(60):
            deg = i * 6
            r_out = clear_radius(deg, r_in, r_max - (0 if i % 5 else -8), margin=8)
            if r_out - r_in < 14:
                continue
            x1, y1 = polar(r_in, deg)
            x2, y2 = polar(r_out, deg)
            lines.append(line(x1, y1, x2, y2, color, width if i % 5 else width + 2))
        return part_draw(*lines)
    sweep = "[MINUTE] * 6 + [SECOND] * 0.1 + 3"
    lit = group("lit",
                part_draw(arc(CX, CY, 225, 0, 0, "#FFFFFFFF", 225, cap="BUTT",
                              kids=[transform("endAngle", sweep)]), renderMode="MASK"),
                rays(pal.clock(), 5))
    return [
        rays(pal.clock(CONTAINER), 5),
        active_only(lit),
        *dual_time("hh", 0, 162, 450, 66, 66, pal.clock(), "BLACK"),
        *dual_time("mm", 0, 222, 450, 66, 66, "#FFFFFF", "BLACK"),
        circular_text(CX, CY, 420, 240, 120, "%s", C.FULL_DATE, size=22, weight="BOLD",
                      color=pal.clock(LIGHT), direction="COUNTER_CLOCKWISE", localize=True),
        C.battery([circular_text(CX, CY, 418, -20, 20, "%s%%", "[BATTERY_PERCENT]", size=20,
                                 weight="BOLD", color="#BDBDBD")]),
    ]


# =====================================================================================
# 19  Segments - a seven-segment display built from Material pills
# =====================================================================================

_SEGMENTS = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg", 6: "acdefg",
             7: "abc", 8: "abcdefg", 9: "abcdfg"}


def _segment_rects(ox, oy, w, h, t, g):
    half = h / 2
    vx = h / 2 - t / 2 - 2 * g
    return {
        "a": (ox + t / 2 + g, oy, w - t - 2 * g, t),
        "g": (ox + t / 2 + g, oy + half - t / 2, w - t - 2 * g, t),
        "d": (ox + t / 2 + g, oy + h - t, w - t - 2 * g, t),
        "f": (ox, oy + t / 2 + g, t, vx),
        "b": (ox + w - t, oy + t / 2 + g, t, vx),
        "e": (ox, oy + half + g, t, vx),
        "c": (ox + w - t, oy + half + g, t, vx),
    }


@style(19, "segments", "Segments", category="eccentric", palette=(15, 15, 30),
       description="A seven-segment display made of rounded pills, ghost segments behind.")
def segments(ctx):
    pal = ctx.pal
    hour = "([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])"
    digits = [
        (f"floor({hour} / 10)", f"([IS_24_HOUR_MODE] || {hour} >= 10)"),
        (f"({hour} % 10)", None),
        ("floor([MINUTE] / 10)", None),
        ("([MINUTE] % 10)", None),
    ]
    w, h, t, g = 64, 128, 15, 3
    xs = [62, 140, 248, 326]
    oy = 166
    ghost, lit = [], []
    for (value, visible), ox in zip(digits, xs):
        for seg, (x, y, sw, sh) in _segment_rects(ox, oy, w, h, t, g).items():
            ghost.append(rrect(x, y, sw, sh, t / 2, fill_color=pal.clock(CONTAINER)))
            on = [d for d, segs in _SEGMENTS.items() if seg in segs]
            cond = " || ".join(f"{value} == {d}" for d in on)
            if visible:
                cond = f"{visible} && ({cond})"
            lit.append(part_draw(rrect(0, 0, sw, sh, t / 2, fill_color=pal.clock()),
                                 transform("alpha", f"({cond}) ? 255 : 0"),
                                 x=x, y=y, w=sw, h=sh))
    colon = part_draw(circle(9, 9, 8, fill_color=pal.clock()), circle(9, 59, 8,
                                                                      fill_color=pal.clock()),
                      transform("alpha", "[SECOND] % 2 == 0 ? 255 : 70"),
                      x=216, y=oy + 30, w=18, h=68)
    return [
        active_only(part_draw(*ghost)),
        *lit,
        colon,
        C.info_line(ctx, 314, 26, color=pal.clock(LIGHT), weight="BOLD", x=60, w=330,
                    full=C.WEEKDAY_DATE),
        C.battery_text(150, 356, 150, 28, 22, color="#BDBDBD"),
    ]


# =====================================================================================
# 20  Shapes - Material shapes mark the hours (Pixel 'Shapes')
# =====================================================================================

def _shape(kind, cx, cy, r, color, angle=0):
    """A ~2r sized Material-style shape centred at (cx, cy)."""
    box = 2 * r + 8
    o = box / 2
    k = []
    if kind == "circle":
        k = [circle(o, o, r, fill_color=color)]
    elif kind == "ring":
        k = [circle(o, o, r - 4, stroke_color=color, thickness=8)]
    elif kind == "square":
        k = [rrect(o - r * 0.9, o - r * 0.9, r * 1.8, r * 1.8, r * 0.5, fill_color=color)]
    elif kind == "diamond":
        k = [rrect(o - r * 0.75, o - r * 0.75, r * 1.5, r * 1.5, r * 0.35, fill_color=color)]
        angle += 45
    elif kind == "pill":
        k = [rrect(o - r * 0.5, o - r, r, 2 * r, r * 0.5, fill_color=color)]
    elif kind == "clover":
        q = r * 0.48
        k = [circle(o + dx * q, o + dy * q, r * 0.55, fill_color=color)
             for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))]
    elif kind == "flower":
        k = cookie_shape(o, o, 6, r * 0.62, r * 0.38, color)
    elif kind == "half":
        k = [arc(o, o + r * 0.35, r, 270, 450, color, r, cap="BUTT")]
    elif kind == "plus":
        k = [rrect(o - r * 0.32, o - r, r * 0.64, 2 * r, r * 0.32, fill_color=color),
             rrect(o - r, o - r * 0.32, 2 * r, r * 0.64, r * 0.32, fill_color=color)]
    return part_draw(*k, x=cx - o, y=cy - o, w=box, h=box, angle=angle or None)


@style(20, "shapes", "Shapes", category="eccentric", palette=(36, 9, 24),
       description="Each hour is marked by a different Material shape.")
def shapes(ctx):
    pal = ctx.pal
    colors = [pal.clock(), pal.left(), pal.right(), pal.clock(LIGHT)]
    kinds = ["flower", None, "pill", "circle", "square", "diamond", "ring", "pill", "clover",
             "half", "plus", None]
    marks, dots = [], []
    for h, kind in enumerate(kinds):
        if not kind:
            continue
        size = 30 if h == 0 else 24
        r = 172 if h == 0 else 186
        x, y = polar(r, h * 30)
        if not clear_of_slots(x, y, size + 14):
            size, r = 15, 204
            x, y = polar(r, h * 30)
        marks.append(_shape(kind, x, y, size, colors[h % 4],
                            angle=h * 30 if kind in ("pill", "half") else 0))
        dots.append(circle(x, y, 5, fill_color=colors[h % 4]))
    return [
        active_only(group("marks", *marks)),
        ambient_only(part_draw(*dots)),
        C.date_text(165, 284, 120, 32, 24, C.SHORT_DATE, color="#FFFFFF", weight="BOLD"),
        C.battery_text(165, 130, 120, 28, 20, color="#BDBDBD"),
        *analog_hands(pal, "#FFFFFF", pal.clock(LIGHT), pal.right(), hour=(100, 22),
                      minute=(160, 14), second=(170, 4, 30)),
        active_only(center_cap("#FFFFFF", pal.right(), 10, 4)),
    ]


# =====================================================================================
# 21  Halo - a gradient ring fills with the minutes
# =====================================================================================

@style(21, "halo", "Halo", category="eccentric", palette=(39, 2, 36), preview_time="10:38:30",
       description="A thick gradient ring fills around the time as the hour passes.")
def halo(ctx):
    pal = ctx.pal
    cx, cy, r, t = CX, 270, 124, 26
    sweep = "[MINUTE] * 6 + [SECOND] * 0.1"
    # WFF v1 gradients only take literal colours, so wear4 gets a solid ring
    grad = E("SweepGradient", centerX=cx, centerY=cy, startAngle=-20, endAngle=340,
             colors=f"{pal.left()} {pal.clock()}", positions="0 1") if ctx.v2 else None
    progress = part_draw(E("Arc", E("Stroke", grad, color=pal.clock(), thickness=t, cap="ROUND"),
                           transform("endAngle", sweep), centerX=cx, centerY=cy,
                           width=2 * r, height=2 * r, startAngle=0, endAngle=0))
    tip = group("tip", part_draw(circle(CX, cy - r, 7, fill_color="#FFFFFF")),
                transform("angle", sweep), x=0, y=0, w=450, h=2 * cy, pivotX=0.5, pivotY=0.5)
    return [
        active_only(part_draw(circle(cx, cy, r, stroke_color=pal.clock(CONTAINER),
                                     thickness=t))),
        active_only(progress),
        ambient_only(part_draw(arc(cx, cy, 2 * r, 0, 0, pal.clock(DARK), 4,
                                   kids=[transform("endAngle", sweep)]))),
        active_only(tip),
        *dual_time("hh", 0, cy - 92, 450, 96, 96, pal.clock(LIGHT), "BLACK"),
        *dual_time("mm", 0, cy - 2, 450, 96, 96, "#FFFFFF", "BLACK"),
        C.date_text(172, 48, 106, 32, 26, C.SHORT_DATE, color=pal.clock(LIGHT), weight="BOLD"),
        C.battery_text(172, 82, 106, 28, 20, color="#BDBDBD"),
    ]


# =====================================================================================
# Lab - renderer experiments, never shipped
# =====================================================================================

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve"]


def _lookup(expr, values):
    out = '""'
    for i in reversed(range(len(values))):
        out = f'({expr}) == {i} ? "{values[i]}" : {out}'
    return out


@style(99, "lab", "Lab", category="lab", palette=(0, 26, 36), enabled=False)
def lab(ctx):
    pal = ctx.pal
    weights = ["THIN", "LIGHT", "NORMAL", "MEDIUM", "BOLD", "BLACK"]
    kids = []
    for i, wgt in enumerate(weights):
        x = 40 + i * 63
        kids.append(part_draw(rect(0, 0, 60, 60, stroke_color="#444444", thickness=1),
                              x=x, y=160, w=60, h=60))
        kids.append(part_text(x, 160, 60, 60, "08", size=48, weight=wgt, color=pal.clock()))
    # condensed + letter spacing
    kids.append(part_text(40, 225, 370, 50, "10:08 COND", size=44, weight="BOLD",
                          font_width="CONDENSED", color=pal.clock(LIGHT)))
    # mask test: circle mask over stripes
    stripes = part_draw(*[rect(i * 20, 0, 10, 120, fill_color=pal.left()) for i in range(6)],
                        x=40, y=285, w=120, h=120)
    mask = part_draw(circle(60, 60, 50, fill_color="#FFFFFF"), x=40, y=285, w=120, h=120,
                     renderMode="MASK")
    kids.append(group("mask_test", mask, stripes))
    # expressions: words, modulo, floor
    kids.append(part_text(170, 285, 240, 40, "%s|%s|%s",
                          _lookup("[HOUR_1_12]", WORDS),
                          "[MINUTE] % 10", "floor([MINUTE] / 10)",
                          size=30, color=pal.right()))
    # circular text along the bottom edge
    kids.append(circular_text(CX, CY, 400, 120, 240, "%s", C.FULL_DATE, size=26,
                              color=pal.clock(LIGHT), direction="COUNTER_CLOCKWISE",
                              localize=True))
    # hand test
    kids.append(hand("hour", 100, 16, pal.clock(), HOUR_ANGLE))
    kids.append(hand("minute", 170, 8, pal.clock(LIGHT), MINUTE_ANGLE, alpha=180))
    # container swatches
    kids.append(part_draw(*[rrect(i * 36, 0, 30, 30, 8, fill_color=c) for i, c in enumerate(
        [pal.clock(t) for t in range(4)] + [pal.left(t) for t in range(4)])],
        x=80, y=335, w=290, h=30))
    return kids


@style(98, "lab2", "Lab 2", category="lab", palette=(0, 26, 36), enabled=False)
def lab2(ctx):
    pal = ctx.pal
    kids = []
    # circular text probes: (start, end, direction, colour)
    probes = [(0, 60, "CLOCKWISE", "#FF5252", "A cw 0-60"),
              (90, 150, "CLOCKWISE", "#FFD740", "B cw 90-150"),
              (240, 120, "COUNTER_CLOCKWISE", "#69F0AE", "C ccw 240-120"),
              (300, 240, "COUNTER_CLOCKWISE", "#40C4FF", "D ccw 300-240")]
    for start, end, direction, color, label in probes:
        kids.append(circular_text(CX, CY, 410, start, end, label, size=22, color=color,
                                  direction=direction))
    # rotating ring of labels, rotated by a transform
    ring = [part_text(*(lambda p: (p[0] - 20, p[1] - 14))(polar(150, i * 30)), 40, 28,
                      f"{i * 5:02d}", size=22, color=pal.clock(LIGHT),
                      angle=i * 30) for i in range(12)]
    kids.append(group("ring", *ring, transform("angle", "-([MINUTE] * 6)")))
    # sector fill via thick arc
    kids.append(part_draw(arc(CX, CY, 100, 0, 0, pal.left(CONTAINER), 100, cap="BUTT",
                              kids=[transform("endAngle", "[MINUTE] * 6")])))
    # alpha transform
    kids.append(part_draw(circle(CX, CY, 20, fill_color=pal.right()),
                          transform("alpha", "[SECOND] % 2 == 0 ? 255 : 60")))
    kids.append(time_text("hh", 0, 300, 450, 90, 90, color=pal.clock(), weight="BLACK"))
    return kids


@style(97, "lab3", "Lab 3", category="lab", palette=(3, 26, 36), enabled=False)
def lab3(ctx):
    pal = ctx.pal
    stripes = lambda x, y: part_draw(*[rect(i * 20, 0, 10, 120, fill_color=pal.left())
                                       for i in range(6)], x=x, y=y, w=120, h=120)
    # A: static circle mask over PartText
    a = group("a", part_draw(circle(60, 60, 45, fill_color="#FFFFFF"), x=40, y=160, w=120,
                             h=120, renderMode="MASK"),
              part_text(40, 160, 120, 120, "88", size=100, weight="BLACK", color=pal.clock()))
    # B: transformed rect mask over stripes (should show lower half only)
    b = group("b", part_draw(rect(0, 0, 120, 120, fill_color="#FFFFFF",
                                  kids=[transform("y", "60")]), x=165, y=160, w=120, h=120,
                             renderMode="MASK"),
              stripes(165, 160))
    # C: text as mask over a rect
    c = group("c", part_text(290, 160, 120, 120, "88", size=100, weight="BLACK",
                             color="#FFFFFF", renderMode="MASK"),
              part_draw(rect(0, 60, 120, 60, fill_color=pal.right()), x=290, y=160, w=120,
                        h=120))
    # D: PartDraw-level mask: transformed rect mask whose PartDraw is full size
    d = group("d", part_draw(rect(0, 450, 450, 450, fill_color="#FFFFFF",
                                  kids=[transform("y", "350")]), renderMode="MASK"),
              part_draw(rect(0, 0, 450, 450, fill_color=pal.clock(CONTAINER))),
              part_text(0, 300, 450, 100, "MASKED", size=60, weight="BLACK", color=pal.clock()))
    def masked(name, x, expr, wrap):
        g = group(name, part_draw(rect(0, 450, 120, 450, fill_color="#FFFFFF",
                                       kids=[transform("y", expr)]), x=x, y=0, w=120, h=450,
                                  renderMode="MASK"),
                  part_draw(rect(0, 0, 120, 450, fill_color=pal.clock(CONTAINER)), x=x, y=0,
                            w=120, h=450),
                  part_text(x, 300, 120, 100, "88", size=60, weight="BLACK", color=pal.clock()))
        return active_only(g) if wrap else g
    # E: constant transform + active_only; F: time transform, no wrapper
    # H: static circle mask over dynamic text
    h = group("h", part_draw(circle(60, 60, 45, fill_color="#FFFFFF"), x=40, y=300, w=120,
                             h=120, renderMode="MASK"),
              part_text(40, 300, 120, 120, "%s", "[MINUTE_Z]", size=100, weight="BLACK",
                        color=pal.clock()))
    # I: dynamic text as mask over a rect
    i = group("i", part_text(290, 300, 120, 120, "%s", "[MINUTE_Z]", size=100, weight="BLACK",
                             color="#FFFFFF", renderMode="MASK"),
              part_draw(rect(0, 60, 120, 60, fill_color=pal.right()), x=290, y=300, w=120,
                        h=120))
    # J: static text with a full-size transformed mask, liquid style
    j = group("j", part_draw(rect(0, 450, 120, 450, fill_color="#FFFFFF",
                                  kids=[transform("y", "360")]), x=165, y=0, w=120, h=450,
                             renderMode="MASK"),
              part_text(165, 300, 120, 120, "88", size=100, weight="BLACK", color=pal.left()))
    return [a, b, c, h, i, j]
