# Functional interpretation and comparison: working research map

2026-10-19. Research and proposed semantic interfaces only. No application code,
workflow run, annotation, database installation or experimental validation is
performed by this report. Earlier implementation and design were archived under
`_superseded/2026-10-19-genome-runner`; their existence does not approve their
choices for the new task.

The intended work is iterative improvement of biological understanding and its
annotation. More hits, more specific names, more tools or more activity are not
the objective. The annotator must be able to reconsider the explanation, the
sequence interpretation, the relevant comparisons and what to investigate next.

The biological questions below do **not** define Episode types. They describe
information and reasoning that useful investigations may need. An Episode's
method, ownership, communication and yielding remain a separate question. The
earlier [local method-loop design](../../_superseded/2026-10-19-genome-runner/docs/METHOD_LOOP_DESIGN.md)
was read for its actual ownership/accounting contracts, not as authority for a
mandatory biological decomposition.

## Six defeasible judgment traces, grounded in primary sources

Substantive article sections were read, including methods and qualifications,
rather than inferring behavior from titles or search snippets. The cases are
historical evidence about reasoning practice, not claims that their database
records or software remain unchanged today. Each proposed test and possible
revision is our working design inference. The central object is a scientific
judgment that can change: what normally suggests an interpretation, when that
cue misleads, what context matters, and what observation distinguishes the
alternatives. These are considerations for reasoning, not acceptance rules.

### 1. Similarity does not settle catalytic specificity

**Source:** Schnoes et al. (2009), *Annotation Error in Public Databases:
Misannotation of Molecular Function in Enzyme Superfamilies*.
[Full article](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1000605).
Read **“Types of misannotation,” Table 1, Figure 6; Methods → “Assessment of
functional residue designation”; “Misannotation issues for large-scale
databases.”**

**Usually:** Conserved catalytic residues support a functional assignment;
their apparent loss challenges it. **Exception/context:** Curators checked
alignment errors and substitutions, accepting some nonconservative changes
after literature analysis. Repeated names also shared errors.

**Proposed judgment:** Distinguish wrong alignment, mechanism-compatible
substitution, another activity and inactive protein. Re-align against
authenticated representatives and inspect the mechanistic position. Changed
correspondence revises the alignment interpretation; compatible chemistry can
retain a qualified function. Persistent incompatibility weakens the specific
activity hypothesis while preserving broader family support and alternatives.
None of these outcomes deletes the sequence.

**Limit:** The study concerned selected, experimentally characterized enzyme
families. Its historical error frequencies are not present-day universal rates.

### 2. A missing familiar gene can indicate a different biological solution

**Source:** Overbeek et al. (2005), *The Subsystems Approach to Genome Annotation
and its Use in the Project to Annotate 1000 Genomes*.
[Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC1251668/),
[full-text XML mirror used when the PMC page was inaccessible](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1251668/fullTextXML).
Read **“What is a subsystem,” “A framework for developing a precise vocabulary
for functional roles,” “Example populated subsystems” → Coenzyme A biosynthesis,
Figure 4, and “The impact of populated subsystems.”**

**Usually:** A missing familiar enzyme suggests an incomplete pathway.
**Exception/context:** CoA analysis distinguished nonorthologous kinase forms;
some CoaX-like proteins carried misleading labels. Buchnera's pathway pattern
instead motivated a host-intermediate-exchange hypothesis.

**Proposed judgment:** Compare missed gene, alternative family, assembly absence,
salvage and host dependence. Inspect alternative families and pathway context;
compare available completeness and physiology. Another implementation revises
the role-to-gene mapping. A sequence gap weakens an absence claim. A retained
truncated pathway motivates a dependence hypothesis, not a proved nutritional
requirement. Context can redirect investigation without forcing a missing
function into an existing family.

**Limit:** The host-exchange account and archaeal kinase candidates were
hypotheses in that historical paper, not permission to assert their present
status or infer growth requirements without additional evidence.

### 3. A broken protein can be a broken interpretation of the sequence

