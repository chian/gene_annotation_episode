"""One caller preparation step, after verified custody and real case preparation.

This script does not import the episode application, open SQLite, prepare a case,
choose work, or launch anything. Its outputs are new, exclusive caller files.
It is tied to the adopted particular profile rather than a runtime interface.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path('/home/chia/repos/gene_annotation_episode')
PLAN = ROOT / 'verification/configured_api_caller_plan_2026-10-22_001'
CPLAN = ROOT / 'verification/scientific_checkpoint_custody_plan_2026-10-22_001'
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-006')
OLD_RUN = 'run_a9cae64280ed405594a79255d659f917'
OLD_PIN = 'a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a'
OLD_PENDING = '21e2407799ae840e2192619396d1c74ee823fc445dab2a13aab5e940816ad16c'
STATIC_POLICY = 'dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def checked_read(path):
    path = Path(path)
    assert path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents))
    return path.read_bytes()


def load(path):
    return json.loads(checked_read(path))


def validate(document, schema, name):
    Draft202012Validator({'$ref': '#/$defs/' + name, '$defs': schema['$defs']},
        format_checker=FormatChecker()).validate(document)


def verify_plan():
    manifest_path = PLAN / 'MANIFEST_FINAL.json'
    assert sha(checked_read(manifest_path)) == 'b7b2f62aa19399207fa31741f3f7a5eba740fd1556623b3424305ffa901b64fd'
    manifest = load(manifest_path)
    for member in manifest['members']:
        body = checked_read(PLAN / member['path'])
        assert len(body) == member['bytes'] and sha(body) == member['sha256']
    assert sha(checked_read(CPLAN / 'SCHEMAS004.json')) == 'b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112'


def derive(custody_result_path, expected_implementation_sha256):
    verify_plan()
    cschema, pschema = load(CPLAN / 'SCHEMAS004.json'), load(PLAN / 'SCHEMAS.json')
    result = load(custody_result_path)
    validate(result, cschema, 'result')
    workspace = RUN / 'workspace'
    assert result['destination_workspace'] == str(workspace)
    descriptor = result['receipt']
    receipt_path = Path(descriptor['path'])
    assert receipt_path.is_absolute() and receipt_path.is_relative_to(workspace)
    assert '..' not in receipt_path.parts
    body = checked_read(receipt_path)
    assert len(body) == descriptor['bytes'] and sha(body) == descriptor['sha256']
    receipt = json.loads(body)
    validate(receipt, cschema, 'receipt')
    assert receipt['destination_workspace'] == str(workspace)
    assert receipt['source']['run_id'] == OLD_RUN
    assert receipt['source']['implementation_sha256'] == OLD_PIN
    assert receipt['source']['pending']['request_raw_utf8_sha256'] == OLD_PENDING
    refs = result['initial_known_record_refs']
    assert refs == receipt['initial_known_record_refs'] == sorted(set(refs))
    assert sha(canonical(refs)) == receipt['initial_known_record_refs_sha256']
    assert result['lineage_source_refs'] == {
        'observations': receipt['lineage']['observation_source_ref'],
        'index': receipt['lineage']['index_source_ref']}
    assert set(result['lineage_source_refs'].values()) <= set(refs)
    assert refs == sorted(set(receipt['caller_initial_known_record_refs'])
        | set(result['lineage_source_refs'].values()))
    committed_descriptor = receipt['checkpoint']['committed_reference_manifest']
    assert committed_descriptor['path'] == 'checkpoint/committed-references.json'
    committed_path = workspace / committed_descriptor['path']
    assert committed_path.is_relative_to(workspace) and '..' not in committed_path.parts
    committed_body = checked_read(committed_path)
    assert sha(committed_body) == committed_descriptor['sha256']
    assert len(committed_body) == committed_descriptor['bytes']
    committed = json.loads(committed_body)
    validate(committed, cschema, 'committed_reference_manifest')
    assert {r['reference'] for r in committed['records']} <= set(refs)

    launch_path = RUN / 'case-launch.json'
    launch = load(launch_path)
    assert launch['run_dir'] == str(RUN)
    blueprint = load(PLAN / 'PARAMETER_BLUEPRINT.json')
    assert launch['case_dir'] == blueprint['fixed_case_directory']
    configuration = load(PLAN / 'PROPOSED_CALLER_CONFIGURATION.json')
    validate(configuration, pschema, 'normalized_configuration')
    assert canonical(launch['configuration']) == canonical(configuration)
    assert launch['focus'].encode('utf-8') == checked_read(PLAN / 'PROPOSED_CALLER_FOCUS.txt')
    identity = receipt['fixed_identity']
    original = load(PLAN / 'ORIGINAL_CALLER_OPERANDS.json')
    case_path = Path(launch['case_dir']) / 'case.json'
    case_body = checked_read(case_path)
    case_witness = next(row for row in load(PLAN / 'READSET.json')['entries']
        if row['path'] == str(case_path))
    assert len(case_body) == case_witness['bytes'] and sha(case_body) == case_witness['sha256']
    custody_case = next(row for row in receipt['source']['authority_files']
        if row['source_path'] == str(case_path))
    assert custody_case['sha256'] == case_witness['sha256']
    assert custody_case['bytes'] == case_witness['bytes']
    case = json.loads(case_body)
    assert identity['case_ref'] == case['case_ref']
    assert identity['target_ref'] == case['target_ref']
    assert identity['problem_ref'] == case['problem_ref']
    for key in ('target_ref', 'problem_ref', 'target_sequence_sha256'):
        assert identity[key] == launch[key] == original['fixed_identity'][key]
    assert identity['target_sequence_artifact_ref'] == 'artifact_' + identity['target_sequence_sha256']

    # Only the two declared unresolved fields change in the adopted template.
    parameters = deepcopy(blueprint['template'])
    parameters['policy']['scientific_progress']['initial_known_record_refs'] = refs
    registry_ref = launch['registry_configuration']['registry_ref']
    assert registry_ref != original['parameters']['policy']['operational']['registry_ref']
    parameters['policy']['operational']['registry_ref'] = registry_ref
    validate(parameters, pschema, 'configured_parameters')
    static = deepcopy(parameters['policy'])
    del static['operational']['registry_ref']
    del static['scientific_progress']['initial_known_record_refs']
    assert sha(canonical(static)) == STATIC_POLICY

    source_files = sorted(p for package in ('gene_annotation_episode', 'method_loop')
        for p in (CODE / package).rglob('*.py'))
    digest = hashlib.sha256()
    for path in source_files:
        digest.update(str(path.relative_to(CODE)).encode('utf-8') + b'\0')
        digest.update(hashlib.sha256(checked_read(path)).digest())
    assert digest.hexdigest() == expected_implementation_sha256
    policy_source = CODE / 'gene_annotation_episode/api_planning_case_policy.py'
    evidence = {'version': 'particular_api_caller_parameter_derivation_v1',
        'custody_result': {'path': str(Path(custody_result_path)),
            'sha256': sha(checked_read(custody_result_path))},
        'custody_receipt': descriptor, 'case_launch_sha256': sha(checked_read(launch_path)),
        'policy_source_sha256': sha(checked_read(policy_source)),
        'implementation_sha256': digest.hexdigest(), 'runtime_files': len(source_files),
        'parameters_canonical_sha256': sha(canonical(parameters)),
        'inherited_list_sha256': sha(canonical(refs)), 'inherited_refs': len(refs),
        'static_policy_remainder_sha256': STATIC_POLICY,
        'native_registry_ref': registry_ref, 'application_imports': 0,
        'database_opens': 0, 'model_http_native_calls': 0}
    return parameters, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--custody-result', type=Path, required=True)
    parser.add_argument('--expected-implementation-sha256', required=True)
    args = parser.parse_args()
    parameters, evidence = derive(args.custody_result, args.expected_implementation_sha256)
    outputs = {RUN / 'caller-inputs/parameters.json': canonical(parameters) + b'\n',
        RUN / 'caller-inputs/PARAMETER_DERIVATION.json': canonical(evidence) + b'\n'}
    output_parent = RUN / 'caller-inputs'
    assert output_parent.is_dir() and output_parent.resolve() == output_parent
    assert not any(path.is_symlink() for path in (output_parent, *output_parent.parents))
    assert all(not path.exists() and not path.is_symlink() for path in outputs)
    for path, body in outputs.items():
        with path.open('xb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o400)
    parent_fd = os.open(RUN / 'caller-inputs', os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    print(json.dumps({'outputs': [str(p) for p in outputs],
        'parameters_sha256': sha(outputs[RUN / 'caller-inputs/parameters.json']),
        'scientific_run_started': False}))


if __name__ == '__main__':
    main()
