import pytest

from rosetta_core.human_doc import (
    render_human_doc,
    extract_fields_comment,
    extract_schema_ver_comment,
    extract_notes,
    MalformedRosettaDoc,
)

FIELDS = {"TASK": "ENTITY_RESOLUTION", "ID_THRESHOLD": 0.92}
DESCRIPTIONS = {"TASK": "Task", "ID_THRESHOLD": "Identity match threshold"}


def test_render_includes_markers_and_bullets():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="Escalate ambiguous cases.")
    assert "<!-- ROSETTA:AUTO-GENERATED" in doc
    assert "<!-- /ROSETTA:AUTO-GENERATED -->" in doc
    assert "<!-- ROSETTA:NOTES" in doc
    assert "- Identity match threshold: 0.92" in doc
    assert "Escalate ambiguous cases." in doc


def test_extract_fields_comment_round_trips():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="")
    assert extract_fields_comment(doc) == FIELDS


def test_extract_schema_ver_comment_round_trips():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="")
    assert extract_schema_ver_comment(doc) == "1.0"


def test_extract_notes_round_trips():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="Escalate ambiguous cases.")
    assert extract_notes(doc) == "Escalate ambiguous cases."


def test_notes_region_is_editable_independent_of_fields():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="original")
    hand_edited = doc.replace("original", "analyst added a caveat here")
    assert extract_notes(hand_edited) == "analyst added a caveat here"
    assert extract_fields_comment(hand_edited) == FIELDS


def test_extract_fields_comment_raises_on_missing_marker():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="")
    malformed = doc.replace("<!-- ROSETTA:FIELDS ", "no marker here ")
    with pytest.raises(MalformedRosettaDoc, match="ROSETTA:FIELDS"):
        extract_fields_comment(malformed)


def test_extract_schema_ver_comment_raises_on_missing_marker():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="")
    malformed = doc.replace("<!-- ROSETTA:SCHEMA_VER ", "no marker here ")
    with pytest.raises(MalformedRosettaDoc, match="ROSETTA:SCHEMA_VER"):
        extract_schema_ver_comment(malformed)


def test_extract_notes_raises_on_missing_marker():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="Escalate ambiguous cases.")
    malformed = doc.replace("<!-- ROSETTA:NOTES", "no marker here")
    with pytest.raises(MalformedRosettaDoc, match="ROSETTA:NOTES"):
        extract_notes(malformed)
