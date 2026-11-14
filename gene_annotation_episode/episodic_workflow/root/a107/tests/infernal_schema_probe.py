"""Actual private schema callback baseline; no Infernal execution/evidence.

The constructor is real; the presence of a configured Infernal return adapter is
the controlled port. Schema factories and both owner callbacks are actual code.
"""
import json
from types import SimpleNamespace

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from .rna_context_probe import module, PARENTS


def probe(output, *, expected):
    if expected not in {'missing_original_helper', 'original_helper_restored'}:
        raise ValueError('explicit_expected_regression_phase_required')
    output.mkdir(parents=True)
    rows = []
    with module('state').Store(output / 'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        for parent in PARENTS:
            for leaf in ('execution_job_submission', 'execution_result_acquisition'):
                home = parent + '/' + leaf
                owner = module(home + '/episode').ExecutionEpisode(
                    SimpleNamespace(annotation_task_required=lambda: False), store=store,
                    run_id='a107-infernal-schema', directory=output / 'workflow', resources=resources(),
                    initial_information={}, tool_registry=None, handoff_unit=3, acquired_record_unit=2,
                    log_window_bytes=1024, log_roles=('stdout', 'stderr'))
                owner.native_infernal_returns = SimpleNamespace(controlled_adapter_presence=True)
                owner.native_infernal_results = SimpleNamespace(controlled_adapter_presence=True)
                for name, role in (('received_report_sources', 'annotation'), ('fact_sources', 'results')):
                    row = {'home': home, 'callback': name, 'role': role}
                    try:
                        result = getattr(owner, name)(role)
                        if expected == 'missing_original_helper':
                            raise AssertionError('expected_missing_helper_did_not_raise')
                        schema = result['execution_infernal_result_refs']['report_schema']
                        assert schema == {'type': 'array', 'uniqueItems': True,
                            'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
                            'x-source': 'execution_infernal_result_refs'}
                        row.update(status='returned_original_schema', descriptor=result['execution_infernal_result_refs'])
                    except AttributeError as error:
                        if expected != 'missing_original_helper' or '_infernal_reference_source' not in str(error): raise
                        row.update(status='reproduced_missing_original_helper', exception_type=type(error).__name__, message=str(error))
                    rows.append(row)
    (output / 'infernal_schema_probe.json').write_text(json.dumps({'expected': expected,
        'checks': rows, 'controlled_port': 'native_infernal_returns presence only; no native work or evidence'}, indent=2) + '\n')
    return {'checks': len(rows), 'output': str(output), 'expected': expected}
