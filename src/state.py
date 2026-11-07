"""Loop state kept in files, so a run survives restarts: results/state.json plus one directory per iteration."""

import json
from dataclasses import dataclass, field
from pathlib import Path


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n")


@dataclass
class State:
    root: Path
    iteration: int = 0
    history: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path) -> "State":
        file = root / "state.json"
        if not file.exists():
            return cls(root)
        data = json.loads(file.read_text())
        return cls(root, data["iteration"], data["history"])

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        write_json(self.root / "state.json", {"iteration": self.iteration, "history": self.history})

    def start_iteration(self) -> Path:
        """Open the directory of the next iteration.

        The counter is saved only when the iteration is recorded,
        so a crashed iteration is redone in the same directory on the next run.
        """
        self.iteration += 1
        it_dir = self.root / f"iter_{self.iteration:03d}"
        it_dir.mkdir(parents=True, exist_ok=True)
        return it_dir
