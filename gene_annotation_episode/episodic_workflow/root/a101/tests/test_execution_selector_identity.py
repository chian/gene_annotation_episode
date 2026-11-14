"""Descriptor preservation for original native BLAST result selectors."""
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOMES = sorted(str(p.parent.relative_to(ROOT)) for p in ROOT.rglob('episode.py')
    if 'tests' not in p.parts and 'def _masking_selector(' in p.read_text())


@pytest.mark.parametrize('home', HOMES)
def test_native_masking_selector_remains_static_on_private_instance(home):
    cls = importlib.import_module('gene_annotation_episode.episodic_workflow.root.a101.' + home.replace('/', '.') + '.episode').ExecutionEpisode
    binding = object.__new__(cls)
    assert binding._masking_selector({'selector': {'version': 'native_blast_masking_result_selector_v1'}})
    assert not binding._masking_selector({'selector': {'version': 'unrelated'}})
