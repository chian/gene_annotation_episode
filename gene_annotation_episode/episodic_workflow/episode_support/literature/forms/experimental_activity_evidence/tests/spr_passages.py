"""Chunks of text for the SPR extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states many SPR details; ``synthetic_answer``
is the answer that reads it correctly. It contains a multi-byte character ('µ', '°', '×', '²') so that byte offsets
differ from character offsets. ``popz_chunk`` is the real paragraph of Bowman et al., Cell 2008 (PMC2745220) that states
the SPR KD of 20 nM, cut from the owner's primary text of that paper in ``research/``."""
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_extraction import (
    FIT_MODEL, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import UNITS

SYNTHETIC = (
    'Surface plasmon resonance was performed on a Biacore T200 at 25 °C to measure the binding of the protein PopZ to its '
    'partner protein ParB in 20 mM HEPES pH 7.4 with 150 mM NaCl, as shown in Figure 3. The ligand protein ParB (55 kDa) was '
    'amine-coupled to a CM5 chip to a level of 1000 RU; flow cell 1, left blank, served as the reference surface and '
    'all sensorgrams were additionally double referenced against buffer injections. The analyte PopZ (20 kDa; a '
    'monomer in solution) was injected at 2, 6, 20, 60, 200 and 600 nM at 30 µl/min. A 1:1 Langmuir binding model '
    'fitted the data well, with residuals shown in Figure 3D and a chi-squared of 2.0 RU². The baseline noise of the '
    'instrument was 1.5 RU. The fit gave kon = '
    '1.0 × 10^5 M^-1 s^-1 and koff = 2.0 × 10^-3 s^-1, giving KD = 20 nM (standard error 2 nM, n = 3 independent '
    'chips). The KD was obtained from this kinetic fit of the association and dissociation phases. The steady-state fit gave KD = 30 nM. The maximum response was 200 RU for 1:1 binding. Mass-transport '
    'limitation was tested by varying the flow rate and was not observed. The baseline was stable and the surface '
    'was regenerated completely with 10 mM glycine pH 2.0 between cycles. The immobilized ParB was active: it bound '
    'its DNA partner.')

# field -> (value, unit, quote) for the synthetic passage.
SYNTHETIC_STATED = {
    'kd': (20, 'nM', 'KD = 20 nM'),
    'kd_steady_state': (30, 'nM', 'steady-state fit gave KD = 30 nM'),
    'kon': (100000, 'M^-1 s^-1', 'kon = 1.0 × 10^5 M^-1 s^-1'),
    'koff': (0.002, 's^-1', 'koff = 2.0 × 10^-3 s^-1'),
    'rmax': (200, 'RU', 'The maximum response was 200 RU'),
    'kd_spread': (2, 'nM', 'standard error 2 nM'),
    'chi_squared': (2.0, 'RU^2', 'chi-squared of 2.0 RU²'),
    'baseline_noise': (1.5, 'RU', 'baseline noise of the instrument was 1.5 RU'),
    'immobilization_level': (1000, 'RU', 'to a level of 1000 RU'),
    'analyte_mass': (20, 'kDa', 'PopZ (20 kDa'),
    'ligand_mass': (55, 'kDa', 'ParB (55 kDa)'),
    'stoichiometry': (1, 'dimensionless', '1:1 binding'),
    'replicate_count': (3, 'count', 'n = 3 independent chips'),
    SERIES: ([2, 6, 20, 60, 200, 600], 'nM', 'injected at 2, 6, 20, 60, 200 and 600 nM'),
    SPREAD_KIND: ('standard_error', None, 'standard error 2 nM'),
    FIT_MODEL: ('1:1_langmuir', None, 'A 1:1 Langmuir binding model'),
    'reference_surface': ('yes', None, 'flow cell 1, left blank, served as the reference surface'),
    'double_referencing': ('yes', None, 'double referenced against buffer injections'),
    'mass_transport': ('checked_not_limited', None, 'Mass-transport limitation was tested by varying the flow rate and was not observed'),
    'baseline_drift': ('yes', None, 'The baseline was stable'),
    'regeneration': ('yes', None, 'the surface was regenerated completely'),
    'independent_surfaces': ('yes', None, 'n = 3 independent chips'),
    'immobilized_activity': ('yes', None, 'The immobilized ParB was active'),
    'analyte_bivalent_or_oligomeric': ('no', None, 'a monomer in solution'),
    'residuals_reported': ('yes', None, 'residuals shown in Figure 3D'),
    'single_estimate_method': ('no', None, 'The steady-state fit gave KD = 30 nM'),
    'kd_analysis': ('kinetic_fit', None, 'The KD was obtained from this kinetic fit'),
}


# The expected identity of the model run (normalized: casefold, whitespace collapsed). The synthetic passage is about PopZ binding to its partner ParB;
# the real paragraph's SPR assay is about PopZ (the analyte) and ParB (on the chip), 'the interaction between ParB and PopZ'.
SYNTHETIC_TARGET = 'popz'
SYNTHETIC_PARTNER = 'parb'
REAL_EXPECTED_TARGET = 'popz'
REAL_EXPECTED_PARTNER = 'parb'


def answer_from(chunk, stated):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable."""
    answer = {}
    for name in field_names():
        carries_unit = name in UNITS
        if name in stated:
            value, unit, quote = stated[name]
            answer[name] = {'status': 'stated', 'value': value, 'quote': quote, 'support': 'direct', 'reason': None,
                            **({'unit': unit} if carries_unit else {})}
        else:
            answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None,
                            'reason': 'not_stated_in_passage', **({'unit': None} if carries_unit else {})}
    return answer


def synthetic_answer():
    return answer_from(SYNTHETIC, SYNTHETIC_STATED)


PRIMARY = (Path(__file__).resolve().parents[7] / 'research' / 'experimental_scoring_review_2026-10-23' /
           'template_a105_binding_002' / 'popz_2745220_primary.txt')
POPZ_FIRST, POPZ_LAST = 'The direct interaction between PopZ and ParB was demonstrated in vitro', '(not shown).'


def popz_chunk():
    """The Results paragraph of PMC2745220 that states the SPR KD of 20 nM: ``(text, byte offset in the paper's
    text)``."""
    text = PRIMARY.read_text(encoding='utf-8')
    start = text.index(POPZ_FIRST)
    end = text.index(POPZ_LAST, start) + len(POPZ_LAST)
    return text[start:end], len(text[:start].encode('utf-8'))


def popz_answer(chunk):
    return answer_from(chunk, {'kd': (20, 'nM', 'the equilibrium dissociation constant for the interaction between ParB and PopZ to be 20 nanomolar')})
