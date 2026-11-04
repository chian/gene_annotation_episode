"""Synthetic literal source locations; no paper or model inference."""
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_partner_source_fields import read_source_number, read_source_rate_unit
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.source_locations import locate
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def source(store, raw, *, text=None, parents=()):
    return store.put('source', {'provider': 'synthetic_location_fixture', 'accession': None,
        'uri': None, 'artifact_ref': store.artifact(raw, 'application/octet-stream'),
        'text_ref': store.artifact(text, 'text/plain') if text is not None else None,
        'request_ref': None, 'version': None, 'retrieved_at': None,
        'parent_source_refs': list(parents)}, origin='caller')


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path) as value:
        value.create_problem(raw_sequence='ATGGCT', molecule='dna')
        yield value


def query(store, row, needle, **kwargs):
    return locate(store, row['id'], kwargs.pop('representation', 'original'), needle,
        permitted_inputs=(row['id'],), scope=store.validate_scope(), **kwargs)


def test_utf8_crlf_markup_and_distinct_representations(store):
    raw = 'α\r\n<p>µ 12 µM/min</p>\r\n'.encode()
    row = source(store, raw, text='µ 12 µM/min\n')
    result = query(store, row, '12 µM/min', context_bytes=3)
    match, = result['matches']
    assert match['witness'] == {'source_ref': row['id'], 'representation': 'original',
        'start': raw.index(b'12'), 'end': raw.index(b'12') + len('12 µM/min'.encode()), 'quote': '12 µM/min'}
    context = match['context']
    assert raw[context['start']:context['end']].decode() == context['text']
    assert context['artifact_ref'] == match['artifact_ref'] == row['artifact_ref']
    text = query(store, row, '12 µM/min', representation='text')
    assert text['artifact_ref'] == row['text_ref'] != row['artifact_ref']
    assert text['matches'][0]['witness']['start'] == len('µ '.encode())


@pytest.mark.parametrize('chunk', [1, 2, 3, 7, 65536])
def test_streaming_overlaps_chunk_spans_and_pagination_without_omissions(store, monkeypatch, chunk):
    monkeypatch.setattr('gene_annotation_episode.source_locations.CHUNK_BYTES', chunk)
    raw = 'αaaaaaβaaaa'.encode()
    row = source(store, raw)
    args = dict(source_ref=row['id'], representation='original', needle='aa', limit=2, context_bytes=1)
    positions, ranges = [], []
    while args is not None:
        result = locate(store, **args, permitted_inputs=(row['id'],), scope=store.validate_scope())
        positions.extend(item['witness']['start'] for item in result['matches'])
        ranges.append(result['scanned_range'])
        assert result['has_more'] == (result['next_query'] is not None)
        args = result['next_query']
    assert positions == [2, 3, 4, 5, 9, 10, 11]
    assert ranges[-1]['end'] == len(raw)
    spanning = query(store, row, 'aβa')
    assert spanning['matches'][0]['witness']['start'] == 6


def test_no_match_exact_eof_and_multibyte_context_clipping(store):
    row = source(store, 'αXβγ'.encode())
    empty = query(store, row, 'missing')
    assert empty['matches'] == [] and empty['scanned_range'] == {'start': 0, 'end': 7}
    assert query(store, row, 'X', offset=7)['matches'] == []
    match, = query(store, row, 'X', context_bytes=1)['matches']
    assert match['context']['text'] == 'X'
    with pytest.raises(ContractError, match='not_utf8_boundary'):
        query(store, row, 'X', offset=1)


@pytest.mark.parametrize('field,value', [('needle', ''), ('needle', None), ('needle', True),
    ('offset', True), ('offset', -1), ('offset', 99), ('offset', 1.5), ('offset', float('nan')),
    ('limit', False), ('limit', 0), ('limit', float('inf')), ('context_bytes', -1), ('context_bytes', True)])
def test_invalid_parameters_are_not_no_match(store, field, value):
    row = source(store, b'abc')
    args = {'needle': 'a', field: value}
    with pytest.raises(ContractError):
        query(store, row, **args)


@pytest.mark.parametrize('raw,code', [(b'a\xff', 'not_utf8'), (b'a\xe2', 'not_utf8'), (b'a\x00', 'binary')])
def test_binary_and_invalid_utf8_fail(store, raw, code):
    with pytest.raises(ContractError, match=code):
        query(store, source(store, raw), 'a')


def test_explicit_text_does_not_fall_back_to_original(store):
    row = source(store, b'only original')
    with pytest.raises(ContractError, match='representation_unavailable'):
        query(store, row, 'original', representation='text')


