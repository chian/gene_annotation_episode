"""Saved-document validation is detached and independent of native-byte readers."""
import builtins
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_metacats_formats as readers
from gene_annotation_episode.bvbrc_metacats_format_contracts import (
    validate_metacats_adjusted_matrix, validate_metacats_chisq_table,
    validate_metacats_metadata, validate_metacats_pair_table, validate_metacats_raw_r_table,
)


VALIDATORS = {"chisq": validate_metacats_chisq_table, "pair": validate_metacats_pair_table,
              "omnibus": validate_metacats_raw_r_table, "pairwise": validate_metacats_raw_r_table,
              "metadata": validate_metacats_metadata, "matrix": validate_metacats_adjusted_matrix}


@pytest.fixture
def documents():
    supplied = {
        "chisq": b"Position\tChi-square_value\tP-value\tDegrees_of_freedom\tFewer_5\tA\tB\n2\t8.3\t0.003\t1\tN\t6 A\t6 C\n",
        "pair": b"Position\tMultiple_comparison_p-value\tGroups\n2\t.005\tA,B\n",
        "omnibus": b'"resultCST"\n"1" "Chi-square Analysis Result:\n Site2 \t 8.3 \t .003 \t 1 \t N \t group1(6_A)|group2(6_C) \n"\n',
        "pairwise": b'"resultMC"\n"1" "MGC Multiple Comparison Result:\n Site2 \t .005 \t 1 \t 2 \n"\n',
        "metadata": b"ID\tcomparison\na\tA\nb\tB\n",
        "matrix": b"a\t1\t A # -\nb\t2\t C # -\n",
    }
    docs = {}
    for name, data in supplied.items():
        kwargs = {"artifact": {"raw_artifact_ref": "synthetic-" + name, "source_ref": "supplied",
                               "sha256": sha256(data).hexdigest()}, "encoding": "ascii"}
        if name == "metadata":
            result = readers.parse_metacats_metadata(data, **kwargs, delimiter="tab", header="present")
        elif name == "matrix":
            result = readers.parse_metacats_adjusted_matrix(data, **kwargs, category_id="c")
        elif name in ("omnibus", "pairwise"):
            result = readers.parse_metacats_raw_r_table(data, **kwargs, category_id="c", kind=name,
                layout="r_write_table_single_result_string")
        else:
            function = readers.parse_metacats_chisq_table if name == "chisq" else readers.parse_metacats_pair_table
            result = function(data, **kwargs, category_id="c", layout="current_filtered_tsv")
        assert result["status"] == "ok"
        docs[name] = json.loads(json.dumps(result["value"], allow_nan=False))
    return docs


@pytest.mark.parametrize("name", VALIDATORS)
def test_saved_document_roundtrip_detached_offline_without_parsing(documents, name, monkeypatch):
    value = documents[name]
    before = deepcopy(value)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-document validation attempted external operation or native parsing")
    for owner, attribute in [(builtins, "open"), (Path, "read_bytes"), (socket, "socket"),
                             (subprocess, "run"), (subprocess, "Popen")]:
        monkeypatch.setattr(owner, attribute, forbidden)
    for attribute in readers.__all__:
        monkeypatch.setattr(readers, attribute, forbidden)
    validated = VALIDATORS[name](value)
    assert validated == before and validated is not value
    validated["artifact"]["source_ref"] = "changed"
    active = "omnibus_rows" if name == "omnibus" else "pair_rows" if name == "pairwise" else "rows"
    validated[active][0]["source_location"]["artifact"]["sha256"] = "0" * 64
    assert value == before


@pytest.mark.parametrize("name", VALIDATORS)
def test_closed_document_shapes_and_finite_errors(documents, name):
    validator, original = VALIDATORS[name], documents[name]
    for wrong in (None, [], "", 1, True, {**original, "invented": 1}):
        with pytest.raises(ValueError):
            validator(wrong)
    for field in original:
        value = deepcopy(original)
        del value[field]
        with pytest.raises(ValueError):
            validator(value)
    for field in ("artifact", "encoding", "completeness"):
        for malformed in (None, [], {}, True, "unsupported"):
            value = deepcopy(original)
            value[field] = malformed
            with pytest.raises(ValueError):
                validator(value)


@pytest.mark.parametrize("name", VALIDATORS)
def test_digest_identity_and_source_relationships(documents, name):
    validator = VALIDATORS[name]
    identity = "document_id" if name in ("metadata", "matrix") else "table_id"
    active = "omnibus_rows" if name == "omnibus" else "pair_rows" if name == "pairwise" else "rows"
    original = documents[name]
    for change in (
        lambda v: v.update({identity: "wrong"}),
        lambda v: v["artifact"].update(sha256="wrong"),
        lambda v: v["artifact"].update(sha256="0" * 64),
        lambda v: v[active][0].update(row_index=True),
        lambda v: v[active][0].update(row_index=-1),
        lambda v: v[active][0].update(extra="unknown"),
        lambda v: v[active][0]["source_location"]["artifact"].update(source_ref="wrong"),
        lambda v: v[active][0]["source_location"].update(byte_start_0based=-1),
    ):
        value = deepcopy(original)
        change(value)
        with pytest.raises(ValueError):
            validator(value)


