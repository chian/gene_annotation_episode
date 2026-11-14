"""Original/current A102 protection dispatch with real Store and explicit ports.

The access callbacks are controlled boundary inputs, not authentic native
receipts. They show which denial reaches byte validation; positive historical
native custody remains a separate integration test requirement.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.episodic_workflow.root.a102.state import Store

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a102'
FAMILIES = ('flux_balance', 'fluorescence', 'expression_nmf', 'atac', 'chromatin', 'protein')


def original_validator():
    path = Path(__file__).with_name('fixtures') / 'original_execution_input_protection/execution_input_versions.py.txt'
    namespace = {'__name__': PREFIX + '._retained_test_input_protection', '__package__': PREFIX}
    exec(compile(path.read_bytes(), str(path), 'exec'), namespace)
    return namespace['validate_execution_input_versions']


def current_validator():
    return import_module(PREFIX + '.execution_input_versions').validate_execution_input_versions


def restored_validator():
    return import_module(PREFIX + '.library.received_execution_information.input_versions').validate_execution_input_versions


def forbidden(*args, **kwargs):
    raise AssertionError('input protection checks cannot launch a native process or provider')


@contextmanager
def actual_store(directory):
    directory = Path(directory).resolve()
    assert directory.is_relative_to(Path(active_budget()['run_directory']).resolve())
    with patch('subprocess.Popen', forbidden), patch('socket.socket.connect', forbidden), patch('socket.socket.connect_ex', forbidden):
        with Store(directory) as store:
            store.create_problem(raw_sequence='ATGGCT', molecule='dna')
            yield store


def observe(validator, store, *, denied=None, content_mismatch=False, revision_mismatch=False, unscoped=False):
    assert denied is None or denied in FAMILIES
    scope = store.validate_scope()
    reference = store.targets()[0]['sequence_ref']
    if unscoped:
        reference = store.artifact('unselected protected bytes', 'application/octet-stream')
    raw = store.get_artifact(reference)
    context = SimpleNamespace(scope=deepcopy(scope), role='launch_local', assignment={})
    owner = SimpleNamespace(store=store, native_flux_balance_results=object(),
        native_fluorescence_results=object(), native_expression_nmf_results=object())
    access_calls, artifact_reads = [], []
    for family in FAMILIES:
        def check(current, selected, namespace, *, family=family):
            assert current is context and selected == reference and namespace is None
            access_calls.append(family)
            return False if family == denied else None
        setattr(owner, '_' + family + '_reference_access', check)
    version = {'reference': reference, 'version': 'wrong-revision' if revision_mismatch else None,
        'content_sha256': '0' * 64 if content_mismatch else hashlib.sha256(raw).hexdigest()}
    real = store.get_artifact
    def read(selected):
        artifact_reads.append(selected)
        return real(selected)
    before = store.db.total_changes
    with patch.object(store, 'get_artifact', read):
        try:
            result = validator(owner, [version], scope, context=context)
        except Exception as error:
            outcome = {'status': 'raised', 'exception_type': type(error).__module__ + '.' + type(error).__qualname__,
                'message': str(error)}
        else:
            outcome = {'status': 'returned', 'value': result}
    assert store.db.total_changes == before
    return {'outcome': outcome, 'access_calls': access_calls, 'artifact_reads': artifact_reads,
        'original_artifact_sha256': hashlib.sha256(raw).hexdigest(),
        'recorded_input_version': version, 'native_receipt_custody_proved': False,
        'controlled_ports': 'original protected-reference access callbacks only'}
