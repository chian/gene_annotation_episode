"""Run one full autonomous A108 investigation from supplied protein material.

An optional root assignment supplies the organism, candidate function and
biological question. Evaluator expectations and preferred publications are
never loaded. This is a live-workflow driver, not a pytest test. Launch it
through tools/one_workflow.sh; generated output belongs beneath runs/.
"""
import argparse
import asyncio
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import traceback


GOAL = (
    'Investigate A108 organism-context evidence for the supplied protein sequence. '
    'Establish the target organism and available strain/sample context from the '
    'supplied material and acquired records. Discover plausible functional '
    'assertions when none were supplied, retaining their origin and uncertainty. '
    'Find literature and database observations about the organism physiology, '
    'environment, substrate/cofactor availability and cellular localization '
    'that bear on those assertions. Select questions relevant to the actual '
    'organism and proposed function. Use the purpose-specific subscoring sheets '
    'and main A108 evidence scoring sheet to return numerical supporting, '
    'conflicting and unresolved evidence, with original observation identity '
    'and actual organism/context relationships preserved. Return useful partial '
    'results and the specific unresolved source or context links.'
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--assignment', type=Path,
                        help='Root-provided organism, candidate function and question JSON.')
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--source-root', type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = args.source_root.resolve()
    repository = Path(__file__).resolve().parents[1]
    run = args.run_dir.resolve()
    if not run.is_relative_to(repository / 'runs'):
        parser.error('--run-dir must be beneath the repository runs directory')
    assignment_bytes = None if args.assignment is None else args.assignment.read_bytes()
    assignment = None if assignment_bytes is None else json.loads(assignment_bytes)
    if assignment is not None:
        fields = {'schema_version', 'organism', 'candidate_function', 'sample_context', 'question'}
        if (not isinstance(assignment, dict) or set(assignment) != fields
                or assignment['schema_version'] != 1
                or not isinstance(assignment['question'], str) or not assignment['question'].strip()
                or any(not isinstance(assignment[key], dict)
                       for key in ('organism', 'candidate_function', 'sample_context'))):
            parser.error('--assignment requires the root-assignment input schema')
    assignment_digest = (None if assignment_bytes is None else
                         hashlib.sha256(assignment_bytes).hexdigest())
    goal = GOAL if assignment is None else (
        GOAL + '\n\nRoot-provided assignment:\n' + json.dumps(assignment, indent=2))
    if args.resume:
        original = json.loads((run / 'launch.json').read_text())
        if original.get('assignment_sha256') != assignment_digest or original['goal'] != goal:
            parser.error('resume requires the original root assignment')
    run.mkdir(parents=True, exist_ok=True)
    (run / 'tmp').mkdir(exist_ok=True)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['TMPDIR'] = str(run / 'tmp')
    os.environ['XDG_CACHE_HOME'] = str(run / 'cache')
    sys.path.insert(0, str(root))
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_configuration import build_tools

    flags = dict(a108_context_evidence=True, reference_parent_sources=[],
                 contract_information_profile=CONTRACT_INFORMATION_PROFILE)
    config = {'public': {'provider_access_dir': str(run / 'provider-access')},
              'local_tools': {'minimap2_cache_dir': str(run / 'cache/minimap2')}}
    for name in ('pdfinfo', 'pdftotext', 'pdftoppm'):
        executable = shutil.which(name)
        if executable:
            config['local_tools'][name + '_executable'] = executable

    async def execute():
        with Store(run / 'state') as store:
            if not args.resume:
                sequence = ''.join(args.input.read_text().split())
                if not sequence or not sequence.isalpha():
                    raise ValueError('input must contain only the raw protein sequence')
                store.create_problem(raw_sequence=sequence, molecule='protein',
                                     caller_context=assignment)
                (run / 'input.txt').write_text(sequence + '\n')
                if assignment_bytes is not None:
                    (run / 'assignment.json').write_bytes(assignment_bytes)
                (run / 'launch.json').write_text(json.dumps({
                    'goal': goal, 'input_mode': ('raw_sequence_only' if assignment is None
                                                else 'sequence_and_root_assignment'),
                    'assignment_sha256': assignment_digest,
                    'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
                    'sequence_length': len(sequence), 'literature_flags': flags,
                    'models': 'repository defaults',
                    'controller': 'repository default YieldController',
                    'annotation_child_roles': ['literature'],
                    'preloaded_evidence': [], 'scripted_model_decisions': False,
                    'evaluator_expectations_loaded': False,
                    'targeted_tests': False,
                }, indent=2) + '\n')
            initial_refs = [store.targets()[0]['source_ref']]
            supplied_context = store.problem().get('caller_context_source_ref')
            if supplied_context is not None:
                initial_refs.append(supplied_context)
            result = await run_workflow(store, build_tools(store, config),
                run_dir=run / 'workflow', resume=args.resume, goal=goal,
                episode_binding_factories=(partial(LiteratureEpisodes, **flags),),
                initial_known_record_refs=initial_refs,
                annotation_child_roles=('literature',))
            (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result), flush=True)

    try:
        asyncio.run(execute())
    except BaseException as error:
        (run / 'failure.json').write_text(json.dumps({
            'type': type(error).__name__, 'message': str(error),
            'traceback': traceback.format_exc()}, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
