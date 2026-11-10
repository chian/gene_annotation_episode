"""Host-filled report references obey the actual public-provider owner.

The HTTP entity and controller below are engineering fixtures. No model call,
network request or biological conclusion is claimed.
"""
import asyncio
import json
import urllib.request

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_alphafold_acquisition_host import _controller, _credit
from test_ensembl_acquisition_host import HTTP
from test_ncbi_entrez_acquisition import arguments
from test_ncbi_entrez_acquisition_host import SEARCH
from test_runtime import ScriptedProvider, obj
from test_scientific_process_runtime import action


def test_entrez_private_request_metadata_does_not_break_child_report_delivery(tmp_path, monkeypatch):
    http = HTTP()
    http.add(SEARCH, media_type="application/json")
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: http)
    def forbidden(*_args, **_kwargs):
        raise AssertionError("This regression uses only a controlled HTTP entity")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    with Store(tmp_path / "state") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        schema = obj({"basis": {"type": "array", "items": {
            "type": "string", "format": "reference"}, "x-source": "interpretation_basis_refs"}})
        parent = {"selection": {"kind": "child", "goal": "Acquire the selected study metadata.",
            "scope": scope, "purpose": "Receive the child's scientific evidence references.",
            "schema_json": json.dumps(schema), "initial_report_json": "{}"}, "report_update": {}}
        actor = ScriptedProvider([parent,
            action("public.ncbi.entrez", arguments(term="GSE1000[ACCN]", max_bytes=4096)),
            action("sequence.inspect", {"subject_ref": scope["subject_refs"][0]})])
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        workflow = Workflow(store, tools, actor, tmp_path / "workflow", "report-basis-custody",
            _controller, _credit, project_child_credit=_credit,
            episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build("annotation", "root", "Investigate the supplied protein.", scope)
        asyncio.run(root.run_async(workflow.context))
        source = json.loads(store.db.execute("SELECT data FROM records WHERE record_type='source' "
            "AND json_extract(data,'$.provider')='public.ncbi.entrez'").fetchone()[0])
        private, data = source["request_ref"], source["artifact_ref"]
        # This is the triggering case: the metadata identifier was visible to
        # the host, but the retained-publication owner prohibits its export.
        assert private in actor.contexts[2]["visible_record_refs"]
        assert store.get(private)["record_type"] == "artifact"
        attempt, = store.db.execute("SELECT form,failure FROM runtime_report_attempts")
        assert attempt["failure"] is None
        delivered = json.loads(attempt["form"])
        assert {source["id"], data} <= set(delivered["basis"])
        assert private not in delivered["basis"]
        resolve = workflow.resolver(scope, source=root.source)
        assert resolve(source["id"]) and resolve(data) and not resolve(private)
        assert len(http.requests) == 1
        saved = store.db.execute("SELECT facts FROM runtime_forms WHERE episode_id != ?",
            (root.source.episode_id,)).fetchone()[0]
        assert json.loads(saved)["interpretation_basis_refs"] == delivered["basis"]
