# A108 numerical subscoring sheets and exact communication

Proposed specification, 2026-11-05 UTC. This document is not a claim of an
implemented or validated workflow. No workflow, test, Python command, external
source search, or biological analysis was run to write it.

The previous `A108_SCIENTIFIC_SHEET_PLAN.md` described fit relations but omitted
the numerical evidence assessment. This document supplies that assessment.
A105 provides receipt, reader, subscoring-sheet, and main-sheet mechanics;
A108's scientific criteria are defined below for its own observations.

## 1. Controlling user instructions and the score's meaning

The recovered original instructions explicitly define A108 as a literature
assessment: “This is a pseudo-grader/literature reading exercise — does the
proposed function seem plausible given what we know about the sample and the
organism?” They also require measurable terms that can compile a score and
reject freehand words in place of scores. Original witnesses are
`/home/chia/.codex/history.jsonl:4879` and `:5157`; the deduplicated audit stores
these as events 4898 and 5180. They do not require every contextual observation
to provide experimental variance or a likelihood model.

The later withdrawal of arbitrary category grades remains controlling too:
`CATEGORY_SCORE_WITHDRAWAL_2026-10-23_001.md` rejects turning broad quality words
into arbitrary 0/0.25/0.5/1 or 0–3 grades. A count of explicitly identified
observations has an actual measurable unit. It is not an ordinal opinion score.

The primary A108 numerical quantity proposed here is:

> **The number of distinct source-grounded contextual observations that have
> been assessed as supporting or conflicting with a candidate's contextual
> claim within the declared organism/sample circumstances.**

The target's actual organism/context must be established from supplied or
received evidence. A chosen gene name, hypothesized function, or interesting
organism in a paper cannot supply that identity. Without a supported target
organism/context relationship, a discovered source observation remains an
unresolved source lead for this annotation and cannot enter its support or
conflict sets. A source observation about a different organism is usable only
through an explicit, scientifically supported transfer to the actual target.

Each observation is assessed with the purpose-specific criteria below before it
enters the corresponding set. The count measures the amount of assessed
contextual evidence. It is not a probability of correct annotation, a citation
popularity score, a statistical likelihood ratio, or a grading of how convincing
the prose sounds. Support and conflict counts remain separately visible.

Native numerical measurements and supported statistical comparisons also remain
available as their own scientific components. They are not silently added to
observation counts. For example, one measured concentration, its uncertainty,
and a derived contrast are three components of one observation, not three new
pieces of evidence.

## 2. Exactly what gets counted

The counted item is an **original contextual observation**, selected for a
particular candidate and contextual question. Its identity includes the source's
actual scientific observation or experiment, studied subject, endpoint/property,
sample/condition and comparator where relevant. It is not a sentence, parsed
row, quoted passage, report field, file, database hit, paper title, or action.

Examples of one counted item include an organism's observed growth response in
a specified resource comparison; a sample's measured oxygen condition; a
chemically identified substrate observation in a stated compartment; or a
localization observation for the actual molecule/construct. The custom grader
must establish how that observation bears on the candidate's contextual claim.

Counting rules:

- A paper and its database representation retain the same original observation
  identity. Retrieving both does not create a second contribution.
- Repeated sentences, table rows, figure panels, or derived quantities describing
  the same comparison remain one observation. Technical replicates do not become
  individually scored observations merely because they occupy separate rows.
- A genuinely separate source experiment can contribute another observation.
  Distinct identifiers alone do not establish distinct underlying data.
- A strain panel can contain distinct strain-specific observations, but each
  selected strain must have a scientifically justified connection to the
  commissioned organism/sample question. Every row is not automatically relevant.
- The same outside observation can inform multiple contextual relations or
  domains. Its identity is shared, and it contributes once to the overall
  evidence amount.
- An A105 finding establishing an oxygen requirement is an input to the A108
  comparison. It is not a second outside observation alongside the measured
  sample oxygen condition.
- An existing source observation delivered from another axis is reused with its
  original identity and qualifications. A108 does not manufacture a new original
  experiment by saving its own contextual assessment.
