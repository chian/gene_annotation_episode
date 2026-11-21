"""The input list of the source coverage improvement episode: the unread windows in document order, shrinking as
completed source reads consume them."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_reading_windows import (
    consumed_ranges, reading_windows, remaining_windows)

CONTENT = ('é' * 5 + 'abcdefghij' * 3).encode('utf-8')     # 10 + 30 bytes


def _read(start, end, status='completed', representation='text'):
    return {'kind': 'tool', 'tool': 'source_read',
            'outcome': {'status': status, 'result': {'source_ref': 's', 'representation': representation,
                                                      'start': start, 'end': end}}}


def test_windows_run_from_the_starting_window_to_the_end_on_character_boundaries():
    windows = reading_windows(CONTENT, 0, 7)
    assert windows[0] == [0, 6] and windows[-1][1] == len(CONTENT)
    assert all(a[1] == b[0] for a, b in zip(windows, windows[1:]))
    assert reading_windows(CONTENT, 10, 15) == [[10, 25], [25, 40]]
    assert reading_windows(CONTENT, 40, 5) == []


def test_a_completed_read_consumes_the_windows_it_covers_entirely():
    windows = reading_windows(CONTENT, 10, 10)
    assert remaining_windows(windows, consumed_ranges([_read(10, 20)], 's', 'text')) == windows[1:]
    assert remaining_windows(windows, consumed_ranges([_read(10, 15), _read(15, 30)], 's', 'text')) == windows[2:]
    assert remaining_windows(windows, consumed_ranges([_read(10, 19)], 's', 'text')) == windows


def test_failed_or_other_representation_reads_consume_nothing():
    windows = reading_windows(CONTENT, 10, 10)
    outcomes = [_read(10, 40, status='invalid'), _read(10, 40, representation='original')]
    assert remaining_windows(windows, consumed_ranges(outcomes, 's', 'text')) == windows
