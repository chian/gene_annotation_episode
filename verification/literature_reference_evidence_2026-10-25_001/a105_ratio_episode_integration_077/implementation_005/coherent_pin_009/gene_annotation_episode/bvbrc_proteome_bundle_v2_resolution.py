"""Resolve selected retained documents, then run the real pure producers once.

Tools do tasks. Episodes are problem solving processes. This module chooses no
resource, acquisition, retry or next action and supplies no independent credit.
"""
from collections import Counter
from copy import deepcopy
import hashlib

from . import bvbrc_proteome_bundle_v2_contracts as c
from . import bvbrc_proteome_bundle_resolution as legacy
from .bvbrc_appservice_contracts import ContractValidationError, validate_contract
from .bvbrc_proteome_directional import parse_genome_comparison_directional_report
from .bvbrc_proteome_directional_contracts import validate_directional_report
from .bvbrc_proteome_directional_sheet import build_directional_sheet
from .bvbrc_proteome_directional_calculators import calculate_directional_components
from .bvbrc_proteome_numerical_sheet import build_proteome_numerical_sheet


def selected_members(bundle, selection):
    if 'requirement_id' in selection:
        return [a for a in bundle['artifacts'] if selection['requirement_id'] in a.get('requirement_ids', [])]
    return [a for a in bundle['artifacts'] if a['source_ref'] == selection['source_ref'] and
            a['raw_artifact_ref'] == selection['raw_artifact_ref']]


