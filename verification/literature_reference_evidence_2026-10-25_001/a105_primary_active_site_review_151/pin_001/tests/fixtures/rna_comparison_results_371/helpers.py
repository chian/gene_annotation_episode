"""Synthetic original RNA records through real action/form/custody adapters.

No RNA import or native scientific command is used. Original supplied bundles
use the retained358 fixture; comparison collection invokes the real D worker.
"""
from copy import deepcopy
import asyncio
import importlib
import os
from pathlib import Path
import json
from contextlib import nullcontext
from unittest.mock import patch

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.rna_structure_comparison_results import NativeRNAStructureComparisonResults
from gene_annotation_episode.rna_structure_comparison_returns import RNAStructureComparisonReturns
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE, rna_comparison_fact_sources
from gene_annotation_episode.rna_structure_result_views import SAVED_SOURCE, FAMILY_SOURCES
from gene_annotation_episode.runtime import TypedReportContract

F = importlib.import_module("verification.tool_graders_rna_structure_results_2026-10-26_358.fixture_helpers")
B = importlib.import_module("verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")


class Original(F.Fixture):
    def __init__(self, store, *args, original_id, **kwargs):
        self.original_id = original_id
        reuse = store.db.execute("SELECT 1 FROM problem").fetchone() is not None
        with (patch.object(type(store), "create_problem", lambda self, *a, **k: self.problem()) if reuse else nullcontext()):
            super().__init__(store, *args, **kwargs)

    def context(self, path, *args, **kwargs):
        if path == (("launch_local", "synthetic_producer"),):
            path = (("launch_local", "synthetic_producer_" + self.original_id),)
        return super().context(path, *args, **kwargs)


class Targets:
    def __init__(self):
        self.originals, self.observations = {}, []

    def read_target(self, reference, scope):
        f = self.originals[reference]
        f.store.validate_scope(f.target["scope"], parent_scope=plain(scope))
        return deepcopy(f.target)

    def observe_target(self, target, *, operation_key):
        self.observations.append(operation_key)
        f = self.originals[target["handle"]]
        return F.SyntheticTargets(f).observe_target(target, operation_key=operation_key)


def schema(source=True):
    return {"type": "object", "additionalProperties": False, "properties": {
        "comparison": deepcopy(rna_comparison_fact_sources()[PROJECTION_SOURCE]["report_schema"])
    } if source else {"completed": {"type": "boolean", "x-source": "execution_completed"}},
        "required": ["comparison"] if source else ["completed"]}


