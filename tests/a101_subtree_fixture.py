"""Invented proteins and source experiments through the real shared subtree.

Only decisions and continuation horizons are fixtures. phmmer execution,
acquisition, selected-site reads, source extraction, findings, forms, receipts,
archives and recovery use application code. No biological validation is claimed.
"""
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
from random import Random

from gene_annotation_episode.a101_investigation import A101Subtree, initial_report, resolve_report
from gene_annotation_episode.alignment_site_returns import alignment_site_fact_sources
from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs, FileAsset, digest
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.resource_episodes import ResourceEpisodes, LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
PROGRAM = ROOT / "resources/software/infernal-1.1.5/hmmer/src/phmmer"
ARTICLE = Path(__file__).with_name("fixtures") / "a101/characterization.txt"
ROLES = ("scientific_process", "literature", "launch", "monitor", "results")
POLICY = LocalJobPolicy(1024**3, 64*1024**2)


def action(name, arguments=None, report=None):
    return {"selection": {"kind": "tool", "tool": name, "arguments": arguments or {}},
        "report_update": report or {}}


def reasoning(store, **rows):
    commit = {key: [] for key in store.reasoning_schema()["required"]}
    commit.update(rows)
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}


def refs_form():
    return obj({"records": {"type": "array", "items": {"type": "string", "format": "reference"},
        "x-source": "committed_record_refs"}})


def child(role, assignment, scope, schema, goal):
    return {"selection": {"kind": "episode_child", "role": role, "assignment": assignment,
        "scope": scope, "goal": goal, "purpose": goal,
        "schema_json": json.dumps(schema), "initial_report_json": "{}"}, "report_update": {}}


class InterruptedAfterSubmission(Exception):
    pass


