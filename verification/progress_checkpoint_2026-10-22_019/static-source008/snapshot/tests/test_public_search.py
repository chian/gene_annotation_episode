"""Native protocol fixtures, explicitly not model annotation demonstrations."""
import asyncio
import json
from dataclasses import replace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot, parse_hmmer, uniprot_pagination
from gene_annotation_episode.provider_jobs import RemoteSearches, HMMER_IDENTITY_VERSION
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


JOB = "81bddc6e-f6ef-4f16-a8c1-32d262016ccb"


def snapshot(body, request=None):
    return SourceSnapshot("ebi_hmmer", "https://www.ebi.ac.uk/Tools/hmmer/api/v1/result/"+JOB,
        request or {}, "2026-10-19T23:57:06+00:00", json.dumps(body).encode(), "application/json",
        {"representation": "synthetic_native_protocol_fixture"})


def result(algorithm="phmmer"):
    # The model and sequence axes differ deliberately, so a swap cannot pass.
    alignment = {"hmmfrom": 2, "hmmto": 7, "m": 8, "sqfrom": 4, "sqto": 9, "l": 12,
                 "identity": [.5, 3]}
    return {"status": "SUCCESS", "page_count": 2, "result": {
        "stats": {"algo": algorithm, "database": "swissprot", "nhits": 2},
        "hits": [{"index": 0, "name": "internal_native_123", "acc": None, "score": 24., "evalue": .001,
            "metadata": {"accession": "P00001", "uniprot_accession": "P00001", "description": "Reference source label",
                         "taxonomy_id": 2157, "species": "Archaea", "lineage": [2157]},
            "domains": [{"bitscore": 23., "ievalue": .002, "cevalue": .0001, "alignment_display": alignment}]}]}}


def test_hmmer_query_axis_depends_on_algorithm():
    phmmer = parse_hmmer(json.dumps(result()).encode(), algorithm="phmmer")["hits"][0]["domains"][0]
    hmmscan = parse_hmmer(json.dumps(result("hmmscan")).encode(), algorithm="hmmscan")["hits"][0]["domains"][0]
    assert phmmer["query_interval"] == [1, 7] and phmmer["reference_interval"] == [3, 9]
    assert phmmer["query_coverage"] == .75 and phmmer["reference_coverage"] == .5
    assert hmmscan["query_interval"] == [3, 9] and hmmscan["query_coverage"] == .5
    assert hmmscan["reference_interval"] == [1, 7] and hmmscan["reference_coverage"] == .75


def test_uniprot_next_page_comes_from_actual_response_header():
    s = replace(snapshot({}), transport={"response": {"headers": {
        "link": '<https://rest.uniprot.org/uniprotkb/search?query=x&cursor=actual-token&size=2>; rel="next"',
        "x-total-results": "21", "x-uniprot-release": "2026_03"}}})
    assert uniprot_pagination(s)["next_cursor"] == "actual-token"
    assert uniprot_pagination(s)["total_results"] == 21
    malicious = replace(s, transport={"response": {"headers": {"link": '<https://elsewhere.test/?cursor=fake>; rel="next"'}}})
    assert uniprot_pagination(malicious)["next_cursor"] is None
    assert uniprot_pagination(snapshot({}))["pagination_metadata_available"] is False


class Client:
    def __init__(self):
        self.submissions = 0
        self.status_calls = 0

    def hmmer_submit(self, query_fasta, **kwargs):
        self.submissions += 1
        return snapshot({"id": JOB})

    def hmmer_status(self, job_id):
        assert job_id == JOB
        self.status_calls += 1
        return snapshot({"task": {"status": "SUCCESS"},
                         "database": {"id": "swissprot", "version": "fixture-release"}, "algo": "phmmer"})

    def hmmer_result(self, job_id, **kwargs):
        assert job_id == JOB
        return snapshot(result())


def test_whole_search_is_one_operation_with_source_bound_typed_comparisons(tmp_path):
    client = Client()
    with Store(tmp_path) as store:
        p = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        tools = ToolRegistry(store, clients=client, provider_poll_interval_seconds=0)
        args = {"subject_ref": p["subject_refs"][0], "algorithm": "phmmer", "database": "swissprot", "page_size": 1}
        response = tools.execute("public.hmmer.search", args, operation_key="same-search")
        assert response["status"] == "completed", response
        assert response["result"]["next_page"] == 2
        assert response["result"]["database"]["version"] == "fixture-release"
        observation = store.get(response["result"]["records"][0]["domain_observation_refs"][0])
        assert observation["kind"] == "comparison" and observation["subject_refs"] == p["subject_refs"]
        assert observation["source_subject_refs"] != p["subject_refs"]
        assert store.get(observation["source_ref"])["version"] == "fixture-release"
        assert not store.current_annotations()
        assert tools.execute("public.hmmer.search", args, operation_key="same-search") == response
        assert client.submissions == 1 and client.status_calls == 1
        assert store.db.execute("SELECT COUNT(*) FROM tool_operations").fetchone()[0] == 1


