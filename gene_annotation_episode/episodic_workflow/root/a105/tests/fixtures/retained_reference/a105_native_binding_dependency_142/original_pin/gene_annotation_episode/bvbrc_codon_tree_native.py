"""Pure readers for the four explicitly declared CodonTree native tables.

These functions decode supplied bytes. They perform no acquisition or execution,
choose no resource, and assign no scientific score. The caller retains the bytes;
all parsed rows and measurements point to that exact digest-bound artifact.

The family statistics are historical, pre-trim protein statistics. Their count
observations do not identify the original rows or imply final alignment lengths.
The analysis report counts are reported quantities with their native field names.
In particular, the pinned writer reports its protein count as Num_CDS_alignments.
"""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import re
import shlex
from typing import Literal
from urllib.parse import quote

from .phylogeny_format_contracts import _artifact, _native_number


__all__ = [
    "parse_codon_membership", "parse_codon_family_statistics",
    "parse_codon_genome_counts", "parse_codon_analysis_statistics",
]

# A finite diagnostic vocabulary; the native text stays in rows, never messages.
DIAGNOSTIC_CODES = frozenset({
    "codon_artifact_invalid", "codon_data_type_invalid", "codon_hash_mismatch",
    "codon_dialect_unsupported", "codon_utf8_invalid", "codon_empty_input",
    "codon_header_incompatible", "codon_no_complete_records",
    "codon_truncated_line", "codon_unrecognized_row", "codon_malformed_row",
    "codon_duplicate_feature_id", "codon_membership_feature_overlap",
    "codon_duplicate_membership_record", "codon_conflicting_membership_record",
    "codon_unknown_membership_marker", "codon_membership_marker_family_mismatch",
    "codon_missing_family_mismatch", "codon_orphan_missing_family",
    "codon_unpaired_family_line", "codon_duplicate_missing_family",
    "codon_conflicting_missing_family", "codon_native_count_invalid",
    "codon_native_number_invalid", "codon_native_number_missing",
    "codon_boolean_invalid", "codon_boolean_missing", "codon_header_missing_tab",
    "codon_orphan_qualifier", "codon_bad_sequence_map_invalid",
    "codon_bad_sequence_duplicate_key", "codon_duplicate_qualifier",
    "codon_conflicting_qualifier", "codon_unknown_disqualification",
    "codon_duplicate_family_record", "codon_conflicting_family_record",
    "codon_duplicate_genome_record", "codon_conflicting_genome_record",
    "codon_count_stage_order_conflict", "codon_duplicate_analysis_field",
    "codon_conflicting_analysis_field", "codon_reported_cds_uses_protein_count",
    "codon_reported_command_role_unknown", "codon_command_tokenization_failed",
    "codon_analysis_expected_field_missing", "codon_uninterpreted_report_row",
})

_FAMILY_HEADER = (
    "PGFam", "gaps", "sum_squared_freq", "mean_squared_freq", "num_pos",
    "num_seqs", "worstSeqScoreused_in_tree",
)
_GENOME_HEADER = ("Genome", "AllGenes", "SingleCopy", "Filtered_SingleCopy")
_ANALYSIS_HEADER = ("Statistics for CodonTree Analysis",)
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_COUNT = re.compile(r"[0-9]+\Z")
_FAMILY_FIELDS = (
    ("family_native_gaps", "characters", True),
    ("family_native_sum_squared_freq", "column_summed_squared_fraction", False),
    ("family_native_mean_squared_freq", "mean_squared_fraction", False),
    ("family_native_length", "columns", True),
    ("family_native_sequences", "sequences", True),
    ("family_native_worst_sequence_ratio", "ratio", False),
)
_GENOME_FIELDS = (
    "genome_native_all_families", "genome_native_single_copy_families",
    "genome_native_filtered_single_copy_families",
)
_ANALYSIS_FIELDS = (
    "Num_genomes", "Num_protein_alignments", "Num_aligned_amino_acids",
    "Num_CDS_alignments", "Num_aligned_nucleotides",
)


def _diagnostic(code, path, *, phase="native_decode", severity="error"):
    assert code in DIAGNOSTIC_CODES
    return {"code": code, "phase": phase, "path": path,
            "severity": severity, "evidence_refs": []}


