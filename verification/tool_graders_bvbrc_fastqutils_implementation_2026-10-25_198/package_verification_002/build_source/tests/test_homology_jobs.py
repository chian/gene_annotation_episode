"""One tiny real phmmer job; operational assertions, no annotation/credit claim."""
from pathlib import Path
import json
import subprocess
import sys
import time

from Bio import SearchIO
import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, HANDOFF_SCHEMA, SAMPLE_SCHEMA, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, cancel
from gene_annotation_episode.acquisition import AcquisitionError


PROJECT = Path(__file__).resolve().parents[1]
PROGRAM = PROJECT/'resources/software/infernal-1.1.5/hmmer/src/phmmer'
QUERY = (PROJECT/'cases/gene_001/target.faa').read_text()


def prepare(tmp_path, name='jobs', *, max_cpu=1, search_modes=None):
    database = tmp_path/(name+'-references.faa')
    database.write_text(QUERY.replace('>gene_001', '>reference_self_fixture'))
    return HomologyJobs.create(tmp_path/name, executable=FileAsset(PROGRAM, digest(PROGRAM)),
        reference_database=FileAsset(database, digest(database)),
        policy=LocalJobPolicy(128*1024**2, 4*1024**2), max_cpu=max_cpu, search_modes=search_modes)


def wait_terminal(service, job):
    started = time.monotonic()
    while service.status(job)['state'] in {'starting', 'running'}:
        assert time.monotonic()-started < 15  # Test deadline only.
        time.sleep(.02)


def test_order_persists_explicit_cpu_and_configuration_cannot_replace_it(tmp_path):
    service = prepare(tmp_path, max_cpu=2)
    try:
        with pytest.raises(TypeError):
            service.order(query_ref='fixture', query_fasta=QUERY, operation_key='missing-cpu')
        with pytest.raises(ValueError, match='cpu_outside'):
            service.order(query_ref='fixture', query_fasta=QUERY, cpu=3, operation_key='invalid-cpu')
        assert service.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        job = service.order(query_ref='fixture', query_fasta=QUERY, cpu=2, operation_key='selected')
        assert service.configure(job, 2)['configured_cpu'] == 2
        with pytest.raises(ValueError, match='selected_job_cpu_is_immutable'):
            service.configure(job, 1)
        with pytest.raises(ValueError, match='order_identity_conflict'):
            service.order(query_ref='fixture', query_fasta=QUERY, cpu=1, operation_key='selected')
        directory = service.directory
        service.close()
        service = HomologyJobs(directory)
        assert service._row(job)['cpu'] == 2
        assert service.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    finally:
        service.close()


def test_handoff_resolves_native_job_after_launch_connection_closes(tmp_path):
    service = prepare(tmp_path)
    job = service.order(query_ref='product_fixture', query_fasta=QUERY, cpu=1, operation_key='selected-launch')
    assert service.order(query_ref='product_fixture', query_fasta=QUERY, cpu=1, operation_key='selected-launch') == job
    with pytest.raises(ValueError, match='staged_inputs_required'):
        service.submit(job)
    with pytest.raises(ValueError, match='cpu_outside'):
        service.configure(job, 2)
    service.stage(job)
    reference_stamp = (service.directory/job/'references.faa').stat().st_mtime_ns
    # A later launch decision can repair missing prepared bytes without
    # replacing a submitted job or changing its requested query.
    (service.directory/job/'query.faa').unlink()
    service.stage(job)
    assert (service.directory/job/'query.faa').read_text().startswith('>query\n')
    assert (service.directory/job/'references.faa').stat().st_mtime_ns == reference_stamp
    service.configure(job, 1)
    root = service.directory
    try:
        returned = service.submit(job)
        assert returned['new_submission'] is True
        assert service.submit(job)['new_submission'] is False
        handoff = service.handoff(job)
        validate_form(handoff, HANDOFF_SCHEMA, service.resolve)
        receipt = service.check_handoff(handoff)
        assert service.resolve(receipt['receipt_ref'], 'handoff_receipt')
        assert receipt['sample']['job_ref'] == job
        assert receipt['checked_at_unix_seconds'] > 0
        service.close()
        service = HomologyJobs(root)
        wait_terminal(service, job)
        observed = service.receive(handoff)
        assert observed['outcome'] == 'succeeded', observed
        assert observed['native_returncode'] == 0
        assert all(row['writer_closed'] and row['available'] for row in observed['outputs'])
        sample = service.sample(handoff, operation_key='monitor-one-action')
        validate_form(sample, SAMPLE_SCHEMA, service.resolve)
        assert service.sample(handoff, operation_key='monitor-one-action') == sample
        assert service.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 1
        native = SearchIO.read(service.result_file(handoff, 'native_text'), 'hmmer3-text')
        assert native.id == 'query' and len(native) == 1
        assert native[0].id == 'reference_self_fixture' and native[0].evalue < .001
        # Native evidence is available; no scientific conclusion/score exists.
        assert service.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        with pytest.raises(ReportBoundaryError):
            service.check_handoff({**handoff, 'status_interface': 'Trust this explanatory paragraph'})
        with pytest.raises(ReportBoundaryError):
            service.check_handoff({**handoff, 'registry_ref': 'execution_registry_unknown'})
        # A native handle copied from another directory cannot be relabeled as
        # this registered job just because the job identifier is syntactically valid.
        import json
        native_handle = root/job/'native.handle.json'
        original = native_handle.read_text()
        altered = json.loads(original)
        altered['cwd'] = str(tmp_path/'a-different-job')
        native_handle.write_text(json.dumps(altered))
        try:
            with pytest.raises(ValueError, match='does_not_describe_registered_job'):
                service.check_handoff(handoff)
        finally:
            native_handle.write_text(original)
        other = prepare(tmp_path, 'other-jobs')
        try:
            with pytest.raises(ReportBoundaryError):
                other.receive(handoff)
        finally:
            other.close()
    finally:
        handle = NativeJobHandle(root/job/'native.handle.json')
        if handle.path.exists():
            cancel(handle)
        service.close()


