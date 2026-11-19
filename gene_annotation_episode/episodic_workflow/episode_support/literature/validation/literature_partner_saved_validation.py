"""Complete original saved partner-science validation; never rerun source reading or calculation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import BINDINGS, CHECK_REASONS, COMPONENTS, ContractError, EXPERIMENT_TYPES, FORMULA_CODES, LITERAL_FIELDS, LITERAL_REFERENCE_ROLES_VERSION, LITERAL_REFERENCE_TYPES, NATIVE_UNITS, PROVIDER, REASONS, SOURCE_KINDS, _COMPONENT_ROLES, _FIXED_METADATA, _NATIVE_ARGUMENT_SCHEMA, _NATIVE_BINDING_VERSION, _NATIVE_EVIDENCE_SCHEMA, _NATIVE_EVIDENCE_V2_SCHEMA, _NATIVE_IDENTITY_FIELDS, _ROLES, _arguments_schema, _arm_metadata_schema, _binding_record, _cell_schema, _check_schema, _checks_schema, _condition_refs, _condition_role, _direct_references, _factor_names, _factor_record, _input_schema, _metadata, _native_evidence_schema, _native_operand_projection, _native_population_schema, _native_version, _saved_check, _spread_schema, assessments, canonical, deepcopy, hashlib, identity, json, literal_reference_role, obj, partner_cells_schema, partner_population_schema, partner_source_population_schema, plain, publication, read_partner_inputs, source_literal_label, unicodedata, validate_schema

def _validate_saved(self, sheet_ref, saved):

    def require(condition):
        if not condition:
            raise ContractError('literature_partner_sheet_source_mismatch')
    source = self.store.get(sheet_ref)
    artifact = self.store.get(source['artifact_ref'])
    require(hashlib.sha256(canonical(saved).encode()).hexdigest() == artifact['sha256'])
    request = json.loads(self.store.get_artifact(source['request_ref']))
    require(set(request) == {'operation_key', 'arguments', 'scope'})
    args, extraction = (request['arguments'], saved['extraction'])
    assessment = args.get('experiment_assessment')
    assessments.validate_saved_assessment(self, saved, request, sheet_ref)
    validate_schema(args, _arguments_schema(args))
    marked = 'native_operand_bindings' in saved
    require(saved.get('literal_reference_roles_version') == LITERAL_REFERENCE_ROLES_VERSION)
    require(set(saved) == {'version', 'input_source_ref', 'input_artifact_ref', 'input_source_refs', 'direct_input_source_refs', 'data_source_ref', 'extraction', 'experimental_bindings', 'factor_bindings', 'sheet'} | ({'native_operand_bindings'} if marked else set()) | {'literal_reference_roles_version'} | ({'experiment_assessment'} if assessment is not None else set()))
    require(source['version'] == self.record_version and source['text_ref'] == source['artifact_ref'])
    native = args.get('input_mode') == 'native_source_spans'
    require(extraction['version'] == (_native_version(args) if native else 'literature_partner_inputs_extraction_v1') and extraction['arguments'] == args)
    require(set(extraction) == {'version', 'arguments', 'sources', 'literals', 'interpretations', 'recipe', 'calculation', 'cells'} | ({'native_evidence'} if native else set()))
    recipe = extraction['recipe']
    require(set(recipe) == {'version', 'inputs'} and recipe['version'] == 'literature_partner_selection_v1')
    validate_schema(recipe['inputs'], _input_schema())
    calculation = extraction['calculation']
    require(set(calculation) == {'version', 'inputs', 'cells', 'comparison_checks'})
    require(calculation['version'] == 'literature_partner_components_v1' and calculation['inputs'] == recipe['inputs'])
    require(calculation['cells'] == extraction['cells'])
    if native:
        self._validate_native_saved(args, extraction['native_evidence'], recipe['inputs'], version=extraction['version'])
    validate_schema(calculation['comparison_checks'], _checks_schema(raw=True))
    self._validate_scientific_saved(recipe['inputs'], calculation, args)
    direct = _direct_references(args)
    require(saved['direct_input_source_refs'] == direct)
    require(isinstance(extraction['sources'], list) and len(extraction['sources']) == len(direct) and (set(extraction['sources']) == set(direct)))
    require(saved['input_source_refs'] == self._parents(request['scope'], list(dict.fromkeys([*direct, *self._assessment_sources(assessment)]))))
    require(saved['input_artifact_ref'] == self.store.get(args['source_ref'])['artifact_ref'] and saved['data_source_ref'] == args['data_source_ref'])

    def witness(value):
        row = self.store.get(value['source_ref'])
        artifact = row['artifact_ref'] if value['representation'] == 'original' else row['text_ref']
        return {**value, 'artifact_ref': artifact}
    require(set(extraction['literals']) == set(LITERAL_FIELDS))
    for literal in LITERAL_FIELDS:
        selected = args['literals'][literal]
        expected = {'value': selected['quote'], 'witness': witness(selected)} if selected else None
        require(extraction['literals'][literal] == expected)
    require(extraction['interpretations'] == [witness(entry) for entry in args['interpretation_witnesses']])
    native_records = None
    native_common, interpretation = ({}, extraction['literals'])
    if marked:
        require(native)
        projection, native_records, native_common, interpretation = _native_operand_projection(extraction)
        require(saved['native_operand_bindings'] == projection)
        for reference, (kind, record) in native_records.items():
            require(self.store.get(reference) == {'id': reference, 'record_type': kind, 'origin': 'tool', **record})
    require(set(saved['experimental_bindings']) == set(BINDINGS))
    for field, (literal, kind) in BINDINGS.items():
        entry, reference = (extraction['literals'][literal], saved['experimental_bindings'][field])
        if field == 'experiment_ref' and assessment is not None:
            require(reference == assessment['experiment_ref'])
            continue
        if field in native_common:
            require(reference == native_common[field])
            continue
        if entry is None:
            require(reference is None)
        else:
            record = _binding_record(literal, kind, entry)
            require(reference == identity(kind, {'origin': 'tool', 'record': record}))
            require(self.store.get(reference) == {'id': reference, 'record_type': kind, 'origin': 'tool', **record})
            if kind == 'context':
                role = _condition_role(literal, entry)
                role_ref = record['related_refs'][0]
                require(self.store.get(role_ref) == {'id': role_ref, 'record_type': 'reference', 'origin': 'tool', **role})
    factors = saved['factor_bindings']
    require(isinstance(factors, dict) and sorted(factors) == _factor_names(extraction))
    for name in sorted(factors):
        record = _factor_record(args['data_source_ref'], name)
        reference = factors[name]
        require(reference == identity('term', {'origin': 'tool', 'record': record}))
        require(self.store.get(reference) == {'id': reference, 'record_type': 'term', 'origin': 'tool', **record})
    require(set(saved['sheet']) == {'cells'} and saved['sheet']['cells'] == extraction['cells'])
    require(set(extraction['cells']) == set(COMPONENTS))

def _validate_native_saved(self, args, evidence, inputs, *, version=None):
    """Check frozen native-selector relationships without parsing again.

        Numerical conversions were committed by the original selected reader.
        Replay verifies their ownership/representation and copies their saved
        canonical values. It neither reacquires source bytes nor evaluates a
        number, unit conversion, scientific interpretation or core formula.
        """

    def require(condition):
        if not condition:
            raise ContractError('literature_partner_sheet_source_mismatch')
    expected_version = _native_version(args)
    require(version is None or version == expected_version)
    validate_schema(evidence, _NATIVE_EVIDENCE_V2_SCHEMA if expected_version.endswith('_v2') else _NATIVE_EVIDENCE_SCHEMA)

    def witness(selected, actual):
        if selected is None:
            require(actual is None)
            return
        source = self.store.get(selected['source_ref'])
        require(source['record_type'] == 'source')
        artifact = source['artifact_ref'] if selected['representation'] == 'original' else source['text_ref']
        require(actual == {**selected, 'artifact_ref': artifact})
        require(artifact is not None)
        metadata = self.store.get(artifact)
        require(0 <= selected['start'] < selected['end'] <= metadata['size'])

    def number(selected, actual, *, rate=False, condition=False):
        witness(selected['witness'], actual['selector']['witness'])
        require(actual['selector'] == {**selected, 'witness': actual['selector']['witness']})
        start, end = (selected['number_start'], selected['number_end'])
        quote = selected['witness']['quote']
        require(0 <= start < end <= len(quote) and actual['raw_number'] == quote[start:end])
        require(condition or actual['value'] >= 0)
        if not rate:
            require(actual['relation'] == 'point')

    def contained(parent, child):
        require(all((parent[field] == child[field] for field in ('source_ref', 'artifact_ref', 'representation'))))
        require(parent['start'] <= child['start'] < child['end'] <= parent['end'])
        raw = parent['quote'].encode('utf-8')
        require(raw[child['start'] - parent['start']:child['end'] - parent['start']] == child['quote'].encode('utf-8'))

    def source_text(value):
        return ' '.join(unicodedata.normalize('NFKC', value).split())

    def whole_entity(parent, child):
        contained(parent, child)
        raw = parent['quote'].encode('utf-8')
        before = raw[:child['start'] - parent['start']].decode('utf-8')[-1:]
        after = raw[child['end'] - parent['start']:].decode('utf-8')[:1]
        require(not before or not (before.isalnum() or before == '_'))
        require(not after or not (after.isalnum() or after == '_'))

    def rate_unit(selected, actual, endpoint):
        if selected.get('kind') != 'source_defined_rate_unit':
            require('definition' not in actual)
            witness(selected, actual['witness'])
            require(actual['raw_unit'] == selected['quote'])
            allowed = {'pmol/min/mg': (1, 1000, 1000000), 'per_min': (1, 60), 'uM/min': (1, 0.001)}
            require(actual['multiplier'] in allowed[actual['canonical_unit']])
            return
        require('definition' in actual and endpoint is not None)
        witness(selected['witness'], actual['witness'])
        require(actual['raw_unit'] == selected['witness']['quote'])
        require(''.join(actual['raw_unit'].split()) == 'U/mg')
        require(actual['canonical_unit'] == 'pmol/min/mg' and actual['multiplier'] > 0)
        chosen, found = (selected['definition'], actual['definition'])
        for field in ('bridge', 'clause', 'amount_unit', 'time_unit', 'endpoint', 'endpoint_entity', 'definition_entity'):
            witness(chosen[field], found[field])
        number(chosen['amount'], found['amount'])
        require(found['amount']['value'] > 0 and found['endpoint'] == endpoint)
        contained(found['bridge'], found['clause'])
        selection = found['amount']['selector']
        amount_witness = selection['witness']
        contained(found['bridge'], amount_witness)
        start, end = (selection['number_start'], selection['number_end'])
        contained(found['clause'], {**amount_witness, 'start': amount_witness['start'] + len(amount_witness['quote'][:start].encode('utf-8')), 'end': amount_witness['start'] + len(amount_witness['quote'][:end].encode('utf-8')), 'quote': amount_witness['quote'][start:end]})
        for field in ('amount_unit', 'time_unit', 'definition_entity'):
            contained(found['clause'], found[field])
        whole_entity(found['endpoint'], found['endpoint_entity'])
        whole_entity(found['clause'], found['definition_entity'])
        require(source_text(found['endpoint_entity']['quote']) == source_text(found['definition_entity']['quote']))
        require(source_text(found['amount_unit']['quote']).replace('µ', 'u').replace('μ', 'u') in ('pmol', 'nmol', 'umol'))
        require(source_text(found['time_unit']['quote']) in ('min', 'minute', 's', 'second'))
    for role in _ROLES:
        selected, actual, core = (args['arms'][role], evidence[role], inputs['arms'][role])
        if selected is None:
            require(actual is None and core is None)
            continue
        require(actual is not None and core is not None)
        require(actual['origin'] == selected['origin'] == core['measurement']['origin'])
        require(actual['partner_state'] == selected['partner_state'] == core['partner_state'])
        for field in ('subject', 'partner', 'endpoint', 'normalization', 'measurement_identity'):
            witness(selected[field], actual[field])
            name = 'measurement_id' if field == 'measurement_identity' else field + '_ref'
            target = core['measurement'] if field == 'measurement_identity' else core
            namespace = 'partner_native_measurement' if field == 'measurement_identity' else 'partner_native_' + field
            require(target[name] == (identity(namespace, actual[field]) if actual[field] else None))
        conditions = actual['conditions']
        require(conditions['coverage'] == selected['conditions']['coverage'] == core['conditions']['coverage'])
        require(len(conditions['factors']) == len(selected['conditions']['factors']) == len(core['conditions']['factors']))
        for chosen, found, normalized in zip(selected['conditions']['factors'], conditions['factors'], core['conditions']['factors']):
            require(chosen['factor'] == found['factor'] == normalized['factor'])
            level, parsed = (chosen['level'], found['level'])
            if level is None:
                require(parsed is None and normalized['level'] is None and (normalized['unit'] == 'unreported'))
            elif level['kind'] == 'literal':
                require(parsed['kind'] == 'literal')
                witness(level['witness'], parsed['witness'])
                require(normalized['level'] == parsed['witness']['quote'] and normalized['unit'] == 'source_literal')
            else:
                require(parsed['kind'] == 'number')
                number(level['selector'], parsed['selector'], condition=True)
                witness(level['unit_witness'], parsed['unit_witness'])
                require(normalized['level'] == parsed['selector']['value'])
                require(normalized['unit'] == (parsed['unit_witness']['quote'] if parsed['unit_witness'] else 'dimensionless'))
        rate, parsed = (selected['rate'], actual['rate'])
        if rate is None:
            require(parsed is None and core['unit'] == 'unreported')
            require(core['measurement']['status'] == 'unreported' and core['measurement']['value'] is None)
            require(core['measurement']['spread'] == {'kind': 'unreported', 'magnitude': None})
            continue
        require(parsed is not None)
        number(rate['value'], parsed['value'], rate=True)
        rate_unit(rate['unit'], parsed['unit'], actual['endpoint'])
        require(core['unit'] == parsed['unit']['canonical_unit'])
        require(core['measurement']['value'] == parsed['canonical_value'])
        require(core['measurement']['status'] == ('observed' if parsed['value']['relation'] == 'point' else 'upper_bound'))
        spread, found = (rate['spread'], parsed['spread'])
        require(spread['kind'] == found['kind'] == core['measurement']['spread']['kind'])
        if spread['unit'] is None:
            require(found['unit'] is None)
        else:
            rate_unit(spread['unit'], found['unit'], actual['endpoint'])
            require(found['unit']['canonical_unit'] == parsed['unit']['canonical_unit'])
        require(len(spread['witnesses']) == len(found['witnesses']))
        for chosen, actual_basis in zip(spread['witnesses'], found['witnesses']):
            witness(chosen, actual_basis)
        require(spread['kind'] not in ('SD', 'SEM', 'CI') or bool(spread['witnesses']))
        if spread['magnitude'] is None:
            require(spread['kind'] == 'unreported' and spread['unit'] is None and (found['magnitude'] is None) and (parsed['canonical_spread'] is None))
        else:
            require(spread['kind'] != 'unreported')
            number(spread['magnitude'], found['magnitude'])
        require(core['measurement']['spread']['magnitude'] == parsed['canonical_spread'])

def _validate_scientific_saved(self, inputs, calculation, args):
    """Validate frozen structures/meanings, never rerun a numerical formula."""

    def require(condition):
        if not condition:
            raise ContractError('literature_partner_sheet_source_mismatch')
    arms = inputs['arms']
    seen = {}
    for role, arm in arms.items():
        if arm is None:
            continue
        for field in ('subject_ref', 'partner_ref', 'endpoint_ref', 'normalization_ref'):
            require(arm[field] is None or bool(arm[field].strip()))
        factors = arm['conditions']['factors']
        names = [factor['factor'] for factor in factors]
        require(len(names) == len(set(names)))
        for factor in factors:
            require(bool(factor['factor'].strip()) and bool(factor['unit'].strip()))
            require(not isinstance(factor['level'], str) or bool(factor['level'].strip()))
        coverage = arm['conditions']['coverage']
        require(coverage != 'unreported' or not factors)
        require(coverage != 'complete' or (bool(factors) and all((f['level'] is not None for f in factors))))
        measurement = arm['measurement']
        require(measurement['measurement_id'] is None or bool(measurement['measurement_id'].strip()))
        require((measurement['status'] == 'unreported') == (measurement['value'] is None))
        require(arm['unit'] != 'unreported' or measurement['status'] == 'unreported')
        spread = measurement['spread']
        require((spread['kind'] == 'unreported') == (spread['magnitude'] is None))
        if args['source_kind'] == 'synthetic_fixture':
            require(measurement['origin'] == 'synthetic')
        key = measurement['measurement_id']
        if key is not None:
            signature = (measurement['value'], measurement['status'], arm['unit'])
            require(key not in seen or seen[key] == signature)
            seen[key] = signature
    require(bool(args['interpretation_witnesses']) or not any((arm is not None and arm['conditions']['coverage'] == 'complete' for arm in arms.values())))
    pairs = {'reference_omitted': (arms['reference'], arms['omitted']), 'addback_omitted': (arms['addback'], arms['omitted'])}
    for name, check in calculation['comparison_checks'].items():
        require(check == _saved_check(*pairs[name]))
    cells = calculation['cells']
    require(set(cells) == set(COMPONENTS))
    for name, cell in cells.items():
        validate_schema(cell, _cell_schema())
        if cell['status'] == 'unavailable':
            require(cell['unavailable_reason'] is not None and all((cell[field] is None for field in ('value', 'lower', 'upper'))))
        elif cell['status'] == 'bounded':
            require(cell['value'] is None and cell['lower'] is not None and (cell['upper'] is not None) and (cell['lower'] <= cell['upper']) and (cell['unavailable_reason'] == 'censored_point_unreported') and (cell['bound_kind'] == 'conditional_input_domain_not_CI'))
        else:
            require(cell['unavailable_reason'] is None and all((cell[field] is not None for field in ('value', 'lower', 'upper'))) and (cell['lower'] <= cell['value'] <= cell['upper']))
        if name in COMPONENTS[3:]:
            require(cell['origin'] == 'derived')
            if name in ('partner_loss_fraction', 'addback_fraction', 'restored_reference_fraction'):
                require(cell['unit'] == 'dimensionless')
    w, o, a = (arms[role] for role in _ROLES)
    checks = calculation['comparison_checks']
    loss_reason = checks['reference_omitted']['unavailable_reason']
    gain_reason = checks['addback_omitted']['unavailable_reason']
    if w is not None and a is not None:
        wk, ak = (arm['measurement']['measurement_id'] for arm in (w, a))
        if wk is not None and wk == ak:
            gain_reason = 'role_measurement_not_distinct'
    triple_reason = loss_reason or gain_reason

    def unit(arm):
        return None if arm is None or arm['unit'] == 'unreported' else arm['unit']
    for name, roles, prerequisite, expected_unit, allowed in (('partner_loss', (w, o), loss_reason, unit(w) if unit(w) == unit(o) else None, ('numerical_model_range',)), ('partner_loss_fraction', (w, o), loss_reason, 'dimensionless', ('numerical_model_range', 'nonpositive_reference_domain')), ('addback_gain', (a, o), gain_reason, unit(a) if unit(a) == unit(o) else None, ('numerical_model_range',)), ('addback_fraction', (w, o, a), triple_reason, 'dimensionless', ('numerical_model_range', 'zero_or_straddling_loss_domain')), ('restored_reference_fraction', (w, o, a), triple_reason, 'dimensionless', ('numerical_model_range', 'nonpositive_reference_domain'))):
        cell = cells[name]
        require(cell['unit'] == expected_unit and cell['origin'] == 'derived')
        missing = prerequisite or ('measurement_unreported' if any((arm is None or arm['measurement']['status'] == 'unreported' for arm in roles)) else None)
        if missing:
            require(cell['status'] == 'unavailable' and cell['unavailable_reason'] == missing and (cell['bound_kind'] == 'point_only_not_uncertainty'))
        else:
            require(cell['status'] != 'unavailable' or cell['unavailable_reason'] in allowed)
            expected_kind = 'conditional_input_domain_not_CI' if any((arm['measurement']['status'] == 'upper_bound' for arm in roles)) and cell['unavailable_reason'] not in ('nonpositive_reference_domain', 'zero_or_straddling_loss_domain') else 'point_only_not_uncertainty'
            require(cell['bound_kind'] == expected_kind)
    for role, name in zip(_ROLES, COMPONENTS[:3]):
        arm, cell = (arms[role], cells[name])
        if arm is None:
            require(cell == {'value': None, 'lower': None, 'upper': None, 'unit': None, 'origin': None, 'bound_kind': 'point_only_not_uncertainty', 'status': 'unavailable', 'unavailable_reason': 'arm_unreported'})
            continue
        measurement = arm['measurement']
        require(cell['origin'] == measurement['origin'] and cell['unit'] == (None if arm['unit'] == 'unreported' else arm['unit']))
        if measurement['status'] == 'observed':
            require(cell['status'] == 'populated' and cell['value'] == cell['lower'] == cell['upper'] == measurement['value'] and (cell['bound_kind'] == 'point_only_not_uncertainty'))
        elif measurement['status'] == 'upper_bound':
            require(cell['status'] == 'bounded' and cell['lower'] == 0 and (cell['upper'] == measurement['value']))
        else:
            require(cell['status'] == 'unavailable' and cell['unavailable_reason'] == 'measurement_unreported' and (cell['bound_kind'] == 'point_only_not_uncertainty'))
