"""Each axis's tool-knowledge, launch and execution library reads its own folder.

A library index and every section it lists live in one folder; freezing copies
exactly those bytes. Real files, real readers; no model, network or HPC.
"""
from importlib import import_module
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LIBRARY_ROOT, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

SUPPORT = Path(import_module('gene_annotation_episode.episodic_workflow.episode_support').__file__).parent
KNOWLEDGE = SUPPORT / 'knowledge'

# Axis role -> its tool-knowledge folder (A106/A108 share the byte-identical one).
KNOWLEDGE_FOLDERS = {
    'sequence_homology_evidence': KNOWLEDGE / 'sequence_homology_evidence',
    'structural_homology_evidence': KNOWLEDGE / 'structural_homology_evidence',
    'gene_context_evidence': KNOWLEDGE / 'gene_context_evidence',
    'evolutionary_history_evidence': KNOWLEDGE / 'evolutionary_history_evidence',
    'perturbation_evidence': KNOWLEDGE,
    'partner_presence_evidence': KNOWLEDGE / 'partner_presence_evidence',
    'sample_context_evidence': KNOWLEDGE,
    'biochemical_feasibility_evidence': KNOWLEDGE / 'biochemical_feasibility_evidence',
}
# Axis role -> its launch folder (A102/A110 share the byte-identical one).
LAUNCH_FOLDERS = {
    'sequence_homology_evidence': LIBRARY_ROOT / 'sequence_homology_evidence',
    'structural_homology_evidence': LIBRARY_ROOT,
    'gene_context_evidence': LIBRARY_ROOT / 'gene_context_evidence',
    'evolutionary_history_evidence': LIBRARY_ROOT / 'evolutionary_history_evidence',
    'perturbation_evidence': LIBRARY_ROOT / 'perturbation_evidence',
    'partner_presence_evidence': LIBRARY_ROOT / 'partner_presence_evidence',
    'biochemical_feasibility_evidence': LIBRARY_ROOT,
}


def _listed(folder):
    index = json.loads((folder / 'index.json').read_text())
    return [section for entry in index['entries'] for section in entry['sections']]


def _folder_holds_exactly_its_sections(folder):
    listed = {section['path'] for section in _listed(folder)}
    assert listed == {path.name for path in folder.glob('*.md')}


@pytest.mark.parametrize('role', sorted(KNOWLEDGE_FOLDERS))
def test_tool_knowledge_freezes_every_section_from_its_own_folder(tmp_path, role):
    folder = KNOWLEDGE_FOLDERS[role]
    _folder_holds_exactly_its_sections(folder)
    library = ToolKnowledge.freeze(tmp_path / 'saved', source=folder)
    index = json.loads((folder / 'index.json').read_text())
    for raw, saved in zip(index['entries'], library.manifest['entries'], strict=True):
        for original, frozen in zip(raw['sections'], saved['sections'], strict=True):
            assert (library.directory / frozen['path']).read_bytes() == (folder / original['path']).read_bytes()


@pytest.mark.parametrize('role', sorted(LAUNCH_FOLDERS))
def test_launch_instructions_freeze_every_section_from_their_own_folder(tmp_path, role):
    folder = LAUNCH_FOLDERS[role]
    _folder_holds_exactly_its_sections(folder)
    library = LaunchInstructions.freeze(tmp_path / 'saved', source=folder)
    index = json.loads((folder / 'index.json').read_text())
    saved = json.loads((library.directory / 'index.json').read_text())
    for raw, frozen_entry in zip(index['entries'], saved['entries'], strict=True):
        for original, frozen in zip(raw['sections'], frozen_entry['sections'], strict=True):
            assert (library.directory / frozen['path']).read_bytes() == (folder / original['path']).read_bytes()


EXECUTION = SUPPORT / 'instructions' / 'execution'
GUIDANCE = 'gene_annotation_episode.episodic_workflow.episode_support.instructions.'


@pytest.mark.parametrize('module, folder', [
    ('execution_guidance', EXECUTION),
    ('sequence_homology_evidence.execution_guidance', EXECUTION),
    ('gene_context_evidence.execution_guidance', EXECUTION),
    ('evolutionary_history_evidence.execution_guidance', EXECUTION),
    ('perturbation_evidence.execution_guidance', EXECUTION),
    ('partner_presence_evidence.execution_guidance', EXECUTION / 'partner_presence_evidence'),
])
@pytest.mark.parametrize('resource', ['api', 'local', 'hpc'])
def test_execution_recipe_reads_its_own_folder(module, folder, resource):
    guidance = import_module(GUIDANCE + module)
    assert guidance.ROOT == folder
    text = guidance.recipe('blastp', resource)
    assert (folder / 'planning.md').read_text().strip() in text
    assert (folder / (resource + '.md')).read_text().strip() in text
