"""Engineered byte/contract controls, not IQ-TREE execution or Source evidence.

All source IDs in this module are supplied metadata. A passing control cannot
establish native production, custody, publication or parent/root delivery.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import iqtree_phylogeny_driver as driver
from gene_annotation_episode import protein_phylogeny_result_contracts as contracts
from gene_annotation_episode import protein_phylogeny_result_worker as worker


PARAMETERS = dict(model="LG", bootstrap_replicates=1000, threads=1, seed=7)
MUSCLE_PARAMETERS = dict(threads=1, randseed=1, perturb=0, perm="none", consiters=2, refineiters=100)
TREE = b"((A:0.1,B:-0.2)95:0.3,(C:0.4,D:0.5)80:0.6);\n"
REPORT = ("Model of substitution: LG\nType of analysis: " + contracts.EXPECTED_ANALYSIS
    + "\n" + contracts.EXPECTED_SUPPORT + ".\n").encode()


def _file(raw, format):
    digest = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + digest, sha256=digest, size_bytes=len(raw), format=format)


def _capture(raw=None, *, state="complete"):
    size = None if raw is None else len(raw)
    return dict(state="missing" if raw is None else state, retained_size_bytes=size,
        original_size_bytes=size if state == "complete" else None)


def _selection():
    return dict(version=contracts.SELECTION_VERSION, trees=[dict(role=role, tree_indices=None) for role in contracts.ROLES],
        nodes=dict(indices=None, offset=0, limit=1000), distances=dict(indices=None, offset=0, limit=1000))


def _fixture(tmp_path, *, tree=TREE, report=REPORT, mode="supplied_alignment", missing=(), capture="complete"):
    context = dict(version=contracts.CONTEXT_VERSION, input_mode=mode,
        input_file=_file(b">A\nACD\n>B\nACE\n>C\nACF\n>D\nACG\n", "fasta"), input_source_ref=None,
        alignment_file=None, alignment_execution=None, iqtree_execution=dict(state="completed", returncode=0, reported_version=None),
        iqtree_parameters=deepcopy(PARAMETERS), muscle_parameters=None, branch_unit="native_unknown",
        support_trace=dict(state="unresolved", method="native_unknown", scale="native_unknown", reported_model=None,
            reported_analysis=None, reported_support=None, report_file=None, report_capture=_capture(), reason_codes=["report_not_read"]),
        outputs=[], interpretation="Native fitted tree and branch support; no calibrated gene-function confidence or biological-root assignment.",
        issues=[])
    context["alignment_file"] = deepcopy(context["input_file"])
    if mode == "selected_MUSCLE_alignment":
        context["muscle_parameters"] = deepcopy(MUSCLE_PARAMETERS)
        context["alignment_execution"] = dict(state="completed", returncode=0, reported_version=None)
        context["alignment_file"]["format"] = "aligned_fasta"
    captures = []
    for index, role in enumerate(contracts.ROLES):
        file = None if role in missing else _file(tree, "newick")
        context["outputs"].append(dict(role=role, file=file, capture=_capture(None if file is None else tree, state=capture),
            parser_status="not_parsed", document_completeness=None, retained_tree_count=None))
        if file is not None:
            path = tmp_path / (role + ".nwk")
            path.write_bytes(tree)
            captures.append(dict(role=role, captured=dict(path=str(path), file=file, source_ref="source_" + str(index + 1) * 24)))
    report_descriptor = None
    if report is not None:
        path = tmp_path / "report.iqtree"
        path.write_bytes(report)
        file = _file(report, "iqtree_report")
        report_descriptor = dict(path=str(path), file=file, source_ref="source_" + "3" * 24, capture=_capture(report))
        context["support_trace"].update(report_file=file, report_capture=_capture(report))
    return dict(version=worker.REQUEST_VERSION, mode="parse", context=context, captured_trees=captures,
        report=report_descriptor, saved=None, pair_requests=[], selection=_selection())


def _run(tmp_path, **kwargs):
    request = _fixture(tmp_path, **kwargs)
    output_path = tmp_path / "parsed"
    output_path.mkdir()
    output = worker.run_protein_phylogeny_result(request, output_directory=output_path)
    sheet = json.loads((output_path / "sheet.json").read_bytes())
    value = json.loads((output_path / "value.json").read_bytes())
    return request, output, sheet, value, output_path


def _native_request():
    return dict(version=driver.REQUEST_VERSION, input=dict(path="/selected/alignment.fasta", file=_file(b"aligned", "fasta"), source_ref=None),
        software=dict(path="/selected/iqtree2", sha256="a" * 64, size_bytes=123), parameters=deepcopy(PARAMETERS))


def test_explicit_selected_native_argv_and_intermediate_file_identity():
    request = _native_request()
    assert driver.iqtree_native_argv(request) == ["/selected/iqtree2", "-s", "input.fasta", "-st", "AA", "-m", "LG",
        "-bb", "1000", "-nt", "1", "-seed", "7", "-pre", "result"]
    request["input"]["file"]["format"] = "aligned_fasta"
    assert driver.validate_iqtree_native_request(request)["input"]["file"]["format"] == "aligned_fasta"


@pytest.mark.parametrize("key,value", [("model", "WAG"), ("model", "MFP"), ("bootstrap_replicates", 999),
    ("bootstrap_replicates", True), ("threads", "AUTO"), ("threads", 0), ("threads", True),
    ("seed", 0), ("seed", 2**31), ("seed", 1.0)])
def test_no_unselected_model_or_implicit_resource_parameter(key, value):
    request = _native_request()
    request["parameters"][key] = value
    with pytest.raises(ValueError):
        driver.validate_iqtree_native_request(request)


@pytest.mark.parametrize("path", ["relative", "/a/../b", "/a//b", "/a\nb", "/a\\b", "//a", "/"])
def test_native_path_must_be_exact_absolute(path):
    request = _native_request()
    request["software"]["path"] = path
    with pytest.raises(ValueError):
        driver.validate_iqtree_native_request(request)


@pytest.mark.parametrize("role", ["maximum_likelihood_tree", "bootstrap_consensus_tree"])
def test_manifest_preserves_missing_native_outputs_without_success_claim(role):
    request = _native_request()
    manifest = dict(version=driver.MANIFEST_VERSION, request=request, argv=driver.iqtree_native_argv(request), returncode=1,
        files=[], issues=["iqtree_phylogeny_native_nonzero_exit", *["iqtree_phylogeny_" + item + "_file_unavailable"
            for item, _, _, required in driver._FILES if required]])
    assert driver.validate_iqtree_native_manifest(manifest) == manifest
    manifest["issues"].remove("iqtree_phylogeny_" + role + "_file_unavailable")
    with pytest.raises(ValueError, match="file_issue_conflict"):
        driver.validate_iqtree_native_manifest(manifest)


@pytest.mark.parametrize("mode", contracts.INPUT_MODES)
def test_literal_tree_roles_support_and_shared_signed_length_arithmetic(tmp_path, mode):
    request, output, sheet, value, _ = _run(tmp_path, mode=mode)
    assert output["mode"] == "parse" and sheet["context"]["input_mode"] == mode
    assert sheet["context"]["support_trace"]["state"] == "resolved"
    assert [row["role"] for row in value["trees"]] == list(contracts.ROLES)
    for row in sheet["trees"]:
        assert row["tree"]["native_rooted_marker"] == "unspecified"
        assert row["components"]["tip_count"]["value"] == 4
        assert row["components"]["branch_length_sum"]["value"] == pytest.approx(1.7)
        branch = row["components"]["branches"][0]
        assert branch["support_method"] == "ultrafast_bootstrap" and branch["support_rescaled"]["value"] == .95
        assert row["components"]["branches"][2]["length"]["value"] == -.2
        assert row["components"]["branch_length_sum"]["unit"] == "native_unknown"
    assert worker.validate_protein_phylogeny_result_request(request) == request
    if mode == "supplied_alignment":
        received_alignment = deepcopy(sheet["context"])
        received_alignment["input_file"]["format"] = received_alignment["alignment_file"]["format"] = "aligned_fasta"
        assert contracts.validate_phylogeny_context(received_alignment) == received_alignment


@pytest.mark.parametrize("report", [None, b"unrecognized report", REPORT.replace(b"LG", b"WAG"),
    REPORT.replace(b"1000 replicates", b"100 replicates"), REPORT.replace(b"ultrafast bootstrap support (%)",
        b"SH-aLRT support (%) / ultrafast bootstrap support (%)"), REPORT + b"Model of substitution: LG\n", b"\xff"])
def test_numeric_labels_do_not_resolve_support_without_exact_native_report(tmp_path, report):
    _, _, sheet, value, _ = _run(tmp_path, report=report)
    assert sheet["context"]["support_trace"]["state"] in ("unresolved", "conflict")
    assert sheet["context"]["support_trace"]["reason_codes"]
    assert all(row["support_observations"] == [] and all(observation["field"] == "branch_length"
        for observation in row["native_measurements"]) for row in sheet["trees"])
    assert all(branch["support_rescaled"]["value"] is None for row in sheet["trees"] for branch in row["components"]["branches"])
    assert all(node["node"]["decoded_label"] in (None, "95", "80", "A", "B", "C", "D")
        for row in value["trees"] for node in row["nodes"])


@pytest.mark.parametrize("capture", ["partial", "truncated", "unknown"])
def test_incomplete_capture_never_becomes_resolved_ufboot(tmp_path, capture):
    _, _, sheet, _, _ = _run(tmp_path, capture=capture)
    assert sheet["context"]["support_trace"]["state"] == "unresolved"
    assert "tree_outputs_incomplete" in sheet["context"]["support_trace"]["reason_codes"]


def test_report_capture_must_be_complete_before_support_resolution(tmp_path):
    request = _fixture(tmp_path)
    request["report"]["capture"] = _capture(REPORT, state="truncated")
    request["context"]["support_trace"]["report_capture"] = deepcopy(request["report"]["capture"])
    sheet, _ = worker._parse(worker.validate_protein_phylogeny_result_request(request))
    assert "report_capture_incomplete" in sheet["context"]["support_trace"]["reason_codes"]


def test_missing_outputs_keep_unknown_population_separate_from_empty_selection(tmp_path):
    _, _, sheet, value, _ = _run(tmp_path, missing=contracts.ROLES)
    assert sheet["trees"] == value["trees"] == []
    assert value["accounting"] == dict(retained_record_count=None, selected_record_count=None, returned_record_count=0,
        omitted_record_count=None)
    empty = _selection()
    empty["trees"] = []
    projected = contracts.project_phylogeny_value(sheet, empty)
    assert projected["accounting"] == dict(retained_record_count=None, selected_record_count=0, returned_record_count=0,
        omitted_record_count=0)


def test_malformed_segment_retains_later_tree_and_its_original_index(tmp_path):
    _, _, sheet, value, _ = _run(tmp_path, tree=b"(A,B));" + TREE)
    assert [row["tree"]["tree_index"] for row in sheet["trees"]] == [1, 1]
    assert all(row["parser_status"] == "partial" for row in sheet["context"]["outputs"])
    assert value["accounting"]["returned_record_count"] == 2
    assert sheet["context"]["support_trace"]["state"] == "unresolved"


@pytest.mark.parametrize("token", [b"NaN", b"", b"1e-999"])
def test_invalid_native_length_is_retained_missing_without_fabricated_zero(tmp_path, token):
    raw = TREE.replace(b"A:0.1", b"A:" + token)
    _, _, sheet, _, _ = _run(tmp_path, tree=raw)
    for row in sheet["trees"]:
        assert row["tree"]["nodes"][2]["branch_length_token"] == token.decode()
        assert row["tree"]["nodes"][2]["branch_length"] is None
        assert row["components"]["branch_length_sum"]["value"] is None
        assert row["components"]["missing_branch_length_count"]["value"] == 1
        assert row["components"]["branches"][1]["length"]["value"] is None


def test_saved_calculation_uses_retained_trees_after_native_files_vanish(tmp_path, monkeypatch):
    request, _, original, _, root = _run(tmp_path)
    for item in request["captured_trees"]:
        Path(item["captured"]["path"]).unlink()
    Path(request["report"]["path"]).unlink()
    def forbidden(*args, **kwargs):
        raise AssertionError("saved calculation must not parse original native files")
    monkeypatch.setattr(worker, "parse_newick", forbidden)
    saved_path = root / "sheet.json"
    saved = dict(path=str(saved_path), file=_file(saved_path.read_bytes(), contracts.SHEET_VERSION))
    pairs = [dict(role=role, tree_index=0, node_a=2, node_b=3) for role in contracts.ROLES]
    modified = dict(version=worker.REQUEST_VERSION, mode="calculate_saved", context=None, captured_trees=None, report=None,
        saved=saved, pair_requests=pairs, selection=_selection())
    output_path = tmp_path / "saved"
    output_path.mkdir()
    output = worker.run_protein_phylogeny_result(modified, output_directory=output_path)
    assert output["documents"] is None
    sheet = json.loads((output_path / "sheet.json").read_bytes())
    assert sheet["context"] == original["context"]
    assert [row["components"]["distances"][0]["value"]["value"] for row in sheet["trees"]] == pytest.approx([-.1, -.1])
    assert [row["tree"] for row in sheet["trees"]] == [row["tree"] for row in original["trees"]]


def test_projection_preserves_order_population_and_omitted_counts_without_calculator(tmp_path, monkeypatch):
    _, _, sheet, _, _ = _run(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("literal projection must not parse or calculate")
    monkeypatch.setattr(worker, "parse_newick", forbidden)
    monkeypatch.setattr(worker, "tree_components", forbidden)
    selection = _selection()
    selection["trees"].reverse()
    selection["nodes"] = dict(indices=[5, 0, 1], offset=1, limit=2)
    value = contracts.project_phylogeny_value(sheet, selection)
    assert [row["role"] for row in value["trees"]] == list(reversed(contracts.ROLES))
    assert [entry["node"]["node_index"] for entry in value["trees"][0]["nodes"]] == [0, 1]
    assert value["trees"][0]["leaf_population"]["node_indices"] == [2, 3, 5, 6]
    assert value["trees"][0]["accounting"]["nodes"] == dict(retained_record_count=7, selected_record_count=3,
        returned_record_count=2, omitted_record_count=1)
    before = deepcopy(sheet)
    value["trees"][0]["nodes"][1]["node"]["decoded_label"] = "changed"
    assert sheet == before


@pytest.mark.parametrize("mutation", ["branch_identity", "wrong_population", "false_zero", "node_order", "tree_count", "support_method"])
def test_changed_public_values_fail_closed_contract(tmp_path, mutation):
    _, _, sheet, value, _ = _run(tmp_path)
    original = deepcopy(value)
    row = value["trees"][0]
    if mutation == "branch_identity":
        row["nodes"][1]["branch"]["node_index"] = 2
    elif mutation == "wrong_population":
        row["summary"]["tip_count"]["population_ref"] = "other"
    elif mutation == "false_zero":
        row["nodes"][2]["branch"]["support_rescaled"]["value"] = 0
    elif mutation == "node_order":
        row["nodes"].reverse()
    elif mutation == "tree_count":
        value["accounting"]["retained_record_count"] = 200
    else:
        row["nodes"][1]["branch"]["support_method"] = "rapid_bootstrap"
    with pytest.raises(ValueError):
        contracts.validate_phylogeny_value(value)
    if mutation == "branch_identity":
        def changed_artifact(node):
            if type(node) is dict:
                if "raw_artifact_ref" in node:
                    node["sha256"] = "0" * 64
                for child in node.values():
                    changed_artifact(child)
            elif type(node) is list:
                for child in node:
                    changed_artifact(child)
        for packet, validate in ((deepcopy(sheet), contracts.validate_phylogeny_sheet),
                (original, contracts.validate_phylogeny_value)):
            changed_artifact(packet["trees"][0]["tree"])
            with pytest.raises(ValueError, match="tree_capture_identity_conflict"):
                validate(packet)


def test_only_outer_return_source_is_semantic_and_closed_fact_schema_validates(tmp_path):
    _, _, _, value, _ = _run(tmp_path)
    returned = contracts.project_phylogeny_return(value, source_ref="source_" + "a" * 24)
    schema = contracts.phylogeny_result_schema()
    Draft202012Validator.check_schema(schema)
    assert Draft202012Validator(schema).is_valid(returned)
    paths = []
    def visit(node, path):
        if type(node) is dict:
            if node.get("format") == "reference" or "x-reference-namespace" in node:
                paths.append(path)
            for key, child in node.items():
                visit(child, path + "/" + key)
        elif type(node) is list:
            for index, child in enumerate(node):
                visit(child, path + "/" + str(index))
    visit(schema, "")
    assert paths == ["/$defs/Return/properties/source_ref"]
    facts = contracts.phylogeny_fact_sources()[contracts.FACT_SOURCE]
    assert facts["type"] == "array" and facts["report_schema"]["x-source"] == contracts.FACT_SOURCE
    Draft202012Validator.check_schema(facts["report_schema"])
    assert Draft202012Validator(facts["report_schema"]).is_valid([returned])


def test_modified_input_pin_fails_before_any_tree_values(tmp_path):
    request = _fixture(tmp_path)
    Path(request["captured_trees"][0]["captured"]["path"]).write_bytes(b"different")
    with pytest.raises(ValueError, match="file_identity_conflict"):
        worker._parse(worker.validate_protein_phylogeny_result_request(request))


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -1])
def test_noninteger_or_nonfinite_selected_node_index_is_rejected(bad):
    selection = _selection()
    selection["nodes"]["indices"] = [bad]
    with pytest.raises(ValueError):
        contracts.validate_phylogeny_selection(selection)


def test_duplicate_pair_requests_rejected_before_saved_calculation(tmp_path):
    request = _fixture(tmp_path)
    pair = dict(role=contracts.ROLES[0], tree_index=0, node_a=2, node_b=3)
    request["pair_requests"] = [pair, deepcopy(pair)]
    with pytest.raises(ValueError, match="duplicate_pair_request"):
        worker.validate_protein_phylogeny_result_request(request)
