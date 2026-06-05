"""Tests for gridnotes.data.note_tags."""

import json

from gridnotes.data.note_tags import (
    DEFAULT_NOTE_TAGS,
    NoteTag,
    chip_label,
    load_note_tags,
    save_note_tags,
)


def test_note_tag_append_text():
    tag = NoteTag("Clean", "Clean racer")
    assert tag.append_text() == "Clean racer"
    assert NoteTag("Solo", "").append_text() == "Solo"


def test_chip_label():
    assert chip_label("Clean") == "+ Clean"
    assert chip_label("+Tag") == "+Tag"


def test_load_default_when_missing(file_db):
    db_path, _ = file_db
    tags = load_note_tags(db_name=db_path)
    assert len(tags) >= len(DEFAULT_NOTE_TAGS)
    assert tags[0].label


def test_save_and_load_custom_tags(file_db):
    db_path, _ = file_db
    custom = [NoteTag("Test", "Test note")]
    save_note_tags(custom, db_name=db_path)
    loaded = load_note_tags(db_name=db_path)
    assert loaded[0].label == "Test"


def test_load_invalid_json_falls_back(file_db, monkeypatch):
    db_path, _ = file_db
    from gridnotes.data.db import set_setting
    from gridnotes.data.note_tags import SETTING_KEY

    set_setting(SETTING_KEY, "{not json", db_name=db_path)
    tags = load_note_tags(db_name=db_path)
    assert len(tags) >= 1


def test_save_json_format(file_db):
    db_path, _ = file_db
    save_note_tags([NoteTag("X", "Y")], db_name=db_path)
    from gridnotes.data.db import get_setting
    from gridnotes.data.note_tags import SETTING_KEY

    raw = get_setting(SETTING_KEY, db_name=db_path)
    payload = json.loads(raw)
    assert payload[0]["label"] == "X"
