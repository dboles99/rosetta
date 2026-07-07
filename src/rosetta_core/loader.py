# src/rosetta_core/loader.py
from pathlib import Path

from .cpn import parse_packet
from .schema import SchemaValidationError, validate_fields


class PacketUnavailable(Exception):
    pass


def load_prompt(name: str, directory: Path, schema: dict) -> str:
    cpn_path = directory / f"{name}.cpn"
    md_path = directory / f"{name}.md"

    if cpn_path.exists():
        text = cpn_path.read_text(encoding="utf-8")
        try:
            schema_ver, fields = parse_packet(text)
            validate_fields({**fields, "SCHEMA_VER": schema_ver}, schema)
            return text
        except (ValueError, SchemaValidationError):
            pass

    if md_path.exists():
        return md_path.read_text(encoding="utf-8")

    raise PacketUnavailable(f"neither {cpn_path} nor {md_path} exists or is valid")
