"""Selected-input authority over real Store, Journal and frozen receipts.

Scientific inputs and software declarations are explicitly synthetic and never
parsed or probed. Run these checks through packet450's bounded native lifecycle.
They do not establish native execution, numerical validity or Workflow wiring.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode import chromatin_interaction_operands as operands
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_chromatin_interaction_contracts import (
    REQUIRED_DEPENDENCIES, REQUIRED_MODULES, requested_job_from_chromatin,
)
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


def source(store, label, raw=None):
    artifact = store.artifact(label.encode() if raw is None else raw)
    return store.put("source", {"provider": "fixture.chromatin." + label,
        "accession": None, "uri": None, "artifact_ref": artifact, "text_ref": None,
        "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")


def identity(store, artifact, format):
    row = store.get(artifact)
    return {"artifact_ref": artifact, "sha256": row["sha256"], "size_bytes": row["size"], "format": format}


def reference(source_ref=None):
    return {"assembly_accession": "fixture.1", "assembly_label": "fixture",
        "contigs": [{"chromosome": "chr1", "length_bp": 100}], "source_ref": source_ref}


def make_request(f):
    f.sources = {name: source(f.store, name) for name in (
        "contact", "elements", "element_reference", "gene0", "gene1", "contact_reference",
        "sample0", "sample1", "link0", "link1", "dependence", "uncertainty0", "uncertainty1")}
    r = {key: row["id"] for key, row in f.sources.items()}
    contact = {"input_key": "contact", "file": identity(f.store,
        f.sources["contact"]["artifact_ref"], "cooler_hdf5_v3"), "source_ref": r["contact"],
        "format": "cooler_hdf5_v3", "group_path": "/", "resolution_bp": 10,
        "value_field": "count", "value_kind": "contact_count", "value_unit": "contacts", "specimen_key": None}
    elements = {"input_key": "elements", "file": identity(f.store,
        f.sources["elements"]["artifact_ref"], "bed_outer_span_v1"), "source_ref": r["elements"],
        "format": "bed_outer_span_v1", "reference": reference(r["element_reference"]), "assignments": [
            {"element_key": "element" + str(i), "source_data_row": i,
             "class": "enhancer" if i == 0 else "promoter", "anchor": {"policy": "interval_start"},
             "gene_links": [{"gene_key": "gene" + str(i), "relationship": "supplied_association",
                             "source_ref": r["gene" + str(i)]}]} for i in range(2)]}
    metadata = {"reference": reference(r["contact_reference"]),
        "samples": [{"sample_key": "sample" + str(i), "condition_key": "condition" + str(i),
            "replicate_key": "replicate" + str(i), "assay": "Hi-C", "source_ref": r["sample" + str(i)]}
            for i in range(2)],
        "contact_sample_links": [{"contact_input_key": "contact", "sample_key": "sample" + str(i),
            "fraction": None, "source_ref": r["link" + str(i)]} for i in range(2)],
        "dependence_groups": [{"group_key": "group", "member_sample_keys": ["sample0", "sample1"],
            "relationship": "shared_library", "source_ref": r["dependence"]}],
        "native_attribute_bindings": [{"native_attribute_path": "/attrs/" + name, "meaning": name,
            "supplied_target_key": target} for name, target in (("sample_key", "sample0"),
            ("condition_key", "condition0"), ("replicate_key", "replicate0"), ("assembly_label", "fixture"))],
        "supplied_uncertainty": [{"input_key": key, "population_key": "region" if i == 0 else None,
            "field": "source_assay_measurement", "native_attribute_path": None, "kind": "standard_error",
            "value": 0.2, "lower": None, "upper": None, "unit": {"kind": "dimensionless", "source_unit": None},
            "source_ref": r["uncertainty" + str(i)]} for i, key in enumerate(("contact", "elements"))]}
    return {"version": "chromatin_interaction_request_v1", "operation": "analyze_chromatin_interactions",
        "analysis_modes": ["cis_anchor_contact_enrichment", "cross_window_insulation_heuristic"],
        "contact": contact, "elements": elements,
        "populations": [{"population_key": "region", "chromosome": "chr1", "start_bp": 0, "end_bp": 60}],
        "normalization": {"kind": "raw", "weight_column": None, "convention": None},
        "supplied_metadata": metadata, "output_prefix": "chromatin"}


def selected_references(request):
    # Explicit expected order, independent of production enumeration.
    contact, elements, metadata = request["contact"], request["elements"], request["supplied_metadata"]
    refs = [contact["source_ref"], contact["file"]["artifact_ref"]]
    if elements is not None:
        refs.extend([elements["source_ref"], elements["file"]["artifact_ref"], elements["reference"]["source_ref"]])
        refs.extend(link["source_ref"] for row in elements["assignments"] for link in row["gene_links"])
    refs.append(metadata["reference"]["source_ref"])
    refs.extend(row["source_ref"] for key in ("samples", "contact_sample_links", "dependence_groups", "supplied_uncertainty")
        for row in metadata[key])
    return list(dict.fromkeys(ref for ref in refs if ref is not None))


def make_assignment(f, request=None):
    request = deepcopy(f.request if request is None else request)
    dependencies = [{"distribution": name, "version": "fixture", "package_root": "/fixture/deps/" + name,
        "files": [{"path": "/fixture/deps/" + name + "/fixture", "sha256": "3" * 64, "size_bytes": 1}]}
        for name in sorted(REQUIRED_DEPENDENCIES)]
    software = {"python_executable": "/fixture/python", "python_sha256": "1" * 64,
        "python_version": "fixture", "module_root": "/fixture/source",
        "driver_module": "gene_annotation_episode.native_chromatin_interaction_driver",
        "implementation_files": [{"module": name, "sha256": "2" * 64} for name in sorted(REQUIRED_MODULES)],
        "dependencies": dependencies}
    specs = [request["contact"]] + ([request["elements"]] if request["elements"] is not None else [])
    job = {"request": request, "software": software, "input_bindings": [{"input_key": spec["input_key"],
        "file": deepcopy(spec["file"]), "path": str(f.store.path / "artifacts" / spec["file"]["sha256"][:2]
            / spec["file"]["sha256"])} for spec in specs]}
    dependency_roots = [row["package_root"] for row in sorted(dependencies,
        key=lambda row: row["distribution"] not in {"numpy", "h5py"})]
    environment = {key: "/fixture/runtime" for key in
        ("PYTHONHOME", "TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME", "PIP_CACHE_DIR")}
    environment.update({key: "1" for key in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE",
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")})
    environment["PYTHONPATH"] = ":".join([software["module_root"], *dependency_roots])
    return {"requested_job": requested_job_from_chromatin(job, environment=environment)}


def context(f, *, parent=None, role="annotation", index=0, assigned=None, persist=True, scope=None):
    path = (() if parent is None else parent.path) + ((role, "root" if parent is None else "child_" + str(index)),)
    episode_id = EpisodeRef(f.run_id, path).episode_id
    scope = deepcopy(f.scope if scope is None else scope)
    assigned = {} if assigned is None else deepcopy(assigned)
    manifest = f.receipts.bind(episode_id, None if parent is None else parent.episode_id)
    schema = {"type": "object", "properties": {"received": {"type": "boolean",
        "description": "Whether the child observed the assigned supplied input records."}},
        "required": ["received"], "additionalProperties": False}
    contract = None if parent is None else TypedReportContract("Return selected chromatin input facts", schema, lambda *_: True)
    goal = (EpisodeGoal.root(objective="Verify supplied chromatin input authority", result_contract={"role": role})
        if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
            objective="Verify supplied chromatin input authority", result_contract=schema))
    message = {"scope": scope, "episode_assignment": assigned,
        "initial_report": {} if parent is None else {"received": False}, "knowledge_inheritance": manifest}
    request = EpisodeRequest(goal, Record(message), contract).as_record()
    result = BindingContext(f.run_id, episode_id, role, path, scope, assigned, request)
    if persist:
        f.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        if parent is not None:
            selection = {"kind": "episode_child", "role": role, "assignment": assigned,
                "scope": scope, "purpose": contract.decision, "schema_json": canonical(schema)}
            f.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
                "action": canonical(selection), "result": None, "credit": None})
    return result


@pytest.fixture(scope="module")
def problem_template(tmp_path_factory):
    path = tmp_path_factory.mktemp("chromatin_problem") / "store"
    with Store(path) as store:
        store.create_problem(raw_sequence="ACGTACGT", molecule="dna")
        fixture = SimpleNamespace(store=store)
        request = make_request(fixture)
    # Reuse original immutable authored inputs; every test still gets its own
    # real Store and creates independent actual runtime/receipt records.
    return path, request, fixture.sources


@pytest.fixture
def f(tmp_path, problem_template):
    template, request, sources = problem_template
    shutil.copytree(template, tmp_path / "store")
    with Store(tmp_path / "store") as store:
        value = SimpleNamespace(store=store, run_id="chromatin-selected-inputs450",
            scope={"subject_refs": store.problem()["subject_refs"]})
        value.journal, value.receipts = Journal(store, value.run_id), EpisodeReceipts(store, value.run_id)
        value.root = context(value)
        value.request, value.sources = deepcopy(request), deepcopy(sources)
        value.receipts.receive(value.root.episode_id, selected_references(value.request), kind="initial")
        yield value


def validate(f, assigned=None, *, using=None, access=lambda *_: None):
    return operands.validate_chromatin_job_inputs(f.store, using or f.root,
        make_assignment(f) if assigned is None else assigned, reference_access=access)


def fails(code):
    return pytest.raises(ValueError, match="^chromatin_input_" + code + "$")


def test_exact_selected_reference_order_is_detached_without_mutation(f):
    assigned = make_assignment(f)
    original = deepcopy(assigned)
    before, changes = list(f.store.db.iterdump()), f.store.db.total_changes
    expected = selected_references(f.request)
    assert validate(f, assigned) == expected
    result = validate(f, assigned)
    result.clear()
    assert validate(f, assigned) == expected
    assert assigned == original and list(f.store.db.iterdump()) == before
    assert f.store.db.total_changes == changes
    assert all(f.store.roots(ref) == [] for ref in expected)
    unselected = {row["artifact_ref"] for key, row in f.sources.items() if key not in {"contact", "elements"}}
    assert not unselected.intersection(expected)


def test_insulation_only_has_no_imaginary_elements_reference_or_uncertainty(f):
    f.request["elements"] = None
    f.request["analysis_modes"] = ["cross_window_insulation_heuristic"]
    metadata = f.request["supplied_metadata"]
    metadata.update(reference={"assembly_accession": None, "assembly_label": None, "contigs": None, "source_ref": None})
    for key in ("samples", "contact_sample_links", "dependence_groups", "native_attribute_bindings", "supplied_uncertainty"):
        metadata[key] = []
    assert validate(f) == selected_references(f.request)
    assert len(validate(f)) == 2


def test_present_reference_assertions_can_have_no_source_handle(f):
    f.request["elements"]["reference"]["source_ref"] = None
    f.request["supplied_metadata"]["reference"]["source_ref"] = None
    assert validate(f) == selected_references(f.request)
    assert len(validate(f)) == 13


@pytest.mark.parametrize("access_result", [None, True])
@pytest.mark.parametrize("position", range(15))
def test_each_explicit_source_and_file_requires_actual_receipt_despite_hints(f, access_result, position):
    reference = selected_references(f.request)[position]
    f.store.db.execute("DELETE FROM runtime_record_receipts WHERE record_ref=?", (reference,))
    hinted = replace(f.root, received_record_refs=(reference,))
    assert f.store.get(reference)["id"] == reference
    with fails("input_not_received"):
        validate(f, using=hinted, access=lambda *_: access_result)


@pytest.mark.parametrize("result,code", [(False, "protected_reference_denied"), (1, "invalid_reference_access"),
    (0, "invalid_reference_access"), ("yes", "invalid_reference_access"), (object(), "invalid_reference_access")])
def test_composite_provider_denial_and_strict_tri_state(f, result, code):
    private = f.request["contact"]["file"]["artifact_ref"]
    # The broadly scoped source and real receipt already make the artifact
    # accessible through Store. Provider classification must still be final.
    assert private in f.store.reference_subset([private], f.scope)
    with fails(code):
        validate(f, access=lambda _, ref, namespace: result if ref == private else None)


@pytest.mark.parametrize("role", ["launch", "launch_local", "launch_hpc", "launch_api", "results"])
@pytest.mark.parametrize("kind", ["initial", "own_action", "child_form"])
def test_execution_roles_use_frozen_inheritance_and_original_own_inputs(f, role, kind):
    child = context(f, parent=f.root, role=role)
    new = source(f.store, "new-input")
    f.request["supplied_metadata"]["samples"][0]["source_ref"] = new["id"]
    f.receipts.receive(child.episode_id, [new["id"]], kind=kind)
    if kind == "initial":
        assert validate(f, using=child) == selected_references(f.request)
    else:
        with fails("input_not_received"):
            validate(f, using=child)


def test_scientific_current_receipts_and_frozen_descendants_do_not_share_future_inputs(f):
    science = context(f, parent=f.root, role="scientific_process")
    launch = context(f, parent=science, role="launch")
    local = context(f, parent=launch, role="launch_local")
    new = source(f.store, "later-reference")
    f.request["elements"]["reference"]["source_ref"] = new["id"]
    f.receipts.receive(science.episode_id, [new["id"]], kind="child_form", source_index=1)
    assert validate(f, using=science) == selected_references(f.request)
    for child in (launch, local):
        with fails("input_not_received"):
            validate(f, using=child)
    original_manifest = plain(launch.request)["message"]["knowledge_inheritance"]
    assert f.receipts.bind(launch.episode_id, science.episode_id) == original_manifest
    later = context(f, parent=science, role="launch", index=2, persist=False)
    assert validate(f, using=later) == selected_references(f.request)


def test_sibling_receipt_does_not_make_input_known(f):
    first = context(f, parent=f.root, role="scientific_process", index=0)
    second = context(f, parent=f.root, role="scientific_process", index=1)
    new = source(f.store, "sibling-reference")
    f.receipts.receive(first.episode_id, [new["id"]], kind="own_action")
    f.request["elements"]["assignments"][0]["gene_links"][0]["source_ref"] = new["id"]
    assert validate(f, using=first) == selected_references(f.request)
    with fails("input_not_received"):
        validate(f, using=second, access=lambda *_: True)


@pytest.mark.parametrize("fault", ["run", "episode", "path", "role", "request", "assignment", "scope",
    "consistent_assignment", "consistent_scope"])
def test_original_context_identity_cannot_be_replaced(f, fault):
    if fault == "run":
        changed = replace(f.root, run_id="other-run")
    elif fault == "episode":
        changed = replace(f.root, episode_id="other-episode")
    elif fault == "path":
        changed = replace(f.root, path=(("annotation", "other"),))
    elif fault == "role":
        changed = replace(f.root)
        object.__setattr__(changed, "role", "launch")
    elif fault == "request":
        request = plain(f.root.request)
        request["message"]["invented"] = True
        changed = replace(f.root, request=request)
    elif fault == "assignment":
        changed = replace(f.root, assignment={"invented": True})
    elif fault in {"consistent_assignment", "consistent_scope"}:
        field = "assignment" if fault == "consistent_assignment" else "scope"
        value = {"invented": True} if field == "assignment" else {"subject_refs": []}
        request = plain(f.root.request)
        request["message"]["episode_assignment" if field == "assignment" else "scope"] = value
        changed = replace(f.root, request=request, **{field: value})
    else:
        changed = replace(f.root, scope={"subject_refs": []})
    with fails("invalid_context"):
        validate(f, using=changed)


@pytest.mark.parametrize("fault", ["missing", "altered", "legacy", "prefix", "wrong_parent", "cycle", "ancestor_manifest"])
def test_original_manifest_and_actual_path_ancestry_are_required(f, fault):
    child = context(f, parent=f.root, role="launch", persist=False)
    request = plain(child.request)
    if fault == "missing":
        del request["message"]["knowledge_inheritance"]
    elif fault == "altered":
        request["message"]["knowledge_inheritance"]["through_receipt_index"] += 1
    elif fault == "legacy":
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=NULL WHERE episode_id=?", (child.episode_id,))
        request["message"]["knowledge_inheritance"].pop("received_report_prefix")
    elif fault == "prefix":
        prefix = {"version": "frozen_received_report_prefix_v1", "attempts": [{"decision_index": 0,
            "delivery_ref": "unreceived", "child_episode_id": "unreceived", "contract_sha256": "1" * 64,
            "form_sha256": "2" * 64}]}
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE episode_id=?",
            (canonical(prefix), child.episode_id))
    elif fault == "wrong_parent":
        sibling = context(f, parent=f.root, role="scientific_process", index=1)
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET parent_episode_id=? WHERE episode_id=?",
            (sibling.episode_id, child.episode_id))
        request["message"]["knowledge_inheritance"] = f.receipts.manifest(child.episode_id)
    elif fault == "cycle":
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET parent_episode_id=? WHERE episode_id=?",
            (child.episode_id, f.root.episode_id))
    else:
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET through_receipt_index=999 WHERE episode_id=?", (f.root.episode_id,))
    with fails("invalid_context"):
        validate(f, using=replace(child, request=request))


@pytest.mark.parametrize("table", ["runtime_actions", "runtime_forms", "runtime_model_calls", "runtime_observations"])
def test_unsaved_construction_cannot_hide_existing_history(f, table):
    child = context(f, parent=f.root, role="launch", persist=False)
    rows = {"runtime_actions": {"decision_index": 0, "action": "{}", "result": "{}", "credit": 0},
        "runtime_forms": {"facts": "{}", "form": "{}"},
        "runtime_model_calls": {"call_index": 0, "purpose": "decision", "request": "{}", "response": "{}"},
        "runtime_observations": {"unit_index": 0, "observation": "{}"}}
    f.journal.save(table, {"episode_id": child.episode_id, **rows[table]})
    with fails("invalid_context"):
        validate(f, using=child)


@pytest.mark.parametrize("slot", ["contact", "elements"])
def test_source_file_pair_requires_exact_identity_even_with_equal_sizes(f, slot):
    selected = make_assignment(f)
    job = selected["requested_job"]["native_chromatin_interactions"]
    replacement = source(f.store, "other-" + slot, b"z" * job["request"][slot]["file"]["size_bytes"])
    f.receipts.receive(f.root.episode_id, [replacement["id"]], kind="own_action")
    file = identity(f.store, replacement["artifact_ref"], job["request"][slot]["format"])
    job["request"][slot]["file"] = file
    binding = job["input_bindings"][0 if slot == "contact" else 1]
    binding.update(file=deepcopy(file), path=str(f.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]))
    with fails("source_artifact_mismatch"):
        validate(f, selected)


@pytest.mark.parametrize("field", ["sha256", "size_bytes"])
def test_declared_file_identity_matches_store_metadata(f, field):
    selected = make_assignment(f)
    job = selected["requested_job"]["native_chromatin_interactions"]
    file = job["request"]["contact"]["file"]
    file[field] = "f" * 64 if field == "sha256" else file[field] + 1
    job["input_bindings"][0]["file"] = deepcopy(file)
    with fails("artifact_metadata_mismatch"):
        validate(f, selected)


@pytest.mark.parametrize("field,value", [("sha256", "f" * 64), ("size", 999), ("media_type", "bad\nmedia")])
def test_actual_artifact_metadata_must_be_valid(f, field, value):
    selected = make_assignment(f)
    ref = f.request["contact"]["file"]["artifact_ref"]
    f.store.db.execute(f"UPDATE artifacts SET {field}=? WHERE id=?", (value, ref))
    with fails("artifact_metadata_mismatch"):
        validate(f, selected)


@pytest.mark.parametrize("fault", ["argv", "format", "file_format", "bool_size", "artifact_id", "binding_key", "binding_order", "duplicate_binding", "duplicate_input"])
def test_present_job_uses_existing_c3_shape_and_input_binding_validator(f, fault):
    selected = make_assignment(f)
    job = selected["requested_job"]["native_chromatin_interactions"]
    if fault == "argv":
        selected["requested_job"]["argv"][-1] = "other.json"
    elif fault == "format":
        job["request"]["contact"]["format"] = "hic_binary_v9"
    elif fault in {"file_format", "bool_size", "artifact_id"}:
        key, value = {"file_format": ("format", "wrong"), "bool_size": ("size_bytes", True),
            "artifact_id": ("artifact_ref", "artifact_malformed")}[fault]
        job["request"]["contact"]["file"][key] = value
        job["input_bindings"][0]["file"][key] = value
    elif fault == "binding_key":
        job["input_bindings"][0]["input_key"] = "foreign"
    elif fault == "binding_order":
        job["input_bindings"].reverse()
    elif fault == "duplicate_binding":
        job["input_bindings"].append(deepcopy(job["input_bindings"][0]))
    else:
        job["request"]["elements"]["input_key"] = "contact"
        job["input_bindings"][1]["input_key"] = "contact"
    with fails("invalid_requested_job"):
        validate(f, selected)


@pytest.mark.parametrize("fault", ["alternate", "dot", "parent", "trailing"])
def test_selected_path_is_exact_canonical_store_path_without_resolving_it(f, fault):
    selected = make_assignment(f)
    binding = selected["requested_job"]["native_chromatin_interactions"]["input_bindings"][0]
    parent, name = binding["path"].rsplit("/", 1)
    binding["path"] = {"alternate": "/not-the-store/" + name, "dot": parent + "/./" + name,
        "parent": parent + "/other/../" + name, "trailing": binding["path"] + "/"}[fault]
    with fails("selected_path_mismatch" if fault == "alternate" else "invalid_requested_job"):
        validate(f, selected)


def test_actual_other_target_is_outside_scope_before_source_kind(tmp_path):
    # Store intentionally keeps broad scalar-region read visibility. Use a
    # genuinely different target, not an invented segment access restriction.
    input_path = tmp_path / "two-targets.fasta"
    input_path.write_text(">selected\nACGTACGT\n>foreign\nTTTTCCCC\n")
    with Store(tmp_path / "two-target-store") as store:
        targets = store.create_problem(input_path, molecule="dna", format="fasta")["subject_refs"]
        f = SimpleNamespace(store=store, run_id="chromatin-foreign-target450", scope={"subject_refs": [targets[0]]})
        f.journal, f.receipts = Journal(store, f.run_id), EpisodeReceipts(store, f.run_id)
        f.root = context(f)
        f.request = make_request(f)
        f.receipts.receive(f.root.episode_id, [*selected_references(f.request), targets[1]], kind="initial")
        f.request["contact"]["source_ref"] = targets[1]
        with fails("input_outside_scope"):
            validate(f)


@pytest.mark.parametrize("slot", ["contact", "elements", "metadata"])
def test_source_kind_must_match_selected_role(f, slot):
    artifact = f.request["contact"]["file"]["artifact_ref"]
    if slot == "metadata":
        f.request["supplied_metadata"]["supplied_uncertainty"][0]["source_ref"] = artifact
    else:
        f.request[slot]["source_ref"] = artifact
    with fails("metadata_source_required" if slot == "metadata" else "source_artifact_mismatch"):
        validate(f)


@pytest.mark.parametrize("fault", ["sample", "contact_input", "dependence", "uncertainty_input", "uncertainty_population",
    "sample_key", "group_key", "population_key", "element_key", "element_row", "element_contig", "contact_contig",
    "attribute_sample", "attribute_condition", "attribute_replicate", "attribute_assembly"])
def test_structural_metadata_joins_and_duplicate_keys_reject(f, fault):
    selected = make_assignment(f)
    request = selected["requested_job"]["native_chromatin_interactions"]["request"]
    metadata, elements = request["supplied_metadata"], request["elements"]
    if fault in {"sample", "contact_input"}:
        metadata["contact_sample_links"][0]["sample_key" if fault == "sample" else "contact_input_key"] = "foreign"
    elif fault == "dependence":
        metadata["dependence_groups"][0]["member_sample_keys"] = ["foreign"]
    elif fault.startswith("uncertainty_"):
        metadata["supplied_uncertainty"][0][fault.removeprefix("uncertainty_") + "_key"] = "foreign"
    elif fault in {"sample_key", "group_key", "population_key"}:
        rows = metadata["samples"] if fault == "sample_key" else metadata["dependence_groups"] if fault == "group_key" else request["populations"]
        rows.append(deepcopy(rows[0]))
    elif fault in {"element_key", "element_row"}:
        key = "element_key" if fault == "element_key" else "source_data_row"
        elements["assignments"][1][key] = elements["assignments"][0][key]
    elif fault.endswith("_contig"):
        ref = elements["reference"] if fault == "element_contig" else metadata["reference"]
        ref["contigs"].append(deepcopy(ref["contigs"][0]))
    else:
        index = ["attribute_sample", "attribute_condition", "attribute_replicate", "attribute_assembly"].index(fault)
        metadata["native_attribute_bindings"][index]["supplied_target_key"] = "foreign"
    with fails("metadata_relation_mismatch"):
        validate(f, selected)


def test_ordinary_biological_strings_are_not_followed_as_references(f):
    literal = "artifact_" + "f" * 64
    request, metadata = f.request, f.request["supplied_metadata"]
    request["contact"].update(specimen_key=literal, group_path="/" + literal)
    request["output_prefix"] = literal
    request["populations"][0]["chromosome"] = literal
    request["elements"]["assignments"][0]["gene_links"][0]["gene_key"] = literal
    for ref in (request["elements"]["reference"], metadata["reference"]):
        ref.update(assembly_accession=literal, assembly_label=literal)
        ref["contigs"][0]["chromosome"] = literal
    metadata["samples"][0].update(sample_key=literal, condition_key=literal, replicate_key=literal)
    metadata["contact_sample_links"][0]["sample_key"] = literal
    metadata["dependence_groups"][0]["member_sample_keys"][0] = literal
    for row in metadata["native_attribute_bindings"]:
        row.update(native_attribute_path="/" + literal, supplied_target_key=literal)
    calls = []
    def access(_, ref, namespace):
        calls.append(ref)
        assert namespace is None and ref != literal
        return None
    assert validate(f, access=access) == selected_references(request)
    assert literal not in calls


def test_shared_metadata_handle_is_checked_per_role_and_returned_once(f):
    shared = f.request["contact"]["source_ref"]
    request, metadata = f.request, f.request["supplied_metadata"]
    request["elements"]["reference"]["source_ref"] = shared
    for assignment in request["elements"]["assignments"]:
        assignment["gene_links"][0]["source_ref"] = shared
    metadata["reference"]["source_ref"] = shared
    for name in ("samples", "contact_sample_links", "dependence_groups", "supplied_uncertainty"):
        for row in metadata[name]:
            row["source_ref"] = shared
    selected = make_assignment(f)
    before, calls = deepcopy(selected), []
    assert validate(f, selected, access=lambda _, ref, ns: calls.append(ref)) == selected_references(request)
    assert selected == before and calls.count(shared) == 12
    assert validate(f, selected).count(shared) == 1


def test_identical_bytes_preserve_both_input_roles_and_only_deduplicate_return_handle(f):
    #441/010 corrects C3's byte-identity check. These deliberately opaque bytes
    # are not evidence that one file actually parses as both Cooler and BED.
    repeated = source(f.store, "elements-same-bytes", b"contact")
    f.receipts.receive(f.root.episode_id, [repeated["id"]], kind="own_action")
    file = deepcopy(f.request["contact"]["file"])
    file["format"] = "bed_outer_span_v1"
    f.request["elements"].update(source_ref=repeated["id"], file=file)
    selected = make_assignment(f)
    original, calls = deepcopy(selected), []
    actual = validate(f, selected, access=lambda _, ref, ns: calls.append(ref))
    assert actual == selected_references(f.request) and len(actual) == 14
    assert actual.count(file["artifact_ref"]) == 1 and calls.count(file["artifact_ref"]) == 2
    assert selected == original
    bindings = selected["requested_job"]["native_chromatin_interactions"]["input_bindings"]
    assert [row["input_key"] for row in bindings] == ["contact", "elements"]
    assert [row["file"]["format"] for row in bindings] == ["cooler_hdf5_v3", "bed_outer_span_v1"]
    assert bindings[0]["path"] == bindings[1]["path"]


def test_supplied_assembly_conflict_and_unknown_fraction_are_not_scientific_gates(f):
    f.request["elements"]["reference"].update(assembly_accession="other.1", assembly_label="other")
    for row in f.request["supplied_metadata"]["contact_sample_links"]:
        row["fraction"] = 0.8  # No unprovided sum-to-one rule is imposed.
    assert validate(f) == selected_references(f.request)


@pytest.mark.parametrize("state", ["present", "missing", "changed"])
def test_metadata_only_boundary_never_reads_bytes_executes_or_writes_authority(f, monkeypatch, state):
    import builtins
    import io
    import os
    import socket
    import subprocess
    from gene_annotation_episode import materials, native_file_capture, native_lifecycle, local_jobs
    from gene_annotation_episode import chromatin_interaction_inputs, chromatin_cooler_inputs
    from gene_annotation_episode import native_chromatin_interaction_driver
    selected = make_assignment(f)
    expected = selected_references(f.request)
    for binding in selected["requested_job"]["native_chromatin_interactions"]["input_bindings"]:
        path = Path(binding["path"])
        if state == "missing":
            path.unlink()
        elif state == "changed":
            path.write_bytes(b"z" * binding["file"]["size_bytes"])
    before, changes = list(f.store.db.iterdump()), f.store.db.total_changes
    def forbidden(*args, **kwargs):
        raise AssertionError("input authority attempted bytes, parser, work, hash, stat or mutation")
    with monkeypatch.context() as patch:
        for owner, names in ((builtins, ("open",)), (io, ("open",)), (os, ("open", "stat", "lstat")),
                (Path, ("open", "read_bytes", "read_text", "stat", "lstat", "resolve")),
                (f.store, ("get_artifact", "artifact", "put")),
                (materials, ("artifact_path", "artifact_file")),
                (native_file_capture, ("retained_native_file", "capture_native_file")),
                (chromatin_interaction_inputs, ("parse_chromatin_elements", "extract_chromatin_metadata", "build_chromatin_sheet")),
                (chromatin_cooler_inputs, ("read_cooler_contacts",)),
                (native_chromatin_interaction_driver, ("run_chromatin_interaction_driver",)),
                (subprocess, ("Popen", "run")), (socket, ("create_connection",)),
                (native_lifecycle, ("prepare_job", "start_prepared")), (local_jobs, ("run_local_job",)),
                (EpisodeReceipts, ("__init__", "bind", "receive"))):
            for name in names:
                patch.setattr(owner, name, forbidden)
        assert validate(f, selected) == expected
        with fails("protected_reference_denied"):
            validate(f, selected, access=lambda *_: False)
        assert list(f.store.db.iterdump()) == before and f.store.db.total_changes == changes


@pytest.mark.parametrize("value", [None, {}, [], "malformed"])
def test_malformed_present_native_key_does_not_silently_opt_out(f, value):
    with fails("invalid_requested_job"):
        validate(f, {"requested_job": {"native_chromatin_interactions": value}})


def test_unrelated_request_needs_no_context_or_provider(f):
    assert operands.validate_chromatin_job_inputs(f.store, None,
        {"requested_job": {"argv": ["ordinary"]}}, reference_access=None) == []


def test_missing_runtime_schema_and_receipts_are_not_installed(f):
    f.store.db.execute("DROP TABLE runtime_receipt_inheritance")
    before, changes = list(f.store.db.iterdump()), f.store.db.total_changes
    with fails("invalid_context"):
        validate(f)
    assert list(f.store.db.iterdump()) == before and f.store.db.total_changes == changes


def test_unexpected_programming_callback_and_storage_errors_propagate(f, monkeypatch):
    selected = make_assignment(f)
    for error in (RuntimeError("callback bug"), TypeError("callback bug"), sqlite3.ProgrammingError("callback bug")):
        def callback(*args):
            raise error
        with pytest.raises(type(error), match="callback bug"):
            validate(f, selected, access=callback)
    def broken_scope(*args):
        raise sqlite3.OperationalError("storage failure")
    monkeypatch.setattr(f.store, "reference_subset", broken_scope)
    with pytest.raises(sqlite3.OperationalError, match="storage failure"):
        validate(f, selected)
