"""The run journal, the progress clock and typed forms, on a real SQLite journal and the real boot clock."""
import math

import pytest

from episode_runtime import JournalError, ProgressClock, RunJournal
from episode_runtime.journal import EpisodeRecorder

PATH = (('example__episode', 'key'),)


@pytest.fixture
def journal(tmp_path):
    return RunJournal(tmp_path / 'journal.sqlite3')


def test_a_rebuilt_number_equals_its_recorded_spelling_but_not_a_boolean(journal):
    journal.open_run('run', {'entry': 1})
    journal.open_episode('run', PATH, 'example/episode', {'request': {'credit': 6}})
    assert journal.open_episode('run', PATH, 'example/episode', {'request': {'credit': 6.0}}) is True
    journal.begin_unit('run', PATH, 0, 'unit:0', 'key', 'digest')
    journal.record_unit('run', PATH, 0, 'unit:0', {'credit': 6.0}, {'value': 1}, None, {'stop': False})
    journal.record_unit('run', PATH, 0, 'unit:0', {'credit': 6}, {'value': 1.0}, None, {'stop': False})
    with pytest.raises(JournalError, match='recorded_unit_differs'):
        journal.record_unit('run', PATH, 0, 'unit:0', {'credit': 6.5}, {'value': 1}, None, {'stop': False})
    journal.begin_unit('run', PATH, 1, 'unit:1', 'key', 'digest')
    journal.record_unit('run', PATH, 1, 'unit:1', {'done': True}, None, None, {'stop': True})
    with pytest.raises(JournalError, match='recorded_unit_differs'):
        journal.record_unit('run', PATH, 1, 'unit:1', {'done': 1}, None, None, {'stop': True})


def test_progress_receipts_carry_the_first_receipt_as_reference_span(journal):
    recorder = EpisodeRecorder(journal, 'run', PATH)
    clock = ProgressClock(recorder, run_id='run', episode_id='episode')
    first, second = clock.receipt(0), clock.receipt(1)
    assert first['status'] == second['status'] == 'available'
    reference = first['reference_observation_monotonic_ns']
    assert reference == first['observed_monotonic_ns'] == second['reference_observation_monotonic_ns']
    assert clock.origin['monotonic_ns'] < reference <= second['observed_monotonic_ns']
    for receipt in (first, second):
        assert math.isclose(receipt['reference_elapsed_seconds'], (reference - receipt['origin_monotonic_ns']) / 1e9)
        assert math.isclose(receipt['elapsed_seconds'],
                            (receipt['observed_monotonic_ns'] - receipt['origin_monotonic_ns']) / 1e9)
    resumed = ProgressClock(EpisodeRecorder(journal, 'run', PATH), run_id='run', episode_id='episode')
    assert resumed.receipt(1) == second


def test_a_decision_clock_is_captured_once_per_unit_position_and_names_the_last_progress_receipt(journal):
    clock = ProgressClock(EpisodeRecorder(journal, 'run', PATH), run_id='run', episode_id='episode')
    first = clock.decision_point(0)
    assert first.status == 'available' and first.progress_time is None and first.elapsed_seconds > 0
    assert first.began_at == clock.origin['captured_at'] < first.now
    assert clock.decision_point(0) == first
    with pytest.raises(LookupError, match='progress_receipt_not_recorded_for_completed_unit:0'):
        clock.decision_point(1)
    receipt = clock.receipt(0)
    second = clock.decision_point(1)
    assert second.progress_time == receipt and second.elapsed_seconds > first.elapsed_seconds
    resumed = ProgressClock(EpisodeRecorder(journal, 'run', PATH), run_id='run', episode_id='episode')
    assert resumed.decision_point(0) == first and resumed.decision_point(1) == second


def test_the_yield_controllers_import_nothing_from_the_runner():
    import ast
    import yield_control
    tree = ast.parse(open(yield_control.__file__).read())
    imported = [node.module if isinstance(node, ast.ImportFrom) else name.name for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for name in (node.names if isinstance(node, ast.Import) else [node])]
    assert not [name for name in imported if name and name.split('.')[0] in ('episode_runtime', 'method_loop')]
    from episode_runtime import progress
    assert progress.PROGRESS_TIME_VERSION is yield_control.PROGRESS_TIME_VERSION


