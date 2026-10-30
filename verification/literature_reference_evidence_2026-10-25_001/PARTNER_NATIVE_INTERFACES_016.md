# Native source spans populate the existing partner sheet

Implementation continuation of015, using its supplied scientific conversion and
completed post-paper reset. No new paper or new biological interpretation is
assigned. The eight numerical components, their meanings and arithmetic remain
unchanged. The native source route closes the need for caller-prepared numeric
JSON; retained source-data population remains available and backward compatible.

Fresh exclusive owners:
- Scalar owner: literature_partner_source_fields.py and its new test file only.
- Native-input owner: literature_partner_native_inputs.py and its new test file only.
- Storage owner: existing literature_partner_storage.py and new
  tests/test_literature_partner_native_storage.py only.
- Coordinator: existing reader dispatcher, episode registration/TASK, integration
  fixture, exact source selectors, examples and final independent review.
All production module names above are under gene_annotation_episode/. No other
files, old pins/runs/history, core calculator, tool graders or credit changes.

## Scientific instructions and numerical illustration

Establish actual source subject/partner, endpoint, normalization, conditions and
physical observation identities. Select exact native numerical/unit spans and
explicit spread meanings; do not type scientific numbers into arguments. A
canonical identifying passage may be reused only for the same actual entity or
physical observation. Different mentions/number positions do not prove different
measurements. If identity is unresolved, leave its witness null. Reference labels
and units alone do not establish matching preparations or isolated effects.

The reader parses selected literal values and upper limits, preserving exact
source custody and raw tokens. It converts compatible rate units before filling
the existing core. For synthetic native W=.1nmol/min/mg,O=.02nmol/min/mg,
A=.09nmol/min/mg, canonical W100,O20,A90pmol/min/mg yield loss80, fractional
loss.8, addback fraction.875 and restored-reference fraction.7. An O<.005
nmol/min/mg supplies domain[0,5], not an observed zero. Existing Pdx source spans
must yield774(spread58) and284(spread33), preserving unspecified spread and
different nitrogen conditions. No controlled partner loss follows from that pair.

## Scalar helper: exact interfaces

Use existing _Sources from literature_assay_inputs and ExperimentalContractError.
Export number_selector_schema(), read_source_number(selector,*,sources,role),
read_source_rate_unit(witness,*,sources), convert_source_number(number,unit).
No I/O, SQL, network, models or mutation beyond the supplied _Sources cache.

Number selector exactly {witness:<ordinary _Sources witness>,number_start:int,
number_end:int}; offsets are Unicode character offsets within quote, witness
offsets are UTF8 byte offsets. number_start<end. role is rate|spread|condition.
Read the actual complete finite signed decimal/scientific-notation token, reject
partial mantissas/exponents/signs, decimal/thousands commas and nonliteral values.
Check original bytes around the token, not just the selected quote. An outside
comparator must not disappear by shortening a witness. Skip terminal XML/HTML
tags when distinguishing markup from comparisons. Support plain points and
upper-bound prefixes <,<=,≤,&lt; and literal phrases below/less than/at most/no more
than (including optional or equal to). Preserve lt versus le. Unsupported lower
bounds, intervals and approximations return specific repairable ContractErrors.
For rate role, a preceding ±,+/-,&plusmn; is uncertainty, not a main point.
For spread/condition roles require a plain nonnegative point (spread may follow
±); a bound is not a spread or exact condition. Reject nonfinite and unrepresentable
canonical values rather than silently producing zero/infinity.

read_source_number returns exactly {selector:<deepcopy with enriched witness>,
raw_number:string,value:finite number,relation:point|lt|le}. No measurement or
independence identity is inferred from this numerical token. Native nonnegative
rate scope is inherited from the existing core; negative noise measurements need
a different supported endpoint route and are not clipped here.

