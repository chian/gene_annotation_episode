# Single-gene case: ybhP / b0790

The only annotation target is the 762-nt ybhP gene from E. coli K-12 MG1655,
NC_000913.3 positions 823736–824497 on the reverse strand. Its translation is
253 aa and matches UniProt P0AAW1 exactly. case.json fixes the target hashes.
Other sequences, genomes and proteins acquired later are source evidence.

## Actual unresolved question

What function and biological role can be defended for this particular gene?
Which family-based transfers are supported, and where must uncertainty remain?
This is an investigation, not a request to copy a database product name.

## Starting source assertions (not our conclusions)

The fetched UniProt record calls YbhP uncharacterized and marks protein existence
as predicted. It links an endonuclease/exonuclease/phosphatase superfamily,
Pfam PF03372, a DNase-I-like structural superfamily and a GPI-anchor lipid
remodeling family. These are overlapping classifications, not independent
experiments or demonstrations of one specific substrate/function.

UniProt also links a high-throughput plasma-membrane localization assertion to
Sueki et al. (2020), PMID 32127419. The full article XML was subsequently retrieved from Europe PMC and its
introduction, results, discussion and methods inspected. The experiment used a
specific MG1655-derived strain grown in LB-Lennox at 37 C during exponential growth.
It measured sucrose-gradient fractionation with quantitative proteomics; the
article discusses contamination, peripheral association and condition dependence.
At the initial inspection the target-specific supplemental row had not yet been
obtained, so no YbhP-specific localization conclusion was established then.
The later retrieved row and its limits are recorded below. Neither inspection
establishes a membrane-spanning segment. The PMC HTML route returned a browser challenge; a later
Europe PMC all-supplements download failed with a read timeout, without erasing
the successfully retrieved full text.

NCBI Gene's fetched summary reports computational association with FliR and
expression changes under several conditions. Those are summary assertions here;
the underlying studies and applicability have not been established. Association
and regulation do not themselves identify the molecular substrate.

## Initial reasoning and possible discriminating work

Broad fold/family resemblance alone cannot choose among nuclease, phosphatase,
or another activity. A specific family name warrants checking aligned regions,
active-site evidence and the context in which that family's function was shown.
The localization assertion and limited existence evidence also warrant examining
what was actually measured rather than inferring a membrane-spanning protein.

One useful ordinary evidence job is a one-query protein homology search against
reviewed proteins across taxa: do characterized relatives narrow the alternatives,
or do matches support only a broad family? An exact self-match or a copied label
will not resolve that question. Any proposed transfer needs actual alignment and
reference evidence. Search results are inputs to subsequent reasoning.

These are current reasoning possibilities, not a prescribed episode sequence.
The initial case setup itself established no function conclusion, numerical
annotation credit, monitoring score or model-driven episodic execution. Subsequent
model-driven runs and their verification limits are recorded in
[BUILD_STATUS.md](../../BUILD_STATUS.md).

## Context observation and resulting change of investigation

A fetched 8,001-nt source neighborhood contains ybhP and an immediately adjacent,
same-strand CDS labeled clsB / cardiolipin synthase B. Their annotated intervals
overlap by 4 nt. Source coordinates and labels are preserved in
acquisition/neighborhood-features.json; the target binding remains just ybhP.
The GenBank record says its annotation incorporates EcoCyc and UniProt, so these
product labels must not be counted as independent confirmation of those databases.

This makes a relationship to lipid biology a question worth investigating. It
DOES NOT establish an operon, coexpression, substrate, catalytic activity or a
specific function for YbhP. Conserved neighborhood in appropriate homologs and
relevant experimental evidence could help assess that possibility. Broad-fold
similarity must still be evaluated against competing activities. The parent must
remain free to revise this direction as actual evidence arrives.

## Literature identity check

