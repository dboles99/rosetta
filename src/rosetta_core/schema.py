import jsonschema


class SchemaValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_fields(fields: dict, schema: dict) -> None:
    validator = jsonschema.Draft7Validator(schema)
    found = sorted(validator.iter_errors(fields), key=lambda e: list(e.path))
    if found:
        messages = [
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
            for e in found
        ]
        raise SchemaValidationError(messages)