def _invalid(code, path, *, phase="native_decode"):
    return {"status": "invalid", "value": None,
            "diagnostics": [_diagnostic(code, path, phase=phase)]}


def _identifier(token):
    return bool(token) and not any(c.isspace() or ord(c) < 32 or ord(c) == 127
                                   for c in token)


class _Reader:
    """Internal source-location bookkeeping, without loading any external data."""

    def __init__(self, data, artifact, suffix, dialect):
        self.artifact = deepcopy(artifact)
        self.table = {"table_id": artifact["raw_artifact_ref"] + suffix,
                      "artifact": deepcopy(artifact), "dialect": dialect,
                      "header_tokens": [], "rows": [], "completeness": "complete"}
        self.diagnostics = []
        self.lines = []
        self.unterminated = set()
        # LF and CRLF are physical line delimiters. Unicode separators in IDs or
        # tokens must not manufacture new physical lines or change byte offsets.
        offset = 0
        parts = data.split(b"\n")
        physical_lines = [part + b"\n" for part in parts[:-1]]
        if parts[-1]:
            physical_lines.append(parts[-1])
        for line_index, part in enumerate(physical_lines):
            terminated = part.endswith(b"\n")
            body = part[:-1] if terminated else part
            if terminated and body.endswith(b"\r"):
                body = body[:-1]
            self.lines.append((body.decode("utf-8"), offset, line_index + 1, terminated))
            offset += len(part)
        if not data:
            self.issue("codon_empty_input", "/data")
            self.table["completeness"] = "unknown"

    def issue(self, code, path, *, phase="native_decode", severity="error",
              incomplete=None):
        self.diagnostics.append(_diagnostic(code, path, phase=phase, severity=severity))
        if incomplete is None:
            incomplete = severity == "error"
        if incomplete and self.table["completeness"] != "truncated":
            self.table["completeness"] = "partial"

    def location(self, start, end, line):
        return {"artifact": deepcopy(self.artifact), "byte_start_0based": start,
                "byte_end_0based_exclusive": end, "line_start_1based": line,
                "line_end_1based_inclusive": line, "xml_path": None}

    def body(self, header=None):
        if header is not None:
            if not self.lines or tuple(self.lines[0][0].split("\t")) != header:
                self.issue("codon_header_incompatible", "/header_tokens")
                return False
            self.table["header_tokens"] = self.lines[0][0].split("\t")
            if not self.lines[0][3]:
                self.issue("codon_truncated_line", "/header_tokens")
                return False
        for text, offset, number, terminated in self.lines[header is not None:]:
            index = len(self.table["rows"])
            self.table["rows"].append({
                "row_index": index, "record_kind": "other_retained", "raw_text": text,
                "fields": text.split("\t"), "family_id": None,
                "location": self.location(offset, offset + len(text.encode("utf-8")), number),
            })
            if not terminated:
                self.unterminated.add(index)
                self.issue("codon_truncated_line", self.path(index))
                self.table["completeness"] = "truncated"
        return True

    @staticmethod
    def path(index, field=None):
        path = f"/value/table/rows/{index}"
        return path if field is None else path + f"/fields/{field}"

    def token_location(self, row, field):
        prefix = "\t".join(row["fields"][:field])
        offset = len(prefix.encode("utf-8")) + (1 if field else 0)
        start = row["location"]["byte_start_0based"] + offset
        return self.location(start, start + len(row["fields"][field].encode("utf-8")),
                             row["location"]["line_start_1based"])

    def observation(self, row, column, field, unit, count, subject, population, method):
        token = row["fields"][column]
        value, state = None, "failed"
        if token == "na":
            state = "missing"
            self.issue("codon_native_number_missing", self.path(row["row_index"], column),
                       severity="qualification")
        else:
            try:
                if count:
                    if not _COUNT.fullmatch(token):
                        raise ValueError
                    value = int(token)
                else:
                    if not _NUMBER.fullmatch(token):
                        raise ValueError
                    value = _native_number(token)
                    if value is None:
                        raise ValueError
                state = "available"
            except (ValueError, OverflowError):
                value = None
                self.issue("codon_native_count_invalid" if count else "codon_native_number_invalid",
                           self.path(row["row_index"], column))
        return {
            "observation_id": f'{self.table["table_id"]}/row/{row["row_index"]}/{field}',
            "field": field, "value": value, "raw_token": token, "state": state,
            "unit": unit, "population_id": population, "subject_id": subject,
            "method": method, "location": self.token_location(row, column),
            "evidence": [], "uncertainty": None, "requirement_ids": [],
        }

    def finish(self, value, count):
        if not count:
            self.issue("codon_no_complete_records", "/value/table/rows",
                       incomplete=self.table["completeness"] != "unknown")
        status = "ok" if self.table["completeness"] == "complete" else "partial"
        if not count:
            status = "invalid"
        return {"status": status, "value": value, "diagnostics": self.diagnostics}


