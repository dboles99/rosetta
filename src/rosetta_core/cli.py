import argparse
import json
import sys
from pathlib import Path

from .fields import FieldsStore
from .human_doc import extract_notes, render_human_doc
from .schema import SchemaValidationError, validate_fields
from .sync import SyncConflict, sync


def _default_title(name: str) -> str:
    return name.replace("_", " ").title()


def _run_sync(name: str, directory: Path) -> int:
    try:
        result = sync(name, directory, _default_title(name), field_descriptions={})
    except SyncConflict as exc:
        print(f"CONFLICT: {exc}", file=sys.stderr)
        return 1
    print(f"sync: {result}")
    return 0


def _run_validate(name: str, directory: Path) -> int:
    store = FieldsStore.load(directory / f"{name}.fields.json")
    schema = json.loads((directory / f"{name}.schema.json").read_text(encoding="utf-8"))
    try:
        validate_fields(store.fields_with_schema_ver(), schema)
    except SchemaValidationError as exc:
        for message in exc.errors:
            print(f"INVALID: {message}", file=sys.stderr)
        return 1
    print("valid")
    return 0


def _run_expand(name: str, directory: Path) -> int:
    store = FieldsStore.load(directory / f"{name}.fields.json")
    md_path = directory / f"{name}.md"
    notes = extract_notes(md_path.read_text(encoding="utf-8")) if md_path.exists() else ""
    print(render_human_doc(_default_title(name), store.schema_ver, store.fields, field_descriptions={}, notes=notes))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rosetta")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name in ("sync", "compile", "validate", "expand"):
        sub = subparsers.add_parser(command_name)
        sub.add_argument("name")
        sub.add_argument("--dir", default=".")

    args = parser.parse_args(argv)
    directory = Path(args.dir)

    if args.command in ("sync", "compile"):
        return _run_sync(args.name, directory)
    if args.command == "validate":
        return _run_validate(args.name, directory)
    if args.command == "expand":
        return _run_expand(args.name, directory)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
