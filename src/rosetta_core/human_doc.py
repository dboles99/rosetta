import json

AUTO_START = "<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->"
AUTO_END = "<!-- /ROSETTA:AUTO-GENERATED -->"
FIELDS_COMMENT_PREFIX = "<!-- ROSETTA:FIELDS "
SCHEMA_VER_COMMENT_PREFIX = "<!-- ROSETTA:SCHEMA_VER "
COMMENT_SUFFIX = " -->"
NOTES_START = "<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->"
NOTES_END = "<!-- /ROSETTA:NOTES -->"


def render_human_doc(title: str, schema_ver: str, fields: dict, field_descriptions: dict, notes: str) -> str:
    lines = [
        AUTO_START,
        f"{FIELDS_COMMENT_PREFIX}{json.dumps(fields, sort_keys=True)}{COMMENT_SUFFIX}",
        f"{SCHEMA_VER_COMMENT_PREFIX}{schema_ver}{COMMENT_SUFFIX}",
        f"# {title}",
    ]
    for key in sorted(fields.keys()):
        description = field_descriptions.get(key, key)
        lines.append(f"- {description}: {fields[key]}")
    lines.append(AUTO_END)
    lines.append("")
    lines.append(NOTES_START)
    lines.append(notes.strip())
    lines.append(NOTES_END)
    return "\n".join(lines) + "\n"


def extract_fields_comment(doc_text: str) -> dict:
    start = doc_text.index(FIELDS_COMMENT_PREFIX) + len(FIELDS_COMMENT_PREFIX)
    end = doc_text.index(COMMENT_SUFFIX, start)
    return json.loads(doc_text[start:end])


def extract_schema_ver_comment(doc_text: str) -> str:
    start = doc_text.index(SCHEMA_VER_COMMENT_PREFIX) + len(SCHEMA_VER_COMMENT_PREFIX)
    end = doc_text.index(COMMENT_SUFFIX, start)
    return doc_text[start:end]


def extract_notes(doc_text: str) -> str:
    start = doc_text.index(NOTES_START) + len(NOTES_START)
    end = doc_text.index(NOTES_END)
    return doc_text[start:end].strip()
