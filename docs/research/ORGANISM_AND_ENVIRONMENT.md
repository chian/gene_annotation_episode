# Organism, environment, and physiology as annotation investigations

Research and rough architecture, 2026-10-19. This document addresses replacing
biological judgments made by a human annotator. It specifies questions and
information relationships, not an implementation, mandatory pipeline, list of
required episode types, stopping rule, quality gate, or credit revision.

## What the investigation is trying to explain

An annotation should explain what the particular organism could do, under which
conditions, and which genes could account for that behavior. An assembly alone
does not establish the organism's physiology. A coherent biological account can
include genuine dependency, incomplete knowledge, conflicting observations,
unknown enzymes, and functions performed by another organism.

Organism-level reasoning and gene-level reasoning must revise one another. An
unexpected phenotype can make a weakly annotated protein worth investigating;
a revised enzyme interpretation can invalidate a previously attractive pathway
explanation. Neither direction makes an expectation into an observation.

The research below supports **defeasible judgments**: a usual inference, reasons
it may fail, observations that distinguish competing explanations, and changes
in the next useful investigation. These are the units around which iterative
reasoning should be organized. A search, calculation, or source retrieval used
by such an investigation remains an ordinary tool call.

## Primary studies read and what they establish

Relevant results and methods were read, rather than using search-result snippets.
For the two studies retrieved through Europe PMC XML, this was the primary
article's full text, not a generated summary. Historical claims are attributed
to the study; they are not universal rules for an entire lineage.

### SAR11: a plausible metabolic bypass did not establish prototrophy

