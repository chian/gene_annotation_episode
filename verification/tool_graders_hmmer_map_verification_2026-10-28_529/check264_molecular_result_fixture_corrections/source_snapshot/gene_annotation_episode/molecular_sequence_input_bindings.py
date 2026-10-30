"""Read actual received JSON bytes without launching, granting or freezing work.

This owner captures current admitted metadata only. Historical selected versions
and immutable logical launch controls belong to the later request binding.
"""
from copy import deepcopy
import hashlib
import re

from method_loop.identities import EpisodeRef

from .bvbrc_appservice_custody import AppServiceCustody, AppServiceCustodyError
from .communication import plain
from .domain import ContractError, identity
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .materials import source_window_selection
from .molecular_sequence_input_contracts import (
    RECEIVED_INPUT_VERSION, NAMESPACES, TAG_KEYS, decode_molecular_sequence_input,
    input_record_digest, molecular_sequence_input_failure,
    unread_molecular_sequence_input_content, validate_molecular_sequence_received_input,
)
from .native_file_capture import NativeFileCaptureError, _metadata, retained_native_file
from .native_flux_balance_storage import read_bytes


_BASELINE_ROLES = frozenset(("launch", "launch_local", "launch_api", "launch_hpc", "results"))


class _InputFailure(ValueError):
    def __init__(self, code): self.code = code


def _require(condition, code):
    if not condition: raise _InputFailure(code)