class Scenario:
    def __init__(self, path, store, *, fragment=False, partial=False):
        self.path, self.store, self.fragment, self.partial = path, store, fragment, partial
        generator = Random(101)
        residues = list("M" + "".join(generator.choices("ACDEFGHIKLMNPQRSTVWY", k=159)))
        residues[60] = "Q"
        self.sequence = "".join(residues)
        reference_a = residues.copy()
        reference_a[60] = "H"
        reference_b = residues.copy()
        for position in range(5, 155, 10):
            reference_b[position] = "A" if reference_b[position] != "A" else "G"
        database = path / "references.faa"
        database.write_text(">RefA\n" + "".join(reference_a) + "\n>RefB\n" + "".join(reference_b) + "\n")
        self.target, = store.create_problem(raw_sequence=self.sequence[:50] if fragment else self.sequence,
            molecule="protein")["subject_refs"]
        self.scope = {"subject_refs": [self.target]}
        data = ARTICLE.read_bytes()
        artifact = store.artifact(data, "text/plain")
        self.source = store.put("source", {"provider": "synthetic_a101_fixture",
            "accession": "characterization", "uri": None, "artifact_ref": artifact,
            "text_ref": artifact, "request_ref": None, "version": "1", "retrieved_at": None},
            origin="caller")["id"]
        self.artifact, self.text = artifact, data.decode()
        self.jobs = HomologyJobs.create(path / "jobs", executable=FileAsset(PROGRAM, digest(PROGRAM)),
            reference_database=FileAsset(database, digest(database)), policy=POLICY, max_cpu=1)
        self.homology = HomologyEpisodes(self.jobs, parser_policy=POLICY,
            credit_projector=lambda *a, **k: 0, credit_binding={"fixture": "unused_legacy_job_channel"},
            monitoring_projector=lambda *a, **k: 0, monitoring_binding={"fixture": "unused_legacy_monitor_channel"})
        self.tools = ToolRegistry(store)
        self.directory, self.run_id = path / "run", "a101-subtree"
        self.progress = ScientificFindingProgress(FindingProgressPolicy(1))
        self.calls = defaultdict(int)
        self.frames, self.forms, self.native_pages = [], {}, []
        self.interrupt_once = False
        self.interrupted = False

    def setup(self, store, *, run_id, directory, job_episodes, resource_estimator, tool_catalog):
        return bind_assembled_services(store, run_id=run_id, directory=directory,
            job_episodes=job_episodes, resource_estimator=resource_estimator,
            source_directory=PUBLICATION, tool_catalog=tool_catalog,
            tool_retrieval={"version": "scientific_tool_retrieval_v1", "mode": "literal_test_v1"},
            scientific_child_roles=ROLES, handoff_unit=1, acquired_record_unit=1,
            monitoring_information_unit=1, literature_outcome_page_size=8,
            monitor_outcome_page_size=8, log_window_bytes=128, log_roles=("native_text",))

    def controller(self, path, initial):
        role = path[-1][0]
        if role == "scientific_process":
            horizon = (2 if self.partial else 8) if len(path) == 2 else 3 if path[-1][1] == "child_0" else 2
        else:
            horizon = {"annotation": 2, "launch": 1, "launch_local": 4,
                "monitor": 2, "results": 1 if self.partial else 3, "literature": 2}[role]
        def estimate(history, parameters, contexts):
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1),
                parameters, {"fixture": "explicit_test_horizon"})
        return YieldController(str(path), initial, 0, estimate_with_context=estimate)

    def workflow(self):
        flow = Workflow(self.store, self.tools, self, self.directory, self.run_id,
            self.controller, self.progress, project_child_credit=self.progress,
            job_episodes=self.homology, resource_estimator=ResourceToolEstimator(),
            episode_service_factory=self.setup, episode_service_binding={"fixture": "a101_real_subtree_v1"},
            episode_service_inputs="actual_tool_catalog_v1", annotation_child_roles=ROLES,
            episode_record_receipts=True, initial_known_record_refs=[self.source])
        self.flow, self.subtree = flow, A101Subtree(self.directory)
        return flow

    def a101(self, task, *, selected=(), schema=None, initial=None, inherited=(), thought="P01", revision=None):
        selected = self.subtree.commission(self.store, target_ref=self.target, scope=self.scope,
            completeness="fragment" if self.fragment else "complete", child_tool_info=list(selected),
            question={"manager": "Investigate functional distinctions for the supplied unnamed target.",
                "comparisons": "Find informative sequence comparisons and preserve actual native evidence.",
                "features": "Compare the characterized reference sites to distinguish candidate functions."}[task],
            thought_id=thought, evidence_refs=[self.source, *inherited],
            constraints={"network_access": False}, context={"a101_task": task}, schema=schema, initial=initial,
            revision=revision)
        return {"selection": selected, "report_update": {}}

    def anchor(self, phrase):
        start = self.text.index(phrase)
        return {"source_ref": self.source, "artifact_ref": self.artifact,
            "start": start, "end": start + len(phrase), "quote": phrase}

    def extract_references(self):
        terms = [{"alias": alias, "label": label, "term_type": kind,
            "source_ref": self.source, "anchor": self.anchor(phrase)} for alias, label, kind, phrase in (
            ("family", "HydrolaseFamily", "family", "RefA and RefB belong to HydrolaseFamily."),
            ("alpha", "AlphaReaction", "reaction", "ConstructA catalyzed AlphaReaction with AlphaSubstrate."),
            ("beta", "BetaReaction", "reaction", "ConstructB catalyzed BetaReaction with BetaSubstrate."))]
        subjects = [{"alias": "assayed" + letter, "reference_type": "protein", "source_ref": self.source,
            "label": "Construct" + letter,
            "anchor": self.anchor(f"Search sequence Ref{letter} is the sequence of assayed protein Construct{letter}.")}
            for letter in ("A", "B")]
        conditions = [{"alias": "conditions", "context_type": "assay_condition", "name": "buffer pH 7 at 25 C",
            "source_ref": self.source, "attributes": [], "related_refs": ["@assayedA", "@assayedB"],
            "anchor": self.anchor("Assays used buffer pH 7 at 25 C.")}]
        observations = []
        for letter, reaction in (("A", "AlphaReaction"), ("B", "BetaReaction")):
            observations.append({"alias": "experiment" + letter,
                "subject_refs": ["@assayed" + letter], "source_subject_refs": ["@assayed" + letter],
                "kind": "biochemical_assay", "source_ref": self.source,
                "measurements": [{"name": "reference_ref", "value": {"type": "reference", "ref": self.references[letter]}},
                    {"name": "activity", "value": {"type": "enum", "value": "positive"}}],
                "dependencies": [self.references[letter], "@conditions"],
                "anchor": self.anchor(f"Construct{letter} catalyzed {reaction} with {reaction[:-8]}Substrate.")})
        observations.append({"alias": "necessary_site", "subject_refs": ["@assayedA"],
            "source_subject_refs": ["@assayedA"], "kind": "genetic_phenotype", "source_ref": self.source,
            "measurements": [{"name": "start", "value": {"type": "number", "value": 61, "unit_ref": None}},
                {"name": "assay_outcome", "value": {"type": "enum", "value": "negative"}}],
            "dependencies": [self.references["A"], "@conditions", "@experimentA"],
            "anchor": self.anchor("Its H61Q mutant lost AlphaReaction activity while retaining the measured folded state under these assay conditions.")})
        return reasoning(self.store, terms=terms, source_subjects=subjects, contexts=conditions, observations=observations)

    def interpret(self):
        hypotheses = [{"alias": alias, "subject_refs": [self.target], "predicate": predicate,
            "value": {"type": "term_ref", "ref": self.extracted[term]}, "context_refs": []}
            for alias, predicate, term in (("family", "functional_family", "family"),
                ("alpha", "catalyzes", "alpha"), ("beta", "catalyzes", "beta"))]
        rows = []
        for alias, hypothesis, observation, predicate, value, relation, qualification in (
            ("family_support", "family", self.comparisons["A"], "functional_family",
                {"type": "term_ref", "ref": self.extracted["family"]}, "strengthens", "different_source_subject"),
            ("reference_activity", "beta", self.extracted["experimentB"], "catalyzes",
                {"type": "term_ref", "ref": self.extracted["beta"]}, "does_not_discriminate", "different_source_subject"),
            ("specificity_limit", "alpha", self.site_observation, "feature_structure",
                {"type": "enum", "value": "not_measured" if self.fragment else "protein_site"},
                "does_not_discriminate" if self.fragment else "weakens",
                "alternatives_not_discriminated" if self.fragment else "conditions_limit_transfer")):
            source_subjects = ([self.target] if alias == "specificity_limit" else
                self.store.get(observation)["source_subject_refs"])
            source_contexts = [self.extracted["conditions"]] if alias == "reference_activity" else []
            conditions = [self.extracted["conditions"]]
            if alias == "specificity_limit":
                conditions.append(self.extracted["necessary_site"])
            rows.append({"alias": alias, "hypothesis_ref": "@" + hypothesis, "observation_ref": observation,
                "relation": relation, "applicability": "scope_limited" if self.fragment else "transfer",
                "extent_basis": "inferred_extent", "condition_refs": conditions,
                "assumption_refs": [], "expected_revision": 0,
                "target_footprint": self.store.coverage(self.target),
                "investigation_finding": {"source_claim": {"subject_refs": source_subjects,
                    "predicate": predicate, "value": value, "context_refs": source_contexts},
                    "qualification": {"kind": qualification, "context_refs": [], "assumption_refs": []},
                    "status": "retained", "withdrawal_reason": "not_withdrawn",
                    "same_source_claim_as_ref": None, "replaces_refs": []}})
        return reasoning(self.store, hypotheses=hypotheses, assessments=rows)

    def conclusions(self):
        aliases = self.interpreted
        report = initial_report()
        report["family"] = {"status": "supported", "hypothesis_refs": [aliases["family"]],
            "assessment_refs": [aliases["family_support"]]}
        report["activity"] = {"status": "limited", "hypothesis_refs": [aliases["beta"]],
            "assessment_refs": [aliases["reference_activity"]]}
        report["specificity"] = {"status": "unresolved" if self.fragment else "limited",
            "hypothesis_refs": [aliases["alpha"], aliases["beta"]],
            "assessment_refs": [aliases["specificity_limit"]]}
        report["alternative_hypothesis_refs"] = [aliases["alpha"], aliases["beta"]]
        report["limitations"] = (["fragment_input", "unknown_full_length", "unobserved_feature"]
            if self.fragment else ["incompatible_feature"]) + ["unassessed_alternatives"]
        return report

    def integrate_parent(self):
        """Consume only the admitted return, without reading a child's trace."""
        resolved = resolve_report(self.store, self.received, scope=self.scope)
        hypotheses, interpretations = [], {}
        for claim in resolved["claims"].values():
            for hypothesis in claim["hypotheses"]:
                reference = hypothesis["id"]
                row = interpretations.setdefault(reference, {"hypothesis_ref": reference,
                    "disposition": "unresolved", "assessment_refs": []})
                if claim["status"] == "supported":
                    row["disposition"] = "supported"
                for assessment in claim["assessments"]:
                    if assessment["hypothesis_ref"] == reference:
                        if assessment["id"] not in row["assessment_refs"]:
                            row["assessment_refs"].append(assessment["id"])
                        if assessment["relation"] == "weakens":
                            row["disposition"] = "weakened"
        if not interpretations:
            hypotheses = [{"alias": "pending_family", "subject_refs": [self.target],
                "predicate": "functional_family", "value": {"type": "enum", "value": "unresolved"},
                "context_refs": []}]
            interpretations["pending_family"] = {"hypothesis_ref": "@pending_family",
                "disposition": "unresolved", "assessment_refs": []}
        account = {"alias": "a101_parent_account", "subject_ref": self.target,
            "footprint_kind": "localized", "coherent_sets": [{"interpretations": list(interpretations.values()),
                "context_refs": []}], "alternative_refs": self.received["alternative_hypothesis_refs"],
            "resolution": "alternatives_retained" if self.received["alternative_hypothesis_refs"] else "unresolved",
            "expected_revision": 0}
        return reasoning(self.store, hypotheses=hypotheses, interpretation_accounts=[account])

    async def complete(self, episode_id, role, instructions, current, output_schema):
        response = await self.choose(episode_id, role, instructions, current, output_schema)
        process = current.get("scientific_process", {})
        if (process.get("assignment", {}).get("context", {}).get("a101_task") == "manager"
                and not response["report_update"]):
            # Ordinary report updates carry the complete interpretation form.
            # Preserve the initial unknowns until actual assessments are visible.
            response["report_update"] = initial_report()
        return response

    async def choose(self, episode_id, role, instructions, current, output_schema):
        assert role == "REASONING"
        assert not current.get("feedback"), current.get("feedback")
        self.frames.append((episode_id, deepcopy(current)))
        count = self.calls[episode_id]
        self.calls[episode_id] += 1
        row = self.store.db.execute("SELECT path FROM runtime_episodes WHERE episode_id=?", (episode_id,)).fetchone()
        episode_role = json.loads(row[0])[-1][0]
        if episode_role == "annotation":
            if count == 0:
                return self.a101("manager", selected=[{"name": name, "resources": "local"}
                    for name in ("state.query", "source.read")])
            self.received = current["child_reports"][-1]
            return self.integrate_parent()
        if episode_role == "scientific_process":
            process = current["scientific_process"]
            assert process["selection"]["evidence_axis"]["option_id"] == "A101"
            task = process["assignment"]["context"]["a101_task"]
            if task == "manager":
                if count == 0:
                    return self.a101("comparisons", schema=refs_form(), initial={})
                if count == 1:
                    self.forms["comparisons"] = current["child_reports"][-1]
                    if self.partial:
                        report = initial_report()
                        report["limitations"] = ["partial_acquisition", "reference_subject_unlinked", "unassessed_alternatives"]
                        return action("state.query", {"kind": "observation", "limit": 20, "offset": 0}, report)
                    self.comparisons, self.references, self.native_sources = {}, {}, {}
                    self.all_comparisons, by_reference = [], {}
                    for ref in self.forms["comparisons"]["records"]:
                        record = self.store.get(ref)
                        if record["record_type"] == "observation" and record["kind"] == "alignment":
                            reference = self.store.get(record["source_subject_refs"][0])
                            self.all_comparisons.append(ref)
                            values = {row["name"]: row["value"].get("value") for row in record["measurements"]}
                            candidate = (values["bitscore"], ref, reference)
                            previous = by_reference.get(reference["id"])
                            if previous is None or candidate[0] > previous[0]:
                                by_reference[reference["id"]] = candidate
                    # Retain every native domain. Select the strongest scoped
                    # comparison per actual reference for this site question;
                    # several domain rows do not become several references.
                    self.reference_reads = [(ref, reference) for _, ref, reference in by_reference.values()]
                    reference = self.reference_reads[0][1]
                    return action("source.read", {"source_ref": reference["source_ref"],
                        "representation": "original", "offset": 0, "limit": 4096})
                if count in (2, 3):
                    comparison, reference = self.reference_reads[count-2]
                    native = json.loads(current["last_local_outcome"]["result"]["text"])
                    assert native["native_identifier"] in {"RefA", "RefB"}
                    letter = native["native_identifier"][-1]
                    self.comparisons[letter], self.references[letter] = comparison, reference["id"]
                    self.native_sources[letter] = native
                    if count == 2:
                        reference = self.reference_reads[1][1]
                        return action("source.read", {"source_ref": reference["source_ref"],
                            "representation": "original", "offset": 0, "limit": 4096})
                    return child("literature", {"version": "literature_assignment_v1",
                        "question_context_refs": list(self.comparisons.values()) + list(self.references.values()),
                        "source_refs": [self.source]}, self.scope, refs_form(),
                        "Read the supplied characterization source and link each actual assayed subject to its search reference.")
                if count == 4:
                    self.forms["literature"] = current["child_reports"][-1]
                    self.extracted = {}
                    for ref in self.forms["literature"]["records"]:
                        record = self.store.get(ref)
                        if record["record_type"] == "term":
                            self.extracted[{"HydrolaseFamily": "family", "AlphaReaction": "alpha", "BetaReaction": "beta"}[record["label"]]] = ref
                        elif record["record_type"] == "context":
                            self.extracted["conditions"] = ref
                        elif record["record_type"] == "observation":
                            if record["kind"] == "biochemical_assay":
                                assayed = self.store.get(record["source_subject_refs"][0])["label"]
                                self.extracted["experiment" + assayed[-1]] = ref
                            elif record["kind"] == "genetic_phenotype":
                                self.extracted["necessary_site"] = ref
                    return action("process.revise", {"thought_pattern": self.subtree.library.reference("P02"),
                        "child_tool_info": [{"name": "sequence.sites", "resources": "local"}]})
                if count == 5:
                    revision = current["last_local_outcome"]
                    self.revision = deepcopy(revision)
                    source = alignment_site_fact_sources()["reference_site_rows"]["report_schema"]
                    source["items"]["properties"]["selection_policy"] = {
                        "type": "string", "const": "all_own_completed_results"}
                    selected = self.a101("features", thought="P02", inherited=[
                        *self.forms["comparisons"]["records"], *self.forms["literature"]["records"]],
                        selected=[{"name": "sequence.sites", "resources": "local"}],
                        schema=obj({"sites": source, **refs_form()["properties"]}), initial={}, revision=revision)
                    return selected
                if count == 6:
                    self.forms["features"] = current["child_reports"][-1]
                    assert self.forms["features"]["sites"]
                    self.site_observation = next(ref for ref in self.forms["features"]["records"]
                        if self.store.get(ref)["record_type"] == "observation")
                    return self.interpret()
                self.interpreted = current["last_local_outcome"]["aliases"]
                return action("state.query", {"kind": "assessment", "limit": 20, "offset": 0}, self.conclusions())
            if task == "comparisons":
                if count == 0:
                    assignment = {"version": LAUNCH_VERSION, "job_request": {"query_ref": self.target, "cpu": 1},
                        "immutable_input_versions": [], "constraints": {"cpu": 1}, "resource_selection": None,
                        "software_knowledge_refs": [], "resource_knowledge_refs": []}
                    return child("launch", assignment, self.scope, self.handoff_schema(), "Acquire a usable native comparison handoff.")
                if count == 1:
                    self.handoff = current["child_reports"][-1]["handoff"]
                    return child("monitor", {"version": "monitor_assignment_v1",
                        "target_handle": self.handoff["monitoring"]["target_handle"],
                        "requested_fields": ["execution_status"], "known_progress_refs": [],
                        "permitted_committed_record_types": []}, self.scope,
                        obj({"progress": MonitorEpisodes(None).fact_sources("monitor")["monitoring_progress_refs"]["report_schema"]}),
                        "Observe the exposed native comparison progress.")
                return child("results", {"version": RESULTS_VERSION, "handoff": self.handoff,
                    "requested_data_selector": {}}, self.scope, obj({**refs_form()["properties"],
                        "coverage": self.homology.fact_sources("job_results")["job_result_progress"]["report_schema"]}),
                    "Acquire requested comparison rows while preserving parser and acquisition completeness.")
            assert task == "features" and process["thought_pattern"]["id"] == "P02"
            return action("sequence.sites", {"alignment_ref": self.comparisons["A" if count == 0 else "B"], "positions": [60]})
        if episode_role == "literature":
            if count == 0:
                return action("source.read", {"source_ref": self.source, "representation": "original", "offset": 0, "limit": len(self.text)})
            result = self.extract_references()
            # The fixture knows the source selectors; all actual publication IDs
            # are read only after the real reasoning commit has completed.
            return result
        if episode_role == "launch":
            binding = self.flow.episode_bindings.for_role("launch")
            adapter, = binding.adapters.values()
            assignment = deepcopy(current["assignment"])
            assignment["resource_selection"] = adapter._selection(1)
            return child("launch_local", assignment, self.scope, self.handoff_schema(), "Establish this exact native job.")
        if episode_role == "launch_local":
            if self.interrupt_once and count == 3 and not self.interrupted:
                self.calls[episode_id] -= 1
                self.interrupted = True
                raise InterruptedAfterSubmission()
            return action(("homology.configure", "homology.stage", "homology.submit", "homology.check_handoff")[count])
        if episode_role == "monitor":
            return action("progress.observe", {"requested_fields": ["execution_status"]})
        assert episode_role == "results"
        if count:
            self.native_pages.append(deepcopy(current["last_local_outcome"]))
        # The native inventory contains reference rows followed by domain
        # observations. The first prefix includes an actual comparison while
        # leaving a later comparison unacquired; the next page uses its cursor.
        if count == 2 and current["last_local_outcome"]["result"]["next_offset"] is None:
            return action("homology.coverage", {"snapshot_ref": current["last_local_outcome"]["result"]["snapshot_ref"]})
        offset = 0 if count < 2 else current["last_local_outcome"]["result"]["next_offset"]
        arguments = {"limit": 3 if count < 2 else current["last_local_outcome"]["result"]["total"] - offset,
            "offset": offset}
        if count:
            arguments["snapshot_ref"] = current["last_local_outcome"]["result"]["snapshot_ref"]
        return action("homology.extract", arguments)

    def handoff_schema(self):
        return obj({"handoff": self.flow.episode_bindings.for_role("launch").fact_sources("launch")["execution_handoff"]["report_schema"]})

    async def release(self, episode_id):
        pass

    async def run(self):
        flow = self.workflow()
        root = flow.build("annotation", "root", "Investigate this unnamed target using the A101 subtree.", self.scope)
        self.root = root
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