class Fixture:
    def __init__(self, store, root, *, failure=False, source_only=False):
        self.store, self.root_path = store, Path(root)
        self.targets, self.originals, self.bodies, self.descriptors = Targets(), [], [], []
        for i, sequence in enumerate(("GGGAAACCC", "GGGAAAUCC")):
            f = Original(store, self.root_path / str(i), original_id=str(i),
                request=F.CORE.feature_input(sequence=sequence, record_key="WT" if i == 0 else "V"))
            self.attach(f)
        first = self.originals[0]
        self.owner, self.root, self.scope = first.owner, first.root, first.scope
        self.run_id, self.journal, self.receipts = first.run_id, first.journal, first.receipts
        for i, f in enumerate(self.originals):
            child = f.child(index=i, sources=[F.REFERENCE_SOURCE] if source_only else [SAVED_SOURCE])
            body = f.execute(child)
            f.returned(self.root, child)
            self.bodies.append(body)
            self.descriptors.append(f.results.saved_descriptor(body))
        self.failure_row = None
        if failure:
            f = Original(store, self.root_path / "failure", original_id="failure", failure=True)
            self.attach(f)
            child = f.child(index=2, sources=[FAMILY_SOURCES["failure"]])
            if failure == "null_source":
                (f.attempt / "bundle.json").unlink()
            body = f.execute(child)
            form = f.returned(self.root, child)
            self.failure_row = form["value_0"][0]
            self.failure_body = body
        self.results = self.owner.rna_structure_comparison_results = NativeRNAStructureComparisonResults(self.owner)
        self.returns = self.owner.rna_structure_comparison_returns = RNAStructureComparisonReturns(self.owner)
        self.native_returns = self.owner.native_rna_structure_returns

    def attach(self, f):
        self.originals.append(f)
        self.targets.originals[f.handoff] = f
        f.owner.directory = self.root_path / "shared-episodes"
        f.results.directory = f.owner.directory / "native-rna-structure-result-index"
        f.owner.job_progress_provider.targets = self.targets

    def selector(self, *, structures=False, scan=False):
        members = [{"member_id": name, "kind": "saved_sheet", "saved_input": deepcopy(desc)}
            for name, desc in zip(("WT", "V"), self.descriptors)]
        if scan:
            if self.failure_row is not None:
                members.append({"member_id": "failed", "kind": "received_failure", "failure": deepcopy(self.failure_row)})
            members += [{"member_id": "not-run", "kind": "declared_absent", "state": "not_tested"},
                {"member_id": "alias-V", "kind": "alias", "canonical_member_id": "V"}]
            energy = B.energy_request()
            selected = B.selector(members, [B.comparison(m["member_id"], energy=energy)
                for m in members if m["member_id"] != "WT" and m["kind"] != "alias"], scan=B.scan_request(energy))
            selected["projections"] = [{"projection_id": "rank", "family": "scan_energy", "scan_id": "scan",
                "metrics": ["declared_variant_count", "received_failure_variant_count", "not_tested_variant_count", "baseline_rank_start"],
                "include_rank_class": True}]
        else:
            selected = B.selector(members, [B.comparison("V", correspondence={"kind": "substitution_only",
                "substitutions": [{"index": 6, "baseline_symbol": "C", "variant_symbol": "U"}]}, pairs=True)])
            selected["projections"] = ([{"projection_id": "two", "family": "structures", "member_ids": ["WT", "V"],
                "fields": ["original_sequence", "dot_bracket"]}] if structures else [{"projection_id": "counts", "family": "comparison_counts",
                "comparison_ids": ["compare-V"], "selection_ids": [], "metrics": ["preserved_pair_count", "pair_symmetric_difference_count"],
                "include_pairing_change_state": True}])
        return selected

    def child(self, selector=None, *, index=10, parent=None, role="results", returned=True, anchor=None):
        parent = parent or self.root
        selector = selector or self.selector()
        contract = TypedReportContract("Return exactly selected comparison values", schema(returned), lambda *_: True)
        assignment = {"version": "execution_results_assignment_v1", "handoff_ref": anchor or self.originals[1].handoff,
            "selector": deepcopy(selector)} if role == "results" else {}
        child = self.originals[0].context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent)
        action = {"kind": "episode_child", "role": role, "assignment": assignment, "scope": deepcopy(self.scope),
            "purpose": contract.decision, "schema_json": canonical(contract.schema)}
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical(action), "result": None, "credit": None})
        return child

    def execute(self, child, *, index=0, name="execution.results.collect", finish=True):
        key = f"{self.run_id}:{child.episode_id}:{index}"
        action = {"kind": "tool", "tool": name, "arguments": {}}
        self.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": index,
            "action": canonical(action), "result": None, "credit": None})
        outcome = asyncio.run(self.results.execute(child, self.owner._target(child), name, {}, key))
        if finish:
            outcome["pending_work_after_action"] = {"version": "pending_work_v1", "captured_at": "2026-10-26T00:00:04+00:00", "items": []}
            self.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": index,
                "action": canonical(action), "result": canonical(outcome), "credit": 0})
        return outcome["result"]

    def returned(self, parent, child):
        contract = plain(child.request)["report_contract"]
        declared = contract["measurements"]["schema"]
        facts = self.results.facts(child) if child.role == "results" else self.returns.received_facts(child, declared)
        form = form_with_facts({}, declared, facts)
        self.returns.validate_received_report(child, form, declared)
        self.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        index = int(child.path[-1][1][6:])
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "comparison-delivery-" + str(index), "child_episode_id": child.episode_id,
            "contract": canonical(contract), "form": canonical(form), "failure": None})
        refs = self.returns.record_admission(parent, form, declared, f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        assert refs == []
        self.receipts.receive(parent.episode_id, refs, kind="child_form", source_index=index)
        return form


def retain(name, **values):
    destination = os.environ.get("RNA_COMPARISON_E_EXAMPLES")
    if destination:
        path = Path(destination)
        path.mkdir(parents=True, exist_ok=True)
        (path / (name + ".json")).write_text(json.dumps(values, indent=2, sort_keys=True, allow_nan=False) + "\n")
