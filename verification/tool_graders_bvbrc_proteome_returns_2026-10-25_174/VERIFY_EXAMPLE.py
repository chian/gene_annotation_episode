"""Retain one actual provider/typed-return example with controlled publication.

Run from the repository root using .venv/bin/python. No network, scientific
service, configured-model call or complete Workflow execution is claimed.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from gene_annotation_episode import bvbrc_proteome_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_proteome_returns import FACT_SOURCES, IDENTIFIER_NAMESPACES
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.state import Store
from test_bvbrc_proteome_returns import ReturnFixture, MEASUREMENTS, RATIOS


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def main():
    destination = Path(__file__).with_name('example_001')
    destination.mkdir(exist_ok=False)
    with Store(destination / 'state') as store:
        fixture = ReturnFixture(store)
        args = fixture.example()
        parent = fixture.child(fixture.saved.root, 'scientific_process', args[0])
        child = fixture.child(parent, 'results', args[0])
        body = fixture.publications.add(child, args)
        before = store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
        form, schema, key, references = fixture.admit(parent, child)
        received = fixture.host.received_facts(parent, schema)
        fixture.admit(fixture.saved.root, parent)
        root_received = fixture.host.received_facts(fixture.saved.root, schema)
        assert root_received == received
        assert received[MEASUREMENTS][0]['value']['cell']['value'] == .4375
        assert received[MEASUREMENTS][1]['value']['cell']['value'] == 0
        assert received[MEASUREMENTS][2]['value']['cell']['value'] is None
        assert received[RATIOS][0]['value']['fraction']['value'] is None
        after = store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
        observations = store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0]
        assert before == after and observations == 0
        for name, value in (
            ('PUBLICATION_VIEW.json', body), ('PROVIDER_SHEET.json', args[1]), ('COMPONENTS.json', args[2]),
            ('RETURN_FORM.json', form), ('RETURN_SCHEMA.json', schema), ('RECEIVED_FACTS.json', root_received),
        ):
            write(destination / name, value)
        record = {
            'evidence_kind': 'retained_synthetic_native_format_real_provider_and_typed_boundary_controlled_publication',
            'live_service_execution': False, 'full_appservice_publication_path': False,
            'complete_workflow': False, 'configured_model_or_prompt_verification': False,
            'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
            'implementation_sha256': adapter.implementation_sha256(),
            'fact_sources': list(FACT_SOURCES), 'identifier_namespaces': list(IDENTIFIER_NAMESPACES),
            'bundle_sha256': body['publication']['bundle_content']['sha256'],
            'sheet_bundle_sha256': args[1]['bundle_sha256'],
            'sheet_sha256': digest(args[1]), 'components_sha256': digest(args[2]),
            'mean_identity_fraction': received[MEASUREMENTS][0]['value']['cell']['value'],
            'observed_zero_identity_percent': received[MEASUREMENTS][1]['value']['cell']['value'],
            'executed_reference_denominator': received[MEASUREMENTS][2]['value']['cell']['value'],
            'complete_published_reference_fraction': received[RATIOS][0]['value']['fraction']['value'],
            'provider_projection_status': body['publication']['adapter_result']['status'],
            'results_episode_id': child.episode_id, 'scientific_parent_episode_id': parent.episode_id,
            'root_episode_id': fixture.saved.root.episode_id, 'admission_operation_key': key,
            'admitted_source_refs': references, 'runtime_actions_before_admission': before,
            'runtime_actions_after_admission': after, 'runtime_observation_rows': observations,
        }
        write(destination / 'RECEIPT.json', record)
        print(json.dumps({key: record[key] for key in ('evidence_kind', 'mean_identity_fraction',
            'observed_zero_identity_percent', 'executed_reference_denominator',
            'complete_published_reference_fraction', 'runtime_actions_before_admission',
            'runtime_actions_after_admission', 'runtime_observation_rows')}))
    sources = [ROOT / 'gene_annotation_episode' / name for name in adapter._DEPENDENCIES]
    sources.extend(ROOT / name for name in ('gene_annotation_episode/bvbrc_proteome_returns.py',
        'tests/test_bvbrc_proteome_returns.py', 'tests/test_bvbrc_proteome_returns_original.py'))
    write(destination / 'SOURCE_SHA256.json', {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                             for path in sources})


if __name__ == '__main__':
    main()
