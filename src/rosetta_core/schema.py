import jsonschema


class SchemaValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _coerce_to_schema_types(fields: dict, schema: dict) -> dict:
    """Return a copy of ``fields`` with string values coerced to the numeric
    type declared for that property in ``schema``, where possible.

    CPN packets always parse field values as plain strings, so a value that
    is semantically a number (e.g. "0.95") arrives as the string "0.95".
    JSON Schema's "number"/"integer" types expect real numeric values, so
    without this bridge every schema with a numeric field would fail
    validation for input parsed from a .cpn packet. If a string can't be
    converted, it is left as-is so jsonschema still reports a genuine type
    error for actually-bad data.
    """
    properties = schema.get("properties", {})
    coerced = dict(fields)
    for key, value in fields.items():
        if key not in properties or not isinstance(value, str):
            continue
        declared_type = properties[key].get("type")
        if declared_type == "number":
            try:
                coerced[key] = float(value)
            except ValueError:
                pass
        elif declared_type == "integer":
            try:
                coerced[key] = int(value)
            except ValueError:
                pass
    return coerced


def validate_fields(fields: dict, schema: dict) -> None:
    coerced_fields = _coerce_to_schema_types(fields, schema)
    validator = jsonschema.Draft7Validator(schema)
    found = sorted(validator.iter_errors(coerced_fields), key=lambda e: list(e.path))
    if found:
        messages = [
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
            for e in found
        ]
        raise SchemaValidationError(messages)
