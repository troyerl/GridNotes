"""Tests for gridnotes.legal.user_notice."""

from gridnotes.legal.user_notice import (
    COPYRIGHT_HOLDER,
    PRODUCT_NAME,
    data_privacy_html,
    disclaimer_html,
    iracing_notice_html,
    license_summary_html,
    using_gridnotes_html,
)


def test_license_summary_mentions_personal_use():
    html = license_summary_html()
    assert "personal use" in html.lower()
    assert COPYRIGHT_HOLDER in html
    assert PRODUCT_NAME in html


def test_using_gridnotes_local_storage():
    html = using_gridnotes_html()
    assert "local" in html.lower()
    assert "cheat" not in html or "Not intended" in html


def test_iracing_notice_not_affiliated():
    html = iracing_notice_html()
    assert "not affiliated" in html.lower()
    assert "iracing.com" in html


def test_data_privacy_local_db():
    html = data_privacy_html()
    assert "sqlite" in html.lower() or "local" in html.lower()


def test_disclaimer_not_legal_advice():
    html = disclaimer_html()
    assert "not legal advice" in html.lower()