A PubMed query for ybhP returned four records, but their full abstracts concern
pig breeds and lanthanide chemistry, not this bacterial gene. Those records
provide no evidence for this gene. A context-qualified name/accession query
returned no records; that does not prove there is no relevant literature.
NCBI Gene's explicit gene-to-publication links do identify genome, expression,
coevolution and localization studies. Their abstracts were read; the association
is not yet validation of a target-specific measurement. In particular,
co-evolution is not a physical-interaction measurement, and altered expression
under acivicin or polyamine conditions is not itself identification of substrate
or direct physiological role. Original responses are retained in acquisition/.

## Family-description provenance and structural context

The complete InterPro IPR051916 record explicitly marks its narrative description
as generated by an LLM and unchecked, with no literature listed. Its GPI-anchor
remodeling narrative must not be relabeled as a target-specific experimental
finding. The family classification itself remains source evidence. The full
IPR005135 description covers several different activities sharing the broad EEP
fold; it does not identify the substrate of this target.

IPR051916 points to experimental structure 4RUW. The acquired RCSB entry/polymer
metadata identify the source protein as Bcav_3678 from Beutenbergia cavernae, with
E. coli as its expression host. The source protein is not an E. coli YbhP assay.
The 440-aa construct includes an expression tag and maps to a 437-aa reference
protein, with an additional annotated Ig-like region. The structure's enzyme/GO
labels include imported classifications. Crystal resolution, a bound zinc and
a family label do not establish physiological metal dependence or YbhP activity.
No coordinate-based active-site comparison has been performed yet.

These observations sharpen what needs distinguishing: fold/family membership,
domain architecture, the origin of descriptive labels, and actual functional
evidence. They are case research, not proof of model-driven scientific reasoning.

The subsequent configured-model investigation_006 read these retained source
records. At action 50 it recorded assessment
`assessment_655ee0887b7a4e724a9f0bef`, with IPR051916 itself as the source subject
of the family-classification claim. It qualified that claim as nonmeasurement
information that does not discriminate the target GPI-family hypothesis.
At action 51 the parent integrated this assessment while retaining that
hypothesis as unresolved. This demonstrates that particular model decision and
integration; it does not establish the correctness of every broader inference.
The source's LLM flag applies to its descriptive narrative, not automatically to
the family assignment or underlying sequence models.

The 17 native reference records and 20 HSP observations are registered in the
canonical workspace; `evidence-refs.json` provides their actual semantic refs.
Each HSP source retains native independent/conditional scores and exact paired
residue intervals. For this case import, coverage explicitly means paired residues
divided by the full operand length; it must not be confused with a span-based
coverage definition. The omitted stop codon is not an aligned residue. Publication
created no assessment or annotation; idempotent case-preparation evidence is in
`evidence-verification.json`. The RCSB polymer metadata are now registered as a
canonical source linked to the structure entry, so an episode can inspect the
actual source organism, expression host, construct and imported classifications
through the existing source-reading tool. No assay or functional conclusion was
created by registering that source. `verify_preparation.py` replays preparation
with native process creation forbidden and checks source bytes/lineage, typed
comparison refs, exact one-gene bounds and unchanged record counts.

## Retrieved localization evidence and limits

Investigation_005 retrieved the primary study's versioned supplemental workbooks.
Table S3, sheet `Average ratio and clustering`, row 1324 identifies YBHP/P0AAW1.
Its original STEPdb label is `Cytoplasm`; the study's fractionation-based label
is `IM`. Both replicate cluster assignments are 2 and their comparison is
`match`. The retained sucrose-gradient ratio is -0.51241541000000002. These are
different fields with different origins, rather than two independent localization
experiments. The Info sheet identifies the IM field as the study's assigned
localization and explains the prior database field. Table S1 retains separate
replicate fraction measurements at row 308.

