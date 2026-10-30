"""Direct deterministic primary XML demo; ordinary episode path is tested separately.

Run from the checkout with its Python environment and --output NEW_DIRECTORY.
No source acquisition, model inference or controller execution occurs here.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_quantity_storage import LiteratureQuantityRepository
from gene_annotation_episode.literature_activity_calculations import populate_corrected_activity
from gene_annotation_episode.state import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    destination = parser.parse_args().output
    destination.mkdir(parents=True, exist_ok=False)
    original = Path(__file__).parent / 'primary_csid/PMC6265302_original.xml'
    raw = original.read_bytes()
    outputs = []
    with Store(destination / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        artifact = store.artifact(raw, 'application/xml')
        source = store.put('source', {'provider': 'retained_primary_jats', 'accession': 'PMC6265302',
            'uri': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6265302/fullTextXML',
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='caller')
        context = BindingContext('csid-primary-direct-demo', 'source-quantity-adapter-demo',
            'literature', (('literature', 'direct-demo'),), store.validate_scope(), {}, {}, (source['id'],))
        repo = LiteratureQuantityRepository(store, context.run_id)
        for quantity, analyte in [('specific_activity', None), ('apparent_km', 'GA'), ('apparent_km', 'αKG')]:
            args = {'source_ref': source['id'], 'source_kind': 'primary_jats', 'section_id': 'Sec3',
                'paragraph_id': 'Par4', 'subject': 'CsiD', 'quantity': quantity, 'analyte': analyte}
            outcome = repo.populate(context, args, quantity + '-' + (analyte or 'activity'))
            received = (*context.received_record_refs, *outcome['record_refs'])
            outputs.append({'selected_arguments': args, 'outcome': outcome,
                'saved_sheet': repo.read(outcome['result']['sheet_ref']),
                'requested_cells': repo.project_cells([outcome['result']['sheet_ref']],
                    permitted_record_refs=received,
                    components=('reported_value', 'reported_spread', 'relative_reported_spread', 'source_presence_index'))})
        native = {'execution_kind': 'direct_deterministic_adapter', 'model_inference': False,
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_ref': source['id'],
            'source_artifact_ref': artifact, 'populations': outputs}
        (destination / 'PRIMARY_SOURCE_POPULATION.json').write_text(json.dumps(native, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'source_sha256': native['source_sha256'], 'primary_quantities': [
            {'quantity': item['saved_sheet']['sheet']['extraction']['quantity'],
             'analyte': item['saved_sheet']['sheet']['extraction']['analyte'],
             'value': item['saved_sheet']['sheet']['cells']['reported_value']['value'],
             'unit': item['saved_sheet']['sheet']['cells']['reported_value']['unit']} for item in outputs]}))
    diagonal = [.04, .0225, .0025, .01, .01, .01]
    synthetic = populate_corrected_activity({'values': {'q': 1., 'g': .15, 'k': 1., 'E': 1., 'u': 2., 'v': 1.6},
        'covariance': [[diagonal[i] if i == j else 0. for j in range(6)] for i in range(6)],
        'variance_status': 'known', 'distinct_residual_variance': .0625,
        'observation_model': 'known_normal_nonnegative_presence'})
    (destination / 'SYNTHETIC_CORRECTION_CALCULATION.json').write_text(json.dumps({
        'origin': 'synthetic', 'primary_source_measurement': False, 'result': synthetic}, indent=2) + '\n')
    print(json.dumps({'synthetic_calculator_values': {name: cell['value'] for name, cell in synthetic['cells'].items()}}))


if __name__ == '__main__':
    main()
