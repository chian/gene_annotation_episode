"""Present saved A110 results beside their original action's recorded credit.

The common report owns action identity and iterator credit. This adapter only
projects the original own outcome and already authorized receiver views. It
opens no source or artifact, calculates no chemical quantity and supplies no
additional functional verdict.
"""
from collections.abc import Mapping
from copy import deepcopy
import json

from .literature_reaction_calculations import COMPONENTS as REACTION_COMPONENTS


_ACCOUNTING = frozenset({'a110_chemical_accounting_v1', 'a110_chemical_accounting_v2'})
_FBA = frozenset({'a110_flux_balance_hpc_v1', 'a110_flux_balance_hpc_v2'})
_QUALIFICATIONS = frozenset({'a110_received_qualification_v1',
                            'a110_experimental_component_use_v1'})
_COMMON = ('source_ref', 'grading_artifact_ref', 'artifact_ref', 'target_ref',
    'target_regions', 'scope', 'request_ref', 'hpc_result_ref', 'scientific_profile',
    'input_snapshot_status', 'changed_received_input_metadata_refs')
_CELL_FIELDS = ('sheet_ref', 'component', 'value', 'lower', 'upper', 'unit',
    'status', 'origin', 'formula_code', 'unavailable_reason', 'bound_kind',
    'conditional_on', 'evaluation_scope', 'operand_source_kind',
    'evidence_source_ref', 'data_source_ref', 'subject_ref', 'protein_ref',
    'assayed_subject_ref', 'construct_ref', 'experiment_ref', 'partner_ref',
    'condition_ref', 'resource_context_ref',
    'reaction_ref', 'endpoint_ref', 'numerator_ref', 'denominator_ref',
    'normalization_ref', 'model_name', 'observation_unit', 'count_meaning',
    'sampling_design', 'prediction_model', 'uncertainty_kind',
    'measurement_corrections', 'target_correspondence', 'uncertainty_interpretation',
    'ratio_origin', 'budget_origin', 'independent_n', 'reported_sample_sd',
    'derived_sample_sd', 'ratio_uncertainty', 'ratio_mode', 'ratio_kind',
    'ratio_unit', 'claim_prediction', 'alternative_predictions', 'budget_basis',
    'budget_unit', 'resources_complete', 'demand', 'model_definitions',
    'comparison_member_refs', 'comparison_reduction', 'resource_definitions',
    'demand_definition', 'nominal_limiting_resource_refs')


def _nodes(value):
    if isinstance(value, Mapping):
        yield value
        version = value.get('version')
        if (value.get('axis') == 'A110' and isinstance(value.get('native_components'), Mapping)
                or isinstance(version, str) and version in _ACCOUNTING | _FBA
                or isinstance(version, str) and version in _QUALIFICATIONS
                    and isinstance(value.get('result'), Mapping)
                or value.get('component') in REACTION_COMPONENTS
                    and value.get('evaluation_scope') == 'reported_reference_reaction_constraints'
                or value.get('evaluation_scope') == 'native_reference_reaction_operands'):
            return
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _nodes(child)


def _references(value):
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _references(child)
    elif isinstance(value, str) and value.startswith('source_'):
        yield value


def _species_terms(values, species):
    """Resolve the returned species definitions; do not infer chemical names."""
    return [{**deepcopy(row),
        **({'declared_species': deepcopy(species[row['species_id']])}
           if row.get('species_id') in species else {})} for row in values]