Reading the complete primary methods identifies the experimental strain as
MG1655 Δ(argF-lac)U169 rprA::lacZ, grown in LB-Lennox at 37°C and 200 rpm for four
generations, then harvested during exponential growth at OD578 0.6–0.8. The study
assigns localization using reproducible fractionation patterns and agreement
between clustering and a gradient-ratio method. Its discussion describes
peripheral interactions, conditional association and complexes that can produce
misleading fractionation. An IM assignment here does not by itself demonstrate
a membrane-spanning segment, membrane insertion, exclusive localization under
other conditions or a particular catalytic substrate.

The row also reports four quantified unique peptide matches. That experimental
observation and the retained UniProt `Predicted` existence label have different
provenance. Assessing what the peptide evidence establishes for this precise
target and assay is distinct from treating the database label as current truth;
neither alone verifies the entire protein sequence or its molecular function.

The original Table S3 workbook has SHA-256
`b7a18c32752040f3e11150c8024bda6d9df2b51ed5261a895bfe63c2f48a7952`.
In investigation_005 its retained source is
`source_010bd54d7870ff271dd2aa04`; selected row/header source
`source_d828627e56d52ada628be599` retains the original cell addresses and parent
workbook link. The article source is `source_7bc43de7ef423954085482a1`, PMID
32127419 / PMC7055658, DOI 10.1128/mSystems.00808-19. These human case notes do
not create episode findings, change credit or replace the parent episode's
scientific interpretation.

### Current source-provenance question

The complete primary article body was reread during the investigation_006 audit.
It explicitly describes STEPdb as integrating computational predictions and
experimental information. The Databases methods also explain that its original
localization categories were summarized/modified for this study, including
assigning a single location where the database had multiple annotations.
Table S3 therefore establishes the prior reported Cytoplasm label, but it does
not by itself establish that YbhP's original entry was purely a prediction.

Inherited finding `assessment_aeea3b144bb25dc04a278115` uses qualification
`prediction_not_measurement` for that label. The precise open question is what
entry-level evidence and source version supported the original YbhP STEPdb
annotation. The reviewed article does not settle that question. No conclusion
that the original label is experimentally established, wrong, or purely
computational follows from this audit. The cited STEPdb paper is Orfanoudaki
and Economou (2014), DOI 10.1074/mcp.O114.041137, PMC4256514. The direct PMC
page presented a browser challenge, the DOI route was forbidden, and Europe PMC
full-text acquisition returned HTTP 500. The latter response and its receipt
are retained as `acquisition/STEPdb-2014-PMC4256514.http-500.body` and the matching
receipt; they are not an acquired article. This human note withdraws no episode
finding and changes no scientific score or stopping rule.

### Target-specific FliR remark

Investigation_006 read Table S4, sheet Table S4, row 49: YBHP/P0AAW1, prior
STEPdb Cytoplasm, study localization IM, and the remark
"Functional relationship/co-evolution with integral IM FliR" with DOI
10.1073/pnas.0709671105. The selected source is
`source_07ae39d1343a2730835990de`, derived from workbook source
`source_da5508d4be4b6bc894de7d17`. The original workbook's SHA-256 is
`416c59e0c7f57bd631830289260b91a259d674a57dca3fc0406002c2e20e9a27`.

The episode's action 42 retained this source assertion with the qualification
`prediction_not_measurement`; action 43 integrated the corresponding biological
role as unresolved. These records do not establish direct binding to FliR,
participation in a measured complex, a molecular substrate or an enzyme activity.
The cited paper's returned abstract describes a coevolution estimator. Full-text
acquisition returned HTTP 500 and the alternate PMC listing returned no versions;
neither transport outcome is negative biological evidence. Further interpretation
must preserve what was and was not read.

## Retained profile-match evidence for the fixed sequence

The earlier parent's admitted form included the raw Pfam search evidence now
supplied to investigation_006 as caller input. Observation
`observation_69f7e1b493bf9618e1949c24` points to PF03372 in the original response
`source_1c24bca2fe7c6c7816e792b9`. That response identifies the profile as a
`Domain`, labeled Endonuclease/Exonuclease/phosphatase family. The native domain
bit score is 83.15518951416016, independent-domain E-value
2.878650475323588e-23 and conditional E-value 2.3913029368031133e-27. The retained
observation correctly uses the independent value. Its query interval is
[13, 244) aa, with span coverage 231/253 of the query and 224/225 of the profile.
These are span coverages, distinct from the paired-residue coverage in the local
phmmer results described above.