- An unsupported annotation repeated in a database or paper is a lead, not an
  observed contextual fact. A direct curated observation with actual source
  provenance can qualify; full-paper reacquisition is not automatically required
  when the needed original observation is already delivered.
- Search failure or missing metadata is not a biological observation of absence.

The assessment can identify support, conflict, or a particular unresolved
connection. These relations are scientific classifications used to select
explicit observation sets; they are not numeric strength ratings.

## 3. Numerical cells in each purpose-specific subscoring sheet

For a saved sheet, let:

```text
S = distinct original_observation_refs in its eligible support relations
C = distinct original_observation_refs in its eligible conflict relations
U = distinct original_observation_refs in its unresolved relations
```

The deterministic cells are:

```text
support_observation_count    = |S|
conflict_observation_count   = |C|
overlap_observation_count    = |S intersection C|
evidence_amount             = |S union C|
                            = support_observation_count
                            + conflict_observation_count
                            - overlap_observation_count
net_support_count           = |S| - |C|
unresolved_observation_count = |U|
```

All count cells have unit `distinct_contextual_observations`. The primary
evidence score is `evidence_amount`. `net_support_count` is a separate directional
summary. An observation supporting one relation and conflicting with another
is visible in both directional sets but contributes only once to the amount.

U can overlap S or C: an established narrower relationship must survive an
unresolved broader one. For example, the substrate can be measured in a sample
while access to the enzyme's compartment remains unresolved. The valid
availability observation remains available; no additional evidence is awarded
for merely recording the unresolved access question.

Zero means an evaluated selection has no eligible observations in that set.
Missing sources, unavailable readers, or incomplete assessment are not asserted
to establish biological absence. The sheet carries selection/completion status
and exact missing inputs separately. It does not declare complete investigation
coverage from an empty or nonempty count.

There is no mandatory list of all physiological requirements and no denominator
of presumed requirements. No coverage fraction, target capability graph,
normalization to 0–1, score cap, or weighted missing-condition penalty is added.

## 4. Purpose-specific scientific sheets and graders

Each entry below defines a separate scientific contract. The arithmetic in
section 3 can be shared, but a common `context_measurement` rubric cannot
replace these field meanings and criteria.

### 4.1 Organism resource-response subscoring sheet

**Counted observation.** A stated organism/strain's resource-related response
under an identified culture condition and comparison. Growth rate, biomass
yield, survival, and a qualitative observed growth call retain their endpoint.

**Reader must supply.** Organism/strain; actual resource and chemical form;
sole versus supplementary nutrient; culture/medium and state; endpoint/time;
comparison and source result; biological versus technical replication where
reported; original source observation identity. Native values/uncertainty are
retained when available, but a documented qualitative result is not discarded
because it lacks a numeric sampling model.

**Support criterion.** The observed response establishes a physiological
behavior compatible with a source-grounded role of the proposed function in
the stated organism/conditions. The actual biological connection is identified;
growth is not automatically assigned to this gene or reaction.

**Conflict criterion.** The observation contradicts a source-established
physiological implication of the proposed function under the conditions where
that implication is claimed. Failure to grow does not conflict automatically
when other required nutrients or conditions are missing.

**Unresolved cases.** Community versus isolate attribution; an unspecified
nutrient combination; an unknown connection between organism phenotype and
candidate role; unestablished comparability. Retain a narrower supported
physiology observation where possible.

**Numerical output.** The six count cells in section 3, plus requested native
endpoint estimates/contrasts with their original meaning. The count concerns
assessed organism physiology, not a gene perturbation effect newly scored again.

### 4.2 Organism metabolic-observation subscoring sheet

**Counted observation.** A source-established organism-level respiratory,
consumption, production, or assimilation observation for identified chemical
species and stated conditions.

**Reader must supply.** Actual organism/community attribution; donor, acceptor,
substrate and/or product identity as measured; endpoint type; time and sample;
normalization and controls when reported; source conclusion; native values and
uncertainty when available; original experiment/measurement identity.

**Support criterion.** The observation establishes a physiological mode in which
the proposed role has a source-supported biological place. The grader identifies
the proposed role's connection to the measured process and retains alternative
routes. Substrate disappearance, uptake, isotope assimilation and identified
product formation are different observations.