def test_unconfirmed_submission_does_not_silently_execute_again(tmp_path):
    service = prepare(tmp_path)
    try:
        job = service.order(query_ref='product_fixture', query_fasta=QUERY, cpu=1, operation_key='operation')
        service.stage(job); service.configure(job, 1)
        # Crash after durable intent but before native handle publication.
        with service.db:
            service.db.execute('UPDATE orders SET submission_requested=1 WHERE job_ref=?', (job,))
        result = service.submit(job)
        assert result['new_submission'] is False
        assert result['status']['state'] == 'submission_unconfirmed'
        assert result['status']['elapsed_seconds'] is None
        assert not (service.directory/job/'native.handle.json').exists()
        with pytest.raises(ValueError, match='handoff_unresolved'):
            service.handoff(job)
    finally:
        service.close()


@pytest.mark.parametrize('phase', ['after_reservation', 'before_dispatch'])
def test_real_process_loss_resumes_same_never_dispatched_reservation(tmp_path, phase):
    service = prepare(tmp_path)
    job = service.order(query_ref='product_fixture', query_fasta=QUERY, cpu=1, operation_key='operation')
    service.stage(job); service.configure(job, 1)
    script = ('import os\nfrom gene_annotation_episode.homology_jobs import HomologyJobs\n'
        'import gene_annotation_episode.homology_jobs as module\n'
        'original=module.prepare_job\n'
        'def interrupted(*args,**kwargs):\n'
        '    handle=original(*args,**kwargs)\n'
        '    os._exit(42)\n'
        + ('module.prepare_job=interrupted\n' if phase == 'after_reservation' else
           'module.start_prepared=lambda *args,**kwargs: os._exit(42)\n')
        + f'service=HomologyJobs({str(service.directory)!r})\nservice.submit({job!r})\n')
    try:
        owner = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=15)
        assert owner.returncode == 42, owner.stderr
        reservation = service._handle(job).read()
        assert reservation['stage'] == 'prepared'
        assert reservation['started_at'] is reservation['started_monotonic_ns'] is reservation['boot_id'] is None
        assert service._row(job)['submission_requested'] == (phase == 'before_dispatch')
        assert service.environment(job)['submission_requested'] is True
        assert service.status(job)['state'] == 'prepared'
        assert service.status(job)['elapsed_seconds'] is None
        assert (service._directory(job)/'native.stdout').read_bytes() == b''
        with pytest.raises(ValueError, match='handoff_unresolved'):
            service.handoff(job)
        with pytest.raises(ValueError, match='cpu_outside'):
            service.configure(job, 2)
        # Repair exact unsubmitted operand bytes, preserving the valid corpus.
        reference = service._directory(job)/'references.faa'
        stamp = reference.stat().st_mtime_ns
        (service._directory(job)/'query.faa').unlink()
        service.stage(job)
        assert reference.stat().st_mtime_ns == stamp
        root = service.directory
        service.close(); service = HomologyJobs(root)
        service.resume_start(job)
        wait_terminal(service, job)
        assert service.status(job)['outcome'] == 'succeeded'
        assert service._handle(job).read()['unit'] == reservation['unit']
        assert service._handle(job).read()['paths'] == reservation['paths']
        assert service._handle(job).read()['started_monotonic_ns'] is not None
        assert service.submit(job)['new_submission'] is False
        assert service.check_handoff(service.handoff(job))['sample']['outcome'] == 'succeeded'
        assert service.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    finally:
        handle = service._handle(job)
        if handle.path.exists():
            cancel(handle)
        service.close()


def test_dispatch_uncertainty_is_not_permission_to_submit_another_unit(tmp_path):
    service = prepare(tmp_path)
    job = service.order(query_ref='product_fixture', query_fasta=QUERY, cpu=1, operation_key='operation')
    service.stage(job); service.configure(job, 1)
    script = ('import os\nimport gene_annotation_episode.native_lifecycle as native\n'
        'from gene_annotation_episode.homology_jobs import HomologyJobs\n'
        'original=native.subprocess.run\n'
        'def interrupted(command,*args,**kwargs):\n'
        '    if command[0]=="systemd-run": os._exit(43)\n'
        '    return original(command,*args,**kwargs)\n'
        'native.subprocess.run=interrupted\n'
        + f'service=HomologyJobs({str(service.directory)!r})\nservice.submit({job!r})\n')
    try:
        owner = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=15)
        assert owner.returncode == 43, owner.stderr
        handle = service._handle(job)
        original = handle.path.read_bytes()
        assert handle.read()['stage'] == 'submitting'
        assert service.status(job)['state'] == 'execution_unknown'
        assert service.submit(job)['new_submission'] is False
        with pytest.raises(AcquisitionError):
            service.resume_start(job)
        assert handle.path.read_bytes() == original
        assert (service._directory(job)/'native.stdout').read_bytes() == b''
    finally:
        service.close()