class MolecularSequenceInputBindings:
    """One current received-file authority for all participating profiles."""

    def __init__(self, owner):
        self.owner, self.store, self.run_id = owner, owner.store, owner.run_id
        self.records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix="molecular_sequence_input_")
        # Only its original generic selection/form readers are used. No
        # AppService operand, task, transport or submission method is called.
        self.frames = AppServiceCustody(self.store, self.run_id)

    def _authority(self, context):
        _require(isinstance(context, BindingContext) and context.run_id == self.run_id
            and context.path and context.role == context.path[-1][0], "invalid_context")
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.store.db, self.run_id
        current, seen = context, set()
        while True:
            _require(current.episode_id not in seen, "invalid_inheritance")
            seen.add(current.episode_id)
            try:
                self.records.authenticate(current)
            except (ValueError, KeyError, TypeError) as error:
                raise _InputFailure("invalid_context") from error
            try:
                manifest = receipts.manifest(current.episode_id)
                parent_id = EpisodeRef(self.run_id, current.path[:-1]).episode_id if len(current.path) > 1 else None
                _require(manifest["parent_episode_id"] == parent_id and "received_report_prefix" in manifest
                    and self.records._equal(current.request["message"].get("knowledge_inheritance"), manifest), "invalid_inheritance")
                through = manifest["through_receipt_index"]
                _require(through is None if parent_id is None else type(through) is int and through >= 0, "invalid_inheritance")
            except (ValueError, KeyError, TypeError) as error:
                if isinstance(error, _InputFailure): raise
                raise _InputFailure("invalid_inheritance") from error
            try:
                self.store.validate_scope(plain(current.scope))
            except ContractError as error:
                raise _InputFailure("scope_denied") from error
            if parent_id is None: break
            try:
                parent = self.records.context(parent_id)
                slot = re.fullmatch(r"child_(0|[1-9][0-9]*)", current.path[-1][1])
                _require(slot is not None and parent.path == current.path[:-1], "invalid_commission")
                selected, sent = self.frames._selection(parent, int(slot[1]))
                _require(selected.get("kind") in ("child", "episode_child", "job_child")
                    and (selected.get("kind") == "child" or selected.get("role") == current.role)
                    and self.records._equal(selected.get("scope"), current.scope)
                    and self.records._equal(selected.get("assignment", {}), current.assignment), "invalid_commission")
                self.frames._child_contract(current, selected, sent)
            except (AppServiceCustodyError, ValueError, KeyError, TypeError) as error:
                if isinstance(error, _InputFailure): raise
                raise _InputFailure("invalid_commission") from error
            try:
                self.store.validate_scope(plain(current.scope), parent_scope=plain(parent.scope))
            except ContractError as error:
                raise _InputFailure("scope_denied") from error
            current = parent
        try:
            scope = self.store.validate_scope(plain(context.scope))
            manifest = receipts.manifest(context.episode_id)
            known = set(receipts.known(context.episode_id, baseline=context.role in _BASELINE_ROLES))
        except (ValueError, KeyError, TypeError) as error:
            raise _InputFailure("invalid_inheritance") from error
        return scope, manifest, known

    def _access(self, context, reference, namespace, *, artifact=False):
        callback = getattr(self.owner, "resolve_received_reference", None)
        _require(callable(callback), "artifact_denied" if artifact else "reference_denied")
        try:
            verdict = callback(context, reference, namespace)
        except ValueError as error:
            raise _InputFailure("artifact_denied" if artifact else "reference_denied") from error
        _require(verdict is None or type(verdict) is bool, "artifact_denied" if artifact else "reference_denied")
        _require(verdict is not False, "artifact_denied" if artifact else "reference_denied")

    def read_received(self, context, reference, namespace, *, tag_key):
        """Read original bytes only; format=json labels the selected processing.

        Authority failure returns no private input metadata. Original source
        text_ref/auxiliary refs never substitute for its admitted artifact_ref.
        """
        if (type(reference) is not str or not reference or any(c in reference for c in "\0\r\n")
                or namespace not in NAMESPACES or tag_key not in TAG_KEYS):
            raise ValueError("molecular_sequence_input_invalid_selection")
        result = dict(version=RECEIVED_INPUT_VERSION, selection=dict(reference=reference, namespace=namespace), input=None, failure=None)
        try:
            with self.store.read_snapshot():
                scope, manifest, known = self._authority(context)
                _require(reference in known, "reference_not_received")
                self._access(context, reference, namespace)
                try:
                    record = self.store.get(reference)
                except (ContractError, OSError) as error:
                    raise _InputFailure("reference_unavailable") from error
                _require(record.get("id") == reference and record.get("record_type") == namespace, "reference_type_conflict")
                if namespace == "source":
                    try:
                        _require(bool(self.store.reference_subset([reference], scope)), "scope_denied")
                    except ContractError as error:
                        raise _InputFailure("scope_denied") from error
                    payload = {key: value for key, value in record.items() if key not in ("id", "record_type", "origin")}
                    _require(record.get("origin") is not None
                        and identity("source", dict(origin=record["origin"], record=payload)) == reference, "source_identity_conflict")
                    artifact_ref, representation, _ = source_window_selection(record, "original")
                    _require(representation == "original" and type(artifact_ref) is str, "artifact_unavailable")
                else:
                    artifact_ref = reference
                _require(artifact_ref in known, "artifact_not_received")
                self._access(context, artifact_ref, "artifact", artifact=True)
                try:
                    artifact = _metadata(self.store, artifact_ref)
                except NativeFileCaptureError as error:
                    code = "artifact_identity_conflict" if error.code == "retained_artifact_mismatch" else "artifact_unavailable"
                    raise _InputFailure(code) from error
                file = dict(artifact_ref=artifact_ref, sha256=artifact["sha256"], size_bytes=artifact["size"], format="json")
                item = dict(receiver=dict(run_id=self.run_id, episode_id=context.episode_id,
                    request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment))),
                    scope=scope, inheritance_manifest=manifest,
                    witness=dict(reference=reference, namespace=namespace, record=deepcopy(record), record_sha256=input_record_digest(record),
                        record_revision=record.get("revision"), source_version=record.get("version") if namespace == "source" else None),
                    file=file, artifact_record=artifact, tag_key=tag_key, byte_verification="unavailable", content=None)
                result["input"] = item
                try:
                    raw = read_bytes(retained_native_file(self.store, file))
                    _require(len(raw) == file["size_bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"], "artifact_identity_conflict")
                except NativeFileCaptureError as error:
                    code = "artifact_identity_conflict" if error.code == "retained_artifact_mismatch" else "artifact_bytes_unavailable"
                except (OSError, ValueError) as error:
                    code = error.code if isinstance(error, _InputFailure) else "artifact_bytes_unavailable"
                else:
                    item["byte_verification"] = "verified"
                    item["content"] = decode_molecular_sequence_input(raw, tag_key=tag_key)
                    result["failure"] = deepcopy(item["content"]["failure"])
                    return validate_molecular_sequence_received_input(result)
                result["failure"] = molecular_sequence_input_failure(code)
                item["byte_verification"] = "identity_conflict" if code == "artifact_identity_conflict" else "unavailable"
                item["content"] = unread_molecular_sequence_input_content(result["failure"])
        except _InputFailure as error:
            # No witness/File details leave an authority failure boundary.
            result["input"] = None
            result["failure"] = molecular_sequence_input_failure(error.code)
        return validate_molecular_sequence_received_input(result)


__all__ = ["MolecularSequenceInputBindings"]