**Conflict criterion.** The observed metabolic behavior conflicts with a stated
physiological implication of the proposed role under matched conditions. An
alternative pathway's existence alone is not contradiction; it limits how
specifically the observation identifies the candidate's role.

**Unresolved cases.** Ambiguous chemical identity, pool versus flux, abiotic or
community contribution, unknown role-to-phenotype connection, or unestablished
sample applicability. Molecular enzyme evidence retains its A105 identity.

**Numerical output.** Count cells and requested native flux/amount/stoichiometric
components. Multiple derived descriptions of the same balance retain one
original observation identity.

### 4.3 pH-condition subscoring sheet

**Counted observation.** An actual sample/compartment pH observation or a
documented organism growth/activity condition relevant to a source-established
pH dependence of the proposed function.

**Reader must supply.** pH value or actual source-described condition; sampled
compartment and state/time; measured versus nominal status; organism/sample
relation; source-supported biological pH requirement or response finding.

**Support criterion.** The observed pH circumstance is compatible with what the
source actually establishes about the proposed role's pH dependence. A nominal
culture pH supports only that culture circumstance.

**Conflict criterion.** The source establishes an incompatible pH circumstance
for the claimed scope. A single successful assay pH or an optimum does not
establish inactivity elsewhere and cannot support that exclusion.

**Unresolved cases.** External versus intracellular pH, unknown regulation,
missing activity-response relationship, or an uncertain sample link.

**Numerical output.** Count cells; native pH and supported requested comparisons.
No arbitrary distance from an optimum is converted to a quality score.

### 4.4 Temperature-condition subscoring sheet

**Counted observation.** A source-described thermal condition of the actual
organism/sample relevant to the proposed role's established activity or
stability circumstances.

**Reader must supply.** Temperature/scale or source-described thermal regime;
exposure duration/history; growth versus exposure versus activity meaning;
measured versus nominal status; organism/sample; relevant biological requirement.

**Support criterion.** Conditions agree with the established role at the
appropriate duration and molecular state. A thermophilic species name alone
does not establish the temperature of the sample being annotated.

**Conflict criterion.** Source-established activity/stability dependence makes
the documented circumstance incompatible with the proposed role's claimed
scope. Melting temperature, growth optimum and enzyme activity temperature
cannot substitute for one another.

**Unresolved cases.** Unknown duration, source/target state differences, or
missing activity versus stability interpretation.

**Numerical output.** Count cells and source-supported temperature/duration
components. The source's physiological condition is not an imposed score limit.

### 4.5 Oxygen/redox-condition subscoring sheet

**Counted observation.** A documented oxygen or redox circumstance of the actual
organism/sample relevant to an established requirement or sensitivity of the
proposed role.

**Reader must supply.** Actual measured quantity or reported cultivation state;
sample/site/time; oxygen exposure history; nominal versus observed status;
source-supported requirement/sensitivity; native value/detection qualifier when
reported. Gas composition, dissolved oxygen and electrode potential remain
distinct.

**Support criterion.** The documented circumstance permits the source-established
role under the declared conditions. A documented anaerobic cultivation result
can qualify as a contextual observation without a manufactured variance.

**Conflict criterion.** The documented circumstance is incompatible with the
particular oxygen requirement or sensitivity. The conflict is scoped to that
state: a claim about anaerobic growth does not establish absence of all transient
oxygen exposure throughout the organism's history.

**Unresolved cases.** Requirement inferred only from an annotation name; bulk
condition used as local concentration; redox potential treated as oxygen;
source/target condition transfer not established.

**Numerical output.** Count cells; native oxygen/redox data when available.
The source-backed contextual comparison supplies the counted observation; the
word `anaerobic` is not assigned an arbitrary numerical confidence.

### 4.6 Salinity/water-condition subscoring sheet

**Counted observation.** A documented ionic or water-availability circumstance
relevant to the proposed role in the actual organism/sample.

**Reader must supply.** Actual salt/ion, salinity, ionic strength, osmolarity or
water-activity property; sampled medium/compartment and state; source observation
and method; native units; source-supported dependence of the proposed role.

