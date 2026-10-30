# Input, structure and quality: judgments needed for biological annotation

Research note, 2026-10-19. This is a problem analysis for a replacement design,
not a specification inherited from the superseded genome runner. No application
code or model workflow was run for this note. Published examples below are
distinguished from proposed investigations.

The central work is deciding what an observation means in its biological and
experimental context. Gene calls, sequence searches and quality estimators supply
observations. A REASONING task compares explanations, notices when its current
interpretation is inappropriate, and considers what would discriminate between
the remaining explanations. The numerical controller decides continuation.

## What the input can and cannot establish

Input modality, biological role and organismal scope are different questions.
The following are proposed representation and reasoning requirements, not claims
that the listed information is always available.

| Supplied material | Useful local questions | Context that must not be invented |
| --- | --- | --- |
| A DNA string or individual gene sequence | Coding/noncoding alternatives, strand, frame, partial boundaries, local sequence anomalies | A complete chromosome, known taxon, standard code, neighboring genes or a missing whole-organism pathway |
| An RNA string or transcript collection | RNA-family/structure hypotheses, mature versus precursor interpretation, coding potential, processing alternatives | The genomic locus, genomic introns, expression abundance, complete transcript boundaries or a genome-wide absence |
| A protein string or protein collection | Family/domain alternatives, termini, residue observations, architecture and function specificity | A fabricated CDS, contig, nucleotide sequence, codon usage or particular genomic neighborhood |
| Raw reads or read fragments | Read-supported local sequence, partial coding/RNA hypotheses, alternative assemblies, error explanations | A trustworthy finished consensus, one read per gene, one organism per collection or independent evidence from overlapping reads |
| An assembly or MAG | Feature structure, contig relationships, lineage consistency, possible missing or foreign sequence | Completeness, purity, culture identity, circularity or a single correct bin assignment merely because a file is called a genome |
| A heterogeneous dataset | Which observations and comparisons belong to which samples/entities | A universal taxon, common processing history or organismal linkage solely from membership in the same file |

Preserve original bytes, sequence identities, declared roles and provenance.
Possible molecule interpretations can remain unresolved; a name or alphabet
alone need not decide the biological role. In particular, NCBI documents that
GenBank mRNA is conventionally displayed using the DNA alphabet, so T versus U
does not supply a universal DNA/RNA classifier. [NCBI genetic-code documentation](https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi)

The relevant unit can be a sample, sequence, feature hypothesis, translation,
RNA product, read-supported variant, element, bin or collection. These are
related identities, not interchangeable names. A protein input remains a direct
annotation subject. A derived feature or translated product is created only
when that derivation actually occurs.

## Defeasible judgments and discriminating follow-ups

These are examples of small scientific reasoning tasks. They are not obligatory
stages or a request to create one Episode per question. A broader iterative
investigation can revisit several judgments as outcomes arrive. A useful child
investigation has a question it can refine; an ordinary extraction, alignment or
single assay-data lookup remains an ordinary tool acquisition.

### An apparent broken gene in a short or noisy sequence

**Published basis.** FragGeneScan explicitly models partial genes and
indel-related frameshifts. Its authors also acknowledge that the exact amino
acids inferred across an error can remain uncertain. Its 2010 sequencing models
and benchmarks must not be treated as validation for every present-day platform.
[FragGeneScan paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC2978382/)

**Reasoning question.** Does a split alignment suggest a real disruption,
insufficient sequence, an assembly/basecalling error, or a different translation
interpretation? An algorithm's reconstructed reading frame does not establish
that the original molecule contained those reconstructed bases.

**Possible next investigation.** Compare the competing translations with
independent read support and available quality measurements. Consistent support
for an indel and weak support near a problematic region affect different
explanations. Functional split components and fusion alternatives also remain
possible hypotheses when the evidence motivates them; an expectation of an
intact single protein cannot decide the matter. If reads or suitable models are unavailable, retain a conditional
or partial interpretation rather than inventing a correction.

**Information passed onward.** Original subject and interval, observed indel/stop
positions, exact derived translations, source/read references, changed-versus-
unchanged alternatives and the specific missing discriminator.

