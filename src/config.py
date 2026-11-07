import os
from pathlib import Path

import yaml


def load_config(path: str | Path) -> dict:
    """Read config.yaml and resolve its paths relative to the file.

    The environment variable MICROGRAPHS_DIR, when set, overrides paths.dataset.
    """
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text())
    if os.environ.get("MICROGRAPHS_DIR"):
        cfg["paths"]["dataset"] = os.environ["MICROGRAPHS_DIR"]
    cfg["paths"] = {name: path.parent / Path(value).expanduser() for name, value in cfg["paths"].items()}
    return cfg
