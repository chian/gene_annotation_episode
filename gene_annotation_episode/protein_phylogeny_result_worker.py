"""Store-free reading and saved calculation of captured IQ-TREE outputs.

The ordinary owner authenticates the original native attempt and each capture
Source. This leaf checks declared file pins, preserves literal Newick records,
and uses the established tree calculator. It runs no native program, publishes
no Source and cannot establish custody from supplied metadata.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from . import native_flux_balance_storage as storage
from . import protein_phylogeny_result_contracts as contracts
from . import phylogeny_calculation_contracts as common
from .native_file_capture import _identity
from .phylogeny_formats import parse_newick
from .phylogeny_format_contracts import _native_number, validate_tree_record
from .phylogeny_calculators import tree_components


REQUEST_VERSION = "protein_phylogeny_result_request_v1"
SAVED_REPORT_REQUEST_VERSION = "protein_phylogeny_result_request_v2"
OUTPUT_VERSION = "protein_phylogeny_result_output_v1"
DOCUMENTS_VERSION = "protein_phylogeny_documents_v1"
OPERATION = "protein_phylogeny_result"
_FILES = {"documents": ("documents.json", DOCUMENTS_VERSION),
    "sheet": ("sheet.json", contracts.SHEET_VERSION), "value": ("value.json", contracts.PACKET_VERSION)}
_SOURCE = r"source_[0-9a-f]{24,64}"


def _require(condition, code):
    if not condition:
        raise ValueError("protein_phylogeny_result_" + code)


def _closed(value, names, code):
    _require(type(value) is dict and set(value) == set(names.split()), code)


def _file(value, format, *, captured=False):
    _closed(value, "path file source_ref" if captured else "path file", "file_descriptor_invalid")
    identity = _identity(value["file"])
    path = value["path"]
    _require(type(path) is str and bool(path) and Path(path).is_absolute()
        and str(Path(path)) == path and ".." not in Path(path).parts
        and not any(char in path for char in "\0\r\n\\"), "file_path_invalid")
    _require(identity["format"] == format, "file_format_conflict")
    if captured:
        _require(type(value["source_ref"]) is str and re.fullmatch(_SOURCE, value["source_ref"]) is not None,
            "capture_source_invalid")
    return identity


def _pairs(value):
    _require(type(value) is list, "pair_requests_invalid")
    seen = set()
    for row in value:
        _closed(row, "role tree_index node_a node_b", "pair_request_invalid")
        _require(row["role"] in contracts.ROLES and all(type(row[key]) is int and row[key] >= 0
            for key in ("tree_index", "node_a", "node_b")), "pair_request_invalid")
        key = tuple(row[name] for name in ("role", "tree_index", "node_a", "node_b"))
        _require(key not in seen, "duplicate_pair_request")
        seen.add(key)


def validate_protein_phylogeny_result_request(value):
    value = contracts._copy(value)
    _closed(value, "version mode context captured_trees report saved pair_requests selection", "request_invalid")
    _require(value["version"] in (REQUEST_VERSION, SAVED_REPORT_REQUEST_VERSION)
        and value["mode"] in ("parse", "calculate_saved")
        and (value["version"] != SAVED_REPORT_REQUEST_VERSION or value["mode"] == "calculate_saved"), "request_invalid")
    _pairs(value["pair_requests"])
    contracts.validate_phylogeny_selection(value["selection"])
    if value["mode"] == "parse":
        context = contracts.validate_phylogeny_context(value["context"])
        _require(value["saved"] is None and type(value["captured_trees"]) is list, "parse_request_invalid")
        _require(all(row["parser_status"] == "not_parsed" and row["retained_tree_count"] is None
            for row in context["outputs"]), "parser_state_conflict")
        roles = []
        for row in value["captured_trees"]:
            _closed(row, "role captured", "tree_capture_invalid")
            role = row["role"]
            _require(role in contracts.ROLES, "tree_capture_role_invalid")
            roles.append(role)
            _file(row["captured"], "newick", captured=True)
            output = next(item for item in context["outputs"] if item["role"] == role)
            _require(row["captured"]["file"] == output["file"], "tree_capture_identity_conflict")
        _require(roles == [row["role"] for row in context["outputs"] if row["file"] is not None],
            "tree_capture_population_conflict")
        report = value["report"]
        if report is not None:
            _closed(report, "path file source_ref capture", "report_capture_invalid")
            _file({key: report[key] for key in ("path", "file", "source_ref")}, "iqtree_report", captured=True)
            _require(report["capture"] == context["support_trace"]["report_capture"], "report_capture_conflict")
        _require((None if report is None else report["file"]) == context["support_trace"]["report_file"],
            "report_identity_conflict")
        _require(context["support_trace"]["state"] == "unresolved", "support_not_yet_read")
    else:
        _require(value["context"] is value["captured_trees"] is None, "saved_request_invalid")
        if value["version"] == REQUEST_VERSION:
            _require(value["report"] is None, "saved_request_invalid")
        elif value["report"] is not None:
            report = value["report"]
            _closed(report, "path file source_ref capture", "report_capture_invalid")
            _file({key: report[key] for key in ("path", "file", "source_ref")}, "iqtree_report", captured=True)
        _file(value["saved"], contracts.SHEET_VERSION)
    return value


def _read(value):
    try:
        raw = storage.read_bytes(value["path"])
    except OSError as error:
        raise ValueError("protein_phylogeny_result_file_unavailable") from error
    identity = value["file"]
    _require(len(raw) == identity["size_bytes"] and hashlib.sha256(raw).hexdigest() == identity["sha256"],
        "file_identity_conflict")
    return raw


def _evidence(captured):
    identity = captured["file"]
    return [{"content": {"source_ref": captured["source_ref"], "artifact_field": "artifact_ref",
        "artifact_ref": identity["artifact_ref"], "sha256": identity["sha256"],
        "byte_count": identity["size_bytes"]}, "pointer": ""}]


def _issue(code, path, *, severity="qualification", evidence=()):
    return dict(code="protein_phylogeny_" + code, phase="native_output", path=path,
        severity=severity, evidence_refs=list(evidence))


def _support_trace(context, report, raw):
    """Resolve only the selected single UFBoot test from its captured report.

    The official IQ-TREE tutorial and command reference identify .treefile,
    .contree, -bb and report-defined support ordering. An unfamiliar report or
    combined support display remains unresolved; numeric labels do not decide.
    https://iqtree.github.io/doc/Tutorial
    https://iqtree.github.io/doc/Command-Reference
    """
    trace = dict(state="unresolved", method="native_unknown", scale="native_unknown",
        reported_model=None, reported_analysis=None, reported_support=None,
        report_file=None if report is None else deepcopy(report["file"]),
        report_capture=deepcopy(context["support_trace"]["report_capture"]), reason_codes=[])
    if report is None:
        trace["reason_codes"].append("report_unavailable")
        return trace
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        trace["reason_codes"].append("report_encoding_invalid")
        return trace
    native_lines = text.splitlines()
    lines = [" ".join(line.split()) for line in native_lines]
    models = [line.partition(":")[2].strip() for line in lines if line.startswith("Model of substitution:")]
    analyses = [line.partition(":")[2].strip() for line in lines if line.startswith("Type of analysis:")]
    meanings = [line for line in lines if line.startswith("Numbers in parentheses are")]
    for name, rows in (("reported_model", models), ("reported_analysis", analyses)):
        if len(rows) == 1:
            trace[name] = rows[0]
    if models != ["LG"]:
        trace["reason_codes"].append("reported_model_unresolved" if not models else "reported_model_conflict")
    if analyses != [contracts.EXPECTED_ANALYSIS]:
        trace["reason_codes"].append("reported_analysis_unresolved")
    ml = [index for index, line in enumerate(lines) if line == "MAXIMUM LIKELIHOOD TREE"]
    consensus = [index for index, line in enumerate(lines) if line == "CONSENSUS TREE"]
    # The genuine 2.4.0 report has a UFBoot caption for ML and a generic
    # bootstrap caption for its consensus. Their section and bootstrap-tree
    # population, together with the selected analysis, establish the meanings.
    sections = len(ml) == len(consensus) == 1 and ml[0] < consensus[0]
    if sections:
        ml_meanings = [line.rstrip(".") for line in lines[ml[0] + 1:consensus[0]]
            if line.startswith("Numbers in parentheses are")]
        consensus_meanings = [line.rstrip(".") for line in lines[consensus[0] + 1:]
            if line.startswith("Numbers in parentheses are")]
        populations = [line for line in lines[consensus[0] + 1:]
            if line.startswith("Consensus tree is constructed from ")]
        sections = (ml_meanings == [contracts.EXPECTED_SUPPORT]
            and consensus_meanings == [contracts.EXPECTED_CONSENSUS_SUPPORT]
            and populations == [contracts.EXPECTED_CONSENSUS_POPULATION]
            and [line.rstrip(".") for line in meanings] ==
                [contracts.EXPECTED_SUPPORT, contracts.EXPECTED_CONSENSUS_SUPPORT])
    if sections:
        captions = [native_lines[index] for index, line in enumerate(lines)
            if line.startswith("Numbers in parentheses are")]
        population = next(native_lines[index] for index in range(consensus[0] + 1, len(lines))
            if lines[index].startswith("Consensus tree is constructed from "))
        trace["reported_support"] = "\n".join((*captions, population))
    else:
        trace["reason_codes"].append("reported_support_meaning_unresolved")
        if len(meanings) == 1:
            trace["reported_support"] = next(native_lines[index] for index, line in enumerate(lines)
                if line.startswith("Numbers in parentheses are"))
    if context["iqtree_execution"]["state"] != "completed":
        trace["reason_codes"].append("native_execution_not_completed")
    if trace["report_capture"]["state"] != "complete":
        trace["reason_codes"].append("report_capture_incomplete")
    if any(row["file"] is None or row["capture"]["state"] != "complete"
            or row["parser_status"] != "ok" or row["document_completeness"] != "complete"
            for row in context["outputs"]):
        trace["reason_codes"].append("tree_outputs_incomplete")
    if not trace["reason_codes"]:
        trace.update(state="resolved", method="ultrafast_bootstrap", scale="percent")
    elif "reported_model_conflict" in trace["reason_codes"]:
        trace["state"] = "conflict"
    return trace


def _measurements(tree, population, context, captured, report):
    native, supports, issues = [], [], []
    tid, pid = tree["tree_id"], population["population_id"]
    evidence = _evidence(captured)
    resolved = context["support_trace"]["state"] == "resolved"
    for node in tree["nodes"]:
        index = node["node_index"]
        if node["parent_index"] is None:
            continue
        subject = tid + "/node/" + str(index)
        length = dict(observation_id=subject + "/branch_length", field="branch_length",
            value=node["branch_length"], raw_token=node["branch_length_token"],
            state="missing" if node["branch_length"] is None else "available", unit=context["branch_unit"],
            population_id=pid, subject_id=subject, method="iqtree_native_branch_length",
            location=deepcopy(node["source_location"]), evidence=deepcopy(evidence), uncertainty=None, requirement_ids=[])
        common.native_observation(length)
        native.append(length)
        token = node["decoded_label"]
        if not node["child_indices"] or token is None:
            continue
        # Until the command/report trace identifies this field, it remains a
        # literal internal node label in the unchanged TreeRecord.
        if not resolved:
            continue
        value = _native_number(token)
        if value is None:
            issues.append(_issue("internal_label_not_finite_support", "/trees/" + tid + "/nodes/" + str(index),
                evidence=[captured["file"]["artifact_ref"]]))
            continue
        if not 0 <= value <= 100:
            issues.append(_issue("internal_label_outside_support_scale", "/trees/" + tid + "/nodes/" + str(index),
                evidence=[captured["file"]["artifact_ref"]]))
            continue
        method, scale = "ultrafast_bootstrap", "percent"
        observation = dict(observation_id=subject + "/internal_label", field="branch_support_native",
            value=value, raw_token=token, state="available", unit=scale, population_id=pid, subject_id=subject,
            method=method, location=deepcopy(node["source_location"]),
            evidence=deepcopy(evidence + ([] if report is None else _evidence(report))), uncertainty=None, requirement_ids=[])
        common.native_observation(observation)
        native.append(observation)
        supports.append(dict(tree_id=tid, node_index=index, native_observation_id=observation["observation_id"],
            source_kind="internal_label", method=method, scale=scale, command_id="iqtree_LG_bb1000",
            bootstrap_population_id=None, evidence=deepcopy(observation["evidence"])))
    return native, supports, issues


def _calculate(context, trees, pair_requests):
    _pairs(pair_requests)
    keys = {(row["role"], row["tree"]["tree_index"]) for row in trees}
    _require(all((row["role"], row["tree_index"]) in keys for row in pair_requests), "pair_tree_unavailable")
    for row in trees:
        pairs = tuple((pair["node_a"], pair["node_b"]) for pair in pair_requests
            if (pair["role"], pair["tree_index"]) == (row["role"], row["tree"]["tree_index"]))
        row["components"] = tree_components(row["tree"], leaf_population=row["leaf_population"],
            support_observations=tuple(row["support_observations"]), native_measurements=tuple(row["native_measurements"]),
            branch_unit=context["branch_unit"], pairs=pairs)
    return contracts.validate_phylogeny_sheet(dict(version=contracts.SHEET_VERSION,
        context=context, pair_requests=deepcopy(pair_requests), trees=trees))


def _parse(request):
    context = deepcopy(request["context"])
    documents, trees = [], []
    captured = {row["role"]: row["captured"] for row in request["captured_trees"]}
    for output in context["outputs"]:
        role = output["role"]
        if role not in captured:
            documents.append(dict(role=role, document=None))
            context["issues"].append(_issue("tree_output_missing", "/outputs/" + role, severity="error"))
            continue
        descriptor = captured[role]
        parsed = parse_newick(_read(descriptor), artifact=dict(raw_artifact_ref=descriptor["file"]["artifact_ref"],
            source_ref=descriptor["source_ref"], sha256=descriptor["file"]["sha256"]), dialect="newick", allow_multiple=True)
        document = parsed["value"]
        documents.append(dict(role=role, document=deepcopy(document)))
        output["parser_status"] = parsed["status"]
        context["issues"].extend(deepcopy(parsed["diagnostics"]))
        if document is None:
            continue
        output["document_completeness"] = document["completeness"]
        output["retained_tree_count"] = len(document["trees"])
        for tree in document["trees"]:
            tree = validate_tree_record(tree)
            population = dict(population_id=tree["tree_id"] + "/whole_tree_tips", tree_id=tree["tree_id"],
                node_indices=[node["node_index"] for node in tree["nodes"] if not node["child_indices"]],
                completeness="complete", evidence=_evidence(descriptor))
            trees.append(dict(role=role, tree=tree, leaf_population=population))
    report = request["report"]
    report_raw = None if report is None else _read(report)
    context["support_trace"] = _support_trace(context, report, report_raw)
    for row in trees:
        native, supports, issues = _measurements(row["tree"], row["leaf_population"], context, captured[row["role"]], report)
        row.update(native_measurements=native, support_observations=supports)
        context["issues"].extend(issues)
    return _calculate(context, trees, request["pair_requests"]), dict(version=DOCUMENTS_VERSION, outputs=documents)


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode() + b"\n"


def _write(root, key, value):
    name, format = _FILES[key]
    storage.immutable_bytes(root / name, _json_bytes(value))
    pin = storage.file_pin(root / name)
    return dict(relative_path=name, format=format, sha256=pin["sha256"], size_bytes=pin["size_bytes"])


def validate_protein_phylogeny_result_output(value):
    value = contracts._copy(value)
    _closed(value, "version mode documents sheet value", "output_invalid")
    _require(value["version"] == OUTPUT_VERSION and value["mode"] in ("parse", "calculate_saved"), "output_invalid")
    for key, (name, format) in _FILES.items():
        row = value[key]
        if key == "documents" and value["mode"] == "calculate_saved":
            _require(row is None, "output_documents_conflict")
            continue
        _closed(row, "relative_path format sha256 size_bytes", "output_file_invalid")
        _require(row["relative_path"] == name and row["format"] == format and type(row["sha256"]) is str,
            "output_file_invalid")
        _identity(dict(artifact_ref="artifact_" + row["sha256"], sha256=row["sha256"],
            size_bytes=row["size_bytes"], format=format))
    return value


def run_protein_phylogeny_result(request, *, output_directory):
    request = validate_protein_phylogeny_result_request(request)
    root = storage.directory(Path(output_directory))
    for name, _ in _FILES.values():
        _require(not storage.confined_file(root, name).exists(), "output_already_exists")
    if request["mode"] == "parse":
        sheet, documents = _parse(request)
    else:
        original = contracts.validate_phylogeny_sheet(storage.decode_json(_read(request["saved"])))
        context, trees = deepcopy(original["context"]), deepcopy(original["trees"])
        if request["version"] == SAVED_REPORT_REQUEST_VERSION and request["report"] is not None:
            report = request["report"]
            _require(report["file"] == context["support_trace"]["report_file"]
                and report["capture"] == context["support_trace"]["report_capture"], "saved_report_identity_conflict")
            context["support_trace"] = _support_trace(context, report, _read(report))
            for row in trees:
                file = next(output["file"] for output in context["outputs"] if output["role"] == row["role"])
                artifact = row["tree"]["source_location"]["artifact"]
                _require(file is not None and artifact["raw_artifact_ref"] == file["artifact_ref"]
                    and artifact["sha256"] == file["sha256"], "saved_tree_capture_conflict")
                captured = dict(file=file, source_ref=artifact["source_ref"])
                native, supports, issues = _measurements(row["tree"], row["leaf_population"], context, captured, report)
                row.update(native_measurements=native, support_observations=supports)
                context["issues"].extend(issue for issue in issues if issue not in context["issues"])
        sheet = _calculate(context, trees, request["pair_requests"])
        documents = None
    value = contracts.project_phylogeny_value(sheet, request["selection"])
    return validate_protein_phylogeny_result_output(dict(version=OUTPUT_VERSION, mode=request["mode"],
        documents=None if documents is None else _write(root, "documents", documents),
        sheet=_write(root, "sheet", sheet), value=_write(root, "value", value)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("result")
    args = parser.parse_args(argv)
    envelope = storage.read_json(args.request)
    _closed(envelope, "operation arguments", "worker_payload_invalid")
    _require(envelope["operation"] == OPERATION, "worker_operation_invalid")
    _closed(envelope["arguments"], "request", "worker_arguments_invalid")
    result = Path(args.result)
    _require(result.name not in {name for name, _ in _FILES.values()} and not result.exists()
        and not result.is_symlink(), "worker_result_path_conflict")
    try:
        output = run_protein_phylogeny_result(envelope["arguments"]["request"], output_directory=result.parent)
    except ValueError as error:
        storage.immutable_bytes(result, _json_bytes(dict(code=str(error), exception_type="ValueError")))
        return 2
    storage.immutable_bytes(result, _json_bytes(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
