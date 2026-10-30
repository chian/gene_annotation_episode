"""Direct deterministic primary-table example; no model/episode execution claim.

The retained table is a labeled manual visual transcription of printed Table3.
The parser validates its numerical expressions; it does not perform OCR.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(ROOT))


def main():
    from gene_annotation_episode.literature_binding_reader import read_binding_parameter_table
    from gene_annotation_episode.literature_binding_calculations import populate_binding_contrast

    parser = argparse.ArgumentParser()
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    directory = args.output_directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    original = BASE / 'primary_iscr2013/table3_original.jpg'
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    original_ref = 'source_primary_iscr2013_table3_' + digest[:24]
    original_artifact = 'artifact_' + digest
    ligands = ['hya', 'shuffled', 'hya (7C to G)', 'hya (8C to G)',
               'hya (8C to A)', 'hya (8C to T)']
    values = [('32 ± 2', '11 ± 1'), ('>1000', '>1000'), ('>510', '17 ± 3'),
              ('>740', '7 ± 3'), ('>1000', '6 ± 1'), ('>1000', '8 ± 1')]
    bands = [(62, 83), (87, 107), (110, 131), (136, 156), (161, 181), (186, 210)]
    rows = []
    for ligand, pair, (top, bottom) in zip(ligands, values, bands):
        for index, expression in enumerate(pair):
            rows.append({'subject': ['IscR', 'IscR-E43A'][index], 'state': 'apo',
                'experiment': 'Table3 competition', 'ligand': ligand, 'expression': expression,
                'locator': {'original_source_ref': original_ref,
                    'original_artifact_ref': original_artifact,
                    'image_region': [402, top, 476, bottom] if index == 0 else [520, top, 597, bottom]}})
    table = {'version': 'binding_parameter_table_v1', 'table_id': 'Table3',
        'parameter_kind': 'ic50', 'unit': 'nM',
        'uncertainty_basis': 'fit_to_averaged_curve', 'minimum_experiment_count': 3,
        'rows': rows}
    content = json.dumps(table, ensure_ascii=False, indent=2) + '\n'
    (directory / 'MANUAL_TABLE_TRANSCRIPTION.json').write_text(content)
    table_digest = hashlib.sha256(content.encode()).hexdigest()
    source = {'source_ref': 'source_retained_iscr2013_table3_' + table_digest[:24],
        'artifact_ref': 'artifact_' + table_digest, 'text': content,
        'representation': 'retained_visual_transcription'}
    results = []
    for subject in ['IscR', 'IscR-E43A']:
        extraction = read_binding_parameter_table(source, expected_subject=subject,
            expected_state='apo', expected_experiment='Table3 competition',
            reference_ligand='hya', test_ligand='hya (7C to G)', parameter_kind='ic50')
        results.append({'subject': subject, 'extraction': extraction,
                        'sheet': populate_binding_contrast(extraction)})
    receipt = {'execution': 'direct_deterministic_functions',
        'model_backed': False, 'literature_episode_execution': False,
        'original_image': str(original), 'original_image_sha256': digest,
        'implementation_hashes': {str(Path(sys.modules[function.__module__].__file__).resolve()):
            hashlib.sha256(Path(sys.modules[function.__module__].__file__).read_bytes()).hexdigest()
            for function in (read_binding_parameter_table, populate_binding_contrast)},
        'article_html_sha256': hashlib.sha256((BASE / 'primary_iscr2013/PMC3676455.html').read_bytes()).hexdigest(),
        'original_source_ref': original_ref,
        'transcription_origin': 'manual_visual_transcription_not_ocr',
        'unit_basis': 'competition Methods competitor concentration range in nM; not printed unit OCR',
        'spread_basis': 'Table3 footnote c: reported fit SD of averaged independent titrations',
        'limitations': ['no raw titration data', 'exact experiment count unknown',
            'independent preparation count unknown', 'sampling model and covariance unavailable',
            'greater-than limit mechanism unstated', 'no IC50 to Kd conversion',
            'no source likelihood implementation', 'no target correspondence or credit'],
        'results': results}
    (directory / 'PRIMARY_BINDING_POPULATION.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'subjects': len(results), 'output': str(directory),
                      'model_backed': False, 'episode_execution': False}))


if __name__ == '__main__':
    main()