class _ResolutionV2(legacy._Resolution):
    def __init__(self, *args):
        super().__init__(*args)
        self.directional_results = []

    def problem(self, code, path, *, refs=(), severity='qualification', row=None):
        if code not in c.DIRECTIONAL_BINDING_CODES:
            return super().problem(code, path, refs=refs, severity=severity, row=row)
        kind, role, phase = c.DIRECTIONAL_BINDING_DETAILS[code]
        refs = list(dict.fromkeys(refs))
        selection = None if row is None else {k: row[k] for k in ('selector_kind','selection_index')}
        payload = dict(version='bvbrc_proteome_requirement_v1', analysis_id=self.parameters['analysis_id'],
            reason_code=code, role=role, field=None, selection=selection, source_refs=refs, pure_requirement=None)
        req = dict(requirement_id='proteome_requirement_' + c.digest(payload), kind=kind, role=role,
                   source_refs=refs, reason_code=code)
        self.requirements = legacy._unique([*self.requirements, req])
        self.diagnostics = legacy._unique([*self.diagnostics, dict(code=code, phase=phase, path=path,
            severity=severity, evidence_refs=refs)])
        if row is not None and req['requirement_id'] not in row['requirement_ids']:
            row['requirement_ids'].append(req['requirement_id'])
        return req

    def documents(self):
        selections = [('native_document', i, s) for i, s in enumerate(self.parameters['native_documents'])]
        selections += [('directional_document', i, s) for i, s in enumerate(self.parameters['directional_documents'])]
        memberships = [selected_members(self.bundle, s) for _, _, s in selections]
        counts = Counter(m[0]['source_ref'] for m in memberships if len(m) == 1)
        for (kind, i, selected), members in zip(selections, memberships):
            group = 'native_documents' if kind == 'native_document' else 'directional_documents'
            path, row = f'/parameters/{group}/{i}', self.outcome(kind, i)
            if len(members) == 1 and counts[members[0]['source_ref']] > 1:
                row['state'] = 'invalid'
                self.problem('proteome_directional_duplicate_document_selection', path,
                    refs=[members[0]['source_ref']], severity='error', row=row)
                continue
            if kind == 'directional_document':
                self.directional_document(selected, members, row, path)
                continue
            declaration, contract = selected['declared_format'], selected['source_contract']
            refs = [members[0]['source_ref']] if len(members) == 1 else []
            if declaration['format'] not in legacy._FORMATS or declaration['version'] is not None or declaration['mode'] is not None:
                row['state'] = 'incompatible'
                self.problem('artifact_format_incompatible', path + '/declared_format', refs=refs, severity='error', row=row)
                continue
            if contract['deployment_match'] != 'unobserved':
                row['state'] = 'incompatible' if contract['deployment_match'] == 'different' else 'unverified'
                self.problem('source_contract_incompatible' if contract['deployment_match'] == 'different' else 'deployment_evidence_unverified',
                    path + '/source_contract', refs=refs, severity='error' if contract['deployment_match'] == 'different' else 'qualification', row=row)
                continue
            raw, source = self.artifact(selected.get('source_ref'), selected.get('raw_artifact_ref'), path, row,
                declared=declaration, role=selected['role'], requirement_id=selected.get('requirement_id'))
            if raw is None: continue
            result = legacy.parse_genome_comparison(raw, source=source, declared_format=declaration['format'], source_contract=contract)
            row['result_index'] = len(self.native_results)
            self.native_results.append(result)
            self.record(result, row, f'/native_results/{row["result_index"]}', 'proteome_native_projection')

    def directional_document(self, selected, members, row, path):
        def fail(code, state, refs=()):
            row['state'] = state
            self.problem('proteome_directional_' + code, path, refs=refs,
                         severity='qualification' if state == 'missing' else 'error', row=row)
        if len(members) != 1:
            near = [] if 'requirement_id' in selected else [a for a in self.bundle['artifacts'] if
                a['source_ref'] == selected['source_ref'] or a['raw_artifact_ref'] == selected['raw_artifact_ref']]
            fail('document_ambiguous' if members else 'artifact_binding_conflict' if near else 'document_missing',
                 'invalid' if members or near else 'missing', [a['source_ref'] for a in members + near])
            return
        member = members[0]
        content = row['content'] = legacy._content(member)
        refs = [content['source_ref']]
        if member['role'] != selected['role']:
            fail('artifact_binding_conflict', 'invalid', refs)
            return
        if member['declared_format'] != selected['declared_format']:
            fail('format_incompatible', 'incompatible', refs)
            return
        transfer, observed = member['transfer'], member['transfer']['observed_range']
        if observed is not None and observed['start'] != 0 or (observed is None and transfer['object_complete'] != 'yes' and
                transfer['requested_range'] is not None and transfer['requested_range'][0] != 0):
            fail('nonzero_range_unsupported', 'incompatible', refs)
            return
        raw = self.raw.get(content['artifact_ref'])
        if raw is None:
            fail('document_missing', 'missing', refs)
            return
        if type(raw) is not bytes or len(raw) != content['byte_count'] or hashlib.sha256(raw).hexdigest() != content['sha256']:
            fail('artifact_digest_mismatch', 'invalid', refs)
            return
        if not self.register(content, path, row, code='proteome_directional_artifact_binding_conflict'):
            return
        source = dict(content=deepcopy(content), body_complete=transfer['body_complete'], object_complete=transfer['object_complete'])
        try:
            result = parse_genome_comparison_directional_report(raw, source=source,
                declared_format=selected['declared_format']['format'], report_key=selected['report_key'])
            result = validate_directional_report(result)
            c._require(result['source'] == source and result['report_key'] == selected['report_key'] and
                result['declared_format'] == selected['declared_format']['format'])
        except ValueError:
            fail('reader_contract_invalid', 'invalid', refs)
            return
        row['result_index'] = len(self.directional_results)
        self.directional_results.append(result)
        row['state'] = {'ok':'resolved','partial':'partial','failure':'invalid'}[result['parse_state']]
        if c.declaration_conflict(result, selected):
            fail('declared_version_conflict', 'incompatible', refs)


