"""Saved official Rfam query on original reads; scripted interpretation only.

Transport serves the retained provider response. No network/model requests or
unknown-target biological performance are established by these boundary checks.
"""
import asyncio
import json

import pytest

from gene_annotation_episode.credit import CreditPolicy, project_credit
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_rfam_discovery import Client, NATIVE, QUERY
from test_runtime import FixtureController, ScriptedProvider


@pytest.mark.parametrize("operand_kind", ["original_read", "mapped_rna_view"])
def test_saved_profile_search_keeps_original_member_and_scoped_credit_operands(tmp_path, operand_kind):
    path = tmp_path / "official_example_reads.fastq"
    path.write_text("".join(f"@same {name}\n{QUERY}\n+\n{'I' * len(QUERY)}\n"
                            for name in ("first", "second")))
    with Store(tmp_path / "store") as store:
        problem = store.create_problem(path, molecule="dna")
        library, = store.targets()
        client = Client()
        tools = ToolRegistry(store, clients=client, provider_poll_interval_seconds=0)
        inventory = tools.execute("library.members", {"library_ref": library["id"]})
        a, b = inventory["result"]["members"]
        selected = tools.execute("library.select", {"library_ref": library["id"],
            "member_refs": [a["member_ref"]]})
        scope = selected["result"]["scope"]
        operand = a["id"]
        if operand_kind == "mapped_rna_view":
            viewed = tools.execute("sequence.view", {"subject_ref": operand, "molecule": "rna"}, scope=scope)
            assert viewed["status"] == "completed", viewed
            operand = viewed["result"]["records"][0]["product_ref"]
        response = tools.execute("public.rfam.search", {"subject_ref": operand},
                                 scope=scope, operation_key="official-example-on-read")
        assert response["status"] == "completed", response
        hit, = response["result"]["records"]
        observation = store.get(hit["observation_ref"])
        assert observation["subject_refs"] == [operand]
        assert observation["operand_intervals"] == [{"role": "query", "subject_ref": operand,
            "start": 0, "end": 119, "unit": "nt", "model_unit": "nt"}]
        expected_span = {"target_ref": library["id"], "member_ref": a["member_ref"],
                         "start": 0, "end": 119, "unit": "nt"}
        assert store.map_segments(operand, [{"start": 0, "end": 119}]) == [expected_span]
        family = store.get(hit["family_ref"])
        assert family["reference_type"] == "family"
        assert family["length"] is None and family["sequence_ref"] is None
        assert store.coverage(family["id"]) == []
        source = store.get(response["result"]["source_ref"])
        assert store.get_artifact(source["artifact_ref"]) == NATIVE
        assert client.sequences == [QUERY] and client.submissions == client.gets == 1
        assert not store.current_annotations() and project_credit(store).credit == 0

        # This explicit scripted interpretation is separate from native output.
        hypothesis = store.put("hypothesis", {"subject_refs": [a["id"]],
            "predicate": "functional_family", "value": {"type": "reference", "ref": family["id"]},
            "context_refs": []}, origin="reasoning", scope=scope)
        assessment = store.put("assessment", {"hypothesis_ref": hypothesis["id"],
            "observation_ref": observation["id"], "relation": "strengthens", "applicability": "direct",
            "extent_basis": "observed_extent", "condition_refs": [], "assumption_refs": [],
            "expected_revision": 0}, origin="reasoning", scope=scope)
        annotation = store.put("annotation", {"subject_ref": a["id"], "footprint_kind": "localized",
            "coherent_sets": [{"interpretations": [{"hypothesis_ref": hypothesis["id"],
                "disposition": "supported", "assessment_refs": [assessment["id"]]}], "context_refs": []}],
            "alternative_refs": [], "resolution": "selected", "expected_revision": 0}, origin="reasoning", scope=scope)
        policy = CreditPolicy(scale=217.)
        whole = project_credit(store, policy=policy, details_limit=10)
        local = project_credit(store, scope, policy=policy, details_limit=10)
        assert local.credit > 0 and local.credit == pytest.approx(2 * whole.credit)
        row, = local.source_contributions
        assert row["member_ref"] == a["member_ref"] and row["annotation_ref"] == annotation["id"]
        assert row["native_operand_interval"]["subject_ref"] == operand
        assert row["contributing_segments"] == [expected_span]

        # The ordinary runtime details reader preserves that same caller policy.
        provider = ScriptedProvider([{"selection": {"kind": "tool", "tool": "episode.credit",
            "arguments": {"limit": 1, "offset": 0}}, "report_update": {}}])
        summary = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / "run",
            credit_policy=policy.as_record(), controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert summary["completed_actions"] == 1 and summary["credit"] == whole.credit
        action = store.db.execute("SELECT result FROM runtime_actions").fetchone()
        page = json.loads(action["result"])["result"]
        assert page["policy"] == policy.as_record()
        assert page["source_contributions"][0]["member_ref"] == a["member_ref"]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1

        rejected = tools.execute("public.rfam.search", {"subject_ref": b["id"]}, scope=scope)
        assert rejected["status"] == "invalid" and client.submissions == 1
        assert store.problem() == problem and store.targets() == [library]
