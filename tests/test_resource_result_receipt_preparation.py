"""Original selectable operands versus explicitly host-added preparation.

Handoffs are synthetic schema fixtures. These tests grant no execution or
registry authority; they check the pure comparison used after authentication.
"""
from copy import deepcopy
from types import MappingProxyType, SimpleNamespace

import pytest

from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.homology_jobs import VERSION
from gene_annotation_episode.resource_records import RESULTS_VERSION
from gene_annotation_episode.state import Store


@pytest.mark.parametrize('external_query',[False,True])
def test_results_receipt_accepts_preparation_and_rejects_identity_or_selector_changes(tmp_path,external_query):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"]
        def reference(accession):
            return store.put('reference',{'reference_type':'protein','source_ref':store.get(target)['source_ref'],
                'accession':accession,'label':'Engineering query operand','sequence_ref':store.artifact('MDEAKG','text/plain'),
                'molecule':'protein','length':6,'term_refs':[],'context_refs':[]},origin='external')['id']
        query=reference('received-query') if external_query else target
        job, registry = "homology_job_" + "a"*24, "execution_registry_" + "b"*24
        native = {"job_ref": job, "registry_ref": registry, "backend": VERSION,
            "status_interface": "homology.status.v1", "progress_interface": "homology.progress.v1",
            "results_interface": "homology.results.v1"}
        handoff = {"version": "execution_handoff_v1", "execution_handle": job,
            "resource_selection": {"resource_id": "selected", "kind": "local",
                "capability_binding_ref": registry, "allocation": {'cpu': 1, 'memory_bytes': 1024 ** 3, 'scratch_bytes': 1024 ** 2}},
            "submitted_input_versions": [],
            "monitoring": {"provider_id": "selected", "target_handle": job, "contract_ref": "homology.status.v1"},
            "results": {"provider_id": "selected", "target_handle": job, "contract_ref": "homology.results.v1"},
            "checked_at": "2026-10-31T00:00:00+00:00", "check_record_refs": ["handoff_receipt_" + "c"*24],
            "state": "usable", "failure": None}
        selected = {"version": RESULTS_VERSION, "handoff": handoff, "requested_data_selector": {"offset": 0, "limit": 2}}
        prepared = {**deepcopy(selected), "adapter_assignment": {
            "job_ref": job, "query_ref": query, "cpu": 1, "handoff": native}}
        child = SimpleNamespace(assignment=MappingProxyType(prepared),episode_id='fixture-results',
            scope=MappingProxyType({"subject_refs": (target,)}))
        receipts=EpisodeReceipts(store,'fixture')
        receipts.bind(child.episode_id)
        receipts.receive(child.episode_id,[query],kind='initial')
        reader = EpisodeReturnRecords(store, "fixture", failure_prefix="test_")
        reader._results_assignment(selected, SimpleNamespace(assignment=selected))
        reader._results_assignment(selected, child)
        changed = deepcopy(selected)
        changed["requested_data_selector"]["offset"] = 1
        with pytest.raises(ValueError, match="commission_assignment_conflict"):
            reader._results_assignment(changed, child)
        for field, replacement in (("job_ref", "homology_job_" + "d"*24), ("cpu", 2),
                ("query_ref", "input_" + "e"*24), ("handoff", {**native, "registry_ref": "execution_registry_" + "f"*24})):
            altered = deepcopy(prepared)
            altered["adapter_assignment"][field] = replacement
            with pytest.raises(ValueError, match="commission_assignment_conflict"):
                reader._results_assignment(selected, SimpleNamespace(assignment=altered, scope=child.scope,
                    episode_id=child.episode_id))
        unrelated = store.put("reference", {"reference_type": "protein", "source_ref": store.get(target)["source_ref"],
            "accession": "source-only", "label": "Source-only protein", "sequence_ref": None,
            "molecule": "protein", "length": None, "term_refs": [], "context_refs": []}, origin="external")["id"]
        altered = deepcopy(prepared)
        altered["adapter_assignment"]["query_ref"] = unrelated
        with pytest.raises(ValueError, match="commission_assignment_conflict"):
            reader._results_assignment(selected, SimpleNamespace(assignment=altered, scope=child.scope,
                episode_id=child.episode_id))
        unreceived=reference('unreceived-query')
        altered=deepcopy(prepared)
        altered['adapter_assignment']['query_ref']=unreceived
        with pytest.raises(ValueError,match='commission_assignment_conflict'):
            reader._results_assignment(selected,SimpleNamespace(assignment=altered,scope=child.scope,
                episode_id=child.episode_id))
        receipts.receive(child.episode_id,[unreceived],kind='own_action',source_index=0)
        with pytest.raises(ValueError,match='commission_assignment_conflict'):
            reader._results_assignment(selected,SimpleNamespace(assignment=altered,scope=child.scope,
                episode_id=child.episode_id))
        assert store.problem()['subject_refs']==[target]
        # The exception is restricted to the known resource-results preparation;
        # direct execution results keep their original exact assignment check.
        direct = {"version": "execution_results_assignment_v1", "handoff_ref": "source_" + "a"*24,
            "selector": {"page": 1}}
        reader._results_assignment(direct, SimpleNamespace(assignment=direct))
        with pytest.raises(ValueError, match="commission_assignment_conflict"):
            reader._results_assignment(direct, SimpleNamespace(assignment={**direct, "adapter_assignment": {}}))
