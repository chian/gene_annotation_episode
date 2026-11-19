"""A real run of this episode with the real model, through the public runner only, one level above the ordered
reading child (``source_coverage_improvement``).

The entry holds the same real sources as the child's own model-run test (a paper reporting a deposited structure,
its mmCIF coordinates and wwPDB validation report, a methods table of literal witnesses, the proposed annotation).
Every decision is the model's: whether to read, grade or commission a reading child. The run ends through the yield
controller; each child the parent commissioned returned exactly the fields its own ``RETURN_FORM`` admits for the
parent's selection, with the credit its controller stopped on; the parent's credit and finding are what its own code
computes; a resume replays the recorded run without a model process.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config

PACKAGE = __name__.rsplit('.', 2)[0]
PARENT = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
ORDERED = importlib.import_module(PACKAGE + '.source_coverage_improvement.episode').SourceCoverageImprovement
TABLE = importlib.import_module(PACKAGE + '.table_evidence_extraction.episode').TableEvidenceExtraction
PASSAGE = importlib.import_module(PACKAGE + '.passage_evidence_extraction.episode').PassageEvidenceExtraction
ORDERED_FINAL = importlib.import_module(PACKAGE + '.source_coverage_improvement.messages.final_to_parent')
LEAF = importlib.import_module(PACKAGE + '.source_coverage_improvement.tests.test_model_run')
RUN_ID = 'real102_parent'
LEADS = 'literature_source_lead_dispositions'
# A full article: the structural result sits in one section of several, so where and how to read is a choice.
SECTIONS = (
    ('Abstract', 'Glutamate-binding domains recognise small ligands through conserved acidic residues. We report '
     'binding measurements and the X-ray crystal structure of the glutamate-binding domain GBD1 bound to the '
     'ligand LIG (PDB entry 1ABC). The deposited coordinates and the wwPDB validation report were obtained with '
     'this article.'),
    ('Introduction', 'Members of the GBD family are found in bacterial transport systems, where they capture '
     'amino acids and related compounds in the periplasm. Sequence comparisons place GBD1 in a subfamily whose '
     'ligand preferences are poorly characterised. Earlier work proposed that a single acidic side chain near the '
     'N-terminus orients bound ligands, but no structure of a subfamily member with a bound ligand was available. '
     'Here we combine thermal-shift and isothermal titration measurements with a crystal structure.'),
    ('Results: ligand binding in solution', 'Purified GBD1 was stabilised by LIG in thermal-shift assays, with a '
     'melting temperature increase of 6.2 plus or minus 0.4 K at 1 mM ligand (three replicates). Isothermal '
     'titration calorimetry gave an apparent dissociation constant of 12 micromolar. A related compound lacking '
     'the amine group of LIG produced no detectable shift. These measurements characterise the purified domain '
     'under the stated buffer conditions; they do not locate the binding site.'),
    ('Results: crystal structure of the GBD1 complex', 'Crystals of GBD1 grown in the presence of LIG diffracted '
     'to 1.9 angstrom. In the deposited model, the carboxylate oxygens OE1 and OE2 of Glu1 in chain A lie close to '
     'atom N1 of LIG (chain B, residue 2). We propose that this contact holds the ligand. The ligand density is '
     'well defined, and the local fit of Glu1 and of LIG is reported in the validation report. The experimental '
     'details (molecule, construct, expression system, crystallization condition, partner and experiment) are '
     'listed in the methods table that accompanies this article.'),
    ('Discussion', 'The structure suggests that the Glu1 carboxylate positions the ligand amine. Because only one '
     'complex was determined, alternative binding modes in solution cannot be excluded, and the contact geometry '
     'alone does not establish an energetic contribution. Mutational analysis of Glu1 will be required to test '
     'the proposed role.'),
    ('Methods', 'GBD1 residues 1 to 120 were expressed with an N-terminal His6 tag in Escherichia coli BL21(DE3) '
     'and purified by nickel affinity and size-exclusion chromatography. Crystals were grown by vapour diffusion '
     'at pH 7.0; data were collected at 100 K. The structure was solved by molecular replacement and refined; '
     'coordinates and the validation report are deposited under 1ABC.'),
)
ARTICLE = 'Ligand recognition by the glutamate-binding domain GBD1.\n\n' + ''.join(
    f'{title}\n{text}\n\n' for title, text in SECTIONS)


def collaborators(store, directory, cache):
    settings = {**LEAF.SETTINGS, 'tool_registry': {'minimap2_cache_dir': str(cache)}}
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': {episode.binding_path: settings for episode in (PARENT, ORDERED, TABLE, PASSAGE)},
            'services': {}}


def parent_entry(entry):
    """The parent's page assignment over the same page, task, annotation, scope and records."""
    child = entry['assignment']
    return {'assignment': {**child['page'], 'literature_task': child['literature_task'],
                           'proposed_annotation_ref': child['proposed_annotation_ref'], 'scope': child['scope'],
                           'received_record_refs': child['received_record_refs']},
            'message': {'objective': 'examine'}, 'selection': []}


