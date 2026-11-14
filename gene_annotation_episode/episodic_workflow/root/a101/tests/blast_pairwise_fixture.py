"""Resolve immutable BLAST pairwise captures after their move into test fixtures."""

from copy import deepcopy
import json
from pathlib import Path
import shutil

from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_contracts import native_blast_digest


FIXTURES = Path(__file__).resolve().parent / "fixtures/blast_pairwise"


def fixture_path(saved_path, *, package=FIXTURES):
    """Map a path embedded in a saved plan to its byte-identical fixture."""
    original = Path(saved_path)
    marker = "tool_graders_blast_pairwise_2026-10-26_294"
    parts = original.parts
    if marker not in parts:
        return original
    return package.joinpath(*parts[parts.index(marker) + 1:])


def retained_request(plan_path):
    plan = json.loads(Path(plan_path).read_bytes())
    request = deepcopy(plan["requested_job"])
    return _map_strings(request, [(str(Path(plan["attempt_directory"]).parents[2]), str(FIXTURES))])


def _map_strings(value, replacements):
    if isinstance(value, str):
        for old, new in replacements:
            if value == old or value.startswith(old + "/"):
                return new + value[len(old):]
        return value
    if isinstance(value, list):
        return [_map_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _map_strings(item, replacements) for key, item in value.items()}
    return value


def replay_copy(plan_path, tmp_path):
    """Translate one sealed capture into a disposable replay without editing it."""
    plan_path = Path(plan_path)
    saved_plan = json.loads(plan_path.read_bytes())
    source_attempt = plan_path.parent / "attempt"
    saved_owner = json.loads((source_attempt / ".native-blast-owner.json").read_bytes())
    saved_bundle = json.loads((source_attempt / "bundle.json").read_bytes())
    assert saved_owner == saved_plan
    old_attempt = Path(saved_plan["attempt_directory"])
    old_package = old_attempt.parents[2]
    new_attempt = tmp_path / plan_path.parent.name / "attempt"
    shutil.copytree(source_attempt, new_attempt)
    forward = [(str(old_attempt), str(new_attempt)), (str(old_package), str(FIXTURES))]
    plan = _map_strings(saved_plan, forward)
    bundle = _map_strings(saved_bundle, forward)
    digest = native_blast_digest(plan["requested_job"])
    plan["identity"]["requested_job_sha256"] = digest
    bundle["identity"]["requested_job_sha256"] = digest
    (new_attempt / ".native-blast-owner.json").write_text(json.dumps(plan))
    (new_attempt / "bundle.json").write_text(json.dumps(bundle))
    return plan, bundle, saved_bundle, new_attempt


def original_bundle(replayed, *, saved_plan, new_attempt):
    """Undo only path translation and the resulting request digest."""
    old_attempt = Path(saved_plan["attempt_directory"])
    old_package = old_attempt.parents[2]
    reverse = [(str(new_attempt), str(old_attempt)), (str(FIXTURES), str(old_package))]
    restored = _map_strings(replayed, reverse)
    restored["identity"]["requested_job_sha256"] = saved_plan["identity"]["requested_job_sha256"]
    return restored
