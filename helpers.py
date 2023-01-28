STR_TO_BOOL_MAPPINGS = {
    "y": True,
    "yes": True,
    "true": True,
    "on": True,
    "1": True,
    "n": False,
    "no": False,
    "false": False,
    "off": False,
    "0": False,
}


def strtobool(value):
    """
    Converts a string to a boolean.
    :returns Respective boolean of the given string
    :raises ValueError
    """
    try:
        return STR_TO_BOOL_MAPPINGS[str(value).lower()]
    except KeyError:
        # pylint: disable=raise-missing-from
        raise ValueError(f"'{value}' is not a valid boolean value.")
