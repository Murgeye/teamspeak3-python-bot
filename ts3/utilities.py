__author__ = 'fabian'

# FROM OLD API
_ESCAPE_MAP = [
    ("\\", r"\\"),
    ("/", r"\/"),
    (" ", r"\s"),
    ("|", r"\p"),
    ("\a", r"\a"),
    ("\b", r"\b"),
    ("\f", r"\f"),
    ("\n", r"\n"),
    ("\r", r"\r"),
    ("\t", r"\t"),
    ("\v", r"\v")
    ]


def escape(raw):
    for char, replacement in _ESCAPE_MAP:
        raw = raw.replace(char, replacement)
    return raw


def unescape(raw):
    for replacement, char in reversed(_ESCAPE_MAP):
        raw = raw.replace(char, replacement)
    return raw
