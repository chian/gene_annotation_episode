"""Utility publication/custody fixtures; no native command is run here.

Producer histories and binary members below are controlled engineering fixtures.
Tests named retained_native_stream authenticate the original 084/085 stream bytes
from626, then use a controlled capture to verify this reader/publication boundary.
They establish native format handling, not an authentic new producer invocation.
All imports, fixture reads and worker processing run only inside runner529.
"""
from contextlib import redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import blast_database_extraction as extraction
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import blast_database_inspection as inspection
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import blast_database_preparation as preparation
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.sequence_homology_evidence import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search import native_blast_utility_result_publication as publication
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence import native_blast_utility_result_worker as worker
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.native_blast_utility_contracts import BUNDLE_VERSION, compile_native_blast_utility_job, database_file_selections, native_environment, producer_failure, staged_relative, validate_native_blast_utility_bundle
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.native_worker_files import _encoded
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_homology_evidence.practical_execution_state import _immutable
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.tests.test_native_blast_utility_producer_628 import FAMILY, POLICY, job_fixture, plan_fixture
import gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.native_blast_utility_worker_context as _scientific_native_blast_utility_result_worker
import gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_utility_capture_contracts as _scientific_native_blast_utility_acquisition


READER_EVIDENCE = Path(__file__).resolve().parents[7] / "gene_annotation_episode/episodic_workflow/episode_support/tools/similarity_search/sequence_homology_evidence/tests/fixtures/blast_database_readers"
EXTRACT = b"0\tlcl|ALPHA\tALPHA\t8\tACGTACGT\n"


def selector(**kwargs):
    return {"version": "native_blast_utility_result_selector_v1", "sequences": None,
        "database_fields": [], "integrity": None, "preparation": None,
        "prepared_database": False, "include_checks": False, "artifacts": [], "saved_data": [], **kwargs}


def retained_stream(name):
    provenance = json.loads((READER_EVIDENCE / "FIXTURE_PROVENANCE_001.json").read_text())
    row = next(row for row in provenance["cases"] if row["name"] == name)
    data = {}
    for key in ("stdout", "stderr"):
        data[key] = (READER_EVIDENCE / "fixtures" / name / (key + ".txt")).read_bytes()
        assert hashlib.sha256(data[key]).hexdigest() == row[key]["sha256"]
        assert len(data[key]) == row[key]["size_bytes"]
    return row, data


