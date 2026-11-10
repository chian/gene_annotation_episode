"""Run a full, unscripted A105 workflow from a raw sequence.

This is an executable live-workflow driver, not a pytest test. Evaluator
expectations are deliberately not loaded. All generated output belongs in runs/.
"""
import argparse
import asyncio
from functools import partial
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib
import traceback


def build_literature_controller(cost):
    """Apply the caller's A105 calibration to the measured literature role."""
    from gene_annotation_episode.numerical import YieldController, YieldParameters, provenance
    from gene_annotation_episode.providers import default_config_path
    from gene_annotation_episode.runtime import controller_from_settings

    control = tomllib.loads(default_config_path().read_text())['controller']
    parameters = YieldParameters(**{key: value for key, value in control.items() if key != 'cost'})
    YieldController('configuration', 0, cost, parameters)
    baseline = controller_from_settings({'controller': control})

    def controller(path, initial_credit):
        original = baseline(path, initial_credit)
        if path[-1][0] == 'literature':
            return YieldController(original.epoch, initial_credit, cost, original.settings)
        return original

    definition = {
        'version': 'existing_yield_controller_explicit_role_costs_v2',
        'cost': control['cost'], 'cost_by_role': {'literature': cost},
        'parameters': parameters.as_record(), 'estimator': provenance(),
        'continuation': 'available_next_gain_upper_bound_lte_cost',
        'cost_selection': 'exact_episode_role_override_otherwise_caller_cost',
    }
    return controller, definition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--literature-continuation-cost', type=float, default=0.075,
                        help='Yield-based continuation cost for the A105 literature episode, in its existing credit units.')
    parser.add_argument('--database-focus', choices=('sabiork', 'brenda', 'bioassay', 'chembl', 'mavedb'),
                        help='Commission a full A105 investigation centered on this source and its publications.')
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if 'runs' not in run.parts:
        parser.error('--run-dir must be beneath the repository runs directory')
    run.mkdir(parents=True, exist_ok=True)
    (run / 'tmp').mkdir(exist_ok=True)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['TMPDIR'] = str(run / 'tmp')
    os.environ['XDG_CACHE_HOME'] = str(run / 'cache')
    sys.path.insert(0, str(args.source_root.resolve()))
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
    controller, controller_definition = build_literature_controller(args.literature_continuation_cost)

    goal = (
        'Investigate A105 direct experimental evidence of molecular function for the supplied protein sequence. '
        'Discover relevant experiments using the available literature and experimental database sources. '
        'Consider the coverage and purpose of each available experimental database; query those that '
        'could supply relevant direct experiments and inspect positive records through the same scoring workflow. '
        'Establish the actual assayed molecules, constructs and preparations and their relationship to the input. '
        'Recover what the measurements, controls, conditions and uncertainty establish. '
        'Save the supported assay assessments and combined A105 experimental subscore using the existing '
        'readers, graders and aggregation. Return useful partials with specific unresolved requirements.'
    )
    if args.database_focus:
        goal += (
            f' Center this investigation on the experimental records accessible through {args.database_focus} '
            'search and read operations and their cited publications. Resolve the molecule from the raw '
            'sequence, select relevant queries and experiments, and carry the supported evidence through '
            'the complete existing A105 grading, aggregation and return workflow.'
        )
    flags = dict(rate_population=True, ratio_source_population=True,
        controlled_response_population=True, gel_population=True,
        completion_time_population=True, product_partition_population=True,
        active_site_population=True, parent_depletion_population=True,
        stoichiometric_balance_population=True, compiled_assay_population=True,
        channel_population=True, ion_discrimination_population=True,
        assay_grading_population=True, reference_parent_sources=[],
        contract_information_profile=CONTRACT_INFORMATION_PROFILE)
    config = {'public': {'provider_access_dir': str(run / 'provider-access')},
              'local_tools': {'minimap2_cache_dir': str(run / 'cache/minimap2')}}
    for name in ('pdfinfo', 'pdftotext', 'pdftoppm'):
        if shutil.which(name):
            config['local_tools'][name + '_executable'] = shutil.which(name)

    async def execute():
        with Store(run / 'state') as store:
            if not args.resume:
                sequence = args.input.read_text().strip()
                store.create_problem(raw_sequence=sequence, molecule='protein')
                (run / 'input.txt').write_text(sequence + '\n')
                (run / 'launch.json').write_text(json.dumps({
                    'goal': goal, 'input_mode': 'raw_sequence_only',
                    'sequence_length': len(sequence), 'literature_flags': flags,
                    'models': 'repository defaults', 'controller': controller_definition,
                    'annotation_child_roles': ['literature'], 'preloaded_evidence': [],
                    'scripted_model_decisions': False, 'targeted_tests': False,
                    'database_focus': args.database_focus,
                }, indent=2) + '\n')
            result = await run_workflow(store, build_tools(store, config),
                run_dir=run / 'workflow', resume=args.resume, goal=goal,
                episode_binding_factories=(partial(LiteratureEpisodes, **flags),),
                controller_factory=controller,
                binding_definitions={'controller': controller_definition},
                initial_known_record_refs=[store.targets()[0]['source_ref']],
                annotation_child_roles=('literature',))
            (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result), flush=True)

    try:
        asyncio.run(execute())
    except BaseException as error:
        (run / 'failure.json').write_text(json.dumps({'type': type(error).__name__,
            'message': str(error), 'traceback': traceback.format_exc()}, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
