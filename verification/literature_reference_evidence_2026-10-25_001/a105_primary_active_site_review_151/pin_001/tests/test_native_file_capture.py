"""Real Store custody checks for contract419; no scientific or episode claims."""
from contextlib import contextmanager
from copy import deepcopy
import errno
import hashlib
import os
from pathlib import Path
import socket
import sqlite3

import pytest

from gene_annotation_episode import native_file_capture as capture
from gene_annotation_episode.state import Store


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "retained") as value:
        yield value


@pytest.fixture
def producer(tmp_path):
    path = tmp_path / "producer"
    path.mkdir()
    return path


def declaration(path="result.bin", data=b"abc", **changes):
    return {"relative_path": path, "format": "opaque_native_bytes", "state": "present",
        "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), **changes}


def saved(store, producer, data=b"abc"):
    (producer / "result.bin").write_bytes(data)
    return capture.capture_native_file(store, directory=str(producer),
        relative_path="result.bin", format="opaque_native_bytes")


def error_code(code, function, *args, **kwargs):
    with pytest.raises(capture.NativeFileCaptureError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code
    assert str(caught.value) == code


def assert_no_artifacts(store):
    assert store.db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
    assert list((store.path / "artifacts").iterdir()) == []


def test_complete_capture_streams_multiple_chunks(store, producer, monkeypatch):
    data = bytes(range(256)) * 8192 + b"final incomplete chunk\0\xff"
    (producer / "result.bin").write_bytes(data)
    original_open = Path.open
    reads = []

    class ReadObserver:
        def __init__(self, path, stream):
            self.path, self.stream = path, stream

        def read(self, size=-1):
            assert 0 < size <= 1024 * 1024, "unbounded file read"
            value = self.stream.read(size)
            reads.append((str(self.path), size, len(value)))
            return value

    @contextmanager
    def observed_open(path, *args, **kwargs):
        with original_open(path, *args, **kwargs) as stream:
            assert args == ("rb",)
            yield ReadObserver(path, stream)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", observed_open)
        patch.setattr(Path, "read_bytes", lambda self: pytest.fail("whole-file read"))
        identity = capture.capture_native_file(store, directory=str(producer),
            relative_path="result.bin", format="native/v1", media_type="application/x-native")
    digest = hashlib.sha256(data).hexdigest()
    assert identity == {"artifact_ref": "artifact_" + digest, "sha256": digest,
        "size_bytes": len(data), "format": "native/v1"}
    assert capture.retained_native_file(store, identity).read_bytes() == data
    assert store.get(identity["artifact_ref"])["media_type"] == "application/x-native"
    producer_reads = [length for path, _, length in reads if path.startswith("/proc/self/fd/")]
    assert producer_reads == [1048576, 1048576, len(data) - 2097152, 0]
    retained_reads = [length for path, _, length in reads if not path.startswith("/proc/self/fd/")]
    assert retained_reads == producer_reads
    assert not list((store.path / "artifacts").glob(".capture-*"))


def test_zero_present_absent_missing_and_good_preserve_order(store, producer):
    (producer / "empty").touch()
    (producer / "good").write_bytes(b"abc")
    # A declared absence is not today's filesystem state.
    (producer / "absent").write_bytes(b"must not be captured")
    declarations = [declaration("missing"), declaration("empty", b""),
        declaration("absent", state="absent", sha256=None, size_bytes=None), declaration("good")]
    rows = capture.capture_declared_native_files(store, directory=str(producer), declarations=declarations)
    assert [row["declared"] for row in rows] == declarations
    assert [row["outcome"] for row in rows] == ["unavailable", "verified", "declared_absent", "verified"]
    assert rows[0]["observed"] is None and rows[0]["failure"] == "capture_file_unavailable"
    assert rows[2]["observed"] is None and rows[2]["failure"] is None
    assert rows[1]["observed"]["size_bytes"] == 0
    assert rows[1]["observed"]["sha256"] == hashlib.sha256(b"").hexdigest()
    assert rows[3]["observed"]["size_bytes"] == 3
    assert all(rows[i]["failure"] is None for i in (1, 3))
    assert store.db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 2


def test_absence_and_empty_list_do_not_inspect_producer(store, producer, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("producer was inspected for an absent declaration")
    monkeypatch.setattr(capture.os, "open", unexpected)
    declarations = [declaration("never/check", state="absent", sha256=None, size_bytes=None)]
    assert capture.capture_declared_native_files(store, directory=str(producer / "nonexistent"),
        declarations=declarations) == [{"declared": declarations[0], "observed": None,
            "outcome": "declared_absent", "failure": None}]
    assert capture.capture_declared_native_files(store, directory=str(producer), declarations=[]) == []


@pytest.mark.parametrize("change", [{"sha256": "0" * 64}, {"size_bytes": 4},
    {"sha256": "0" * 64, "size_bytes": 0}])
def test_declared_mismatch_keeps_actual_bytes(store, producer, change):
    (producer / "result.bin").write_bytes(b"abc")
    declared = declaration(**change)
    row, = capture.capture_declared_native_files(store, directory=str(producer), declarations=[declared])
    assert row["outcome"] == "digest_mismatch"
    assert row["failure"] == "capture_file_digest_mismatch"
    assert row["declared"] == declared
    assert row["observed"]["size_bytes"] == 3
    assert row["observed"]["sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert capture.retained_native_file(store, row["observed"]).read_bytes() == b"abc"


@pytest.mark.parametrize("bad", [None, [], {}, {"extra": True},
    {"format": ""}, {"format": "native\x00"}, {"format": "native\x85"},
    {"state": True}, {"state": "unknown"}, {"size_bytes": True}, {"size_bytes": -1},
    {"size_bytes": 3.0}, {"size_bytes": "3"}, {"size_bytes": None}, {"sha256": None},
    {"sha256": "A" * 64}, {"sha256": "g" * 64}, {"sha256": "0" * 63},
    {"state": "absent"}, {"state": "absent", "sha256": None}])
def test_malformed_declarations_rejected_before_any_capture(store, producer, bad):
    (producer / "good").write_bytes(b"abc")
    invalid = {**declaration(), **bad} if type(bad) is dict and bad else bad
    error_code("invalid_file_declaration", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=[declaration("good"), invalid])
    assert_no_artifacts(store)


@pytest.mark.parametrize("field", ["relative_path", "format", "state", "sha256", "size_bytes"])
def test_missing_declaration_fields_are_rejected_before_capture(store, producer, field):
    invalid = declaration()
    del invalid[field]
    error_code("invalid_file_declaration", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=[declaration("good"), invalid])
    assert_no_artifacts(store)


@pytest.mark.parametrize("declarations", [None, (), {}, (declaration(),)])
def test_declarations_must_be_a_list(store, producer, declarations):
    error_code("invalid_file_declaration", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=declarations)
    assert_no_artifacts(store)


def test_duplicate_relative_paths_reject_before_capture(store, producer):
    (producer / "result.bin").write_bytes(b"abc")
    error_code("invalid_file_declaration", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=[declaration(), declaration(format="different")])
    assert_no_artifacts(store)


@pytest.mark.parametrize("path", [None, 1, "", ".", "..", "a/..", "a/../b", "/a", "//a",
    "a//b", "a/./b", "./a", "a/", "a\0b", "a\nb", "a\rb", "a\\b"])
def test_invalid_relative_path_rejects_whole_list(store, producer, path):
    error_code("invalid_capture_path", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=[declaration("good"), declaration(path)])
    assert_no_artifacts(store)


@pytest.mark.parametrize("path", [None, 1, "", "/", "//", "//tmp", "relative", ".", "/tmp/",
    "/tmp//x", "/tmp/./x", "/tmp/../x", "/tmp\0x", "/tmp\nx", "/tmp\rx", "/tmp\\x"])
def test_invalid_directory_rejects_before_capture_even_for_absence(store, path):
    error_code("invalid_capture_path", capture.capture_declared_native_files, store,
        directory=path, declarations=[declaration(state="absent", sha256=None, size_bytes=None)])
    assert_no_artifacts(store)


@pytest.mark.parametrize("field,value", [("format", ""), ("format", None), ("format", "a\t"),
    ("format", "a\x7f"), ("media_type", ""), ("media_type", None), ("media_type", "a\r"),
    ("media_type", "a\x85")])
def test_capture_labels_reject_control_characters_before_io(store, producer, field, value):
    kwargs = {"directory": str(producer), "relative_path": "result.bin", "format": "opaque"}
    kwargs[field] = value
    error_code("invalid_file_declaration", capture.capture_native_file, store, **kwargs)
    assert_no_artifacts(store)


@pytest.mark.parametrize("level", ["absolute_ancestor", "directory", "relative_directory", "final"])
def test_symlink_at_each_producer_path_level_is_unavailable(store, producer, tmp_path, level):
    nested = producer / "subdir"
    nested.mkdir()
    (nested / "result.bin").write_bytes(b"abc")
    directory, relative = producer, "subdir/result.bin"
    if level == "absolute_ancestor":
        alias = tmp_path / "ancestor_alias"
        alias.symlink_to(producer, target_is_directory=True)
        directory, relative = alias / "subdir", "result.bin"
    elif level == "directory":
        directory = tmp_path / "directory_alias"
        directory.symlink_to(producer, target_is_directory=True)
    elif level == "relative_directory":
        (producer / "alias").symlink_to(nested, target_is_directory=True)
        relative = "alias/result.bin"
    else:
        (nested / "alias.bin").symlink_to(nested / "result.bin")
        relative = "subdir/alias.bin"
    row, = capture.capture_declared_native_files(store, directory=str(directory),
        declarations=[declaration(relative)])
    assert row["outcome"] == "unavailable" and row["observed"] is None
    assert row["failure"] == "capture_file_unavailable"
    assert_no_artifacts(store)


@pytest.mark.parametrize("kind", ["directory", "fifo", "socket"])
def test_nonregular_final_file_is_unavailable_without_wait(store, producer, kind, monkeypatch):
    path = producer / "result.bin"
    endpoint = None
    if kind == "directory":
        path.mkdir()
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        endpoint = socket.socket(socket.AF_UNIX)
        directory_fd = os.open(producer, os.O_RDONLY | os.O_DIRECTORY)
        try:
            endpoint.bind(f"/proc/self/fd/{directory_fd}/result.bin")
        finally:
            os.close(directory_fd)
    original_open = os.open
    def open_nonblocking(name, flags, *args, **kwargs):
        if name == "result.bin":
            assert flags & os.O_NONBLOCK, "a FIFO must never be opened in blocking mode"
            assert flags & os.O_NOFOLLOW
        return original_open(name, flags, *args, **kwargs)
    monkeypatch.setattr(capture.os, "open", open_nonblocking)
    try:
        error_code("capture_file_unavailable", capture.capture_native_file, store,
            directory=str(producer), relative_path="result.bin", format="opaque")
    finally:
        if endpoint is not None:
            endpoint.close()
    assert_no_artifacts(store)


def test_directory_entry_replacement_after_open_keeps_original_inode(store, producer, monkeypatch):
    original = b"opened inode bytes\0\xff"
    replacement = b"different directory entry"
    source = producer / "result.bin"
    source.write_bytes(original)
    shared_copier = capture.artifact_file
    observed = []
    pinned_descriptors = []
    def replace_then_copy(actual_store, pinned, media_type):
        assert str(pinned).startswith("/proc/self/fd/")
        pinned_descriptors.append(int(pinned.name))
        observed.append(os.fstat(int(pinned.name)).st_ino)
        alternate = producer / "replacement"
        alternate.write_bytes(replacement)
        os.replace(alternate, source)
        assert source.stat().st_ino != observed[0]
        return shared_copier(actual_store, pinned, media_type)
    monkeypatch.setattr(capture, "artifact_file", replace_then_copy)
    identity = capture.capture_native_file(store, directory=str(producer),
        relative_path="result.bin", format="opaque")
    assert source.read_bytes() == replacement
    assert identity["sha256"] == hashlib.sha256(original).hexdigest()
    assert capture.retained_native_file(store, identity).read_bytes() == original
    with pytest.raises(OSError):
        os.fstat(pinned_descriptors[0])


def test_retained_only_read_never_accesses_original_producer(store, producer, monkeypatch):
    identity = saved(store, producer)
    (producer / "result.bin").unlink()
    producer.rmdir()
    original_open = Path.open
    opened = []
    def retained_open(path, *args, **kwargs):
        assert path.is_relative_to(store.path / "artifacts")
        opened.append(path)
        return original_open(path, *args, **kwargs)
    def no_producer(*args, **kwargs):
        pytest.fail("retained reading attempted producer capture")
    monkeypatch.setattr(Path, "open", retained_open)
    monkeypatch.setattr(capture, "_producer_file", no_producer)
    path = capture.retained_native_file(store, identity)
    assert path.read_bytes() == b"abc"
    assert opened and all(p == path for p in opened)


@pytest.mark.parametrize("change,code", [("same_size_bytes", "retained_artifact_mismatch"),
    ("truncated_bytes", "retained_artifact_mismatch"), ("removed", "retained_artifact_unavailable"),
    ("fifo", "retained_artifact_unavailable"), ("symlink", "retained_artifact_unavailable")])
def test_retained_mutation_removal_and_nonregular_objects(store, producer, change, code):
    identity = saved(store, producer)
    path = capture.retained_native_file(store, identity)
    if change == "same_size_bytes":
        path.write_bytes(b"xyz")
    elif change == "truncated_bytes":
        path.write_bytes(b"a")
    else:
        path.unlink()
        if change == "fifo":
            os.mkfifo(path)
        elif change == "symlink":
            path.symlink_to(producer / "result.bin")
    error_code(code, capture.retained_native_file, store, identity)


@pytest.mark.parametrize("field,value", [("size", 4), ("size", -1), ("size", "bad"),
    ("sha256", "0" * 64), ("sha256", "../../producer/result.bin"),
    ("media_type", ""), ("media_type", "a\n")])
def test_store_metadata_mismatch_is_not_producer_absence(store, producer, field, value):
    identity = saved(store, producer)
    store.db.execute(f"UPDATE artifacts SET {field}=? WHERE id=?", (value, identity["artifact_ref"]))
    error_code("retained_artifact_mismatch", capture.retained_native_file, store, identity)
    error_code("retained_artifact_mismatch", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=[declaration()])


def test_missing_store_metadata_is_unavailable(store, producer):
    identity = saved(store, producer)
    store.db.execute("DELETE FROM artifacts WHERE id=?", (identity["artifact_ref"],))
    error_code("retained_artifact_unavailable", capture.retained_native_file, store, identity)


@pytest.mark.parametrize("change", [{"extra": True}, {"size_bytes": True}, {"size_bytes": -1},
    {"size_bytes": 3.0}, {"sha256": "A" * 64}, {"artifact_ref": "artifact_" + "0" * 64},
    {"format": "a\n"}, {"format": ""}])
def test_identity_contract_rejects_malformed_records(store, producer, change):
    identity = {**saved(store, producer), **change}
    error_code("invalid_file_identity", capture.retained_native_file, store, identity)


@pytest.mark.parametrize("invalid", [None, [], {}, {"artifact_ref": "a"}])
def test_identity_contract_rejects_wrong_shape(store, invalid):
    error_code("invalid_file_identity", capture.retained_native_file, store, invalid)


@pytest.mark.parametrize("invalid_ref", [None, {}, "not_an_artifact", "artifact_" + "A" * 64])
def test_invalid_copier_return_is_identity_error(store, producer, monkeypatch, invalid_ref):
    (producer / "result.bin").write_bytes(b"abc")
    monkeypatch.setattr(capture, "artifact_file", lambda *args: invalid_ref)
    error_code("invalid_file_identity", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=[declaration()])


def test_copy_detects_corrupt_already_retained_bytes(store, producer):
    identity = saved(store, producer)
    capture.retained_native_file(store, identity).write_bytes(b"xyz")
    error_code("retained_artifact_mismatch", capture.capture_declared_native_files, store,
        directory=str(producer), declarations=[declaration()])


def test_detached_records_and_same_content_labels(store, producer):
    (producer / "one").write_bytes(b"abc")
    (producer / "two").write_bytes(b"abc")
    declarations = [declaration("one"), declaration("two", format="another_format")]
    original = deepcopy(declarations)
    rows = capture.capture_declared_native_files(store, directory=str(producer), declarations=declarations)
    assert rows[0]["observed"] is not rows[1]["observed"]
    assert rows[0]["observed"]["artifact_ref"] == rows[1]["observed"]["artifact_ref"]
    assert rows[1]["observed"]["format"] == "another_format"
    rows[0]["declared"]["size_bytes"] = 9
    rows[0]["observed"]["format"] = "changed"
    declarations[1]["format"] = "changed input"
    assert declarations[0] == original[0]
    assert rows[1]["declared"] == original[1]
    assert rows[1]["observed"]["format"] == "another_format"
    assert capture.retained_native_file(store, rows[1]["observed"]).read_bytes() == b"abc"


@pytest.mark.parametrize("failure,expected", [(None, None), ("missing", "capture_file_unavailable"),
    ("nonregular", "capture_file_unavailable"), ("intermediate", "capture_file_unavailable"),
    ("copy_oserror", "retained_artifact_unavailable"), ("store_corruption", "retained_artifact_unavailable"),
    ("bad_identity", "invalid_file_identity"), ("programming_error", None)])
def test_descriptor_cleanup_on_all_exit_paths(store, producer, monkeypatch, failure, expected):
    (producer / "result.bin").write_bytes(b"abc")
    relative = "result.bin"
    if failure == "missing":
        relative = "missing"
    elif failure == "nonregular":
        relative = "directory"
        (producer / relative).mkdir()
    elif failure == "intermediate":
        relative = "alias/result.bin"
        (producer / "alias").symlink_to(producer, target_is_directory=True)
    elif failure in ("copy_oserror", "store_corruption", "programming_error"):
        error = {"copy_oserror": OSError(errno.ENOSPC, "Store full"),
            "store_corruption": sqlite3.DatabaseError("database disk image is malformed"),
            "programming_error": RuntimeError("test programming failure")}[failure]
        def fail(*args):
            raise error
        monkeypatch.setattr(capture, "artifact_file", fail)
    elif failure == "bad_identity":
        monkeypatch.setattr(capture, "artifact_file", lambda *args: "bad")
    original_open = os.open
    opened = []
    def track_open(*args, **kwargs):
        fd = original_open(*args, **kwargs)
        opened.append(fd)
        return fd
    monkeypatch.setattr(capture.os, "open", track_open)
    kwargs = {"directory": str(producer), "relative_path": relative, "format": "opaque"}
    if expected:
        error_code(expected, capture.capture_native_file, store, **kwargs)
    elif failure == "programming_error":
        with pytest.raises(RuntimeError, match="test programming failure"):
            capture.capture_native_file(store, **kwargs)
    else:
        capture.capture_native_file(store, **kwargs)
    assert opened
    for fd in set(opened):
        with pytest.raises(OSError) as caught:
            os.fstat(fd)
        assert caught.value.errno == errno.EBADF
