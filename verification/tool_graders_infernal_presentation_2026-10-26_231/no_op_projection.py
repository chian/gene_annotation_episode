"""Test-process-only baseline: disable the four new Infernal projections.

No source files are changed. The normal projection implementation is restored
when this pytest process exits. This reproduces only presentation behavior before
the Infernal fix, preserving current root action ownership and all other code.
"""
from copy import deepcopy
import importlib
import json
from pathlib import Path


MODULES = (
    'gene_annotation_episode.decision_context',
    'gene_annotation_episode.runtime',
    'gene_annotation_episode.providers',
    'gene_annotation_episode.scientific_process_prompt',
)


def pytest_configure(config):
    for name in MODULES:
        module = importlib.import_module(name)
        module.infernal_receiver_context = deepcopy
    directory = Path(config.option.basetemp).parent.parent
    (directory / 'no_op_projection_baseline.json').write_text(json.dumps({
        'kind': 'test_process_only_projection_baseline',
        'overridden_module_globals': [name + '.infernal_receiver_context' for name in MODULES],
        'replacement': 'copy.deepcopy', 'pytest_arguments': config.args,
        'production_files_changed': False,
    }, indent=2, sort_keys=True) + '\n')
