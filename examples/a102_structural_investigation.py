"""Run a fresh configured-model A102 investigation on retained real structures.

The host fixes the input and commissions A102 once. Scientific and specialist
episode decisions use the configured ModelConnection. Trace, state, caches and
native execution remain beneath --run-directory. No expected function or score
is supplied to the model.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))

from a102_native_fixture import NativeCase,PUBLICATION
from gene_annotation_episode.a102_investigation import A102ServiceFactory
from gene_annotation_episode.a102_publication import received_grade
from gene_annotation_episode.decision_context import PROTOCOL,apply_state_frame
from gene_annotation_episode.numerical import YieldController,YieldEstimate,NumericBand
from gene_annotation_episode.providers import ModelConnection,load_config
from gene_annotation_episode.state import Store


CASES={'tpi':('P0A858.faa','AF_P0A858.pdb','1YPI.cif'),
    'lacy':('P02920.faa','AF_P02920.pdb','AF_P18817.pdb'),
    'atpg':('P0ABA6.faa','AF_P0ABA6.pdb','AF_Q9KNH4.pdb'),
    'mj0226':('MJ0226.faa','1B78.cif','1ADJ.cif')}


class ModelCase(NativeCase):
    def __init__(self,*args,connection,**kwargs):
        self.connection=connection
        self.roles=connection.roles
        super().__init__(*args,**kwargs,workflow_run_id='a102-real-model',decision_protocol=PROTOCOL,
            tool_retrieval={'version':'scientific_tool_retrieval_v1','mode':'semantic_fast_v1',
                'model':deepcopy(connection.config['FAST'])})

    def has_session(self,episode_id,role):return self.connection.has_session(episode_id,role)
    def conversation_key(self,episode_id,role):return self.connection.conversation_key(episode_id,role)
    async def release(self,episode_id):await self.connection.release(episode_id)

    def controller(self,path,initial):
        horizon=1 if path[-1][0]=='annotation' else 12 if path[-1][0]=='scientific_process' else 6
        def estimate(history,parameters,contexts):
            return YieldEstimate(len(history),NumericBand.exact(0 if len(history)>=horizon else 1),parameters,
                {'validation':'explicit_finite_action_budget','budget':horizon,
                    'meaning':'Model chooses every scientific action; budget is a validation constraint, not biological saturation.'})
        return YieldController(str(path),initial,0,estimate_with_context=estimate)

    async def complete(self,episode_id,role,instructions,frame,output_schema):
        if role=='FAST':return await self.connection.complete(episode_id,role,instructions,frame,output_schema)
        path=json.loads(self.store.db.execute('SELECT path FROM runtime_episodes WHERE episode_id=?',
            (episode_id,)).fetchone()[0])
        if path[-1][0]!='annotation':
            return await self.connection.complete(episode_id,role,instructions,frame,output_schema)
        if frame.get('kind') in {'decision_bootstrap','decision_update'}:
            self.states[episode_id]=apply_state_frame(self.states.get(episode_id),frame)
        sources=[]
        for ordinal,(filename,reference) in enumerate(zip(self.files,self.file_refs,strict=True)):
            sources.append({'file_source_ref':reference,'role':'target_model' if ordinal==0 else 'comparison_lead',
                'format':'pdb_3x_text' if filename.endswith('.pdb') else 'pdbx_mmcif_text',
                'chain_id':'A','model_ordinal':0,'block_ordinal':0,
                'origin':'predicted' if filename.startswith('AF_') else 'experimental'})
        selected=self.subtree.commission(self.store,target_ref=self.target,scope=self.scope,
            completeness='unknown',child_tool_info=[{'name':name,'resources':'local'} for name in (
                'structure.bind','structure.inspect','structure.align','structure.discover',
                'structure.feature_geometry','structure.contrast','structure.reported_comparison',
                'structure.model_request','state.query','source.read','sequence.inspect')],
            question='Investigate structural homology of the anonymous supplied protein using the actual received '
                'structure files listed in context. Choose and execute the structural work needed to establish '
                'correspondence, inspect actual native credit, preserve extent and model qualifications, and '
                'communicate missing functional facts to the shared parent. No candidate function is supplied. '
                'Return a valid bounded interpretation with the actual scientific records.',
            context={'supplied_structures':sources,'validation_budget':'12 scientific own actions; choose useful work within the finite budget.'})
        return {'response':{'response_type':'select_action','selection':selected,'report_update':{}}}


async def main_async(args):
    directory=Path(args.run_directory).resolve()
    if 'runs' not in directory.parts:raise ValueError('Validation output requires a runs/ directory')
    directory.mkdir(parents=True,exist_ok=False)
    for name in ('tmp','cache'):(directory/name).mkdir()
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(directory/'tmp'),XDG_CACHE_HOME=str(directory/'cache'))
    configuration=load_config(args.model_config)
    with Store(directory/'state') as store:
        async with ModelConnection(configuration,directory/'provider',directory) as connection:
            sequence,target,reference=CASES[args.case]
            case=ModelCase(directory,store,connection=connection,sequence_file=sequence,target_file=target,
                reference_file=reference,usalign=args.usalign,foldseek=args.foldseek)
            record=await asyncio.wait_for(case.run(),timeout=args.timeout)
            native=[]
            for row in store.db.execute('SELECT source_ref FROM a102_native_publications'):
                grade=received_grade(store,row[0])['grade']
                native.append({'source_ref':row[0],'producer':grade['producer'],'components':grade['components'],
                    'target_model':grade['target_model'],'reference_model':grade['reference_model'],
                    'function_specific':grade['function_specific']})
            forms=[json.loads(row[0]) for row in store.db.execute('SELECT form FROM runtime_report_attempts '
                'WHERE form IS NOT NULL')]
            result={'case':args.case,'decision_mode':'fresh_configured_model_scientific_and_specialist_episodes',
                'model_configuration':configuration,'native_comparisons':native,
                'parent_credit':record.controller_state.current_credit,'returned_forms':forms,
                'decisions':[{'path':json.loads(row[0]),'action':json.loads(row[1])} for row in store.db.execute(
                    'SELECT episodes.path,actions.action FROM runtime_actions actions JOIN runtime_episodes episodes '
                    'USING(run_id,episode_id) WHERE actions.result IS NOT NULL ORDER BY actions.rowid')]}
            (directory/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps({'case':args.case,'parent_credit':result['parent_credit'],
                'native_comparison_count':len(native),'result_path':str(directory/'RESULTS.json')}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=CASES,required=True)
    parser.add_argument('--run-directory',required=True)
    parser.add_argument('--usalign',required=True)
    parser.add_argument('--foldseek')
    parser.add_argument('--model-config')
    parser.add_argument('--timeout',type=float,default=1200)
    asyncio.run(main_async(parser.parse_args()))


if __name__=='__main__':main()