The retained provider request and actual submitted FASTA sequence agree with
the existing 253-aa product, SHA-256
`f0cdd3744b5bc986fd574175ecb7155c0ed57c7749098f20300735a3c849560a`.
That product maps to nt [0, 759) of the same fixed gene, excluding its terminal
stop codon. The response and request artifacts were hash-checked. This is
target-specific profile evidence for examining a broad EEP association; it is
not a measured substrate preference or enzyme activity. The reuse imports no
prior assessment, annotation, hypothesis or interpretation account, and adds
zero investigation credit by itself. The exact read-only verification is in
`runs/investigation_006/baseline-verification.json`. Parent interpretation and
subsequent investigation remain episode decisions.

## ANGEL activity: experimental subjects and unresolved transfer

Investigation_005 retrieved PMC9525292, DOI 10.1038/s41467-022-33368-9,
as `source_126645454cb20b9528ab9fe3`. Reading its complete Results and Discussion
and the relevant cloning, localization and phosphatase methods distinguishes
two observations. Recombinant Drosophila and mouse ANGEL constructs removed
terminal 2′ and cyclic phosphates in vitro, without efficient 3′ phosphate
removal under those conditions. Knockout-tissue RNA assays instead implicated
3′ terminal phosphate processing in vivo. The authors leave the explanation
open; these are not interchangeable substrate observations.

The recombinant proteins are truncated constructs: DmANGEL aa 26–354,
human ANGEL2 aa 165–544 and mouse ANGEL2 aa 164–544. E. coli expression cells
are production hosts, not the biological subjects whose activities were
established. The native search's zebrafish ANGEL2 match is also distinct from
those assayed subjects. Consequently neither an ANGEL label nor this paper
alone establishes a substrate or mitochondrial role for YbhP. These are source
audit notes, not new episode findings or an imposed interpretation. The parent
must determine the relevance of the actual sequence match and source evidence.

## Further GPI-process source qualification (investigation_006, action 115)

The parent retained the GO:0006506 GPI-anchor biosynthetic-process assertion from
RCSB source source_aad3bfbfb9e43ec998ece3bf as an imported UniProt annotation
about C5C3L1, not an assay of YbhP. The retained UniProt C5C3L1 response explicitly
labels that GO assertion IEA:TreeGrafter; its catalytic-activity GO assertion is
IEA:InterPro. Neither is direct target-specific activity evidence. The original
RCSB artifact digest and exact [14900, 15600) anchor match the recorded observation.
Assessment assessment_7369113d95e10c026f135ddd is incomparable/does_not_discriminate
for the YbhP GPI-process hypothesis, with prediction_not_measurement qualification.

Annotation revision 13 (annotation_e0e1a658f1f59fa7b525c4b0) keeps GPI family/process
interpretations unresolved. This useful qualification increases investigation
progress from 14 to 15, while the separately reported annotation support remains
0.2667005334010668 in supplied decision context 127. It does not establish a new
enzymatic function or turn the reference protein into the annotation target.

## Localization qualification applied to the FliR question (investigation_009)

At root action 19, assessment `assessment_6d66a5db2009811fdeebb5b3` applies the
existing IM-localization source claim and its
`measurement_does_not_establish_claim` qualification to the proposed functional
relationship/co-evolution with FliR. It explicitly declares the same source claim
as `assessment_6e66c41eeff2eb6394bfce19`, uses `does_not_discriminate`, and retains
the original observed protein subject. The observation is an anchored selection
of the existing localization workbook row, not an independent interaction assay.
Root action 20 integrates it in annotation revision 14,
`annotation_f7f59d09cd13a2ec8c9f448d`, leaving the FliR interpretation unresolved.