def _start(data, artifact, suffix, dialect, allowed):
    try:
        _artifact(artifact)
    except ValueError:
        return None, _invalid("codon_artifact_invalid", "/artifact", phase="association")
    if not isinstance(data, bytes):
        return None, _invalid("codon_data_type_invalid", "/data")
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        return None, _invalid("codon_hash_mismatch", "/artifact/sha256", phase="association")
    if not isinstance(dialect, str) or dialect not in allowed:
        return None, _invalid("codon_dialect_unsupported", "/dialect")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None, _invalid("codon_utf8_invalid", "/data")
    return _Reader(data, artifact, suffix, dialect), None


def _bad_header(reader):
    return {"status": "invalid", "value": None, "diagnostics": reader.diagnostics}


def _repeated(reader, seen, key, signature, index, duplicate_code, conflict_code):
    if key in seen:
        equal = seen[key] == signature
        reader.issue(duplicate_code if equal else conflict_code, reader.path(index),
                     phase="association", severity="qualification" if equal else "error")
    else:
        seen[key] = signature


def parse_codon_membership(data: bytes, *, artifact: dict,
                           dialect: Literal["pgfams_legacy", "homologs_current"]) -> dict:
    """Read source-ordered protein/CDS membership without inferring genome IDs."""
    reader, failure = _start(data, artifact, "#codon_membership", dialect,
                              {"pgfams_legacy", "homologs_current"})
    if failure is not None:
        return failure
    reader.body()
    value = {"table": reader.table, "rows": [], "missing_codon_family_ids": []}
    pending = None
    seen = {}
    missing_rows = []
    for row in reader.table["rows"]:
        index, raw, fields = row["row_index"], row["raw_text"], row["fields"]
        if index in reader.unterminated:
            continue
        if pending is not None:
            family = pending["raw_text"]
            if raw == "No codon alignment " + family:
                for part in (pending, row):
                    part["family_id"] = family
                    part["record_kind"] = "missing_codon_alignment"
                if family in value["missing_codon_family_ids"]:
                    reader.issue("codon_duplicate_missing_family", reader.path(index),
                                 phase="association", severity="qualification")
                value["missing_codon_family_ids"].append(family)
                missing_rows.append((family, index))
                pending = None
                continue
            reader.issue("codon_missing_family_mismatch" if raw.startswith("No codon alignment ")
                         else "codon_unpaired_family_line", reader.path(pending["row_index"]),
                         phase="association")
            pending = None
            if raw.startswith("No codon alignment "):
                continue
        if not raw:
            continue
        if raw.startswith("No codon alignment "):
            reader.issue("codon_orphan_missing_family", reader.path(index), phase="association")
            continue
        if len(fields) == 1 and _identifier(raw) and not raw.endswith(":"):
            pending = row
            continue
        if len(fields) < 3 or not _identifier(fields[0]) or fields[1] not in {"Proteins", "Codons"} or fields[2] != "":
            reader.issue("codon_malformed_row", reader.path(index))
            continue
        family, representation = fields[0], fields[1]
        included, deleted, missing = [], [], []
        destination = included
        marker_seen = False
        valid = True
        for column, token in enumerate(fields[3:], 3):
            expected = "deletedParalogs: " if representation == "Proteins" else f"lacking CodonAlignment for {family}: "
            if token == expected and not marker_seen:
                marker_seen = True
                destination = deleted if representation == "Proteins" else missing
            elif token.startswith("lacking CodonAlignment for "):
                reader.issue("codon_membership_marker_family_mismatch", reader.path(index, column),
                             phase="association")
                valid = False
                break
            elif not _identifier(token) or token.endswith(":"):
                reader.issue("codon_unknown_membership_marker" if token else "codon_malformed_row",
                             reader.path(index, column), severity="qualification" if token else "error",
                             incomplete=True)
                valid = False
                break
            else:
                destination.append(token)
        if marker_seen and not destination:
            reader.issue("codon_malformed_row", reader.path(index))
            valid = False
        if not valid:
            continue
        for group in (included, deleted, missing):
            if len(group) != len(set(group)):
                reader.issue("codon_duplicate_feature_id", reader.path(index),
                             phase="association", severity="qualification")
        if set(included).intersection(deleted + missing):
            reader.issue("codon_membership_feature_overlap", reader.path(index), phase="association")
        typed = {"family_id": family,
                 "representation": "protein" if representation == "Proteins" else "coding_nucleotide",
                 "included_feature_ids": included, "deleted_feature_ids": deleted,
                 "missing_codon_feature_ids": missing, "source_row_index": index}
        row["record_kind"], row["family_id"] = "data", family
        _repeated(reader, seen, (family, representation), (included, deleted, missing), index,
                  "codon_duplicate_membership_record", "codon_conflicting_membership_record")
        value["rows"].append(typed)
    if pending is not None:
        reader.issue("codon_unpaired_family_line", reader.path(pending["row_index"]), phase="association")
    for family, index in missing_rows:
        if (family, "Codons") in seen:
            reader.issue("codon_conflicting_missing_family", reader.path(index), phase="association")
    return reader.finish(value, len(value["rows"]) + len(missing_rows))