**Support/conflict criteria.** Compare the specific observed property with the
actual biological dependence. Habitat labels do not establish a sample's
measurement. Organism salt tolerance is not automatically molecular activity
under that condition. Unsupported conversions among salinity, osmolarity,
ionic strength and water activity cannot establish support or conflict.

**Numerical output.** Count cells and requested native quantities. Missing
composition prevents a conversion, not the retention of the original observation.

### 4.7 Substrate-availability subscoring sheet

**Counted observation.** An identified required substrate is observed, supplied,
produced, or demonstrably absent under specified conditions, at the source's
actual location and chemical resolution.

**Reader must supply.** Chemical identity/form; actual organism/sample/matrix;
compartment and sampling state/time; endogenous observation versus added reagent;
method/result and qualifiers; native concentration/amount/detection information
where available; source-grounded reason the proposed role uses this chemical;
accessibility evidence where the assessed claim requires it.

**Support criterion.** The observation establishes the relevant presence/supply
relationship at its stated resolution. Demonstrated local accessibility is
stronger in scope than whole-sample presence, but no invented strength multiplier
converts that distinction to a score. Both can be represented as distinct
relations to the same original observation.

**Conflict criterion.** Actual observations establish absence or incompatible
chemical form/location within the scope required by the candidate claim. A
missing database entry, no literature hit, or non-detection without its detection
scope does not establish absolute absence.

**Unresolved cases.** Free versus total amount, related analogue versus substrate,
whole sample versus accessible compartment, transfer from engineered mutant
to wild type, or missing transport connection. A supported narrower presence
relation remains when enzyme access is unresolved.

**Numerical output.** Count cells and requested native chemical components. A
source measurement and its detector call retain one observation identity.

### 4.8 Cofactor-availability subscoring sheet

**Counted observation.** A source establishes the presence, supply, accessible
form, or relevant absence of the particular cofactor required by the proposed
role in the stated organism/sample circumstances.

**Reader must supply.** Named active molecular/oxidation form; sample/compartment;
source observation of supply/form; relevant biosynthetic/import/recycling
finding if used; source-established role requirement; native measurements and
their exact denominators when present.

**Support criterion.** The documented observation establishes the cofactor
relationship actually needed for the proposed role. Endogenous synthesis,
environmental supply and import are different supported routes, not assumed
equivalents inferred from a cofactor name.

**Conflict criterion.** Source-established chemistry/access or physiological
observations contradict the required form/supply relationship at the claimed
scope. Total metal content does not establish a metal-containing cofactor, and
an unannotated biosynthetic gene does not establish absence of the cofactor.

**Unresolved cases.** Active versus inactive forms, total versus accessible
pool, salvage/import, redox state, or recycling requirement.

**Numerical output.** Count cells and actual source quantities such as active-form
amount/fraction. A source-derived physical fraction is retained as that
measurement; it is not an A108 0–1 evidence score.

### 4.9 Microscopy-localization subscoring sheet

**Counted observation.** A microscopy observation establishes a molecule's or
required chemical/partner's location in a defined organism/state, relevant to
the proposed role's spatial requirement.

**Reader must supply.** Actual molecule/construct and tag; organism/state;
compartment marker and method; source localization result; marker/background
qualifications; time/sample; native counts or spatial measures if reported.

**Support criterion.** The observed localization permits the required spatial
relationship, at the source's actual resolution. Whole-cell detection is not
same-compartment access; apparent optical overlap is not proof of binding.

**Conflict criterion.** The observed localization contradicts required access
within the stated scope, with any known transport/contact route considered.

**Unresolved cases.** Tag effects, optical resolution, molecule identity,
expression-host transfer, missing counterpart location, or predicted localization
substituted for observation.

**Numerical output.** Count cells and requested native quantitative localization
components. Cells/pixels/fields are not independently scored observations merely
because the source reports many of them.

### 4.10 Fractionation-localization subscoring sheet

**Counted observation.** A source-supported distribution among biochemical
fractions establishes a spatial relationship relevant to the proposed role.

