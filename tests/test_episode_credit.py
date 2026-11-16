"""Scoped native credit reads and caller binding fidelity; no model/network use."""
import asyncio


from gene_annotation_episode.episodic_workflow.root.run_execution import run_workflow
from test_runtime import (FixtureController, FixtureStore, FixtureTools,
                          ScriptedProvider, fixture_credit, reason)


def test_custom_projector_without_details_is_not_replaced_with_default_policy(tmp_path):
    store = FixtureStore(tmp_path / "fixture.sqlite3")
    provider = ScriptedProvider([reason(7)])
    summary = asyncio.run(run_workflow(store, FixtureTools(store), provider=provider,
        project_credit=fixture_credit, run_dir=tmp_path / "run",
        controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
    assert summary["credit"] == 7
    assert "episode.credit" not in {item["name"] for item in provider.contexts[0]["tools"]}