class _ScalarMapError(ValueError):
    def __init__(self, code="codon_bad_sequence_map_invalid"):
        self.code = code


def _scalar_map(text):
    """Decode only Python dictionary syntax with literal string/numeric leaves.

    Inspect the AST before creating any mapping, so duplicate keys cannot be
    overwritten. No eval, literal_eval, call, comprehension, unpacking, numeric
    expression, nested object, boolean or nonfinite scalar is evaluated.
    """
    try:
        expression = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as error:
        raise _ScalarMapError from error
    if not isinstance(expression.body, ast.Dict):
        raise _ScalarMapError
    result, seen = [], set()
    for key, node in zip(expression.body.keys, expression.body.values):
        if not isinstance(key, ast.Constant) or type(key.value) is not str:
            raise _ScalarMapError
        if key.value in seen:
            raise _ScalarMapError("codon_bad_sequence_duplicate_key")
        seen.add(key.value)
        sign = 1
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            sign = -1 if isinstance(node.op, ast.USub) else 1
            node = node.operand
        if not isinstance(node, ast.Constant) or type(node.value) not in (int, float):
            raise _ScalarMapError
        value = node.value
        if type(value) is float:
            # AST constants have already rounded nonzero underflow to zero.
            # Validate the original numeric leaf before applying its unary sign.
            value = _native_number(ast.get_source_segment(text, node))
            if value is None:
                raise _ScalarMapError
        value = sign * value
        result.append({"genome_id": key.value, "value": value})
    return result


