"""Real filesystem controls for the original confined byte-reading functions."""
import os

import pytest

from gene_annotation_episode.episodic_workflow.root.library import retained_file_read as reader


def test_complete_bytes_are_returned_without_changing_the_file(tmp_path):
    source = tmp_path / 'original.bin'
    raw = b'\x00\xfforiginal\r\n' * 137
    source.write_bytes(raw)
    before = source.stat()
    assert reader.read_bytes(source) == raw
    after = source.stat()
    assert reader._stable(before, after)
    assert source.read_bytes() == raw


def test_empty_file_is_a_valid_complete_read(tmp_path):
    source = tmp_path / 'empty'
    source.write_bytes(b'')
    assert reader.read_bytes(source) == b''


@pytest.mark.parametrize('kind', ['file', 'parent'])
def test_symlink_at_file_or_parent_is_rejected(tmp_path, kind):
    real = tmp_path / 'real'
    real.mkdir()
    source = real / 'source'
    source.write_bytes(b'original bytes')
    alias = tmp_path / 'alias'
    alias.symlink_to(source if kind == 'file' else real, target_is_directory=kind == 'parent')
    selected = alias if kind == 'file' else alias / 'source'
    with pytest.raises(OSError):
        reader.read_bytes(selected)
    assert source.read_bytes() == b'original bytes'


def test_directory_is_not_accepted_as_file_content(tmp_path):
    with pytest.raises(IsADirectoryError):
        reader.read_bytes(tmp_path)


def test_missing_file_preserves_original_os_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        reader.read_bytes(tmp_path / 'absent')


@pytest.mark.parametrize('value,absolute', [
    ('relative', True), ('/absolute', False), ('/a/../b', True),
    ('/a//b', True), ('//a', True), ('/', True), ('.', False),
    ('a\\b', False), ('a\n', False), ('a\x00', False), (True, False),
])
def test_original_path_validation_rejects_ambiguous_or_wrong_kind(value, absolute):
    with pytest.raises(ValueError, match='^fba_invalid_path$'):
        reader.path_value(value, absolute=absolute)


def test_actual_file_change_during_read_is_rejected_and_stream_closed(tmp_path, monkeypatch):
    source = tmp_path / 'changing'
    source.write_bytes(b'first bytes')
    original_fstat = os.fstat
    original_fdopen = os.fdopen
    observations = []
    streams = []

    def observe(fd):
        observations.append(fd)
        # regular() checks file type, then read_bytes() observes its before
        # and after stats. Change the real file before that final observation.
        if len(observations) == 3:
            source.write_bytes(b'a different and longer real file')
        return original_fstat(fd)

    def opened(*args, **kwargs):
        stream = original_fdopen(*args, **kwargs)
        streams.append(stream)
        return stream

    monkeypatch.setattr(reader.os, 'fstat', observe)
    monkeypatch.setattr(reader.os, 'fdopen', opened)
    with pytest.raises(ValueError, match='^fba_file_changed_during_read$'):
        reader.read_bytes(source)
    assert source.read_bytes() == b'a different and longer real file'
    assert len(streams) == 1 and streams[0].closed


def test_regular_closes_its_stream_when_the_consumer_raises(tmp_path):
    source = tmp_path / 'original'
    source.write_bytes(b'original')
    with pytest.raises(RuntimeError, match='^consumer_failure$'):
        with reader.regular(source) as stream:
            assert stream.read(2) == b'or'
            raise RuntimeError('consumer_failure')
    assert stream.closed
    assert source.read_bytes() == b'original'
