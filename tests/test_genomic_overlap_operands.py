"""Real Store/receipt authority tests; no native execution or episode-path claim.

The declared software binding is synthetic and never probed. Test execution is
enclosed in packet430's local_jobs worker, with a readonly source snapshot.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode import genomic_overlap_operands as operands
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_genomic_overlap_contracts import (
    genomic_overlap_output_files, requested_job_from_genomic_overlap,
)
from gene_annotation_episode.state import Store


def source(store, raw, *, label):
    artifact = store.artifact(raw)
    return store.put("source", {"provider": "fixture.genomic_overlap." + label,
        "accession": None, "uri": None, "artifact_ref": artifact,
        "text_ref": None, "request_ref": None, "version": None,
        "retrieved_at": None}, origin="caller")


def file_identity(store, artifact, format):
    metadata = store.get(artifact)
    return {"artifact_ref": artifact, "sha256": metadata["sha256"],
        "size_bytes": metadata["size"], "format": format}


def set_spec(store, key, raw, *, format="bed_outer_span_v1"):
    saved = source(store, raw, label=key)
    return {"set_key": key, "display_label": None, "source": {
        "kind": "bed_artifact" if format == "bed_outer_span_v1" else "coordinate_rows_artifact",
        "source_ref": saved["id"], "file": file_identity(store, saved["artifact_ref"], format)},
        "format": format, "reference": None}


def refs(specs):
    return list(dict.fromkeys(ref for spec in specs for ref in (
        spec["source"]["source_ref"], spec["source"]["file"]["artifact_ref"])))


def assignment(store, specs):
    request = {"version": "genomic_overlap_request_v1",
        "operation": "analyze_genomic_region_overlap", "mode": "unstranded_outer_span",
        "region_sets": deepcopy(specs), "comparisons": [], "output_prefix": "overlap"}
    for i, first in enumerate(specs):
        for second in specs[i + 1:]:
            ordinal = len(request["comparisons"])
            request["comparisons"].append({"comparison_key": "pair" + str(ordinal),
                "ordinal": ordinal, "a_set_key": first["set_key"], "b_set_key": second["set_key"]})
    modules = ["native_genomic_overlap_driver", "native_genomic_overlap_contracts",
        "genomic_overlap_contracts", "genomic_overlap_inputs"]
    # These fixture declarations are never native availability evidence.
    software = {"python_executable": "/fixture/python", "python_sha256": "1" * 64,
        "python_version": "3.12.3", "module_root": "/fixture/source",
        "driver_module": "gene_annotation_episode.native_genomic_overlap_driver",
        "implementation_files": [{"module": "gene_annotation_episode." + name,
            "sha256": "2" * 64} for name in modules],
        "bedtools_executable": "/fixture/bedtools", "bedtools_sha256": "3" * 64,
        "bedtools_version": "bedtools v2.31.1"}
    job = {"version": "native_genomic_overlap_job_v1", "program": "bedtools_intersect_all_pairs",
        "request": request, "software": software, "inputs": [{"set_key": spec["set_key"],
            "path": str(store.path / "artifacts" / spec["source"]["file"]["sha256"][:2]
                / spec["source"]["file"]["sha256"])} for spec in specs],
        "outputs": genomic_overlap_output_files(request), "environment": {"LC_ALL": "C"}}
    return {"requested_job": requested_job_from_genomic_overlap(job)}


def context(f, *, parent=None, role="annotation", label="root", save=True, scope=None,
            assigned=None, supplied_refs=()):
    path = (() if parent is None else parent.path) + ((role, label),)
    scope = f.scope if scope is None else scope
    assigned = {} if assigned is None else assigned
    request = {"message": {"scope": scope, "episode_assignment": assigned}}
    value = BindingContext(f.run_id, EpisodeRef(f.run_id, path).episode_id,
        role, path, scope, assigned, request, tuple(supplied_refs))
    if save:
        f.journal.save("runtime_episodes", {"episode_id": value.episode_id,
            "path": canonical(path), "request": canonical(request),
            "initial_credit": 0, "state": "active"})
    f.receipts.bind(value.episode_id, None if parent is None else parent.episode_id)
    return value


@pytest.fixture(scope="module")
def problem_template(tmp_path_factory):
    directory = tmp_path_factory.mktemp("original_store")
    with Store(directory / "store") as store:
        inputs = directory / "targets.fasta"
        inputs.write_text(">target\nACGTACGT\n>other\nTTTTCCCC\n")
        store.create_problem(inputs, molecule="dna", format="fasta")
    return directory / "store"


@pytest.fixture
def f(tmp_path, problem_template):
    # Copy the closed real Store so each authority test has independent state;
    # the fixture's unrelated two-sequence ingestion need happen only once.
    shutil.copytree(problem_template, tmp_path / "store")
    with Store(tmp_path / "store") as store:
        targets = store.problem()["subject_refs"]
        value = SimpleNamespace(store=store, run_id="genomic-overlap-authority-fixture",
            scope={"subject_refs": [targets[0]]}, other=targets[1])
        value.journal = Journal(store, value.run_id)
        value.receipts = EpisodeReceipts(store, value.run_id)
        value.root = context(value)
        value.specs = [set_spec(store, "A", b"chr1\t0\t10\n"),
            set_spec(store, "B", b"chr1\t7\t12\n")]
        value.receipts.receive(value.root.episode_id, refs(value.specs), kind="initial")
        yield value


def validate(f, assigned=None, *, using=None, access=lambda *_: None):
    return operands.validate_genomic_overlap_job_inputs(f.store, using or f.root,
        assignment(f.store, f.specs) if assigned is None else assigned, reference_access=access)


def fails(code):
    return pytest.raises(ValueError, match="^genomic_overlap_" + code + "$")


def add_metadata(f):
    assembly = source(f.store, b"supplied assembly metadata", label="assembly")
    contig = source(f.store, b"supplied contig metadata", label="contig")
    dictionary = source(f.store, b"dictionary is opaque here", label="dictionary")
    metadata = {"assembly_accession_version": "fixture-assembly.1", "assembly_label": None,
        "source_refs": [assembly["id"], assembly["id"]],
        "contigs": [{"chromosome": "chr1", "length_bp": 100, "sequence_accession_version": None,
            "sequence_sha256": None, "source_refs": [contig["id"], assembly["id"]]}],
        "sequence_dictionary": file_identity(f.store, dictionary["artifact_ref"], "dictionary_fixture_v1")}
    f.specs[0]["reference"] = metadata
    # Receipt of sources may carry their forward references; only the exact
    # explicitly selected refs belong in this validator's detached result.
    f.receipts.receive(f.root.episode_id, [assembly["id"], contig["id"], dictionary["artifact_ref"]],
        kind="own_action")
    return metadata, [assembly["id"], contig["id"], dictionary["artifact_ref"]]


def test_received_global_bed_and_coordinate_inputs_are_allowed_without_target_claim(f):
    f.specs[1] = set_spec(f.store, "Coordinates", b'[["chr1",7,12]]', format="coordinate_rows_v1")
    f.receipts.receive(f.root.episode_id, refs(f.specs[1:]), kind="own_action")
    expected = refs(f.specs)
    assert all(f.store.roots(ref) == [] for ref in expected)
    assert validate(f) == expected


@pytest.mark.parametrize("missing", ["source", "artifact"])
@pytest.mark.parametrize("access_result", [None, True])
def test_existing_unreceived_global_record_cannot_borrow_callback_or_supplied_context_grant(f, missing, access_result):
    selected = refs(f.specs)[0 if missing == "source" else 1]
    f.store.db.execute("DELETE FROM runtime_record_receipts WHERE record_ref=?", (selected,))
    forged_hint = replace(f.root, received_record_refs=(selected,))
    assert f.store.get(selected)["id"] == selected
    with fails("input_not_received"):
        validate(f, using=forged_hint, access=lambda *_: access_result)


def test_received_source_must_name_the_exact_selected_artifact(f):
    changed = deepcopy(f.specs)
    changed[0]["source"]["file"] = deepcopy(changed[1]["source"]["file"])
    with fails("source_artifact_mismatch"):
        validate(f, assignment(f.store, changed))


def test_equal_actual_bytes_at_another_path_are_not_the_selected_store_path(f, tmp_path):
    selected = assignment(f.store, f.specs)
    alternate = tmp_path / "equal.bed"
    alternate.write_bytes(b"chr1\t0\t10\n")
    assert hashlib.sha256(alternate.read_bytes()).hexdigest() == f.specs[0]["source"]["file"]["sha256"]
    selected["requested_job"]["native_genomic_overlap"]["inputs"][0]["path"] = str(alternate)
    with fails("selected_path_mismatch"):
        validate(f, selected)


@pytest.mark.parametrize("field", ["sha256", "size_bytes"])
def test_declared_identity_must_equal_retained_metadata(f, field):
    changed = deepcopy(f.specs)
    changed[0]["source"]["file"][field] = "f" * 64 if field == "sha256" else 999
    with fails("artifact_metadata_mismatch"):
        validate(f, assignment(f.store, changed))


@pytest.mark.parametrize("field,value", [("sha256", "f" * 64), ("size", 999), ("media_type", "bad\nmedia")])
def test_actual_artifact_metadata_identity_is_not_trusted_from_declaration(f, field, value):
    selected = assignment(f.store, f.specs)
    f.store.db.execute(f"UPDATE artifacts SET {field}=? WHERE id=?",
        (value, f.specs[0]["source"]["file"]["artifact_ref"]))
    with fails("artifact_metadata_mismatch"):
        validate(f, selected)


def test_metadata_inputs_are_explicit_ordered_deduplicated_and_not_guessed_joins(f):
    metadata, selected_metadata = add_metadata(f)
    first, second = refs(f.specs[:1]), refs(f.specs[1:])
    expected = first + selected_metadata + second
    result = validate(f)
    assert result == expected
    result.clear()
    assert validate(f) == expected
    # Metadata sources are individually selected; their custody artifacts are
    # not implicitly added to the output. The dictionary source is not selected.
    assert metadata["sequence_dictionary"]["artifact_ref"] in result + expected


@pytest.mark.parametrize("index", [0, 1, 2])
def test_each_explicit_metadata_reference_requires_its_own_receipt(f, index):
    _, selected = add_metadata(f)
    f.store.db.execute("DELETE FROM runtime_record_receipts WHERE record_ref=?", (selected[index],))
    with fails("input_not_received"):
        validate(f)


def test_dictionary_identity_is_checked_without_reading_its_contents(f):
    metadata, _ = add_metadata(f)
    metadata["sequence_dictionary"]["size_bytes"] += 1
    with fails("artifact_metadata_mismatch"):
        validate(f)


@pytest.mark.parametrize("metadata", [False, True])
def test_wrong_type_received_source_reference_rejects(f, metadata):
    if metadata:
        value, _ = add_metadata(f)
        value["source_refs"] = [f.specs[0]["source"]["file"]["artifact_ref"]]
    else:
        f.specs[0]["source"]["source_ref"] = f.specs[0]["source"]["file"]["artifact_ref"]
    with fails("source_artifact_mismatch"):
        validate(f)


def test_existing_scope_boundary_rejects_received_foreign_subject_as_source(f):
    # Sources/artifacts themselves are global in Store. This actual scoped input
    # is also the wrong source type; the earlier existing scope boundary rejects
    # it without manufacturing a source-to-target association.
    f.receipts.receive(f.root.episode_id, [f.other], kind="initial")
    f.specs[0]["source"]["source_ref"] = f.other
    with fails("input_outside_scope"):
        validate(f)


def test_repeated_source_under_distinct_set_keys_remains_separate_selected_input(f):
    repeated = deepcopy(f.specs[0])
    repeated["set_key"] = "A_again"
    f.specs.append(repeated)
    selected = assignment(f.store, f.specs)
    original = deepcopy(selected)
    assert validate(f, selected) == refs(f.specs[:2])
    assert selected == original
    assert len(selected["requested_job"]["native_genomic_overlap"]["inputs"]) == 3


def test_later_parent_receipts_do_not_extend_frozen_child_or_grandchild(f):
    launch = context(f, parent=f.root, role="launch", label="child_0")
    local = context(f, parent=launch, role="launch_local", label="child_0")
    assert validate(f, using=launch) == validate(f, using=local) == refs(f.specs)
    f.specs[1] = set_spec(f.store, "Later", b"chr1\t20\t30\n")
    f.receipts.receive(f.root.episode_id, refs(f.specs[1:]), kind="own_action")
    assert validate(f) == refs(f.specs)
    for child in (launch, local):
        with fails("input_not_received"):
            validate(f, using=child)
    later = context(f, parent=f.root, role="launch", label="child_1", save=False)
    assert validate(f, using=later) == refs(f.specs)


@pytest.mark.parametrize("role", ["launch", "launch_local", "launch_hpc", "launch_api", "results"])
@pytest.mark.parametrize("receipt_kind", ["own_action", "child_form", "initial"])
def test_resource_episode_uses_only_original_own_inputs_and_frozen_inheritance(f, role, receipt_kind):
    child = context(f, parent=f.root, role=role, label="child_0")
    f.specs[1] = set_spec(f.store, "Own", b"chr1\t40\t50\n")
    f.receipts.receive(child.episode_id, refs(f.specs[1:]), kind=receipt_kind)
    if receipt_kind == "initial":
        assert validate(f, using=child) == refs(f.specs)
    else:
        with fails("input_not_received"):
            validate(f, using=child)


@pytest.mark.parametrize("where", ["source", "artifact", "assembly", "contig", "dictionary"])
def test_protected_callback_denial_precedes_ordinary_receipt_visibility(f, where):
    _, selected_metadata = add_metadata(f)
    selected = dict(zip(["source", "artifact", "assembly", "contig", "dictionary"],
        refs(f.specs[:1]) + selected_metadata))[where]
    called = []
    def access(ctx, ref, namespace):
        assert ctx is f.root and namespace is None
        called.append(ref)
        return False if ref == selected else None
    with fails("protected_reference_denied"):
        validate(f, access=access)
    assert called[-1] == selected
    f.store.db.execute("DELETE FROM runtime_record_receipts WHERE record_ref=?", (selected,))
    with fails("protected_reference_denied"):
        validate(f, access=access)


@pytest.mark.parametrize("field", ["scope", "assignment", "request", "episode_id", "saved_scope"])
def test_forged_supplied_context_rejects_against_original_saved_context(f, field):
    changes = {"scope": {"subject_refs": [f.other]}, "assignment": {"forged": True},
        "request": {"message": {"scope": f.scope, "episode_assignment": {}, "forged": True}},
        "episode_id": "not-the-original-episode"}
    if field == "saved_scope":
        changed_scope = {"subject_refs": [f.other]}
        changed = replace(f.root, scope=changed_scope,
            request={"message": {"scope": changed_scope, "episode_assignment": {}}})
    else:
        changed = replace(f.root, **{field: changes[field]})
    with fails("invalid_context"):
        validate(f, using=changed)


def test_unsaved_construction_is_allowed_with_real_frozen_receipts(f):
    child = context(f, parent=f.root, role="launch", label="not-saved", save=False)
    assert validate(f, using=child) == refs(f.specs)


def test_unbound_receipt_context_rejects_without_installing_authority(f):
    f.store.db.execute("DELETE FROM runtime_receipt_inheritance WHERE episode_id=?", (f.root.episode_id,))
    before = f.store.db.total_changes
    with fails("invalid_context"):
        validate(f)
    assert f.store.db.total_changes == before


def test_non_overlap_assignment_does_not_need_context_or_callback(f):
    assert operands.validate_genomic_overlap_job_inputs(f.store, None,
        {"requested_job": {"argv": ["ordinary"]}}, reference_access=None) == []


@pytest.mark.parametrize("fault,code", [("argv", "invalid_requested_job"),
    ("format", "input_format_binding"), ("set_order", "input_identity_mismatch")])
def test_existing_exact_requested_job_validator_is_the_first_shape_authority(f, fault, code):
    selected = assignment(f.store, f.specs)
    job = selected["requested_job"]["native_genomic_overlap"]
    if fault == "argv":
        selected["requested_job"]["argv"][-1] = "another-plan.json"
    elif fault == "format":
        job["request"]["region_sets"][0]["source"]["kind"] = "coordinate_rows_artifact"
    else:
        job["inputs"].reverse()
    with fails(code):
        validate(f, selected)


def test_programming_and_callback_errors_are_not_hidden(f, monkeypatch):
    for error in (RuntimeError("callback bug"), TypeError("callback bug"),
                  sqlite3.ProgrammingError("callback bug")):
        def bad(*args):
            raise error
        with pytest.raises(type(error), match="callback bug"):
            validate(f, access=bad)
    with fails("invalid_reference_access"):
        validate(f, access=lambda *_: "grant")
    with monkeypatch.context() as patch:
        patch.setattr(f.store, "reference_subset", lambda *_: (_ for _ in ()).throw(TypeError("scope bug")))
        with pytest.raises(TypeError, match="scope bug"):
            validate(f)


@pytest.mark.parametrize("physical_state", ["present", "missing", "changed"])
def test_host_reads_only_metadata_creates_no_state_and_leaves_physical_checks_to_driver(f, monkeypatch, physical_state):
    from gene_annotation_episode import materials, native_file_capture, genomic_overlap_inputs
    from gene_annotation_episode import native_genomic_overlap_driver, native_lifecycle, local_jobs
    import builtins
    import io
    import os
    import socket
    import subprocess

    _, selected_metadata = add_metadata(f)
    selected = assignment(f.store, f.specs)
    expected = refs(f.specs[:1]) + selected_metadata + refs(f.specs[1:])
    for path in [Path(row["path"]) for row in selected["requested_job"]["native_genomic_overlap"]["inputs"]]:
        if physical_state == "missing":
            path.unlink()
        elif physical_state == "changed":
            path.write_bytes(b"different bytes after retention")
    before = list(f.store.db.iterdump())
    changes = f.store.db.total_changes
    def forbidden(*args, **kwargs):
        raise AssertionError("authority port attempted bytes, parsing, work or receipt mutation")
    with monkeypatch.context() as patch:
        for owner, names in ((builtins, ("open",)), (io, ("open",)), (os, ("open",)),
                (Path, ("open", "read_bytes", "read_text")), (f.store, ("get_artifact", "artifact", "put")),
                (materials, ("artifact_path", "artifact_file")),
                (native_file_capture, ("retained_native_file", "capture_native_file", "capture_declared_native_files")),
                (genomic_overlap_inputs, ("parse_region_set",)),
                (native_genomic_overlap_driver, ("run_genomic_overlap_driver",)),
                (subprocess, ("Popen", "run")), (socket, ("create_connection",)),
                (native_lifecycle, ("prepare_job", "start_prepared")), (local_jobs, ("run_local_job",)),
                (EpisodeReceipts, ("__init__", "bind", "receive"))):
            for name in names:
                patch.setattr(owner, name, forbidden)
        assert validate(f, selected) == expected
        assert f.store.db.total_changes == changes
        assert list(f.store.db.iterdump()) == before


def supplied_file_spec(store, key, raw, format):
    """Retain a caller File directly, without an acquisition Source."""
    artifact = store.artifact(raw)
    return {"set_key": key, "display_label": None, "source": {
        "kind": "bed_artifact" if format == "bed_outer_span_v1" else "coordinate_rows_artifact",
        "file": file_identity(store, artifact, format)}, "format": format, "reference": None}


@pytest.mark.parametrize("formats", [
    ("bed_outer_span_v1", "bed_outer_span_v1"),
    ("coordinate_rows_v1", "coordinate_rows_v1"),
    ("bed_outer_span_v1", "coordinate_rows_v1"),
])
def test_file_only_inputs_reach_frozen_resource_child_without_source_or_mutation(f, formats):
    raw = {"bed_outer_span_v1": b"chr2\t20\t30\n",
        "coordinate_rows_v1": b'[["chr2",25,35]]'}
    before_sources = f.store.count("source")
    f.specs = [supplied_file_spec(f.store, key, raw[format], format)
        for key, format in zip(("SuppliedA", "SuppliedB"), formats)]
    selected = list(dict.fromkeys(spec["source"]["file"]["artifact_ref"] for spec in f.specs))
    f.receipts.receive(f.root.episode_id, selected, kind="own_action")
    launch = context(f, parent=f.root, role="launch", label="file-only")
    local = context(f, parent=launch, role="launch_local", label="file-only")
    original = assignment(f.store, f.specs)
    before = list(f.store.db.iterdump())
    changes = f.store.db.total_changes
    for child in (f.root, launch, local):
        assert validate(f, original, using=child) == selected
    assert assignment(f.store, f.specs) == original
    assert all("source_ref" not in spec["source"] for spec in f.specs)
    assert f.store.count("source") == before_sources
    assert f.store.db.total_changes == changes and list(f.store.db.iterdump()) == before


@pytest.mark.parametrize("fault,code", [
    ("unreceived", "input_not_received"),
    ("protected", "protected_reference_denied"),
    ("identity", "artifact_metadata_mismatch"),
    ("path", "selected_path_mismatch"),
])
def test_file_only_inputs_preserve_file_authority_and_metadata_checks(f, fault, code):
    f.specs[0] = supplied_file_spec(f.store, "Supplied", b"chr2\t0\t5\n", "bed_outer_span_v1")
    reference = f.specs[0]["source"]["file"]["artifact_ref"]
    if fault != "unreceived":
        f.receipts.receive(f.root.episode_id, [reference], kind="own_action")
    if fault == "identity":
        f.specs[0]["source"]["file"]["size_bytes"] += 1
    selected = assignment(f.store, f.specs)
    if fault == "path":
        selected["requested_job"]["native_genomic_overlap"]["inputs"][0]["path"] += ".other"
    with fails(code):
        validate(f, selected, access=lambda _ctx, ref, _ns: False
            if fault == "protected" and ref == reference else None)


@pytest.mark.parametrize("invalid", [None, "", False, 7, [], {}])
def test_optional_source_reference_cannot_be_null_empty_or_wrong_type(f, invalid):
    f.specs[0]["source"]["source_ref"] = invalid
    with pytest.raises(ValueError):
        assignment(f.store, f.specs)


def test_file_only_metadata_admission_does_not_read_changed_or_missing_bodies(f, monkeypatch):
    f.specs = [supplied_file_spec(f.store, key, raw, format) for key, raw, format in (
        ("SuppliedA", b"chr2\t20\t30\n", "bed_outer_span_v1"),
        ("SuppliedB", b'[["chr2",25,35]]', "coordinate_rows_v1"))]
    selected_refs = [spec["source"]["file"]["artifact_ref"] for spec in f.specs]
    f.receipts.receive(f.root.episode_id, selected_refs, kind="own_action")
    selected = assignment(f.store, f.specs)
    inputs = selected["requested_job"]["native_genomic_overlap"]["inputs"]
    Path(inputs[0]["path"]).unlink()
    Path(inputs[1]["path"]).write_bytes(b"changed after retention")
    before = list(f.store.db.iterdump())
    def forbidden(*args, **kwargs):
        raise AssertionError("File-only host admission read bytes or created a Source/receipt")
    for owner, names in ((Path, ("open", "read_bytes", "read_text")),
            (f.store, ("get_artifact", "artifact", "put")),
            (EpisodeReceipts, ("receive", "bind", "__init__"))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    assert validate(f, selected) == selected_refs
    assert list(f.store.db.iterdump()) == before


def test_received_nonartifact_cannot_be_used_as_a_file_identity(f):
    # A File receipt cannot turn an input record into retained artifact metadata.
    changed = deepcopy(f.specs)
    changed[0]["source"].pop("source_ref")
    changed[0]["source"]["file"]["artifact_ref"] = f.other
    f.receipts.receive(f.root.episode_id, [f.other], kind="own_action")
    with fails("artifact_metadata_mismatch"):
        validate(f, assignment(f.store, changed))


def test_later_file_only_parent_input_does_not_extend_frozen_child(f):
    child = context(f, parent=f.root, role="launch", label="before-file")
    f.specs[0] = supplied_file_spec(f.store, "LaterFile", b"chr2\t40\t50\n", "bed_outer_span_v1")
    ref = f.specs[0]["source"]["file"]["artifact_ref"]
    f.receipts.receive(f.root.episode_id, [ref], kind="own_action")
    assert ref in validate(f)
    with fails("input_not_received"):
        validate(f, using=child)
