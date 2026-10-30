# Independent parent review and numerical-sheet correction

The adopted goal remains GOAL_VERBATIM.txt, with ten axes exactly A101–A108,A110,
A111. No target correspondence, combined credit or additional axis is introduced.

## Actual source coverage and reset

Parent read all440 lines of primary_iscr2013/article_clean.txt, the retained BioC
article projection, in consecutive untruncated portions1–70,71–140,141–220,
221–330,331–440. An initial1–140 attempt was truncated and was replaced. Parent
viewed the original600×221 Table3 JPEG, then read all107 lines of the source
worker's SOURCE_AND_COMPONENTS_001.md. Article HTML/BioC/image original bytes are
retained in that packet; this is not a new acquisition or raw instrument dataset.
PDF/supplement challenge responses are not treated as papers or scientific data.

After that review, before this numerical interpretation, parent reread the full
applicable authority set: root AGENTS.md, GOAL.md, EPISODE_STRUCTURE.md,
TIME_AWARE_ESTIMATION.md, TOOL_KNOWLEDGE.md, TASK_AND_STEERING.md, both specified
TASK_AND_STEERING and EVIDENCE_AXIS_REVIEW amendments, VERBATIM_DIRECTION.md,
complete VERBATIM_RECOVERY_002.md, complete EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS
amendment, scoring_sheet_numeric_review_002.md, research review AGENTS.md and
SOURCE_CORRECTIONS.md. Parent also reread the complete696-line current A105 sheet
in portions1–230,231–460,461–720 and NATIVE_INTERFACES001/002 plus
ASSAY_GRAPH_INTERFACES001/002. The full adopted goal was read last, followed by
the latest actual user direction in this conversation: literature supports A105
reference evidence, not A101 alignment, with integration deferred. Historical
sheet transfer/candidate formulas remain preserved and excluded from this build.

## Experiment and necessary correction

E. coli IscR competition uses apo preparations; wild-type and E43A are separate
protein preparations/assays. Labeled wild-type hya and unlabeled competitor DNA
coexist within each competition reaction. Do not confuse ligand coexistence with
a WT/mutant protein mixture. Structural 3CA, 6xHis and1–133 details do not establish
binding-construct identity. Binding construct boundaries/tag status stay unknown.

Competition Methods supplies5nM labeled hya,8–1000nM competitor,22nM WT or20nM
E43A protein;250mM KCl,40mM Tris-Cl pH7.9,5% glycerol,10µM DTT, anaerobic. Source
defines normalized anisotropy (A−Afree)/(Abound−Afree) and four-parameter logistic
IC50. The separate increasing-protein direct binding uses150mM KCl and a Hill
fit; it cannot silently supply Kd for this competition experiment.

Current A105 sheet section8's32nM point omits the table's ±2. Corrected retained
source value is32±2, with footnote SD from fitting an averaged titration curve
on at least three occasions. Exact n, batch/preparation independence, individual
curves and the relevant joint sampling model/covariance are absent. The spread
is available; its conversion into known sampling variance/SEM is not established.
The source's >510 threshold mechanism is not specified by the inspected text.
Do not substitute1000, infer no binding, or claim a confidence bound.

## Numerical conversion and scientific bearing

Fields and formulas printed in chat before coding:32±2 gives relative reported
fit spread2/32=.0625; the WT mutant/self competitor calculation gives reported-
limit/reported-point ratio>510/32=>15.9375 and log contrast>2.768674822919.
For E43A the corresponding17/11=1.545454545455 and log=.435318071258 are descriptive
points. Ratio and log reuse exactly the same operands and are not added as
independent evidence. These components describe competition discrimination under
the supplied assay; they do not establish transcription, catalytic turnover or
intrinsic equilibrium affinity. The printed denominator is itself estimated;
threshold arithmetic is not a lower bound on a true population parameter.

Comparability and isolation remain separate. Intended competitor nucleotide
change is not a penalty. Protein amount22vs20nM qualifies any across-protein
comparison;22/20=1.1 is not a quality multiplier or calibrated IC50 correction.
Purified protein/no-protein/no-competitor/self/shuffled controls address specified
alternatives without proving zero contamination, fully active preparation or
absence of optical/folding/oligomerization effects. Structure and direct binding
are complementary endpoints, not extra independent titration replicates.

For a supported future joint log-parameter model, e=log(test)−log(reference) and
Ve=Vlog(test)+Vlog(reference)−2Cov(log(test),log(reference)). Across-protein contrast
subtracts those e values, retaining all shared covariance. This first implementation
adds finite descriptive point/limit calculations; source likelihood/index remains
explicitly unimplemented. Missing scientific inputs and unimplemented functions
are reported separately. A105 and the full literature goal remain unfinished.

No permanent sheet, historical source record, original case or live pin was edited.
New BINDING_PARAMETER_INTERFACES001/002 define the additive paired field/cell path
and fresh disjoint coding ownership. Other appropriate literature responsibilities
A106/A111/A108/A110/partner experiments remain in the adopted goal.