The recorded progress rises 15 → 16 because the current finding identity includes
the target hypothesis; annotation support remains 0.2667005334010668. This does
not establish a new localization measurement, direct interaction or specific
enzyme activity. Whether reuse of an already-known claim and qualification across
hypotheses should earn another progress unit is an explicit question to the user.
No answer, new identity rule or historical score correction is assumed.

## Fluoride-stress expression context (investigation_009, actions 56–57)

The parent acquired PMC10100675 (DOI 10.1128/spectrum.04158-22), retained as
`source_d46af70f27113511c1225280`. The study uses E. coli MG1655 in anaerobic
M9 medium with 0.4% glucose. It compares untreated cultures with 20 or 70 mM NaF
treatment, and diluted recovery cultures, using whole-genome tiling arrays and
three biological replicates. The article groups ybhP with lipid-biosynthesis
genes; its functional grouping uses STRING annotations. This is distinct from
measuring YbhP enzymatic activity. Its targeted RNA-stability/Northern experiments
on osmC and yghA do not become experiments on YbhP.

At action 56, `assessment_7918dd27d33e5185427e035f` retains the paper's reported
lipid-biosynthesis grouping with `prediction_not_measurement` qualification,
`contextual` applicability and a `mixed` relation to the target-role hypothesis.
The observation retains the paper's named ybhP source subject, and the anaerobic
condition is a separate source-anchored context. Action 57 integrates that
assessment into whole-input-context annotation revision 2,
`annotation_ee66f5aea52b32a08cae57ff`, with the role still unresolved.

Supplied parent context 58 has investigation progress 17, annotation support
0.2667005334010668 and monitoring information 1. The source-annotation observation
is not automatically a new experimental hypervolume axis. This is a distinct
source finding, unlike the previous reuse across hypotheses. These notes verify
what the parent recorded and the scope of the primary article; they add no
outside scientific assessment or credit to the workspace.

Action 59 then separates the measured expression grouping from the paper's
functional classification. Assessment `assessment_d4645ea0782d69c108899be3`
retains the reported membership among upregulated genes under the same anaerobic
condition, with `measurement_does_not_establish_claim` qualification and
`does_not_discriminate` relation to the lipid-role hypothesis. Thus expression
response is retained information without being promoted into evidence of lipid
substrate specificity or catalytic activity. Supplied context 60 has progress
18, with annotation support and monitoring information still unchanged.

Action 68 records a more specific source assertion from Table 2: its Operons
column lists `ybhP-cslB-ybhN` under the functional subcategory `Cardiolipin
biosynthesis I`, with ppGpp in the activator column. The original spelling
`cslB` is retained; this source group is not silently relabeled as the single
target gene. The category cell spans the pgpC and ybhP-group rows. The table
caption concerns expression clusters, and its footnote distinguishes bold
entries that were insignificantly affected by NaF. The ybhP-group cell has no
bold markup in the retained XML; no gene-specific p-value or enzymatic assay is
inferred from that formatting.

Assessment `assessment_3856c41088f842906f87b405` keeps the group pathway label
as a prediction, with contextual applicability and a mixed relation to target
hypothesis `hypothesis_b2a523018022f93a803c3dce`. Its addition raises recorded
progress to 19; target pathway participation remains unresolved. The parent
integrates it into context annotation revision 4,
`annotation_772cc64347ac4f5681c5a3c0`.

That integration also exercised actual partial-work recovery. At action 69 the
annotation update succeeded while a separate interpretation-account row had a
revision conflict. Context 70 contains the preserved annotation reference and
the conflict's actual current revision (0). The parent's next selected commit
uses revision 0 and records `interpretation_account_c7fc7ee98a94f14456c6afd1`.
Both selected reasoning actions have zero scientific gain; the pathway finding
had already contributed at action 68. The complete trace and targeted table
header/category/footnote inspection are in
`runs/investigation_009/fluoride-context-verification.json`.

