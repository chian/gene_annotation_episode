"""The evaluation harness can bind the production roles without network work."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from live_a106_workflow import execution_factory
from gene_annotation_episode import bvbrc_tnseq_bundle_adapter as tnseq
from gene_annotation_episode import bvbrc_rnaseq_bundle_adapter as rnaseq
from gene_annotation_episode.intervention_execution import analysis_children, contract_catalog
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG


def test_explicit_analysis_binding_preserves_anonymous_input_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: pytest.fail("unexpected network work"))
    monkeypatch.setenv("GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY", str(tmp_path / "local-resources"))
    resource = deepcopy(CONFIG)
    resource["scientific_adapters"] = [dict(adapter_id=module.ADAPTER_ID, adapter_version=module.ADAPTER_VERSION,
        implementation_sha256=module.implementation_sha256()) for module in (tnseq, rnaseq)]
    config = dict(resources={"analysis":resource}, initial_information={}, handoff_unit=1,
        acquired_record_unit=1, log_window_bytes=1024, log_roles=["stdout", "stderr"])
    with Store(tmp_path / "state") as store:
        tools = ToolRegistry(store)
        services = SimpleNamespace(workflow=SimpleNamespace(run_id="controlled-run"))
        factory = execution_factory(config, store=store, directory=tmp_path / "execution", tool_registry=tools)
        config["resources"].clear()
        family = factory(services)
        services.workflow.episode_bindings = SimpleNamespace(roles=family.roles, for_role=lambda _:family)
        assert analysis_children(services) == ("launch", "results")
        assert contract_catalog(services)[0]["input_schema"]["properties"]["resource_id"] == {"enum":["analysis"]}
        assert set(family.api_execution.services["analysis"].scientific_adapters) == {("bvbrc_tnseq", "1"), ("bvbrc_rnaseq", "1")}
        config["initial_information"] = {"analysis":{"expected_findings":"must not preload"}}
        with pytest.raises(ValueError, match="empty_initial_information"):
            execution_factory(config, store=store, directory=tmp_path / "execution", tool_registry=tools)
