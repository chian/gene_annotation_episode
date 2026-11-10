"""Resume an interrupted original A104 HPC pilot without replacing its PBS job.

Original scientific/source snapshots stay unchanged. This explicit migration
turns the known missing-handoff tool failure into feedback and selects formal
redelivery of the parent's own completed Launch report. The corrected custody
reader admits original results. Every repair remains an ordinary journalled
action; no private child records are injected into the parent's receipts.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-directory', type=Path, required=True)
    args = parser.parse_args()
    case = args.case_directory.resolve()
    source = case.parent/'source'
    sys.path.insert(0, str(source))
    from gene_annotation_episode.workflow_budget import active_budget
    run = Path(active_budget()['run_directory'])
    original = load('a104_original_hpc_driver', source/'examples/a104_hpc_investigation.py')
    reader_path = run/'a104_custody_reader.py'
    shutil.copy2(root/'gene_annotation_episode/a104_hpc.py', reader_path)
    reader = load('gene_annotation_episode.a104_repair_custody_reader', reader_path)
    original.import_result = reader.import_result
    base_workflow, base_connection = original.Workflow, original.ModelConnection

    class RepairWorkflow(base_workflow):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            binding = self.episode_bindings.for_role('hpc')
            execute = binding.execute
            async def recover_feedback(context, name, arguments, key):
                try:
                    return await execute(context, name, arguments, key)
                except ValueError as error:
                    if name not in {'hpc.results', 'hpc.monitor', 'hpc.monitor.wait'} \
                            or not str(error).startswith('unknown_hpc_evidence:handoff:'):
                        raise
                    print(json.dumps({'event': 'original_missing_handoff_returned_as_feedback',
                        'operation_key': key, 'code': str(error)}), flush=True)
                    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                        'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                            'next_step': 'redeliver the original Launch using hpc_launch_report_form; do not submit again'}}
            binding.execute = recover_feedback

    class RepairConnection(base_connection):
        async def complete(self, episode_id, role, instructions, frame, output_schema):
            deliveries = {row['delivery_ref']: row for row in frame.get('hpc_launch_deliveries', [])}
            if not deliveries and 'hpc_commission' in frame:
                # Earlier snapshots exposed these same parent-owned returns
                # through the ordinary report fields, without the new alias.
                reports = frame.get('child_reports', [])
                delivered = frame.get('report_deliveries', [])
                if len(reports) == len(delivered):
                    deliveries = {row['delivery_ref']: {'delivery_ref': row['delivery_ref'],
                        'delivered_form': report} for row, report in zip(delivered, reports)
                        if 'execution_handoff_refs' in report}
            missing = [row for row in deliveries.values()
                       if not (row.get('delivered_form') or {}).get('execution_handoff_refs')]
            schema = frame.get('hpc_launch_report_form')
            if missing and schema is None:
                schema = {'type': 'object', 'additionalProperties': False, 'properties': {
                    'execution_handoff_refs': {'type': 'array', 'uniqueItems': True,
                        'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_handoff'},
                        'x-source': 'execution_handoff_refs'}}, 'required': ['execution_handoff_refs']}
            if missing and schema:
                reference = missing[-1]['delivery_ref']
                print(json.dumps({'event': 'select_original_launch_report_redelivery',
                    'episode_id': episode_id, 'delivery_ref': reference}), flush=True)
                return {'selection': {'kind': 'redeliver_report', 'delivery_ref': reference,
                    'purpose': 'Recover the original completed Launch handoff fact for this same submitted PBS job.',
                    'schema_json': json.dumps(schema)}, 'report_update': {}}
            return await super().complete(episode_id, role, instructions, frame, output_schema)

    original.Workflow, original.ModelConnection = RepairWorkflow, RepairConnection
    manifest = {'version': 'a104_explicit_original_run_repair_v1', 'case_directory': str(case),
        'source_snapshot_unchanged': str(source), 'reader_sha256': hashlib.sha256(reader_path.read_bytes()).hexdigest(),
        'repair_driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'submission_rule': 'reuse_original_only; no replacement_job_or_new_scientific_computation'}
    (run/'REPAIR.json').write_text(json.dumps(manifest, indent=2)+'\n')
    asyncio.run(original.run(argparse.Namespace(case_directory=case, repository_root=root, model_config=None)))


if __name__ == '__main__':
    main()
