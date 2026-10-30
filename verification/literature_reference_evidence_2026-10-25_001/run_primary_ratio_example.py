"""Deterministic primary-source adapter example, not a model/episode run."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.state import Store
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_ratio_storage import LiteratureRatioRepository
from register_yeag_sources import register_sources


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    destination=parser.parse_args().output
    destination.mkdir(parents=True,exist_ok=False)
    with Store(destination/'state') as store:
        # Synthetic caller material isolates this source-adapter check. No target
        # function or correspondence is inferred from it.
        store.create_problem(raw_sequence='ATGGCT',molecule='dna')
        sources=register_sources(store,Path(__file__).parent/'primary_yeag')
        context=BindingContext('primary-yeag-ratios','direct-source-adapter','literature',
            (('literature','source'),),store.validate_scope(),{},{},sources['source_refs'])
        repo=LiteratureRatioRepository(store,context.run_id)
        results=[]
        for variant,visual in sources['visual_transcriptions'].items():
            args={'source_ref':sources['paper_ref'],'source_kind':'primary_jats','section_id':'sec2','paragraph_index':1,
                'subject':'YeaG','variant':variant,'reference_literal':'wild-type levels','visual_source_refs':[visual],
                'signal_kind':'unknown','reference_role':'unknown','arrangement':'unknown','interpretation_witnesses':[]}
            outcome=repo.populate(context,args,variant)
            payload=repo.read(outcome['result']['sheet_ref'])
            results.append({'variant':variant,'selected_arguments':args,'outcome':outcome,'saved_sheet':payload})
            cell=payload['sheet']['cells']['reported_ratio']
            print(json.dumps({'variant':variant,'value':cell['value'],'candidates':cell['value_candidates'],'status':cell['status']}))
        (destination/'PRIMARY_RATIO_POPULATION.json').write_text(json.dumps({'execution_kind':'direct_deterministic_adapter',
            'model_inference':False,'visual_origin':'manual_visual_transcription_of_printed_labels',
            'sources':sources,'results':results},ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
