# Native source rate inputs — engineering proposal 024

No shared production file has changed. This proposal maps native inputs to the
existing ten rate components; it proposes no new scoring arithmetic or axis.

## Selected operation

Add `literature.rate.source.populate`, returning the existing
`literature_rate_cells` projection through the existing repository/provider.
Only the seven literature roles receive the operation. The root's existing
names/descriptions projection will describe it without granting execution.

Closed arguments:

```text
source_ref: received root source
source_kind: primary_source | retained_extraction | synthetic_fixture
literals: {subject: Witness|null, experiment: Witness|null}
arms: {reference: Arm|null, test: Arm|null}
dependence: {value: unknown|independent, witnesses: Witness[]}
observation_model: {value: none|independent_normal_groups, witnesses: Witness[]}

Arm:
  label, condition, endpoint, normalization, measurement_identity: Witness|null
  rate: {number: NumberSelector, unit: Witness|null}|null
  uncertainty:
    kind: unreported|unspecified|sd|sem
    magnitude: NumberSelector|null
    unit: Witness|null
    kind_witnesses: Witness[]
    count: NumberSelector|null
    sampling_basis: {value: biological_preparations|technical_measurements|unspecified,
                     witnesses: Witness[]}

Witness: {source_ref, representation: original|text, start, end, quote}
NumberSelector: {witness: Witness, number_start, number_end}
```

Only byte/character offsets are model-supplied numbers. Values, counts and
spread magnitudes come from exact bytes. Nontrivial statistical assumptions,
typed spread and sampling basis need source witnesses; quotes establish custody,
not biological truth or applicability. Null meanings remain null.

## Native extraction

Add `a105_rate_extraction_v2` while preserving v1 validation and output exactly.
Top-level fields remain version, subject, experiment, rows; native subject and
experiment may be null. Reference/test roles are selection roles, not invented
source arm labels. Each native row retains its actual label witness separately.

Native rows retain the existing operand keys, allowing nullable context/unit
where unavailable, and an explicit source variant:

```text
source:
  representation: native_source_spans
  source_ref, artifact_ref: exact selected rate source/representation artifact
  number: enriched parsed rate selector|null
  unit: enriched unit witness|null
  meanings: enriched label/subject/experiment/condition/endpoint/normalization witnesses
  uncertainty: enriched selected spread/count/kind/sampling witnesses
  measurement_identity: enriched explicit physical-observation witness|null
```

There are no fabricated row numbers or generated CSV sources. Byte-location
identity is the actual number's absolute byte range (or an explicit missing-arm
record identity); physical observation identity is an independent nullable
source-backed meaning. The same physical observation selected under two roles
cannot become a valid independent comparison. Unknown identity cannot establish
independence. Distinct byte locations or equal/unequal values do not establish
distinct physical observations.

The new reader reuses `_Sources` custody and the witnessed-number machinery
where supported. It supplies a native-rate unit parser for all current RATE_UNITS
dimensions instead of reusing partner conversion into pmol/min/mg. Unit tokens
must be complete, including their denominator. U without a selected definition
returns a specific unsupported native-unit result, never a universal factor.
An unsupported numeric lexical expression is repairable, never coerced to a
point. Upper/lower limits and approximation markers must remain such; the native
route cannot silently accept a clipped comparator.

## Calculations and missing information

Keep all v1 calculations and shapes unchanged. Extend identity helpers to use
actual native witness identity, and add a v2-only path for nullable meanings.
Individual known rates retain their own canonical unit even if the pair is not
comparable. Missing rate or unit makes that individual cell unavailable, while
its parsed raw number/unsupported raw unit remain saved in extraction.

Pair difference, ratios and conditional statistics require known common subject,
experiment, endpoint and normalization meanings, compatible dimensions and
known selected conditions. Missing meanings, disagreement or repeated physical
observation leave pair cells unavailable with specific reasons; they do not
discard individual rates. The intended condition difference is retained, not
required to be equal. These are source-preparation comparisons, not proof that
nuisance variables or mixed contributions have been isolated.

Reported SEM can populate an individual mean-SE cell. SD requires count and the
existing explicitly selected normal model. Unknown physical identity/dependence
cannot populate pair uncertainty/profile cells. Untyped spread remains untyped.
The calculator's current profile and proposed-index formulas are unchanged.

Extend the existing unavailable-reason enum additively for these native-only
unknown/mismatch reasons. Do not alter current v1 reasons or replace the saved
historical forms. This is the only proposed change to current projection schema
content; fields, namespaces, component meanings and all old values are unchanged.

## Persistence and communication

`LiteratureRateRepository.populate_native` validates run/key/closed operands,
original root source receipt/scope and every witnessed source through its actual
read callback. A replay signature binds mode, operands and scope. Exact replay
returns the original outcome before artifact reads; changed operands fail.

Persist `literature_rate_population_record_v2` in the same operations table and
provider, with input root/original artifact, all actually consulted source refs,
native selection, complete native extraction, unchanged sheet component meanings
and nullable existing experimental bindings. Parent-source refs include the
actual consulted sources and their required custody ancestry.

The existing `read` accepts v2 only for the rate provider; subclass providers
retain their own version checks. V2 saved validation checks request/operation,
source metadata and enriched selected fields without reopening source bytes or
rerunning numeric extraction/calculation. Projection copies the saved cells;
receive/admission keeps exactly the caller-requested subset and arbitrary field
name. The existing C7/runtime source receives this one selected outcome, creates
its ordinary receipt/observation, and populates its existing typed fact source.
No new observation, model report composer, score or continuation rule is added.

## Required coordination

Adding a real operation intentionally extends the child catalog. The 023 test
currently requires the entire catalog to equal its immutable 14-entry baseline.
Preserve that historical JSON fixture and replace the assertion with exact
equality of those 14 original entries plus one separately checked native entry.
The parent-information runtime fixture's metadata count/baseline comparison also
needs that additive adjustment. The coding owner has not changed that test;
the parent must assign its ownership explicitly.

Potential implementation alternatives to resolve before code: (1) whether native
source-defined U support belongs in this workload or remains a specific
unsupported partial component; (2) whether missing native metadata should be
expressed with the additive current reason enum proposed here or a separate
projection, which would duplicate the existing rate sheet unnecessarily.

No paper was acquired or interpreted. The synthetic 12-versus-3 example maps to
the existing cells and does not demonstrate a complete experimental scoring
sheet. Runtime integration and saved-only reconstruction still require tests.
