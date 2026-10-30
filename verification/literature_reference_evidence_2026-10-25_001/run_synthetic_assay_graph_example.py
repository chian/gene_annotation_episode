"""Verification-only synthetic source graph; ordinary loop coverage is in tests.

This script intentionally uses the explicit synthetic test source factory. It
executes the installed selected-operation adapter, not a biological source, a
live model or a standalone workflow/episode implementation.
"""
import argparse
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
from test_literature_assay_integration import setup_store,binding_for,COMPONENTS,FORM
from gene_annotation_episode.communication import form_with_facts


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    destination=parser.parse_args().output
    destination.mkdir(parents=True,exist_ok=False)
    results=[]
    for complete in (True,False):
        label='complete' if complete else 'missing_contaminant'
        store,context,args=setup_store(destination/label,full=complete)
        try:
            binding=binding_for(store,context)
            outcome=asyncio.run(binding.execute(context,'literature.assay.populate',args,'selected-demo'))
            if outcome['status']!='completed':
                raise RuntimeError(outcome)
            current=replace(context,received_record_refs=(*context.received_record_refs,*outcome['record_refs']))
            form=form_with_facts({},FORM,binding.facts(current,{'committed_record_refs':outcome['record_refs']}))
            binding.validate_report(current,form,FORM)
            payload=binding.services.literature_assay_repository().read(outcome['result']['sheet_ref'])
            results.append({'case':label,'origin':'synthetic_fixture','selected_arguments':args,
                            'outcome':outcome,'saved_sheet':payload,'requested_form':form})
            print(json.dumps({'case':label,'synthetic_values':{
                row['component']:row['value'] for row in form['measurements']}}))
        finally:
            store.close()
    output={'execution_kind':'direct_selected_operation_adapter','actual_model_inference':False,
            'primary_source_measurements':False,'cases':results}
    (destination/'SYNTHETIC_ASSAY_GRAPH_POPULATION.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    main()
