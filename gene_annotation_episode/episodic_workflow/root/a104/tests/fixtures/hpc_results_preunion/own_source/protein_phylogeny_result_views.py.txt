"""Literal selected tree values, with private custody addresses kept opaque."""
from collections.abc import Mapping
from copy import deepcopy
import json

from .protein_phylogeny_result_contracts import PACKET_VERSION, validate_phylogeny_return, validate_phylogeny_value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def select_protein_phylogeny_values(value):
    if not isinstance(value, Mapping) or value.get("version") != PACKET_VERSION:
        return None
    try:
        value = _plain(value)
        return (validate_phylogeny_return if "source_ref" in value else validate_phylogeny_value)(value)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        return None


def _literal(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _table(headers, rows):
    def cell(value):
        return _literal(value).replace("|", "\\|").replace("\n", "\\n").replace("\r", "\\r")
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)])


def _file(file):
    return None if file is None else {key: file[key] for key in ("format", "size_bytes")}


def _location(value):
    return None if value is None else {key: deepcopy(child) for key, child in value.items() if key != "artifact"}


def _quantity(value, population):
    value = deepcopy(value)
    value["population_ref"] = population
    value["evidence"] = ["retained quantity evidence" for _ in value["evidence"]]
    return value


def render_protein_phylogeny_result(value, number=1):
    packet = select_protein_phylogeny_values(value)
    if packet is None:
        raise ValueError("protein_phylogeny_presentation_value_invalid")
    context = packet["context"]
    trace = {key: deepcopy(item) for key, item in context["support_trace"].items() if key != "report_file"}
    trace["report_file"] = _file(context["support_trace"]["report_file"])
    parts = ["Selected molecular result " + str(number), "", _table(("Result property", "Supplied value"), [
        ("Callable result Source", packet.get("source_ref")), ("Operation", "analyze_protein_phylogeny"),
        ("Selected tree/node/distance records", packet["selection"]), ("Input mode", context["input_mode"]),
        ("Input File representation", _file(context["input_file"])),
        ("Input Source association", None if context["input_source_ref"] is None else "received input Source"),
        ("Alignment File representation", _file(context["alignment_file"])),
        ("MUSCLE parameters", context["muscle_parameters"]), ("IQ-TREE parameters", context["iqtree_parameters"]),
        ("Alignment execution", context["alignment_execution"]), ("IQ-TREE execution", context["iqtree_execution"]),
        ("Branch-length unit", context["branch_unit"]), ("Support command/report trace", trace),
        ("Requested node pairs", packet["pair_requests"]), ("Tree record accounting", packet["accounting"])]), "",
        context["interpretation"], "Native tip labels remain literal. Their biological identities and reference-function "
        "associations are supplied and interpreted by the parent. Node zero describes the stored representation; "
        "it does not establish a biological root. Unknown support meaning remains unknown."]
    parts.extend(["", "Native output capture and parsing", "", _table(
        ("Native role", "File representation", "Capture extent", "Parser status", "Document completeness", "Retained trees"),
        [(row["role"], _file(row["file"]), row["capture"], row["parser_status"], row["document_completeness"],
            row["retained_tree_count"]) for row in context["outputs"]])])
    split_labels = {}
    for row in packet["trees"]:
        tree, population = row["tree"], row["leaf_population"]
        label = row["role"] + "/tree/" + str(tree["tree_index"])
        pop_label = label + "/whole_tree_tips"
        summary = {key: _quantity(item, pop_label) for key, item in row["summary"].items()
            if key not in ("tree_id", "population_id")}
        parts.extend(["", "Retained tree " + label, "", _table(("Property", "Supplied value"), [
            ("Source format", tree["source_format"]), ("Root node index in representation", tree["root_node_index"]),
            ("Native rooted marker", tree["native_rooted_marker"]),
            ("Original tree location", _location(tree["source_location"])),
            ("Whole-tree tip node indices", population["node_indices"]),
            ("Tip population completeness", population["completeness"]),
            ("Scientific quantities", summary), ("Displayed record accounting", row["accounting"])]), "",
            "Scalar quantities retain the whole-tree population even when the displayed node or distance view is empty."])
        nodes = []
        for entry in row["nodes"]:
            node, branch = entry["node"], entry["branch"]
            shown = None
            if branch is not None:
                split = branch["split_id"]
                if split is not None and split not in split_labels:
                    split_labels[split] = "retained split " + str(len(split_labels) + 1)
                shown = dict(node_index=branch["node_index"], split_association=None if split is None else split_labels[split],
                    length=_quantity(branch["length"], pop_label),
                    native_support_observations=[label + "/node/" + str(node["node_index"]) + "/support/" + str(i)
                        for i, _ in enumerate(branch["native_support_observation_ids"])],
                    support_method=branch["support_method"], support_scale=branch["support_scale"],
                    support_rescaled=_quantity(branch["support_rescaled"], pop_label))
            comments = [{**{key: item for key, item in comment.items() if key != "location"},
                "location": _location(comment["location"])} for comment in node["comments"]]
            nodes.append((node["node_index"], node["parent_index"], node["child_indices"], node["raw_label"],
                node["decoded_label"], node["label_token"], node["branch_length"], node["branch_length_token"],
                comments, _location(node["source_location"]), shown))
        parts.extend(["", "Selected literal native nodes and branch values", "", _table(
            ("Node index", "Parent", "Children", "Raw label", "Decoded label", "Original label token", "Branch length",
                "Original length token", "Comments", "Original location", "Retained branch quantities"), nodes) if nodes else "[]",
            "", "Selected retained pair distances", "", _table(("Node A", "Node B", "Quantity"), [
                (pair["node_a"], pair["node_b"], _quantity(pair["value"], pop_label)) for pair in row["distances"]])
                if row["distances"] else "[]"])
    issues = context["issues"]
    def issue_path(path):
        for row in packet["trees"]:
            prefix = "/trees/" + row["tree"]["tree_id"]
            if path == prefix or path.startswith(prefix + "/"):
                return "/trees/" + row["role"] + "/" + str(row["tree"]["tree_index"]) + path[len(prefix):]
        return path
    parts.extend(["", "Retained issues and qualifications", "", _table(("Code", "Phase", "Path", "Severity", "Evidence roles"),
        [(row["code"], row["phase"], issue_path(row["path"]), row["severity"],
            ["retained diagnostic evidence" for _ in row["evidence_refs"]]) for row in issues]) if issues else "[]"])
    return "\n".join(parts)


__all__ = ["select_protein_phylogeny_values", "render_protein_phylogeny_result"]