@pytest.mark.parametrize("name", ("chisq", "pair", "omnibus", "pairwise"))
def test_numbers_must_match_token_semantics_and_exact_locations(documents, name):
    active = "omnibus_rows" if name == "omnibus" else "pair_rows" if name == "pairwise" else "rows"
    original = documents[name]
    for field, replacement in (("value", 0.7), ("value", True), ("state", "missing"),
                               ("token_kind", "malformed"), ("raw_token", "0.7"), ("extra", 1)):
        value = deepcopy(original)
        value[active][0]["p_value"][field] = replacement
        with pytest.raises(ValueError):
            VALIDATORS[name](value)
    value = deepcopy(original)
    loc = value[active][0]["p_value"]["source_location"]
    loc["byte_start_0based"] += 1
    loc["byte_end_0based_exclusive"] += 1
    with pytest.raises(ValueError, match="number_source_range_conflict"):
        VALIDATORS[name](value)


def test_chisq_position_group_count_and_header_relationships(documents):
    for change in (
        lambda v: v["rows"][0].update(position_1based=4),
        lambda v: v["rows"][0].update(position_qualification="legacy_star"),
        lambda v: v.update(group_heading_tokens=["B", "A"]),
        lambda v: v["rows"][0]["group_cells"].pop(),
        lambda v: v["rows"][0]["group_cells"][0].update(heading_index=1),
        lambda v: v["rows"][0]["group_cells"][0]["symbol_counts"][0].update(symbol="T"),
        lambda v: v["rows"][0]["group_cells"][0].update(symbol_counts=[]),
        lambda v: v["rows"][0]["group_cells"][0]["symbol_counts"][0].update(count={}),
        lambda v: v["rows"][0]["df"].update(value=1.0),
    ):
        value = deepcopy(documents["chisq"])
        change(value)
        with pytest.raises(ValueError):
            validate_metacats_chisq_table(value)


def test_raw_kind_wrapper_and_positional_relationships(documents):
    for change in (
        lambda v: v.update(pair_rows=[]),
        lambda v: v.update(wrapper_column_token='"resultMC"'),
        lambda v: v.update(wrapper_row_token='"2"'),
        lambda v: v.update(section_heading_token="different heading"),
        lambda v: v["omnibus_rows"][0].update(site_token=" Site4 "),
        lambda v: v["omnibus_rows"][0]["positional_groups"][0].update(position_1based=2),
        lambda v: v["omnibus_rows"][0]["positional_groups"][0].update(raw_token="group3(6_A)"),
        lambda v: v["omnibus_rows"][0]["positional_groups"].pop(),
    ):
        value = deepcopy(documents["omnibus"])
        change(value)
        with pytest.raises(ValueError):
            validate_metacats_raw_r_table(value)


def test_metadata_rows_stay_ordered_and_complete_width_is_honest(documents):
    for change in (
        lambda v: v.update(header_tokens=None),
        lambda v: v["rows"].reverse(),
        lambda v: v["rows"][1].update(row_index=0),
        lambda v: v["rows"][0].update(cells={"ID": "a"}),
        lambda v: v["rows"][0]["cells"].append("extra"),
    ):
        value = deepcopy(documents["metadata"])
        change(value)
        with pytest.raises(ValueError):
            validate_metacats_metadata(value)


def test_adjusted_matrix_preserves_hash_and_rejects_false_complete_dimensions(documents):
    for change in (
        lambda v: v["rows"][0].update(native_group_token=None),
        lambda v: v["rows"][0].update(native_member_token=""),
        lambda v: v["rows"][0]["symbols"].append("A"),
        lambda v: v["rows"][0]["symbols"].__setitem__(0, "TRUE"),
        lambda v: v["rows"][0]["symbols"].__setitem__(0, 1),
    ):
        value = deepcopy(documents["matrix"])
        change(value)
        with pytest.raises(ValueError):
            validate_metacats_adjusted_matrix(value)
    assert validate_metacats_adjusted_matrix(documents["matrix"])["rows"][0]["symbols"] == ["A", "#", "-"]


def test_partial_malformed_native_values_remain_replayable():
    data = b"Position\tMultiple_comparison_p-value\tGroups\n2\t1e-999\tA,B\n3\t2\tA,B\n4\tNA\tA,B\n"
    original = readers.parse_metacats_pair_table(data, artifact={"raw_artifact_ref": "partial",
        "source_ref": "s", "sha256": sha256(data).hexdigest()}, layout="current_filtered_tsv", category_id="c", encoding="ascii")
    assert original["status"] == "partial"
    saved = json.loads(json.dumps(original["value"]))
    replay = validate_metacats_pair_table(saved)
    assert [(r["p_value"]["state"], r["p_value"]["value"]) for r in replay["rows"]] == [("failed", None), ("incompatible", 2.0), ("not_measured", None)]
