"""Focused read orchestration; full publication authentication is separate."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.bvbrc_appservice_saved_results import read_latest_adapter_result


class PublicationFixture:
    """Explicitly controlled publication reader, not native custody evidence."""
    def __init__(self):
        self.context = SimpleNamespace(run_id='run', episode_id='results', role='results',
            scope={'target': 'gene'}, assignment={'selector': 'original'})
        self.calls, self.checked, self.contents_checked = [], [], []
        self.host = SimpleNamespace(custody=SimpleNamespace(authenticate=self.authenticate))
        self.api = SimpleNamespace(_own_outcomes=self.outcomes)
        self.saved = {}

    def authenticate(self, context, *, allow_unsaved):
        assert context is self.context and allow_unsaved is True
        self.checked.append(context.episode_id)

    def add(self, index, *, status='completed', adapter='bvbrc_msa', contents=True):
        ref = f'result:{index}'
        body = {'run_id': 'run', 'episode_id': 'results', 'scope': {'target': 'gene'},
            'assignment': {'selector': 'original'}, 'reference': ref, 'status': status,
            'publication': {'origin': {'operation_key': f'run:results:{index}'},
                'adapter_result': {'adapter_id': adapter,
                    'sheet_content': {'source_ref': 'sheet:' + str(index)} if contents else None,
                    'components_content': {'source_ref': 'components:' + str(index)} if contents else None}},
            'publication_inputs': {'current_snapshot': {'retrieved_at': 'original-time:' + str(index)}}}
        self.saved[index] = body
        return body

    def outcomes(self, context):
        assert context is self.context
        for index in sorted(self.saved):
            yield None, {'result': {'result_record_refs': [f'result:{index}']}}

    def read(self, reference, scope, *, episode_id):
        self.calls.append(reference)
        value = self.saved[int(reference.split(':')[-1])]
        if value.get('corrupt'):
            raise ValueError('actual-publication-check-failed')
        assert scope == self.context.scope and episode_id == self.context.episode_id
        return deepcopy(value)

    def _content(self, binding, origin, kind, stamp):
        index = int(binding['source_ref'].split(':')[-1])
        assert origin == {'operation_key': f'run:results:{index}'}
        assert stamp == 'original-time:' + str(index)
        self.contents_checked.append((binding['source_ref'], origin, kind, stamp))
        return {'value': index, 'kind': kind}


def test_latest_numeric_index_is_read_once_with_original_content_origin():
    p = PublicationFixture()
    p.add(2)
    expected = p.add(10)
    p.add(1)
    body, sheet, components = read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))
    assert body == expected
    assert sheet == {'value': 10, 'kind': 'sheet'}
    assert components == {'value': 10, 'kind': 'components'}
    assert p.calls == ['result:10'] and len(p.contents_checked) == 2


def test_newest_partial_is_not_replaced_by_older_completion():
    p = PublicationFixture()
    p.add(2)
    p.add(10, status='partial')
    assert read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))[0]['status'] == 'partial'


def test_invalid_latest_publication_raises_without_falling_back():
    p = PublicationFixture()
    p.add(2)
    p.add(10)['corrupt'] = True
    with pytest.raises(ValueError, match='actual-publication-check-failed'):
        read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))
    assert p.calls == ['result:10'] and not p.contents_checked


def test_each_call_reauthenticates_and_observes_changed_saved_state():
    p = PublicationFixture()
    p.add(2)
    read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))
    p.saved[2]['corrupt'] = True
    with pytest.raises(ValueError):
        read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))
    assert p.calls == ['result:2', 'result:2'] and len(p.checked) == 2


@pytest.mark.parametrize('field,value', [('run_id', 'other'), ('episode_id', 'other'),
    ('scope', {'target': 'other'}), ('assignment', {'selector': 'other'})])
def test_other_ownership_is_rejected_before_content_read(field, value):
    p = PublicationFixture()
    p.add(2)[field] = value
    with pytest.raises(ValueError, match='owner_conflict'):
        read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))
    assert not p.contents_checked


def test_absent_contents_stay_none_without_substitute():
    p = PublicationFixture()
    p.add(2, status='partial', contents=False)
    assert read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))[1:] == (None, None)
    assert not p.contents_checked


def test_other_adapter_is_authenticated_before_older_matching_result():
    p = PublicationFixture()
    p.add(2)
    p.add(10, adapter='bvbrc_gene_tree')
    assert read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',))[0]['reference'] == 'result:2'
    assert p.calls == ['result:10', 'result:2']


def test_no_owned_result_is_none_and_nonresults_context_does_not_enumerate():
    p = PublicationFixture()
    assert read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',)) is None
    p.context.role = 'scientific_process'
    p.add(2)
    assert read_latest_adapter_result(p, p.context, adapter_ids=('bvbrc_msa',)) is None
    assert not p.calls


@pytest.mark.parametrize('value', [(), ['bvbrc_msa'], ('bvbrc_msa', 'bvbrc_msa'), (True,), ('',)])
def test_adapter_filter_is_an_exact_nonempty_tuple(value):
    p = PublicationFixture()
    with pytest.raises(ValueError, match='adapter_selection_invalid'):
        read_latest_adapter_result(p, p.context, adapter_ids=value)
    assert not p.checked
