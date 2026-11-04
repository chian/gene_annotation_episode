"""One genuine selected LUMPY PE call, followed by the shared VCF result path.

This checks native output and result delivery. The caller runs under the
enclosing bounded check, not through a newly claimed execution binding.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import vcf_result_measurements as core
from gene_annotation_episode import vcf_result_tools as host
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_atac_differential_reference import extract_atac_bam_header
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_vcf_result_workflow import (
    PUBLICATION, POLICY, SOURCE, VcfProvider, _closed_child, _controller,
    _forbidden, _schema, _selection, _tables, _zero,
)


FIXTURES = Path(__file__).parent / 'fixtures/lumpy_pe'
QUESTION = (
    'For the supplied native LUMPY paired-end VCF, what record, ALT-token and sample-cell '
    'populations and reported SVTYPE, SVLEN, support counts, confidence intervals and mate labels '
    'are retained? Preserve missing genotypes and return the controlled VCF result groups.'
)
INFO = ['SVTYPE', 'SVLEN', 'END', 'SU', 'PE', 'SR', 'CIPOS', 'CIEND', 'MATEID', 'EVENT', 'SECONDARY']


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _body(raw):
    return [line for line in raw.splitlines() if line and not line.startswith(b'#')]


def _reconstruct_original_workflow(store, proof):
    """Fresh runtime owners; preserve every original identity and binding."""
    factory = ExecutionServiceFactory.from_record(proof['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    factory.configure_tool_registry(tools)
    directory = Path(proof['workflow_directory'])
    library = ScientificProcessLibrary(directory / 'scientific-process-library')
    provider = VcfProvider(store, library, proof['scope'], proof['input_ref'], question=QUESTION,
        native_file=Path(proof['native_vcf']), analyze_selection=proof['calculator_calls'][0],
        derived_selection=proof['calculator_calls'][1], allow_partial=True)
    application = factory(store, run_id=proof['run_id'], directory=directory, tool_registry=tools)
    workflow = Workflow(store, tools, provider, directory, proof['run_id'], _controller, _zero,
        project_child_credit=_zero,
        episode_binding_descriptors=[proof['scientific_binding'], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=[proof['input_ref']])
    return workflow, provider


def test_selected_lumpy_PE_native_output_shared_saved_values_and_typed_delivery(tmp_path, monkeypatch):
    selected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY')
    expected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_SHA256')
    if not selected or not expected:
        pytest.skip('requires the explicitly selected built LUMPY executable and digest')
    binary = Path(selected).resolve(strict=True)
    assert _sha(binary) == expected
    provenance = json.loads((FIXTURES / 'provenance.json').read_text())
    for item in provenance['objects']:
        path = FIXTURES / item['name']
        assert _sha(path) == item['sha256'] and path.stat().st_size == item['size_bytes']
    native = tmp_path / 'native'
    native.mkdir()
    for name in ('tmp', 'cache'):
        (native / name).mkdir()
    bam, histogram = FIXTURES / 'test_sub.filtered_disc.bam', FIXTURES / 'test.sample1.lib1.x4.histo'
    pe = ('bam_file:' + str(bam) + ',histo_file:' + str(histogram)
        + ',mean:438.420989806,stdev:92.6149432404,read_length:100,min_non_overlap:100'
        + ',discordant_z:5,back_distance:10,weight:1,id:test,min_mapping_threshold:1'
        + ',read_group:33PR_WHAIPI005638-93_gAHB')
    argv = [str(binary), '-P', '-msw', '4', '-tt', '0', '-pe', pe]
    environment = dict(PATH='/usr/bin:/bin', LC_ALL='C.UTF-8', TMPDIR=str(native / 'tmp'),
        TMP=str(native / 'tmp'), TEMP=str(native / 'tmp'), XDG_CACHE_HOME=str(native / 'cache'),
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    output, stderr = native / 'lumpy.vcf', native / 'stderr.log'
    proof = dict(question=QUESTION, passed=False, selected_executable=str(binary),
        selected_executable_sha256=expected, argv=argv, environment=environment,
        caller_label='test', selected_read_group='33PR_WHAIPI005638-93_gAHB',
        reference_build=None, biological_sample=None, taxon=None,
        native_execution_binding_verified=False, native_calls=0,
        parser_calls=[], calculator_calls=[], provenance=provenance)
    try:
        retained = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RETAINED_PROOF')
        if retained:
            retained_sha = os.environ['HMMER_NATIVE_ORACLE_LUMPY_RETAINED_SHA256']
            prefix_path = Path(retained).resolve(strict=True)
            assert _sha(prefix_path) == retained_sha
            prefix = json.loads(prefix_path.read_text())
            assert prefix['native_calls'] == 1 and prefix['native_returncode'] == 0
            assert prefix['parser_calls'] == prefix['calculator_calls'] == []
            assert prefix['selected_executable_sha256'] == expected
            output, header = Path(prefix['native_vcf']), Path(prefix['input_header_path'])
            assert _sha(output) == prefix['native_vcf_sha256']
            assert _sha(header) == prefix['input_header_extraction']['header']['sha256']
            proof.update(original_native_proof=dict(path=str(prefix_path), sha256=retained_sha),
                original_native_argv=prefix['argv'], original_native_executable=prefix['selected_executable'],
                native_returncode=prefix['native_returncode'], input_header_extraction=prefix['input_header_extraction'])
        else:
            # Reuse the existing File-only extraction leaf. Its historical
            # envelope name implies no ATAC or callpeak commission.
            header = native / 'bam.header.sam'
            descriptor = dict(artifact_ref='artifact_' + _sha(bam), sha256=_sha(bam),
                size_bytes=bam.stat().st_size, format='bam')
            extraction = extract_atac_bam_header(input_path=bam, input_file=descriptor,
                input_key='selected_discordant_BAM', callpeak_run_key='selected_LUMPY_PE_input_inspection',
                input_ordinal=0, output_path=header, output_relative_path='bam.header.sam',
                policy=LocalJobPolicy(**POLICY))
            proof.update(input_header_extraction=extraction)
            assert extraction['producer_outcome'] == 'succeeded' and extraction['supplied_extent'] == 'complete'
            with output.open('xb') as stdout, stderr.open('xb') as errors:
                completed = subprocess.run(argv, cwd=native, env=environment,
                    stdout=stdout, stderr=errors, check=False)
            proof.update(native_calls=1, native_returncode=completed.returncode,
                native_stderr_sha256=_sha(stderr))
        proof.update(input_header_path=str(header), input_header_sha256=_sha(header),
            bam_read_group_header_lines=[line for line in header.read_text().splitlines() if line.startswith('@RG\t')],
            native_vcf=str(output), native_vcf_sha256=_sha(output),
            native_vcf_size_bytes=output.stat().st_size)
        assert proof['native_returncode'] == 0
        raw = output.read_bytes()
        body = _body(raw)
        expected_body = _body((FIXTURES / 'test_onlydisc.bam.vcf').read_bytes())
        proof.update(upstream_expected_records=len(expected_body), observed_records=len(body),
            upstream_expected_record_bytes_equal=body == expected_body)
        assert raw.startswith(b'##fileformat=VCFv4.2\n') and body
        native_tokens = [line.decode('utf-8').split('\t') for line in body]
        # The oracle is the original caller bytes; these reads do not replace
        # the shared sheet/calculator in any production or result consumer.
        negative = next(i for i, fields in enumerate(native_tokens)
            if any(token.startswith('SVLEN=-') for token in fields[7].split(';')))
        breakends = [i for i, fields in enumerate(native_tokens) if '[' in fields[4] or ']' in fields[4]]
        proof['native_breakend_ordinals'] = breakends
        chosen = [negative, *[i for i in range(len(native_tokens)) if i != negative][:2]]
        assert len(set(chosen)) == len(chosen)
        assert raw == (FIXTURES / 'test_onlydisc.bam.vcf').read_bytes()
        derived_selection = _selection(record_ordinals=chosen, info_keys=INFO,
            format_keys=['GT', 'SU', 'PE', 'SR'], offset=0, limit=3)
        with Store(tmp_path / 'store') as store:
            subject_file = tmp_path / 'subject.fa'
            subject_file.write_text('>engineering_scope\nACGTACGT\n')
            subject, = store.create_problem(subject_file, molecule='dna')['subject_refs']
            scope = store.validate_scope(dict(subject_refs=[subject]))
            supplied = store.register_material(input_path=output, name='actual_lumpy_PE_output', use='evidence')
            source = store.get(supplied['source_ref'])
            input_ref = source['artifact_ref']
            workspace = tmp_path / 'workspace'
            workspace.mkdir()
            factory = ExecutionServiceFactory({'ordinary': dict(kind='local', workspace=str(workspace),
                policy=deepcopy(POLICY))}, {}, 2, .25, .5)
            tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(tools)
            directory, run_id = tmp_path / 'run', 'native-lumpy-vcf-shared-results'
            scientific = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
                tool_catalog=tools.catalog(), child_roles=['scientific_process'])
            library = ScientificProcessLibrary(directory / 'scientific-process-library')
            provider = VcfProvider(store, library, scope, input_ref, question=QUESTION, native_file=output,
                analyze_selection=_selection(info_keys=INFO, format_keys=['GT', 'SU', 'PE', 'SR']),
                derived_selection=derived_selection, allow_partial=True)
            application = factory(store, run_id=run_id, directory=directory, tool_registry=tools)
            workflow = Workflow(store, tools, provider, directory, run_id, _controller, _zero,
                project_child_credit=_zero, episode_binding_descriptors=[scientific, *application.episode_binding_descriptors],
                role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
                episode_record_receipts=True, initial_known_record_refs=[input_ref])
            proof.update(store_directory=str(store.path), workflow_directory=str(directory), run_id=run_id,
                factory=factory.as_record(), scientific_binding=scientific, scope=scope, input_ref=input_ref,
                native_selected_ordinals=chosen)
            calculate, parse, get = core.calculate_vcf_components, core.parse_vcf_sheet, Store.get_artifact
            def calculated(sheet, selection):
                proof['calculator_calls'].append(deepcopy(selection))
                return calculate(sheet, selection)
            def parsed(record):
                proof['parser_calls'].append(record['input_id'])
                return parse(record)
            def artifact(current, reference, *args, **kwargs):
                if reference == input_ref and proof['parser_calls']:
                    raise AssertionError('saved LUMPY result reopened native VCF')
                return get(current, reference, *args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(core, 'calculate_vcf_components', calculated)
                patch.setattr(core, 'parse_vcf_sheet', parsed)
                patch.setattr(Store, 'get_artifact', artifact)
                patch.setattr('subprocess.run', _forbidden)
                patch.setattr('socket.create_connection', _forbidden)
                patch.setattr('gene_annotation_episode.acquisition.PublicClients._http', _forbidden)
                for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status', 'cancel', 'release'):
                    patch.setattr(native_lifecycle, name, _forbidden)
                root = workflow.build('annotation', 'root', QUESTION, scope)
                value = asyncio.run(root.run_async(workflow.context))
                assert plain(asyncio.run(root.build_result(value)).as_record()) == dict(credit=0, pending_handles=[])
                original, derived, read = provider.outcomes()
                assert all(item['status'] in ('completed', 'partial') for item in (original, derived, read))
                assert derived['result'] == read['result'] and read['changed_record_refs'] == []
                group = [original['result'], derived['result']]
                assert len(proof['parser_calls']) == 1 and len(proof['calculator_calls']) == 2
                records = EpisodeReturnRecords(store, run_id, failure_prefix='lumpy_vcf_')
                episodes = list(store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)', (run_id,)))
                parent, science = [records.context(row[0]) for row in episodes]
                population = group[0]['value']['population']
                assert [population[key] for key in ('total_original_record_slots', 'retained_record_slots',
                    'selected_record_slots', 'returned_record_slots')] == [len(body), len(body), len(body), 2]
                assert group[1]['value']['population']['selected_record_slots'] == len(chosen)
                for record in group[1]['value']['records']:
                    tokens = native_tokens[record['record_ordinal_0based']]
                    assert record['chrom'] == tokens[0] and record['pos_1based'] == int(tokens[1])
                    assert record['alts'][0]['token']['raw_token'] == tokens[4]
                    fields = {row['key']: row for row in record['info']}
                    for token in tokens[7].split(';'):
                        key, separator, literal = token.partition('=')
                        if key in INFO and separator:
                            assert [row['token']['raw_token'] for row in fields[key]['values']] == literal.split(',')
                    assert record['samples'][0]['genotype']['token']['raw_token'] == './.'
                    assert record['filter']['state'] == 'not_applied'
                assert all(item['value']['input']['source_ref'] is None for item in group)
                for current, method in ((science, workflow.services.molecular_own_facts),
                        (science, workflow.services.molecular_frozen_facts), (parent, workflow.services.molecular_received_facts)):
                    assert method(current, fact_source=SOURCE) == group
                assert _closed_child(workflow, root, parent, science) == dict(form=dict(outcomes=group))
                references = {item['source_ref'] for item in group}
                assert validate_form(dict(outcomes=group), _schema(),
                    lambda ref, namespace: namespace == 'source' and ref in references) == dict(outcomes=group)
                before = _tables(store)
                with patch.context() as replay:
                    replay.setattr(core, 'calculate_vcf_components', _forbidden)
                    replay.setattr(core, 'parse_vcf_sheet', _forbidden)
                    replay.setattr(ToolRegistry, 'execute_async', _forbidden)
                    replay.setattr(provider, 'complete', _forbidden)
                    replay.setattr(Store, 'get_artifact', _forbidden)
                    reopened, other_provider = _reconstruct_original_workflow(store, proof)
                    replay.setattr(other_provider, 'complete', _forbidden)
                    closed = reopened.build('annotation', 'root', QUESTION, scope)
                    again = asyncio.run(closed.run_async(reopened.context))
                    assert plain(asyncio.run(closed.build_result(again)).as_record()) == dict(credit=0, pending_handles=[])
                    assert _closed_child(reopened, closed, parent, science) == dict(form=dict(outcomes=group))
                    assert other_provider.contexts == other_provider.wire == []
                assert before == _tables(store)
            proof.update(passed=True, returned=group, closed_replay_rows_unchanged=True,
                model_rpc_calls=0, scripted_provider_calls=len(provider.contexts),
                runtime_counts={name: store.db.execute('SELECT count(*) FROM ' + name + ' WHERE run_id=?', (run_id,)).fetchone()[0]
                    for name in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls', 'runtime_forms', 'runtime_report_attempts')})
    except BaseException as error:
        proof['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        (tmp_path / 'lumpy_native_vcf_workflow_audit.json').write_text(json.dumps(proof, indent=2, allow_nan=False) + '\n')


def test_retained_lumpy_result_closed_history_reconstructs_without_new_work(tmp_path, monkeypatch):
    selected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESULT_PROOF')
    expected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESULT_SHA256')
    if not selected or not expected:
        pytest.skip('requires the explicit retained LUMPY result-path proof and digest')
    path = Path(selected).resolve(strict=True)
    assert _sha(path) == expected
    prefix = json.loads(path.read_text())
    assert prefix['native_calls'] == 0 and len(prefix['parser_calls']) == 1 and len(prefix['calculator_calls']) == 2
    audit = dict(original_proof=dict(path=str(path), sha256=expected), passed=False,
        new_native_calls=0, new_parser_calls=0, new_calculator_calls=0, new_tool_calls=0, new_model_rpc_calls=0)
    try:
        with Store(prefix['store_directory']) as store:
            run_id = prefix['run_id']
            rows = list(store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)', (run_id,)))
            assert len(rows) == 2
            records = EpisodeReturnRecords(store, run_id, failure_prefix='lumpy_reconstruction_')
            parent, science = [records.context(row[0]) for row in rows]
            form, = list(store.db.execute('SELECT form FROM runtime_forms WHERE run_id=?', (run_id,)))
            frozen = json.loads(form[0])
            group = frozen['outcomes']
            assert len(group) == 2
            public_files = {store.get(item['source_ref'])['artifact_ref'] for item in group}
            get, reads = Store.get_artifact, []
            def public_packet(current, reference, *args, **kwargs):
                assert reference in public_files, 'result facts reopened a private or native File'
                reads.append(reference)
                return get(current, reference, *args, **kwargs)
            before = _tables(store)
            with monkeypatch.context() as patch:
                patch.setattr(core, 'parse_vcf_sheet', _forbidden)
                patch.setattr(core, 'calculate_vcf_components', _forbidden)
                patch.setattr(ToolRegistry, 'execute_async', _forbidden)
                patch.setattr(Store, 'get_artifact', public_packet)
                patch.setattr('gene_annotation_episode.materials._verified_artifact_path', _forbidden)
                patch.setattr('gene_annotation_episode.native_file_capture._verified_artifact_path', _forbidden)
                patch.setattr('subprocess.run', _forbidden)
                patch.setattr('socket.create_connection', _forbidden)
                for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status', 'cancel', 'release'):
                    patch.setattr(native_lifecycle, name, _forbidden)
                workflow, provider = _reconstruct_original_workflow(store, prefix)
                patch.setattr(provider, 'complete', _forbidden)
                with patch.context() as closed:
                    closed.setattr(Store, 'get_artifact', _forbidden)
                    root = workflow.build('annotation', 'root', QUESTION, prefix['scope'])
                    completed = asyncio.run(root.run_async(workflow.context))
                    assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
                    assert _closed_child(workflow, root, parent, science) == dict(form=frozen)
                assert workflow.services.molecular_own_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_frozen_facts(science, fact_source=SOURCE) == group
                assert workflow.services.molecular_received_facts(parent, fact_source=SOURCE) == group
                assert provider.contexts == provider.wire == []
            assert before == _tables(store)
            audit.update(passed=True, store_directory=str(store.path), run_id=run_id,
                all_original_rows_unchanged=True, original_typed_form=frozen,
                scripted_provider_calls=0, exact_original_controller_factory_and_request=True,
                public_packet_reads=reads, private_or_native_File_reads=[])
    except BaseException as error:
        audit['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        (tmp_path / 'lumpy_closed_reconstruction_audit.json').write_text(json.dumps(audit, indent=2, allow_nan=False) + '\n')