**Reader must supply.** Actual molecule/preparation and organism; fractions and
markers; observed distribution; fraction purity/contamination/recovery
qualifications; method and state; actual amount/profile values when reported.

**Support/conflict criteria.** The marker-supported fraction assignment bears on
the proposed role's required compartment/access. A biochemical fraction name
does not establish localization without its actual source interpretation;
contamination and recovery qualifications remain attached. The profile's many
fractions and normalized views represent one original distribution observation.

**Numerical output.** Count cells plus requested native fraction amounts/profile
comparisons. A fractionation result does not establish physical binding.

### 4.11 Curated localization-observation subscoring sheet

**Counted observation.** A curated record conveys a particular original
localization observation for an identified molecule/organism and cites its
support or native evidence provenance.

**Reader must supply.** Exact native field/record version; molecule/organism;
location term; evidence code/qualifier; original cited observation when supplied;
inference method; source relation to existing paper/experiment records.

**Support/conflict criteria.** The actual documented location bears on the
candidate's required spatial relation. A directly curated observation may be
usable without reacquiring information already possessed. A prediction or an
annotation propagated from the candidate being evaluated is not silently
counted as an observed location. Transfer from a characterized homolog retains
its actual source organism/construct and qualified applicability.

**Numerical output.** Count cells for eligible curated observations, separate
diagnostic counts/refs for prediction or annotation leads, and explicit original
observation identity to prevent a database/paper duplicate contribution.

## 5. Source-specific reader and tool subscoring obligations

These reader obligations precede the appropriate scientific grader; tool success
alone does not populate a positive evidence cell. The full existing tool
inventory and exposure gaps are in `A108_SOURCE_AND_READER_PLAN.md`.

| Source/tool route | Required exact selection and interpretation | Numerical return and exclusion |
|---|---|---|
| Literature text/ordered/targeted reading | Original source and passage witnesses; named subject; actual observation; context; requirement/relationship passages | Selected eligible observation IDs and corresponding count cells through its purpose-specific grader. Sentence/quotation count is excluded. |
| Literature table/XLSX reader | Original table/row/headers/footnotes; actual study unit and comparator; native values/units | Actual observation grouping plus numerical source cells. Multiple rows/replicate wells/derived columns are not automatically distinct evidence. |
| Literature figure/PDF-image reader | Actual viewed figure/panel; legend; original experiment relation; graphical versus reported origin; sample conditions | Source observation grouping and requested numerical extraction. Panel count and image acquisition do not score. |
| UniProt record | Exact native field, sequence/organism identity, location/condition statement, evidence qualifier and citation | Curated-observation or other applicable sheet. An annotation label without a demonstrated outside observation remains a lead. |
| NCBI taxonomy/sequence or supplied GenBank metadata | Actual taxon/strain/isolate/source qualifier; record version; original sample/condition assertion; source-to-target relation | Relevant documented context observations through the matching condition/availability grader. Taxonomic identity alone is not a physiological observation. |
| GEO/SRA context records | Actual sample/experiment accession and metadata field; condition/treatment/time; measured versus submitter-recorded status | Relevant recorded sample-condition observation and source-specific scope. No raw-read analysis, gene-expression inference, or score from number of samples downloaded. |
| BV-BRC native data | Original collection/record/field; genome/taxon/experiment/sample links actually supplied; original assertion/observation identity | Relevant context observation only where frozen native fields actually contain it. Missing broad phenotype fields cannot be invented from a genome identifier. |
| ChEBI/Rhea/chemical/reaction records | Exact chemical/reaction identity and source-supported requirement | Identity/requirement inputs to the scientific comparison; a reaction record does not itself establish that the organism has the substrate. |
| Existing A105/A106/other-axis received components | Exact admitted source component, original experiment/measurement identity, original qualifications | Reused numerical/requirement inputs; no second assay score merely because A108 reads them. |

Search/record readers may return useful numerical operational facts such as the
number of returned IDs or examined original sources. Those values have their
own meanings and are not `evidence_amount`. The scientific grader must examine
the actual observation and contextual connection before it contributes.