def _chemical(row):
    wrapped = row.get('native_components')
    body = wrapped if isinstance(wrapped, Mapping) else row
    if not isinstance(body.get('version'), str) or body['version'] not in _ACCOUNTING:
        return None
    species = {item['id']: item for item in body.get('species', [])}
    reactions = []
    for reaction in body.get('reactions', []):
        result = {name: deepcopy(reaction[name]) for name in ('reaction_id',
            'entity_id', 'source_locator', 'pointer', 'accounting',
            'coefficient_interpretation', 'conditional_gibbs') if name in reaction}
        result['participants'] = _species_terms(reaction.get('participants', []), species)
        if 'signed_net_stoichiometry' in reaction:
            result['signed_net_stoichiometry'] = [
                {'species_id': name, 'signed_coefficient': value,
                 **({'declared_species': deepcopy(species[name])} if name in species else {})}
                for name, value in reaction['signed_net_stoichiometry'].items()]
        reactions.append(result)
    result = {'result': 'Saved declared chemical accounting and conditional energetics',
        **{name: deepcopy(row[name]) for name in _COMMON if name in row},
        **{name: deepcopy(body[name]) for name in ('version', 'dataset_id', 'origin',
            'selection', 'limitations') if name in body}, 'reactions': reactions}
    pathway = body.get('pathway')
    if isinstance(pathway, Mapping):
        result['declared_pathway'] = {name: deepcopy(pathway[name]) for name in
            ('steps', 'accounting', 'conditional_gibbs', 'limitation') if name in pathway}
        if 'net_species_coefficients' in pathway:
            result['declared_pathway']['net_species_coefficients'] = [
                {'species_id': name, 'signed_coefficient': value,
                 **({'declared_species': deepcopy(species[name])} if name in species else {})}
                for name, value in pathway['net_species_coefficients'].items()]
        pools = []
        for pool in pathway.get('carrier_pools', []):
            retained = {name: deepcopy(value) for name, value in pool.items() if name != 'members'}
            retained['members'] = [{'species_id': name, **deepcopy(member),
                **({'declared_species': deepcopy(species[name])} if name in species else {})}
                for name, member in pool.get('members', {}).items()]
            pools.append(retained)
        result['declared_pathway']['carrier_pools'] = pools
    if 'reported_constraints' in body:
        result['reported_constraints'] = deepcopy(body['reported_constraints'])
    return result


def _fba(row):
    wrapped = row.get('native_components')
    body = wrapped if isinstance(wrapped, Mapping) else row
    if not isinstance(body.get('version'), str) or body['version'] not in _FBA:
        return None
    return {'result': 'Delivered selected flux-balance projection',
        **{name: deepcopy(row[name]) for name in _COMMON if name in row},
        **{name: deepcopy(body[name]) for name in ('version', 'dataset_id', 'origin',
            'selection', 'projection', 'requested_projection_status',
            'native_execution_state', 'native_association', 'native_evidence_roles',
            'driver_returncode', 'diagnostics', 'software', 'limitations') if name in body}}


def _cell(row):
    if (row.get('component') not in REACTION_COMPONENTS
            or row.get('evaluation_scope') != 'reported_reference_reaction_constraints'):
        return None
    return {'result': 'Delivered experimental reaction or resource-model component',
        **{name: deepcopy(row[name]) for name in _CELL_FIELDS if name in row}}


def _operand(row):
    if row.get('evaluation_scope') != 'native_reference_reaction_operands':
        return None
    return {'result': 'Saved source-reported reaction or resource measurement',
        **{name: deepcopy(row[name]) for name in (*_CELL_FIELDS,
            'observation_position', 'measurement_ref', 'resource_ref',
            'source_number_refs', 'basis_refs', 'count_basis_refs',
            'uncertainty_basis_refs', 'count_number_ref', 'uncertainty_number_ref',
            'source_unit_ref', 'operand_role', 'reported_value', 'numerator_value',
            'denominator_value', 'source_unit', 'ratio_form', 'measurement_basis',
            'reported_count', 'count_basis', 'uncertainty_value', 'transformation') if name in row}}


def _qualification(row):
    if (not isinstance(row.get('version'), str) or row['version'] not in _QUALIFICATIONS
            or not isinstance(row.get('result'), Mapping)):
        return None
    actual = row['result']
    result = {'result': 'Saved qualification for this particular A110 evidence use',
        **{name: deepcopy(row[name]) for name in (*_COMMON, 'version',
            'qualification_kind') if name in row},
        'qualification': {name: deepcopy(actual[name]) for name in ('state', 'missing',
            'missing_components', 'required_record_refs', 'reaction_ref',
            'native_reaction', 'native_entity_identifier_matches_reference_accession',
            'component_family', 'quantity_scope', 'limitation', 'experiment_binding',
            'source_assayed_subject_ref', 'actual_reference_ref',
            'source_function_finding', 'component_correspondence',
            'measured_subject_correspondence') if name in actual}}
    if 'selected_components' in actual:
        result['qualification']['selected_components'] = [
            _cell(cell) or deepcopy(cell) for cell in actual['selected_components']]
    if 'sheet_ref' in actual:
        result['qualification']['sheet_ref'] = actual['sheet_ref']
    revision_context = {name: deepcopy(row[name]) for name in ('current',
        'changed_received_operand_refs', 'source_assessment_change_refs',
        'qualification_update_reasons') if name in row}
    if revision_context:
        result['receiver_view_revision_context'] = revision_context
    return result


