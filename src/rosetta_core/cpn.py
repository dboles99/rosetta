# src/rosetta_core/cpn.py

def _canonicalize_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def serialize_packet(schema_ver: str, fields: dict) -> str:
    lines = [f"SCHEMA_VER={schema_ver}"]
    for key in sorted(fields.keys()):
        lines.append(f"{key}={_canonicalize_value(fields[key])}")
    return "\n".join(lines) + "\n"


def parse_packet(text: str) -> tuple[str, dict]:
    schema_ver = None
    fields: dict = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        key, sep, value = line.partition("=")
        if sep != "=":
            continue
        if key == "SCHEMA_VER":
            schema_ver = value
        else:
            fields[key] = value
    if schema_ver is None:
        raise ValueError("packet missing SCHEMA_VER")
    return schema_ver, fields
