"""Controlled protocol operands; actual session/spawn/parser/cleanup stay original."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.episodic_workflow.root.model_session import _SessionConnection
from gene_annotation_episode.episodic_workflow.root.model_transport_resources import owned_process_group_running
from gene_annotation_episode.episodic_workflow.root.providers import ModelConnection

FIXTURE = Path(__file__).parent / 'fixtures/model_transport/controlled_server.py'


class LiteralPresentationSession(_SessionConnection):
    """Only the absent scientific presentation is replaced, explicitly for tests."""
    def _presentation(self, episode_id, role, instructions, context):
        return 'Controlled transport bytes; no scientific interpretation.', instructions


class ControlledConnection(ModelConnection):
    session_type = LiteralPresentationSession


def configuration(directory, **settings):
    directory.mkdir()
    (directory / 'settings.json').write_text(json.dumps(settings), encoding='utf-8')
    role = {'model': 'controlled-protocol-peer', 'reasoning_effort': 'controlled'}
    return {'connection': {'command': [sys.executable, '-B', str(FIXTURE.resolve()),
            '--control', str(directory.resolve())]}, 'FAST': dict(role),
            'REASONING': dict(role), 'routing': {}}


async def observed(path, task=None):
    """Observe a real handshake, with no elapsed/count success or failure cutoff."""
    while not path.exists():
        if task is not None and task.done():
            task.result()
            raise AssertionError('Task exited before handshake: ' + str(path))
        await asyncio.sleep(0.01)  # Observation cadence only.
    return json.loads(path.read_text())


async def ensure_closed(session):
    process = session.process
    if process is not None and (process.returncode is None
            or owned_process_group_running(process.pid)
            or session.stderr is not None and not session.stderr.closed):
        await session.__aexit__(asyncio.CancelledError, None, None)


@asynccontextmanager
async def actual_session(directory, **settings):
    control = directory / 'control'
    config = configuration(control, **settings)
    session = LiteralPresentationSession(config, directory / 'session', directory)
    try:
        async with session:
            yield session, control
    finally:
        await ensure_closed(session)


def assert_exited(session, ready):
    assert session.process.pid == ready['pid'] == ready['pgid']
    assert session.process.returncode is not None
    assert not owned_process_group_running(ready['pgid'])
    if ready['child_pid'] is not None:
        stat = Path('/proc') / str(ready['child_pid']) / 'stat'
        try:
            state = stat.read_bytes().rsplit(b')', 1)[1].split()[0]
        except FileNotFoundError:
            pass
        else:
            assert state in {b'Z', b'X', b'x'}
    assert session.stderr.closed
    assert session.stderr_reader is None or session.stderr_reader.done()


def requests(control):
    return [json.loads(line) for line in (control / 'received.jsonl').read_text().splitlines()]


def declared_publication_test_factory(*args, **kwargs):
    raise RuntimeError('controlled_publication_test_factory_must_not_execute')


def requested_descriptor(settings):
    """A real declared callable, without executing that callable."""
    from gene_annotation_episode.episodic_workflow.root.method_loop.durable import content_digest
    return {'factory_module': __name__, 'factory_name': 'declared_publication_test_factory',
            'arguments': {'purpose': 'publication identity fixture only'},
            'settings_sha256': content_digest(settings)}
