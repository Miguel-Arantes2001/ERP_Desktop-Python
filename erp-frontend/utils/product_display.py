import re

PLACEHOLDER_DESCRIPTIONS = {"sem descrição"}


def clean_name(value) -> str:
    return (value or "").strip()


def clean_description(value) -> str:
    text = (value or "").strip()
    if not text or text.casefold() in PLACEHOLDER_DESCRIPTIONS:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def display_name(name: str, *, title_case: bool = False) -> str:
    cleaned = clean_name(name)
    if title_case:
        return cleaned.title()
    return cleaned


def name_with_description(name: str, description: str | None = None, *, title_case: bool = False) -> str:
    label = display_name(name, title_case=title_case)
    desc = clean_description(description)
    if desc:
        return f"{label}\n{desc}"
    return label


def name_tooltip(name: str, description: str | None = None, *, title_case: bool = False) -> str:
    label = display_name(name, title_case=title_case)
    desc = clean_description(description)
    if desc:
        return f"{label}\n\nDescrição: {desc}"
    return label
