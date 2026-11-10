"""Prepare explicit synthetic partner/expression data on retained real sequences.

Copies original translation annotations without claiming DNA verification.
Evaluator expectations are written separately and are never case inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path

from Bio import SeqIO


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def prepare(output):
    fixtures = Path(__file__).parent / 'fixtures'
    genomic = fixtures / 'a103/real/rcapsulatus-bioy.gb'
    acquisition = json.loads((genomic.parent / 'manifest.json').read_text())['genomic_files'][genomic.name]
    digest = hashlib.sha256(genomic.read_bytes()).hexdigest()
    if digest != acquisition['sha256']:
        raise ValueError('retained_genbank_identity_conflict')
    selected = {}
    for record in SeqIO.parse(genomic, 'genbank'):
        for index, feature in enumerate(record.features):
            if feature.type != 'CDS':
                continue
            locus, = feature.qualifiers.get('locus_tag', [None])
            if locus not in {'RCAP_RS16045', 'RCAP_RS16050'}:
                continue
            translation, = feature.qualifiers['translation']
            accession, = feature.qualifiers['protein_id']
            selected[locus] = {'locus_tag': locus, 'protein_accession': accession,
                'record_accession': record.id, 'source_feature_index': index,
                'sequence': ''.join(translation.split()), 'meaning': 'copied_annotation; DNA_unverified'}
    if set(selected) != {'RCAP_RS16045', 'RCAP_RS16050'}:
        raise ValueError('required_source_annotations_missing')
    subject, component = selected['RCAP_RS16045'], selected['RCAP_RS16050']
    output.mkdir(parents=True, exist_ok=True)
    lines = [
        'Explicit synthetic declared model dataset joined-partner-model-01.',
        'These are simulated measurements for workflow evaluation, not wet experiments.',
        'Assay joined-omission-addback-01 measures declared product formation per mg Role S.',
        'The same defined synthetic condition c1, preparation and normalization apply to all three arms.',
        'Role S and Role T are defined by the following complete protein strings in this model.',
        'Role S is supplied in every arm; all other modeled ingredients are unchanged.',
        f'Role S; reference {subject["protein_accession"]}; locus {subject["locus_tag"]}.',
        '>declared-role-S', subject['sequence'], '',
        f'Role T; reference {component["protein_accession"]}; locus {component["locus_tag"]}.',
        '>declared-role-T', component['sequence'], '',
        'Reference arm, measurement model-reference: Role S and Role T present; 100 pmol/min/mg.',
        'Omitted arm, measurement model-omitted: Role S present and Role T absent; 20 pmol/min/mg.',
        'Addback arm, measurement model-addback: Role T restored with Role S unchanged; 90 pmol/min/mg.',
        'All three rates are synthetic point values; spread, independent replication and joint uncertainty are unreported.',
        'This models condition-specific contribution and partial restoration; no cellular necessity, affinity or catalysis is measured.',
        'The associated expression panel uses the same complete Role S and Role T strings in declared condition c1.',
        'Its sample genome accessions name a reference only; experimental genotype and organism are not established.',
        'The retained genomic sequence is a reference window, not a complete genome or proof of an assay sample origin.',
    ]
    (output / 'declared-assay.txt').write_text('\n'.join(lines) + '\n')
    for name, item in [('role-s', subject), ('role-t', component)]:
        (output / (name + '.faa')).write_text('>' + item['protein_accession'] + ' copied_annotation\n' + item['sequence'] + '\n')
    panel = {'version': 'a107_expression_table_v2', 'dataset_id': 'synthetic-joined-expression-01',
        'origin': 'synthetic', 'quantity': {'unit': 'declared_signal_units', 'scale': 'linear',
            'normalization': 'same_declared_standard', 'nonnegative': True,
            'source_locator': 'synthetic://joined-expression-01/quantity'},
        'features': [], 'samples': [], 'measurements': [], 'detection_criteria': []}
    for side, item in [('role_s', subject), ('role_t', component)]:
        panel['features'].append({'id': side, 'entity_id': item['protein_accession'],
            'molecule': 'protein', 'sequence_sha256': hashlib.sha256(item['sequence'].encode()).hexdigest(),
            'source_locator': 'synthetic://joined-expression-01/features/' + side})
    for sample, unit, value in [('s1', 'u1', 1), ('s2', 'u2', 2), ('s3', 'u2', 4)]:
        panel['samples'].append({'id': sample, 'biological_unit_id': unit, 'condition_key': 'c1',
            'organism_id': None, 'genome_accession': subject['record_accession'],
            'source_locator': 'synthetic://joined-expression-01/samples/' + sample})
        for side, number in [('role_s', value), ('role_t', value * 2)]:
            locator = 'synthetic://joined-expression-01/' + sample + '/' + side
            panel['measurements'].append({'feature_id': side, 'sample_id': sample,
                'measurement_id': 'joined-' + sample + '-' + side, 'value': number,
                'missing_reason': None, 'reported_bound': None, 'source_locator': locator})
            panel['detection_criteria'].append({'id': 'criterion-' + sample + '-' + side,
                'feature_id': side, 'sample_id': sample, 'kind': 'limit_of_detection',
                'operator': 'greater_than', 'value': .5, 'unit': 'declared_signal_units',
                'scale': 'linear', 'normalization': 'same_declared_standard',
                'calibration_condition_key': 'c1', 'control_source_locator': locator + '/control',
                'source_locator': locator + '/criterion'})
    save_json(output / 'declared-expression.json', panel)
    save_json(output / 'provenance.json', {'version': 'a107_joined_declared_inputs_v1',
        'original_genomic_source': '../../a103/real/rcapsulatus-bioy.gb',
        'original_genomic_sha256': digest, 'original_acquisition': acquisition,
        'sequences': list(selected.values()), 'synthetic_assay_and_expression': True,
        'translation_verification_performed': False, 'physiological_claim': None})
    save_json(output / 'case.json', {'axis': 'A107', 'question':
        'Investigate the supplied declared partner-dependence and expression observations and their '
        'application to the supplied protein and reference genomic window. Establish the original '
        'assayed molecules, particular required component and sequence correspondence, qualify '
        'presence or scoped non-detection against actual encoded molecules, and assess matched '
        'expression with the correct sample dependence. Keep modeled requirement, sequence '
        'detection, expression and biological function distinct. Preserve unknown sample origin '
        'and all source/model qualifications. Return saved numerical components and actual '
        'per-use evidence, along with specific missing-information needs.',
        'input_path': '../anonymous-case-02.faa', 'molecule': 'protein',
        'source_directory': '../../../../research/slotted_process_library/publications/2026-10-24-001',
        'evidence_paths': ['declared-assay.txt', 'declared-expression.json', 'role-s.faa', 'role-t.faa',
            'provenance.json', '../../a103/real/rcapsulatus-bioy.gb',
            '../annotated-cds/rcapsulatus-bioy.annotated.faa', '../annotated-cds/provenance.json'],
        'target_genomic_paths': ['../../a103/real/rcapsulatus-bioy.gb']})
    save_json(output / 'expectations.json', {'evaluator_only': True, 'never_load_as_episode_input': True,
        'requirements': ['Original role/assay and numerical cell identities survive identity qualification.',
            'The declared full source sequences support only their particular roles and experiment.',
            'Original genomic DNA verification and search use authenticated HPC publications.',
            'Copied annotations alone are not DNA verification or functional requirement.',
            'The requirement, detected sequence and measured protein are joined explicitly.',
            'Raw expression values and matching source criteria survive original numerical grading.',
            's2/s3 share u2; three complete pairs do not imply three independent preparations.',
            'Synthetic dependence/expression and a genomic reference do not establish sample physiology.',
            'Same-source repeated use earns no independent confirmation or duplicate credit.',
            'Actual typed parent receipts and subsequent parent interpretation are inspected.'],
        'conditional_partner_loss': .8, 'conditional_restoration_fraction': .875,
        'expression_complete_pairs': 3, 'expression_distinct_declared_biological_units': 2,
        'expression_descriptive_pearson': 1.0, 'scientific_scalar': None})
    return {'output': str(output), 'copied_sequences': len(selected), 'workflow_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().output.resolve())), flush=True)
