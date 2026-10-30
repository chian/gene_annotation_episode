"""Configured-model source investigation in the existing ordinary Workflow.

Run with an immutable package snapshot. No scripted decisions, custom projector,
fixed-turn controller, private episode loop or source-completion override.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--pin',type=Path,required=True)
parser.add_argument('--directory',type=Path,required=True)
parser.add_argument('--resume',action='store_true')
args=parser.parse_args()
pin=args.pin.resolve()
directory=args.directory.resolve()
sys.path.insert(0,str(pin))
from functools import partial
from gene_annotation_episode.state import Store
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.providers import load_config
from gene_annotation_episode.tool_configuration import build_tools
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from register_yeag_sources import register_sources

JOB='''Evaluate what the supplied YeaG experimental reference paper establishes and what it does not establish. This is a source-evidence task, not an annotation of the supplied fixed gene and not target correspondence. Examine the actual experimental subject/genotype/construct, molecular arrangement, conditions, measured endpoints, controls and uncertainty. Resolve the Fig3 recovery-growth and protein-signal comparisons separately from Fig6 survival. Keep the tagged WT signal reference distinct from physiological WT/empty-vector controls. Preserve disagreement between original prose and printed figure representations without averaging or calling representations independent. Determine which numerical experimental components are justified and which activity, calibration, amount-response or uncertainty inputs are unavailable.
Use the assigned retained original paper/image and explicitly labeled retained visual transcriptions; the latter are manually inspected printed labels, not OCR, raw densitometry, new assays or calibrated protein counts. Their original image custody is preserved. Reading the original source is available. Literature investigations can perform selected deterministic numerical population operations and return the needed closed numerical forms. Choose useful work and request only the typed information needed for integration. Do not create target assessments, transfer weights, enzyme rates from growth, or missing zero/one operands. Possible function claims can emerge, but no initial candidate annotation is required. The parent owns integration of its received source evidence; the ordinary configured estimator/controller owns continuation. No additional paper search or target computation is needed to answer this bounded source question. Keep genuine source conflicts and unknowns, including the source's strain naming, rather than resolving them by assumption.'''


async def main():
    if not args.resume:
        directory.mkdir(parents=True,exist_ok=False)
    (directory/'PROCESS.json').write_text(json.dumps({'pid':os.getpid(),'pin':str(pin),
        'caller':str(Path(__file__).resolve()),'mode':'resume' if args.resume else 'new'},indent=2)+'\n')
    with Store(directory/'state') as store:
        if args.resume:
            source_info=json.loads((directory/'SOURCE_INPUTS.json').read_text())
        else:
            fasta=(pin/'inputs/target.fna').read_text()
            sequence=''.join(line.strip() for line in fasta.splitlines() if line.strip() and not line.startswith('>'))
            store.create_problem(raw_sequence=sequence,molecule='dna')
            source_info=register_sources(store,pin/'inputs/primary_yeag')
            (directory/'SOURCE_INPUTS.json').write_text(json.dumps(source_info,indent=2)+'\n')
            (directory/'JOB.txt').write_text(JOB+'\n')
            (directory/'INPUT_DIGESTS.json').write_text(json.dumps({
                'target_fasta_sha256':hashlib.sha256((pin/'inputs/target.fna').read_bytes()).hexdigest(),
                'target_sequence_sha256':hashlib.sha256(sequence.encode()).hexdigest(),
                'paper_sha256':hashlib.sha256((pin/'inputs/primary_yeag/PMC4664914_original.xml').read_bytes()).hexdigest(),
                'figure_sha256':hashlib.sha256((pin/'inputs/primary_yeag/srep17524-f3.jpg').read_bytes()).hexdigest()},indent=2)+'\n')
        configuration=load_config()
        tools=build_tools(store,configuration)
        print(json.dumps({'phase':'configured_workflow_start','pid':os.getpid(),
            'source_count':len(source_info['source_refs']),'ordinary_tool_count':len(tools.catalog(scope=store.validate_scope())),
            'models':{key:configuration[key] for key in ('REASONING','FAST')}}),flush=True)
        result=await run_workflow(store,tools,provider_config=configuration,run_dir=directory/'run',resume=args.resume,
            goal=JOB,initial_known_record_refs=source_info['source_refs'],
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
                reference_parent_sources=source_info['source_refs']),),annotation_child_roles=('literature',))
        (directory/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'phase':'configured_workflow_returned','result':result}),flush=True)


if __name__=='__main__':
    try:asyncio.run(main())
    except BaseException as error:
        (directory/'CALLER_ERROR.json').write_text(json.dumps({'type':type(error).__name__,'message':str(error)},indent=2)+'\n')
        raise
