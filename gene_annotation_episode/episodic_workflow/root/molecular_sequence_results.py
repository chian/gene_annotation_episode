"""Original molecular result responsibility: molecular_sequence_results."""
from __future__ import annotations
from copy import deepcopy
import hashlib
from pathlib import Path
from .method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .bvbrc_appservice_custody import AppServiceCustody
from .episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import validate_target
from gene_annotation_episode.execution_contracts import canonical, digest
from .molecular_result_actions import MolecularResultActions as _Actions
from gene_annotation_episode.native_control_records import immutable, same
from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import MODES, require, validate_molecular_sequence_result_selector
from gene_annotation_episode.native_file_capture import capture_native_file, _identity
from gene_annotation_episode.episodic_workflow.root.library import molecular_sequence_result_contracts as supplied
from .molecular_result_values import PREFIX, _json

from .molecular_result_custody import MolecularResultCustody
from .molecular_result_publication import MolecularResultPublication
from .molecular_result_saved import MolecularResultSaved
from .molecular_result_original_evidence import MolecularResultOriginalEvidence
from .molecular_result_execution import MolecularResultExecution
from .molecular_result_facts import MolecularResultFacts
from .molecular_result_supplied import MolecularResultSupplied

class MolecularSequenceResults(MolecularResultCustody, MolecularResultPublication, MolecularResultSaved, MolecularResultOriginalEvidence, MolecularResultExecution, MolecularResultFacts, MolecularResultSupplied, EpisodeReturnRecords):
    """One owner for five profiles; no per-profile receipt or episode types."""
    locked_action = _Actions.locked_action
    require_action = _Actions.require_action
    _artifact_value = _Actions._artifact_value
    capture_control = _Actions.capture_control
    observation = _Actions.observation
    _selection = AppServiceCustody._selection
    _selected_form = AppServiceCustody._selected_form
    _child_contract = AppServiceCustody._child_contract
    _report_contract = staticmethod(AppServiceCustody._report_contract)
    _contract_information = AppServiceCustody._contract_information
    _json = AppServiceCustody._json
    _table = AppServiceCustody._table
    _attempt = AppServiceCustody._attempt

    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="molecular_sequence_result_")
        self.owner, self._active = owner, {}

    @property
    def returns(self):
        return self

    def applies(self, context):
        return context.role == "results" and plain(context.assignment).get("selector", {}).get("version") in (
            "molecular_sequence_result_selector_v1", supplied.SUPPLIED_SELECTOR_VERSION)

    def action_directory(self, episode_id, operation_key):
        return Path(self.owner.directory) / "execution-results" / digest([self.run_id, episode_id]) / "molecular-sequence-actions" / digest(operation_key)

    def file_metadata(self, file, *, value=None, newline=False):
        file = _identity(file)
        metadata = self.store.get(file["artifact_ref"])
        require(metadata["record_type"] == "artifact" and metadata["id"] == file["artifact_ref"]
            and metadata["sha256"] == file["sha256"] and metadata["size"] == file["size_bytes"], "molecular_sequence_file_identity_conflict")
        if value is not None:
            raw = canonical(value).encode() + (b"\n" if newline else b"")
            require(hashlib.sha256(raw).hexdigest() == file["sha256"] and len(raw) == file["size_bytes"], "molecular_sequence_file_value_conflict")
        return file

    def _commission(self, parent, child, *, construction=False):
        self.authenticate(parent, allow_unsaved=construction); self.authenticate(child, allow_unsaved=construction)
        require(child.path[:-1] == parent.path, "molecular_sequence_commission_parent_conflict")
        self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        slot = child.path[-1][1]
        require(slot.startswith("child_") and slot[6:].isdecimal(), "molecular_sequence_commission_slot_conflict")
        index = int(slot[6:])
        require(str(index) == slot[6:])
        selected, sent = self._selection(parent, index, unsaved=construction)
        require(selected.get("kind") in ("episode_child", "job_child"), "molecular_sequence_original_commission_required")
        require(selected.get("role") == child.role, "molecular_sequence_commission_role_conflict")
        require(same(selected.get("scope"), plain(child.scope)), "molecular_sequence_commission_scope_conflict")
        if child.role in ("results", "launch", "launch_local"):
            require(same(selected.get("assignment"), plain(child.assignment)), "molecular_sequence_commission_assignment_conflict")
        self._child_contract(child, selected, sent)

    def _context(self, context):
        self.authenticate(context)
        require(self.applies(context) and len(context.path) > 1, "molecular_sequence_results_context_required")
        assignment = plain(context.assignment)
        if assignment.get("selector", {}).get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            require(set(assignment) == {"version", "selector", "constraints"}
                and assignment["version"] == supplied.SUPPLIED_ASSIGNMENT_VERSION)
            supplied.validate_molecular_sequence_supplied_selector(assignment["selector"])
            supplied.supplied_execution_constraints(assignment["constraints"])
        else:
            require(set(assignment) == {"version", "handoff_ref", "selector"} and assignment["version"] == "execution_results_assignment_v1")
            validate_molecular_sequence_result_selector(assignment["selector"])
        self.store.validate_scope(plain(context.scope))
        self._commission(self.context(EpisodeRef(self.run_id, context.path[:-1]).episode_id), context)
        return assignment

    def intent(self, context, target, tool_name, arguments, operation_key):
        if tool_name in supplied.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS:
            self.authenticate(context)
            require(target is None)
            self.store.validate_scope(plain(context.scope))
            value = supplied.validate_ordinary_molecular_sequence_intent(dict(version=supplied.ordinary_molecular_sequence_intent_version(tool_name, arguments),
                run_id=self.run_id, episode_id=context.episode_id, path=plain(context.path), scope=plain(context.scope),
                assignment=plain(context.assignment), original_request_sha256=digest(plain(context.request)),
                operation_key=operation_key, tool_name=tool_name, arguments=deepcopy(arguments), target=None), operation=tool_name)
            self._selected(value)
            return value
        assignment = self._context(context)
        require(tool_name in ("execution.results.status", "execution.results.collect") and arguments == {} and type(arguments) is dict)
        if assignment["selector"].get("version") == supplied.SUPPLIED_SELECTOR_VERSION:
            require(target is None)
        elif assignment["selector"]["mode"] == MODES[0]:
            target = validate_target(plain(target))
            require(target["run_id"] == self.run_id and target["handle"] == assignment["handoff_ref"] and target["resource_kind"] == "local")
            self.store.validate_scope(target["scope"], parent_scope=plain(context.scope))
        else:
            require(target is None)
        value = dict(version="molecular_sequence_result_intent_v1", run_id=self.run_id, episode_id=context.episode_id,
            path=plain(context.path), scope=plain(context.scope), assignment=assignment,
            original_request_sha256=digest(plain(context.request)), operation_key=operation_key, tool_name=tool_name,
            arguments={}, target=deepcopy(target))
        self._selected(value)
        return value

    def _selected(self, intent):
        operation = intent.get("tool_name")
        if operation not in supplied.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS:
            return _Actions._selected(self, intent)
        intent = supplied.validate_ordinary_molecular_sequence_intent(intent, operation=operation)
        context = self.context(intent["episode_id"])
        require(same(intent, self._ordinary_context_intent(context, intent["arguments"], intent["operation_key"],
            operation=operation)), "molecular_sequence_ordinary_context_conflict")
        row = self.owner._selected_result_action(intent["episode_id"], intent["operation_key"],
            operation, intent["arguments"])
        require(same(_json(row["action"].encode()), dict(kind="tool", tool=operation,
            arguments=intent["arguments"])), "molecular_sequence_ordinary_selected_action_conflict")
        return row

    def _ordinary_context_intent(self, context, arguments, operation_key, *, operation=supplied.ORDINARY_ORF_TOOL):
        EpisodeReturnRecords(self.store, context.run_id, failure_prefix="molecular_sequence_ordinary_").authenticate(context)
        return supplied.validate_ordinary_molecular_sequence_intent(dict(version=supplied.ordinary_molecular_sequence_intent_version(operation, arguments),
            run_id=context.run_id, episode_id=context.episode_id, path=plain(context.path), scope=plain(context.scope),
            assignment=plain(context.assignment), original_request_sha256=digest(plain(context.request)),
            operation_key=operation_key, tool_name=operation, arguments=deepcopy(arguments), target=None), operation=operation)
