from pathlib import Path

from .cpn import parse_packet, serialize_packet
from .fields import FieldsStore
from .hashing import sha256_text
from .human_doc import (
    extract_fields_comment,
    extract_notes,
    extract_schema_ver_comment,
    render_human_doc,
)
from .lockfile import Lockfile


class SyncConflict(Exception):
    def __init__(self, differing_keys: list[str]):
        self.differing_keys = differing_keys
        super().__init__(f"conflicting fields: {', '.join(differing_keys)}")


def _differing_keys(human_fields: dict, machine_fields: dict) -> list[str]:
    all_keys = set(human_fields) | set(machine_fields)
    return sorted(
        key for key in all_keys
        if str(human_fields.get(key)) != str(machine_fields.get(key))
    )


def sync(name: str, directory: Path, title: str, field_descriptions: dict) -> str:
    fields_path = directory / f"{name}.fields.json"
    md_path = directory / f"{name}.md"
    cpn_path = directory / f"{name}.cpn"
    lock_path = directory / f"{name}.rosetta.lock"

    store = FieldsStore.load(fields_path)
    lock = Lockfile.load_or_default(lock_path)

    human_text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    machine_text = cpn_path.read_text(encoding="utf-8") if cpn_path.exists() else ""

    never_synced = lock.human_hash == "" and lock.machine_hash == ""
    if never_synced:
        new_machine = serialize_packet(store.schema_ver, store.fields)
        new_human = render_human_doc(title, store.schema_ver, store.fields, field_descriptions, notes="")
        cpn_path.write_text(new_machine, encoding="utf-8", newline="\n")
        md_path.write_text(new_human, encoding="utf-8", newline="\n")
        Lockfile(human_hash=sha256_text(new_human), machine_hash=sha256_text(new_machine)).save(lock_path)
        return "bootstrap"

    human_changed = sha256_text(human_text) != lock.human_hash
    machine_changed = sha256_text(machine_text) != lock.machine_hash

    if human_changed and machine_changed:
        human_fields = extract_fields_comment(human_text)
        _, machine_fields = parse_packet(machine_text)
        raise SyncConflict(_differing_keys(human_fields, machine_fields))

    if machine_changed:
        schema_ver, fields = parse_packet(machine_text)
        store.schema_ver = schema_ver
        store.fields = fields
        store.save(fields_path)
        notes = extract_notes(human_text)
        new_human = render_human_doc(title, store.schema_ver, store.fields, field_descriptions, notes)
        md_path.write_text(new_human, encoding="utf-8", newline="\n")
        Lockfile(human_hash=sha256_text(new_human), machine_hash=sha256_text(machine_text)).save(lock_path)
        return "machine-to-human"

    if human_changed:
        store.fields = extract_fields_comment(human_text)
        store.schema_ver = extract_schema_ver_comment(human_text)
        store.save(fields_path)
        new_machine = serialize_packet(store.schema_ver, store.fields)
        cpn_path.write_text(new_machine, encoding="utf-8", newline="\n")
        Lockfile(human_hash=sha256_text(human_text), machine_hash=sha256_text(new_machine)).save(lock_path)
        return "human-to-machine"

    return "no-op"
