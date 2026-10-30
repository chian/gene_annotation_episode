"""Cold synthetic saved-return check; never opens provider or model records."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def forbidden(*args, **kwargs):
    raise AssertionError('cold reconstruction must not read scientific sources or recalculate')


def main():
    import gene_annotation_episode.literature_activity_calculations as calculator
    import gene_annotation_episode.literature_assay_inputs as assay_inputs
    import gene_annotation_episode.literature_prose_reader as prose
    calculator.populate_corrected_activity = forbidden
    assay_inputs.read_assay_inputs = forbidden
    prose.read_jats_quantity = forbidden
    state, manifest = sys.argv[1:]
    data = json.loads(Path(manifest).read_text())
    context, parent = BindingContext(**data['context']), BindingContext(**data['parent'])
    with Store(state) as store:
        metadata = store.get(data['outcome']['result']['sheet_ref'])
        allowed = {metadata['artifact_ref'], metadata['request_ref']}
        original_get = store.get_artifact
        def retained_only(reference):
            if reference not in allowed:
                forbidden()
            return original_get(reference)
        store.get_artifact = retained_only
        host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
        services = WorkflowServices(host)
        composition = compose_episode_bindings(services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None,
            descriptors=[data['descriptor']], job_episodes=None,
            resource_estimator=None, role_credit_bindings={})
        binding, = composition.bindings
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        repository = getattr(services, f'literature_{data["kind"]}_repository')()
        assert binding.as_record() == data['descriptor']
        assert asyncio.run(binding.execute(context, f'literature.{data["kind"]}.populate',
            data['arguments'], data['operation_key'])) == data['outcome']
        current = replace(context, received_record_refs=parent.received_record_refs)
        assert repository.read(metadata['id']) == data['payload']
        binding.validate_report(current, data['form'], data['schema'])
        assert repository.received_cells(parent) == data['form']['measurements']
        assert binding.received_report_facts(parent)[f'literature_{data["kind"]}_cells'] == data['form']['measurements']
        assert store.db.execute(f'SELECT count(*) FROM {repository.operations_table}').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        print(json.dumps({'kind': data['kind'], 'version': data['payload']['version'],
            'exact_admitted_cells': len(data['form']['measurements']), 'source_reads': 0, 'calculations': 0}))


if __name__ == '__main__':
    main()