## 6. Scope, transfer, conditions, and unresolved joins

**Direct evidence.** Source observation concerns the actual target organism,
strain and sample/state. The returned row identifies which of those relations
are established; species identity alone must not be reported as exact strain
or sample identity.

**Qualified transfer.** A source observation from a related organism, strain,
construct or sample can inform the proposed context when the biological
transfer is supported. The reader/grader records the actual source scope and
the specific correspondence evidence. No default 0.5 related-strain factor is
introduced. The main sheet can return requested direct and transferred count
subtotals without pretending their biological meanings are identical.

**Conditional evidence.** An observation can support the proposed role under a
stated condition, such as host inflammation. It contributes as conditional
evidence with that condition preserved, not as evidence that every target sample
has that condition. An outside-scope condition is not rewritten into the
commissioned sample; the grader instead reports the exact remaining relation.

**Narrower supported relation plus missing access.** Establishing substrate
presence does not require the reader to invent enzyme-compartment access. The
supported presence relation and unresolved access relation share their original
observation identity. The unresolved relation adds no new positive evidence.

**Contradictory sources.** Separate original observations can support and
conflict with the same scoped claim. Preserve both sets. A correction to one
observation retires its superseded assessment rather than becoming new
independent corroboration or simultaneous current disagreement with itself.

**Quantitative observations.** Native values can make the contextual comparison
more precise, but their absence does not automatically disqualify a documented
qualitative physiological observation. Conversely, extracting a number does
not establish its biological relevance or permit arbitrary arithmetic.

## 7. Optional native numerical comparison components

These are additional purpose-specific components, never prerequisites imposed
on every literature observation and never mixed arithmetically with counts.

- A resource-response reader can return
  `response_difference = response_resource - response_control`, with variance
  `V_resource + V_control - 2*covariance` when its actual sampling design supplies
  those terms. Missing covariance is not assumed to be zero.
- A substrate-availability reader can return a requested
  `sample_concentration / source_test_concentration` after units, chemical form,
  matrix and comparison meaning are established. A successful assay
  concentration is not a minimal in-vivo requirement.
- A cofactor reader can return `active_form_amount / matched_total_amount` with
  its actual denominator. This is a composition measurement, not evidence quality.
- A pH/temperature reader can return an actual matched-unit condition difference.
  An optimum is not treated as an exclusion threshold.
- A microscopy reader can return `observed_positive_units / evaluated_units`
  with the actual biological/technical counting unit. It does not treat image
  pixels or repeated fields as independent biological replicates.
- A fractionation reader can return actual abundance profiles or selected
  fractions with recovery and marker qualifications, rather than reinterpreting
  them as binding or function probabilities.
- If a source supplies supported observation models and their numerical
  operands, a specifically requested likelihood comparison can be retained in
  nats. The existing A105 equal-variance normal comparison is
  `((x-mu_alternative)^2 - (x-mu_claim)^2)/(2*V)`; its predictions, variance and
  model need actual support. A108 does not manufacture them from a function
  name or require them before scoring a qualitative outside-context observation.

One source observation's count and optional measurement/model components retain
the same original identity. Neither derived components nor source model
diagnostics create additional counted observations.

## 8. Exact typed handoffs

### Main evidence question to the applicable subscoring grader

The commission provides the candidate assertion; requested contextual claim;
organism/sample/condition scope; actually received source/requirement components;
permitted source tools; and exact requested count/native components. It supplies
no known-case answer, preferred result, or assumed substrate/localization fact.

### Reader to purpose-specific subscoring grader

The reader supplies the exact observation fields specified in section 4, using
authenticated source selectors or admitted components. Literal numbers carry
their actual unit/context witnesses. A received component is identified by
`namespace`, `sheet_ref`, and `component`; a reference alone does not expose
private measurements. Source record and context identities are delivered as
typed references, not replaced by a freehand paraphrase.

### Subscoring grader to saved subscoring sheet

Each assessed relation retains these explicit identities and scientific fields:

