"""First merger, for the ligand_binding (binding) subscoring sheet.

Takes one OR MORE converted experiment results (convert_spr, convert_itc, convert_bli, convert_gci, convert_fp, convert_fret, convert_mst, convert_trp, convert_fcs, convert_elisa, convert_alpha, convert_radioligand, convert_spa, convert_pulldown, convert_emsa, convert_sec, convert_dialysis or convert_auc
output; later converters for other binding experiments hand in the same
shape) and produces ONE row of the binding sheet. Results of different
experiment types for the same binding statement are pooled by the same rules;
the row reports which experiment types contributed ('experiment_types', and
'group_experiment_types' for each dependence group). Deterministic; no model call, no store access
(the episode saves the row through its scoped store).

Dependence rule (shared preparation or data are not independent)
---------------------------------------------------------------
Each converted result carries four dependence keys: analyte_preparation_ref,
immobilized_preparation_ref, surface_ref, dataset_ref (a string, or None when
the source does not say). Two results are DEPENDENT when
  (a) they share a known value in any of the four keys (same protein
      preparation, same sensor surface, same data reused), or
  (b) either result has an unknown analyte_preparation_ref or unknown
      immobilized_preparation_ref. Independence cannot be shown, so it is
      not assumed, or
  (c) a known preparation of one (analyte or immobilized/cell partner) is
      a known preparation of the other, in either role: an SPR analyte that
      is the ITC syringe protein, or an SPR analyte that is the ITC cell
      protein, is one preparation, so the two are not independent.
ITC results give their syringe preparation as the analyte key and their cell
preparation as the immobilized key; they have no surface (None). BLI results give
their analyte, their loaded partner and their sensor (as the surface key); two BLI
experiments on one sensor, or a BLI analyte that is an SPR or ITC protein, are
dependent by the rules above. GCI results give their analyte, their immobilized
partner and their chip (as the surface key): two GCI experiments on channels of
one chip share the chip and are dependent; a GCI analyte that is an SPR, ITC or
BLI protein is one preparation by (c). FP results give their titrant as the analyte key and their labelled tracer partner
as the other preparation; they have no surface (None); an FP titrant that is an SPR, ITC, BLI or GCI protein is one
preparation by (c). FRET results give their titrant as the analyte key and the labelled partner they hold fixed as the
other preparation; they have no surface (None); a FRET titrant or fixed partner that is an SPR, ITC, BLI, GCI or FP
protein is one preparation by (c). MST results give their titrant as the analyte key and the detected (labelled or label-free) partner they hold fixed
as the other preparation; they have no surface (None); an MST titrant or fixed partner that is an SPR, ITC, BLI, GCI, FP or FRET
protein is one preparation by (c). Intrinsic fluorescence quenching (Trp) results give their ligand (the titrant) as the analyte key and the protein whose fluorescence
is read, held at a constant concentration, as the other preparation; they have no surface (None); a Trp ligand or protein that is an SPR, ITC, BLI, GCI, FP, FRET or
MST protein is one preparation by (c). FCS results give their titrant as the analyte key and the fluorescently labelled partner
they hold at a low constant concentration as the other preparation; they have no surface (None); an FCS titrant or labelled
partner that is an SPR, ITC, BLI, GCI, FP, FRET, MST or Trp protein is one preparation by (c).
ELISA results give their titrant as the analyte key and the coated partner as the other preparation (no surface), and AlphaScreen
results give their titrant as the analyte key and the partner they hold at a constant concentration as the other preparation (no
surface, the plate is not one); an ELISA or AlphaScreen partner that is a protein of any other type is one preparation by (c).
Radioligand binding results give their radioligand as the analyte key and the receptor preparation (membranes, purified protein or
cells) as the other preparation (no surface: a filter or a well is not one); a radioligand or receptor preparation that is a protein of
any other type is one preparation by (c).
Scintillation proximity assay (SPA) results give their radioligand as the analyte key and the captured target (membranes, purified
protein or cells held on the beads) as the other preparation (no surface: a bead or a well is not one); an SPA radioligand or captured
target that is a protein of any other type is one preparation by (c).
Pull-down and co-immunoprecipitation (pulldown) results give their prey as the analyte key and their bait (held on the beads) as the other
preparation (no surface: a bead is not one); a prey or bait that is a protein of any other type is one preparation by (c).
Electrophoretic mobility shift assay (EMSA) results give their protein (the titrant or the added protein) as the analyte key and their labelled probe as the
other preparation (no surface: a gel is not one); an EMSA protein or probe that is a protein or preparation of any other type is one preparation by (c).
Size-exclusion chromatography (SEC / SEC-MALS) results give their first component as the analyte key and their second component as the other preparation (no surface:
a column is not one); an SEC component that is a protein or preparation of any other type is one preparation by (c).
Equilibrium dialysis / ultrafiltration (dialysis) results give their ligand as the analyte key and their protein as the other preparation (no surface: a membrane or a device is not
one); a dialysis ligand or protein that is a protein or preparation of any other type is one preparation by (c).
Analytical ultracentrifugation (AUC) results give their first component as the analyte key and their second component as the other preparation (no surface: a cell or a rotor is not
one); an AUC component that is a protein or preparation of any other type is one preparation by (c).
BRET / NanoBRET results give their donor-fused protein as the analyte key and their acceptor-fused protein (or tracer target) as the other preparation (no surface: a cell is not one); a BRET partner that is a protein or preparation of any other type is one preparation by (c). An apparent KD, else a Ki, from a tracer titration or displacement (measurement keys bret_kd, bret_ki: apparent, in live cells) is pooled like any other constant; a BRET with neither (a BRET ratio, a saturation curve, a BRET50 in acceptor-to-donor ratio) is a qualitative result, with 'qualitative_effect' {'statement', 'support_refs', 'signal_over_control'}; the merger reads only 'statement' and 'support_refs'; no merger code changes.
Cellular thermal shift assay (CETSA) results give their compound as the analyte key and their target protein as the other preparation (no surface: a cell or a tube is not one); a CETSA compound or
target that is a protein or preparation of any other type is one preparation by (c). A CETSA with an EC50 of an isothermal dose-response is a quantitative result whose effect is an APPARENT engagement constant derived from the thermal shift (measurement key
'cetsa_apparent_kd', not a dissociation constant); one with no EC50 is a qualitative result ('qualitative_effect' with 'statement' and 'support_refs'); the merger's code and contract are unchanged.
Proximity ligation assay (PLA: in situ PLA, Duolink) results give their first protein as the analyte key and their second protein as the other preparation (no surface: a cell or a tissue
section is not one); a PLA protein that is a protein or preparation of any other type is one preparation by (c). A PLA reports puncta per cell and no binding constant, so it is always a
qualitative result (below), with 'puncta_fold_over_control' in its qualitative effect in place of a constant; the merger code is unchanged.
Split-reporter (protein-fragment complementation: NanoBiT, split GFP / BiFC, split beta-lactamase, split TEV) results give their first fusion partner as the analyte key and their second as the other preparation (no surface: a cell or a lysate is not
one); a split-reporter partner that is a protein or preparation of any other type is one preparation by (c). Their apparent KD (measurement key split_reporter_kd) is pooled like any other constant; one with no KD is qualitative (the merger reads only 'statement' and 'support_refs'); no merger code changes.
Yeast two-hybrid (Y2H) results give their prey as the analyte key and their bait as the other preparation (no surface: a yeast cell is not one); a Y2H prey or bait that is a protein of any other type is one preparation by (c).
A Y2H reports no binding constant (growth or a beta-galactosidase activity in Miller units is not a KD): it is always a qualitative result, with 'qualitative_effect' {'statement', 'support_refs', 'reporter_fold'}; the merger reads only 'statement' and 'support_refs'.
Thermal shift (DSF / nanoDSF) results give their protein as the analyte key and their ligand as the other preparation (no surface: a plate is not one); a DSF protein or ligand that is a protein or
preparation of any other type is one preparation by (c). A DSF apparent KD (from the shifts of the Tm, measurement key dsf_kd) is pooled like any other constant; a DSF with no KD is qualitative (statement and support_refs; its 'thermal_shift_c' is not read).
Proximity labeling (BioID, TurboID, miniTurbo, APEX, APEX2 and split versions; 'proximity') results give their bait as the analyte key and their candidate partner as the other preparation (no surface: a cell is not one); a proximity bait or
candidate that is a protein or preparation of any other type is one preparation by (c). A proximity-labeling experiment reports no binding constant (an enrichment is not a KD): it is always a qualitative result, with 'qualitative_effect' {'statement', 'support_refs', 'fold_enrichment'};
its 'interaction_detected' means PROXIMITY (within about 10 to 20 nm in living cells), not direct binding; the merger reads only 'statement' and 'support_refs' and its code and contract are unchanged.
Dependence is transitive: groups are the connected components. Experiments in
one group are one independent unit; the row counts groups, not experiments.

Qualitative results (a pull-down or co-IP, or an EMSA, an SEC / SEC-MALS, a dialysis or an AUC that reports no apparent KD)
-----------------------------------------------------------------------------------
An EMSA, an SEC or a dialysis with a KD (a dialysis also with a Ki) is a quantitative result (its effect is pooled like any other constant, and it carries no 'qualitative_effect'); one with no
KD is a qualitative one (a dialysis with only a percent bound or a percent unbound), handled as below with no change of this contract (the merger reads only 'statement' and 'support_refs' of the qualitative effect).
A converted result may carry 'qualitative_effect' ({'statement', 'support_refs', 'fold_enrichment'}) instead of an effect: the experiment reports no binding
constant, so its sheet has no measured_effect and nothing of it can be pooled on the nM scale. Such a result is NOT excluded and does not enter the
pooling, the effect, the variance or the 'counts' above (those stay those of the experiments with a constant). It does contribute (1) its sheet
interpretations to the row interpretations, under the same rule as every other experiment, and (2) the row's 'qualitative' block: its experiment
refs and types, its statement (interaction_detected / interaction_not_detected / interaction_not_stated) with the spans that state it, and its own
dependence groups among the qualitative results ('independent_groups'). A row with only qualitative results has unavailable effect cells
('no_experiment_with_a_measured_effect') and still reports its interpretations and its qualitative block.

Pooling rule
------------
Only results whose sheet has a populated measured_effect take part; the
others are listed under 'excluded' with their reason.
* Inside a group (fully dependent: they share systematic error) the group's
  effect is the mean of its members' effects. If every member has a
  variance, the group's variance is (mean of the members' standard
  deviations)^2, the exact variance of that mean when the members are
  perfectly correlated; adding members never lowers it. A member without a
  variance makes the group's variance unavailable.
* Across groups (independent) the row's effect is the inverse-variance
  weighted mean and its variance is 1 / sum of the weights, when every
  group has a variance. If any group has none, the row's effect is the plain
  mean of the group effects (status 'conditional'), and variance and
  precision are unavailable with the reason; a missing variance is never 0.
Pooling is on the native nM scale of the sheet's binding_parameter.

Row interpretations: for each sheet criterion, 'conflicting' if any pooled
experiment is conflicting, 'supported' if all pooled experiments are
supported, otherwise 'unknown'. A criterion an experiment did not select
counts as unknown for it.

Degrees: an interpretation of a result may carry a degree (a number from 0 to 1, how far its status holds). The row carries them in 'interpretation_degrees'
({criterion: {experiment_ref: degree}}), one entry per contributing result that gave one, and does not combine them: an average or a minimum would hide a
result (a 0.2 next to a 1.0), and which result a degree belongs to stays visible. The row's status of the criterion is the rule above and ignores the degree, and
the pooled effect, variance and precision are not touched by it.

The row also reports counts (experiments, independent groups) and, for the
sheet components this merger does not fill, the reasons they stay
unavailable.
"""
import math

