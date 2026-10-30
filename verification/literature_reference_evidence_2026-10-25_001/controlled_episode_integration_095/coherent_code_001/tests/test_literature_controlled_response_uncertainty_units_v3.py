"""Independent retained uncertainty carriers; constructed source reports only."""
import json

import pytest

from gene_annotation_episode import literature_controlled_response_storage as storage
from test_literature_controlled_response_storage_v3 import native_case,seed_runtime_rows
from test_literature_controlled_response_render_v3 import text_for


def configure_uncertainty_units(f,*,unknown_response=False):
    quote='Independent reported CI: [121.135791, 136.246802] nM/min.'
    f.append(quote);start=f.data[f.main_ref].index(quote.encode())
    uncertainty=f.args['arms']['protein_condition1']['reported_uncertainty']
    uncertainty.update(statistic=f.interp('ci','Independent reported CI'),magnitude=None,
        interval={'witness':f.witness(quote,tagged=False),
            'lower_start':quote.index('121.135791'),'lower_end':quote.index('121.135791')+len('121.135791'),
            'upper_start':quote.index('136.246802'),'upper_end':quote.index('136.246802')+len('136.246802')},
        unit=f.witness('nM/min',tagged=False,start=start),unit_relationship=f.interp('explicit_unit',quote),
        confidence_level=None,count=None)
    if unknown_response:f.args['arms']['protein_condition1']['measurement']['unit']=None


@pytest.mark.parametrize('unknown_response',[False,True])
def test_actual_explicit_uncertainty_carrier_survives_typed_receipt_and_render(tmp_path,unknown_response):
    store,context,args,_=native_case(tmp_path,modify=lambda f:configure_uncertainty_units(f,unknown_response=unknown_response))
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'fixture-run:fixture-child:4');row=outcome['result']['cells'][0]
        saved=repo.read(row['sheet_ref']);actual=saved['extraction']['arms']['protein_condition1']['reported_uncertainty']
        assert row['reported_uncertainty']==actual['canonical']
        assert row['reported_uncertainty_unit']==actual['effective_unit']['record']['canonical_unit']=='uM/min'
        assert row['reported_uncertainty']['interval']==[.121135791,.136246802]
        assert row['cell']['unit']==(None if unknown_response else 'umol/min')
        assert row['native_reading']['unit']==(None if unknown_response else 'nmol/min')
        parent,key=seed_runtime_rows(store,context,outcome,[row]);repo.receive_cells(parent,[row],key)
        assert repo.received_cells(parent)==[row]
        records={ref:store.get(ref) for ref in repo.cell_record_refs([row])}
        text=text_for([row],records,repo.semantic_bindings([row]))
        section=text.split('Requested source uncertainty\n')[1]
        uncertainty=json.loads(section)
        assert uncertainty['magnitude_and_interval_unit']=='uM/min'
        assert uncertainty['interval']==[.121135791,.136246802]
        assert 'nmol/min' not in section
        assert all(r['reported_uncertainty_unit'] is None for r in outcome['result']['cells'] if r['kind']!='native_raw')
    finally:store.close()