def parse_codon_family_statistics(data: bytes, *, artifact: dict,
                                  dialect: Literal["current_missing_header_tab"]) -> dict:
    """Retain the exact fused header and native pre-trim cells, never ranking."""
    reader, failure = _start(data, artifact, "#codon_family_statistics", dialect,
                              {"current_missing_header_tab"})
    if failure is not None:
        return failure
    if not reader.body(_FAMILY_HEADER):
        # This literal defect flag cannot truthfully describe an arbitrary bad
        # header. The caller still retains the original supplied artifact bytes.
        return _bad_header(reader)
    reader.issue("codon_header_missing_tab", "/value/table/header_tokens/6",
                 severity="qualification")
    value = {"table": reader.table, "observations": [], "rows": [],
             "header_defect": "missing_tab_before_used_in_tree"}
    active = None
    qualifier_values = {}
    conflicting_disqualifications = set()
    for row in reader.table["rows"]:
        index, raw, fields = row["row_index"], row["raw_text"], row["fields"]
        if index in reader.unterminated:
            continue
        if raw.startswith(("bad seqs:", "disqualification:")):
            if active is None:
                reader.issue("codon_orphan_qualifier", reader.path(index), phase="association")
                continue
            active["source_row_indices"].append(index)
            row["family_id"] = active["family_id"]
            is_bad = raw.startswith("bad seqs:")
            row["record_kind"] = "bad_sequences" if is_bad else "disqualification"
            prefix = "bad seqs: " if is_bad else "disqualification: "
            if not raw.startswith(prefix):
                reader.issue("codon_malformed_row", reader.path(index))
                continue
            payload = raw[len(prefix):]
            key = (active["source_row_indices"][0], row["record_kind"])
            if not is_bad and key in qualifier_values and qualifier_values[key] != payload:
                conflicting_disqualifications.add(key)
            _repeated(reader, qualifier_values, key, payload, index,
                      "codon_duplicate_qualifier", "codon_conflicting_qualifier")
            if is_bad:
                try:
                    values = _scalar_map(payload)
                except _ScalarMapError as error:
                    reader.issue(error.code, reader.path(index),
                                 phase="association" if error.code == "codon_bad_sequence_duplicate_key" else "native_decode")
                    continue
                # Repeated qualifier records remain repeated entries. The raw
                # source indices preserve their independent record identities.
                active["bad_sequence_values"].extend(values)
            elif payload in {"bad seqs", "low alignment score"}:
                if key in conflicting_disqualifications:
                    active["disqualification"] = None
                else:
                    active["disqualification"] = payload
            else:
                active["disqualification"] = None
                reader.issue("codon_unknown_disqualification", reader.path(index),
                             severity="qualification", incomplete=True)
            continue
        active = None
        if not raw:
            continue
        if len(fields) != 8 or not _identifier(fields[0]):
            reader.issue("codon_malformed_row", reader.path(index))
            continue
        family = fields[0]
        row["family_id"], row["record_kind"] = family, "data"
        observations = [
            reader.observation(row, column, field, unit, count, family,
                               reader.table["table_id"] + "/population/family/" + quote(family, safe=""),
                               "codon_tree_native_pretrim_statistics")
            for column, (field, unit, count) in enumerate(_FAMILY_FIELDS, 1)
        ]
        value["observations"].extend(observations)
        boolean = fields[7]
        used = {"True": True, "False": False}.get(boolean)
        if boolean not in {"True", "False"}:
            reader.issue("codon_boolean_missing" if boolean == "na" else "codon_boolean_invalid",
                         reader.path(index, 7), severity="qualification" if boolean == "na" else "error")
        active = {"family_id": family, "observation_ids": [o["observation_id"] for o in observations],
                  "used_in_tree": used, "bad_sequence_values": [], "disqualification": None,
                  "source_row_indices": [index]}
        value["rows"].append(active)
    seen = {}
    for family in value["rows"]:
        # Include continuation records so repeated data rows with different
        # source qualifiers are diagnosed as conflicts, never overwritten.
        signature = tuple(reader.table["rows"][i]["raw_text"] for i in family["source_row_indices"])
        _repeated(reader, seen, family["family_id"], signature, family["source_row_indices"][0],
                  "codon_duplicate_family_record", "codon_conflicting_family_record")
    return reader.finish(value, len(value["rows"]))


