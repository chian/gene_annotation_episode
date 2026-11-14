"""Closed retained views of selected IQ-TREE protein inference.

The native owner authenticates programs, files and Sources. These contracts
validate supplied data and literal projections; they do not infer a tree or
authenticate execution. Only the outer Return.source_ref grants a reference.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, validators

from . import phylogeny_calculation_contracts as common
from .iqtree_phylogeny_driver import validate_iqtree_parameters
from .muscle_alignment_driver import validate_muscle_alignment_parameters
from .phylogeny_format_contracts import validate_tree_record


TOOL = "analyze_protein_phylogeny"
SOURCE_VERSION = "ordinary_protein_phylogeny_result_v1"
SHEET_VERSION = "protein_phylogeny_sheet_v1"
PACKET_VERSION = "ordinary_protein_phylogeny_values_v1"
SELECTION_VERSION = "protein_phylogeny_selection_v1"
CONTEXT_VERSION = "protein_phylogeny_context_v1"
FACT_SOURCE = "protein_phylogeny_outcomes"
ROLES = ("maximum_likelihood_tree", "bootstrap_consensus_tree")
INPUT_MODES = ("supplied_alignment", "selected_MUSCLE_alignment")
EXPECTED_ANALYSIS = "tree reconstruction + ultrafast bootstrap (1000 replicates)"
EXPECTED_SUPPORT = "Numbers in parentheses are ultrafast bootstrap support (%)"
EXPECTED_CONSENSUS_SUPPORT = "Numbers in parentheses are bootstrap supports (%)"
EXPECTED_CONSENSUS_POPULATION = "Consensus tree is constructed from 1000 bootstrap trees"
EXPECTED_ROLE_SUPPORT = "\n".join((EXPECTED_SUPPORT, EXPECTED_CONSENSUS_SUPPORT, EXPECTED_CONSENSUS_POPULATION))
_SOURCE = r"^source_[0-9a-f]{24,64}$"
_ARTIFACT = r"^artifact_[0-9a-f]{64}$"
_SHA = r"^[0-9a-f]{64}$"


def _require(condition, code):
    if not condition:
        raise ValueError("protein_phylogeny_" + code)


def _copy(value):
    def visit(item, seen):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return item
        if kind is float:
            _require(math.isfinite(item), "finite_json_required")
            return item
        _require(kind in (dict, list) and id(item) not in seen, "finite_json_required")
        seen.add(id(item))
        try:
            if kind is list:
                return [visit(child, seen) for child in item]
            _require(all(type(key) is str for key in item), "finite_json_required")
            return {key: visit(child, seen) for key, child in item.items()}
        finally:
            seen.remove(id(item))
    return visit(value, set())


def _obj(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _ref(name):
    return {"$ref": "#/$defs/" + name}


def _nullable(value):
    return {"anyOf": [{"type": "null"}, value]}


def _array(value, *, unique=False):
    result = dict(type="array", items=value)
    if unique:
        result["uniqueItems"] = True
    return result


def _definitions():
    text = dict(type="string")
    named = dict(type="string", minLength=1)
    integer = dict(type="integer", minimum=0)
    indices = _array(integer, unique=True)
    strings = _array(named, unique=True)
    artifact = _obj(dict(raw_artifact_ref=named, source_ref=named, sha256=dict(type="string", pattern=_SHA)))
    location = _obj(dict(artifact=_ref("Artifact"), byte_start_0based=_nullable(integer),
        byte_end_0based_exclusive=_nullable(integer), line_start_1based=_nullable(dict(type="integer", minimum=1)),
        line_end_1based_inclusive=_nullable(dict(type="integer", minimum=1)), xml_path=_nullable(named)))
    evidence = _array(_obj(dict(content=_obj(dict(source_ref=named,
        artifact_field=dict(enum=["artifact_ref", "text_ref", "stdout_ref", "stderr_ref"]),
        artifact_ref=named, sha256=dict(type="string", pattern=_SHA), byte_count=integer)), pointer=text)))
    file = _obj(dict(artifact_ref=dict(type="string", pattern=_ARTIFACT), sha256=dict(type="string", pattern=_SHA),
        size_bytes=integer, format=named))
    quantity = _obj(dict(value=_nullable(dict(type="number")), state=dict(enum=list(common.STATES)),
        unit=named, origin=dict(enum=["derived", "native_fitted", "native_observed"]),
        numerator=_nullable(dict(type="number")), denominator=_nullable(dict(type="number")),
        population_ref=named, method=named, evidence=_ref("Evidence"), requirement_ids=strings))
    comment = _obj(dict(text=text, token=text,
        position=dict(enum=["before_label", "after_label", "after_length", "before_tree", "after_tree"]),
        location=_ref("Location")))
    node = _obj(dict(node_index=integer, parent_index=_nullable(integer), child_indices=indices,
        raw_label=_nullable(text), decoded_label=_nullable(text), label_token=_nullable(text),
        branch_length=_nullable(dict(type="number")), branch_length_token=_nullable(text),
        comments=_array(_ref("Comment")), source_location=_ref("Location")))
    metadata = dict(tree_id=named, document_id=named, tree_index=integer, source_format=dict(const="newick"),
        root_node_index=dict(const=0), native_rooted_marker=dict(enum=["rooted", "unrooted", "unspecified"]),
        source_location=_ref("Location"))
    tree = _obj({**metadata, "nodes": _array(_ref("Node"))})
    leaf = _obj(dict(population_id=named, tree_id=named, node_indices=indices,
        completeness=dict(const="complete"), evidence=_ref("Evidence")))
    branch = _obj(dict(node_index=integer, split_id=_nullable(named), length=_ref("Quantity"),
        native_support_observation_ids=strings, support_method=dict(enum=list(common.SUPPORT_METHODS)),
        support_scale=dict(enum=list(common.SUPPORT_SCALES)), support_rescaled=_ref("Quantity")))
    distance = _obj(dict(node_a=integer, node_b=integer, value=_ref("Quantity")))
    split = _obj(dict(split_id=named, tree_id=named, side_node_indices=indices,
        complement_node_indices=indices, edge_node_indices=indices))
    scalar_fields = ("tip_count", "internal_node_count", "rooted_representation_polytomies",
        "unrooted_degree_polytomies", "branch_length_sum", "known_branch_length_sum", "missing_branch_length_count")
    summary = dict(population_id=named, tree_id=named, **{name: _ref("Quantity") for name in scalar_fields})
    components = _obj({**summary, "splits": _array(_ref("Split")),
        "branches": _array(_ref("Branch")), "distances": _array(_ref("Distance"))})
    uncertainty = _obj(dict(kind=dict(enum=["standard_error", "interval", "native_other"]),
        lower=_nullable(dict(type="number")), upper=_nullable(dict(type="number")),
        value=_nullable(dict(type="number")), method=named))
    observation = _obj(dict(observation_id=named, field=dict(enum=list(common.NATIVE_FIELDS)),
        value=_nullable(dict(type="number")), raw_token=_nullable(text), state=dict(enum=list(common.STATES)),
        unit=dict(enum=list(common.NATIVE_UNITS)), population_id=named, subject_id=_nullable(named), method=named,
        location=_nullable(_ref("Location")), evidence=_ref("Evidence"), uncertainty=_nullable(_ref("Uncertainty")),
        requirement_ids=strings))
    support = _obj(dict(tree_id=named, node_index=integer, native_observation_id=named,
        source_kind=dict(enum=["internal_label", "branch_comment", "phyloxml_confidence"]),
        method=dict(enum=list(common.SUPPORT_METHODS)), scale=dict(enum=list(common.SUPPORT_SCALES)),
        command_id=_nullable(named), bootstrap_population_id=_nullable(named), evidence=_ref("Evidence")))
    execution = _obj(dict(state=dict(enum=["completed", "failed", "unknown", "not_attempted"]),
        returncode=_nullable(dict(type="integer")), reported_version=_nullable(named)))
    capture = _obj(dict(state=dict(enum=["complete", "partial", "truncated", "missing", "unknown"]),
        retained_size_bytes=_nullable(integer), original_size_bytes=_nullable(integer)))
    output = _obj(dict(role=dict(enum=list(ROLES)), file=_nullable(_ref("File")), capture=_ref("Capture"),
        parser_status=dict(enum=["ok", "partial", "invalid", "not_parsed"]),
        document_completeness=_nullable(dict(enum=list(common.COMPLETENESS))), retained_tree_count=_nullable(integer)))
    trace = _obj(dict(state=dict(enum=["resolved", "unresolved", "conflict"]),
        method=dict(enum=["ultrafast_bootstrap", "native_unknown"]), scale=dict(enum=["percent", "native_unknown"]),
        reported_model=_nullable(text), reported_analysis=_nullable(text), reported_support=_nullable(text),
        report_file=_nullable(_ref("File")), report_capture=_ref("Capture"), reason_codes=strings))
    parameters = _obj(dict(model=dict(const="LG"), bootstrap_replicates=dict(const=1000),
        threads=dict(type="integer", minimum=1), seed=dict(type="integer", minimum=1)))
    muscle = _obj(dict(threads=dict(type="integer", minimum=1), randseed=dict(type="integer", minimum=1),
        perturb=integer, perm=dict(enum=["none", "abc", "acb", "bca"]), consiters=integer, refineiters=integer))
    issue = _obj(dict(code=named, phase=named, path=text, severity=dict(enum=["error", "qualification"]), evidence_refs=strings))
    context = _obj(dict(version=dict(const=CONTEXT_VERSION), input_mode=dict(enum=list(INPUT_MODES)),
        input_file=_ref("File"), input_source_ref=_nullable(dict(type="string", pattern=_SOURCE)),
        alignment_file=_nullable(_ref("File")), alignment_execution=_nullable(_ref("Execution")),
        iqtree_execution=_ref("Execution"), iqtree_parameters=_ref("Parameters"),
        muscle_parameters=_nullable(_ref("MuscleParameters")), branch_unit=dict(enum=list(common.BRANCH_UNITS)),
        support_trace=_ref("SupportTrace"), outputs=_array(_ref("Output")),
        interpretation=dict(const="Native fitted tree and branch support; no calibrated gene-function confidence or biological-root assignment."),
        issues=_array(_ref("Issue"))))
    pair = _obj(dict(role=dict(enum=list(ROLES)), tree_index=integer, node_a=integer, node_b=integer))
    window = _obj(dict(indices=_nullable(indices), offset=integer, limit=integer))
    selector = _obj(dict(role=dict(enum=list(ROLES)), tree_indices=_nullable(indices)))
    selection = _obj(dict(version=dict(const=SELECTION_VERSION), trees=_array(selector),
        nodes=_ref("Window"), distances=_ref("Window")))
    count = _obj(dict(retained_record_count=_nullable(integer), selected_record_count=_nullable(integer),
        returned_record_count=integer, omitted_record_count=_nullable(integer)))
    node_row = _obj(dict(node=_ref("Node"), branch=_nullable(_ref("Branch"))))
    public_tree = _obj(dict(role=dict(enum=list(ROLES)), tree=_ref("TreeMetadata"),
        leaf_population=_ref("LeafPopulation"), summary=_ref("Summary"), nodes=_array(_ref("NodeRow")),
        distances=_array(_ref("Distance")), accounting=_obj(dict(nodes=_ref("Accounting"), distances=_ref("Accounting")))))
    entry = _obj(dict(role=dict(enum=list(ROLES)), tree=_ref("Tree"), leaf_population=_ref("LeafPopulation"),
        native_measurements=_array(_ref("Observation")), support_observations=_array(_ref("Support")),
        components=_ref("Components")))
    sheet = _obj(dict(version=dict(const=SHEET_VERSION), context=_ref("Context"),
        pair_requests=_array(_ref("PairRequest")), trees=_array(_ref("StoredTree"))))
    packet = _obj(dict(version=dict(const=PACKET_VERSION), context=_ref("Context"),
        pair_requests=_array(_ref("PairRequest")), selection=_ref("Selection"),
        trees=_array(_ref("PublicTree")), accounting=_ref("Accounting")))
    returned = deepcopy(packet)
    returned["properties"]["source_ref"] = dict(type="string", pattern=_SOURCE,
        format="reference", **{"x-reference-namespace": "source"})
    returned["required"].append("source_ref")
    input_selection = _obj(dict(namespace=dict(enum=["artifact", "source"]),
        reference=dict(type="string", pattern=r"^(artifact_[0-9a-f]{64}|source_[0-9a-f]{24,64})$"),
        format=dict(enum=["fasta", "aligned_fasta"])))
    arguments = dict(oneOf=[
        _obj(dict(mode=dict(const="run_native"), input_mode=dict(enum=list(INPUT_MODES)), input=_ref("InputSelection"),
            pair_requests=_array(_ref("PairRequest")), selection=_ref("Selection"))),
        _obj(dict(mode=dict(const="calculate_saved"), result_ref=dict(type="string", pattern=_SOURCE),
            pair_requests=_array(_ref("PairRequest")), selection=_ref("Selection"))),
        _obj(dict(mode=dict(const="read_stored"), result_ref=dict(type="string", pattern=_SOURCE), selection=_ref("Selection")))])
    return dict(Artifact=artifact, Location=location, Evidence=evidence, File=file, Quantity=quantity,
        Comment=comment, Node=node, Tree=tree, TreeMetadata=_obj(metadata), LeafPopulation=leaf,
        Branch=branch, Distance=distance, Split=split, Summary=_obj(summary), Components=components,
        Uncertainty=uncertainty, Observation=observation, Support=support, Execution=execution, Capture=capture,
        Output=output, SupportTrace=trace, Parameters=parameters, MuscleParameters=muscle, Issue=issue,
        Context=context, PairRequest=pair, Window=window, Selection=selection, Accounting=count,
        NodeRow=node_row, PublicTree=public_tree, StoredTree=entry, Sheet=sheet, Value=packet,
        Return=returned, InputSelection=input_selection, Arguments=arguments)


_DEFS = _definitions()
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _checker, value: type(value) is int)
    .redefine("number", lambda _checker, value: type(value) is int or type(value) is float and math.isfinite(value))
    .redefine("array", lambda _checker, value: type(value) is list)
    .redefine("object", lambda _checker, value: type(value) is dict))


def phylogeny_result_schema(kind="Return"):
    _require(kind in ("Arguments", "Selection", "Context", "Sheet", "Value", "Return"), "schema_kind_invalid")
    needed, pending = {}, [kind]
    while pending:
        name = pending.pop()
        if name in needed:
            continue
        needed[name] = deepcopy(_DEFS[name])
        def visit(node):
            if type(node) is dict:
                if "$ref" in node:
                    pending.append(node["$ref"].split("/")[-1])
                for child in node.values():
                    visit(child)
            elif type(node) is list:
                for child in node:
                    visit(child)
        visit(needed[name])
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": needed, "$ref": "#/$defs/" + kind}


def _validated(value, kind):
    value = _copy(value)
    _require(_STRICT(phylogeny_result_schema(kind)).is_valid(value), kind.lower() + "_invalid")
    return value


def validate_phylogeny_selection(value):
    value = _validated(value, "Selection")
    roles = [row["role"] for row in value["trees"]]
    _require(len(roles) == len(set(roles)), "duplicate_selected_role")
    return value


def validate_phylogeny_arguments(value):
    value = _validated(value, "Arguments")
    validate_phylogeny_selection(value["selection"])
    if value["mode"] == "run_native":
        item = value["input"]
        _require(re.fullmatch(_ARTIFACT if item["namespace"] == "artifact" else _SOURCE, item["reference"]) is not None,
            "input_namespace_conflict")
    return value


def validate_phylogeny_context(value):
    value = _validated(value, "Context")
    validate_iqtree_parameters(value["iqtree_parameters"])
    for file in (value["input_file"], value["alignment_file"], value["support_trace"]["report_file"]):
        if file is not None:
            _require(file["artifact_ref"] == "artifact_" + file["sha256"], "file_identity_conflict")
    _require(value["input_file"]["format"] in ("fasta", "aligned_fasta") and (value["alignment_file"] is None or
        value["alignment_file"]["format"] in ("fasta", "aligned_fasta")), "input_format_conflict")
    aligned = value["input_mode"] == "supplied_alignment"
    _require((value["muscle_parameters"] is None) is aligned and (value["alignment_execution"] is None) is aligned,
        "alignment_mode_conflict")
    if aligned:
        _require(value["alignment_file"] == value["input_file"], "supplied_alignment_file_conflict")
    else:
        validate_muscle_alignment_parameters(value["muscle_parameters"])
    for execution in (value["iqtree_execution"], *([] if aligned else [value["alignment_execution"]])):
        state, code = execution["state"], execution["returncode"]
        _require(state != "completed" or code == 0, "execution_state_conflict")
        _require(state != "failed" or code is None or code != 0, "execution_state_conflict")
        _require(state not in ("not_attempted", "unknown") or code is None, "execution_state_conflict")
    _require(value["iqtree_execution"]["state"] != "completed" or value["alignment_file"] is not None,
        "alignment_unavailable")
    _require([row["role"] for row in value["outputs"]] == list(ROLES), "output_roles_conflict")
    for row in value["outputs"]:
        capture = row["capture"]
        if row["file"] is None:
            _require(row["parser_status"] == "not_parsed" and row["retained_tree_count"] is None
                and row["document_completeness"] is None and capture["state"] in ("missing", "unknown")
                and capture["retained_size_bytes"] is None and capture["original_size_bytes"] is None,
                "missing_output_conflict")
        else:
            file = row["file"]
            _require(file["artifact_ref"] == "artifact_" + file["sha256"] and file["format"] == "newick",
                "tree_file_identity_conflict")
            _require(capture["retained_size_bytes"] == file["size_bytes"], "capture_extent_conflict")
            _require(capture["state"] != "missing" and (capture["original_size_bytes"] is None or
                capture["original_size_bytes"] >= file["size_bytes"]), "capture_extent_conflict")
            _require((row["retained_tree_count"] is None) == (row["document_completeness"] is None),
                "parsed_population_conflict")
            _require(row["parser_status"] != "not_parsed" or row["retained_tree_count"] is None,
                "parsed_population_conflict")
        if capture["state"] == "complete":
            _require(capture["retained_size_bytes"] is not None and capture["original_size_bytes"] in
                (None, capture["retained_size_bytes"]), "capture_extent_conflict")
    trace = value["support_trace"]
    report_capture = trace["report_capture"]
    if trace["report_file"] is None:
        _require(report_capture["state"] in ("missing", "unknown")
            and report_capture["retained_size_bytes"] is report_capture["original_size_bytes"] is None,
            "report_capture_conflict")
    else:
        size, original = trace["report_file"]["size_bytes"], report_capture["original_size_bytes"]
        _require(report_capture["retained_size_bytes"] == size and report_capture["state"] != "missing"
            and (original is None or original >= size) and (report_capture["state"] != "complete"
            or original is None or original == size), "report_capture_conflict")
    if trace["state"] == "resolved":
        _require(trace["method"] == "ultrafast_bootstrap" and trace["scale"] == "percent"
            and trace["report_file"] is not None and trace["reported_model"] == "LG"
            and trace["reported_analysis"] == EXPECTED_ANALYSIS and value["iqtree_execution"]["state"] == "completed"
            and type(trace["reported_support"]) is str and "\n".join(
                " ".join(line.split()) for line in trace["reported_support"].splitlines()).rstrip(".") in
                (EXPECTED_SUPPORT, EXPECTED_ROLE_SUPPORT)
            and report_capture["state"] == "complete"
            and trace["reason_codes"] == [], "support_trace_conflict")
        _require(all(row["capture"]["state"] == "complete" and row["parser_status"] == "ok"
            and row["document_completeness"] == "complete" and row["retained_tree_count"] is not None
            and row["retained_tree_count"] > 0 for row in value["outputs"]), "support_trace_conflict")
    else:
        _require(trace["method"] == trace["scale"] == "native_unknown" and bool(trace["reason_codes"]), "support_trace_conflict")
    _require(trace["report_file"] is None or trace["report_file"]["format"] == "iqtree_report", "report_format_conflict")
    return value


def validate_phylogeny_sheet(value):
    value = _validated(value, "Sheet")
    validate_phylogeny_context(value["context"])
    keys = []
    for row in value["trees"]:
        tree = validate_tree_record(row["tree"])
        _tree_capture(tree, row["role"], value["context"])
        key = row["role"], tree["tree_index"]
        keys.append(key)
        population, components = row["leaf_population"], row["components"]
        _quantities(components, population["population_id"])
        _require(population["tree_id"] == components["tree_id"] == tree["tree_id"]
            and components["population_id"] == population["population_id"], "tree_population_conflict")
        _require(set(population["node_indices"]) == {node["node_index"] for node in tree["nodes"] if not node["child_indices"]},
            "whole_tree_leaf_population_required")
        _require([branch["node_index"] for branch in components["branches"]] ==
            [node["node_index"] for node in tree["nodes"] if node["parent_index"] is not None], "branch_population_conflict")
        observations = {}
        for observation in row["native_measurements"]:
            common.native_observation(observation)
            _require(observation["observation_id"] not in observations
                and observation["population_id"] == population["population_id"], "native_population_conflict")
            observations[observation["observation_id"]] = observation
        support_by_node, support_ids = {}, set()
        for support in row["support_observations"]:
            index, identity = support["node_index"], support["native_observation_id"]
            _require(support["tree_id"] == tree["tree_id"] and 0 < index < len(tree["nodes"])
                and bool(tree["nodes"][index]["child_indices"]) and identity in observations
                and identity not in support_ids, "support_identity_conflict")
            observation = observations[identity]
            _require(value["context"]["support_trace"]["state"] == "resolved"
                and support["method"] == "ultrafast_bootstrap" and support["scale"] == "percent"
                and observation["value"] is not None and 0 <= observation["value"] <= 100,
                "support_meaning_conflict")
            _require(observation["field"] == "branch_support_native"
                and observation["subject_id"] == tree["tree_id"] + "/node/" + str(index)
                and observation["method"] == support["method"]
                and observation["unit"] == support["scale"], "support_identity_conflict")
            support_ids.add(identity)
            support_by_node.setdefault(index, []).append(identity)
        _require(all(observation["field"] == "branch_length" or observation["field"] == "branch_support_native"
            and identity in support_ids for identity, observation in observations.items()), "native_field_conflict")
        for branch in components["branches"]:
            node = tree["nodes"][branch["node_index"]]
            _require(branch["length"]["value"] == node["branch_length"], "branch_length_conflict")
            _require(branch["native_support_observation_ids"] == support_by_node.get(node["node_index"], []),
                "support_identity_conflict")
            if branch["support_rescaled"]["value"] is not None:
                _require(value["context"]["support_trace"]["state"] == "resolved" and bool(node["child_indices"])
                    and branch["support_method"] == "ultrafast_bootstrap" and branch["support_scale"] == "percent",
                    "support_meaning_conflict")
        for quantity in (components[name] for name in components if name not in
                ("population_id", "tree_id", "splits", "branches", "distances")):
            _require(quantity["population_ref"] == population["population_id"], "quantity_population_conflict")
    _require(len(keys) == len(set(keys)), "duplicate_tree_identity")
    _require(keys == sorted(keys, key=lambda key: (ROLES.index(key[0]), key[1])), "tree_order_conflict")
    for output in value["context"]["outputs"]:
        actual = [key for key in keys if key[0] == output["role"]]
        _require(output["retained_tree_count"] is None and actual == [] or output["retained_tree_count"] == len(actual),
            "tree_count_conflict")
    requested = [(row["role"], row["tree_index"], row["node_a"], row["node_b"]) for row in value["pair_requests"]]
    _require(len(requested) == len(set(requested)), "duplicate_pair_request")
    for row in value["trees"]:
        selected = [(a, b) for role, index, a, b in requested if (role, index) == (row["role"], row["tree"]["tree_index"])]
        _require([(pair["node_a"], pair["node_b"]) for pair in row["components"]["distances"]] == selected,
            "pair_population_conflict")
    _require(all((role, index) in keys for role, index, _, _ in requested), "pair_tree_unavailable")
    return value


def _tree_capture(tree, role, context):
    file = next(row["file"] for row in context["outputs"] if row["role"] == role)
    artifact = tree["source_location"]["artifact"]
    _require(file is not None and artifact["raw_artifact_ref"] == file["artifact_ref"]
        and artifact["sha256"] == file["sha256"], "tree_capture_identity_conflict")


def _quantities(value, population):
    if type(value) is list:
        for row in value:
            _quantities(row, population)
    elif type(value) is dict:
        if "population_ref" in value:
            _require(value["population_ref"] == population
                and (value["value"] is not None) == (value["state"] == "available"), "quantity_state_conflict")
            common.evidence(value["evidence"])
        else:
            for row in value.values():
                _quantities(row, population)


def _indices(available, selection):
    requested = selection["indices"]
    selected = available if requested is None else requested
    _require(all(index in available for index in selected), "selection_outside_retained_values")
    returned = selected[selection["offset"]:selection["offset"] + selection["limit"]]
    return selected, returned


def _accounting(retained, selected, returned):
    return dict(retained_record_count=retained, selected_record_count=selected,
        returned_record_count=returned, omitted_record_count=None if selected is None else selected - returned)


def project_phylogeny_value(sheet, selection):
    """Copy saved records and quantities; do not parse or recalculate them."""
    sheet = validate_phylogeny_sheet(sheet)
    selection = validate_phylogeny_selection(selection)
    by_key = {(row["role"], row["tree"]["tree_index"]): row for row in sheet["trees"]}
    chosen, unknown = [], False
    for requested in selection["trees"]:
        role, indices = requested["role"], requested["tree_indices"]
        available = [index for kind, index in by_key if kind == role]
        if indices is None:
            indices = available
            unknown |= next(row for row in sheet["context"]["outputs"] if row["role"] == role)["retained_tree_count"] is None
        _require(all((role, index) in by_key for index in indices), "selection_tree_unavailable")
        chosen.extend(by_key[role, index] for index in indices)
    trees = []
    for row in chosen:
        tree, components = row["tree"], row["components"]
        selected_nodes, node_indices = _indices(list(range(len(tree["nodes"]))), selection["nodes"])
        selected_distances, distance_indices = _indices(list(range(len(components["distances"]))), selection["distances"])
        branches = {branch["node_index"]: branch for branch in components["branches"]}
        trees.append(dict(role=row["role"], tree={key: deepcopy(item) for key, item in tree.items() if key != "nodes"},
            leaf_population=deepcopy(row["leaf_population"]),
            summary={key: deepcopy(item) for key, item in components.items() if key not in ("branches", "splits", "distances")},
            nodes=[dict(node=deepcopy(tree["nodes"][i]), branch=deepcopy(branches.get(i))) for i in node_indices],
            distances=[deepcopy(components["distances"][i]) for i in distance_indices],
            accounting=dict(nodes=_accounting(len(tree["nodes"]), len(selected_nodes), len(node_indices)),
                distances=_accounting(len(components["distances"]), len(selected_distances), len(distance_indices)))))
    retained = None if any(row["retained_tree_count"] is None for row in sheet["context"]["outputs"]) else len(sheet["trees"])
    result = dict(version=PACKET_VERSION, context=deepcopy(sheet["context"]), pair_requests=deepcopy(sheet["pair_requests"]),
        selection=selection, trees=trees, accounting=_accounting(retained,
            None if unknown else len(chosen), len(trees)))
    return validate_phylogeny_value(result)


def validate_phylogeny_value(value):
    value = _validated(value, "Value")
    validate_phylogeny_context(value["context"])
    validate_phylogeny_selection(value["selection"])
    keys = [(row["role"], row["tree"]["tree_index"]) for row in value["trees"]]
    _require(len(keys) == len(set(keys)), "duplicate_tree_identity")
    outputs = {row["role"]: row for row in value["context"]["outputs"]}
    retained = None if any(row["retained_tree_count"] is None for row in outputs.values()) else sum(
        row["retained_tree_count"] for row in outputs.values())
    requested_keys, selected, unknown = [], 0, False
    for choice in value["selection"]["trees"]:
        role, indices = choice["role"], choice["tree_indices"]
        actual = [index for kind, index in keys if kind == role]
        if indices is None:
            _require(actual == sorted(actual), "selected_tree_order_conflict")
            count = outputs[role]["retained_tree_count"]
            _require(count is None or count == len(actual), "selected_tree_count_conflict")
            unknown |= count is None
            requested_keys.extend((role, index) for index in actual)
            selected += len(actual)
        else:
            requested_keys.extend((role, index) for index in indices)
            selected += len(indices)
    _require(keys == requested_keys and value["accounting"] == _accounting(retained,
        None if unknown else selected, len(keys)), "tree_accounting_conflict")
    pairs = [(row["role"], row["tree_index"], row["node_a"], row["node_b"]) for row in value["pair_requests"]]
    _require(len(pairs) == len(set(pairs)), "duplicate_pair_request")
    for row in value["trees"]:
        _tree_capture(row["tree"], row["role"], value["context"])
        _require(row["tree"]["tree_id"] == row["leaf_population"]["tree_id"] == row["summary"]["tree_id"]
            and row["summary"]["population_id"] == row["leaf_population"]["population_id"], "tree_population_conflict")
        _quantities(row["summary"], row["leaf_population"]["population_id"])
        _quantities(row["nodes"], row["leaf_population"]["population_id"])
        _quantities(row["distances"], row["leaf_population"]["population_id"])
        tips, internal = row["summary"]["tip_count"]["value"], row["summary"]["internal_node_count"]["value"]
        _require(type(tips) is int and type(internal) is int and tips == len(row["leaf_population"]["node_indices"]),
            "tree_population_conflict")
        all_pairs = [(a, b) for role, index, a, b in pairs if (role, index) == (row["role"], row["tree"]["tree_index"])]
        for name, count, indices in (("nodes", tips + internal, [entry["node"]["node_index"] for entry in row["nodes"]]),
                ("distances", len(all_pairs), None)):
            selected_indices, expected = _indices(list(range(count)), value["selection"][name])
            _require(row["accounting"][name] == _accounting(count, len(selected_indices), len(expected)),
                "view_accounting_conflict")
            if indices is not None:
                _require(indices == expected, "selected_node_order_conflict")
            else:
                _require([(pair["node_a"], pair["node_b"]) for pair in row[name]] == [all_pairs[i] for i in expected],
                    "selected_pair_order_conflict")
        for entry in row["nodes"]:
            branch = entry["branch"]
            _require((branch is None) == (entry["node"]["parent_index"] is None), "branch_identity_conflict")
            if branch is not None:
                _require(branch["node_index"] == entry["node"]["node_index"] and branch["length"]["value"] == entry["node"]["branch_length"],
                    "branch_identity_conflict")
                if branch["support_rescaled"]["value"] is not None:
                    _require(value["context"]["support_trace"]["state"] == "resolved"
                        and bool(entry["node"]["child_indices"]) and branch["support_method"] == "ultrafast_bootstrap"
                        and branch["support_scale"] == "percent", "support_meaning_conflict")
    return value


def project_phylogeny_return(value, *, source_ref):
    value = validate_phylogeny_value(value)
    value["source_ref"] = source_ref
    return validate_phylogeny_return(value)


def validate_phylogeny_return(value):
    value = _validated(value, "Return")
    validate_phylogeny_value({key: item for key, item in value.items() if key != "source_ref"})
    return value


def phylogeny_fact_sources():
    item = phylogeny_result_schema("Return")
    report = {"type": "array", "items": _ref("Return"), "$defs": item["$defs"], "x-source": FACT_SOURCE}
    report["$id"] = "urn:protein-phylogeny-facts:" + hashlib.sha256(json.dumps(report, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {FACT_SOURCE: dict(type="array", report_schema=report)}


__all__ = ["TOOL", "SOURCE_VERSION", "SHEET_VERSION", "PACKET_VERSION", "SELECTION_VERSION", "CONTEXT_VERSION",
    "FACT_SOURCE", "ROLES", "INPUT_MODES", "phylogeny_result_schema", "validate_phylogeny_arguments",
    "validate_phylogeny_selection", "validate_phylogeny_context", "validate_phylogeny_sheet",
    "project_phylogeny_value", "validate_phylogeny_value", "project_phylogeny_return", "validate_phylogeny_return",
    "phylogeny_fact_sources"]