Tripp and colleagues tested *Pelagibacter ubique* after an earlier reconstruction
had proposed a threonine-aldolase bypass for missing serine-biosynthesis genes.
Growth supplementation supported conditional glycine/serine dependence. Filtered,
autoclaved seawater still contained small quantities of those nutrients, making
unsupplemented growth an unreliable test of biosynthesis. A glycine-binding
riboswitch upstream of malate synthase linked nutrient availability to regulation;
the proposed regulatory explanation remained distinct from direct binding and
growth measurements. Different carbon-source conditions also changed responses.
[Tripp et al., 2009, results and experimental procedures](https://pmc.ncbi.nlm.nih.gov/articles/PMC2621071/).

### MK-D1: community input is not the target organism's substrate

Imachi and colleagues cultivated *Prometheoarchaeum syntrophicum* MK-D1 from an
anaerobic, methane-fed enrichment. Cultivation, isotope uptake, and partner
perturbation supported amino-acid degradation with syntrophic partners; elevated
hydrogen or formate suppressed growth. Long lag and doubling times affected how
negative cultivation observations could be interpreted. Their manual curation
used family-specific evidence and phylogenies for enzymes whose activities were
not resolved by sequence similarity alone. Several metabolite exchanges in the
reconstruction remained predictions, not individually measured transfers.
The proposed hydrogen-generating role of an MvhADG–HdrABC complex illustrates
why a familiar enzyme-family assignment does not settle physiological direction.
[Imachi et al., 2020, cultivation, physiology, and genome-analysis methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC7015854/).

### Nanoarchaeum: missing biosynthesis and split genes can be real biology

Waters and colleagues investigated a closed *Nanoarchaeum equitans* genome from
cells cultivated with an *Ignicoccus* host. Broad biosynthetic absences were
interpreted with the known association, rather than filled with invented genes.
Two distant coding regions encoding parts of alanyl-tRNA synthetase reconstituted
activity together in an assay. Other split functions and missing tRNAs had
multiple proposed explanations with unequal experimental support. The paper
explicitly left important bioenergetic and exchange mechanisms unresolved.
[Waters et al., 2003, primary paper PDF, methods and results](https://rcn.montana.edu/Publications/Pdf/2003/Nanoarchium%20genome.pdf).

### GUNC: contradictory lineage signals require source-ownership reasoning

Orakov and colleagues examined contamination using gene assignments distributed
across contigs. An *Aerococcus urinae* assembly included an *Afipia*-like component
on many small contigs. Their analysis also exposed plausible plasmid-related
misclassification and limitations when reference lineages were missing. Thus a
foreign-looking function can reflect contamination, real transferred material,
or a misleading reference classification. A marker inventory or taxonomic score
alone does not settle which organism owns a proposed metabolic capability.
[Orakov et al., 2021, results, limitations, and methods](https://link.springer.com/article/10.1186/s13059-021-02393-0).

### eQuilibrator: reaction feasibility depends on explicit chemical assumptions

Beber and colleagues describe thermodynamic estimates with correlated uncertainty,
chemical-identity mapping, magnesium/protonation adjustments, and transport across
compartments with different conditions and membrane potentials. Their 3.0 paper
lists temperature adjustment as future work, so it cannot authorize assuming
room-temperature estimates describe an extreme habitat. Thermodynamic calculations
can challenge a proposed route under stated conditions; they do not establish
that a gene encodes the required enzyme or that the organism uses that route.
[Beber et al., 2022, primary article](https://doi.org/10.1093/nar/gkab1106),
[primary full-text XML read](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8728285/fullTextXML).

## Small reasoning tasks and their revision traces

The following are proposed investigations inferred from the studies. Their
boundaries follow the biological question. They may stay within one episode or
be delegated when a parent needs a substantive sub-investigation. They do not
require creating a new episode for every consideration or test.

| Reasoning question | Usual inference to consider | Why that inference can fail | Competing explanations | Next discriminating work | How an outcome changes interpretation |
| --- | --- | --- | --- | --- | --- |
| Does growth establish biosynthesis of a missing nutrient? | Growth without supplementation suggests endogenous synthesis. | The medium, inoculum, a companion, or the handling process may supply it. Growth also depends on the carbon and energy conditions. | Missed enzyme; active alternative route; scavenging; carryover; partner supply; condition-dependent demand. | Read the exact medium and handling history, quantify what was actually measured, compare relevant supplementation/depletion observations, and ask the gene investigation about specific candidate routes. | A supplied nutrient weakens the biosynthesis inference; evidence for an alternative enzyme redirects the locus investigation; missing measurements leave conditional alternatives. |
| Can this weak enzyme assignment close the pathway gap? | A related enzyme or family member may provide the missing reaction. | Broad family membership does not establish substrate, cofactor, direction, regulation, or sufficient activity. | Correct alternative route; promiscuous activity insufficient for growth; different family function; unknown replacement; genuine auxotrophy. | Compare characterized family members and discriminating residues/architecture, inspect organism-specific context, and obtain condition-relevant activity or phenotype observations when available. | Retain a broad family assignment when specificity is unresolved; revise the route hypothesis instead of forcing a specific label. |
| Which organism performs the observed transformation? | A substrate in the enrichment or a product in the bottle belongs to the focal organism's metabolism. | A community can transform the input before the focal organism uses it; a partner can remove products or provide nutrients. | Direct use; partner conversion; syntrophic product removal; environmental crossfeeding; wrong attribution of sequence or phenotype. | Reconstruct sample/organism identities, inspect partner genomes and experimental separation, compare target-specific uptake/expression with community-level measurements, and examine perturbations. | Split the community process into organism-owned contributions; revise which genes need explaining and which partner dependencies remain hypothetical. |
| Is an incomplete energy chain a missing-gene problem? | A familiar respiratory or biosynthetic route should have its canonical components. | The route may be irrelevant under the observed condition, use different chemistry, run in the other direction, or depend on a partner. | Annotation miss; different electron carrier; alternative coupling; unmeasured concentrations; different growth mode; true dependency. | State the carbon source separately from electron donor/acceptor, identify reaction and compartment assumptions, and test feasible conditional routes without adding genomic claims. | A conditional inconsistency directs a targeted gene or chemistry question. It does not delete a gene or require the route to exist. |
| Are fragments damaged genes or functional parts? | A homolog split between regions is a pseudogene, assembly error, or failed caller. | Some systems use separately encoded subunits, processing, or unusual RNA/protein organization. | Assembly error; recent disruption; missed boundaries; distinct functional subunits; processing-dependent function. | Ask sequence/assembly reasoning about read and boundary support, gene reasoning about conserved domains and complementary parts, and organism reasoning whether the relevant function is independently supported. | Preserve the original regions; revise the proposed product relationship. A distant complementary part changes the next search, while an unsupported join stays hypothetical. |
| Does a surprising metabolic gene belong to this organism? | A taxonomically discordant sequence is contamination, or a novel metabolic capability. | Genuine transferred/mobile material and sparse references can produce similar signals; a mixed sample can be assembled or binned incorrectly. | Contamination; mis-binning; misassembly; genuine transfer; plasmid; reference misclassification; unresolved lineage. | Compare contig-wide context, coverage/linkage, sample processing, independent lineage markers and available assemblies, while checking reference representation. | Reassign the biological claim's subject or keep ownership unresolved. Source sequence is preserved; a taxonomic score does not automatically remove it. |

Within its immutable EpisodeGoal and assigned scope, an investigation can revise
its working explanations and select different follow-up questions. A suspected
missing enzyme may lead it to examine transport, cofactors, or whether the
phenotype was measured in the target organism. The episode owns those scientific
choices within its assignment; they do not redefine its goal, target, scope or
credit policy. An actual change of scientific goal or scope belongs to the parent
through a new commission. This distinction preserves ownership; it adds no gate,
runtime fallback or prescribed stage.

## Information the reasoning needs

### Keep source facts, observations, and hypotheses separate

A **source fact** records what was supplied or reported: sequence bytes, strain
identifier, sample accession, a medium recipe, an assay record, or a publication's
assertion. Its authenticity does not make every interpretation in that source
biologically correct.

An **observation** has a subject, measured property, method, condition, result,
units, detection limit when known, and provenance. For example, growth of a
mixed culture and uptake by identified target cells are different observations.
An assertion that a paper found a gene missing remains a reported search result
with that search's scope; it is not automatically a new exhaustive absence result.

A **hypothesis** connects named subjects and conditions: a gene could catalyze a
reaction, a target could depend on a partner, or a contig could have another
origin. It carries the observations and assumptions on which it depends,
competing hypotheses, and its current interpretation. An attractive explanation
is not relabelled as an observed mechanism.

The DNA and source records stay fixed. Inferred physiology, environmental role,
function, sequence ownership and ancestral explanations remain revisable.
Imported genetic-code or taxonomic assertions need their source identity; an
inference investigation must be able to question them without silently rewriting
the supplied source or treating an organism's label as proof of its physiology.

### Context is attached to a particular strain, sample, and condition

The reasoning needs structured identities for field sample, enrichment, isolate,
passage or time point, focal population, sequence preparation, assembly and
annotation revision. A description from another strain or a community-level
sample cannot silently become a phenotype of the target strain.

Potentially relevant context includes environmental location and time; physical
association; medium composition and preparation; measured residual substrates;
inoculum carryover; gas/headspace conditions; temperature; pH; salinity; oxygen
exposure; incubation duration; collection/preservation/extraction history; and
available negative controls. These are information needs to investigate when
relevant, not mandatory fields that must be filled before annotation proceeds.
Unknown values remain unknown. A habitat descriptor is evidence about possible
conditions, not a measured intracellular concentration.

### Energy, carbon, nutrients, and chemical identity are different questions

A proposed physiological explanation should identify which compounds supply
carbon, reducing equivalents and nutrients, and what can accept electrons or
remove products. A proposed reaction must distinguish substrate identity,
cofactor, compartment, direction and coupling assumptions. A plausible gene
family cannot supply all those distinctions by name alone.

A calculation can expose the importance of an unknown concentration, pH,
membrane potential, or reaction identity. It should return conditional results
and sensitivity to those assumptions. If a chemical structure, equilibrium
estimate, kinetic fact or relevant extreme-condition correction is unavailable,
the result stays limited. Feasibility under one assumption set does not establish
actual flux, enzyme expression, sufficient capacity, or growth.

## Dependencies between the reasoning tasks

These are exchanges of information, not fixed episode classes or a required
execution order. The responsible investigation chooses which dependency matters
next and can revise that choice after receiving its requested form.

| Investigation needing information | Question it sends to another investigation | Useful constrained result | What it can decide afterward |
| --- | --- | --- | --- |
| Organism/growth interpretation | Which sample and population does this phenotype actually describe? | Registered subject and condition references; measured-versus-reported origin; mixed/target-specific/unresolved attribution. | Which observations can bear on the focal organism. |
| Metabolic-route interpretation | Is the proposed missing reaction unsupported because of a gene-model or family-specificity problem? | Candidate and reaction references; covered domains/sites; conditional support/conflict/unresolved relation; unexamined alternatives. | Whether to search a locus more deeply, compare an alternative route, or retain a genuine dependency hypothesis. |
| Gene-function interpretation | Under which observed conditions would these candidate activities explain a target phenotype? | Condition/reaction/phenotype references; observed-versus-predicted applicability; supporting and opposing observation references. | Which substrate/cofactor distinctions are worth resolving; it cannot promote expected pathway membership into an assay. |
| Energy/chemistry interpretation | Are the reactants, compartments, exchange possibilities and chemical assumptions defined well enough for this calculation? | Chemical/reaction/condition references; explicit unknowns; estimates and units; scope of any conditional inconsistency. | Whether a calculation is informative, which assumption dominates, or what evidence modality is missing. |
| Sequence-ownership interpretation | Could the unusual gene reflect a partner, mobile element, or assembly assignment? | Contig/region and source-population references; linkage/coverage/reference-representation observations; scoped ownership alternatives. | Whether the physiological claim belongs to the target, a partner, or an unresolved source. |
| Comparative/evolutionary interpretation | Is the pattern conserved in appropriate relatives, and how were those relatives selected? | Named reference set; comparable conditions where known; orthology/paralogy/transfer alternatives; presence/search-absence observations. | Whether an analogy is informative or may be distorted by reference sampling, convergent function, or lineage-specific loss. |

The parent's form can ask for particular fields from these semantic results. For
example, an organism investigation might request a reaction reference, candidate
references, condition references, supporting/opposing observation references and
an enum describing whether specificity is unresolved, supported under the stated
condition, or contradicted by the cited test. The parent already knows what those
fields mean and uses them to choose its next action.

A child does not send an unrestricted biological essay, direct instructions to
the parent, or a numerical confidence it invented to persuade the parent. Its
private reasoning may be extensive. The crossing boundary carries the requested
structured meanings, including useful unresolved dependencies. New hypotheses
can be registered as typed propositions rather than smuggled into a findings
paragraph. The exact contract is a later design responsibility.

## What was missing from the earlier documents

The archived [biological-method design](../../_superseded/2026-10-19-genome-runner/docs/BIOLOGICAL_METHODS.md)
correctly preserved alternatives and warned against manufacturing pathway genes.
It concentrated on callers, boundaries, RNA models, homology and local context.
It did not develop a working account of condition-specific organism physiology,
sample and culture history, target-versus-community attribution, energy and
chemical assumptions, or the small judgments that exchange information between
those questions. The table of examples primarily selected another sequence tool.
The replacement design should make these biological judgment traces central.

The archived [credit design](../../_superseded/2026-10-19-genome-runner/docs/CREDIT_AND_YIELD.md)
correctly separated source-bound evidence from persuasive reports and retained
signed corrections and local action accounting. Its concrete initial projection
emphasized positive support on genomic intervals; it did not explain how a
condition-specific physiological interpretation, a well-supported refutation, or
corrected source ownership would be represented as scientific progress. That is
a gap to resolve in the overall design, not authorization here to add scores,
weights, gates or an extra controller.

## Scientific limits and responsibility

A universal complete-metabolism template would erase the very phenomena these
investigations need to understand. A familiar pathway gap is a question, not a
requirement to fill the gap. A novel environment permits more alternatives and
makes source/reference limits more important; it does not justify a confident
story about an unmeasured adaptation.

Evidence that narrows or changes a claim can be useful even when the resulting
annotation is less specific. Explanation text, additional hypothesis names,
apparent pathway completeness, and an untested growth prediction do not by
themselves constitute stronger evidence. Existing evidence reused by several
reasoning tasks keeps the same source identity.

The reasoning episode owns scientific judgment and revision. The runtime executes
selected work, preserves source relationships and communicates the requested
forms. The numerical yield estimator/controller owns scientific continuation.
An unanswered biological question is neither a quality gate nor permission for
infrastructure to decide the organism's biology. No requirement to complete all
of these investigations follows from this rough architecture.