def capture_fixture(tmp_path, mode="extract_sequences", *, job=None, stdout=None, stderr=b"", returncode=0,
                    family=None, omit=()):
    """Explicit controlled original history; no producer or native invocation."""
    job = job_fixture(tmp_path, mode) if job is None else deepcopy(job)
    plan = plan_fixture(tmp_path, job)
    root = Path(plan["attempt_directory"])
    store = Store(tmp_path / "store")
    if stdout is None:
        stdout = EXTRACT if mode == "extract_sequences" else b"controlled utility fixture\n"
    family = deepcopy(FAMILY if family is None else family)
    if mode == "create_sequence_database" and family.get("njs") == FAMILY["njs"]:
        family["njs"] = json.dumps({"version": "1.2", "dbname": "tiny", "dbtype": "Nucleotide", "db-version": 5,
            "description": job["operation"]["parameters"]["title"], "last-updated": "fixture time",
            "number-of-sequences": 1, "number-of-letters": 8,
            "bytes-total": sum(len(v) for k, v in family.items() if k != "njs"),
            "files": ["tiny." + suffix for suffix in sorted(family) if suffix != "njs"]}).encode()
    bundle = {"version": BUNDLE_VERSION, "identity": plan["identity"], "requested_job": plan["requested_job"],
        "operation": job["operation"], "software": {"executable": job["software"]["executable"],
            "expected_sha256": job["software"]["sha256"], "actual_sha256": job["software"]["sha256"],
            "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": compile_native_blast_utility_job(job,
            input_paths={r["input_key"]: str(root / staged_relative(r)) for r in job["inputs"]},
            database_paths={r["database_key"]: r["native_paths"] for r in job["databases"]}, output_directory=str(root)),
        "environment": native_environment(job, root), "started": returncode is not None, "returncode": returncode,
        "writer_closed": True, "inventory_complete": True, "started_at": "2026-10-28T00:00:00+00:00",
        "finished_at": "2026-10-28T00:00:01+00:00", "inputs": [], "database_files": [], "artifacts": [],
        "failures": ([producer_failure("command_unavailable")] if returncode is None else
                     [producer_failure("nonzero_returncode")] if returncode else [])}
    raw_by_path = {}
    for row in job["inputs"]:
        data = Path(row["path"]).read_bytes()
        bundle["inputs"].append({"input_key": row["input_key"], "role": row["role"], "format": row["format"],
            "original_path": row["path"], "relative_path": staged_relative(row), "artifact_ref": row["artifact_ref"],
            **{prefix + "sha256": row["sha256"] for prefix in ("expected_", "staged_", "final_")},
            **{prefix + "size_bytes": row["size_bytes"] for prefix in ("expected_", "staged_", "final_")}})
        raw_by_path[row["path"]] = data
    for row in database_file_selections(job):
        bundle["database_files"].append({**row, "before_sha256": row["expected_sha256"], "final_sha256": row["expected_sha256"],
            "before_size_bytes": row["expected_size_bytes"], "final_size_bytes": row["expected_size_bytes"]})
        raw_by_path[row["original_path"]] = Path(row["original_path"]).read_bytes()
    native_outputs = [(r["role"], 0, r["relative_path"], r["format"], stdout if r["role"] == "stdout" else stderr)
                      for r in job["outputs"] if r["role"] != "database_family"]
    if mode == "create_sequence_database":
        prefix = job["operation"]["parameters"]["output_prefix"]
        native_outputs += [("database_metadata" if suffix in {"njs", "pjs"} else "database_file", ordinal,
            prefix + "." + suffix, "blastdb_metadata_json" if suffix in {"njs", "pjs"} else "blastdb_binary", data)
            for ordinal, (suffix, data) in enumerate(sorted(family.items()))]
    for role, ordinal, relative, fmt, data in native_outputs:
        bundle["artifacts"].append({"role": role, "ordinal": ordinal, "relative_path": relative, "format": fmt,
            "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data),
            "completeness": "complete" if returncode == 0 else "partial"})
        raw_by_path[str(root / relative)] = data
    bundle = validate_native_blast_utility_bundle(bundle, plan)
    capture = {"version": _scientific_native_blast_utility_acquisition.VERSION, "source_ref": None, "plan": plan, "original_bundle": bundle,
        "bundle_artifact_ref": store.artifact(_encoded(bundle), "application/json"), "bundle_validated": True,
        "artifacts": [], "failures": []}
    for row in _scientific_native_blast_utility_acquisition._selected_files(plan, bundle):
        if (row["direction"], row["role"], row["ordinal"]) in omit:
            capture["failures"].append(acquisition._failure("original_file_unavailable", row))
            continue
        data = raw_by_path[row["original_path"]]
        reference = store.artifact(data, "application/octet-stream")
        capture["artifacts"].append({k: row[k] for k in _scientific_native_blast_utility_acquisition._ROW_FIELDS - {"artifact_ref"}} | {"artifact_ref": reference})
    capture["source_ref"] = store.put("source", acquisition._source_payload(capture), origin="tool")["id"]
    acquisition._validate_saved(store, capture)
    return store, capture


def prepare(store, capture, tmp_path):
    return publication.prepare_native_blast_utility_result(store, capture=capture,
        directory=tmp_path / "preparation", policy=LocalJobPolicy(**POLICY))


def publish(store, prepared, selected, tmp_path, *, name="projection"):
    return publication.publish_selected_utility_result(store, source_ref=prepared["source_ref"], prepared=prepared,
        selector=selected, directory=tmp_path / name, policy=LocalJobPolicy(**POLICY))


def payload(store, prepared):
    return json.loads(store.get_artifact(prepared["result_artifact_ref"]))


def forbid_readers(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("saved projection/replay reran a native reader or preparation calculation")
    for owner, names in ((extraction, ("parse_blastdbcmd_sequences",)),
            (inspection, ("parse_blast_database_inspection", "parse_blastdbcheck_diagnostics", "_metadata_fields")),
            (preparation, ("populate_database_artifact_set", "project_prepared_blast_database"))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)


def test_same_bytes_preserve_occurrences_and_original_ordinals(tmp_path):
    store, capture = capture_fixture(tmp_path, "create_sequence_database", stdout=b"", stderr=b"")
    context = _scientific_native_blast_utility_result_worker.qualified_utility_context(capture)
    streams = [r for r in context["occurrences"] if r["role"] in {"stdout", "stderr"}]
    assert streams[0]["artifact_ref"] == streams[1]["artifact_ref"]
    assert streams[0]["occurrence_id"] != streams[1]["occurrence_id"]
    assert [r["ordinal"] for r in context["occurrences"] if r["role"] == "database_file"] == [0, 1, 2, 3, 5]


@pytest.mark.parametrize("mutation", [lambda c: c["artifacts"][0].update(original_path="/unselected/file"),
    lambda c: c["artifacts"][0].update(ordinal=91), lambda c: c["artifacts"][0].update(size_bytes=991),
    lambda c: c["original_bundle"]["identity"].update(run_id="forged"),
    lambda c: c["artifacts"].append(deepcopy(c["artifacts"][0])),
    lambda c: c["artifacts"].pop(0)])
def test_qualified_context_rejects_wrong_original_associations(tmp_path, mutation):
    _, capture = capture_fixture(tmp_path)
    mutation(capture)
    with pytest.raises(ValueError):
        _scientific_native_blast_utility_result_worker.qualified_utility_context(capture)


def test_unfinished_preparation_intent_is_not_restarted(tmp_path, monkeypatch):
    store, capture = capture_fixture(tmp_path)
    directory = tmp_path / "preparation" / "native-blast-utility-preparation"
    directory.mkdir(parents=True)
    _immutable(directory / "intent.json", {"capture": capture, "policy": POLICY})
    monkeypatch.setattr(publication, "run_local_job", lambda *a, **k: pytest.fail("uncertain work restarted"))
    with pytest.raises(ContractError, match="original_result_work_incomplete"):
        prepare(store, capture, tmp_path)


def test_qualified_context_is_detached_and_does_not_read_files(tmp_path, monkeypatch):
    _, capture = capture_fixture(tmp_path)
    expected = _scientific_native_blast_utility_result_worker.qualified_utility_context(capture)
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("pure context read a file"))
    monkeypatch.setattr(Path, "resolve", lambda *a, **k: pytest.fail("pure context resolved a native path"))
    value = _scientific_native_blast_utility_result_worker.qualified_utility_context(capture)
    assert value == expected and value is not expected
    value["occurrences"][0]["native_path"] = "/changed"
    assert _scientific_native_blast_utility_result_worker.qualified_utility_context(capture) == expected
