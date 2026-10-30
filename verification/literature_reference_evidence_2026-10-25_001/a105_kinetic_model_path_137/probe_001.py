"""Synthetic engineering population only: no paper, model service or credit."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.literature_kinetic_model_storage import kinetic_model_cells_schema
from test_literature_kinetic_model_inputs import setup_model
from test_literature_kinetic_model_integration import binding_for

async def main():
    results = []
    for status in ('known', 'estimated', 'absent'):
        store, context, native_args, model_args, _, _ = setup_model(Path(__file__).parent / ('synthetic_probe_state_' + status),
            status='known' if status == 'absent' else status)
        try:
            binding = binding_for(store, context)
            native = await binding.execute(context, 'literature.kinetic.populate', native_args, 'synthetic-native')
            assert native['status'] == 'completed', native
            if status == 'absent':
                model_args.update(model_source_ref=None, model_witnesses=[])
            model_args['source_ref'] = native['result']['sheet_ref']
            context = replace(context, received_record_refs=(*context.received_record_refs, *native['record_refs']))
            modeled = await binding.execute(context, 'literature.kinetic.model.populate', model_args, 'synthetic-model')
            assert modeled['status'] == 'completed', modeled
            context = replace(context, received_record_refs=(*context.received_record_refs, *modeled['record_refs']))
            facts = binding.facts(context, {'committed_record_refs': [modeled['result']['sheet_ref']]})
            form = obj({'kinetic_model': kinetic_model_cells_schema()})
            returned = form_with_facts({}, form, facts)
            binding.validate_report(context, returned, form)
            results.append({'fixture': 'synthetic_Km_20_over_10_uM', 'variance_case': status,
                'native_five_cells': native['result']['cells'], 'typed_four_model_cells': returned['kinetic_model'],
                'ordinary_runtime_observations': 'not_run_in_this_direct_adapter_probe'})
        finally:
            store.close()
    target = Path(__file__).parent / 'SYNTHETIC_POPULATION_001.json'
    target.write_text(json.dumps({'scientific_status': 'synthetic_engineering_fixture_only', 'cases': results}, indent=2) + '\n')
    print(target)

if __name__ == '__main__':
    asyncio.run(main())
