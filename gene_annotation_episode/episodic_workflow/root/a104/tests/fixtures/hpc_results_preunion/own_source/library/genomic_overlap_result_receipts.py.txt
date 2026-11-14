"""Selected overlap action controls and historical completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Historical checks use frozen controls and Store metadata, never scientific bytes.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.retained_native_read_profiles import retained_policy_matches
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import PurePosixPath
import stat
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.library.native_genomic_overlap_contracts import POLICY
from gene_annotation_episode.episodic_workflow.root.a104.progress_records import validate_resource_observation

def require(condition, code='genomic_overlap_result_authority_conflict'):
    if not condition:
        raise ValueError(code)

def same(left, right):
    return canonical(left) == canonical(right)

@contextmanager
def directory(path, *, create=False):
    value = str(path)
    pure = PurePosixPath(value)
    require(pure.is_absolute() and str(pure) == value and (value != '/') and ('..' not in pure.parts) and (not any((c in value for c in '\x00\r\n\\'))), 'genomic_overlap_result_invalid_path')
    with ExitStack() as stack:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in pure.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 448, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        require(os.fstat(fd).st_uid == os.geteuid(), 'genomic_overlap_result_invalid_path')
        yield fd

@contextmanager
def regular(fd, name, *, flags=os.O_RDONLY):
    require(type(name) is str and name not in ('', '.', '..') and ('/' not in name))
    handle = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 384, dir_fd=fd)
    try:
        require(stat.S_ISREG(os.fstat(handle).st_mode), 'genomic_overlap_result_invalid_path')
        yield handle
    finally:
        os.close(handle)

class GenomicOverlapResultReceipts:

    def _selected(self, intent):
        row = self.owner._selected_result_action(intent['episode_id'], intent['operation_key'], intent['tool_name'], intent['arguments'])
        require(same(json.loads(row['action']), {'kind': 'tool', 'tool': intent['tool_name'], 'arguments': {}}))
        return row

    def validate_observation(self, value, intent):
        from gene_annotation_episode.episodic_workflow.root.a104.terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
        if is_terminal_target(intent['target']):
            return validate_terminal_observation(value, intent, self.store, self.owner.run_id)
        from gene_annotation_episode.episodic_workflow.root.a104.native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value['native']
        require(native.get('execution_id') == intent['target']['execution_id'] and native.get('version') == native_version and (type(native.get('terminal')) is bool) and (type(native.get('quiescent')) is bool) and retained_policy_matches(native.get('metadata', {}).get('policy')))
        require(not native['terminal'] or (native['quiescent'] and native['state'] == 'returned'))
        if native['terminal']:
            require(type(native['metadata'].get('service_exit')) is dict and value['state'] in {'completed', 'failed'})
        return value
