"""Source-derived tabular7 messages are not additional alignment rows."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
from tests.test_blast_iteration_inputs import from_collection
from tests.test_blast_sequence_database import invocation


FIELDS = ["qseqid", "sseqid", "qlen", "slen", "qstart", "qend", "sstart", "send", "qseq", "sseq", "bitscore"]
MESSAGE = "Search has CONVERGED!"


def collect(*, program="psiblast", version="2.17.0+", newline="\n", delimiter="\t",
            position=2, message=None, declared=2, extra_row=None, format="tabular7"):
    lines = [f"# {program.upper()} {version}", "# Query: q", "# Database: synthetic_db", f"# {declared} hits found"]
    rows = [delimiter.join(["q", subject, "8", "10", "3", "6", "2", "5", "ACDE", "ACDE", "40"]) for subject in ("A", "B")]
    if extra_row is not None:
        rows.insert(1, extra_row)
    rows.insert(position, MESSAGE if message is None else message)
    raw = (newline.join(lines + rows) + newline).encode()
    descriptor = dict(artifact_key="synthetic-report", role="primary_report", format=format, fields=FIELDS, delimiter=delimiter)
    return raw, parse_blast_report_collection({"synthetic-report": raw}, artifacts=[descriptor], invocation=invocation(program))


def calculate(collection):
    return calculate_blast_iteration_components(populate_blast_iteration_sheet(**from_collection(collection)))


@pytest.mark.parametrize("program", ["psiblast", "deltablast"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("delimiter", ["\t", "@"])
def test_supported_control_message_preserves_text_and_exact_alignment_counts(program, newline, position, delimiter):
    raw, collection = collect(program=program, newline=newline, position=position, delimiter=delimiter)
    before = deepcopy(collection)
    search, = collection["searches"]
    assert search["native"]["report"]["text"] == raw.decode()
    assert search["native"]["search"]["text"] == raw.decode()
    assert collection["artifacts"][0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(search["native"]["search"]["rows"]) == 2
    expected_lines = [5, 6, 7]
    expected_lines.pop(position)
    assert search["native"]["line_numbers"] == expected_lines
    assert [row["hsp_ordinals"] for row in search["row_map"]] == [[0], [1]]
    result = calculate(collection)
    row, = result["searches"]
    assert {key: cell["value"] for key, cell in row["counts"].items()} == dict(
        reported_hit_count=2, reported_hsp_count=2, observed_hsp_count=2,
        parsed_hit_count=2, parsed_hsp_count=2, declared_alignment_row_count=2)
    assert row["native_converged"]["value"] is None
    assert result["convergence_observations"] == []
    assert collection == before


def test_malformed_real_row_stays_counted_and_keeps_its_original_ordinal():
    _, collection = collect(extra_row="unparseable original row", position=2)
    search, = collection["searches"]
    assert len(search["native"]["search"]["rows"]) == 3
    assert search["native"]["line_numbers"] == [5, 6, 8]
    assert [row["hsp_ordinals"] for row in search["row_map"]] == [[0], [2]]
    row, = calculate(collection)["searches"]
    assert row["counts"]["reported_hit_count"]["value"] is None
    assert row["counts"]["observed_hsp_count"]["value"] == 3
    assert row["counts"]["parsed_hsp_count"]["value"] == 2
    assert {issue["code"] for issue in search["issues"]} >= {
        "blast_tabular_column_count_invalid", "blast_tabular_reported_row_count_mismatch"}


@pytest.mark.parametrize("options", [dict(version="2.16.0+"), dict(version="2.18.0+"),
    dict(format="tabular6"), dict(message="Search has CONVERGED! "),
    dict(message=" Search has CONVERGED!"), dict(message="Search has converged!"),
    dict(message='"Search has CONVERGED!"'), dict(message="Search has CONVERGED!suffix")])
def test_unsupported_or_near_match_is_not_reclassified(options):
    _, collection = collect(**options)
    assert len(collection["searches"][0]["native"]["search"]["rows"]) == 3


@pytest.mark.parametrize("suffix", ["", "\r"])
def test_unterminated_message_is_preserved_as_unclassified_data(suffix):
    raw, old = collect()
    raw = raw[:-1] + suffix.encode()
    descriptor = {key: old["artifacts"][0][key] for key in ("artifact_key", "role", "format", "fields", "delimiter")}
    collection = parse_blast_report_collection({descriptor["artifact_key"]: raw}, artifacts=[descriptor], invocation=old["invocation"])
    assert len(collection["searches"][0]["native"]["search"]["rows"]) == 3


@pytest.mark.parametrize("header", ["", "# BLASTP 2.17.0+\n", "# PSIBLAST 2.16.0+\n"])
def test_missing_or_conflicting_header_preserves_unclassified_line(header):
    raw, old = collect()
    if not header:
        raw = raw.split(b"\n", 1)[1]
    else:
        raw = header.encode() + raw
    descriptor = {key: old["artifacts"][0][key] for key in ("artifact_key", "role", "format", "fields", "delimiter")}
    collection = parse_blast_report_collection({descriptor["artifact_key"]: raw}, artifacts=[descriptor], invocation=old["invocation"])
    assert sum(len(row["native"]["search"]["rows"]) for row in collection["searches"]) == 3


@pytest.mark.parametrize("fields,delimiter", [(["stitle"], "\t"), (["qseqid", "sseqid", "stitle"], " ")])
def test_message_shaped_valid_width_data_is_not_removed(fields, delimiter):
    raw = ("# PSIBLAST 2.17.0+\n# Query: q\n# Database: synthetic_db\n# 1 hits found\n" + MESSAGE + "\n").encode()
    descriptor = dict(artifact_key="report", role="primary_report", format="tabular7", fields=fields, delimiter=delimiter)
    collection = parse_blast_report_collection({"report": raw}, artifacts=[descriptor], invocation=invocation())
    row, = collection["searches"][0]["native"]["search"]["rows"]
    assert row["values"] == MESSAGE.split(delimiter)


def test_message_inside_a_subject_title_remains_an_ordinary_alignment():
    fields = FIELDS + ["stitle"]
    line = "\t".join(["q", "A", "8", "10", "3", "6", "2", "5", "ACDE", "ACDE", "40", MESSAGE])
    raw = ("# PSIBLAST 2.17.0+\n# Query: q\n# Database: synthetic_db\n# 1 hits found\n" + line + "\n").encode()
    descriptor = dict(artifact_key="report", role="primary_report", format="tabular7", fields=fields, delimiter="\t")
    collection = parse_blast_report_collection({"report": raw}, artifacts=[descriptor], invocation=invocation())
    assert len(collection["searches"][0]["native"]["search"]["rows"]) == 1
    assert collection["searches"][0]["normalized"]["hits"][0]["descriptions"][0]["title"] == MESSAGE


def test_repeated_messages_and_zero_hit_sections_do_not_manufacture_data():
    raw = ("# PSIBLAST 2.17.0+\n# Query: q\n# Database: synthetic_db\n# 0 hits found\n"
           + MESSAGE + "\n" + MESSAGE + "\n").encode()
    descriptor = dict(artifact_key="synthetic-report", role="primary_report", format="tabular7", fields=FIELDS, delimiter="\t")
    collection = parse_blast_report_collection({"synthetic-report": raw}, artifacts=[descriptor], invocation=invocation())
    row, = calculate(collection)["searches"]
    assert all(cell["value"] == 0 for cell in row["counts"].values())
    assert row["native_converged"]["value"] is None
    assert row["native_search"]["native"]["search"]["text"].count(MESSAGE) == 2


def test_multiple_query_sections_keep_original_keys_lines_and_messages():
    raw, old = collect()
    raw += raw
    descriptor = {key: old["artifacts"][0][key] for key in ("artifact_key", "role", "format", "fields", "delimiter")}
    collection = parse_blast_report_collection({descriptor["artifact_key"]: raw}, artifacts=[descriptor], invocation=old["invocation"])
    assert [row["search_key"]["search_pointer"] for row in collection["searches"]] == ["/sections/0", "/sections/1"]
    assert [row["native"]["line_numbers"] for row in collection["searches"]] == [[5, 6], [12, 13]]
    assert [row["counts"]["observed_hsp_count"]["value"] for row in calculate(collection)["searches"]] == [2, 2]
