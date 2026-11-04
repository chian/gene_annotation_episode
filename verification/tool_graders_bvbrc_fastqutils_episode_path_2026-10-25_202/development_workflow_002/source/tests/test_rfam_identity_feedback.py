"""Actual saved incomplete HTTP200 response, with labelled synthetic recovery.

No live query sequence is copied. The transport never performs a provider call;
the independent official public example query drives local accounting fixtures.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.rfam_discovery import result_body, result_url
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController

DIRECTORY = Path(__file__).resolve().parents[1] / "validation/providers"
SAVED = DIRECTORY / "rfam-empty-query-identity"
NATIVE = (SAVED / "native-response.body").read_bytes()
METADATA = (SAVED / "response-metadata.json").read_bytes()
REQUEST = (SAVED / "saved-request.json").read_bytes()
BODY, META, ORIGINAL_REQUEST = json.loads(NATIVE), json.loads(METADATA), json.loads(REQUEST)
JOB = BODY["jobId"]
QUERY = (DIRECTORY / "rfam-batch-calibration/official-api-example.seq").read_text().strip()
QUERY_SHA = hashlib.sha256(QUERY.encode("ascii")).hexdigest()


def actual_saved_snapshot():
    # Reconstruct exactly the saved native body and response metadata, not an
    # assertion that this older GET was a response to the local fixture query.
    fields = deepcopy(META)
    fields.pop("content_ref")
    return SourceSnapshot(content=NATIVE, **fields)


def synthetic_snapshot(content, *, submission=False):
    return SourceSnapshot("rfam_batch", "https://batch.rfam.org/submit-job" if submission else result_url(JOB),
        {"fixture": "synthetic_submission_or_recovery_not_observed_live"}, None,
        json.dumps(content).encode("utf-8"), "application/json",
        {"status": 200, "effective_url": "https://batch.rfam.org/submit-job" if submission else result_url(JOB),
         "representation": "labelled_synthetic_local_protocol_fixture"})


def recovery_body():
    # This complete result is constructed only for local recovery tests. It is
    # neither a later observed response for JOB nor evidence of biological absence.
    return {"jobId": JOB, "searchSequence": QUERY, "numHits": 0, "hits": {},
            "opened": "synthetic_open", "started": "synthetic_start", "closed": "synthetic_close"}


class LocalTransport:
    ncbi_email = None
    def __init__(self):
        self.submissions = self.gets = 0
    def rfam_submit(self, sequence):
        assert sequence == QUERY
        self.submissions += 1
        return synthetic_snapshot({"jobId": JOB, "resultURL": result_url(JOB)}, submission=True)
    def rfam_result(self, job_id):
        assert job_id == JOB
        self.gets += 1
        return actual_saved_snapshot() if self.gets == 1 else synthetic_snapshot(recovery_body())


def test_actual_empty_query_body_metadata_and_request_custody_match_checkpoint():
    assert len(NATIVE) == 141 and hashlib.sha256(NATIVE).hexdigest() == "6131fb56a168f7ec010cd377a9161e29d4c5cafcc9a539076bbaafab343dbacc"
    assert len(METADATA) == 972 and hashlib.sha256(METADATA).hexdigest() == "52b64a76f40c476240894bf71cdda58a02980d1a79db0a636a26c053f0801dca"
    assert hashlib.sha256(REQUEST).hexdigest() == "8fca2192b208dc8b42d2e71c0cfccaa25a1718a27f535427f1b5d9312e953099"
    assert META["content_ref"] == "artifact_" + hashlib.sha256(NATIVE).hexdigest()
    assert META["transport"]["status"] == 200 and META["transport"]["request"]["method"] == "GET"
    assert META["url"] == result_url(JOB) and BODY["searchSequence"] == ""
    assert BODY["numHits"] == 0 and BODY["hits"] == {}  # Not interpreted as a no-hit result.
    assert "sequence" not in ORIGINAL_REQUEST and "query_fasta" not in ORIGINAL_REQUEST
    with pytest.raises(ValueError, match="^rfam_result_sequence_identity_empty$"):
        result_body(NATIVE, job_id=JOB, sequence_sha256=ORIGINAL_REQUEST["sequence_sha256"])


@pytest.mark.parametrize("representation,code", [
    ("absent", "rfam_result_sequence_identity_absent"),
    (None, "rfam_result_sequence_identity_not_string"),
    (17, "rfam_result_sequence_identity_not_string"),
    ("Δ", "rfam_result_sequence_identity_not_ascii"),
    ("A" * len(QUERY), "rfam_result_sequence_identity_conflict"),
])
def test_identity_causes_distinguish_unavailable_representation_from_contradiction(representation, code):
    body = recovery_body()
    if representation == "absent":
        del body["searchSequence"]
    else:
        body["searchSequence"] = representation
    with pytest.raises(ValueError, match="^" + code + "$"):
        result_body(json.dumps(body).encode(), job_id=JOB, sequence_sha256=QUERY_SHA)


def test_correct_nonempty_identity_keeps_completed_zero_hit_representation():
    body = recovery_body()
    assert result_body(json.dumps(body).encode(), job_id=JOB, sequence_sha256=QUERY_SHA) == body


def test_empty_saved_result_retains_exact_response_and_handle_then_explicit_collect_recovers(tmp_path):
    transport = LocalTransport()
    with Store(tmp_path / "store") as store:
        problem = store.create_problem(raw_sequence=QUERY, molecule="dna")
        subject = problem["subject_refs"][0]
        tools = ToolRegistry(store, clients=transport, provider_poll_interval_seconds=0)
        source_count, credit = store.count("source"), project_credit(store).as_record()
        failed = tools.execute("public.rfam.search", {"subject_ref": subject}, operation_key="saved-empty")
        feedback = failed["feedback"]
        assert failed["status"] == "failed" and failed["record_refs"] == [] and failed["result"] is None
        assert feedback["code"] == "rfam_result_sequence_identity_empty"
        assert feedback["remote_handle_known"] and feedback["collectable"]
        assert feedback["submission_state"] == "accepted" and feedback["cause"]["http_status"] == 200
        assert feedback["cause"]["phase"] == "result" and feedback["cause"]["client_phase"] == "result_response"
        assert feedback["diagnostic_ref"] == "artifact_" + hashlib.sha256(METADATA).hexdigest()
        assert store.get_artifact(feedback["diagnostic_ref"]) == METADATA
        assert store.get_artifact(META["content_ref"]) == NATIVE
        job = tools.remote_searches._get(feedback["job_ref"])
        assert job["remote_id"] == JOB and job["result"] is None and job["state"] == "accepted"
        assert job["latest_status"].encode() == METADATA
        assert store.count("source") == source_count and not store.count("observation")
        assert not store.current_annotations() and project_credit(store).as_record() == credit
        assert transport.submissions == transport.gets == 1  # No inferred pending/poll/retry.
        assert tools.execute("public.rfam.search", {"subject_ref": subject}, operation_key="saved-empty") == failed
        assert transport.gets == 1
        recovered = tools.execute("public.rfam.collect", {"job_ref": feedback["job_ref"]}, operation_key="explicit-collect")
        assert recovered["status"] == "completed" and recovered["result"]["records"] == []
        assert recovered["result"]["searched_scope"] == {"subject_ref": subject, "start": 0, "end": len(QUERY), "unit": "nt"}
        assert transport.submissions == 1 and transport.gets == 2
        assert tools.remote_searches.describe(feedback["job_ref"])["cause"] is None
        assert tools.remote_searches._get(feedback["job_ref"])["state"] == "returned"
        assert store.get_artifact(META["content_ref"]) == NATIVE  # Later success does not rewrite failure bytes.
        assert tools.execute("public.rfam.search", {"subject_ref": subject}, operation_key="saved-empty") == failed
        assert store.problem() == problem and not store.count("observation") and project_credit(store).credit == 0


def test_runtime_receives_precise_feedback_and_failed_attempt_has_no_yield_observation(tmp_path):
    transport = LocalTransport()
    with Store(tmp_path / "store") as store:
        problem = store.create_problem(raw_sequence=QUERY, molecule="dna")
        tools = ToolRegistry(store, clients=transport, provider_poll_interval_seconds=0)
        class ScriptedOwner:
            """Local scripted decisions, with no model connection or provider steering."""
            def __init__(self): self.contexts = []
            async def complete(self, episode_id, tier, instructions, context, schema):
                self.contexts.append(context)
                if len(self.contexts) == 1:
                    selection = {"kind": "tool", "tool": "public.rfam.search",
                                 "arguments": {"subject_ref": problem["subject_refs"][0]}}
                else:
                    assert len(self.contexts) == 2
                    feedback = context["feedback"]
                    assert feedback["code"] == "rfam_result_sequence_identity_empty"
                    assert feedback["remote_handle_known"] and feedback["collectable"]
                    assert context["last_local_outcome"]["status"] == "failed" and context["current_credit"] == 0
                    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
                    first = store.db.execute("SELECT credit FROM runtime_actions").fetchone()
                    assert first["credit"] is None and not store.count("observation")
                    assert transport.submissions == transport.gets == 1
                    selection = {"kind": "tool", "tool": "public.rfam.collect", "arguments": {"job_ref": feedback["job_ref"]}}
                return {"selection": selection, "report_update": {}}
        owner = ScriptedOwner()
        summary = asyncio.run(run_workflow(store, tools, provider=owner, run_dir=tmp_path / "scripted-run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert len(owner.contexts) == 2 and summary["completed_actions"] == 1 and summary["credit"] == 0
        actions = [dict(row) for row in store.db.execute("SELECT result,credit FROM runtime_actions ORDER BY decision_index")]
        assert [json.loads(row["result"])["status"] for row in actions] == ["failed", "completed"]
        assert [row["credit"] for row in actions] == [None, 0]
        observations = [json.loads(row[0]) for row in store.db.execute("SELECT observation FROM runtime_observations")]
        assert len(observations) == 1 and observations[0]["label"] == "tool:1"
        assert transport.submissions == 1 and transport.gets == 2
        assert not store.count("observation") and not store.current_annotations() and store.problem() == problem