```text
candidate_assertion_ref
context_claim_ref
required_function_finding_refs
grader_type and actual observation/experiment type
original_observation_ref and original observation-group identity
original experiment, measurement, source-claim and comparator identities
domain: physiology | environment | availability | localization
relation: support | conflict | unresolved
actual source organism, strain, sample, compartment, condition/state/time refs
applicability: direct | qualified_transfer | conditional
actual evidence origin and source-specific method/evidence qualifications
source refs and exact source selectors; source revision/equivalence refs
relationship witnesses; unresolved connection/input refs
optional admitted native component selectors
```

The grader's custom scientific criteria determine the eligible observation
sets. Deterministic calculation then saves the six numerical cells from section
3 with exact contributing sets. A prose conclusion cannot populate a numeric
cell. Reusing the same observation in another representation does not increase
the sets' cardinalities.

### Saved subscoring sheet to main evidence scoring sheet

Return exactly the requested saved count/native components with their original
contributor identities. The main sheet receives numbers and the actual sets
needed to deduplicate them; it does not infer counts from sentences or blindly
sum child scalar totals. It rejects private/unreceived components and bindings
to another candidate/context selection. Scientific missingness is preserved.

The main sheet applies section 3's set arithmetic separately to physiology,
environment, availability and localization. Overall sets are the unions across
those domains. Therefore an observation appearing in two domains contributes
once overall; the overall amount is not necessarily the sum of domain amounts.
Requested native statistical components retain separate units and meanings.

### Main evidence scoring sheet to the parent episode

Return the requested numerical domain/overall components, their actual
contributor references, context qualifications, and specific unresolved needs.
The parent receives neither the child's entire transcript nor an unrestricted
view of private source data. A new source reading that changes no eligible
original observation set does not change `evidence_amount`.

Evidence score and continuation credit must have explicit runtime bindings.
The current A105 live workflow's finding-progress counter is not automatically
this A108 score. If the episode is to use A108 evidence amount as its credit,
the implementation must project this exact saved/received component under the
commissioned scope, with inherited evidence and corrections respected; it must
not silently substitute a generic finding count or sum child credits. The main
integration plan owns that binding and its eventual full-workflow validation.

## 9. Worked arithmetic for the proposed system

This is a **synthetic scoring-sheet illustration**, not a claim that any of
these observations has been extracted or scored in a workflow.

Suppose the target organism and sample are actually established, and the
substrate-availability subscoring sheet assesses original observation O1 as
supporting substrate presence in that documented target context. Its connection
to enzyme access remains unresolved. The sheet contains:

```text
support observation refs:    [O1]
conflict observation refs:   []
unresolved observation refs: [O1]
support_observation_count    = 1
conflict_observation_count   = 0
overlap_observation_count    = 0
evidence_amount             = 1
net_support_count           = 1
unresolved_observation_count = 1
```

The unresolved access relation adds no evidence amount and does not erase the
supported narrower relation. If a database repeats O1, the amount remains 1.
If another domain reuses O1, the overall amount remains 1. If a distinct
original observation O2 establishes a relevant conflict, the main sheet has
support set `{O1}`, conflict set `{O2}`, amount 2 and net support 0. The amount
records two assessed observations; zero net support does not mean nothing was
learned. If O1 itself also informs a conflicting relation, the overlap count
ensures it is still counted once overall.

An actual scored annotation still requires the real retained source selectors,
observation identity, target-organism/sample binding, applicable source relation
and admitted components. This arithmetic does not claim those execution steps
have occurred and supplies no actual biological test case.

## 10. Build obligations

The rebuild needs the eleven scientific branches above, the actual required
source-specific readers, saved-sheet/count arithmetic, exact selected-component
returns, source/observation deduplication, the four-domain main evidence scoring
sheet, and an explicit episode-credit binding. Existing access tools require
deliberate A108 exposure; some source readers and receiver bindings are new.

Source inventory, observation discovery and evidence counts are distinct
deliverables. No assessment is called complete because a JSON schema contains
score-looking field names. A complete worked case must show the original
observation, its custom grader decisions, saved numerical subscoring cells,
the main-sheet calculation, actual parent admission and the resulting bound
episode score. This document supplies the proposed numerical/scientific
specification; implementation and full-workflow validation remain separate.
