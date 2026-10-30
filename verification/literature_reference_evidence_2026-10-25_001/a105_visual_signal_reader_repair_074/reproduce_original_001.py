"""Constructed public-API replay counterexample; no paper/native/model work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def main():
    from gene_annotation_episode.literature_ratio_source_inputs import (
        read_relative_signal_source_inputs, validate_relative_signal_source_extraction)
    from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
    source, subject, genotype = ['source_' + str(n) * 24 for n in (1, 2, 3)]
    data = {source: b'<article><body><sec id="s1"><p>SyntheticProtein 60% (V) of WT levels.</p></sec></body></article>',
        subject: b'SyntheticProtein', genotype: b'ConstructedStrain'}
    def witness(reference):
        return {'kind': 'text', 'source_ref': reference, 'representation': 'original',
                'start': 0, 'end': len(data[reference]), 'quote': data[reference].decode()}
    fields = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
        'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment',
        'condition', 'endpoint', 'normalization', 'signal_kind', 'reference_role', 'arrangement', 'signal_use')
    comparison = {name: {'status': 'unknown', 'value': None, 'witnesses': []} for name in fields}
    for field, reference in (('subject', subject), ('genotype', genotype)):
        comparison[field] = {'status': 'known', 'value': data[reference].decode(), 'witnesses': [witness(reference)]}
    selected = {'version': 'relative_signal_source_selection_v2', 'source_ref': source,
        'comparison': comparison, 'representations': [{'representation_id': 'constructed_prose', 'kind': 'jats_percent',
            'selection': {'source_ref': source, 'section_id': 's1', 'paragraph_index': 0,
                'expected_subject': 'SyntheticProtein', 'variant': 'V', 'reference_literal': 'WT levels'},
            'comparison_relation': {'value': 'supported', 'witnesses': [witness(subject)]},
            'physical_measurement': {'status': 'unknown', 'value': None, 'witnesses': []},
            'reference_measurement': {'status': 'unknown', 'value': None, 'witnesses': []}}]}
    calls = []
    def read_source(reference, representation):
        assert representation == 'original'
        calls.append(reference)
        raw = data[reference]
        return {'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(), 'content': raw}
    def forbidden_view(*args):
        raise AssertionError('no image requested')
    extraction = read_relative_signal_source_inputs(selected, read_source=read_source,
        read_view=forbidden_view, evidence_origin='synthetic_fixture')
    validate_relative_signal_source_extraction(extraction)
    loaded = json.loads(json.dumps(extraction, sort_keys=True))
    failure = None
    try:
        validate_relative_signal_source_extraction(loaded)
    except ExperimentalContractError as error:
        failure = {'code': error.code, 'field': error.field}
    assert failure == {'code': 'saved_relationship_mismatch', 'field': 'sources.roster'}, failure
    row = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'real public-API counterexample reproduced',
        'scope': 'Constructed synthetic JATS and two generic source witnesses only; no native or scientific evidence',
        'initial_public_read_and_detached_validation_succeeded': True,
        'saved_roundtrip': 'json.dumps(sort_keys=True) then json.loads',
        'failure': failure, 'original_source_roster': [row['source_ref'] for row in extraction['sources']],
        'actual_callbacks': calls, 'source_callbacks_after_population': 0,
        'root_cause': 'Dependency traversal relies on dictionary insertion order; canonical saved JSON sorts object fields',
        'original_manifest_or_source_edits': False}
    with (HERE / 'DEPENDENCY_ORDER_COUNTEREXAMPLE_001.json').open('x') as stream:
        json.dump(row, stream, indent=2); stream.write('\n')
    print(json.dumps(row))


if __name__ == '__main__':
    main()