def _construct_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    """Private construction port, consumed by the facade's actual F projection."""
    try:
        bundle = validate_contract('ArtifactBundle', bundle)
    except ContractValidationError as error:
        code = 'proteome_original_task_conflict' if error.code == 'original_task_mismatch' else 'proteome_bundle_invalid'
        raise c.ProteomeBundleV2Error(code, c.legacy._error_path(error)) from error
    try:
        c.canonical(bundle).encode('utf-8')
    except (ValueError, UnicodeError, RecursionError) as error:
        raise c.ProteomeBundleV2Error('proteome_bundle_invalid', '/bundle') from error
    parameters = c.validate_parameters_v2(parameters)
    form = c.validate_form_parameters(requested_form, parameters)
    task = bundle['original_task']
    c._require(task['required_application_id'] == task['native_application_id'] == 'GenomeComparison', 'proteome_application_mismatch', '/original_task')
    c._require(type(artifact_bytes) is dict and all(type(k) is str and k and type(v) is bytes for k,v in artifact_bytes.items()), 'proteome_bundle_invalid', '/artifact_bytes')
    c._require(type(supplied_values) is list, 'proteome_supplied_data_invalid', '/supplied_values')
    for i, value in enumerate(supplied_values):
        c.legacy.validate_shape('SuppliedValue', value, code='supplied_data_invalid', path=f'/supplied_values/{i}')
    c._require([r['evidence'] for r in supplied_values] == bundle['supplied_scientific_metadata'], 'proteome_supplied_source_conflict', '/supplied_values')
    supplied_values = deepcopy(supplied_values)
    resolution = _ResolutionV2(bundle, artifact_bytes, supplied_values, parameters, form)
    resolution.documents()
    primary = resolution.primary() if parameters['native_documents'] else None
    supplied = resolution.supplementary()
    if supplied is not None:
        resolution.inputs(supplied, primary)
        resolution.link_conflicts(supplied, primary)
    data = {name: [r['value'] for r in getattr(resolution, result_name) if r['value'] is not None]
        for name, _, result_name, _, _ in legacy._INPUTS}
    data['input_index'] = None if resolution.input_index_result is None else resolution.input_index_result['value']
    joins = native_sheet = native_components = None
    if primary is not None:
        joins = legacy.build_native_joins(primary, **data,
            execution_links=supplied['execution_links'] if supplied else [], native_links=supplied['native_links'] if supplied else [],
            metadata_links=supplied['metadata_links'] if supplied else [])
        resolution.pure(joins, '/joins_result', role='proteome_native_projection')
        native_sheet = legacy.build_native_sheet(resolution.native_results, primary_source_ref=primary['source']['content']['source_ref'],
            **data, joins=joins['value'], representation_links=supplied['representation_links'] if supplied else [], directional_attachment=None)
        resolution.pure(native_sheet, '/native_sheet_result', role='proteome_native_projection')
        if native_sheet['value'] is not None:
            native_components = legacy.calculate_native_components(native_sheet['value'], parameters=parameters['calculation_parameters'])
            resolution.pure(native_components, '/components/legacy', role='proteome_native_projection')
    observed = directional = None
    if parameters['directional_documents']:
        observed = build_directional_sheet(resolution.directional_results)
        c.validate_shape_v2('DirectionalDirectionalSheetResult', observed, code='proteome_directional_sheet_construction_failed')
        if observed['sheet'] is None:
            resolution.problem('proteome_directional_sheet_construction_failed', '/directional_sheet_result', severity='error')
        else:
            # C performs full A/B producer validation before returning. Do not
            # invoke that component validator a second time at this boundary.
            directional = calculate_directional_components(observed['sheet'], parameters=parameters['directional_calculation_parameters'])
            c.validate_shape_v2('DirectionalDirectionalComponentsResult', directional, code='proteome_directional_calculation_failed')
            if directional['components'] is None:
                resolution.problem('proteome_directional_calculation_failed', '/components/directional', severity='error')
    old_value = None if native_sheet is None else native_sheet['value']
    new_value = None if observed is None else observed['sheet']
    numerical = None if old_value is None and new_value is None else build_proteome_numerical_sheet(legacy_sheet=old_value, directional_sheet=new_value)
    saved = dict(version='bvbrc_proteome_provider_sheet_v2', analysis_id=parameters['analysis_id'], original_task=task,
        parameters=parameters, requested_form=form, bundle_sha256=c.digest(bundle), supplied_values=supplied_values,
        input_resolution=resolution.outcomes, native_results=resolution.native_results, input_index_result=resolution.input_index_result,
        inventory_results=resolution.inventory_results, feature_results=resolution.feature_results, genome_results=resolution.genome_results,
        sequence_results=resolution.sequence_results, joins_result=joins, native_sheet_result=native_sheet,
        requirements=resolution.requirements, diagnostics=resolution.diagnostics, directional_results=resolution.directional_results,
        directional_sheet_result=observed, numerical_sheet=numerical)
    components = None if native_components is None and directional is None else dict(
        version='bvbrc_proteome_provider_components_v2', provider_sheet_sha256=c.digest(saved), legacy=native_components, directional=directional)
    saved, components = c.validate_saved_provider_v2(saved, components, parameters=parameters, requested_form=form,
        original_task=task, bundle_sha256=c.digest(bundle), bundle=bundle)
    return dict(sheet=saved, components=components, missing_requirements=tuple(saved['requirements']), diagnostics=tuple(saved['diagnostics']))


__all__ = []
