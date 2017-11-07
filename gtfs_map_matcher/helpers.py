from pathlib import Path
import json


def get_secret(path, key):
    """
    Given a path (string or Path object)
    to a JSON dictionary of secrets,
    read it and return the value corresponding to the given key.
    """
    with Path(path).open() as src:
        secrets = json.load(src)
    return secrets[key]
