"""738 saved native replay and explicitly engineering HTML counterexamples.

Legacy snippets below are parser fixtures, never biological measurements.
All application imports run only inside the retained bounded529 environment.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ,
                                reason="requires bounded529 retained runtime")


def api():
    from gene_annotation_episode.addgene_sequence_native import (
        ADDGENE_SEQUENCE_PAGE_SCHEMA, read_addgene_sequences,
        validate_addgene_sequence_page,
    )
    return read_addgene_sequences, validate_addgene_sequence_page, ADDGENE_SEQUENCE_PAGE_SCHEMA


def read(html, complete=True):
    return api()[0](html.encode() if isinstance(html, str) else html,
                    source_ref="engineering:legacy-html", requested_id="50005",
                    response_complete=complete)


def legacy(text, *, section="addgene-full", sequence_id="17"):
    identity = f'data-sequence-id="{sequence_id}"' if sequence_id is not None else ""
    return (f'<section id="{section}"><div {identity}>'
            f'<textarea class="mono copy-from">{text}</textarea></div></section>')


def test_actual_saved_current_page_retains_three_authenticated_metadata_rows():
    base = Path(__file__).resolve().parents[1] / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check201_native739/sequence-support-native739"
    content = (base / "addgene50005.entity").read_bytes()
    provenance = json.loads((base / "addgene50005.json").read_text())
    assert len(content) == 211547
    assert hashlib.sha256(content).hexdigest() == "deb0393a4b1c71ae21e438a7dd2a6f410defbc83c3e939c2ce10faf0b4b30c4d"
    assert provenance["status"] == 200 and provenance["body_complete"] is True
    assert provenance["sha256"] == hashlib.sha256(content).hexdigest()
    assert provenance["size_bytes"] == len(content)
    assert provenance["request_method"] == "GET"
    page = api()[0](content, source_ref="saved:check201:addgene50005", requested_id="50005", response_complete=True)
    assert page["parse_status"] == "partial" and page["authentication_required"] is True
    assert [row["sequence_id"] for row in page["records"]] == ["513490", "91118", "91449"]
    assert [row["source_completeness"] for row in page["records"]] == ["full", "partial", "partial"]
    assert all(row["source_verification"] == "addgene_verified" for row in page["records"])
    assert [row["section_id"] for row in page["records"]] == ["addgene-full", "addgene-partial", "addgene-partial"]
    for row in page["records"]:
        assert row["sequence"] is row["native_sequence_text"] is row["native_header"] is None
        assert row["sequence_status"] == "authentication_required"
        assert len(row["locators"]) == 2
        assert all(locator["value"] == f'/browse/sequence/{row["sequence_id"]}/' for locator in row["locators"])
    assert "topology" not in json.dumps(page)
    assert api()[1](page) == page


def test_engineering_legacy_alternatives_and_literal_case_are_retained():
    html = legacy("&gt; Addgene NGS Result  \r\naCgT RYSW\nKMBDHVN", sequence_id="17")
    html += legacy("&gt; depositor original\nTTaa", section="depositor-partial", sequence_id="18")
    page = read(html)
    assert page["parse_status"] == "complete"
    assert [row["sequence"] for row in page["records"]] == ["aCgTRYSWKMBDHVN", "TTaa"]
    assert [row["sequence_id"] for row in page["records"]] == ["17", "18"]
    assert page["records"][0]["native_header"] == "> Addgene NGS Result  "
    assert page["records"][0]["native_sequence_text"] == "> Addgene NGS Result  \r\naCgT RYSW\nKMBDHVN"
    assert page["records"][1]["source_verification"] == "depositor"
    assert page["records"][1]["source_completeness"] == "partial"


@pytest.mark.parametrize("section,expected", [
    ("addgene-partial", ("partial", "addgene_verified")),
    ("depositor-full", ("full", "depositor")),
    ("other", ("unknown", "unknown")),
])
def test_engineering_categories_come_from_containing_native_section(section, expected):
    row = read(legacy("&gt; Addgene NGS Result full\nACGT", section=section))["records"][0]
    assert (row["source_completeness"], row["source_verification"]) == expected


def test_engineering_unidentified_legacy_literal_is_not_guessed_from_page_link():
    page = read('<section id="addgene-full"><a href="/browse/sequence/17/">one</a>'
                '<textarea class="copy-from">&gt; unidentified\nACGT</textarea></section>')
    assert [row["sequence_id"] for row in page["records"]] == ["17", None]
    assert [row["sequence_status"] for row in page["records"]] == ["download_required", "available"]


def test_engineering_unambiguous_surrounding_link_join_coalesces_repeated_locators():
    page = read('<section id="addgene-full"><div><a href="/browse/sequence/17/">one</a>'
                '<textarea class="copy-from">&gt; literal\nACGT</textarea>'
                '<a href="/browse/sequence/17/">two</a></div></section>')
    assert len(page["records"]) == 1
    row = page["records"][0]
    assert row["sequence_id"] == "17" and row["sequence"] == "ACGT"
    assert len(row["locators"]) == 3
    assert [locator["tag"] for locator in row["locators"]] == ["a", "textarea", "a"]


def test_engineering_ambiguous_surrounding_ids_preserve_separate_null_identity():
    page = read('<section id="addgene-full"><div><a href="/browse/sequence/17/">one</a>'
                '<a href="/browse/sequence/18/">two</a>'
                '<textarea class="copy-from">&gt; ambiguous\nACGT</textarea></div></section>')
    assert [row["sequence_id"] for row in page["records"]] == ["17", "18", None]
    assert page["records"][2]["native_sequence_text"] == "> ambiguous\nACGT"
    assert page["records"][2]["sequence"] is None
    assert page["records"][2]["issue_codes"] == ["ambiguous_sequence_identity"]


@pytest.mark.parametrize("text,issue", [
    ("", "empty_literal"), ("&gt; header only", "empty_literal"),
    ("&gt; RNA\nACGU", "invalid_literal"),
    ("&gt; invalid\nAC-GT", "invalid_literal"),
    ("&gt; invalid\nAC\u00a0GT", "invalid_literal"),
    ("&gt; invalid\nAC<bad/>GT", "invalid_literal"),
    ("&gt; invalid\nAC&lt;bad/&gt;GT", "invalid_literal"),
])
def test_engineering_invalid_literal_not_silently_normalized(text, issue):
    row = read(legacy(text))["records"][0]
    assert row["sequence"] is None and row["sequence_status"] == "invalid"
    assert row["issue_codes"] == [issue]
    if "bad/" in text:
        assert "<bad/>" in row["native_sequence_text"]


def test_engineering_raw_textarea_character_references_decoded_once():
    row = read(legacy("&gt; literal\nAC&#71;T"))["records"][0]
    assert row["sequence"] == "ACGT"
    row = read(legacy("&gt; literal\nAC&amp;#71;T"))["records"][0]
    assert row["sequence"] is None and "AC&#71;T" in row["native_sequence_text"]


def test_engineering_valid_partial_work_survives_invalid_literal():
    page = read(legacy("&gt; valid\nACGT", sequence_id="1") + legacy("&gt; bad\nAC-GT", sequence_id="2"))
    assert page["parse_status"] == "partial"
    assert page["records"][0]["sequence"] == "ACGT"
    assert page["records"][1]["sequence"] is None


def test_engineering_generic_login_link_and_unrelated_empty_textarea_do_not_authenticate_or_create_result():
    page = read('<a href="/users/login/">Log in</a><textarea name="sequence" id="sequence"></textarea>')
    assert page["authentication_required"] is False and page["records"] == []
    assert page["parse_status"] == "partial"
    assert page["issues"] == [{"code": "representation_unavailable", "record_ordinal": None}]


def test_engineering_explicit_auth_banner_retained_without_following_link():
    page = read('<div class="anonymous-user-sequence-alert">Log in</div>'
                '<section id="other"><a href="/browse/sequence/19/">Download</a></section>')
    assert page["authentication_required"] is True
    assert page["records"][0]["sequence_status"] == "authentication_required"


def test_engineering_http_incomplete_preserves_closed_literals_and_qualifies_page():
    page = read(legacy("&gt; retained\nACGT"), complete=False)
    assert page["parse_status"] == "partial" and page["records"][0]["sequence"] == "ACGT"
    assert {"code": "response_incomplete", "record_ordinal": None} in page["issues"]


def test_engineering_unclosed_textarea_does_not_claim_complete_bases():
    page = read('<section id="addgene-full"><textarea class="copy-from">&gt; unfinished\nACGT', complete=False)
    assert page["records"][0]["sequence"] is None
    assert page["records"][0]["issue_codes"] == ["incomplete_literal"]
    assert page["records"][0]["native_sequence_text"] == "> unfinished\nACGT"


def test_engineering_conflicting_explicit_id_and_link_stays_ambiguous():
    page = read('<div data-sequence-id="17"><a href="/browse/sequence/18/">other</a>'
                '<textarea class="copy-from">&gt; ambiguous\nACGT</textarea></div>')
    assert page["records"][1]["sequence_id"] is None
    assert page["records"][1]["issue_codes"] == ["ambiguous_sequence_identity"]


def test_engineering_conflicting_literals_do_not_choose_first():
    html = '<section id="addgene-full"><div data-sequence-id="17">'
    html += '<textarea class="copy-from">&gt; one\nACGT</textarea>'
    html += '<textarea class="copy-from">&gt; two\nTTTT</textarea></div></section>'
    page = read(html)
    assert len(page["records"]) == 2
    assert all(row["sequence"] is None for row in page["records"])
    assert all("conflicting_sequence_literals" in row["issue_codes"] for row in page["records"])
    assert [row["native_header"] for row in page["records"]] == ["> one", "> two"]


def test_engineering_invalid_utf8_is_typed_invalid_input():
    page = read(b"\xff")
    assert page["parse_status"] == "invalid" and page["records"] == []
    assert page["issues"] == [{"code": "invalid_encoding", "record_ordinal": None}]


@pytest.mark.parametrize("field,value", [
    ("content", "text"), ("content", bytearray(b"x")), ("source_ref", ""),
    ("source_ref", None), ("requested_id", "pUC19"), ("requested_id", 50005),
    ("requested_id", "١"), ("response_complete", 1),
])
def test_engineering_caller_types_and_operands_rejected(field, value):
    kwargs = dict(content=b"", source_ref="engineering", requested_id="50005", response_complete=True)
    kwargs[field] = value
    with pytest.raises(ValueError, match="^addgene_sequence_"):
        api()[0](**kwargs)


def test_engineering_schema_is_closed_and_output_detached():
    read_fn, validate, schema = api()
    page = read(legacy("&gt; detached\nACGT"))
    detached = validate(page)
    detached["records"][0]["locators"][0]["value"] = "changed"
    assert page["records"][0]["locators"][0]["value"] == "mono copy-from"
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(page)
    json.dumps(page, allow_nan=False)
    cyclic = deepcopy(page)
    cyclic["records"] = [cyclic]
    with pytest.raises(ValueError, match="^addgene_sequence_"):
        validate(cyclic)


@pytest.mark.parametrize("mutation", [
    "extra", "ordinal", "status", "sequence", "header", "category", "locator_type",
    "locator_class", "locator_bool", "issue_ordinal", "issue_code", "complete", "nan",
])
def test_engineering_tampered_schema_status_locator_relationships_rejected(mutation):
    page = read(legacy("&gt; genuine literal\nACGT"))
    row = page["records"][0]
    if mutation == "extra": page["topology"] = "circular"
    elif mutation == "ordinal": row["record_ordinal"] = 1
    elif mutation == "status": row["sequence_status"] = "download_required"
    elif mutation == "sequence": row["sequence"] = "TTTT"
    elif mutation == "header": row["native_header"] = "> substituted"
    elif mutation == "category": row["source_verification"] = "depositor"
    elif mutation == "locator_type": row["locators"][0]["tag"] = "a"
    elif mutation == "locator_class": row["locators"][0]["value"] = "other"
    elif mutation == "locator_bool": row["locators"][0]["source_element_ordinal"] = True
    elif mutation == "issue_ordinal": page["issues"] = [{"code": "invalid_literal", "record_ordinal": 4}]
    elif mutation == "issue_code": row["issue_codes"] = ["invented"]
    elif mutation == "complete": page["response_complete"] = False
    elif mutation == "nan": row["sequence_id"] = float("nan")
    with pytest.raises(ValueError, match="^addgene_sequence_"):
        api()[1](page)
