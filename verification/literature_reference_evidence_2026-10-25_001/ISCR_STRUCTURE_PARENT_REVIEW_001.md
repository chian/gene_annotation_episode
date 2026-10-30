# IscR structure evidence: parent conversion after the full reset

The previous goal turn was progress (verified A106 selected path and replay).
The adopted full literature objective remains active and incomplete. This review
adds an appropriate A111 source component; it does not build A102 structural
correspondence, A101 alignment, target transfer or annotation credit.

## Evidence independently inspected

Original article: Rajagopalan et al., Studies of IscR reveal a unique mechanism
for metal-dependent regulation of DNA binding specificity,
https://doi.org/10.1038/nsmb.2568, PMC3676455. Root read all147 passages of the
retained BioC projection and independently checked each against its original
BioC text. Root parsed the original HTML Table1 and viewed original figures1,
2,3,6. All35 retained worker-manifest entries matched their hashes and sizes.

Root used installed Bio.PDB.MMCIF2Dict independently of the worker's small
research parser to inspect actual4HF0/4HF1/4HF2 coordinates and reproduce the
selected4HF1 atom-group distances. No worker research script was executed because
its top-level code would rewrite historical packet outputs. Source checks are
in ISCR_STRUCTURE_PARENT_SOURCE_CHECK001.

The specific missing local-fit question justified acquiring original associated
wwPDB validation for4HF1, retained separately under
primary_iscr_structure_validation001. The core metadata lookup used the RCSB
skill's prescribed rest_request.py. The skill supports metadata/text requests;
the compressed validation XML was obtained directly from the wwPDB file archive:
https://files.wwpdb.org/pub/pdb/validation_reports/hf/4hf1/4hf1_validation.xml.gz.
The exact compressed/decompressed hashes, timestamps and HTTP receipt are saved.
Report schema/creation/version fields and all selected attributes are retained.

After the article, retained packet and new associated report were read, root
reread the complete applicable authority set, current A111sheet027 and exact
reader crosswalk, followed by the adopted full goal and latest human scope last.
ISCR_STRUCTURE_PARENT_RESET001 records actual complete reads. No new paper was
opened in that interval. The component conversion below followed that reset.

## Experiment definitions and comparability

The studied molecule is E. coli IscR. Crystal preparations are C92A/C98A/C104A
variants with a C-terminal His tag. The 4HF1 model has two protein chains and
two strands of a29-bp hya duplex, a type2 site. DNA and protein coexist. A
four-polymer-chain assembly label does not mean four IscR protein subunits.
The reported mixing ratio1:1 at500uM does not state whether protein concentration
is on a monomer or dimer basis; do not infer a solution binding stoichiometry.

The general construction paragraph names a deletion background; the specific
crystallography preparation names BL21(DE3). The latter alone does not establish
the full deletion genotype. All crystal constructs lack the cluster-coordinating
cysteines. Fractional Fe-S loading in separate fluorescence-assay preparations
cannot populate crystal occupancy. No holo-IscR structure was measured here.

The DNA-free4HF0 protein is truncated to1–133, unlike the DNA-bound preparation;
crystallization conditions also differ. E43A4HF2 changes both a side chain and
buffer salt/precipitant. These comparisons do not isolate a DNA-only or
residue-only cause of conformational differences. Missing nuisance-response
scales and alternative-contribution bounds cannot be replaced by C=I=1 for a
causal claim. A complementary binding experiment can test a functional
interpretation without becoming another structure replication.

One crystal per dataset is reported. The two interfaces, coordinate file,
validation report and source figures share that dataset/model, not independent
experimental n. Molecular-replacement/template relationships also remain shared.

## Paired fields and numerical components

The first executable question is intentionally precise: in the selected4HF1
model, are the Glu43 carboxylate groups close to four specified DNA exocyclic
amines, with local residue density agreement? The input preserves model1,
author chain/residue/insertion/component/atom/alternate selectors, both oxygen
coordinates, selected DNA nitrogen, Å units, source/artifact identity, native
occupancy/B fields and exact local-validation row attributes. An unavailable
required endpoint retains its place in the declared panel.

Distances use min over the two oxygen-to-nitrogen distances of each complete
specified chemical group. This does not select among alternate fitted models.

| Fixed geometry member | Coordinate-derived group distance Å |
| --- | ---: |
| A GLU43 {OE1,OE2} to D DC7 N4 | 2.8142604712428443 |
| A GLU43 {OE1,OE2} to D DA8 N6 | 3.5044705734247503 |
| B GLU43 {OE1,OE2} to C DC7 N4 | 2.648124052985433 |
| B GLU43 {OE1,OE2} to C DC8 N4 | 3.0569201821441134 |

The illustrative supporting distance set is[0,3.5]Å; incompatible set[4.5,infinity).
They are disjoint and leave a gap. These are proposed physical criteria, not
paper-reported cutoffs or a calibrated hydrogen-bond classifier. Gplus=3/4=.75,
Gminus=0/4=0. At3.6Å the supporting fraction is1; no reported coordinate
uncertainty resolves the near-boundary3.504Å classification. Its predicate
does not disprove the paper's qualitative contact interpretation.

The local panel is residue-granularity A43,B43,D7,D8,C7,C8. Native report RSCCs
are respectively .911,.903,.963,.944,.960,.939. Both report and coordinate
metadata identify4HF1, revision4 dated2024-02-28; selected model/residue identities
match. The report was generated in2026. This establishes the declared metadata
join, not a coordinate-byte digest supplied by the report or an independent
map recomputation. Raw reflection files were acquired by the earlier worker,
but root did not recompute a map or inspect raw diffraction images.

Under proposal027, D=min(max(0,RSCC)^2)=.903^2=.815409. This weakest-endpoint
and square transformation is a proposed local-fit index, not confidence in
chemical identity. Global resolution, Rfree and fitted B are different quantities;
none fills a missing RSCC. Residue RSCC does not become atom-only validation.

For the explicit selected-state/assignment geometry question, proposal027 allows
conditional q=C=I=1 by definition. Thus the source-only directed products are
p_ref=D*Gplus=.61155675 and o_ref=D*Gminus=0; their signed difference is
.61155675. These are one chain of dependent components. There is no T input,
target product, across-observation reduction, family weighting or W05 result.

The cell bounds from exact arithmetic or unknown-factor domains are conditional
arithmetic/logical outer enclosures, not statistical uncertainty intervals.
Native measurement uncertainty and coordinate uncertainty remain unreported.
Unconditional occupancy remains unestablished: a deposited1.00 parameter and
the conditional q definition do not establish a physical population fraction.
Broader assignment, causal and molecular-function claims cannot inherit this
calculation's conditioning silently.

## Necessary revisions and implementation boundary

The worker's earlier D/p_ref unknowns were accurate for its retained sources.
The newly acquired validation adds actual native local RSCCs and now permits
the narrow conditional arithmetic. Its historical packet is unchanged. The
new output must retain report/model revision binding and source scope, rather
than silently attributing those measurements to the original article.

STRUCTURE_INTERFACES001 defines the paired sheet cells, deterministic source
reader/calculator and disjoint fresh file ownership. The recurring investigation
TASK was printed before root created its separate prompt module. It addresses
actual molecule/state/endpoint meaning and source weaknesses, not sheet dumps.

General alternative-model/assignment scenarios, crystallographic symmetry,
causal comparability/isolation, measured occupancy, calibrated nondetection,
other structural modalities, repeated-experiment reduction and actual model-backed
structural investigation remain work. The appropriate partial path does not
replace those requirements or complete A111/the adopted objective.