## LolCDE-inhibitor expression study: source-verification notes

Investigation_009 action 102 acquired PMC5105897, DOI 10.1128/JB.00502-16,
as `source_c48e06bb88a96ccae58ffcbc`. The parent subsequently selected its
supplementary workbook and extracted only the matching ybhP row and introductory
headers. These are evidence about the fixed target, not new annotation targets.

Reading the complete saved normalized article and its original Table 1 identifies
the experimental subject as E. coli BW25113 ΔacrB, grown in LB at 37°C with
shaking. The methods describe two biological replicates per condition, exposure
to compound 2 at 0.3 or 1.2 µg/mL for 30 minutes, and RNA-seq mapped to BW25113.
This is distinct from both the MG1655 target and the anaerobic fluoride study.
The paper explicitly allows posttranscriptional effects on mRNA stability;
transcript abundance is not a direct measurement of YbhP catalytic activity.

Table 1 gives YbhP fold upregulation of 17.60 and 33.10 at 0.3 and 1.2 µg/mL,
respectively. Its annotation columns label the product Cytoplasmic and the
function unknown, with product information attributed to EcoGene. Those labels
are source annotations, not a localization assay in this paper. Table 1 and the
supplementary measurements describe the same experiment, not independent
replication.

The first selected workbook row is row 41, with original stored fold difference
17.598507269999999 and normalized means 5.114327061319992 (control) and
90.004521990784241 (treated). Its title cell specifies 0.3 µg/mL while the sheet
and treated-column names use the unitless label 0.5. The methods state an MIC
of 0.6 µg/mL, so
0.3 µg/mL is half that MIC. Interpreting 0.5 as a MIC fraction is compatible with
the methods and the matching Table 1 result; the workbook label alone does not
establish its unit or a data error. This is an operator source review,
not a new episode finding, credit award or outside edit to scientific state.

Ordinary spreadsheet calls also exercise the separate timing path in the real
configured-model investigation. Actions 111–113 measured service-wall durations
0.453040593, 0.795610807 and 0.73293492 seconds. Each has one matching physical
statistic and a received native receipt. Parent monitoring information rises
1 → 2 → 3 → 4, while scientific progress remains 19 and annotation support stays
0.2667005334010668. The next decision receives duration forecasts for these
actual execution classes. The exact verification is in
`runs/investigation_009/ordinary-native-timing-verification.json`.

At parent action 129, assessment `assessment_0987318ef933467a60546207` retains
the LolCDE expression observation with `measurement_does_not_establish_claim`
qualification and `does_not_discriminate` relation to the lipid-role hypothesis.
Its observed subject remains source gene `reference_ef077d53e9780f5080132f68`,
distinct from the fixed target. The context record preserves the original
`no compound vs. 0.5 LolCDE` comparison label. It does not yet explicitly encode
BW25113 ΔacrB or the verified concentration/time in attributes; those details
remain in the linked primary article rather than being asserted as measurements
on MG1655. The native result and source quote retain the original numeric cells.

Actual supplied contexts 129 → 130 show scientific progress 19 → 20, monitoring
information unchanged at 7, and annotation support unchanged at
0.2667005334010668. This gain belongs to the qualified scientific finding,
separately from the six preceding spreadsheet duration measurements. The existing
ordinary-native verification receipt now includes this source/receipt/credit
follow-up. No biological interpretation or score was added by the audit itself.

Action 137 separately retains the second LolCDE exposure as assessment
`assessment_15e2678dba43320f48738f99`, again contextual and
`does_not_discriminate`, with `measurement_does_not_establish_claim`
qualification. The original workbook row 45 reports fold difference
33.103287539999997, with a treated normalized mean of 169.30103930000001 and
control mean 5.114327061. Table 1's 33.10 value at 1.2 µg/mL agrees to rounding;
the recorded context preserves the original unitless `2.0 LolCDE` column label.
These are two conditions in one study, not two independent studies.

