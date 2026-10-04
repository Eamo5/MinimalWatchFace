"""Small builder helpers for Watch Face Format (WFF) XML elements."""
import math
import xml.etree.ElementTree as ET

W = H = 450
CX = CY = 225


def _fmt(v):
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def _flatten(items):
    for item in items:
        if item is None or item is False:
            continue
        if isinstance(item, (list, tuple)):
            yield from _flatten(item)
        else:
            yield item


# Containers whose geometry attributes must be integers.
_INT_GEOMETRY = {"Group", "PartText", "PartDraw", "PartImage", "DigitalClock", "TimeText",
                 "AnalogClock", "ComplicationSlot"}
_GEOMETRY = {"x", "y", "width", "height"}


def E(tag, *children, text=None, **attrs):
    """Create an element. Attribute names ending in '_' have it stripped (e.g. id_)."""
    if tag in _INT_GEOMETRY:
        attrs = {k: round(v) if k in _GEOMETRY and isinstance(v, float) else v
                 for k, v in attrs.items()}
    el = ET.Element(tag, {k.rstrip("_"): _fmt(v) for k, v in attrs.items() if v is not None})
    if text is not None:
        el.text = text
    for child in _flatten(children):
        el.append(child)
    return el


# ---------------------------------------------------------------- structure

def group(name, *children, x=0, y=0, w=W, h=H, **kw):
    return E("Group", *children, name=name, x=x, y=y, width=w, height=h, **kw)


def transform(target, value):
    return E("Transform", target=target, value=value)


def ambient(target, value):
    return E("Variant", mode="AMBIENT", target=target, value=value)


def hide_in_ambient():
    return ambient("alpha", 0)


def show_in_ambient_only():
    """Use with alpha=0 on the element."""
    return ambient("alpha", 255)


def condition(cases, default=None):
    """cases: list of (name, expression, children)."""
    exprs = E("Expressions", *[E("Expression", name=n, text=expr) for n, expr, _ in cases])
    compares = [E("Compare", *kids, expression=n) for n, _, kids in cases]
    return E("Condition", exprs, *compares, E("Default", *default) if default else None)


def _single(children, name):
    """BooleanOption / ListOption accept exactly one child; wrap several in a Group."""
    children = list(_flatten(children))
    return children[0] if len(children) == 1 else group(name, *children)


def bool_config(cid, true_children=None, false_children=None):
    return E("BooleanConfiguration",
             E("BooleanOption", _single(true_children, f"{cid}_on"), id_="TRUE")
             if true_children else None,
             E("BooleanOption", _single(false_children, f"{cid}_off"), id_="FALSE")
             if false_children else None,
             id_=cid)


# ---------------------------------------------------------------- drawing

def stroke(color, thickness, cap=None, dash=None, *children):
    return E("Stroke", *children, color=color, thickness=thickness, cap=cap, dashIntervals=dash)


def fill(color, *children):
    return E("Fill", *children, color=color)


def part_draw(*shapes, x=0, y=0, w=W, h=H, name=None, **kw):
    return E("PartDraw", *shapes, name=name, x=x, y=y, width=w, height=h, **kw)


def ellipse(x, y, w, h, fill_color=None, stroke_color=None, thickness=None, kids=()):
    return E("Ellipse",
             fill(fill_color) if fill_color else None,
             stroke(stroke_color, thickness) if stroke_color else None,
             *kids, x=x, y=y, width=w, height=h)


def circle(cx, cy, r, fill_color=None, stroke_color=None, thickness=None, kids=()):
    return ellipse(cx - r, cy - r, 2 * r, 2 * r, fill_color, stroke_color, thickness, kids)


def rect(x, y, w, h, fill_color=None, stroke_color=None, thickness=None, kids=()):
    return E("Rectangle",
             fill(fill_color) if fill_color else None,
             stroke(stroke_color, thickness) if stroke_color else None,
             *kids, x=x, y=y, width=w, height=h)


def rrect(x, y, w, h, r, fill_color=None, stroke_color=None, thickness=None, kids=()):
    r = min(r, w / 2, h / 2)
    return E("RoundRectangle",
             fill(fill_color) if fill_color else None,
             stroke(stroke_color, thickness) if stroke_color else None,
             *kids, x=x, y=y, width=w, height=h, cornerRadiusX=r, cornerRadiusY=r)


def arc(cx, cy, d, start, end, color, thickness, cap="ROUND", kids=(), dh=None, direction=None):
    return E("Arc", stroke(color, thickness, cap), *kids, centerX=cx, centerY=cy, width=d,
             height=dh if dh is not None else d, startAngle=start, endAngle=end,
             direction=direction)


