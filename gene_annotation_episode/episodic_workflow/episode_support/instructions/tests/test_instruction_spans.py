import pytest

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span

TEXT = 'Intro. On a fresh provider conversation, read history. Do not execute native provider tools. End.'


def test_replaces_from_start_marker_up_to_end_marker():
    replaced = replace_span(TEXT, 'On a fresh provider conversation,', 'Do not execute native provider tools.',
                            'Use request_context exchanges.\n')
    assert replaced == 'Intro. Use request_context exchanges.\nDo not execute native provider tools. End.'


def test_missing_or_misordered_markers_raise():
    with pytest.raises(ValueError, match='start_marker'):
        replace_span(TEXT, 'absent', 'End.', '')
    with pytest.raises(ValueError, match='follow_start'):
        replace_span(TEXT, 'Do not execute', 'Intro.', '')
    with pytest.raises(TypeError):
        replace_span(TEXT, 'Intro.', 'End.', None)
