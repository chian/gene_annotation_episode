"""Admit episode-selected source spans to the existing reaction repository.

The episode nominates experimental meanings and exact source selectors. This
boundary retains that nomination, never a model-authored measured value. The
original native reader, numerical calculator, publication and return validator
remain the authorities. Historical retained-dataset operations are unchanged.
"""
from copy import deepcopy
from dataclasses import replace

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from .literature_assay_inputs import _nullable, _witness_schema
from .library.literature_partner_source_fields import number_selector_schema
from .library.literature_reaction_inputs import (
    BATCH_UNITS, BUDGET_BASES, RATE_UNITS, RATIO_KINDS, RATIO_MODES, RATIO_UNITS,
    reaction_population_schema,
)
from .library.literature_reaction_meanings import (
    BASES, DEMAND_FIELDS, MODEL_FIELDS, RESOURCE_FIELDS,
)
from .library.literature_reaction_native_inputs import (
    COUNT_BASES, RATIO_BASES, UNCERTAINTY_KINDS, VERSION, _UNITS,
)


from .library.literature_reaction_source_contracts import (
    native_selection_schema, reaction_source_population_schema, _source_references, PROVIDER, OPERATION,
)

def populate_source(repository, context, arguments, operation_key):
    """One authenticated tool action, with a retained selector intermediate.

    Only the newly created selector source joins the internal context. Every
    evidence source must already be received and within the original scope;
    the original repository independently checks every actually read witness.
    Its immutable operation signature provides replay/idempotency. This does
    not grant the episode access to any other sheet or source.
    """
    if context.run_id != repository.run_id:
        raise ContractError('literature_run_mismatch')
    if not isinstance(operation_key, str) or not operation_key:
        raise ContractError('operation_key_required')
    args = plain(arguments)
    validate_schema(args, reaction_source_population_schema())
    sources = _source_references(args)
    for reference in sources:
        repository._source(context, reference)
    assessment = args.get('experiment_assessment')
    if assessment is not None:
        from .library.literature_experiment_assessments import authorize_assessment
        authorize_assessment(repository, context, assessment)
    store = repository.store
    with store.transaction():
        artifact = store.artifact(canonical(args['native_selection']), 'application/json')
        request = store.artifact(canonical({'operation': OPERATION, 'operation_key': operation_key,
            'run_id': context.run_id, 'episode_id': context.episode_id,
            'scope': plain(context.scope), 'arguments': args}), 'application/json')
        selected = store.put('source', {'provider': PROVIDER, 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
            'version': VERSION, 'retrieved_at': None, 'parent_source_refs': sources},
            origin='tool', scope=plain(context.scope))
        internal = replace(context, received_record_refs=tuple(dict.fromkeys([
            *context.received_record_refs, selected['id']])))
        operands = {name: value for name, value in args.items() if name != 'native_selection'}
        operands['data_source_ref'] = selected['id']
        outcome = repository.populate(internal, operands, operation_key)
        return {**outcome,
            'record_refs': list(dict.fromkeys([*outcome['record_refs'], selected['id']])),
            'changed_record_refs': list(dict.fromkeys([
                *outcome.get('changed_record_refs', ()), selected['id']])),
            'result': {**outcome['result'], 'selection_source_ref': selected['id']}}