def line(x1, y1, x2, y2, color, thickness, cap="ROUND", kids=()):
    return E("Line", stroke(color, thickness, cap), *kids, startX=x1, startY=y1, endX=x2, endY=y2)


def polar(r, deg, cx=CX, cy=CY):
    """Point at radius r, angle in degrees clockwise from 12 o'clock."""
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


# ---------------------------------------------------------------- text

DEVICE_FONT = "SYNC_TO_DEVICE"


def font(size, color=None, weight=None, family=DEVICE_FONT, *children, width=None,
         slant=None, letter_spacing=None, text=None):
    return E("Font", *children, family=family, size=size, color=color, weight=weight,
             width=width, slant=slant, letterSpacing=letter_spacing, text=text)


def template(fmt, *exprs):
    return E("Template", *[E("Parameter", expression=e) for e in exprs], text=fmt)


def part_text(x, y, w, h, fmt, *exprs, size=30, color=None, weight=None, align="CENTER",
              family=DEVICE_FONT, ellipsis=None, localize=False, extra=(), font_width=None,
              letter_spacing=None, **kw):
    """A PartText showing a template. Strings with no expressions are rendered literally."""
    body = template(fmt, *exprs) if exprs else None
    f = font(size, color, weight, family, body, width=font_width, letter_spacing=letter_spacing,
             text=None if exprs else fmt)
    return E("PartText",
             E("Localization") if localize else None,
             *extra,
             E("Text", f, align=align, ellipsis=ellipsis),
             x=x, y=y, width=w, height=h, **kw)


def circular_text(cx, cy, d, start, end, fmt, *exprs, size=26, color=None, weight=None,
                  align="CENTER", direction=None, x=0, y=0, w=W, h=H, localize=False, extra=(),
                  letter_spacing=None, **kw):
    body = template(fmt, *exprs) if exprs else None
    f = font(size, color, weight, DEVICE_FONT, body, letter_spacing=letter_spacing,
             text=None if exprs else fmt)
    return E("PartText",
             E("Localization") if localize else None,
             *extra,
             E("TextCircular", f, centerX=cx, centerY=cy, width=d, height=d, startAngle=start,
               endAngle=end, align=align, direction=direction),
             x=x, y=y, width=w, height=h, **kw)


def time_text(fmt, x, y, w, h, size, color="#FFFFFF", weight=None, align="CENTER",
              tint=None, variants=(), family=DEVICE_FONT, font_width=None, **kw):
    return E("DigitalClock",
             *variants,
             E("TimeText",
               E("Font", family=family, size=size, color=color, weight=weight, width=font_width),
               format=fmt, align=align, x=0, y=0, width=w, height=h),
             x=x, y=y, width=w, height=h, tintColor=tint, **kw)


# ---------------------------------------------------------------- expressions

HOUR_DISPLAY = "([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])"
HOUR_DISPLAY_Z = "([IS_24_HOUR_MODE] ? [HOUR_0_23_Z] : [HOUR_1_12])"
HOUR_ANGLE = "([HOUR_0_11] * 30 + [MINUTE] * 0.5)"
MINUTE_ANGLE = "([MINUTE] * 6 + [SECOND] * 0.1)"
MINUTE_ANGLE_STEP = "([MINUTE] * 6)"
SECOND_ANGLE = "([SECOND] * 6)"
SECOND_ANGLE_SMOOTH = "([SECOND_MILLISECOND] * 6)"


def hand(name, length, width, color, angle_expr, tail=0, outline=None, thickness=None,
         radius=None, ambient_alpha=None, alpha=None, cap_inset=0):
    """A rotating pill-shaped hand drawn as a RoundRectangle in a tight PartDraw.

    The PartDraw is sized to the hand and pivots on the watch center."""
    total = length + tail
    r = width / 2 if radius is None else radius
    pad = (thickness or 0)
    shape = rrect(pad, pad + cap_inset, width, total - cap_inset, r,
                  fill_color=None if outline else color,
                  stroke_color=outline, thickness=thickness)
    pw = width + 2 * pad
    ph = total + 2 * pad
    return part_draw(
        shape,
        transform("angle", angle_expr),
        ambient("alpha", ambient_alpha) if ambient_alpha is not None else None,
        name=name, x=CX - pw / 2, y=CY - length - pad, w=pw, h=ph,
        pivotX=0.5, pivotY=(length + pad) / ph, alpha=alpha,
    )


def write(root, path):
    ET.indent(root, space="    ")
    data = ET.tostring(root, encoding="unicode")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
        fh.write(data)
        fh.write("\n")