def parse_codon_genome_counts(data: bytes, *, artifact: dict) -> dict:
    """Read three stage-specific family counts; AllGenes is not a CDS count."""
    reader, failure = _start(data, artifact, "#codon_genome_counts", "genes_per_genome_current",
                              {"genes_per_genome_current"})
    if failure is not None:
        return failure
    if not reader.body(_GENOME_HEADER):
        return _bad_header(reader)
    value = {"table": reader.table, "observations": [], "rows": []}
    seen = {}
    for row in reader.table["rows"]:
        index, fields = row["row_index"], row["fields"]
        if index in reader.unterminated or not row["raw_text"]:
            continue
        if len(fields) != 4 or not _identifier(fields[0]):
            reader.issue("codon_malformed_row", reader.path(index))
            continue
        genome = fields[0]
        row["record_kind"] = "data"
        observations = [
            reader.observation(row, column, field, "families", True, genome,
                               reader.table["table_id"] + "/population/genome/" + quote(genome, safe=""),
                               "codon_tree_native_genome_family_counts")
            for column, field in enumerate(_GENOME_FIELDS, 1)
        ]
        value["observations"].extend(observations)
        value["rows"].append({
            "genome_id": genome, "all_families_observation_id": observations[0]["observation_id"],
            "single_copy_observation_id": observations[1]["observation_id"],
            "filtered_single_copy_observation_id": observations[2]["observation_id"],
        })
        _repeated(reader, seen, genome, tuple(fields[1:]), index,
                  "codon_duplicate_genome_record", "codon_conflicting_genome_record")
        counts = [o["value"] for o in observations]
        # These are subset stages of the same native family population. Preserve
        # contradictory values exactly and qualify their relationship.
        if any(a is not None and b is not None and a < b for a, b in zip(counts, counts[1:])):
            reader.issue("codon_count_stage_order_conflict", reader.path(index), phase="association")
    return reader.finish(value, len(value["rows"]))


def parse_codon_analysis_statistics(data: bytes, *, artifact: dict,
                                    dialect: Literal["retained_current_source"]) -> dict:
    """Read reported counts and the actual command text with unknown role."""
    reader, failure = _start(data, artifact, "#codon_analysis_statistics", dialect,
                              {"retained_current_source"})
    if failure is not None:
        return failure
    if not reader.body(_ANALYSIS_HEADER):
        return _bad_header(reader)
    value = {"table": reader.table, "observations": [], "commands": [],
             "uninterpreted_source_row_indices": []}
    seen = {}
    expected = set(_ANALYSIS_FIELDS) | {"command_line", "PGFams", "duration"}
    for row in reader.table["rows"]:
        index, fields, raw = row["row_index"], row["fields"], row["raw_text"]
        if index in reader.unterminated:
            value["uninterpreted_source_row_indices"].append(index)
            continue
        name = fields[0]
        if name in _ANALYSIS_FIELDS or name == "command_line":
            if len(fields) != 2:
                reader.issue("codon_malformed_row", reader.path(index))
                value["uninterpreted_source_row_indices"].append(index)
                continue
            row["record_kind"] = "data"
            expected.discard(name)
            _repeated(reader, seen, name, fields[1], index,
                      "codon_duplicate_analysis_field", "codon_conflicting_analysis_field")
            if name in _ANALYSIS_FIELDS:
                value["observations"].append(reader.observation(
                    row, 1, "analysis_native_reported_counts", "reported_count", True, name,
                    reader.table["table_id"] + "/population/reported", "codon_tree_native_analysis_report"))
                if name == "Num_CDS_alignments":
                    reader.issue("codon_reported_cds_uses_protein_count", reader.path(index),
                                 severity="qualification")
            else:
                command = fields[1]
                try:
                    argv = shlex.split(command, posix=True)
                except ValueError:
                    argv = None
                    reader.issue("codon_command_tokenization_failed", reader.path(index, 1))
                value["commands"].append({
                    "command_id": f'{reader.table["table_id"]}/row/{index}/command_line',
                    "role": "unknown", "argv": argv, "raw_text": command,
                    "origin": "observed", "evidence": [], "location": reader.token_location(row, 1),
                })
                reader.issue("codon_reported_command_role_unknown", reader.path(index, 1),
                             severity="qualification")
        else:
            value["uninterpreted_source_row_indices"].append(index)
            if name == "PGFams" and len(fields) == 2:
                expected.discard("PGFams")
                reader.issue("codon_uninterpreted_report_row", reader.path(index), severity="qualification")
            elif re.fullmatch(r"Total job duration [0-9]+ seconds", raw):
                expected.discard("duration")
                reader.issue("codon_uninterpreted_report_row", reader.path(index), severity="qualification")
            elif raw:
                reader.issue("codon_unrecognized_row", reader.path(index),
                             severity="qualification", incomplete=True)
    if expected:
        # No value is synthesized for missing source fields. The finite known
        # expectation is a file-format check, not an execution-completion gate.
        reader.issue("codon_analysis_expected_field_missing", "/value/table/rows",
                     severity="qualification", incomplete=True)
    return reader.finish(value, len(value["observations"]) + len(value["commands"]))
