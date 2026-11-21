# A105 scoring design: readers, graders, subscoring sheets and the literature subtree

Written 2026-11-19 from the owner's explanations.
Anything not stated by the owner is marked `[my reading]` and is open for correction. Terms are the owner's.

## 1. What this is for

A105 is the experimental axis. It scores candidate annotations by the experimental evidence published about what a
protein does. Literature is its primary scoring apparatus: the literature subtree finds the experiments in papers and
feeds the graders. The score covers all candidate annotations at once, so evidence is tied to the annotation it
bears on, and the root combines the axes. If a piece of work cannot add to the score, it has no role and is dropped.

## 2. The terms (the owner's definitions)

| Term | Meaning | Granularity |
| --- | --- | --- |
| Reader | Gets values off a kind of display. One display type can show results of many different experiments. | One per display type: bar plot, gel, table, number in text |
| Grader | Judges one kind of experiment: its goodness metrics, controls, measurement technique, noise expectations, replicates needed and certainty. Hand-built, one per experiment. | One per experiment, more granular than "binding assay": SPR, BLI, ITC, FP, FRET, MST, ELISA, EMSA, pull-down, DSF, CETSA, BRET, Y2H and so on |
| Converter | Turns a grader's native result into the components a subscoring sheet takes. | One per grader, hand-built |
| Subscoring sheet | The sheet for one class of what an experiment EVIDENCES. Many varied experiments can evidence the same thing. | One per class of information type |
| Merger | Combines several inputs into one. It sits in TWO places: (1) between the graders and a subscoring sheet, where it combines what all the experiments of a class hand in into that sheet's row; (2) between the subscoring sheets and the main scoring sheet, where it combines the sheets' rows into the axis score. | One at each place; the placement of the first is per sheet |
| Main scoring sheet | A table. Each row is a subscoring sheet. | One per axis |

## 3. The flow, bottom to top

```text
paper -> literature leaves extract (a reader gets the values off each display)
      -> grader            one per experiment found; populated CONTINUOUSLY as the extraction comes in
      ----- everything below happens at the top, over all the graders -----
      -> converter         each grader's native result -> the sheet's components
      -> merger (1)        all experiments of the class -> one row of that class's sheet
      -> subscoring sheet  (the class of information it evidences, e.g. binding)
      -> merger (2)        the subscoring sheets' rows -> the main scoring sheet
      -> main scoring sheet (a table: each row is a subscoring sheet)
      -> the axis score    -> the root, per candidate annotation
```

The literature subtree AUTO-POPULATES the graders as it extracts. Nothing in it calls a tool to do this, and no model
call decides it. It is the filling that extraction does. If a paper reports several experiments, the leaves fill
several graders, one per experiment. The subtree does not know what the graders do with what they receive.

At the top, the converter and the mergers decide what to do with all the graders and how to digest them upstream.

## 4. The literature subtree

```text
literature -> strategy -> search -> page -> leaves
```

The leaves are only: table, report (document order) and lexical chunks.
- `literature` (the top): decides how to look (which search strategies).
- `strategy`: runs the searches of a strategy. `search`: scores hits and picks pages. `page`: measures the page and
  plans which parts to read. The leaves: extract.
- Pure extraction at the bottom. The leaves populate the graders as they extract: continuous filling, one grader per
  experiment found, so a paper with several experiments fills several graders.
- The graders are filled at the bottom. The converter and the mergers work at the top, over all of them.

`[my reading]` how an extracted experiment finds its grader: a controlled experiment-type value that the extraction
returns, with code choosing the grader. Not confirmed.

## 5. Which axes use literature

- A105 (experimental): the primary scoring apparatus.
- A106 and A108 are other experimental axes that collect other types of evidence `[my reading]`.
- The literature subtree is global, not tied to one axis. Each axis that uses it has its own private copy.

## 6. An example: binding

The sheet: binding (the eight current sheet names include `ligand_binding`; not confirmed as the right row).
Experiments that evidence binding, each with its own grader:
label-free biophysical (SPR, BLI, ITC, grating-coupled interferometry); fluorescence (FP/FA, FRET/TR-FRET, MST,
Trp quenching, FCS); plate-based (ELISA-style, AlphaScreen/AlphaLISA, radioligand binding, SPA); separation-based
(pull-down/co-IP, EMSA, SEC/SEC-MALS, equilibrium dialysis, AUC); thermal shift (DSF/nanoDSF, CETSA); cell-based
(BRET/NanoBRET, Y2H, split reporters, PLA, proximity labeling).
Why one grader each: SPR gives kon, koff and KD from a trace with reference-surface controls. ITC gives KD,
stoichiometry and enthalpy and needs much protein. A co-IP is qualitative, from a lysate. A thermal shift shows
binding only indirectly. Each has different goodness metrics, controls, noise and replicate needs, so the same
number from different experiments means different things. Several different experiments agreeing is stronger
because their error sources differ.

