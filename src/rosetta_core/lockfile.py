import json
from pathlib import Path


class Lockfile:
    def __init__(self, human_hash: str, machine_hash: str):
        self.human_hash = human_hash
        self.machine_hash = machine_hash

    @classmethod
    def load_or_default(cls, path: Path) -> "Lockfile":
        if not path.exists():
            return cls(human_hash="", machine_hash="")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(human_hash=data["human_hash"], machine_hash=data["machine_hash"])

    def save(self, path: Path) -> None:
        data = {"human_hash": self.human_hash, "machine_hash": self.machine_hash}
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
