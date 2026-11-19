"""Pure validators for the frozen phylogeny stored-format contracts.

Validation does not authenticate custody or read source bytes. The byte readers
check their supplied digests. These checks establish closed shapes, native
token/value consistency and internal references for saved-object calculations.
The returned object is detached; callers' objects are never modified.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
from xml.parsers import expat


_LOCATION_KEYS = frozenset({"artifact", "byte_start_0based", "byte_end_0based_exclusive",
    "line_start_1based", "line_end_1based_inclusive", "xml_path"})
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_COMPLETENESS = ("complete", "partial", "truncated", "unknown")


def _fail(code):
    raise ValueError("phylogeny_" + code)


def _shape(value, keys, code):
    if type(value) is not dict or set(value) != set(keys):
        _fail(code)


def _text(value, *, nonempty=False):
    return type(value) is str and (bool(value) or not nonempty)


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _finite(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def _native_number(token):
    """Null for nonfinite/underflowed tokens; never turn a nonzero into zero."""
    if type(token) is not str or _NUMBER.fullmatch(token.strip()) is None:
        return None
    try:
        value = float(token.strip())
    except (ValueError, OverflowError):
        return None
    mantissa = token.strip().lower().split("e")[0]
    if not math.isfinite(value) or value == 0 and re.search(r"[1-9]", mantissa):
        return None
    return value


def _artifact(value):
    _shape(value, {"raw_artifact_ref", "source_ref", "sha256"}, "artifact_invalid")
    if (not _text(value["raw_artifact_ref"], nonempty=True)
            or not _text(value["source_ref"], nonempty=True)
            or not _text(value["sha256"])
            or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None):
        _fail("artifact_invalid")


def _location(value, *, artifact=None):
    _shape(value, _LOCATION_KEYS, "source_location_invalid")
    _artifact(value["artifact"])
    if artifact is not None and value["artifact"] != artifact:
        _fail("source_artifact_conflict")
    present = False
    for start, end, minimum in (("byte_start_0based", "byte_end_0based_exclusive", 0),
                                ("line_start_1based", "line_end_1based_inclusive", 1)):
        a, b = value[start], value[end]
        if a is None and b is None:
            continue
        if not _integer(a, minimum) or not _integer(b, minimum) or b < a:
            _fail("source_location_invalid")
        present = True
    path = value["xml_path"]
    if path is not None:
        if not _text(path, nonempty=True) or not path.startswith("/"):
            _fail("source_location_invalid")
        present = True
    if not present:
        _fail("source_location_missing")


def _contained(inner, outer):
    for start, end in (("byte_start_0based", "byte_end_0based_exclusive"),
                       ("line_start_1based", "line_end_1based_inclusive")):
        if inner[start] is not None and outer[start] is not None:
            if inner[start] < outer[start] or inner[end] > outer[end]:
                _fail("source_location_outside_record")


def _xml_scalar_text(token):
    """Decode retained XML scalar syntax without allowing elements or entities.

    Only XML's predefined/numeric references and CDATA can contribute text.
    DTD/external entities cannot occur inside the wrapper, and handlers also
    reject them explicitly. This operates solely on supplied text.
    """
    parser = expat.ParserCreate()
    parts, depth = [], 0

    def forbid(*args):
        raise ValueError("xml_scalar_invalid")

    def start(name, attrs):
        nonlocal depth
        depth += 1
        if depth != 1 or name != "scalar" or attrs:
            forbid()

    def end(name):
        nonlocal depth
        depth -= 1

    parser.StartElementHandler, parser.EndElementHandler = start, end
    parser.CharacterDataHandler = parts.append
    parser.StartDoctypeDeclHandler = parser.EntityDeclHandler = parser.ExternalEntityRefHandler = forbid
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        parser.Parse("<scalar>" + token + "</scalar>", True)
    except (expat.ExpatError, ValueError):
        return None
    return "".join(parts)


def _number_pair(number, token, *, xml=False):
    if token is None:
        if number is not None:
            _fail("branch_length_token_missing")
    elif type(token) is not str:
        _fail("branch_length_token_invalid")
    elif number is not None:
        parsed = _native_number(_xml_scalar_text(token) if xml else token)
        if not _finite(number) or parsed is None or number != parsed:
            _fail("branch_length_token_conflict")
    elif _native_number(_xml_scalar_text(token) if xml else token) is not None:
        _fail("branch_length_value_missing")


def validate_tree_record(value: dict) -> dict:
    """Validate one closed TreeRecord and its connected, preorder topology."""
    _shape(value, {"tree_id", "document_id", "tree_index", "source_format",
        "root_node_index", "native_rooted_marker", "nodes", "source_location"},
        "tree_record_shape_invalid")
    _location(value["source_location"])
    artifact = value["source_location"]["artifact"]
    if value["source_format"] not in ("newick", "phyloxml"):
        _fail("tree_format_invalid")
    suffix = "#tree_document" if value["source_format"] == "newick" else "#phyloxml"
    if (not _integer(value["tree_index"])
            or value["document_id"] != artifact["raw_artifact_ref"] + suffix
            or value["tree_id"] != value["document_id"] + "/tree/" + str(value["tree_index"])):
        _fail("tree_identity_invalid")
    if value["native_rooted_marker"] not in ("rooted", "unrooted", "unspecified"):
        _fail("rooted_marker_invalid")
    nodes = value["nodes"]
    if type(nodes) is not list or not nodes or type(value["root_node_index"]) is not int or value["root_node_index"] != 0:
        _fail("tree_nodes_invalid")
    for index, node in enumerate(nodes):
        _shape(node, {"node_index", "parent_index", "child_indices", "raw_label",
            "decoded_label", "label_token", "branch_length", "branch_length_token",
            "comments", "source_location"}, "tree_node_shape_invalid")
        if not _integer(node["node_index"]) or node["node_index"] != index:
            _fail("node_index_invalid")
        parent = node["parent_index"]
        if index == 0:
            if parent is not None:
                _fail("root_parent_invalid")
        elif not _integer(parent) or parent >= index:
            _fail("node_parent_invalid")
        children = node["child_indices"]
        if (type(children) is not list or any(not _integer(x) or not index < x < len(nodes) for x in children)
                or len(set(children)) != len(children)):
            _fail("node_children_invalid")
        labels = [node[k] for k in ("raw_label", "decoded_label", "label_token")]
        if not (all(x is None for x in labels) or all(type(x) is str for x in labels)):
            _fail("node_label_invalid")
        if labels[0] is not None and value["source_format"] == "newick":
            raw, decoded, token = labels
            if token.startswith(("'", '"')):
                quote = token[0]
                if len(token) < 2 or not token.endswith(quote) or raw != token[1:-1] or decoded != raw.replace(quote * 2, quote):
                    _fail("node_label_token_conflict")
            elif token != raw or raw != decoded:
                _fail("node_label_token_conflict")
        if labels[0] is not None and value["source_format"] == "phyloxml":
            if labels[0] != labels[2] or _xml_scalar_text(labels[2]) != labels[1]:
                _fail("node_label_token_conflict")
        _number_pair(node["branch_length"], node["branch_length_token"], xml=value["source_format"] == "phyloxml")
        _location(node["source_location"], artifact=artifact)
        _contained(node["source_location"], value["source_location"])
        if type(node["comments"]) is not list:
            _fail("node_comments_invalid")
        for comment in node["comments"]:
            _shape(comment, {"text", "token", "position", "location"}, "comment_shape_invalid")
            if (not _text(comment["text"]) or not _text(comment["token"])
                    or comment["position"] not in ("before_label", "after_label", "after_length", "before_tree", "after_tree")):
                _fail("comment_invalid")
            if value["source_format"] == "newick" and comment["token"] != "[" + comment["text"] + "]":
                _fail("comment_token_conflict")
            _location(comment["location"], artifact=artifact)
            _contained(comment["location"], node["source_location"])
    traversal, stack, seen = [], [0], set()
    while stack:
        index = stack.pop()
        if index in seen:
            _fail("tree_topology_invalid")
        seen.add(index)
        traversal.append(index)
        for child in nodes[index]["child_indices"]:
            if nodes[child]["parent_index"] != index:
                _fail("tree_topology_invalid")
        stack.extend(reversed(nodes[index]["child_indices"]))
    if traversal != list(range(len(nodes))):
        _fail("tree_preorder_invalid")
    return deepcopy(value)


def validate_alignment_document(value: dict) -> dict:
    """Validate actual rows, incomplete matrices and exact declared dimensions.

    In incomplete PHYLIP, observed_row_count counts rows of the declared length;
    all partially read rows still occur in rows. A null column count prevents
    treating an incomplete or unequal matrix as a complete population.
    """
    _shape(value, {"alignment_id", "artifact", "format", "layout", "id_rule", "encoding",
        "declared_row_count", "declared_column_count", "observed_row_count",
        "observed_column_count", "completeness", "rows"}, "alignment_shape_invalid")
    _artifact(value["artifact"])
    if value["alignment_id"] != value["artifact"]["raw_artifact_ref"] + "#alignment":
        _fail("alignment_identity_invalid")
    if value["completeness"] not in _COMPLETENESS or value["encoding"] not in ("ascii", "utf-8"):
        _fail("alignment_metadata_invalid")
    if value["format"] == "aligned_fasta":
        if (value["layout"] != "fasta" or value["id_rule"] != "first_whitespace_token"
                or value["declared_row_count"] is not None or value["declared_column_count"] is not None):
            _fail("alignment_metadata_invalid")
    elif value["format"] == "relaxed_phylip":
        if (value["layout"] not in ("sequential", "interleaved") or value["id_rule"] != "full_phylip_label"
                or value["encoding"] != "ascii" or not _integer(value["declared_row_count"])
                or not _integer(value["declared_column_count"])):
            _fail("alignment_metadata_invalid")
    else:
        _fail("alignment_format_invalid")
    if type(value["rows"]) is not list:
        _fail("alignment_rows_invalid")
    lengths = []
    for index, row in enumerate(value["rows"]):
        _shape(row, {"row_index", "raw_header", "member_label", "sequence", "source_location"}, "alignment_row_shape_invalid")
        if type(row["row_index"]) is not int or row["row_index"] != index:
            _fail("row_index_invalid")
        if any(type(row[key]) is not str for key in ("raw_header", "member_label", "sequence")):
            _fail("alignment_row_invalid")
        if value["encoding"] == "ascii" and any(not row[key].isascii() for key in ("raw_header", "member_label", "sequence")):
            _fail("alignment_encoding_conflict")
        if value["format"] == "aligned_fasta":
            expected = row["raw_header"].split()
            if row["member_label"] != (expected[0] if expected else ""):
                _fail("alignment_label_conflict")
        elif row["raw_header"] != row["member_label"] or any(c.isspace() for c in row["member_label"]):
            _fail("alignment_label_conflict")
        _location(row["source_location"], artifact=value["artifact"])
        lengths.append(len(row["sequence"]))
    nrows, columns = value["observed_row_count"], value["observed_column_count"]
    if not _integer(nrows) or columns is not None and not _integer(columns):
        _fail("alignment_dimensions_invalid")
    expected_rows = len(lengths) if value["format"] == "aligned_fasta" else sum(x == value["declared_column_count"] for x in lengths)
    if nrows != expected_rows:
        _fail("alignment_row_count_conflict")
    if columns is not None:
        if any(x != columns for x in lengths) or not lengths and columns != 0:
            _fail("alignment_column_count_conflict")
        if value["format"] == "relaxed_phylip" and (nrows != value["declared_row_count"] or columns != value["declared_column_count"]):
            _fail("alignment_declared_dimensions_conflict")
        if not lengths and value["completeness"] != "complete":
            _fail("alignment_empty_completeness_conflict")
    if value["completeness"] == "complete":
        if columns is None or any(not row["member_label"] for row in value["rows"]):
            _fail("alignment_complete_dimensions_missing")
        if value["format"] == "relaxed_phylip" and (len(lengths) != value["declared_row_count"] or nrows != len(lengths)):
            _fail("alignment_declared_dimensions_conflict")
    return deepcopy(value)


__all__ = ["validate_tree_record", "validate_alignment_document"]
