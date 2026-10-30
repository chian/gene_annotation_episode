# Published inputs to the existing A104 sheet

2026-10-24. Additive, bounded research conversion. This applies proposal004 and
its exact reader fields from `../a104_clade_support_completion_025/`; it changes
neither. It supplies conditional numerical **function-coverage cells**, not a
complete measured A104 result, production reader, or annotation of ybhP.

The existing Song et al. TyrA example is sufficient for a narrow published
contrast. No additional paper or native phylogenetic analysis was needed.
The important conversion is from specific source assignments and a declared
reference inventory to `n`, `k_f`, `B_f`, and `C_f`. Source ratios do not enter
the sheet merely because they are numerical.

## 1. Evidence and fixed comparison scopes

Source: Song et al. (2005), *The TyrA family of aromatic-pathway dehydrogenases
in phylogenetic context*, [BMC Biology 3:13](https://pmc.ncbi.nlm.nih.gov/articles/PMC1173090/),
[DOI 10.1186/1741-7007-3-13](https://doi.org/10.1186/1741-7007-3-13).
Figure 2 is a tree of selected trimmed TyrA catalytic-core domains. It is not
a census of all natural members. Tables 2 and S1 map its organism labels.

The source explicitly describes an Acinetobacter branch and its sister
Pseudomonas/Azotobacter subgroup within the lineage with a shared TyrA–AroF
fusion. This supplies the biological reason for the two **separate** scopes:

| Fixed scope | Complete intended displayed reference inventory | n | Boundary/source basis |
|---|---|---:|---|
| P5: displayed Pseudomonas/Azotobacter subgroup | Paer, Pstu, Pflu, Pput, Avin | 5 | Figure 2 subgroup; Results, pyridine-nucleotide specificity subsection |
| PA6: displayed fusion-bearing subgroup including its Acinetobacter sister | Paer, Pstu, Pflu, Pput, Avin, ACIN | 6 | Same figure and explicit sister-group/fusion relationship in that Results subsection |

The named subgroups and their displayed membership, rather than an invented
internal branching order, define these inventories. The tree is radial; no
root is assigned here. The reference boundary is the source-defined split side,
with the remaining displayed tree on the external side. These inventories are
complete **for the declared displayed comparison**, not for the biological
family. Members absent from the publication are a generalization limit and do
not become an invented denominator. The broader PA6 scope is not substituted
for P5, nor is P5 selected afterward to hide PA6 heterogeneity.

All listed members are references. No query has been supplied or placed in
this exercise. If a listed member is later used as the query, it must be
excluded from the reference count and the sheet recomputed. For example,
using uncharacterized Pflu as query changes the P5 reference denominator to4;
the same two mapped assignments would then give2/4, not2/5. That is a different
input instance, not a newly measured result.

## 2. Exact molecule and function mapping

The canonical input is one row per source-designated molecule/copy, retaining
its source-tip mapping and any unresolved external identifier. Identifiers
below are historical source identifiers, not freshly validated current records.

Define the comparison dimension as the **joint cofactor/substrate profile**:

* `f`: accepts PPA and AGN, with NAD+-specific cofactor use.
* `g`: accepts PPA and AGN, with NADP+-specific cofactor use.
* `h`: accepts PPA and AGN, without a cofactor-specific assertion.

Both `f` and `g` entail `h`. Here accepting two substrates is one measured
profile, not two conflicting annotations. The broad assertion does not claim
exclusive acceptance of those two substrates. Unexamined additional activities
remain unknown. Cofactor specificity is author-reported; assay detection limits
and quantitative selectivity uncertainty were not supplied by the inspected
summary table.

| Exact source row → proposed canonical input | Identity input retained | Actual function evidence → assignment |
|---|---|---|
| Figure Paer / Table S1 Paer_1 → `Song2005:Paer:TyrA_core` | GI15598360; Table2 P. aeruginosa PAO1; exact original assay-to-tip identity unresolved | Table4 P. aeruginosa: NAD+, PPA/AGN; `S={f}` **if mapping a holds** |
| Figure Pstu → `Song2005:Pstu:TyrA_core` | GI5712093; P. stutzeri; exact original assay-to-tip identity unresolved | Table4 P. stutzeri: NAD+, PPA/AGN; `S={f}` **if mapping b holds** |
| Figure Pflu → `Song2005:Pflu:TyrA_core` | GI23061127; P. fluorescens PfO-1 | No individually checked experimental assignment; `S={}` |
| Figure Pput → `Song2005:Pput:TyrA_core` | GI26988501; P. putida KT2440 | No individually checked experimental assignment; `S={}` |
| Figure Avin → `Song2005:Avin:TyrA_core` | TableS1 displays GI53612601 but links to GI13105295; one unresolved slot | No individually checked experimental assignment; `S={}` |
| Figure ACIN → `Song2005:ACIN:TyrA_core` | GI50085330; Table2 Acinetobacter sp. ADP1; exact original assay-to-tip identity unresolved | Results specificity subsection reports NADP specificity and shared cyclohexadienyl-substrate profile; `S={g}` **if mapping c holds** |

The source's colored lineage labels are not counted as experiments on every
member. `S={}` means no assignment established in this inspected material at
this resolution; it does not mean no activity. The Avin discrepancy does not
make two molecules, remove a member, or alter `n=5/6`. Neither conflicting
identifier is silently chosen. Exact sequence/branch association remains
unresolved regardless of this count invariance.

`a`, `b`, and `c` are **shared identity/assignment scenarios**, not probabilities,
weights, or experimental-confidence grades. Value1 means the reported assay
assignment maps to that designated source tip/core; value0 means that connection
is unavailable in that scenario and its function does not populate that tip.
Zero does not assert that the tip lacks the function. The same scenario is used
in P5, PA6, both function resolutions, and every downstream requirement.

The author-mapped example uses `a=b=c=1`. This is an explicit conditional
illustration accepting the source's assignments. The strict canonical point
remains null while the original assay-to-sequence correspondence is unresolved.
No new requirement to remeasure proteins or search for contrary functions is
introduced: this is the actual missing connection in these retained records.

## 3. Filled numerical cells and checked arithmetic

These are the existing proposal's cells. `C_f=0` when a received other class
occurs in the fixed clade; otherwise `C_f=k_f/n`. Counts are unique reference
molecules, not papers, preparations, bootstrap replicates, or probability mass.

| Published comparison → assertion | Exact operands under author mapping | Existing calculated cell | Meaning |
|---|---|---:|---|
| P5 → `f` | n=5; k_f=2; known-other count=0; unresolved members=3; B_f=false | **C_f=2/5=0.4** | Observed coverage of the reported conserved profile in this displayed subgroup |
| PA6 → `f` | n=6; k_f=2; known-other count=1 (ACIN:g); unresolved members=3; B_f=true | **C_f=0** | The fixed broader group does not conserve the narrower cofactor profile |
| PA6 → broader `h` | n=6; k_h=3 via f→h and g→h; known-other count=0 at this resolution; unresolved members=3; B_h=false | **C_h=3/6=0.5** | Coverage of the separately stated shared two-substrate activity |

The third row does not restore the second row's exact NAD-specific claim. These
are dependent, entailed assertions and must not be added as independent support.
The value0.5 follows from3/6; it is not a midpoint assigned to uncertainty.

The exact mapping-scenario expressions are:

```text
P5, f:    n=5; k_f=a+b; B_f=false; C_f=(a+b)/5.
PA6, f:   n=6; k_f=a+b; B_f=(c=1);
          C_f=0 if c=1, else (a+b)/6.
PA6, h:   n=6; k_h=a+b+c; B_h=false; C_h=(a+b+c)/6.
```

For `a,b,c∈{0,1}`, the finite mapping-only possibilities are:

| Cell | Possible values | Identification envelope | Point without resolved mappings |
|---|---|---|---|
| P5 C_f | 0, 1/5, 2/5 | [0,0.4] | null |
| PA6 C_f | 0, 1/6, 2/6 | [0,1/3] | null; exactly0 if c=1 |
| PA6 C_h | 0, 1/6, 2/6, 3/6 | [0,0.5] | null |

These are **mapping-only** bounds on the currently received observations.
They do not complete unassayed members, establish a correct Avin accession,
or bound all future evidence. Each Avin alternative has the same count because
it occupies the same single slot and has no received experimental assignment.
Adding unreceived function observations can change `k`, reveal heterogeneity,
or change the interpretation; that is a separate completion problem.

The full-clade claim `Q` remains unknown in P5/f and PA6/h because the remaining
three members are uncharacterized here. In the author-mapped PA6/f scenario,
`Q_f=0` because `g` is received. Thus observed coverage is never passed off as
full-clade purity.

## 4. How these cells enter the unchanged formula

Proposal004 combines an applicable region on a shared native draw by
`a_r(z)=C_r(z) F_supported,r(z) J_r(z) O_r(z)` and then uses its specified native
weighted averaging, within-draw requirement minimum and included-analysis
minimum. This packet does not change that compilation.

Under the author mappings, the prospective region expressions are:

```text
P5/f:  0.4 × F_supported × J × O.
PA6/f: 0   × F_supported × J × O, conditional on the valid stated scope.
PA6/h: 0.5 × F_supported × J × O.
```

No query, independently supplied organismal tree, common-tip comparison,
native placement ensemble, or numerical path lengths are provided here.
Those required inputs remain null. The source's 16S congruency grouping allows
different internal branching orders; it is not `F_supported=1`. The displayed
scale bar is not `b`, `d`, or `O`, and no branch length is guessed.

The first and third expressions have only outer bounds[0,0.4] and[0,0.5] under
the unresolved remaining factors, not numerical final A104 points. The second
would fix the region product at0 for a valid applicable instance even with
irrelevant missing factors, which remain separately missing. Because no actual
query/application has been defined, this packet emits **no whole-target A104
coordinate**, including no unconditional zero.

These are absent biological inputs, not an undefined transformation in the
already specified function-coverage calculation. Production readers and W05
credit integration remain separate and unimplemented by these files.

## 5. Experimental limits and shared evidence

These are reports of different organism/protein studies, not a matched
two-species experiment. P. stutzeri's assayed core was engineered from the
fusion; it is not a second independent evolutionary tip alongside its native
precursor. Original assay strains, preparation purity, blanks, concentrations,
temperature, repetitions and quantitative uncertainty were not inspected.
Shared substrate names do not justify numerical experimental comparability;
neither does the source tree establish isolation from assay background.
Those questions would require the original experiment records. No assumed
comparability or isolation number is multiplied into A104 here.

Table4, Figure2 colors and prose can describe the same biochemical evidence.
They populate one assignment for each molecule. The paper's reported1000
bootstrap resamples support a gene-tree analysis; they are neither1000 assays
nor an organismal-tree match count. Acinetobacter's profile is an observed
contrast in this chosen source, not a mandatory contrary-function set imposed
on all A104 uses.

## 6. Disposition of the previously circulated numbers

The current task and proposal004 identify `CLC-F8/29` as screening-panel
coverage and `Wege40/9` as a ratio of current-ratio means. This worker did not
reopen either paper-specific packet. Their diagnostic numbers are **not**
silently installed as `C` or as a final A104 score. Specific experimental
assignments in those records may populate function rows when correctly mapped;
the panel denominator cannot establish clade membership. No conclusion about
their uninspected complete data is claimed.

For TyrA, the additional work above goes beyond leaving2/5 as an isolated
diagnostic: it fixes the complete intended displayed inventory, records exact
identity/class inputs, applies the existing formal `C` calculation, and exposes
the shared scenarios and null unconditional point. Contrasting cases can be
published in one paper and can populate part of the sheet; no complete native
score or second-paper quota is imposed.

## 7. Actual inspection and verification coverage

Read in full: proposal004, exact-reader-fields004, the retained Song
`SOURCE_TO_CELLS_001.md` and `PRINTABLE_HANDOFF_001.md`.

Direct Song source inspection: current PMC page through its opening Results
subsections (through distribution of specificity classes as returned); retained
Figure2 image; complete Tables2/4; complete catalytic-core, pyridine-nucleotide
specificity and Methods sections extracted from retained primary XML; TableS1
rows ACIN, Avin, Mdeg, Paer_1, Pflu, Pput and Pstu with their actual hyperlinks.
The first attempted TableS1 file was a download-preparation page; the successful
read used `Song2005_TableS1_retrieved.html`. The original biochemical papers,
current sequence database records, independent16S trees, full figure-tree
serialization and numerical branch paths were not inspected.

Initial and post-Song complete authority reads are recorded in
`AUTHORITY_READS_001.json`. Initial aggregate-output truncation and proposal
truncation were repaired by complete rereads. The short progress comment about
TyrA scope preceded the post-paper reset and was provisional; this document is
the post-reset reassessment. No unperformed reset is claimed. No next paper was
opened. Only source parsing, counts and exact arithmetic were run; no native
bioinformatics, annotation or HPC job was run.

`CHECK_ARITHMETIC_001.py` reads the manually prepared source-to-input specimen,
checks the fixed inventories, shared assignments, both Avin candidate-ID
scenarios, the three formal C calculations and their mapping envelopes.
It is an arithmetic audit, not an implemented literature reader or native
biological validation. Criterion7 and final completion remain the parent's
responsibility.