## 6b. The activity_rate class (DRAFT, written 2026-11-21, owner to confirm)

The list is a draft for the owner to correct, drafted from the sources found and domain knowledge (no owner-supplied
list). Predicate `catalyzes` (subject the enzyme; not symmetric). One entry per reapplicable protocol. The 19 types stand,
none merged (`redox_mediator` is not folded into `spectro_direct`, `quench_flow` not into `stopped_flow`). The full filled
templates (step 7 below), the sources searched, the class core, the direction and anchors and the class decisions are in
`A105_ACTIVITY_RATE_INVENTORY.md`.

| # | Type id | Experiment | Family |
| --- | --- | --- | --- |
| 1 | `spectro_direct` | Continuous direct spectrophotometric (absorbance) assay | Optical, continuous |
| 2 | `coupled_enzyme` | Continuous coupled (auxiliary-enzyme) assay | Optical, continuous, indirect |
| 3 | `redox_mediator` | Artificial electron donor/acceptor dye assay | Optical, continuous, indirect |
| 4 | `fluorogenic` | Fluorogenic / fluorescent substrate or product assay | Optical, continuous |
| 5 | `luminescent` | Luminescent product-detection assay (luciferase-coupled ATP/ADP etc.) | Optical, plate |
| 6 | `stopped_flow` | Stopped-flow rapid mixing (pre-steady-state, single turnover) | Rapid kinetics, continuous |
| 7 | `quench_flow` | Rapid chemical quench-flow | Rapid kinetics, discontinuous |
| 8 | `chromatographic` | Discontinuous HPLC / LC-MS / GC product (or substrate) quantification | Separation, discontinuous |
| 9 | `stopped_colorimetric` | Stopped assay with colorimetric derivatization | Optical, discontinuous |
| 10 | `radiometric` | Radiolabelled substrate, product separated and counted | Isotope, discontinuous |
| 11 | `separation_band` | Gel / TLC separation of substrate and product with densitometry | Separation, discontinuous |
| 12 | `oxygen_electrode` | O2 consumption/evolution by Clark-type or optical O2 sensor | Electrode, continuous |
| 13 | `ph_stat` | pH-stat titration of released protons | Electrode, continuous |
| 14 | `protein_film_electrochem` | Protein-film voltammetry / chronoamperometry catalytic current | Electrode, continuous |
| 15 | `itc_kinetics` | Isothermal titration calorimetry enzyme kinetics (heat rate) | Calorimetric, continuous |
| 16 | `continuous_ms` | Continuous mass spectrometry (membrane-inlet MS, real-time ESI-MS) | MS, continuous |
| 17 | `nmr_timecourse` | Real-time NMR progress curve | NMR, continuous |
| 18 | `product_immunodetection` | Antibody detection of the modified product (TR-FRET/HTRF, ELISA, AlphaScreen) | Immuno, stopped |
| 19 | `zymogram` | In-gel activity staining (zymography) | Gel, qualitative |

## 7. How to add an experiment (the repeatable procedure; each step is hand-written)

1. Inventory entry: the experiment's name and family; what it evidences (which sheet); its native outputs and units;
   its controls; noise expectations; replicates needed; how certain its result can be; which readers can supply it.
2. The grader for that experiment.
3. Its converter into the sheet's components.
4. Wire it into the first merger, between the graders and the sheet (dependence rules: results sharing a preparation or data are not independent). The second merger, from the subscoring sheets to the main scoring sheet, is per axis.
5. Tests of the grader with real published cases.

Template for step 1:

```text
experiment:            <name>
family:                <technique family>
evidences (sheet):     <class of information type>
native outputs/units:  <...>
controls required:     <...>
noise expectations:    <...>
replicates needed:     <...>
certainty:             <how its result is bounded>
readers that supply it:<display types>
past work (where):     <paper, case record, existing code>
```

## 8. Where things are today (checked this session, from code)

- The current library has eight graders-by-class (activity_rate, endpoint_conversion, product_distribution,
  reaction_coupling, ligand_binding, transport_response, protein_signal, protein_amount). By the owner's labels
  these are the subscoring sheets, not graders. I found no per-experiment graders (no SPR, ITC and so on).
- A105's episodes carry a `reason` action that interprets and grades together in every literature episode, and the
  grader is not auto-populated. That is not the intended design.
- The reader stage that feeds the sheets is not wired in A105's episodes today.
- Figure and plot reading existed in the old A105 and is to be added back later (a detail).

## 9. Open, and where to find the work already done

- The past inventory of experiments (about 150 papers, days per arm, done with Codex): not found yet. The owner wants
  it found, not redone; if anything is redone, use the Codex OAuth. A search is running.
- What each of the two mergers does exactly (rules for combining), and where each lives. The converter is confirmed.
- Whether the eight sheet names are the right rows.
- What A106 and A108 collect and how their sheets are classed.
