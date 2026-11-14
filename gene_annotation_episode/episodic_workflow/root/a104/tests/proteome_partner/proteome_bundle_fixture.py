from copy import deepcopy
import hashlib
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a104.library import bvbrc_proteome_bundle_contracts as c
from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_fact_contracts import requested_form_schema
ROOT = Path(__file__).parent
SOURCE = ROOT / 'fixtures/proteome_data_contracts/construction_example_001'

def binding(raw, name):
    return dict(source_ref=name, artifact_field='artifact_ref', artifact_ref=name, sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))

def declaration(fmt):
    return dict(format=fmt, version=None, mode=None, producer_source_ref=None, transformation_evidence=[])

def member(raw, name='synthetic-native', fmt='genome_comparison_json_v1', role='proteome_native_projection'):
    content = binding(raw, name)
    return dict(role=role, source_ref=name, raw_artifact_ref=name, sha256=content['sha256'], byte_count=len(raw), workspace_object=dict(path='/synthetic/' + name, uuid='uuid-' + name, type='json', metadata_receipt_ref='metadata-' + name), task_association=dict(kind='task_result_manifest', evidence_ref='synthetic-manifest', pointer='/output_files/0', task_id='synthetic-task', output_path='/synthetic/' + name, output_uuid='uuid-' + name, byte_version_status='unknown', version_evidence=[]), transfer=dict(receipt_ref='receipt-' + name, body_complete=True, requested_range=None, observed_range=None, total_size=len(raw), object_complete='yes'), declared_format=declaration(fmt))

def form(include_missing=False):
    selections = {'identity_mean': dict(kind='measurement', target='summary', track_key='comp_genome_2', summary='first_hsp_identity_summary', metric='mean'), 'endpoint_mean': dict(kind='measurement', target='summary', track_key='comp_genome_2', summary='subject_endpoint_difference_summary', metric='mean'), 'selected': dict(kind='measurement', target='selection_count', track_key='comp_genome_2', metric='pass'), 'zero_identity': dict(kind='measurement', target='association', association_key='comp_genome_2/row/1', metric='first_hsp_alignment_identity_percent')}
    if include_missing:
        selections['executed_reference_count'] = dict(kind='measurement', target='track_count', track_key='comp_genome_2', metric='reference_input_record_count')
    return requested_form_schema(selections)

def fixture(*, supplementary=True, effective=True):
    source = json.loads((SOURCE / 'SUPPLIED_VALUES.json').read_text())
    task = json.loads((SOURCE / 'SYNTHETIC_ORIGINAL_TASK.json').read_text())
    native_raw = (SOURCE / 'input_000.bin').read_bytes()
    artifact = member(native_raw)
    raw = {artifact['raw_artifact_ref']: native_raw}
    bundle = dict(version='bvbrc_appservice_artifact_bundle_v1', original_task=task, artifacts=[artifact], input_bindings=[], query_bindings=[], supplied_scientific_metadata=[], supplied_contents=[], acquisition_receipt_refs=[artifact['transfer']['receipt_ref']], requested_selector_sha256='1' * 64, status='ok', missing_requirements=[], diagnostics=[])
    parameters = dict(version='bvbrc_proteome_bundle_parameters_v1', analysis_id='synthetic-proteome-provider', native_documents=[dict(document_id='native', source_ref=artifact['source_ref'], raw_artifact_ref=artifact['raw_artifact_ref'], role='proteome_native_projection', declared_format=deepcopy(artifact['declared_format']), source_contract=source['native']['source_contract'])], primary_document_id='native', supplied_data_evidence=None, calculation_parameters=dict(version='bvbrc_proteome_native_parameters_proposal_v1', track_keys=['comp_genome_2'], minimum_identity_fraction=0.6, minimum_subject_endpoint_difference_fraction=0.7, allowed_hit_categories=None))
    values = []
    if supplementary:
        supplied = dict(version='bvbrc_proteome_supplied_data_v1', original_input_index=None, inventories=[], feature_snapshots=[], genome_snapshots=[], sequence_snapshots=[], execution_links=source['execution_links'], native_links=source['native_links'], metadata_links=source['metadata_links'], representation_links=[])
        parameter_raw = (SOURCE / 'input_001.bin').read_bytes()
        parameter_content = binding(parameter_raw, 'synthetic-effective-parameters' if effective else task['submission_source_ref'])
        raw[parameter_content['artifact_ref']] = parameter_raw
        bundle['supplied_contents'].append(parameter_content)
        parameter_evidence = dict(content=parameter_content, pointer='/parameters')
        if effective:
            task['effective_parameters'] = dict(value=deepcopy(task['submitted_parameters']), evidence=parameter_evidence)
            values.append(dict(evidence=parameter_evidence, value=deepcopy(task['submitted_parameters'])))
        supplied['original_input_index'] = dict(mode='construct', parameter_source=dict(kind='effective' if effective else 'submitted', source_field=dict(source_ref=parameter_content['source_ref'], sha256=parameter_content['sha256'], pointer='/parameters', row_ordinal=None, field_name=None)), additional_parameter_sources=[])
        for i, inventory in enumerate(source['inventories']):
            raw_input = (SOURCE / f'input_{i + 2:03d}.bin').read_bytes()
            content = deepcopy(inventory['source']['content'])
            raw[content['artifact_ref']] = raw_input
            bundle['supplied_contents'].append(content)
            index = 1 if i == 0 else 2
            input_binding = dict(binding_id='input-' + inventory['inventory_key'], parameter_pointer=f'/user_genomes/{index}', kind='retained_bytes', content=content, workspace_path=task['submitted_parameters']['user_genomes'][index], inline_value=None, link_evidence=None, members=[])
            bundle['input_bindings'].append(input_binding)
            supplied['inventories'].append(dict(mode='raw', inventory_key=inventory['inventory_key'], declared_format=inventory['format'], source=dict(kind='original_retained_input', input_binding_id=input_binding['binding_id'])))
        for i, name in enumerate(('feature_snapshots', 'genome_snapshots', 'sequence_snapshots')):
            snapshot = source[name][0]
            content = deepcopy(snapshot['source']['content'])
            raw[content['artifact_ref']] = (SOURCE / f'input_{i + 4:03d}.bin').read_bytes()
            bundle['supplied_contents'].append(content)
            row = dict(mode='raw', snapshot_key=snapshot['snapshot_key'], declared_format=snapshot['format'], source=dict(kind='supplied_snapshot', content=content, completeness_evidence=None), population=snapshot['population'])
            if name == 'feature_snapshots':
                row['coordinate_convention'] = snapshot['coordinate_convention']
            supplied[name].append(row)
        supplied_raw = c.canonical(supplied).encode()
        evidence = dict(content=binding(supplied_raw, 'synthetic-supplied-data'), pointer='')
        values.insert(0, dict(evidence=evidence, value=supplied))
        parameters['supplied_data_evidence'] = evidence
    bundle['supplied_scientific_metadata'] = [deepcopy(r['evidence']) for r in values]
    validate_contract('ArtifactBundle', bundle)
    return dict(bundle=bundle, artifact_bytes=raw, supplied_values=values, requested_form=form(), parameters=parameters)
