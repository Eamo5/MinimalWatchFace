"""Building blocks shared between styles: date/weather line, battery, etc."""
from wff import E, bool_config, condition, group, part_text

WEEKDAY_DATE = 'icuText("MMMdE")'
FULL_DATE = 'icuText("MMMMdEEEE")'
SHORT_DATE = 'icuText("EEEd")'
DAY_NUMBER = 'icuText("d")'
WEEKDAY = 'icuText("EEE")'
MONTH = 'icuText("MMM")'

WEATHER_TEMP = "[WEATHER.TEMPERATURE]"
WEATHER_UNIT = '[WEATHER.TEMPERATURE_UNIT] == 1 ? "C" : "F"'
WEATHER_ICON = "[WEATHER.CONDITION] <= 15 ? [WEATHER.CONDITION] : 0"


def date_text(x, y, w, h, size, skeleton=FULL_DATE, color=None, weight=None, align="CENTER",
              upper=False, **kw):
    return part_text(x, y, w, h, "%s", skeleton, size=size, color=color, weight=weight,
                     align=align, ellipsis="TRUE", localize=True, **kw)


def weather_icon(x, y, size, color=None):
    """Day/night weather condition glyph from the bitmap fonts (WFF v2+)."""
    def glyph(family):
        return E("PartText",
                 E("Text", E("BitmapFont",
                             E("Template", E("Parameter", expression=WEATHER_ICON), text="%s"),
                             family=family, size=size)),
                 x=0, y=0, width=size, height=size, tintColor=color)
    return group("weather_icon", condition(
        [("is_day", "[WEATHER.IS_DAY]", [glyph("weather_icons_day")])],
        default=[glyph("weather_icons_night")]), x=x, y=y, w=size, h=size)


def weather_temp(x, y, w, h, size, color=None, weight=None, align="START", unit=True):
    if unit:
        return part_text(x, y, w, h, "%s° %s", WEATHER_TEMP, WEATHER_UNIT, size=size,
                         color=color, weight=weight, align=align)
    return part_text(x, y, w, h, "%s°", WEATHER_TEMP, size=size, color=color, weight=weight,
                     align=align)


def info_line(ctx, y, size=31, color=None, weight=None, x=0, w=450, short=WEEKDAY_DATE,
              full=FULL_DATE, h=None):
    """The classic 'date · weather' line: short date + icon + temperature when weather is
    available and enabled, otherwise the full date."""
    h = h or round(size * 1.5)
    full_line = date_text(x, y, w, h, size, full, color, weight)
    if not ctx.weather:
        return full_line
    icon = h
    icon_x = w / 2 + round(size * 0.35)
    temp_x = icon_x + icon + 9
    available = group(
        "weather_available",
        date_text(0, 0, w / 2, h, size, short, color, weight, align="END"),
        weather_icon(icon_x, (h - icon) / 2, icon),
        weather_temp(temp_x, 0, w - temp_x, h, size, color, weight),
        x=x, y=y, w=w, h=h)
    return bool_config(
        "show_weather",
        [group("weather_line", condition(
            [("is_weather_available", "[WEATHER.IS_AVAILABLE]", [available])],
            default=[full_line]), x=0, y=0, w=450, h=450)],
        [full_line])


def weather_if_enabled(ctx, children, fallback=None):
    """Children shown only when weather is enabled and available; fallback otherwise."""
    if not ctx.weather:
        return fallback
    inner = condition([("is_weather_available", "[WEATHER.IS_AVAILABLE]", children)],
                      default=fallback if fallback else None)
    return bool_config("show_weather", [group("weather", inner)], fallback)


def battery(children):
    return bool_config("show_battery_percentage", children)


def battery_text(x, y, w, h, size, color=None, weight=None, align="CENTER", fmt="%s%%"):
    return battery([part_text(x, y, w, h, fmt, "[BATTERY_PERCENT]", size=size, color=color,
                              weight=weight, align=align)])