**Source:** Pati et al. (2010), *GenePRIMP: a gene prediction improvement pipeline
for prokaryotic genomes*.
[Published paper](https://www.nature.com/articles/nmeth.1457),
[author manuscript and methods](https://digital.library.unt.edu/ark:/67531/metadc846465/m2/1/high_res_d/1032520.pdf).
Read **main comparison of Methanosphaerula palustris and Mycobacterium;
Online Methods → “Detection of broken genes,” “Detection of frameshifts,” and
“Detection of pseudogenes.”** The accessible manuscript includes editorial
comments; it is identified as that version rather than presented as a current
curation standard.

**Usually:** Adjacent fragments covering consecutive portions of one homolog
suggest a split gene. **Exception/context:** Real splits/fusions, assembly
errors, transposon interruptions and recoding can produce related observations.
The manuscript distinguishes a single frameshift compatible with ribosomal
slippage from an unqualified pseudogene assignment.

**Proposed judgment:** Compare continuous translation, separate genes,
biological disruption and sequence error. Inspect intervening sequence,
alignment correspondence and supplied reads. A supported continuous frame
motivates a boundary revision; persistent disruption supports a disrupted-locus
hypothesis. Without discriminating evidence, retain uncertainty about the cause
rather than repairing bases or declaring functional loss.

**Limit:** Similarity-based anomaly detection and curator agreement do not
experimentally establish the cause of a disruption.

### 4. The translation assumptions can be the biological uncertainty

**Source:** Ivanova et al. (2014), *Stop codon reassignments in the wild*.
[Published-paper PDF](https://www.scienceintheclassroom.org/sites/default/files/research-papers/stop_codon_reassignments_in_the_wild.pdf),
[bibliographic record](https://pubmed.ncbi.nlm.nih.gov/24855270/).
Read **Science pp. 909–912, Figures 1–3, and p. 913 qualification of the proposed
phage-host mechanism.**

**Usually:** Internal stops suggest truncation or disruption. **Exception/context:**
Alternative-code comparisons and alignments supported UGA-to-glycine
interpretation in SR1/Gracilibacteria. Associated phage sequences could use
different codes.

**Proposed judgment:** Compare isolated disruption, wrong code, local recoding
and mixed provenance. Ask whether one alternative restores conserved positions
across unrelated genes, and whether translation machinery and membership agree.
Broad consistent restoration favors a code hypothesis; an isolated anomaly
favors local investigation. Contradictory membership motivates separating
associated sequences. Preserve the original sequence and explicit code-specific
products rather than silently rewriting caller metadata.

**Limit:** This survey found no archaeal stop-codon reassignment. Its proposed
phage interference mechanism still required direct in-vivo observations.

### 5. A surprising repertoire can reflect sample composition

**Source:** Orakov et al. (2021), *GUNC: detection of chimerism and contamination
in prokaryotic genomes*.
[Full article](https://link.springer.com/article/10.1186/s13059-021-02393-0).
Read **Results → “GUNC estimates genome quality based on contig homogeneity
using the full complement of genes,” “GUNC accurately quantifies genome
contamination in multiple simulated scenarios,” HGT section, Figure 3, Discussion.**

**Usually:** Discordant taxonomy suggests contamination. **Exception/context:**
Poor reference representation can cause inconsistent labels; some Salmonella
calls reflected plasmid-related reference artifacts.

**Proposed judgment:** Compare mixed sample, genuine transfer/mobile element,
mis-binning and reference failure. Examine whether disagreements follow contig
boundaries, available read linkage and reference representation. Segregation
supports a membership problem without identifying its laboratory cause.
Integrated discordant material supports another explanation. Diffuse labels
with poor representation leave novelty unresolved. Reconsider which sequences
support the organism-level repertoire; do not discard the entire input or turn
a diagnostic cutoff into an annotation permission check.

**Limit:** GUNC does not estimate completeness; closely related mixtures and
cases where both source lineages are outside the reference remain problematic.
The paper's filters are not proposed as workflow admission gates.

### 6. Structure can change the question without determining the answer alone

**Source:** Hermann et al. (2007), *Structure-based activity prediction for an
enzyme of unknown function*.
[Author-hosted published PDF](https://www.chem.tamu.edu/rgroup/raushel/publications/P228-Nature-Activity%20Prediction-2007.pdf),
[article](https://www.nature.com/articles/nature05981).
Read **“Docking metabolites as high-energy intermediates,” “Experimental testing
of the predicted substrates,” Table 2, “Metabolic pathway of a family of
MTA/SAH deaminases,” and “Predicting function from form.”**

**Usually:** A compatible active site or docking pose supports a substrate
hypothesis. **Exception/context:** Tm0936 initially resembled a broad
cytosine-deaminase group. Assays supported MTA/SAH/adenosine activity, while
relatively well-ranked AMP was inactive.

**Proposed judgment:** Distinguish binding compatibility, catalytic activity
and physiological role. Consider reaction chemistry, alternative substrates and
assay conditions when choosing a test. Positive turnover strengthens activity
under those conditions; a negative test weakens that substrate/condition pairing.
Neither alone settles the organism's pathway role. Contextual and downstream
evidence can motivate physiological testing while retaining alternatives.
Structure guides the next test without determining the answer alone.

**Limit:** One successful structural case does not validate general docking or
prove an enzyme's physiological role from in-vitro activity alone.

## Proposed information responsibilities

The following is an engineering proposal informed by the cases, not a claim that
any paper implements this system. These records are ingredients available to an
investigation. They are not mandatory processing stages or predetermined child
Episode types.

| Semantic object | Required information | What its consumer can reason about |
| --- | --- | --- |
| Biological subject | Stable identity; organism/sample association; observed sequence and version; genomic location; structural/translation hypothesis. | Whether two observations concern the same candidate and whether their contexts are comparable. |
| Functional hypothesis | Subject; proposed activity/role; level of specificity; relevant substrate/product or complex; alternatives; scope of the claim. | Competing substrate, family, mechanism and physiological-role explanations without hiding them in one product name. |
| Reference claim | Exact source/version/sequence; source-assigned meaning; cited experiment if present; assay organism/conditions; derivation links. | Whether a label is an experiment, a transfer, an inference, a broad family description or a copied predecessor. |
| Sequence comparison | Query/reference products; transformation; actual alignment and coverage; query/reference coordinates; domain correspondence; conditions and reference collection. | Whether apparent similarity spans the discriminating region or merely a common domain. |
| Residue observation | Comparison/coordinate mapping; expected mechanistic role; observed residue or missing alignment; uncertainty in positional correspondence. | Substitution versus missing sequence versus alignment error; mechanism-compatible exceptions. |
| Evolutionary hypothesis | Homolog collection and selection scope; alignment/tree assumptions; duplication/speciation/transfer alternatives; support and unresolved relationships. | Whether a putative ortholog actually separates from relevant paralogs. A best hit is not stored as a proved ancestry relationship. |
| Architecture/structure interpretation | Domain spans/order; fusion/split alternatives; model or experimental structure identity; local confidence; pocket/ligand/mechanistic correspondence. | Whether fold, active site and substrate recognition support the same hypothesis. |
| Comparative context | Actual neighbors, distances/orientations, contig boundaries; comparison genomes; observed co-occurrence/fusions; provenance of neighboring annotations. | Functional coupling, alternative pathway implementations, and where a contextual argument is circular. |
| Negative observation | Exact attempted test/search; eligible references/substrates; coverage/sensitivity/conditions; returned result; unexamined alternatives. | What was not found under specified conditions, without asserting universal biological absence. |
| Organism interpretation | Membership/lineage hypotheses; metabolic roles and pathway alternatives; environmental/host context and its provenance; observed physiology separately from prediction. | Whether local assignments form a coherent organism interpretation and which contradictions deserve work next. |
| Investigation change | Earlier and revised hypothesis relationships; new supporting/conflicting evidence; uncertainty changed or retained; dependencies affected. | What improved, what remains unresolved, and why another comparison or observation might help. |

These objects need typed semantic identities and relations. A name, accession or
published paragraph alone cannot substitute for its asserted meaning. In
particular, `same_sequence`, `same_family`, `same_reaction`, `same_substrate`,
`same_physiological_role` and `same_organism` are distinct relationships.

## Small reasoning tasks and what they return

This is a working map of responsibilities. It does not decide which task
becomes a child Episode: a responsible Episode may own several such judgments
and ordinary tools, revise them over iterations, and delegate when useful.

| Reasoning responsibility | Context it needs | Useful result for the next decision |
| --- | --- | --- |
| Decide what can transfer from a homolog | Exact assertion, source/experimental lineage, aligned regions, relevant paralogs and proposed specificity. | Which parts of the assertion are supported, weakened or unexamined; alternatives and their actual evidence. |
| Explain a mechanistic discrepancy | Residue correspondence, sequence completeness, chemical role, structure/assay conditions and plausible exceptions. | Competing explanations, evidence that separates them, and unresolved assumptions. |
| Decide whether context changes a local interpretation | Neighborhood membership, pathways and alternative implementations, organism/sample hypotheses and contextual uncertainty. | Revised connections with explicit dependencies, rather than a forced pathway completion. |
| Choose a discriminating next observation | Live alternatives; what different test outcomes would mean; available observations and practical constraints. | A selected useful tool action or delegated investigation, with its biological question and intended distinctions. |
| Interpret a new outcome | Actual returned observation, tested conditions, prior competing explanations and applicability limits. | A specific revision or justified retention of uncertainty, linked to the observation. |

The model reasoning owns those scientific interpretations and choices of useful
work. Numerical yield estimation owns continuation. Infrastructure represents
and executes selected work, retains observations and dependencies, and enforces
declared communication types. It must not convert a defeasible consideration
into a hidden scientific decision.

A new interpretation need not already have a familiar database name. It can
have a provisional semantic identity with structured reaction/role components,
relationships and evidence. An unrecognized function is not an invalid result.
The parent form can refer to new in-scope hypotheses and their declared
meanings through registered semantic records; a fixed list of known product
names must not close the scientific hypothesis space.

## What may need to communicate

This is a rough working map of information movement, not an Episode topology.
One investigation may perform several of these reasoning activities itself, or
delegate a substantive question when that is useful under the method.

- A local sequence interpretation supplies the exact candidate translation to
  comparison. Comparison can return a boundary contradiction that motivates
  another sequence interpretation. It must not silently edit the underlying DNA.
- A function question supplies **competing possibilities and what distinguishes
  them**, not just a query protein and desired final name. A comparison returns
  observations whose subject, coordinates and specificity remain explicit.
- A comparative argument supplies candidate relationships to organism-level
  interpretation. The latter can expose an unexplained reaction, implausible
  duplication, environmental mismatch or potential sample-composition problem
  that motivates returning to the local evidence.
- Whole-organism context can motivate a targeted search for a missing role.
  The targeted search reports its actual scope and outcome. Neither the
  expectation nor its failure manufactures a gene or proves an auxotrophy.
- The responsible investigator may ask for published physiology, raw reads,
  broader taxonomic comparisons, a structural calculation or a discriminating
  experiment. Availability is recorded separately from its biological result.

When a parent delegates, it chooses which typed information would improve its
next decision. Useful form ingredients could include hypothesis references,
new/unchanged relationship references, supported specificity, positive and
counterevidence references, comparison coverage, unresolved alternative codes,
and unavailable evidence kinds. There is no universal report requiring all of
them, and the child does not issue unrestricted instructions to its parent.
Deterministic observations come from the actual work; interpretations remain
the investigator's interpretations.

## Reuse and dependency relationships

Reuse should follow what a result actually depends on. This is a proposed state
design, not a new approval mechanism.

| Change | What needs a new interpretation or calculation | What can remain usable |
| --- | --- | --- |
| Candidate start or translation changes | Comparisons/structure predictions that used the changed product; claim applicability to that product. | Immutable original observations, source records, and comparisons of unchanged products. |
| Functional label changes in an external record | Claims transferred from that label and affected lineage relationships. | The original sequence alignment when both sequences and algorithm remain unchanged. |
| A broader homolog collection is acquired | New coverage of paralogs/lineages and any interpretation relying on the earlier sampling boundary. | Existing individual alignments and their original scope. |
| A mechanistic exception or new assay is retrieved | Interpretation of relevant residue/function/substrate hypotheses. | The observed residue identities and prior assay provenance. |
| Contig membership changes between organism hypotheses | Organism-specific repertoire, neighborhood/pathway conclusions and contextual support. | The sequence, alignment and source observations as observations. |
| A code hypothesis changes | Translations and downstream analyses that actually depend on that code. | The original assembly and alternative code-specific products as labelled hypotheses. |
| New growth/environment evidence is obtained | Physiological-role or pathway/host-dependence interpretation under those conditions. | Source-bound evidence under its original conditions. |

A new interpretation must not retroactively turn a prediction into an
experiment. Several databases repeating a label must retain their dependency
where known; unknown lineage is recorded as unknown rather than presumed
independent. Conversely, an unrelated metadata edit does not invalidate an
unchanged alignment.

## Real context and tools an investigator may need

The concrete needs are to **read and compare evidence**, not merely to run more
annotation programs. They include access to experimental papers and curated
records; alignments with residue/domain coordinates; representative homologs and
paralogs; neighborhoods across selected genomes; raw sequence and, when supplied,
underlying reads/assembly linkage; structures and mechanistic calculations; and
organism/sample/physiology records with their conditions.

An unavailable experiment or missing reads is useful limiting information. It
should leave the investigator able to improve other aspects of the annotation.
It does not reject the genome, require a human approval stage or add a new
stopping condition. A fully specified lookup or calculation is an ordinary tool
call; owning a revisable biological question can involve iterative decisions.
The method's numerical yielding remains separate from whether that question
has a final biochemical answer.

## Remaining uncertainty

- These six sources do not establish exact growth media, temperature, pH,
  handling conditions or substrate utilization for a newly supplied organism.
  That requires organism-specific physiology and experimental context, not an
  inference from a familiar pathway label alone.
- Data limitations must distinguish absence of a biological feature from an
  incomplete assembly, insensitive comparison, unrepresented lineage, wrong
  translation hypothesis, unavailable experiment and contaminated input.
- A broad but well-supported interpretation, a useful counterexample, or an
  unresolved alternative with a discriminating next investigation can improve
  understanding. A more specific asserted name can make understanding worse.
- This report does not resolve how each of those changes maps to the user's
  softened-hypervolume credit. Evidence semantics and independence must be clear
  before defining what each component measures; activity and repeated labels
  cannot stand in for improved evidence.
- The source papers contain workflows and historical numerical filters. Those
  have not been adopted as this system's gates, compulsory action order,
  scientific stopping rules or definition of an Episode.
