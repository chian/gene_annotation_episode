"""Run an A103 genomic-context investigation on retained real inputs."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))

from gene_annotation_episode.workflow_budget import active_budget
active_budget()  # Before importing BioPython, application setup, or providers.

from a103_native_fixture import A103NativeCase,CASES
from gene_annotation_episode.providers import ModelConnection,load_config
from gene_annotation_episode.state import Store


async def main_async(args):
    directory = Path(args.run_directory).resolve()
    if 'runs' not in directory.parts:raise ValueError('A103 output requires runs/')
    prepared=(args.retained_state is not None and args.retained_state.resolve()==directory/'state')
    if prepared:
        names={p.name for p in directory.iterdir()} if directory.is_dir() else set()
        if 'state' not in names or not names<={'state','recovered-native'}:
            raise ValueError('prepared_case_must_contain_only_its_explicit_retained_state')
    else:directory.mkdir(parents=True,exist_ok=False)
    for name in ('tmp','cache'):(directory/name).mkdir()
    retained=None
    if args.retained_state is not None:
        retained=json.loads((args.retained_state/'RETAINED_INPUTS.json').read_text())
        if not prepared:args.retained_state.rename(directory/'state')
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(directory/'tmp'),XDG_CACHE_HOME=str(directory/'cache'))
    with Store(directory/'state') as store:
        if args.smoke:
            result = await asyncio.wait_for(A103NativeCase(directory,store,case=args.case,smoke=True,wiring_smoke=args.wiring_smoke).run(),args.timeout)
        else:
            async with ModelConnection(load_config(args.model_config),directory/'provider',directory) as connection:
                result = await asyncio.wait_for(A103NativeCase(directory,store,case=args.case,connection=connection,
                    retained_inputs=retained).run(),args.timeout)
    print(json.dumps({'case':args.case,'decision_mode':result['decision_mode'],'axis_components':result['credit']['axis_components'],
        'root_credit':result['credit']['credit'],'native_jobs':result['total_native_job_count']}),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=CASES,required=True)
    parser.add_argument('--run-directory',required=True)
    parser.add_argument('--model-config')
    parser.add_argument('--retained-state',type=Path)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--wiring-smoke',action='store_true',help='Extend the scripted smoke through native sibling sequence attribution (requires --smoke and poxa).')
    parser.add_argument('--timeout',type=float,default=1800)
    asyncio.run(main_async(parser.parse_args()))


if __name__=='__main__':main()