### Repeated internal stops: wrong code, local recoding, or disruption?

NCBI documents different bacterial translation tables: code 4 assigns UGA to
tryptophan, while code 25 assigns it to glycine. Start-codon interpretation is
also distinct from internal translation. These facts make the supplied code and
any inferred code hypothesis explicit dependencies. [NCBI genetic codes](https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi)

A reasoning task should compare a widespread pattern across independent loci
with an isolated exception. It can consider alternate-code translations,
organism-appropriate recoding evidence and disruption explanations. Which
interpretation becomes more plausible depends on the actual pattern, not a
universal rule that internal stops imply pseudogenes. NCBI's annotation process
recognizes programmed frameshifts and selenoproteins; its other pseudogene
labeling conventions are its pipeline's decisions, not authority for ours.
[NCBI annotation process](https://www.ncbi.nlm.nih.gov/refseq/annotation_prok/process/)

A comparison returns the translation-context references, affected loci,
supporting/conflicting observations and whether the evidence discriminates
between global and local explanations. Revising that interpretation does not
rewrite the submitted sequence or relabel old observations with a different code.

### Two fragments at the displayed ends of a sequence

**Illustrative judgment.** Two end fragments matching different parts of one
homolog can motivate an origin-spanning feature hypothesis. They do not alone
establish circularity or justify joining unrelated records.

An investigator can compare an explicit end-to-start derivation with the
unjoined alternatives and inspect available junction support. Agreement under
one coordinate transformation supports a particular interpretation; conflicting
read support or inadequate context leaves it uncertain. Original coordinates,
ordered segments, orientation and mapping back to original bytes travel with
the result. Merely prohibiting partial genes at sequence ends is not a circular
origin analysis.

This example also demonstrates why local and collection context must communicate:
a local alignment cannot decide whether two supplied sequences came from the
same molecule.

### A required-looking RNA is missing, or its subtype is unexpected

**Published curation examples.** The tRNAscan-SE 2.0 authors investigated missing
tRNA types and found different explanations: an alternative decoding tRNA,
unmodeled group-I introns, model misclassification, an incomplete assembly and a
gene split at a circular boundary. They also describe multiple/noncanonical
archaeal introns and distinguish tRNAs sharing a CAU anticodon.
[tRNAscan-SE 2.0 paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8450103/)

The small reasoning task is therefore to interpret the pattern of missing and
conflicting observations. It may compare precursor/mature structures, alternate
models, termini and surrounding sequence before changing a subtype or claiming
absence. An absent expected subtype can motivate a targeted follow-up without
becoming a completeness gate. A high-scoring model is still an observation,
especially for an unfamiliar lineage.

The interface needs candidate identity, original and processed segments,
anticodon observation, competing subtype/model references, intron hypotheses,
and which interpretation changed. Avoid making anticodon, model winner and
biological function synonyms.

### An overlap could be coding sequence, RNA, regulatory sequence, or several

NCBI's documented annotation scope includes structural/small RNAs and CRISPR
arrays in addition to proteins. It uses both sequence and other model evidence;
some overlap handling is native pipeline policy.
[NCBI annotation process](https://www.ncbi.nlm.nih.gov/refseq/annotation_prok/process/)

**Proposed reasoning task.** Compare what the observations actually support:
an encoded protein, an RNA product, a proposed regulatory element, an incidental
match or compatible overlapping roles. Examine orientation, relevant structure,
comparative placement and any supplied transcript/translation observations.
Neither a familiar motif nor the larger raw score from a different model family
automatically settles the question.

Possible follow-ups include checking whether a proposed RNA boundary explains
the same observations, comparing the neighboring feature hypothesis, or asking
whether available expression data discriminate between interpretations. Lack of
expression data leaves a limitation; it is not negative expression evidence.

This note establishes the need for regulatory interpretation, but does not claim
to have reviewed the full literature on bacterial/archaeal promoters,
terminators, riboswitches or transcript processing. Their mechanisms and assay
semantics need additional focused source reading when those judgments are
developed. A generic motif menu is not a substitute.

### A foreign-looking region could be legitimate mobile biology

geNomad's authors use neighborhoods of viral/chromosome markers to infer
integrated elements. Boundaries are inferred and can involve neighboring tRNAs
or integrases. This is evidence for element interpretation, not an automatic
decision about every gene's function.
[geNomad paper](https://www.nature.com/articles/s41587-023-01953-y)

**Proposed judgment.** Does a discordant region fit an integrated element,
an independent plasmid, a misassembled/mis-binned fragment, or an unresolved
combination? Compare its physical placement, marker distribution and available
sequence support. A revised element boundary can change which genes are assigned
to the element without changing their original coordinates or declaring the
entire input contaminated.

The maintainers distinguish marker-based classification from comprehensive gene
annotation, expose native reporting/filter settings, and report terminal-repeat
and integrated-element categories. Preserve those meanings rather than treating
a classification score as a calibrated functional probability or a terminal-
repeat label as a caller-supplied circularity assertion.
[geNomad maintainer documentation](https://github.com/apcamargo/genomad)

### An unusual functional repertoire: novelty, transfer, mixture, or artifact?

GUNC distinguishes redundant and non-redundant contamination. Its clade-
separation score is not a contamination fraction, its reference-representation
score provides different information, and it does not measure completeness.
Poor representation and close relatives limit interpretation.
[GUNC paper](https://link.springer.com/article/10.1186/s13059-021-02393-0)

An investigator can compare lineage observations within and between contigs,
assembly relationships and available sample history. Competing explanations
include unfamiliar biology, horizontal transfer, mixed origins and erroneous
assembly/binning. Changing reference scope may help discriminate these without
silently assigning the whole dataset a new organism identity.

The useful return is the affected subjects, actual metrics with their meanings,
competing explanations and a discriminator the current evidence lacks. A native
contamination flag is informational evidence. It must not automatically erase
genes or suppress the next biological investigation.

### The apparent organism could reflect sample processing

Salter and colleagues experimentally observed kit/lot-dependent contamination,
especially consequential for low-biomass material, and batch-associated patterns
that could be mistaken for biology. [Primary contamination experiments](https://link.springer.com/article/10.1186/s12915-014-0087-z)

A small reasoning task can compare specimen, extraction, amplification and
sequencing relationships with available controls. Is the unusual signal
associated with the sample or with how it was processed? Original biomass
measurements, kit/lot/batch identities, control specimens and replicate links
are observations; reagent contamination is an explanation.

Follow-ups may compare supplied controls or independently processed material.
Unavailable controls remain a context limitation. A genus reported as a
contaminant elsewhere cannot itself justify rejecting a region or organism.

### Growth or habitat appears inconsistent with the sequence interpretation

MIxS separates sampling environment, processing and growth-condition references.
Its environmental-medium term refers to material surrounding the sampled
specimen, not the composition of a culture medium. Its growth-condition field
can identify a publication/protocol rather than a measured outcome.
[MIxS checklist](https://genomicsstandardsconsortium.github.io/mixs/0010003/),
[environmental medium](https://genomicsstandardsconsortium.github.io/mixs/0000014/),
[growth-condition reference](https://genomicsstandardsconsortium.github.io/mixs/0000003/)

**Proposed judgment.** Does an apparent genotype/phenotype discrepancy arise
from the gene interpretation, organismal scope, the assay conditions, inherited
metadata, or missing information? Compare a source-linked growth observation
under its actual conditions with the specific inferred capability. Environmental
association and measured growth are different operands.

A useful return identifies which condition and source were examined, whether
the comparison is appropriate, competing explanations and the observation that
would change the interpretation. It does not fill missing genes from expectation
or infer whole-organism absence from a single protein or fragment.

## How these judgments communicate

The links run both ways. A functional discrepancy can motivate structural
reconsideration; a structural revision changes a translation; a changed
translation changes the appropriate functional comparison. An element or sample
interpretation can change which organism-level conclusions are warranted.
Metabolic/context reasoning can expose a specific uncertainty without taking
ownership of the input sequence or silently selecting a new annotation.

These are proposed semantic interfaces, not final APIs:

| Information crossing a boundary | Identity and meaning that must survive |
| --- | --- |
| Input and specimen context | Original subject/sample, supplied versus inferred status, actual collection/processing relationships, original source |
| Structural candidate | Exact input and ordered coordinates/segments; alternative identity; strand; partial-boundary interpretation; actual producing observation |
| Translation or processed RNA | Parent candidate, chosen context/processing hypothesis, resulting sequence, exact transformation and exceptions |
| Search/model observation | Query identity, eligible reference snapshot, source context, raw measurements, actual examined scope and result limitations |
| Organism/element interpretation | Which subjects the interpretation concerns, competing alternatives, supporting/conflicting references and unresolved ownership/linkage |
| Experimental comparison | Actual condition/measurement/control identities, meaning and units; what was reported versus inferred |
| Reasoned assessment | The particular question, hypotheses compared, evidence relationships, applicability limitations and compared discriminators |

The parent supplies the form and allowed meanings. A child can fill a constrained
comparison rather than returning a findings paragraph. For example, fields could
refer to commissioned hypothesis IDs and use values such as `strengthens`,
`weakens`, `does_not_discriminate` and `context_missing`. A proposed discriminator
can identify a registered test design, the hypotheses it separates and the
observation pattern that would favor each. These are comparisons for the parent's
next decision, not child-issued instructions or executable commands hidden in a
report.

Numerical probabilities must not appear merely to make a judgment look precise.
If an assessment is an uncalibrated model interpretation, record that origin.
Source facts and arithmetic remain distinct from those interpretations. The
private reasoning conversation need not cross the parent boundary.

Every scientific heuristic here is defeasible. A score, expected gene, unusual
taxon or missing metadata field supplies context for reasoning. None is a hidden
approval condition. The owning Episode chooses a next analysis or investigation;
the shared runtime executes it; the configured numerical controller owns
continuation. Returning an interpretation does not by itself establish completion.

## State, provenance and credit consequences

Keep immutable input bytes and supplied assertions separate from append-only
observations and revisable interpretations. The original caller statement may
later look mistaken; preserve it as what was supplied, while recording the new
explanation and its evidence. Do not mutate input identity to follow a taxonomic,
sample or element hypothesis.

Dependencies should be specific. A changed translation affects searches of that
translation. A new interpretation of an unchanged habitat label does not alter
the sequence of an existing alignment. A revised element boundary changes the
current element-membership conclusion while preserving the measured source
coordinates and historical alternatives. Acquired public annotations remain
attributed evidence about their source subjects, never a replacement input.

Coverage needs an examined scope. No hit in one supplied fragment, an unavailable
model, an incomplete reference collection and observed absence in an adequately
examined scope are different outcomes. Missing data, not measured and an actual
negative observation must remain distinguishable.

The exact recorded observations supporting a comparison must be inspectable by
its responsible investigator, including observations beyond a preview page.
Changed current interpretations, owner-facing information and any credit change
must describe that same committed work. Do not award biological progress for
database downloads, new candidate counts, report length or a more confident label.
The user-selected softened evidence-volume objective needs actual evidence
operands; tool activity is not one.

## What was read and what remains open

Primary reading: MIxS checklist and field definitions; GUNC methods, results and
discussion; Salter experimental results, methods and control recommendations;
the complete NCBI process page and relevant genetic-code definitions; FragGeneScan
methods/results/discussion; tRNAscan-SE 2.0 methods and prokaryotic curation
examples; geNomad provirus methods/results and the maintainers' input/output
documentation. Where the PMC browser page returned a challenge, the same papers'
full-text XML was read through Europe PMC's article repository.

This establishes concrete failure explanations and communication needs. It does
not establish a complete theory of gene regulation, a modern-platform error
model, an automatic biological quality decision, or a final Episode tree.
Additional focused reading should refine those questions as the overall
biological investigation design is assembled. No existing runner API is a
requirement for that design.