def test_bounded_search_does_not_validate_unexamined_suffix_or_read_full_source(store, monkeypatch):
    monkeypatch.setattr('gene_annotation_episode.source_locations.CHUNK_BYTES', 8)
    row = source(store, b'aa aa   ' + b'x' * 1000 + b'\xff')
    reads, original = [], Path.open
    class Observed:
        def __init__(self, handle):
            self.handle = handle
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return self.handle.__exit__(*args)
        def __getattr__(self, name):
            return getattr(self.handle, name)
        def read(self, size):
            assert size >= 0
            value = self.handle.read(size)
            reads.append(len(value))
            return value
    monkeypatch.setattr(Path, 'open', lambda path, *args, **kwargs:
        Observed(original(path, *args, **kwargs)) if path.name == row['artifact_ref'][9:]
        else original(path, *args, **kwargs))
    result = query(store, row, 'aa', limit=1, context_bytes=0)
    assert sum(reads) == 11  # boundary byte + 8 scan bytes + exact 2-byte context
    assert result['has_more'] and result['scanned_range']['end'] == 8
    assert result['total_bytes'] == 1009
    assert result['next_query']['offset'] == 3
    with pytest.raises(ContractError, match='not_utf8'):
        query(store, row, 'absent')


def test_context_cannot_hide_malformed_source_eof_as_a_clipped_character(store, monkeypatch):
    monkeypatch.setattr('gene_annotation_episode.source_locations.CHUNK_BYTES', 8)
    row = source(store, b'aa aa   more\xe2')
    with pytest.raises(ContractError, match='not_utf8'):
        query(store, row, 'aa', limit=1, context_bytes=100)


def test_native_readers_receive_unchanged_witness_and_keep_censor_and_unit_checks(store):
    raw = 'α <0.005 nmol/min/mg; exact 2 µM/min'.encode()
    row = source(store, raw)
    sources = _Sources(lambda ref, rep: {'artifact_ref': row['artifact_ref'], 'content': raw})
    witness = query(store, row, '0.005')['matches'][0]['witness']
    original = deepcopy(witness)
    parsed = read_source_number({'witness': witness, 'number_start': 0, 'number_end': 5},
        sources=sources, role='rate')
    assert parsed['relation'] == 'lt' and parsed['value'] == .005
    assert witness == original
    unit = query(store, row, 'nmol/min')['matches'][0]['witness']
    with pytest.raises(ExperimentalContractError, match='partial_source_rate_unit'):
        read_source_rate_unit(unit, sources=sources)
    full = query(store, row, 'nmol/min/mg')['matches'][0]['witness']
    assert read_source_rate_unit(full, sources=sources)['multiplier'] == 1000


def test_registry_original_arguments_replay_receipts_scope_and_no_publication(store, monkeypatch):
    row = source(store, b'exact exact')
    registry = ToolRegistry(store)
    args = {'source_ref': row['id'], 'representation': 'original', 'needle': 'exact'}
    scope = store.validate_scope()
    before = len(store.list('source'))
    outcome = registry.execute('source.locate', args, scope=scope, operation_key='literal',
        permitted_record_refs=(row['id'],))
    assert outcome['status'] == 'completed', outcome
    assert outcome['record_refs'] == [] and len(store.list('source')) == before
    assert not store.list('observation') and not store.list('assessment')
    saved = store.db.execute('SELECT arguments FROM tool_operations WHERE operation_key=?', ('literal',)).fetchone()[0]
    assert saved == canonical(args) and 'offset' not in args
    def forbidden(*args, **kwargs):
        raise AssertionError('replay opened source bytes')
    monkeypatch.setattr(Path, 'open', forbidden)
    assert registry.execute('source.locate', args, scope=scope, operation_key='literal',
        permitted_record_refs=(row['id'],)) == outcome
    denied = registry.execute('source.locate', args, scope=scope, operation_key='literal', permitted_record_refs=())
    assert denied['feedback']['code'] == 'source_location_source_not_received'
    with pytest.raises(ContractError, match='key_reused'):
        registry.execute('source.locate', {**args, 'limit': 1}, scope=scope, operation_key='literal',
            permitted_record_refs=(row['id'],))
    monkeypatch.setattr(store, 'reference_subset', lambda refs, scope: [])
    denied = registry.execute('source.locate', args, scope=scope, operation_key='literal',
        permitted_record_refs=(row['id'],))
    assert denied['feedback']['code'] == 'source_location_outside_scope'