def test_nested_optional_and_choice_fields_are_admitted_at_the_boundary():
    from method_loop import ChoiceField, Field, FormError, RecordForm
    job = RecordForm({'name': Field('text', 'Job name'), 'cores': Field('integer', 'Cores', required=False)})
    form = RecordForm({'job': Field('record', 'The launched job', form=job),
                       'monitors': Field('list', 'Monitor requests', items=job),
                       'pattern': ChoiceField('text', 'Thought pattern', ('P01', 'P02')),
                       'note': Field('text', 'Optional note', required=False)})
    admitted = form.admit({'job': {'name': 'a'}, 'monitors': [{'name': 'b', 'cores': 2}], 'pattern': 'P02'}, 'x')
    assert admitted == {'job': {'name': 'a'}, 'monitors': [{'name': 'b', 'cores': 2}], 'pattern': 'P02'}
    for value, code in (({'job': {'name': 'a', 'extra': 1}, 'monitors': [], 'pattern': 'P01'}, 'x:job_unknown_field'),
                        ({'job': {'name': 'a'}, 'monitors': [{'cores': 1}], 'pattern': 'P01'},
                         r'x:monitors\[0\]_missing_field:name'),
                        ({'job': {'name': 'a'}, 'monitors': [], 'pattern': 'P03'}, 'x_not_an_offered_option:pattern'),
                        ({'job': {'name': 'a'}, 'monitors': []}, 'x_missing_field:pattern')):
        with pytest.raises(FormError, match=code):
            form.admit(value, 'x')
    assert form.choices == {'pattern': ('P01', 'P02')}
    with pytest.raises(ValueError, match='field_form_requires_type_record'):
        Field('list', 'Wrong', form=job)


def test_subset_fields_admit_unique_offered_elements():
    from method_loop import FormError, RecordForm, SubsetField
    form = RecordForm({'tools': SubsetField('text', 'Selected tools', ('a', 'b', 'c'))})
    assert form.admit({'tools': ['c', 'a']}, 'x') == {'tools': ['c', 'a']}
    assert form.admit({'tools': []}, 'x') == {'tools': []}
    for value, code in ((['a', 'd'], 'x:tools_not_an_offered_option:1'), (['b', 'b'], 'x:tools_repeats_an_option:1'),
                        ('a', 'x:tools_must_be_list')):
        with pytest.raises(FormError, match=code):
            form.admit({'tools': value}, 'x')
    assert form.choices == {'tools': ('a', 'b', 'c')}


def test_a_service_read_is_recorded_once_per_request_and_unit_position(journal):
    asked = []

    def ask(value):
        def compute():
            asked.append(value)
            return value
        return compute
    request = {'service': 'table', 'member': 'estimate', 'arguments': ['job']}
    assert journal.service_read('run', PATH, 0, request, ask({'seconds': 3})) == {'seconds': 3}
    assert journal.service_read('run', PATH, 0, request, ask({'seconds': 9})) == {'seconds': 3}     # the record
    assert journal.service_read('run', PATH, 1, request, ask({'seconds': 9})) == {'seconds': 9}     # next position
    other = {**request, 'arguments': ['other']}
    assert journal.service_read('run', PATH, 0, other, ask(None)) is None
    assert journal.service_read('run', PATH, 0, other, ask(4)) is None                              # a recorded null
    assert asked == [{'seconds': 3}, {'seconds': 9}, None]
    assert journal.service_reads('run', PATH) == [
        {'position': 0, 'request': request, 'value': {'seconds': 3}},
        {'position': 1, 'request': request, 'value': {'seconds': 9}},
        {'position': 0, 'request': other, 'value': None}]
    assert journal.service_reads('run', (('other__episode', 'key'),)) == []


def test_a_unit_that_began_and_is_rebuilt_differently_is_refused(journal):
    """The journal's guard for a unit that runs again: the same position must rebuild the same label, operation
    key and arguments (a decision reads the outside world only through recorded reads, so only changed episode
    code or a changed recorded run can make it differ)."""
    assert journal.begin_unit('run', PATH, 0, 'tool:a:0', 'op_1', 'digest_1') is False
    assert journal.begin_unit('run', PATH, 0, 'tool:a:0', 'op_1', 'digest_1') is True
    for label, key, digest in (('tool:b:0', 'op_1', 'digest_1'), ('tool:a:0', 'op_2', 'digest_1'),
                               ('tool:a:0', 'op_1', 'digest_2')):
        with pytest.raises(JournalError, match='abandoned_unit_differs'):
            journal.begin_unit('run', PATH, 0, label, key, digest)
    assert journal.times_begun('run', PATH, 0) == 2


def test_the_initial_credit_of_an_episode_is_computed_once_and_afterwards_read_from_its_record(journal):
    journal.open_run('run', {'entry': 1})
    journal.open_episode('run', PATH, 'example/episode', {'request': {}})
    assert journal.episodes('run')[0]['initial_credit'] is None      # the Episode was built and not yet entered
    asked = []

    def credit(value):
        def compute():
            asked.append(value)
            return value
        return compute
    assert journal.initial_credit('run', PATH, credit(0.25)) == 0.25
    assert journal.initial_credit('run', PATH, credit(7.0)) == 0.25 and asked == [0.25]
    assert journal.episodes('run')[0]['initial_credit'] == 0.25
    reopened = RunJournal(journal.path)                              # another process over the same file
    assert reopened.initial_credit('run', PATH, credit(7.0)) == 0.25 and asked == [0.25]
    # A whole number is recorded and given back as it was computed.
    other = (('example__episode', 'other'),)
    journal.open_episode('run', other, 'example/episode', {'request': {}})
    assert [type(journal.initial_credit('run', other, credit(2))) for _ in range(2)] == [int, int]
