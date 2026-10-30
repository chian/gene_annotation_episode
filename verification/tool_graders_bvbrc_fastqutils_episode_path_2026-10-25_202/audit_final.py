"""Audit terminal evidence without importing or executing scientific code."""
from pathlib import Path
import hashlib
import json
import sys
from urllib.parse import unquote
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    run = Path(sys.argv[1]).resolve()
    receipt = read(run / 'receipt.json')
    assert receipt['exit_code'] == 0
    assert all(not receipt[name] for name in ('frozen_source_changes', 'dependency_changes',
        'concurrent_candidate_changes', 'supplementary_input_changes'))
    assert receipt['scratch_within_limit']
    cases = list(ET.parse(run / 'junit.xml').getroot().iter('testcase'))
    assert len(cases) == 14 and all(not list(case) for case in cases)
    source, dependencies = read(run / 'source_before.json'), read(run / 'dependencies_before.json')
    assert source == read(run / 'source_after.json')
    assert dependencies == read(run / 'dependencies_after.json')
    assert len(source) == 1145 and len(dependencies) == receipt['dependency_file_count']
    assert all(sha(run / 'source' / name) == value for name, value in source.items())
    supplements = read(run / 'supplementary_inputs.json')
    assert len(supplements) == 44 and all(row['disposition'] == 'added' for row in supplements)
    origins = read(run / 'examples/imports/modules.json')
    covered = {str((run / 'source' / name).resolve()): value for name, value in source.items()}
    covered.update(dependencies)
    assert all(covered.get(row['path']) == row['sha256'] == sha(Path(row['path'])) for row in origins)
    code_origins = [row for row in origins if row['module'].startswith(('gene_annotation_episode', 'method_loop'))]
    assert code_origins and all(Path(row['path']).is_relative_to(run / 'source') for row in code_origins)
    examples = run / 'examples'
    workflow = examples / 'workflow'
    publication = read(workflow / 'publication.json')
    facts = publication['publication']['adapter_result']['facts']
    values = {key: facts[key]['records'][0]['payload']['value'] for key in ('read_count', 'gc', 'errors', 'retained')}
    assert list(values.values()) == [2, 5 / 9, .001, .75]
    forwarded = read(workflow / 'root_received_form.json')
    component_order = [unquote(row['field'].split('/', 1)[1]).removeprefix('/facts/')
        for rows in forwarded.values() if isinstance(rows, list)
        for row in rows if isinstance(row, dict) and 'field' in row
        and row['value']['selection']['target']['kind'] == 'component']
    assert component_order == ['gc', 'errors', 'retained']
    counts = read(workflow / 'counts.json')
    assert [row['role'] for row in counts] == ['annotation', 'scientific_process', 'launch', 'launch_api', 'results']
    assert [row['actions'] for row in counts] == [1, 3, 1, 2, 11]
    assert all(row['actions'] == row['observations'] for row in counts)
    for row in counts[2:]:
        band = row['controller']['estimate']['expected_next_gain']
        assert band['value'] == band['lower'] == band['upper'] == band['alpha'] == 0
    assert counts[-1]['marginal_gains'] == [0, 0, 0, 0, 3, 0, 3, 0, 3, 0, 3]
    assert counts[-1]['cumulative_credit'][-1] == 12
    parsed = read(workflow / 'parse_action.json')['result']['parse_attempt']
    assert (parsed['status'], parsed['code']) == ('completed', 'retained_without_sequence_projection')
    observation = read(workflow / 'parse_observation.json')
    assert observation['credit']['credit'] == observation['step']['marginal_credit'] == 0
    partial = read(examples / 'partial/publication.json')['publication']
    partial_fact = partial['adapter_result']['facts']['read_count']
    assert partial_fact['state'] == 'missing_value' and not partial_fact['satisfied']
    assert partial_fact['records'][0]['state'] == 'partial' and partial_fact['records'][0]['payload']['value'] == 1
    assert partial['completion_proof'] is None
    original = read(examples / 'history/original_publication.json')['publication']
    latest = read(examples / 'history/latest_publication.json')['publication']
    assert original['adapter_result']['facts']['read_count']['records'][0]['payload']['value'] == 2
    assert latest['completion_proof'] is None
    closure = read(run / 'scientific_source_closure.json')
    assert closure['implementation_sha256'] == '20adf5d29462216bca37f8bcf23c573aacca8b4eb6f10bb9cabed25ec8f654dd'
    evidence_hashes = {str(path.relative_to(run)): sha(path) for path in sorted(examples.rglob('*.json'))}
    result = dict(exit_code=receipt['exit_code'], tests=[case.attrib for case in cases],
        post_run_auditor_sha256=sha(Path(__file__).resolve()),
        source_paths=len(source), dependency_paths=len(dependencies),
        source_manifest_sha256=sha(run / 'source_before.json'),
        dependency_manifest_sha256=sha(run / 'dependencies_before.json'),
        supplement_manifest_sha256=sha(run / 'supplementary_inputs.json'),
        test_file_sha256=source['tests/test_bvbrc_fastqutils_episode_flow.py'],
        scientific_implementation_sha256=closure['implementation_sha256'],
        imported_modules=len(origins), imported_unique_paths=len({row['path'] for row in origins}),
        all_imports_covered_by_unchanged_manifests=True, application_module_origins=code_origins,
        numerical_values=values, original_component_order=component_order,
        counts=counts, own_action_total=sum(row['actions'] for row in counts),
        observation_total=sum(row['observations'] for row in counts),
        partial_field_state=partial_fact['state'], partial_observed_count=1,
        partial_has_completion_proof=False, original_admitted_history_count=2,
        later_partial_has_completion_proof=False, original_example_hashes=evidence_hashes,
        no_live_qualification=receipt['no_live_qualification'],
        untested='Live BV-BRC, deployed native producer versions, model scientific planning, W05 annotation-credit aggregation, and genuine Cutadapt through this particular fixture are not established. Root owns separate genuine Cutadapt host verification.')
    (run / 'terminal_audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: result[key] for key in ('exit_code', 'source_paths', 'dependency_paths',
        'imported_modules', 'numerical_values', 'own_action_total', 'observation_total')}, indent=2))


if __name__ == '__main__':
    main()
