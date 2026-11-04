"""Constructed source-origin custody; no graph digitization or new assay."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.domain import canonical
from test_literature_reaction_native_integration_129 import setup_case, binding_for, source


@pytest.mark.parametrize('kind,expected', [('primary_source', 'reported'), ('retained_extraction', 'reported'),
    ('graph_extraction', 'graph_derived'), ('synthetic_fixture', 'synthetic')])
def test_native_source_kind_origin_survives_normalization_saved_cells_and_typed_view(tmp_path, kind, expected):
    store, context, args = setup_case(tmp_path / 'state')
    with store:
        args['source_kind'] = kind
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.reaction.populate', args, 'origin'))
        assert outcome['status'] == 'completed', outcome
        assert outcome['result']['ratio_origin'] == expected
        assert outcome['result']['cells']['ratio_mean']['origin'] == expected
        adapter = binding.services.literature_reaction_repository().native_observations_projection()
        rows = adapter.project_rows([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
        assert rows and all(row['origin'] == expected for row in rows)
        saved = adapter.read(outcome['result']['sheet_ref'])
        assert saved['extraction']['calculation_inputs']['ratio']['origin'] == expected
        assert saved['sheet']['inputs']['ratio']['origin'] == expected
        assert asyncio.run(binding.execute(context, 'literature.reaction.populate', args, 'origin')) == outcome


@pytest.mark.parametrize('version', ['a110_source_reaction_measurements_v1', 'a110_source_reaction_measurements_v2'])
def test_legacy_prepared_graph_origin_is_unchanged(tmp_path, version):
    store, context, args = setup_case(tmp_path / 'state')
    with store:
        binding = binding_for(store, context)
        initial = asyncio.run(binding.execute(context, 'literature.reaction.populate', args, 'prepare-fixture'))
        saved = binding.services.literature_reaction_repository().read(initial['result']['sheet_ref'])
        data = deepcopy(saved['extraction']['observations'])
        data['version'] = version
        data['ratio']['origin'] = 'graph_derived'
        if version.endswith('_v1'):
            data.pop('meanings')
        dataset = source(store, canonical(data), [args['source_ref']])
        context = replace(context, received_record_refs=(*context.received_record_refs, dataset['id']))
        args.update(data_source_ref=dataset['id'], source_kind='graph_extraction')
        outcome = asyncio.run(binding.execute(context, 'literature.reaction.populate', args, 'legacy-graph'))
        assert outcome['status'] == 'completed', outcome
        assert outcome['result']['ratio_origin'] == 'graph_derived'
        assert outcome['result']['cells']['ratio_mean']['origin'] == 'graph_derived'
        assert 'native_observations' not in outcome['result']