@pytest.mark.model_run
def test_the_model_examines_the_source_commissions_readings_and_the_run_ends_by_its_yield_controller(tmp_path):
    store, entry = LEAF.world(tmp_path, ARTICLE)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry([PARENT(), ORDERED(), TABLE(), PASSAGE()])
    first = asyncio.run(link(registry, PARENT.binding_path, parent_entry(entry), run_id=RUN_ID, journal=journal,
                             collaborators=collaborators(store, tmp_path, tmp_path / 'minimap2')).run())
    result = first['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    episodes = journal.episodes(RUN_ID)
    top = episodes[0]
    units = journal.units(RUN_ID, top['path'])
    print('PARENT_UNITS', json.dumps([
        (unit[2]['kind'], unit[2].get('tool') or unit[2].get('slot'),
         unit[2]['outcome']['status'] if unit[2]['kind'] == 'tool' else unit[2]['result']['credit'],
         (unit[2]['outcome'].get('feedback') or {}).get('code') if unit[2]['kind'] == 'tool' else None)
        for unit in units]))
    for episode in episodes[1:]:
        print('CHILD', json.dumps(episode['binding_path'].rsplit('/', 1)[1]), json.dumps([
            (unit[2]['tool'], unit[2]['outcome']['status'], (unit[2]['outcome'].get('feedback') or {}).get('code'))
            for unit in journal.units(RUN_ID, episode['path'])]))
    assert journal.model_calls(RUN_ID, top['path'])
    # The parent's own return: the required fields, admitted by its own form, with the credit it stopped on.
    assert set(result) == {'credit', 'finding'}
    assert PARENT.return_form.select(()).admit(result, 'return') == result
    assert result['credit'] == top['completion']['credit'] == units[-1][1]['credit']
    # Each ordered reading the parent commissioned, as the parent received it.
    ordered = [unit[2] for unit in units if unit[2]['kind'] == 'child' and unit[2]['slot'] == 'literature_ordered']
    children = [episode for episode in episodes[1:] if episode['binding_path'] == ORDERED.binding_path]
    for outcome, child in zip(ordered, children):
        assert outcome['message']['selection'] == [LEADS]
        assert set(outcome['result']) == set(ORDERED_FINAL.RETURN_FORM.select((LEADS,)).fields)
        assert ORDERED.return_form.select((LEADS,)).admit(outcome['result'], 'return') == outcome['result']
        assert outcome['result']['credit'] == child['completion']['credit']
        assert child['completion']['ended_by'] == 'yield_stop'
        assert outcome['report']['credit'] == outcome['result']['credit']
        assert outcome['report']['structure_sheets'] == outcome['result']['finding']['structure_sheets']
        # The leads cross the boundary as a count and the relevant sources only; the parent counts those sources.
        leads = outcome['result'][LEADS]
        assert leads['relevant_lead_count'] == len(leads['lead_source_refs'])
        assert outcome['report']['lead_source_refs'] == leads['lead_source_refs']
    # The parent's finding lists its own sheets and every sheet its children returned, each once.
    returned = {sheet['sheet_refs'][0] for outcome in ordered for sheet in outcome['result']['finding']['structure_sheets']}
    assert returned <= {sheet['sheet_refs'][0] for sheet in result['finding']['structure_sheets']}
    calls = {json.dumps(episode['path']): journal.model_calls(RUN_ID, episode['path'])
             for episode in episodes}
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators(store, tmp_path / 'resume', tmp_path / 'minimap2')).run())
    assert resumed['result'].as_record() == result
    assert {json.dumps(episode['path']): journal.model_calls(RUN_ID, episode['path']) for episode in episodes} == calls
    assert not list((tmp_path / 'resume' / 'model_calls').glob('call-*'))
    store.close()
    assert ordered, "the model did not commission the ordered reading child"
