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
    assert (phmmer["query_length"], phmmer["reference_length"]) == (8, 12)
    assert hmmscan["query_interval"] == [3, 9] and hmmscan["reference_interval"] == [1, 7]
    assert (hmmscan["query_length"], hmmscan["reference_length"]) == (12, 8)
    for domain in (phmmer, hmmscan):
        assert not {"query_coverage", "reference_coverage"} & domain.keys()


def test_uniprot_next_page_comes_from_actual_response_header():
    s = replace(snapshot({"results": []}, {"query": "x", "size": 2}), service="uniprot",
        url="https://rest.uniprot.org/uniprotkb/search", transport={"response": {"headers": {
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














def test_concurrent_import_partial_result_never_retains_other_operations_records(tmp_path):
    import time
    class TwoImports:
        def uniprot_record(self, accession):
            if accession == "bad":
                time.sleep(.05)
                body = {}
            else:
                body = {"primaryAccession": accession, "sequence": {"value": "MACDEFGH"}}
            return replace(snapshot(body, {"accession": accession}), service="uniprot",
                url="https://rest.uniprot.org/uniprotkb/"+accession,
                transport={"response": {"status": 200, "headers": {}},
                           "representation": "synthetic_native_protocol_fixture"})
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
