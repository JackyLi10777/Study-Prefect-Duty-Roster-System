"""
Tests for the import pipeline: CSV parsing, column mapping, validation, and
the new confidence-aware mapping functions.
"""
import pytest
from app.utils.importers import (
    parse_csv,
    get_sample_rows,
    map_columns,
    smart_import,
    validate_import_rows,
    auto_detect_columns,
    normalize_column_name,
    compute_mapping_with_confidence,
    get_preview_rows,
)


class TestParseCSV:
    def test_parse_csv_basic(self):
        content = "name,form,class_name\nAlice,F4,4A\nBob,F5,5B"
        cols, rows = parse_csv(content)
        assert cols == ["name", "form", "class_name"]
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[1]["name"] == "Bob"

    def test_parse_csv_empty(self):
        cols, rows = parse_csv("")
        assert cols == []
        assert rows == []

    def test_get_sample_rows(self):
        content = "name,form\nAlice,F4\nBob,F5\nCharlie,F3"
        sample = get_sample_rows(content, 2)
        assert "name" in sample
        assert "Alice" in sample

class TestColumnMapping:
    def test_auto_detect_columns_matches_alias(self):
        raw = ["Student Name", "Grade", "Class"]
        mapping = auto_detect_columns(raw)
        assert mapping["name"] == "Student Name"
        assert mapping["form"] == "Grade"

    def test_normalize_column_name_known(self):
        assert normalize_column_name("Full Name") == "name"
        assert normalize_column_name("Year") == "form"
        assert normalize_column_name("Position") == "role"

    def test_normalize_column_name_unknown(self):
        assert normalize_column_name("RandomCol") == "RandomCol"  # unknown returns original

    def test_map_columns_applies_mapping(self):
        raw_rows = [{"Student Name": "Alice", "Grade": "F4"}]
        mapping = {"name": "Student Name", "form": "Grade"}
        result = map_columns(raw_rows, mapping)
        assert result[0]["name"] == "Alice"
        assert result[0]["form"] == "F4"

class TestValidateImport:
    def test_validate_import_rows_rejects_missing_name(self):
        rows = [{"form": "F4", "role": "STUDY_PREFECT"}]
        valid, errors = validate_import_rows(rows)
        assert len(valid) == 0
        assert len(errors) == 1
        assert "missing name" in errors[0].lower()

    def test_validate_import_rows_accepts_valid(self):
        rows = [{"name": "Alice", "form": "F4", "role": "STUDY_PREFECT"}]
        valid, errors = validate_import_rows(rows)
        assert len(valid) == 1
        assert valid[0]["name"] == "Alice"

    def test_validate_sets_defaults(self):
        rows = [{"name": "Bob", "form": "F5", "role": "Assistant Head Prefect"}]
        valid, _ = validate_import_rows(rows)
        assert valid[0]["role"] == "ASSISTANT_HEAD_PREFECT"
        assert valid[0]["active"] is True

class TestConfidenceMapping:
    def test_compute_mapping_confidence_pure_alias(self):
        """Without AI available, all mapped columns get alias confidence."""
        cols = ["Name", "Form"]
        result = compute_mapping_with_confidence(cols, "")
        assert len(result) == 2
        confs = {r["source_col"]: r["confidence"] for r in result}
        assert confs["Name"] == "alias"
        assert confs["Form"] == "alias"

    def test_compute_mapping_confidence_unmapped(self):
        cols = ["UnmappedColumn", "AnotherOne"]
        result = compute_mapping_with_confidence(cols, "")
        for r in result:
            assert r["confidence"] == "none"
            assert r["target"] is None

    def test_get_preview_rows(self):
        content = "name,form,class_name\nAlice,F4,4A\nBob,F5,5B\nCharlie,F3,3C"
        mapping = {"name": "name", "form": "form", "class_name": "class_name"}
        preview = get_preview_rows(content, mapping, n=2)
        assert len(preview) == 2
        assert preview[0]["name"] == "Alice"
        assert preview[1]["name"] == "Bob"

print("All tests defined successfully")