def test_identity_conflicts_and_storage_failures_are_specific(store, monkeypatch):
    row = source(store, b'abc')
    read = store.get
    monkeypatch.setattr(store, 'get', lambda ref: {**read(ref), 'version': 'tampered'} if ref == row['id'] else read(ref))
    with pytest.raises(ContractError, match='identity_conflict'):
        query(store, row, 'abc')
    monkeypatch.setattr(store, 'get', read)
    path = store.path / 'artifacts' / row['artifact_ref'][9:11] / row['artifact_ref'][9:]
    path.unlink()
    outcome = ToolRegistry(store).execute('source.locate', {'source_ref': row['id'],
        'representation': 'original', 'needle': 'abc'}, permitted_record_refs=(row['id'],))
    assert outcome['status'] == 'failed' and outcome['feedback']['code'] == 'adapter_execution_failed'
    assert outcome['result'] is None


@pytest.mark.parametrize('stage', ['scan', 'context'])
def test_short_source_or_context_read_is_an_integrity_failure_not_a_loop_or_match(store, monkeypatch, stage):
    row = source(store, b'one one')
    original = Path.open
    class ShortRead:
        def __init__(self, handle):
            self.handle, self.reads = handle, 0
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return self.handle.__exit__(*args)
        def seek(self, *args):
            return self.handle.seek(*args)
        def tell(self):
            return self.handle.tell()
        def read(self, size):
            self.reads += 1
            value = self.handle.read(size)
            # First read checks the offset; second scans; later reads context.
            if self.reads == (2 if stage == 'scan' else 3):
                return value[:-1]
            return value
    monkeypatch.setattr(Path, 'open', lambda path, *args, **kwargs:
        ShortRead(original(path, *args, **kwargs)) if path.name == row['artifact_ref'][9:]
        else original(path, *args, **kwargs))
    outcome = ToolRegistry(store).execute('source.locate', {'source_ref': row['id'],
        'representation': 'original', 'needle': 'one'}, permitted_record_refs=(row['id'],))
    assert outcome['status'] == 'invalid'
    assert outcome['feedback']['code'] == 'source_location_artifact_size_conflict'
    assert outcome['result'] is None


@pytest.mark.parametrize('bad', [True, float('nan'), float('inf'), -1, 1.5])
def test_registry_bad_indices_are_structured_failures(store, bad):
    row = source(store, b'abc')
    outcome = ToolRegistry(store).execute('source.locate', {'source_ref': row['id'],
        'representation': 'original', 'needle': 'a', 'offset': bad},
        permitted_record_refs=(row['id'],))
    assert outcome['status'] == 'invalid' and outcome['result'] is None


def test_registry_reopens_original_result_read_only_without_source_io(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        row = source(store, b'exact retained quote')
        args = {'source_ref': row['id'], 'representation': 'original', 'needle': 'retained'}
        scope = store.validate_scope()
        outcome = ToolRegistry(store).execute('source.locate', args, scope=scope,
            operation_key='retained', permitted_record_refs=(row['id'],))
        assert outcome['status'] == 'completed'
    with Store(tmp_path) as reopened:
        registry = ToolRegistry(reopened)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved-only reopen performed source I/O')
        monkeypatch.setattr(Path, 'open', forbidden)
        reopened.db.execute('PRAGMA query_only=ON')
        assert registry.execute('source.locate', args, scope=scope,
            operation_key='retained', permitted_record_refs=(row['id'],)) == outcome


def test_complete_from_zero_scan_verifies_content_addressed_bytes(store):
    row = source(store, b'original')
    path = store.path / 'artifacts' / row['artifact_ref'][9:11] / row['artifact_ref'][9:]
    path.write_bytes(b'tampered')
    with pytest.raises(ContractError, match='artifact_digest_mismatch'):
        query(store, row, 'missing')


@pytest.mark.parametrize('change', [{'representation': 'text'}, {'representation': 'stdout'}, {'offset': 999}])
def test_registry_failed_attempt_replays_its_original_failure_details(store, change):
    row = source(store, b'original only')
    registry = ToolRegistry(store)
    args = {'source_ref': row['id'], 'representation': 'original', 'needle': 'only', **change}
    first = registry.execute('source.locate', args, operation_key='unavailable', permitted_record_refs=(row['id'],))
    assert first['status'] == 'invalid'
    if change == {'representation': 'text'}:
        assert first['feedback']['detail'] == {'representation': 'text'}
    assert registry.execute('source.locate', args, operation_key='unavailable', permitted_record_refs=(row['id'],)) == first
