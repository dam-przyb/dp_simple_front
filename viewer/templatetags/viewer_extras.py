import json

from django import template

register = template.Library()


@register.filter
def tojson(value):
    """Serialize value for inline Alpine x-data arguments."""
    return json.dumps(value)


@register.filter
def picksmeta(picks):
    """Return light pick metadata used by report filtering logic."""
    return [
        {
            "side": pick.get("side", ""),
            "ticker": pick.get("ticker", ""),
            "name": pick.get("name", ""),
        }
        for pick in (picks or [])
    ]
