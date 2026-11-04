"""Combined schema/provider test using three retained native report artifacts.

The task envelope grouping these independent examples is synthetic. This is
not evidence that a single live task produced all three reports.
"""
from pathlib import Path

from gene_annotation_episode.bvbrc_fastqutils_contracts import canonical_json
from gene_annotation_episode.bvbrc_fastqutils_sra_specs import SRA_FIELDS
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import validate_saved_projection
from test_bvbrc_fastqutils_provider import f


def test_sra_and_both_samstat_versions_preserve_distinct_native_populations():
    fixtures = Path(__file__).parent / 'fixtures'
    originals = {
        'sra': ((fixtures / 'bvbrc_fastqutils/sra/native_selected_run.json').read_bytes(), 'sra_metadata'),
        'legacy': ((fixtures / 'bvbrc_fastqutils_samstat_legacy/mixed.sam.samstat.html').read_bytes(), 'samstat_html'),
        'current': ((fixtures / 'bvbrc_fastqutils_samstat_svg/2_5_0/mixed.sam.samstat.html').read_bytes(), 'samstat_html'),
    }
    data = f.build(originals)
    fields = {name: f.selection('measurement', f.measurement('sra', metric, 'sra_run'),
                               availability='available_value') for name, (metric, *_) in SRA_FIELDS.items()}
    for name in ('legacy', 'current'):
        fields[name + '_total'] = f.selection('measurement',
            f.measurement(name, 'samstat_alignment_total_count', 'samstat_summary'),
            availability='available_value')
    fields['requirements'] = f.selection('requirements')
    before = canonical_json([data[0], data[2], data[3]])
    result = f.run(data, fields)
    assert result['status'] == 'ok'
    values = [result['facts'][name]['records'][0]['payload']['value']
              for name in [*SRA_FIELDS, 'legacy_total', 'current_total']]
    assert values == [2673129532, 35172757, 937094000, 76.0, 1, 11, 10]
    documents = {doc['document_id']: doc for doc in result['sheet']['documents']}
    assert documents['legacy']['artifact']['producer_version'] == '2.2.3'
    assert documents['current']['artifact']['producer_version'] == '2.5.0'
    assert documents['sra']['artifact']['producer_version'] is None
    population_ids = [p['id'] for p in result['sheet']['populations']]
    assert len(population_ids) == len(set(population_ids))
    assert not result['sheet']['associations']
    assert all(p['association_ref'] is None for p in result['sheet']['populations'])
    assert all(p['scope'] == 'unknown' for p in documents['sra']['populations'])
    assert not result['components']['calculations']['components']
    validate_saved_projection(result['sheet'], result['components'], facts=result['facts'],
        status=result['status'], missing_requirements=result['missing_requirements'],
        diagnostics=result['diagnostics'], requested_form=f.schema(fields), parameters=data[3],
        original_task=data[0]['original_task'], bundle=data[0])
    assert canonical_json([data[0], data[2], data[3]]) == before
    for name, (raw, _) in originals.items():
        assert data[1]['artifact_' + name] == raw
