"""Original private assay invocation and immutable record identity readers."""
from .communication import plain
from .domain import identity
from gene_annotation_episode.domain import ContractError
from .execution_contracts import canonical, digest
from .episode_return_records import EpisodeReturnRecords

def _require(condition, code):
    if not condition: raise ContractError("reference_edit_outcome_" + code)

def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()), "closed_fields_required")

def _invocation(context, operation_key):
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if type(operation_key) is str and operation_key.startswith(prefix) else ""
    _require(suffix.isdecimal() and str(int(suffix)) == suffix, "action_key_invalid")
    return dict(run_id=context.run_id, episode_id=context.episode_id, operation_key=operation_key,
        decision_index=int(suffix), request_sha256=digest(plain(context.request)), scope=plain(context.scope))

def _context(store, invocation):
    _closed(invocation, "run_id episode_id operation_key decision_index request_sha256 scope")
    _require(type(invocation["decision_index"]) is int and invocation["decision_index"] >= 0, "invocation_conflict")
    records = EpisodeReturnRecords(store, invocation["run_id"], failure_prefix="reference_edit_outcome_")
    context = records.context(invocation["episode_id"])
    _require(canonical(_invocation(context, invocation["operation_key"])) == canonical(invocation), "invocation_conflict")
    return context

def immutable_record(record):
    payload = {k: v for k, v in record.items() if k not in {'id', 'record_type', 'origin'}}
    kind = record['record_type']
    if kind == 'input':
        # materials.create_problem / library_targets.bind hash the original
        # input payload directly, before adding caller ownership metadata.
        expected = identity('input', payload)
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    elif kind == 'read_subject':
        # A read subject is resolved from fixed library membership, rather than
        # stored as an independently hashed scientific record.
        from .library_targets import read_ref
        expected = read_ref(record['library_ref'], record['member_ref'])
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    else:
        expected = identity(kind, {'origin': record['origin'], 'record': payload})
    if record['id'] != expected:
        raise ContractError('site_record_identity_conflict')

