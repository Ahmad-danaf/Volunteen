from django import template
register = template.Library()

@register.filter
def hebrew_weekday(value):
    """
    Convert integer weekday (Monday = 0 … Sunday = 6) to Hebrew name.
    """
    names = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
    try:
        return names[int(value)]
    except (ValueError, IndexError):
        return ""