VERSION = 'a105_binding_row_v1'
SHEET = 'ligand_binding'
DEPENDENCE_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref')
POOLED = ('measured_effect', 'effect_variance', 'effect_precision')


def dependent(first, second):
    """True when two converted results cannot be counted as independent."""
    a, b = first['dependence'], second['dependence']
    if any(a[k] is None or b[k] is None for k in PREPARATION_KEYS):
        return True
    if any(a[k] is not None and a[k] == b[k] for k in DEPENDENCE_KEYS):
        return True
    # one preparation used in different roles (the analyte of one experiment
    # is the immobilized or cell partner of the other) is still one preparation
    return bool({a[k] for k in PREPARATION_KEYS} & {b[k] for k in PREPARATION_KEYS})


def dependence_groups(results):
    """Connected components of the dependence relation, in input order."""
    parent = list(range(len(results)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            if dependent(results[i], results[j]):
                parent[find(j)] = find(i)
    groups = {}
    for i, result in enumerate(results):
        groups.setdefault(find(i), []).append(result)
    return list(groups.values())


def _group_effect(group):
    effects = [r['sheet']['cells']['measured_effect']['value'] for r in group]
    variances = [r['sheet']['cells']['effect_variance']['value'] for r in group]
    effect = sum(effects) / len(effects)
    if any(v is None for v in variances):
        return effect, None
    return effect, (sum(math.sqrt(v) for v in variances) / len(variances)) ** 2


def _cell(name, value, unit, status, reasons, refs):
    return {'component': name, 'value': value, 'unit': unit, 'status': status, 'reasons': reasons, 'source_refs': refs}


def merge_binding(results):
    """Merge converted results of the binding class into one row."""
    qualitative = [r for r in results if r.get('qualitative_effect') is not None]
    excluded = {r['experiment_ref']: r['sheet']['cells']['measured_effect']['reasons'] for r in results if r['sheet']['cells']['measured_effect']['value'] is None and r.get('qualitative_effect') is None}
    pooled = [r for r in results if r['sheet']['cells']['measured_effect']['value'] is not None]
    groups = dependence_groups(pooled)
    effects = [_group_effect(g) for g in groups]
    refs = list(dict.fromkeys(ref for r in pooled for ref in r['sheet']['cells']['measured_effect']['source_refs']))
    unit = 'nM'
    if not groups:
        cells = {name: _cell(name, None, unit, 'unavailable', ['no_experiment_with_a_measured_effect'], []) for name in POOLED}
    else:
        if all(variance is not None and variance > 0 for _, variance in effects):
            weights = [1 / variance for _, variance in effects]
            effect = sum(w * e for w, (e, _) in zip(weights, effects)) / sum(weights)
            variance = 1 / sum(weights)
            cells = {'measured_effect': _cell('measured_effect', effect, unit, 'populated', [], refs), 'effect_variance': _cell('effect_variance', variance, 'nM_squared', 'populated', [], refs), 'effect_precision': _cell('effect_precision', 1 / variance, '1/(nM_squared)', 'populated', [], refs)}
        else:
            effect = sum(e for e, _ in effects) / len(effects)
            reason = ['variance_unavailable_for_at_least_one_independent_group']
            cells = {'measured_effect': _cell('measured_effect', effect, unit, 'conditional', reason, refs), 'effect_variance': _cell('effect_variance', None, 'nM_squared', 'unavailable', reason, []), 'effect_precision': _cell('effect_precision', None, '1/(nM_squared)', 'unavailable', reason, [])}
    contributing = [*pooled, *qualitative]
    criteria = sorted({c for r in contributing for c in r['extraction']['interpretations']})
    interpretations = {}
    for criterion in criteria:
        statuses = [r['extraction']['interpretations'].get(criterion, {'status': 'unknown'})['status'] for r in contributing]
        interpretations[criterion] = 'conflicting' if 'conflicting' in statuses else 'supported' if all(s == 'supported' for s in statuses) else 'unknown'
    degrees = {}
    for r in contributing:
        for criterion, interpretation in r['extraction']['interpretations'].items():
            if 'degree' in interpretation:
                degrees.setdefault(criterion, {})[r['experiment_ref']] = interpretation['degree']
    unfilled = {}
    for r in pooled:
        for component, cell in r['sheet']['cells'].items():
            if component not in POOLED:
                unfilled.setdefault(component, [])
                unfilled[component] = list(dict.fromkeys([*unfilled[component], *cell['reasons']]))
    qualitative_groups = dependence_groups(qualitative)
    qualitative_block = {'experiment_refs': [r['experiment_ref'] for r in qualitative], 'experiment_types': sorted({r['experiment_type'] for r in qualitative}), 'statements': {r['experiment_ref']: r['qualitative_effect']['statement'] for r in qualitative}, 'support_refs': {r['experiment_ref']: r['qualitative_effect']['support_refs'] for r in qualitative}, 'dependence_groups': [[r['experiment_ref'] for r in g] for g in qualitative_groups], 'independent_groups': len(qualitative_groups)}
    return {'version': VERSION, 'sheet': SHEET, 'experiment_refs': [r['experiment_ref'] for r in results], 'experiment_types': sorted({r['experiment_type'] for r in pooled}), 'group_experiment_types': [sorted({r['experiment_type'] for r in g}) for g in groups], 'dependence_groups': [[r['experiment_ref'] for r in g] for g in groups], 'counts': {'experiments': len(results), 'independent_groups': len(groups)}, 'excluded': excluded, 'cells': cells, 'interpretations': interpretations, 'interpretation_degrees': degrees, 'qualitative': qualitative_block, 'unfilled_components': unfilled}
