"""Pure-worker checks using original252 captures, never fabricated native output."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.library import native_infernal_preparation_result_worker as worker
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
# NATIVE_CAPTURE_EXAMPLES_002.json records its retained files as paths relative to the axis home
# that holds this fixture packet (tests/fixtures/infernal_preparation/...).


def forbidden(*args, **kwargs):
    raise AssertionError("native execution, acquisition, parsing or calculation forbidden")


def selector(collection="output_records", quantities=("values.residue_count", "values.gc_count"), checks=(), artifacts=(), *, keys=None, offset=0, limit=1):
    return {"version": "native_infernal_preparation_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": None if collection is None else {"collection": collection,
            "rows": {"record_keys": list(keys)} if keys else {"offset": offset, "limit": limit},
            "quantities": list(quantities), "checks": list(checks)}, "artifacts": list(artifacts)}


def test_worker_plan_and_cli_are_closed(tmp_path):
    with pytest.raises(ValueError, match="result_worker_plan_invalid"):
        worker.run({"task": "grade"})
    with pytest.raises(ValueError, match="exact_result_worker_plan_required"):
        worker.main([])


