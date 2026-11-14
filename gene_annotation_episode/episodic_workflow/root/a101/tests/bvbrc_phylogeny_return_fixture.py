"""Original controlled publication/return fixtures, never native proof.

Publication envelopes and sheets are explicit synthetic fixtures. Actual Store
bytes, original action identities, typed forms and receipt admission are tested.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.a101.bvbrc_appservice_publication import DATA_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain, form_with_facts
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a101.runtime import TypedReportContract
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_phylogeny_returns import BVBRCPhylogenyReturns, FACT_SOURCES
from .bvbrc_controlled_saved_records import SavedRecords
from .bvbrc_phylogeny_saved_fixture import fact_form

class ControlledPublications:
    """Saved Store bytes with controlled publication envelope, never native proof."""
    def __init__(self, saved):
        self.saved, self.bodies, self.sheets = saved, {}, {}

    def add(self, context, body, sheet, *, index=0):
        body = deepcopy(body)
        binding = self.saved.source(canonical(sheet).encode(), provider=DATA_PROVIDER)
        body["publication"]["adapter_result"]["sheet_content"] = binding
        self.sheets[binding["source_ref"]] = binding
        bundle = self.saved.source(canonical({"body": body, "episode_id": context.episode_id, "action_index": index}).encode(), provider=DATA_PROVIDER)
        reference = bundle["source_ref"]
        body.update(reference=reference, source_ref=reference, record_refs=[reference], run_id=context.run_id,
            episode_id=context.episode_id, scope=plain(context.scope), assignment=plain(context.assignment))
        body["publication"].update(bundle_content=bundle, result_record_refs=[reference])
        self.bodies[reference] = body
        self.saved.own(context, reference, index, tool="api.bvbrc_appservice.download")
        return body

    def own_results(self, context):
        self.saved.custody.authenticate(context, allow_unsaved=True)
        rows = self.saved.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND result IS NOT NULL ORDER BY decision_index", (context.run_id, context.episode_id))
        return [ref for row in rows if (result := json.loads(row["result"]))["status"] in {"completed", "partial"}
            for ref in result["record_refs"] if ref in self.bodies]

    def read(self, reference, scope, *, episode_id=None):
        body = deepcopy(self.bodies[reference])
        context = self.saved.custody.context(body["episode_id"])
        assert episode_id is None or episode_id == context.episode_id
        self.saved.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        self.saved.custody.possession(context, reference)
        assert reference in self.own_results(context)
        return body

    def read_content_source(self, reference, scope):
        binding = self.sheets[reference]
        raw = self.saved.store.get_artifact(binding["artifact_ref"])
        assert hashlib.sha256(raw).hexdigest() == binding["sha256"]
        return json.loads(raw)

class ReturnFixture:
    def __init__(self, store):
        self.saved, self.store = SavedRecords(store), store
        self.publications = ControlledPublications(self.saved)
        self.api = SimpleNamespace(store=store, run_id=self.saved.run_id)
        self.api.appservice = SimpleNamespace(publications=self.publications, custody=self.saved.custody, resolve=self.resolve_source)
        self.host = BVBRCPhylogenyReturns(self.api)

    def resolve_source(self, context, reference, namespace):
        if namespace not in {None, "source", "execution_result"}:
            return None
        try:
            self.saved.custody.possession(context, reference)
            if namespace == "execution_result":
                self.publications.read(reference, context.scope)
            return True
        except (KeyError, ValueError):
            return False

    def child(self, parent, role, body, *, index=0, sources=FACT_SOURCES, schema=None):
        assignment = {} if role != "results" else {"version": "execution_results_assignment_v1",
            "handoff_ref": "source_" + "a" * 24, "selector": body["publication_inputs"]["selector"]}
        return self.saved.child(parent, role, assignment, index, schema=fact_form(*sources) if schema is None else schema)

    def candidate(self, child, *, extra_facts=None):
        schema = plain(child.request)["report_contract"]["measurements"]["schema"]
        facts = self.host.facts(child, schema) if child.role == "results" else self.host.received_facts(child, schema)
        facts.update(extra_facts or {})
        form = form_with_facts({}, schema, facts)
        self.saved.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        return form, schema

    def admit(self, parent, child, *, extra_facts=None, receive=True):
        form, schema = self.candidate(child, extra_facts=extra_facts)
        original = plain(child.request)["report_contract"]
        resolve = self.host.resolve_own if child.role == "results" else self.host.resolve_received
        def resolver(reference, namespace):
            value = resolve(child, reference, namespace)
            return self.resolve_source(child, reference, namespace) if value is None else value
        typed = TypedReportContract(original["decision"], schema, resolver,
            lambda value: self.host.validate_received_report(child, value, schema))
        admitted = plain(typed.admit(form, audit_identifiers=(child.episode_id,)).as_record())
        index = int(child.path[-1][1].removeprefix("child_"))
        self.saved.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24], "child_episode_id": child.episode_id,
            "contract": canonical(original), "form": canonical(admitted), "failure": None})
        key = f"{parent.run_id}:{parent.episode_id}:{index}:typed_form"
        references = self.host.record_admission(parent, admitted, schema, key)
        if receive:
            self.saved.receipts.receive(parent.episode_id, references, kind="child_form", source_index=index)
        return admitted, schema, key, references
