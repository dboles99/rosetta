import json
from pathlib import Path


class FieldsStore:
    def __init__(self, schema_ver: str, fields: dict):
        self.schema_ver = schema_ver
        self.fields = fields

    @classmethod
    def load(cls, path: Path) -> "FieldsStore":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(schema_ver=data["schema_ver"], fields=data["fields"])

    def save(self, path: Path) -> None:
        data = {"schema_ver": self.schema_ver, "fields": self.fields}
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    def fields_with_schema_ver(self) -> dict:
        return {**self.fields, "SCHEMA_VER": self.schema_ver}