def test_accepted_search_resumes_after_cancellation_without_resubmission(tmp_path):
    class Pending(Client):
        def hmmer_status(self, job_id):
            self.status_calls += 1
            return snapshot({"task": {"status": "STARTED"}})
    async def cancel_after_acceptance():
        with Store(tmp_path) as store:
            store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
            client = Pending()
            jobs = RemoteSearches(store, client, poll_interval_seconds=5)
            request = {"subject_ref": store.targets()[0]["id"], "query_fasta": ">q\nMACDEFGH", "algorithm": "phmmer", "database": "swissprot"}
            task = asyncio.create_task(jobs.search("search", **request))
            while not jobs.jobs() or jobs.jobs()[0]["state"] not in {"accepted", "STARTED"}:
                await asyncio.sleep(.005)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert jobs.jobs()[0]["remote_id"] == JOB
        with Store(tmp_path) as store:
            resumed = Client()
            jobs = RemoteSearches(store, resumed, poll_interval_seconds=0)
            response = await jobs.search("search", **request)
            assert json.loads(response.content)["status"] == "SUCCESS"
            assert resumed.submissions == 0
    asyncio.run(cancel_after_acceptance())


def test_uncertain_submission_is_never_silently_repeated(tmp_path):
    class Uncertain(Client):
        def hmmer_submit(self, *args, **kwargs):
            self.submissions += 1
            raise TimeoutError("POST may have reached remote service")
    async def check():
        with Store(tmp_path) as store:
            store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
            client = Uncertain()
            jobs = RemoteSearches(store, client)
            request = {"subject_ref": store.targets()[0]["id"], "query_fasta": ">q\nMACDEFGH", "algorithm": "phmmer", "database": "swissprot"}
            for _ in range(2):
                with pytest.raises(AcquisitionError, match="remote_submission_uncertain"):
                    await jobs.search("same-intent", **request)
            assert client.submissions == 1
            assert jobs.jobs()[0]["state"] == "submission_uncertain"
    asyncio.run(check())


@pytest.mark.parametrize("state,code", [("PENDING", "remote_result_not_ready"), ("FAILURE", "remote_search_failed")])
def test_unready_page_is_feedback_without_an_acquired_scientific_result(tmp_path, state, code):
    client = Client()
    with Store(tmp_path) as store:
        p = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        tools = ToolRegistry(store, clients=client)
        response = tools.execute("public.hmmer.search", {"subject_ref": p["subject_refs"][0],
            "algorithm": "phmmer", "database": "swissprot"}, operation_key="first")
        before = store.count("source"), store.count("observation")
        client.hmmer_result = lambda *args, **kwargs: snapshot({"status": state, "result": None})
        page = tools.execute("public.hmmer.page", {"job_ref": response["result"]["job_ref"], "page": 2})
        assert page["status"] == "failed" and page["feedback"]["code"] == code
        assert page["feedback"]["diagnostic_ref"] and not page["record_refs"]
        assert before == (store.count("source"), store.count("observation"))


@pytest.mark.parametrize("field,wrong", [("id", "00000000-0000-4000-8000-000000000000"),
    ("algo", "hmmscan"), ("database", {"id": "pdb"}), ("input", ">q\nYYYYYYYY")])
def test_present_contradictory_native_identity_cannot_be_attributed_to_query(tmp_path, field, wrong):
    client = Client()
    original = client.hmmer_status
    def contradictory(job_id):
        s = original(job_id)
        data = json.loads(s.content)
        data[field] = wrong
        return snapshot(data)
    client.hmmer_status = contradictory
    with Store(tmp_path) as store:
        p = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        tools = ToolRegistry(store, clients=client)
        r = tools.execute("public.hmmer.search", {"subject_ref": p["subject_refs"][0],
            "algorithm": "phmmer", "database": "swissprot"})
        assert r["status"] == "failed" and r["feedback"]["code"] == "remote_identity_conflict_"+field
        assert r["feedback"]["diagnostic_ref"] and r["feedback"]["job_ref"]
        assert not store.count("observation") and not store.current_annotations()


def test_later_successful_page_updates_pending_job_without_becoming_page_one_cache(tmp_path):
    async def check():
        with Store(tmp_path) as store:
            store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
            jobs = RemoteSearches(store, Client())
            request = {"subject_ref": store.targets()[0]["id"], "algorithm": "phmmer", "database": "swissprot", "page_size": 3, "identity_version": HMMER_IDENTITY_VERSION}
            with store.transaction():
                store.db.execute("INSERT INTO provider_jobs VALUES(?,?,?,?,?,?,?,?,?)",
                    ("test-job", "test-key", json.dumps(request), "STARTED", JOB, None, None, None, None))
            response = await jobs.page("test-job", page=2, page_size=3)
            assert response.request["page"] == 2
            assert jobs.describe("test-job")["state"] == "returned"
            assert not jobs.jobs()
            assert jobs._get("test-job")["result"] is None
    asyncio.run(check())


def test_concurrent_import_partial_result_never_retains_other_operations_records(tmp_path):
    import time
    class TwoImports:
        def uniprot_record(self, accession):
            if accession == "bad":
                time.sleep(.05)
                return snapshot({})
            return snapshot({"primaryAccession": "P00001", "sequence": {"value": "MACDEFGH"}})
    async def check():
        with Store(tmp_path) as store:
            store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
            tools = ToolRegistry(store, clients=TwoImports())
            good, partial = await asyncio.gather(
                tools.execute_async("public.uniprot.record", {"accession": "good"}),
                tools.execute_async("public.uniprot.record", {"accession": "bad"}))
            assert good["status"] == "completed" and partial["status"] == "partial"
            assert set(good["record_refs"]).isdisjoint(partial["record_refs"])
            assert len(partial["record_refs"]) == 1
            assert store.get(partial["record_refs"][0])["record_type"] == "source"
    asyncio.run(check())