read_source_rate_unit reads the complete exact ordinary unit witness. Verify
original source edges so nmol cannot be truncated to mol, or /mg dropped. Support
canonical spellings and ordinary whitespace/minus/superscript aliases of:
pmol/min/mg,nmol/min/mg,umol/min/mg,per_min,per_s,uM/min,nM/min.
Return exactly {witness:<enriched>,raw_unit,canonical_unit,multiplier}. Canonical
units are pmol/min/mg (multipliers1,1000,1000000),per_min (1,60),uM/min (1,.001).
Preserve units of different dimensions. No mass-denominator identity is inferred
from the unit. convert_source_number(number,unit) uses exact rational
intermediates and returns a finite canonical float; range failure is explicit.

## Native reader: operation schema and exact return

Export partner_source_population_schema(), read_partner_native_inputs(arguments,
*,read_source), VERSION=literature_partner_inputs_extraction_v2.
Use the same9 LITERAL_FIELDS, SOURCE_KINDS and existing core COMPONENTS as015.
No dependency on the existing partner_inputs dispatcher (avoid a circular import).

Closed args exactly {source_ref,data_source_ref,source_kind,literals,
interpretation_witnesses,input_mode:native_source_spans,arms:{reference,omitted,addback}}.
source_ref/data_source_ref are required actual source refs; data_source_ref is
native source material, not JSON. Read their original bytes for custody without
requiring arbitrary binary bytes to decode. All other selected bytes come from
ordinary exact witnesses, with actual source/artifact/representation custody.
Existing9 literal and interpretation witnesses retain their meanings.

Each native arm is null or exactly:
```
subject: Witness|null
partner: Witness|null
endpoint: Witness|null
normalization: Witness|null
partner_state: present|absent|unreported
conditions: {coverage:complete|partial|unreported, factors:[{
  factor:<nonempty identifier string>,
  level: null | {kind:literal,witness:Witness}
              | {kind:number,selector:NumberSelector,unit_witness:Witness|null}
}]}
measurement_identity: Witness|null
origin: reported|graph_derived|synthetic
rate: null | {
  value:NumberSelector,
  unit:Witness,
  spread:{kind:SD|SEM|CI|unspecified|unreported,
          magnitude:NumberSelector|null,witnesses:[Witness]}
}
```
factor is an internal experimental-field identifier (ASCII letter followed by
ASCII letters/digits/underscore,1..128chars), not free findings/instructions.
Literal factor level is the exact quote, unit=source_literal. Numeric level is
the parsed plain point with the exact selected unit quote, or dimensionless
when unit_witness=null; no condition-unit conversion/equivalence inferred.
Different representations are recorded comparison differences, not proof of
physical incompatibility. Complete/partial/unreported relationships follow the
existing core. Unknown factor level remains null with unit=unreported.

Read all witnesses and preserve their enriched forms in native_evidence. Derive
canonical entity/measurement keys from the identifying witness including source,
artifact,representation,start,end,quote, with fixed identity namespaces. Reusing
the same canonical witness must reuse the same key. Unknown witness ->null key;
no inference from number equality, different tokens or counts. These keys are
source interpretations of experimental identity, not independent-sample claims.
Normalizing a rate unit does not invent its mass/amount denominator identity.

Missing rate ->measurement status=unreported,value=null,unit=unreported,spread
unreported. Present rate: point ->observed; lt/le ->upper_bound, preserving the
original relation in native_evidence. Convert rate and spread magnitude using
the same rate-unit scale; native points/spreads/limits remain alongside derived
canonical values. Spread kind unreported iff magnitude null. SD/SEM/CI require
at least one exact basis witness; unspecified magnitude does not infer SD/SEM.
No CI endpoints, variance, n or sampling model are inferred from a scalar spread.
Rate/spread/source identities and experimental associations remain supplied
scientific interpretations, not truth established by matching byte spans.

Construct the exact existing literature_partner_inputs_v1 core input and invoke
populate_partner_components once. Synthetic fixture requires every present arm
origin=synthetic. Complete condition coverage needs an interpretation witness as
in015. Preserve source_kind, raw provenance and scientific unknowns.

Return exactly the old8 fields plus native_evidence:
{version:VERSION,arguments,sources,literals,interpretations,recipe,calculation,cells,
 native_evidence:{reference,omitted,addback}}.
