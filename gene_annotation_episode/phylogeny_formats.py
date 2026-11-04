"""Supplied-byte phylogeny readers; no acquisition, execution or interpretation.

The frozen stored shapes are in PARSER_CONTRACT.md (2026-10-24). A successful
read means the supplied syntax was understood, not that transport was complete
or scientific inference succeeded. Native bytes remain the caller's artifact.
No support method, biological rooting, alphabet or original residue map is
inferred here. All indices identify source-local records, including duplicates.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from copy import deepcopy
import hashlib
import re
from typing import Literal
from xml.parsers import expat

from .phylogeny_format_contracts import (
    _artifact, _native_number, validate_alignment_document, validate_tree_record,
)


DIAGNOSTIC_CODES = frozenset({
    "phylogeny_artifact_invalid", "phylogeny_artifact_sha256_mismatch",
    "phylogeny_bytes_required", "phylogeny_encoding_invalid", "phylogeny_empty_input",
    "phylogeny_reader_parameter_invalid", "phylogeny_newick_syntax_invalid",
    "phylogeny_newick_truncated", "phylogeny_newick_multiple_disallowed",
    "phylogeny_newick_double_quote_dialect_required", "phylogeny_newick_rooted_marker_conflict",
    "phylogeny_native_number_invalid", "phylogeny_negative_branch_length",
    "phylogeny_fasta_header_missing", "phylogeny_alignment_label_missing",
    "phylogeny_alignment_symbol_invalid", "phylogeny_alignment_lengths_unequal",
    "phylogeny_alignment_whitespace_ignored", "phylogeny_phylip_header_invalid",
    "phylogeny_phylip_truncated", "phylogeny_phylip_row_count_mismatch",
    "phylogeny_phylip_column_count_mismatch", "phylogeny_phylip_block_width_mismatch",
    "phylogeny_phylip_continuation_id_mismatch",
    "phylogeny_phylip_trailing_data", "phylogeny_partition_syntax_invalid",
    "phylogeny_partition_range_invalid", "phylogeny_partition_out_of_bounds",
    "phylogeny_partition_overlap", "phylogeny_partition_holes",
    "phylogeny_phyloxml_syntax_invalid", "phylogeny_phyloxml_truncated",
    "phylogeny_phyloxml_dtd_forbidden", "phylogeny_phyloxml_root_invalid",
    "phylogeny_phyloxml_namespace_unsupported", "phylogeny_phyloxml_root_clade_invalid",
    "phylogeny_phyloxml_branch_length_multiple", "phylogeny_phyloxml_rooted_attribute_invalid",
    "phylogeny_phyloxml_element_uninterpreted", "phylogeny_phyloxml_nested_scalar",
    "phylogeny_phyloxml_trees_missing",
})


def _diagnostic(code, path="", *, phase="native_decode", severity="error", artifact=None):
    assert code in DIAGNOSTIC_CODES
    return {"code": code, "phase": phase, "path": path, "severity": severity,
            "evidence_refs": [artifact["raw_artifact_ref"]] if artifact is not None else []}


def _result(value, diagnostics, *, usable=None):
    if usable is None:
        usable = value is not None
    errors = any(d["severity"] == "error" for d in diagnostics)
    return {"status": "partial" if errors and usable else "invalid" if errors else "ok",
            "value": value, "diagnostics": diagnostics}


def _input(data, artifact):
    try:
        _artifact(artifact)
    except ValueError:
        return _result(None, [_diagnostic("phylogeny_artifact_invalid", "/artifact", phase="association")])
    if type(data) is not bytes:
        return _result(None, [_diagnostic("phylogeny_bytes_required", artifact=artifact)])
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        return _result(None, [_diagnostic("phylogeny_artifact_sha256_mismatch", "/artifact/sha256", phase="association", artifact=artifact)])
    return None


def _parameter(artifact):
    return _result(None, [_diagnostic("phylogeny_reader_parameter_invalid", artifact=artifact)])


def _location(artifact, *, start=None, end=None, line_start=None, line_end=None, xml_path=None):
    return {"artifact": deepcopy(artifact), "byte_start_0based": start,
            "byte_end_0based_exclusive": end, "line_start_1based": line_start,
            "line_end_1based_inclusive": line_end, "xml_path": xml_path}


class _Text:
    """Character positions translated to original (including UTF-8) byte offsets."""
    def __init__(self, data, artifact, encoding):
        self.text = data.decode(encoding)
        self.artifact = artifact
        self.offsets = [0]
        for char in self.text:
            self.offsets.append(self.offsets[-1] + len(char.encode(encoding)))
        self.line_starts = [0] + [m.end() for m in re.finditer(r"\r\n|\r|\n", self.text)]

    def loc(self, start, end):
        return _location(self.artifact, start=self.offsets[start], end=self.offsets[end],
            line_start=bisect_right(self.line_starts, start),
            line_end=bisect_right(self.line_starts, max(start, end - 1)))

    def lines(self):
        cursor = 0
        result = []
        # Unlike str.splitlines(), vertical tabs are not silently new lines.
        for match in re.finditer(r"[^\r\n]*(?:\r\n|\r|\n|$)", self.text):
            if match.start() == len(self.text):
                break
            raw = match.group()
            end = match.end()
            result.append((raw.rstrip("\r\n"), cursor, end))
            cursor = end
        return result


def _decode(data, artifact, encoding):
    try:
        return _Text(data, artifact, encoding), None
    except UnicodeError:
        return None, _result(None, [_diagnostic("phylogeny_encoding_invalid", artifact=artifact)])


def _node(index, parent, location):
    return {"node_index": index, "parent_index": parent, "child_indices": [],
            "raw_label": None, "decoded_label": None, "label_token": None,
            "branch_length": None, "branch_length_token": None,
            "comments": [], "source_location": location}


class _Syntax(ValueError):
    pass


def _newick_segments(text, dialect):
    """Find semicolons outside actual quotes/comments; no regex tree splitting."""
    start = i = depth = 0
    quote = None
    segments = []
    while i < len(text):
        char = text[i]
        if depth:
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
        elif quote:
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char == "[":
            depth = 1
        elif char == "'" or char == '"' and dialect == "bvbrc_double_quoted_names":
            quote = char
        elif char == ";":
            segments.append((start, i + 1, True))
            start = i + 1
        i += 1
    if text[start:].strip():
        segments.append((start, len(text), False))
    return segments


class _NewickReader:
    def __init__(self, source, start, end, dialect, index, diagnostics):
        self.source, self.text = source, source.text
        self.start, self.end, self.i = start, end, start
        self.dialect, self.index, self.diagnostics = dialect, index, diagnostics
        self.nodes = []

    def ws(self):
        while self.i < self.end and self.text[self.i].isspace():
            self.i += 1

    def comments(self, position):
        comments = []
        self.ws()
        while self.i < self.end and self.text[self.i] == "[":
            start = self.i
            self.i += 1
            depth = 1
            while self.i < self.end and depth:
                char = self.text[self.i]
                depth += (char == "[") - (char == "]")
                self.i += 1
            if depth:
                raise _Syntax("phylogeny_newick_truncated")
            token = self.text[start:self.i]
            comments.append({"text": token[1:-1], "token": token, "position": position,
                             "location": self.source.loc(start, self.i)})
            self.ws()
        return comments

    def label(self):
        self.ws()
        start = self.i
        if self.i == self.end or self.text[self.i] in "[:,();]":
            return None, None, None
        char = self.text[self.i]
        if char == '"' and self.dialect != "bvbrc_double_quoted_names":
            raise _Syntax("phylogeny_newick_double_quote_dialect_required")
        if char in "'\"":
            quote = char
            self.i += 1
            while self.i < self.end:
                if self.text[self.i] == quote:
                    self.i += 1
                    if self.i < self.end and self.text[self.i] == quote:
                        self.i += 1
                    else:
                        token = self.text[start:self.i]
                        return token[1:-1], token[1:-1].replace(quote * 2, quote), token
                else:
                    self.i += 1
            raise _Syntax("phylogeny_newick_truncated")
        while self.i < self.end and not self.text[self.i].isspace() and self.text[self.i] not in "[]:,();":
            if self.text[self.i] in "'\"":
                raise _Syntax("phylogeny_newick_syntax_invalid")
            self.i += 1
        token = self.text[start:self.i]
        return token, token, token

    def suffix(self, node):
        node["comments"].extend(self.comments("before_label"))
        raw, decoded, token = self.label()
        node.update(raw_label=raw, decoded_label=decoded, label_token=token)
        node["comments"].extend(self.comments("after_label"))
        if self.i < self.end and self.text[self.i] == ":":
            self.i += 1
            node["comments"].extend(self.comments("after_label"))
            start = self.i
            while self.i < self.end and not self.text[self.i].isspace() and self.text[self.i] not in "[]:,();":
                self.i += 1
            token = self.text[start:self.i]
            node["branch_length_token"] = token
            node["branch_length"] = _native_number(token)
            path = f"/trees/{self.index}/nodes/{node['node_index']}/branch_length_token"
            if node["branch_length"] is None:
                self.diagnostics.append(_diagnostic("phylogeny_native_number_invalid", path, artifact=self.source.artifact))
            elif node["branch_length"] < 0:
                self.diagnostics.append(_diagnostic("phylogeny_negative_branch_length", path,
                    severity="qualification", artifact=self.source.artifact))
            node["comments"].extend(self.comments("after_length"))
        self.ws()

    def tree(self):
        self.ws()
        begin = self.i
        leading = self.comments("before_tree")
        stack, node_starts = [], []
        need_node, root_finished = True, False
        while not root_finished:
            if need_node:
                self.ws()
                start = self.i
                pre = self.comments("before_label")
                if self.i >= self.end or self.text[self.i] == ";":
                    raise _Syntax("phylogeny_newick_syntax_invalid")
                parent = stack[-1] if stack else None
                node = _node(len(self.nodes), parent, self.source.loc(start, start))
                node["comments"] = pre
                self.nodes.append(node)
                node_starts.append(start)
                if parent is not None:
                    self.nodes[parent]["child_indices"].append(node["node_index"])
                if self.text[self.i] == "(":
                    self.i += 1
                    stack.append(node["node_index"])
                    need_node = True
                    continue
                if self.text[self.i] in ",)" and not stack:
                    raise _Syntax("phylogeny_newick_syntax_invalid")
                # Missing labels on tips are real Newick syntax, not empty strings.
                self.suffix(node)
                node["source_location"] = self.source.loc(start, self.i)
                need_node = False
            if not stack:
                root_finished = True
                break
            if self.i >= self.end:
                raise _Syntax("phylogeny_newick_truncated")
            char = self.text[self.i]
            if char == ",":
                self.i += 1
                need_node = True
            elif char == ")":
                self.i += 1
                index = stack.pop()
                node = self.nodes[index]
                self.suffix(node)
                node["source_location"] = self.source.loc(node_starts[index], self.i)
                need_node = False
            else:
                raise _Syntax("phylogeny_newick_syntax_invalid")
        if self.i >= self.end:
            raise _Syntax("phylogeny_newick_truncated")
        if self.text[self.i] != ";":
            raise _Syntax("phylogeny_newick_syntax_invalid")
        self.i += 1
        self.ws()
        if self.i != self.end:
            raise _Syntax("phylogeny_newick_syntax_invalid")
        self.nodes[0]["comments"] = leading + self.nodes[0]["comments"]
        self.nodes[0]["source_location"] = self.source.loc(begin, self.end)
        markers = {c["text"].strip().upper() for c in leading if c["text"].strip().upper() in ("&R", "&U")}
        rooted = "unspecified"
        if len(markers) == 2:
            self.diagnostics.append(_diagnostic("phylogeny_newick_rooted_marker_conflict", f"/trees/{self.index}/native_rooted_marker", artifact=self.source.artifact))
        elif markers:
            rooted = "rooted" if "&R" in markers else "unrooted"
        document_id = self.source.artifact["raw_artifact_ref"] + "#tree_document"
        return validate_tree_record({"tree_id": document_id + "/tree/" + str(self.index),
            "document_id": document_id, "tree_index": self.index, "source_format": "newick",
            "root_node_index": 0, "native_rooted_marker": rooted, "nodes": self.nodes,
            "source_location": self.source.loc(begin, self.end)})


def parse_newick(data: bytes, *, artifact: dict,
                 dialect: Literal["newick", "raxml_branch_labels", "bvbrc_double_quoted_names"],
                 allow_multiple: bool = False) -> dict:
    """Read semicolon-terminated trees with original labels/comments and lengths.

    Ordinary Newick uses single quotes (doubled quote escaping). Double quotes
    require the explicit BV-BRC dialect. Bracket comments, including nested
    brackets, are retained as comments in every dialect; RAxML support remains
    uninterpreted. A complete malformed segment does not discard later trees.
    Comments after the last semicolon belong to the preceding root, after_tree;
    comments before another tree belong to that tree, before_tree.
    """
    invalid = _input(data, artifact)
    if invalid:
        return invalid
    if type(dialect) is not str or dialect not in ("newick", "raxml_branch_labels", "bvbrc_double_quoted_names") or type(allow_multiple) is not bool:
        return _parameter(artifact)
    source, invalid = _decode(data, artifact, "utf-8")
    if invalid:
        return invalid
    if not source.text.strip():
        return _result(None, [_diagnostic("phylogeny_empty_input", artifact=artifact)])
    segments = _newick_segments(source.text, dialect)
    diagnostics, trees = [], []
    complete = "complete"
    tree_segments = len(segments)
    # The trailing comment-only segment is not a second tree.
    trailing = None
    if segments and not segments[-1][2]:
        a, b, _ = segments[-1]
        probe = _NewickReader(source, a, b, dialect, tree_segments - 1, [])
        try:
            comments = probe.comments("after_tree")
            if comments and probe.i == b and len(segments) > 1:
                trailing = (comments, b)
                segments.pop()
        except _Syntax:
            pass
    if len(segments) > 1 and not allow_multiple:
        return _result(None, [_diagnostic("phylogeny_newick_multiple_disallowed", "/trees", artifact=artifact)])
    for index, (start, end, terminated) in enumerate(segments):
        if not terminated:
            diagnostics.append(_diagnostic("phylogeny_newick_truncated", "/trees", artifact=artifact))
            complete = "truncated"
            continue
        before = len(diagnostics)
        try:
            tree = _NewickReader(source, start, end, dialect, len(trees), diagnostics).tree()
            # Source index is retained even when an earlier independent tree failed.
            tree["tree_index"] = index
            tree["tree_id"] = tree["document_id"] + "/tree/" + str(index)
            trees.append(tree)
        except _Syntax as error:
            del diagnostics[before:]
            diagnostics.append(_diagnostic(str(error), "/trees", artifact=artifact))
            complete = "partial" if complete != "truncated" else complete
    if trailing is not None and trees and trees[-1]["tree_index"] == len(segments) - 1:
        comments, end = trailing
        tree = trees[-1]
        root = tree["nodes"][0]
        root["comments"].extend(comments)
        for loc in (root["source_location"], tree["source_location"]):
            loc["byte_end_0based_exclusive"] = source.offsets[end]
            loc["line_end_1based_inclusive"] = bisect_right(source.line_starts, max(0, end - 1))
    if complete == "complete" and any(d["severity"] == "error" for d in diagnostics):
        complete = "partial"
    value = {"document_id": artifact["raw_artifact_ref"] + "#tree_document", "artifact": deepcopy(artifact),
             "format": "newick", "dialect": dialect, "completeness": complete, "trees": trees}
    return _result(value, diagnostics, usable=bool(trees))


def _alignment(artifact, *, format, layout, encoding, nrows=None, ncols=None):
    return {"alignment_id": artifact["raw_artifact_ref"] + "#alignment", "artifact": deepcopy(artifact),
        "format": format, "layout": layout, "id_rule": "first_whitespace_token" if format == "aligned_fasta" else "full_phylip_label",
        "encoding": encoding, "declared_row_count": nrows, "declared_column_count": ncols,
        "observed_row_count": 0, "observed_column_count": None, "completeness": "unknown", "rows": []}


def _sequence(fragment, diagnostics, path, artifact, *, fasta=False):
    # PHYLIP uses whitespace to group symbols. FASTA whitespace is retained in
    # the original bytes and explicitly qualified before removing formatting.
    if fasta and any(char in " \t" for char in fragment):
        diagnostics.append(_diagnostic("phylogeny_alignment_whitespace_ignored", path, severity="qualification", artifact=artifact))
    sequence = fragment.replace(" ", "").replace("\t", "")
    if re.fullmatch(r"[A-Za-z*.?\-]*", sequence) is None:
        diagnostics.append(_diagnostic("phylogeny_alignment_symbol_invalid", path, artifact=artifact))
    return sequence


def read_fasta_records(data: bytes, *, artifact: dict,
                       id_rule: Literal["first_whitespace_token"],
                       encoding: Literal["ascii", "utf-8"] = "ascii") -> dict:
    """Read literal FASTA occurrences without asserting an aligned matrix.

    Case, complete headers, repeated labels and source byte locations retain
    their existing meanings. Variable sequence lengths are ordinary records.
    Format qualifications are separate from any caller's population meaning.
    """
    invalid = _input(data, artifact)
    if invalid:
        return invalid
    if id_rule != "first_whitespace_token" or encoding not in ("ascii", "utf-8"):
        return _parameter(artifact)
    source, invalid = _decode(data, artifact, encoding)
    if invalid:
        return invalid
    rows, diagnostics = [], []
    current, row_start, row_end = None, 0, 0
    for line, start, end in source.lines():
        if line.startswith(">"):
            if current is not None:
                current["source_location"] = source.loc(row_start, row_end)
            raw_header = line[1:]
            tokens = raw_header.split()
            current = {"row_index": len(rows), "raw_header": raw_header,
                "member_label": tokens[0] if tokens else "", "sequence": "", "source_location": source.loc(start, end)}
            rows.append(current)
            row_start, row_end = start, end
            if not tokens:
                diagnostics.append(_diagnostic("phylogeny_alignment_label_missing", f"/rows/{len(rows)-1}/member_label", artifact=artifact))
        elif line.strip():
            if current is None:
                diagnostics.append(_diagnostic("phylogeny_fasta_header_missing", "/rows", artifact=artifact))
            else:
                current["sequence"] += _sequence(line, diagnostics, f"/rows/{len(rows)-1}/sequence", artifact, fasta=True)
                row_end = end
    if current is not None:
        current["source_location"] = source.loc(row_start, row_end)
    if not rows:
        diagnostics.append(_diagnostic("phylogeny_empty_input", "/rows", artifact=artifact))
    errors = any(d["severity"] == "error" for d in diagnostics)
    value = {"version": "native_fasta_record_observations_v1", "artifact": deepcopy(artifact),
        "encoding": encoding, "id_rule": id_rule, "observed_record_count": len(rows),
        "completeness": "partial" if errors else "complete", "rows": rows}
    return _result(value, diagnostics, usable=bool(rows))


def parse_aligned_fasta(data: bytes, *, artifact: dict,
                        id_rule: Literal["first_whitespace_token"],
                        encoding: Literal["ascii", "utf-8"] = "ascii") -> dict:
    """Read all headers/rows, preserving case and duplicate first-token IDs.

    No alphabet or original coordinates are assigned. An empty header is an
    error. Explicit empty sequences can form a zero-column alignment; empty
    bytes do not prove a complete empty matrix. Unequal sequences stay unequal.
    """
    parsed = read_fasta_records(data, artifact=artifact, id_rule=id_rule, encoding=encoding)
    if parsed["value"] is None:
        return parsed
    value = _alignment(artifact, format="aligned_fasta", layout="fasta", encoding=encoding)
    rows, diagnostics = parsed["value"]["rows"], parsed["diagnostics"]
    value["rows"] = rows
    value["observed_row_count"] = len(rows)
    lengths = {len(row["sequence"]) for row in rows}
    if len(lengths) > 1:
        diagnostics.append(_diagnostic("phylogeny_alignment_lengths_unequal", "/rows", artifact=artifact))
    errors = any(d["severity"] == "error" for d in diagnostics)
    value["completeness"] = "partial" if errors else "complete"
    value["observed_column_count"] = next(iter(lengths)) if len(lengths) == 1 and not errors else None
    validate_alignment_document(value)
    return _result(value, diagnostics, usable=bool(rows))


def parse_relaxed_phylip(data: bytes, *, artifact: dict,
                         layout: Literal["sequential", "interleaved"],
                         continuation_ids: Literal["absent", "repeated"]) -> dict:
    """Read ASCII relaxed PHYLIP with explicit layout and continuation policy.

    Full identifiers are whitespace-delimited, never ten-character truncated.
    All sequence fragments remain in their source row, including overlong rows.
    A mismatched repeated continuation ID is not reassigned by label guessing.
    The complete native bytes retain unassociated erroneous lines. Multiple
    matrices in one artifact are not supported as one successful alignment.
    """
    invalid = _input(data, artifact)
    if invalid:
        return invalid
    if layout not in ("sequential", "interleaved") or continuation_ids not in ("absent", "repeated"):
        return _parameter(artifact)
    source, invalid = _decode(data, artifact, "ascii")
    if invalid:
        return invalid
    lines = [line for line in source.lines() if line[0].strip()]
    if not lines:
        return _result(None, [_diagnostic("phylogeny_empty_input", artifact=artifact)])
    match = re.fullmatch(r"\s*([0-9]+)\s+([0-9]+)\s*", lines[0][0])
    if match is None:
        return _result(None, [_diagnostic("phylogeny_phylip_header_invalid", artifact=artifact)])
    try:
        nrows, ncols = int(match[1]), int(match[2])
    except ValueError:
        return _result(None, [_diagnostic("phylogeny_phylip_header_invalid", artifact=artifact)])
    value = _alignment(artifact, format="relaxed_phylip", layout=layout, encoding="ascii", nrows=nrows, ncols=ncols)
    rows, diagnostics = value["rows"], []
    cursor, truncated = 1, False
    starts, ends = [], []

    def new_row(line):
        text, start, end = line
        parts = text.split(None, 1)
        label, fragment = parts[0], parts[1] if len(parts) == 2 else ""
        index = len(rows)
        sequence = _sequence(fragment, diagnostics, f"/rows/{index}/sequence", artifact)
        rows.append({"row_index": index, "raw_header": label, "member_label": label,
                     "sequence": sequence, "source_location": source.loc(start, end)})
        starts.append(start)
        ends.append(end)
        return len(sequence)

    def continuation(index, line):
        text, _, end = line
        row = rows[index]
        parts = text.split(None, 1)
        path = f"/rows/{index}/sequence"
        ends[index] = end
        if continuation_ids == "repeated":
            if parts[0] != row["member_label"]:
                diagnostics.append(_diagnostic("phylogeny_phylip_continuation_id_mismatch", f"/rows/{index}/member_label", phase="association", artifact=artifact))
                return None
            fragment = parts[1] if len(parts) == 2 else ""
        else:
            # With absent IDs all tokens are sequence groups. A group can
            # happen to spell a row label; that is not evidence of an ID.
            fragment = text
        sequence = _sequence(fragment, diagnostics, path, artifact)
        row["sequence"] += sequence
        return len(sequence)

    if layout == "sequential":
        while cursor < len(lines):
            new_row(lines[cursor])
            cursor += 1
            index = len(rows) - 1
            while len(rows[index]["sequence"]) < ncols and cursor < len(lines):
                # A wrong repeated ID could begin another named row. Keep that
                # row independently, but do not claim a correct continuation.
                if continuation_ids == "repeated" and lines[cursor][0].split(None, 1)[0] != rows[index]["member_label"]:
                    diagnostics.append(_diagnostic("phylogeny_phylip_continuation_id_mismatch", f"/rows/{index}/member_label", phase="association", artifact=artifact))
                    break
                continuation(index, lines[cursor])
                cursor += 1
            if cursor == len(lines) and len(rows[index]["sequence"]) < ncols:
                truncated = True
    else:
        widths = []
        while len(rows) < nrows and cursor < len(lines):
            widths.append(new_row(lines[cursor]))
            cursor += 1
        if widths and len(set(widths)) > 1:
            diagnostics.append(_diagnostic("phylogeny_phylip_block_width_mismatch", "/rows", artifact=artifact))
        if len(rows) < nrows:
            truncated = True
        while rows and cursor < len(lines):
            if all(len(row["sequence"]) >= ncols for row in rows):
                diagnostics.append(_diagnostic("phylogeny_phylip_trailing_data", "/rows", artifact=artifact))
            widths = []
            for index in range(len(rows)):
                if cursor == len(lines):
                    truncated = True
                    break
                widths.append(continuation(index, lines[cursor]))
                cursor += 1
            if len(widths) == len(rows) and len(set(widths)) > 1:
                diagnostics.append(_diagnostic("phylogeny_phylip_block_width_mismatch", "/rows", artifact=artifact))
    if cursor < len(lines):
        diagnostics.append(_diagnostic("phylogeny_phylip_trailing_data", "/rows", artifact=artifact))
    for index, row in enumerate(rows):
        row["source_location"] = source.loc(starts[index], ends[index])
        length = len(row["sequence"])
        if length != ncols:
            diagnostics.append(_diagnostic("phylogeny_phylip_column_count_mismatch", f"/rows/{index}/sequence", artifact=artifact))
            truncated = truncated or length < ncols
    if len(rows) != nrows:
        diagnostics.append(_diagnostic("phylogeny_phylip_row_count_mismatch", "/rows", artifact=artifact))
        truncated = truncated or len(rows) < nrows
    if not rows and ncols:
        diagnostics.append(_diagnostic("phylogeny_phylip_column_count_mismatch", "/declared_column_count", artifact=artifact))
    if truncated:
        diagnostics.append(_diagnostic("phylogeny_phylip_truncated", "/rows", artifact=artifact))
    errors = any(d["severity"] == "error" for d in diagnostics)
    value["observed_row_count"] = sum(len(row["sequence"]) == ncols for row in rows)
    value["observed_column_count"] = ncols if not errors else None
    value["completeness"] = "truncated" if truncated else "partial" if errors else "complete"
    validate_alignment_document(value)
    return _result(value, diagnostics, usable=bool(rows) or nrows == ncols == 0 and not errors)


def parse_raxml_partitions(data: bytes, *, artifact: dict,
                           alignment_column_count: int) -> dict:
    """Read actual one-based inclusive ranges and normalize their site sets.

    Normalized columns are sorted unique zero-based indices. Native range order
    remains intact; repeated membership, including within a partition, is
    diagnosed. Out-of-bounds columns are retained, never clipped to the supplied
    actual alignment denominator. Coverage holes and overlap prevent complete
    whole-matrix partition use. No model token supplies an inferred alphabet.
    """
    invalid = _input(data, artifact)
    if invalid:
        return invalid
    if type(alignment_column_count) is not int or alignment_column_count < 0:
        return _parameter(artifact)
    source, invalid = _decode(data, artifact, "utf-8")
    if invalid:
        return invalid
    partitions, diagnostics, counts = [], [], Counter()
    source_index = 0
    for line, start, end in source.lines():
        if not line.strip():
            continue
        index = source_index
        source_index += 1
        match = re.fullmatch(r"\s*([^,=\s]+)\s*,\s*([^=]+?)\s*=\s*(.+?)\s*", line)
        if match is None:
            diagnostics.append(_diagnostic("phylogeny_partition_syntax_invalid", "/partitions", artifact=artifact))
            continue
        ranges, columns = [], []
        bad = False
        for token in match[3].split(","):
            interval = re.fullmatch(r"\s*([0-9]+)(?:\s*-\s*([0-9]+))?(?:\s*\\\s*([0-9]+))?\s*", token)
            if interval is None:
                bad = True
                break
            try:
                first = int(interval[1])
                last = int(interval[2]) if interval[2] is not None else first
                step = int(interval[3]) if interval[3] is not None else 1
            except ValueError:
                bad = True
                break
            if first < 1 or last < first or step < 1:
                bad = True
                break
            ranges.append({"start_1based": first, "end_1based_inclusive": last, "step": step})
            columns.extend(range(first - 1, last, step))
        if bad:
            diagnostics.append(_diagnostic("phylogeny_partition_range_invalid", "/partitions", artifact=artifact))
            continue
        row_index = len(partitions)
        partitions.append({"partition_index": index, "name": match[2].strip(), "model_token": match[1],
            "native_ranges": ranges, "columns_0based": sorted(set(columns)), "source_location": source.loc(start, end)})
        counts.update(columns)
        if any(c >= alignment_column_count for c in columns):
            diagnostics.append(_diagnostic("phylogeny_partition_out_of_bounds", f"/partitions/{row_index}/columns_0based", artifact=artifact))
    holes = [i for i in range(alignment_column_count) if i not in counts]
    overlaps = sorted(i for i, count in counts.items() if count > 1)
    if overlaps:
        diagnostics.append(_diagnostic("phylogeny_partition_overlap", "/overlapping_columns_0based", artifact=artifact))
    if holes:
        diagnostics.append(_diagnostic("phylogeny_partition_holes", "/uncovered_columns_0based", artifact=artifact))
    if not partitions:
        diagnostics.append(_diagnostic("phylogeny_empty_input", "/partitions", artifact=artifact))
    value = {"document_id": artifact["raw_artifact_ref"] + "#partitions", "artifact": deepcopy(artifact),
        "format": "raxml_partitions", "alignment_column_count": alignment_column_count,
        "completeness": "partial" if diagnostics else "complete", "partitions": partitions,
        "uncovered_columns_0based": holes, "overlapping_columns_0based": overlaps}
    return _result(value, diagnostics, usable=bool(partitions))


class _XMLForbidden(ValueError):
    pass


class _XMLReader:
    """Expat never resolves a DTD, external entity or network resource here."""
    def __init__(self, data, artifact):
        self.data, self.artifact = data, artifact
        self.encoding = ("utf-16-le" if data.startswith((b"\xff\xfe", b"<\x00")) else
                         "utf-16-be" if data.startswith((b"\xfe\xff", b"\x00<")) else "utf-8")
        self.root, self.stack = None, []
        self.parser = expat.ParserCreate(namespace_separator="\x1f")
        self.parser.ordered_attributes = True
        self.parser.StartElementHandler = self.start
        self.parser.EndElementHandler = self.end
        self.parser.CharacterDataHandler = self.text
        self.parser.CommentHandler = self.comment
        self.parser.XmlDeclHandler = self.declaration
        self.parser.StartDoctypeDeclHandler = self.forbid
        self.parser.EntityDeclHandler = self.forbid
        self.parser.ExternalEntityRefHandler = self.forbid
        self.parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)

    @staticmethod
    def forbid(*args):
        raise _XMLForbidden()

    @staticmethod
    def expanded(name):
        return "{" + name.replace("\x1f", "}", 1) if "\x1f" in name else name

    def declaration(self, version, encoding, standalone):
        if encoding and encoding.lower().replace("_", "-") not in ("utf-16", "utf16"):
            self.encoding = encoding

    def tag_end(self, start):
        unit = 2 if self.encoding.lower().startswith("utf-16") else 1
        quotes = {c.encode(self.encoding) for c in ("'", '"')}
        close = ">".encode(self.encoding)
        cursor, quoted = start, None
        while cursor < len(self.data):
            char = self.data[cursor:cursor + unit]
            if quoted:
                if char == quoted:
                    quoted = None
            elif char in quotes:
                quoted = char
            elif char == close:
                return cursor + unit
            cursor += unit
        return len(self.data)

    def start(self, name, attrs):
        tag = self.expanded(name)
        parent = self.stack[-1] if self.stack else None
        byte_start = self.parser.CurrentByteIndex
        open_end = self.tag_end(byte_start)
        opening = self.data[byte_start:open_end].decode(self.encoding)
        ordinal = 1 + sum(c["tag"] == tag for c in parent["children"]) if parent is not None else 1
        element = {"tag": tag, "attributes": [(self.expanded(attrs[i]), attrs[i+1]) for i in range(0, len(attrs), 2)],
            "children": [], "text": [], "comments": [], "closed": False,
            "path": (parent["path"] if parent else "") + "/" + tag + f"[{ordinal}]",
            "line_start": self.parser.CurrentLineNumber, "line_end": None,
            "start": byte_start, "open_end": open_end, "opening": opening,
            "content_end": None, "end": None, "self_closing": opening.endswith("/>")}
        if parent is None:
            self.root = element
        else:
            parent["children"].append(element)
        self.stack.append(element)

    def end(self, name):
        element = self.stack.pop()
        element["closed"] = True
        element["line_end"] = self.parser.CurrentLineNumber
        element["content_end"] = element["open_end"] if element["self_closing"] else self.parser.CurrentByteIndex
        element["end"] = element["open_end"] if element["self_closing"] else self.tag_end(self.parser.CurrentByteIndex)

    def text(self, text):
        if self.stack:
            self.stack[-1]["text"].append(text)

    def comment(self, text):
        if self.stack:
            # XML positions use their real lines; XML whitespace/entity decoding
            # is handled by Expat, never by a second source acquisition.
            start = self.parser.CurrentByteIndex
            close = "-->".encode(self.encoding)
            end = self.data.index(close, start) + len(close)
            self.stack[-1]["comments"].append({"text": text, "token": self.data[start:end].decode(self.encoding),
                "position": "before_label" if not self.stack[-1]["children"] else "after_label",
                "location": _location(self.artifact, start=start, end=end, line_start=self.parser.CurrentLineNumber,
                    line_end=self.parser.CurrentLineNumber + text.count("\n"))})

    def loc(self, element):
        return _location(self.artifact, start=element["start"], end=element["end"], line_start=element["line_start"],
            line_end=element["line_end"] or element["line_start"], xml_path=element["path"])

    def scalar(self, element):
        return self.data[element["open_end"]:element["content_end"]].decode(self.encoding)


def _xml_name(tag):
    return tag.rsplit("}", 1)[-1]


def _xml_namespace(tag):
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else None


def _xml_owned(element, namespace):
    """Source-order descendants except child clades, which own their metadata."""
    stack = list(reversed(element["children"]))
    while stack:
        child = stack.pop()
        if _xml_name(child["tag"]) == "clade" and _xml_namespace(child["tag"]) == namespace:
            continue
        yield child
        stack.extend(reversed(child["children"]))


def _xml_property(element, reader):
    attrs = dict(element["attributes"])
    return {"ref": attrs.get("ref"), "datatype": attrs.get("datatype"), "applies_to": attrs.get("applies_to"),
            "value": "".join(element["text"]), "source_location": reader.loc(element)}


def _xml_tree(element, reader, index, namespace, diagnostics, output_index):
    artifact = reader.artifact
    prefix = f"/trees/{output_index}"
    direct = lambda e, name: [c for c in e["children"] if _xml_name(c["tag"]) == name and _xml_namespace(c["tag"]) == namespace]
    roots = direct(element, "clade")
    if len(roots) != 1:
        diagnostics.append(_diagnostic("phylogeny_phyloxml_root_clade_invalid", "/trees", artifact=artifact))
        return None
    nodes, annotations, stack = [], [], [(roots[0], None)]
    attributes = dict(element["attributes"])
    rooted = "unspecified"
    if "rooted" in attributes:
        if attributes["rooted"] in ("true", "1"):
            rooted = "rooted"
        elif attributes["rooted"] in ("false", "0"):
            rooted = "unrooted"
        else:
            diagnostics.append(_diagnostic("phylogeny_phyloxml_rooted_attribute_invalid", prefix + "/native_attributes", artifact=artifact))
    known = {"name", "id", "node_id", "accession", "confidence", "property", "branch_length", "sequence",
             "taxonomy", "scientific_name", "common_name", "code", "synonym", "symbol", "mol_seq", "uri", "annotation",
             "description", "events", "type", "duplications", "speciations", "losses", "date", "desc", "value", "unit"}
    while stack:
        clade, parent = stack.pop()
        node_index = len(nodes)
        node = _node(node_index, parent, reader.loc(clade))
        nodes.append(node)
        if parent is not None:
            nodes[parent]["child_indices"].append(node_index)
        names = direct(clade, "name")
        if names:
            label = "".join(names[0]["text"])
            if not names[0]["children"]:
                token = reader.scalar(names[0])
                node.update(raw_label=token, decoded_label=label, label_token=token)
        lengths = direct(clade, "branch_length")
        # PHYLOXML supports an attribute as well as the element. Both at once
        # are ambiguous and cannot be collapsed into the single stored cell.
        clade_attrs = dict(clade["attributes"])
        if len(lengths) + ("branch_length" in clade_attrs) > 1:
            diagnostics.append(_diagnostic("phylogeny_phyloxml_branch_length_multiple", "/trees", artifact=artifact))
            return None
        token = reader.scalar(lengths[0]) if lengths else None
        decoded_token = "".join(lengths[0]["text"]) if lengths else clade_attrs.get("branch_length")
        if not lengths and "branch_length" in clade_attrs:
            attr_match = re.search(r"\sbranch_length\s*=\s*(['\"])(.*?)\1", clade["opening"], re.DOTALL)
            token = attr_match[2]
        if token is not None:
            node["branch_length_token"] = token
            node["branch_length"] = _native_number(decoded_token) if not lengths or not lengths[0]["children"] else None
            path = prefix + f"/tree/nodes/{node_index}/branch_length_token"
            if node["branch_length"] is None:
                diagnostics.append(_diagnostic("phylogeny_native_number_invalid", path, artifact=artifact))
            elif node["branch_length"] < 0:
                diagnostics.append(_diagnostic("phylogeny_negative_branch_length", path, severity="qualification", artifact=artifact))
        annotation = {"node_index": node_index, "names": [], "ids": [], "accessions": [],
            "confidences": [], "properties": [], "source_location": reader.loc(clade)}
        annotations.append(annotation)
        if set(clade_attrs) - {"branch_length"}:
            diagnostics.append(_diagnostic("phylogeny_phyloxml_element_uninterpreted", prefix + f"/annotations/{node_index}", severity="qualification", artifact=artifact))
        node["comments"].extend(deepcopy(clade["comments"]))
        for child in _xml_owned(clade, namespace):
            name, attrs = _xml_name(child["tag"]), dict(child["attributes"])
            text = "".join(child["text"])
            if _xml_namespace(child["tag"]) != namespace or name not in known:
                diagnostics.append(_diagnostic("phylogeny_phyloxml_element_uninterpreted", prefix + f"/annotations/{node_index}", severity="qualification", artifact=artifact))
                continue
            if name in {"name", "id", "node_id", "accession", "confidence", "property", "branch_length"} and child["children"]:
                diagnostics.append(_diagnostic("phylogeny_phyloxml_nested_scalar", prefix + f"/annotations/{node_index}", artifact=artifact))
            stored_attrs = {"confidence": {"type"}, "property": {"ref", "datatype", "applies_to"}, "accession": {"source"}}.get(name, set())
            if set(attrs) - stored_attrs:
                diagnostics.append(_diagnostic("phylogeny_phyloxml_element_uninterpreted", prefix + f"/annotations/{node_index}", severity="qualification", artifact=artifact))
            if name in ("name", "scientific_name", "common_name", "synonym"):
                annotation["names"].append(text)
            elif name in ("id", "node_id"):
                annotation["ids"].append(text)
            elif name == "accession":
                annotation["accessions"].append({"source": attrs.get("source"), "value": text, "source_location": reader.loc(child)})
            elif name == "property":
                annotation["properties"].append(_xml_property(child, reader))
            elif name == "confidence":
                number = _native_number(text) if not child["children"] else None
                annotation["confidences"].append({"type": attrs.get("type"), "value": number, "raw_token": reader.scalar(child),
                    "source_location": reader.loc(child)})
                if number is None:
                    path = prefix + f"/annotations/{node_index}/confidences/{len(annotation['confidences'])-1}/raw_token"
                    diagnostics.append(_diagnostic("phylogeny_native_number_invalid", path, artifact=artifact))
            elif name not in ("branch_length", "sequence", "taxonomy"):
                diagnostics.append(_diagnostic("phylogeny_phyloxml_element_uninterpreted", prefix + f"/annotations/{node_index}", severity="qualification", artifact=artifact))
        stack.extend((child, node_index) for child in reversed(direct(clade, "clade")))
    docid = artifact["raw_artifact_ref"] + "#phyloxml"
    tree = validate_tree_record({"tree_id": docid + "/tree/" + str(index), "document_id": docid,
        "tree_index": index, "source_format": "phyloxml", "root_node_index": 0,
        "native_rooted_marker": rooted, "nodes": nodes, "source_location": reader.loc(element)})
    properties = []
    for child in _xml_owned(element, namespace):
        if _xml_name(child["tag"]) == "property" and _xml_namespace(child["tag"]) == namespace:
            properties.append(_xml_property(child, reader))
        else:
            diagnostics.append(_diagnostic("phylogeny_phyloxml_element_uninterpreted", prefix + "/tree/source_location", severity="qualification", artifact=artifact))
    return {"tree": tree, "annotations": annotations, "properties": properties,
            "native_attributes": [{"name": name, "value": val} for name, val in element["attributes"]]}


def parse_phyloxml(data: bytes, *, artifact: dict) -> dict:
    """Read namespace-aware phyloXML without any DTD/entity/network resolution.

    Native generic support stays generic. Invalid numeric tokens retain null
    values and their original character data. Repeated names/properties are
    arrays, never flattened or joined by a guessed ID. Completed independent
    phylogenies survive a later XML syntax/truncation failure. Unknown XML data
    remains in the caller's native artifact with an uninterpreted qualification.
    """
    invalid = _input(data, artifact)
    if invalid:
        return invalid
    if not data.strip():
        return _result(None, [_diagnostic("phylogeny_empty_input", artifact=artifact)])
    reader = _XMLReader(data, artifact)
    diagnostics, truncated = [], False
    try:
        reader.parser.Parse(data, True)
    except _XMLForbidden:
        return _result(None, [_diagnostic("phylogeny_phyloxml_dtd_forbidden", artifact=artifact)])
    except (UnicodeError, LookupError, ValueError):
        return _result(None, [_diagnostic("phylogeny_encoding_invalid", artifact=artifact)])
    except expat.ExpatError as error:
        truncated_codes = {expat.errors.codes[name] for name in (expat.errors.XML_ERROR_NO_ELEMENTS,
            expat.errors.XML_ERROR_UNCLOSED_TOKEN, expat.errors.XML_ERROR_PARTIAL_CHAR,
            expat.errors.XML_ERROR_UNCLOSED_CDATA_SECTION)}
        truncated = error.code in truncated_codes
        diagnostics.append(_diagnostic("phylogeny_phyloxml_truncated" if truncated else "phylogeny_phyloxml_syntax_invalid", artifact=artifact))
    root = reader.root
    if root is None or _xml_name(root["tag"]) != "phyloxml":
        diagnostics.append(_diagnostic("phylogeny_phyloxml_root_invalid", artifact=artifact))
        return _result(None, diagnostics)
    namespace = _xml_namespace(root["tag"])
    if namespace not in (None, "http://www.phyloxml.org"):
        diagnostics.append(_diagnostic("phylogeny_phyloxml_namespace_unsupported", artifact=artifact))
        return _result(None, diagnostics)
    trees, source_index = [], 0
    for element in root["children"]:
        if _xml_name(element["tag"]) == "phylogeny" and _xml_namespace(element["tag"]) == namespace:
            index = source_index
            source_index += 1
            if element["closed"]:
                before = len(diagnostics)
                tree = _xml_tree(element, reader, index, namespace, diagnostics, len(trees))
                if tree is not None:
                    trees.append(tree)
                else:
                    # Per-node paths must not point into a skipped tree.
                    diagnostics[before:] = [d for d in diagnostics[before:] if d["path"] == "/trees"]
        else:
            diagnostics.append(_diagnostic("phylogeny_phyloxml_element_uninterpreted", severity="qualification", artifact=artifact))
    if not trees:
        diagnostics.append(_diagnostic("phylogeny_phyloxml_trees_missing", "/trees", artifact=artifact))
    errors = any(d["severity"] == "error" for d in diagnostics)
    value = {"document_id": artifact["raw_artifact_ref"] + "#phyloxml", "artifact": deepcopy(artifact),
        "format": "phyloxml", "namespace": namespace, "version": dict(root["attributes"]).get("version"),
        "completeness": "truncated" if truncated else "partial" if errors else "complete", "trees": trees}
    return _result(value, diagnostics, usable=bool(trees))


__all__ = ["parse_newick", "read_fasta_records", "parse_aligned_fasta", "parse_relaxed_phylip", "parse_raxml_partitions", "parse_phyloxml"]