def _execution(row):
    if row.get('axis') != 'A110' or not isinstance(row.get('status'), str):
        return None
    return {'result': 'Recorded A110 native execution or admission outcome',
        **{name: deepcopy(row[name]) for name in (*_COMMON, 'status', 'operation',
            'resource_id', 'failure', 'missing', 'witness_ref',
            'required_artifact_ref', 'resolved_by_received_request_ref') if name in row}}


def completed_work_result(selection, outcome, received_records):
    """Select exact own/admitted results without deriving another verdict."""
    if not isinstance(selection, Mapping) or not isinstance(outcome, Mapping):
        return None
    if selection.get('kind') == 'tool' and selection.get('tool') in {'source.read', 'source.locate'}:
        # Reading or locating source bytes does not redeliver the source's
        # complete chemical calculation. Keep the actual navigation outcome
        # in the common report and the admitted science in its receiver views.
        return None
    direct = {key: value for key, value in outcome.items() if key != 'received_axis_results'}
    original_refs = set(_references(direct))
    original_cells = {(row.get('sheet_ref'), row['component'])
        for row in _nodes(direct) if _cell(row) is not None}
    original_observations = {(row.get('sheet_ref'), row.get('measurement_ref'),
        row.get('observation_position'), row.get('operand_role'))
        for row in _nodes(direct) if _operand(row) is not None}
    related = str(selection.get('tool', '')).startswith('chemistry.') or any(
        row.get('option_id') == 'A110'
        or row.get('id') == 'A110' and row.get('slot') == 'evidence_axis'
        for row in _nodes(selection))
    results, limitations, seen = [], [], set()

    def append(row, *, received=False):
        nonlocal related
        cell = _cell(row)
        observation = _operand(row)
        if received and cell is not None and (
                row.get('sheet_ref'), row['component']) not in original_cells:
            return
        if received and observation is not None and (
                row.get('sheet_ref'), row.get('measurement_ref'),
                row.get('observation_position'), row.get('operand_role')) not in original_observations:
            return
        result = (_chemical(row) or _fba(row) or _qualification(row)
            or cell or observation or _execution(row))
        if result is None:
            return
        # A qualification's own source_ref identifies this publication; its
        # request/input sheet is not permission to use a later qualification.
        reference = row.get('source_ref') or (row.get('sheet_ref') if cell or observation else None)
        if received and (reference is None or reference not in original_refs):
            return
        related = True
        identity = ((result['result'], reference, row.get('component'),
            row.get('measurement_ref') if observation else None,
            row.get('observation_position') if observation else None,
            row.get('operand_role') if observation else None) if reference is not None
            else json.dumps(result, sort_keys=True, separators=(',', ':')))
        if identity in seen:
            return
        seen.add(identity)
        results.append(result)
        for field in ('missing', 'missing_components', 'unavailable_reason', 'failure', 'diagnostics'):
            value = result.get(field, result.get('qualification', {}).get(field))
            if value:
                limitations.append({'source_ref': reference, field: deepcopy(value)})
        for reaction in result.get('reactions', []):
            energetic = reaction.get('conditional_gibbs', {})
            for field in ('missing', 'applicability_missing'):
                if energetic.get(field):
                    limitations.append({'source_ref': reference,
                        'reaction_id': reaction['reaction_id'], field: deepcopy(energetic[field])})

    for row in _nodes(direct):
        append(row)
        if (str(selection.get('tool', '')).startswith('chemistry.request_')
                and 'new_execution_requested' in row):
            related = True
            results.append({'result': 'Recorded A110 native execution request or reuse',
                **{name: deepcopy(row[name]) for name in ('request_ref', 'commission_source_ref',
                    'execution_status', 'new_execution_requested', 'execution_owner') if name in row}})
    for row in _nodes(outcome.get('received_axis_results', ())):
        append(row, received=True)
    if not related:
        return None
    admitted = outcome.get('admitted_child_return')
    if isinstance(admitted, Mapping) and 'controller_progress' in admitted:
        results.append({'result': 'Delivered child-local investigation progress',
            'value': admitted['controller_progress'],
            'meaning': 'Child task units; receiving-parent earned credit is reported separately'})
    if not results:
        limitations.append({'reason': 'No concrete A110 numerical result or execution outcome was included in this action or its admitted resolved results'})
    return {'axis': 'A110', 'results': results, 'limitations': limitations}
