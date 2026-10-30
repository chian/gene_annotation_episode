"""Exercise existing validators on captured data; no proposed repair is applied."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

OWN = Path(__file__).resolve().parent
BASELINE = OWN / 'baseline_candidate'
CAPTURE = OWN / 'capture_failure_001'
OUT = OWN / 'probe_domains_001'
OUT.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASELINE))
os.chdir(BASELINE)
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_bundle_values import _requirements, _selection
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import (
    validate_genome_alignment_inputs, validate_genome_alignment_associations)
from gene_annotation_episode.bvbrc_genome_alignment_sheet import validate_genome_alignment_data
from gene_annotation_episode.bvbrc_genome_alignment_bundle_adapter import implementation_sha256
from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments


def save(name, value):
    with (OUT / name).open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


observations = json.loads((CAPTURE / 'observations.json').read_text())
failures = [row for row in observations if 'exception' in row]
assert len(failures) == 1
data_file = CAPTURE / failures[0]['data_file']
data = json.loads(data_file.read_text())
publications = [(path, json.loads(path.read_text())) for path in CAPTURE.rglob('publication_inputs.json')]
publication_path, inputs = next((path, value) for path, value in publications
    if value['current_operation']['arguments']['requirement_ids'] == ['native'])
arguments = inputs['current_operation']['arguments']
results = []


def check(name, fn, error=None):
    try:
        fn()
    except ValueError as exc:
        assert error is not None and str(exc) == error, (name, str(exc), error)
        results.append({'name': name, 'outcome': 'expected_rejection', 'code': str(exc)})
    else:
        assert error is None, (name, 'unexpected acceptance', error)
        results.append({'name': name, 'outcome': 'accepted'})


check('captured_C_inputs_are_valid', lambda: validate_genome_alignment_inputs(data['inputs']))
check('captured_C_associations_are_valid', lambda: validate_genome_alignment_associations(data['associations']))
check('captured_original_output_selection_is_valid', lambda: _selection(inputs['current_snapshot'], inputs))
check('unchanged_D_data_still_has_original_failure', lambda: validate_genome_alignment_data(data),
      'bvbrc_genome_alignment_provider_requirement_reference_unknown')

original_artifact = data['associations']['artifacts'][0]['artifact']
check('retained_ArtifactMember_shape_is_valid', lambda: validate_contract('ArtifactMember', original_artifact))
bad_artifact = deepcopy(original_artifact)
bad_artifact['requirement_ids'] = ['native', 'native']
check('duplicate_ArtifactMember_selection_ids_reject', lambda: validate_contract('ArtifactMember', bad_artifact),
      'contract_shape_invalid')

scientific_id = data['associations']['artifacts'][0]['requirement_ids'][0]
bad = deepcopy(arguments); bad['requirement_ids'] = [scientific_id]
check('scientific_requirement_is_not_an_output_selection', lambda: _requirements(inputs, bad),
      'publication_dependency_conflict')
bad_role = deepcopy(arguments); bad_role['role'] = 'genome_alignment_backbone'
check('original_selection_wrong_role_rejects', lambda: _requirements(inputs, bad_role),
      'publication_requirement_conflict')
bad_format = deepcopy(arguments); bad_format['declared_format']['format'] = 'mauve_backbone'
check('original_selection_wrong_format_rejects', lambda: _requirements(inputs, bad_format),
      'publication_requirement_conflict')
different_object = deepcopy(inputs)
different_object['selector']['requirements'][1]['exact_object'] = {'kind': 'original_target', 'target_id': 'unselected'}
check('original_selection_wrong_exact_object_rejects', lambda: _requirements(different_object, arguments),
      'publication_requirement_conflict')

bad_associations = deepcopy(data['associations'])
bad_associations['artifacts'][0]['requirement_ids'] = ['native']
check('output_selection_is_not_scientific_association_cause',
      lambda: validate_genome_alignment_associations(bad_associations), 'bvbrc_genome_alignment_argument_invalid')
bad_inputs = deepcopy(data['inputs'])
assert bad_inputs['files']
bad_inputs['files'][0]['requirement_ids'] = ['native']
check('output_selection_is_not_scientific_input_cause',
      lambda: validate_genome_alignment_inputs(bad_inputs), 'bvbrc_genome_alignment_argument_invalid')
bad_union = deepcopy(data)
bad_union['requirements'] = [row for row in bad_union['requirements'] if row['requirement_id'] != scientific_id]
check('dropping_nested_scientific_cause_from_global_union_rejects',
      lambda: validate_genome_alignment_data(bad_union), 'bvbrc_genome_alignment_provider_component_identity_conflict')

# Explicit counterfactual for the schema-permitted older ArtifactMember shape.
# This is not the captured native acquisition and is not used to claim repair.
legacy_shape = deepcopy(data)
del legacy_shape['associations']['artifacts'][0]['artifact']['requirement_ids']
check('older_optional_ArtifactMember_field_absence_validates', lambda: validate_genome_alignment_data(legacy_shape))

# The provider's native parameter dictionaries have their own meaning too.
native_parameter = deepcopy(legacy_shape)
for task in (native_parameter['original_task'], native_parameter['inputs']['original_task'],
             native_parameter['associations']['original_task']):
    task['submitted_parameters']['diagnostic_payload'] = {'requirement_ids': ['native-parameter-value']}
check('OriginalTask_retained_native_JSON_has_its_own_domain',
      lambda: validate_contract('OriginalTask', native_parameter['original_task']))
check('current_whole_data_walk_also_misreads_native_parameter_JSON',
      lambda: validate_genome_alignment_data(native_parameter),
      'bvbrc_genome_alignment_provider_requirement_reference_unknown')

# Independent native calculation only: the failed provider route is not bypassed.
request = inputs['adapter']['parameters']['calculation_plan']['requests'][0]
document = data['parsed_artifacts'][0]['document']
assert request['kind'] == 'mauve_v4_segments' and request['use_inputs'] is False
selection = request['selection'] | {'document_id': document['document_id']}
native = calculate_mauve_v4_segments(document, selection=selection, inputs=None)
save('native_components_standalone.json', native)
coverage = native['coverage'][0]
assert coverage['known_union_bases']['value'] == 690
assert coverage['denominator_bases']['value'] == 693
assert coverage['coverage_fraction']['value'] == 690 / 693

manifest = json.loads((OWN / 'baseline_copy_manifest_001.json').read_text())
assert all(hashlib.sha256((BASELINE / row['path']).read_bytes()).hexdigest() == row['sha256']
           for row in manifest['files'])
evidence = {
    'captured_data': str(data_file.relative_to(OWN)),
    'publication_inputs': str(publication_path.relative_to(OWN)),
    'failing_reference_path': '/associations/artifacts/0/artifact/requirement_ids',
    'failing_reference_values': ['native'],
    'intended_referent_pointer': '/selector/requirements/1',
    'intended_referent_schema': 'bvbrc_appservice_schemas.json#/$defs/OutputRequirement',
    'intended_referent': inputs['selector']['requirements'][1],
    'scientific_requirement_count': len(data['requirements']),
    'scientific_artifact_cause': next(r for r in data['requirements'] if r['requirement_id'] == scientific_id),
    'baseline_source_files_verified_unchanged': len(manifest['files']),
    'baseline_genome_alignment_adapter_sha256': implementation_sha256(),
    'probe_count': len(results), 'probes': results,
    'standalone_native_example': {key: coverage[key] for key in
        ('member', 'denominator_kind', 'known_union_bases', 'denominator_bases', 'coverage_fraction')},
    'scope': 'Existing baseline validators only; no replacement validator or source modification; no complete provider pass claimed.',
}
save('results.json', evidence)
for path in OUT.iterdir():
    path.chmod(0o444)
print(json.dumps({'probe_count': len(results), 'baseline_files_unchanged': len(manifest['files']),
    'expected_original_failure_preserved': True, 'standalone_coverage': coverage['coverage_fraction']['value']}))