Action 138 integrates both LolCDE findings into whole-input-context annotation
revision 5, `annotation_cce03e6fa9578e32203e9ab9`. Their context references occupy
separate coherent sets and both retain unresolved disposition for the lipid-role
hypothesis. The fluoride-study context remains separate as well. Supplied contexts
137 → 138 show scientific progress 20 → 21 for the second-condition finding;
context 139 retains 21 after integration. Annotation support remains
0.2667005334010668 and monitoring information remains 7. Integration itself adds
no second credit for the finding. The existing ordinary-native receipt retains
the exact record, checked source spans and separate condition sets.

## Later source qualifications and article-table follow-up (investigation_009)

At action 209, `assessment_1262e0e714388e2220b14c46` retains a further
`confounding_unresolved` qualification for the high-condition workbook row.
The parent links the workbook introduction and column contexts, but this
qualification identifies no specific causal confounder. The bound finding rule
adds one unit (21 → 22). The primary Methods give an MIC of 0.6 µg/mL and
an exposure of 1.2 µg/mL: interpreting the column's unitless `2.0` as twice
MIC is compatible arithmetic, not proof of a label contradiction or a data error.
The exact trace and source limits are in
`runs/investigation_009/lolcde-label-qualification-verification.json`.

Action 222 records `assessment_3f0a9891723e3297bb167478`, qualifying Table 1's
`Cytoplasmic` source annotation for the target-localization question. The study
does not perform a YbhP localization assay. Its footnote attributes product
annotations to EcoGene; EcoGene's underlying entry-level evidence remains
untraced. The retained `prediction_not_measurement` qualification must therefore
not be read as proof that EcoGene's original basis was computational. The bound
score becomes 23. Action 223 integrates this assessment into context annotation
revision 6, leaving localization unresolved and the three expression-study
condition sets separate. Annotation integration adds no further unit. The
trace is `runs/investigation_009/paper-localization-qualification-verification.json`.

Action 257 attempts dose-specific article-table records but supplies a 1,908-byte
quote for a declared 2,000-byte span. The exact transcription errors reach the
parent. It selects smaller reads, commits the two source-anchored dose contexts
at action 260, and commits the table observations and assessments at action 262.
The latter are `assessment_91f6c551e4e2743f6a20f91e` (0.3 µg/mL) and
`assessment_ca923938fa170ccf4da7a844` (1.2 µg/mL). Both retain
`measurement_does_not_establish_claim` and `does_not_discriminate` for the same
lipid-role hypothesis as the earlier supplement findings. Action 263 integrates
them into context annotation revision 7, `annotation_d202ecdaddf964c8e164da5a`,
again with unresolved disposition. All five anchors in the successful context,
term and observation commitments validate against the actual source bytes.

The two new assessments receive two further units (23 → 25) under the current
identity rule. This requires a qualification of the progress claim: Table 1's
17.60 and 33.10 agree, to rounding, with the earlier retained supplement values
17.598507269999999 and 33.103287539999997. They report the same experiment.
The new records use the article's source/subject/condition identities and its
fold-upregulation header; the old records use workbook identities and the
`upregulated genes` term. No equivalence to the earlier source claims is declared.
The identity rule therefore separates them even though the target hypothesis
and qualification kind are unchanged. These two units do not establish two
independent experiments, a new target function, or two newly resolved scientific
questions. Cross-representation corroboration and semantic novelty must be
distinguished before calling this additional scientific improvement.

`runs/investigation_009/paper-table-followup-verification.json` retains the
actual commitments, exact next-context delivery checks, original observations,
source-cell agreement and differing identity fields. The failed action has no
own-action observation under the unchanged bound rule; the successful context
commit and annotation integration each have one zero-gain observation, and the
two-assessment commit has one +2 observation. This read-only examination changes
no scientific records, credit or controller history. Annotation support remains
0.2667005334010668 and monitoring information remains 11 in the supplied parent
contexts. The investigation is still running; these notes are not a final
annotation or a claim of scientific completion.