recipe is {version:literature_partner_selection_v1,inputs:<normalized core input>},
created from source spans, not parsed/claimed as original JSON. Each evidence arm
is null or the selected native-arm object with enriched witnesses and parsed
number/unit records; export a closed native_evidence_schema() describing it.
Define its exact structures clearly in code docstrings/tests for the storage
owner. cells is a deep copy of calculation.cells; no raw source bytes in output.

## Selected storage and backward compatibility

The new selected name is literature.partner.source.populate. Existing
literature.partner.populate and partner_population_schema stay unchanged, so
all015 source recipes, frozen schemas and saved rows retain their meanings.
Both tools use the same repository/provider/eight-cell typed handoff. The
existing reader dispatches input_mode=native_source_spans to the new reader;
otherwise uses the exact old retained path. Storage validates the appropriate
argument schema and v1/v2 extraction shape. Reexport native operation schema.

Native direct source order: existing fixed root,data,literals,interpretation
order, then all extra nested native-arm witness source refs sorted/deduplicated.
Validate exact direct set, all receipts/scope/page lineage and scoped ancestors.
Saved data_source_ref remains the real native source (possibly same as root).
No hidden derived source or observation is manufactured for recipe construction.

Save native_evidence in the immutable payload. Reopening validates argument and
evidence relationships, actual source/artifact identities, canonical inputs,
cell metadata, exact outcomes and requested subsets WITHOUT calling any native
reader/helper, core, _Sources or original-byte acquisition. Validate saved fields
and declared meanings; do not rerun numerical parsing or unit conversion in
read/project/replay/forwarding. Typed row shape remains unchanged, carrying
canonical units and actual source bindings/spreads/checks. Keep raw unit tokens,
limits and evidence in committed sheets for scoped later access. Source factor
term mappings retain the existing source-bound reference pattern.

## Required verification

Scalar: UTF8/token/unit boundaries; outside bound/approximation/sign; markup and
entities; exact point/lt/le; spread-vs-point; dimensions and conversions; finite
range; no mutation. Native reader: literal real callbacks and schema, no scientific
numbers in args, canonical repeated identity, unknowns and missing addback, changed
nitrogen source preserving Pdx native points, SD/SEM/unspecified distinctions,
synthetic positive/censored comparisons and all source custody.
Storage/integration: all old retained checks; actual native operation with no JSON
source, full recurring TASK and parent meanings; exact requested typed forms;
transaction/authority/page/provenance; original source helpers disabled and SQL
query_only for saved-only replay. No actual model or native PDF-parser claim.

## Parent clarification: signed condition values

The earlier nonnegative condition restriction was incorrect: a reported Celsius
temperature can be negative. Condition role accepts signed plain point tokens;
spread role alone requires a nonnegative magnitude. Native rate nonnegativity
remains the existing finite core's constraint and is not imposed on conditions.
Selecting only the unsigned suffix of a negative token still fails the partial
token guard. No comparison bound is converted into an exact condition value.

## Source-review clarification: absolute spread units

Native rate.spread additionally requires unit:Witness|null in args, and
unit:ParsedUnit|null in saved evidence. Null declares a common-unit association;
an explicit separate unit is parsed and used to convert the spread magnitude.
It must have the same canonical dimension as the rate. The main unit still
converts the main point/limit. A .1nmol/min/mg mean with10pmol/min/mg SD therefore
preserves both raw units and yields canonical100±10pmol/min/mg, without sampling
inference. Existing015 retained arguments/records remain unchanged.

Scalar helper additionally exports validate_source_spread_unit(number,unit,*,sources).
It checks the original source immediately after the spread token for an explicitly
printed supported rate unit and requires agreement with the chosen spread unit's
canonical_unit and multiplier. It does not silently treat an unselected different
unit as the main unit. No explicit printed unit leaves the common-unit association
as a supplied interpretation, not a scientific-validity proof. Explicit percentage/
percent/per-cent relative errors are unsupported as absolute rate spreads and
must be rejected, never rescaled into a rate. Native reader invokes this helper
before conversion. Saved validation preserves these parsed records/associations
without rerunning source parsing or unit conversion.
