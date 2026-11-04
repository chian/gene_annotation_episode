"""324: unavailable addresses and stable native-result diagnostics."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode import native_blast_database_result_worker as worker
from gene_annotation_episode import native_blast_database_result_views as views
from tests.test_native_blast_database_result_worker import request_fixture


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def test_failure_addresses_are_constrained_locations_not_existing_reference_assertions():
    source = views.native_blast_database_fact_sources()["execution_blast_database_failures"]
    schema = source["report_schema"]
    failure = dict(stage="projection", code="native_blast_database_selector_unavailable",
        artifact_key="never-captured", input_key=None,
        search_key=dict(artifact_key="never-captured", member_ordinal=None,
                        report_index=99, search_pointer="/results/search~1missing"),
        record_key="requested-but-absent", pointer="/projections/0/rows/record_keys/0",
        detail_code="explicit_row_missing")
    worker._shape([failure], schema)
    assert not any("format" in node or "x-reference-namespace" in node for node in walk(schema))
    successful = views.native_blast_database_fact_sources()["execution_blast_database_hsp_rows"]["report_schema"]
    assert any(node.get("x-reference-namespace") == "native_blast_database_row" for node in walk(successful))
    for field, invalid in (("record_key", "bad\nprose"), ("artifact_key", ""), ("record_key", "x" * 513)):
        wrong = deepcopy(failure)
        wrong[field] = invalid
        with pytest.raises(ValueError):
            worker._shape([wrong], schema)
    for field, invalid in (("report_index", -1), ("report_index", True), ("search_pointer", "/bad~escape")):
        wrong = deepcopy(failure)
        wrong["search_key"][field] = invalid
        with pytest.raises(ValueError):
            worker._shape([wrong], schema)


def test_actual_worker_missing_artifact_diagnostics_are_hash_seed_independent(tmp_path):
    request = request_fixture(tmp_path)
    omitted = [r["artifact_key"] for r in request["bundle"]["artifacts"] if r["role"] in {"stdout", "stderr"}]
    assert len(omitted) == 2
    request["artifacts"] = [r for r in request["artifacts"] if r["artifact_key"] not in omitted]
    request["calculation_id"] = worker.native_blast_database_calculation_identity(
        input_identity=worker.native_blast_database_input_identity(request),
        input_implementation_sha256=request["implementation"]["manifest_sha256"],
        sequence_model=request["sequence_model"],
        implementation_manifest_sha256=request["implementation"]["manifest_sha256"])["calculation_id"]
    outputs = []
    for seed in ("1", "2", "91"):
        current = deepcopy(request)
        directory = tmp_path / ("generation-seed-" + seed)
        current["output_directory"] = str(directory)
        path = tmp_path / ("request-seed-" + seed + ".json")
        path.write_bytes(worker._json_bytes(current))
        result = subprocess.run([sys.executable, "-B", "-m",
            "gene_annotation_episode.native_blast_database_result_worker", str(path)], cwd=tmp_path,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]),
                PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED=seed), capture_output=True, check=False)
        assert result.returncode == 0, result.stderr.decode()
        manifest = json.loads((directory / "worker-manifest.json").read_bytes())
        assert manifest["status"] == "partial" and manifest["counts"]["numerical_rows"] > 0
        missing = [r["artifact_key"] for r in manifest["failures"]
                   if r["code"] == "native_blast_database_artifact_missing"]
        assert missing == omitted
        outputs.append(((directory / "diagnostics.json").read_bytes(), (directory / "rows.ndjson").read_bytes()))
    assert outputs[0] == outputs[1] == outputs[2]
