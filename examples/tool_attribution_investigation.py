"""Real reference-only geometry and local traits with a late A101 sibling link."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from tool_attribution_native_fixture import ReferenceAttributionCase
from gene_annotation_episode.state import Store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory',type=Path,required=True)
    parser.add_argument('--usalign',required=True)
    args=parser.parse_args();directory=args.run_directory.resolve()
    if 'runs' not in directory.parts:raise ValueError('Output must be under runs/')
    directory.mkdir(parents=True,exist_ok=False)
    (directory/'tmp').mkdir();(directory/'cache').mkdir()
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(directory/'tmp'),XDG_CACHE_HOME=str(directory/'cache'))
    with Store(directory/'state') as store:
        case=ReferenceAttributionCase(directory,store,usalign=args.usalign)
        try:
            result=asyncio.run(case.run())
            print(json.dumps({'credit':result['final_credit']['credit'],'axes':result['final_credit']['axis_components'],
                'reference_fold_score':result['reference_fold_attachment']['score'],
                'traits':[{'key':t['physical_feature_key'],'score':t['score'],'positions':t['target_positions']} for t in result['local_traits']],
                'additional_structural_jobs_after_link_arrival':result['additional_structural_jobs_after_link_arrival']}),flush=True)
        finally:case.jobs.close()


if __name__=='__main__':main()
