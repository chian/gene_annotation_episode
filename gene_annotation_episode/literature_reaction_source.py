"""Admit episode-selected source spans to the existing reaction repository.

The episode nominates experimental meanings and exact source selectors. This
boundary retains that nomination, never a model-authored measured value. The
original native reader, numerical calculator, publication and return validator
remain the authorities. Historical retained-dataset operations are unchanged.
"""
from copy import deepcopy
from dataclasses import replace

from .communication import plain
from .domain import ContractError, canonical, obj, validate_schema
from .literature_assay_inputs import _nullable, _witness_schema
from .literature_partner_source_fields import number_selector_schema
from .literature_reaction_inputs import (
    BATCH_UNITS, BUDGET_BASES, RATE_UNITS, RATIO_KINDS, RATIO_MODES, RATIO_UNITS,
    reaction_population_schema,
)
from .literature_reaction_meanings import (
    BASES, DEMAND_FIELDS, MODEL_FIELDS, RESOURCE_FIELDS,
)
from .literature_reaction_native_inputs import (
    COUNT_BASES, RATIO_BASES, UNCERTAINTY_KINDS, VERSION, _UNITS,
)


PROVIDER = 'literature.experimental.reaction_source_selection'
OPERATION = 'literature.reaction.source.populate'


def native_selection_schema():
    """Closed operands for the original a110_source_reaction_selection_v1."""
    witness = _witness_schema()
    number = number_selector_schema()
    witnesses = {'type': 'array', 'items': deepcopy(witness)}
    text = {'type': 'string', 'minLength': 1}
    parameter = {'anyOf': [
        obj({'kind': {'const': 'source_number'}, 'number': deepcopy(number),
             'evidence': deepcopy(witnesses)}),
        obj({'kind': {'const': 'declared'}, 'value': {'type': ['number', 'null']},
             'basis': {'enum': ['source_supported_inference', 'conditional_assumption', 'unresolved']},
             'evidence': deepcopy(witnesses)}),
        {'type': 'null'}]}
    parameter['description'] = ('A model prediction, coefficient or demand is a declared '
        'interpretation, separate from an experimentally measured quantity. Preserve its basis.')
    ratio_value = {'anyOf': [
        obj({'kind': {'const': 'point'}, 'number': deepcopy(number)}),
        obj({'kind': {'const': 'reported_pair'}, 'numerator': deepcopy(number),
             'denominator': deepcopy(number)})]}
    ratio_value['description'] = ('Select a complete reported point or an author-reported a:b '
        'expression. Both pair tokens must share the same exact expression witness. Do not '
        'supply measured values or digitize a spectrum through this reader.')
    summary = obj({'value': _nullable(deepcopy(ratio_value)),
        'uncertainty': obj({'kind': {'enum': list(UNCERTAINTY_KINDS)},
            'number': _nullable(deepcopy(number)), 'basis_witnesses': deepcopy(witnesses)}),
        'count': obj({'number': _nullable(deepcopy(number)),
            'basis': {'enum': list(COUNT_BASES)}, 'basis_witnesses': deepcopy(witnesses)})})
    ratio = obj({'mode': {'enum': list(RATIO_MODES)}, 'ratio_kind': {'enum': list(RATIO_KINDS)},
        'unit': {'enum': list(RATIO_UNITS)}, 'measurement_basis': {'enum': list(RATIO_BASES)},
        'basis_witnesses': deepcopy(witnesses),
        'observations': {'type': 'array', 'items': obj({'measurement_key': deepcopy(text),
            'value': deepcopy(ratio_value), 'basis_witnesses': deepcopy(witnesses)})},
        'summary': _nullable(summary), 'claim': deepcopy(parameter),
        'alternatives': {'type': 'array', 'items': obj({'key': deepcopy(text),
            'prediction': deepcopy(parameter)})}})
    unit_witness = deepcopy(witness)
    unit_witness['description'] = (
        'Select the printed unit alone or a source-supported header unit, rather '
        'than the surrounding sentence. Supported normalized literal forms: '
        + ', '.join(sorted(_UNITS)) + '. The existing reader removes unit markup '
        'and spacing and normalizes micro signs to u. Spelled-out unit names are '
        'not parsed by this reader; do not rewrite the original quotation or '
        'substitute a model assumption for a source unit.')
    quantity = _nullable(obj({'number': deepcopy(number), 'unit': unit_witness}))
    budget = obj({'basis': {'enum': list(BUDGET_BASES)},
        'unit': {'enum': [*BATCH_UNITS, *RATE_UNITS]}, 'resources_complete': {'type': 'boolean'},
        'resources': {'type': 'array', 'items': obj({'resource_key': deepcopy(text),
            **{name: deepcopy(quantity) for name in ('value', 'lower', 'upper')},
            'coefficient': deepcopy(parameter)})}, 'demand': deepcopy(parameter)})

    def meaning(fields, bases):
        return {**{name: _nullable(deepcopy(witness)) for name in fields},
            **{name: {'enum': list(BASES)} for name in bases}}

    meanings = obj({'ratio': _nullable(obj({
        'claim': obj(meaning(MODEL_FIELDS, ('prediction_basis',))),
        'alternatives': {'type': 'array', 'items': obj({'key': deepcopy(text),
            **meaning(MODEL_FIELDS, ('prediction_basis',))})}})),
        'budget': _nullable(obj({'resources': {'type': 'array', 'items': obj({
            'resource_key': deepcopy(text),
            **meaning(RESOURCE_FIELDS, ('supply_basis', 'coefficient_basis'))})},
            'demand': obj(meaning(DEMAND_FIELDS, ('demand_basis',)))}))})
    return obj({'version': {'const': VERSION}, 'ratio': _nullable(ratio),
        'budget': _nullable(budget), 'meanings': meanings})


def reaction_source_population_schema():
    fields = deepcopy(reaction_population_schema(include_assessment=True)['properties'])
    fields.pop('data_source_ref')
    fields['native_selection'] = native_selection_schema()
    schema = obj(fields, required=[name for name in fields if name != 'experiment_assessment'])
    schema['description'] = ('Source witness offsets are zero-based half-open UTF-8 bytes. '
        'Inner number_start/number_end offsets count Unicode characters in the exact quote. '
        'The host saves these selections and invokes the existing native reaction reader and '
        'component calculator. Missing physical measurements remain unknown. Model parameters '
        'are explicit interpretations and never substitutes for observed numbers.')
    return schema


def _source_references(value):
    references = []

    def visit(item):
        if isinstance(item, dict):
            if 'source_ref' in item:
                references.append(item['source_ref'])
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return list(dict.fromkeys(references))


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
        from .literature_experiment_assessments import authorize_assessment
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
