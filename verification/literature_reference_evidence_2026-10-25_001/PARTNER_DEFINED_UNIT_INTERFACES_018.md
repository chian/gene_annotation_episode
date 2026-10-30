# Source-defined activity units for the existing experimental partner cells

The parent inspected the one Bcd/Etf primary source and completed the full
post-paper reset in primary_bcd_partner_018/PARENT_RESET_001.json. No other paper
is assigned. This is a source-unit representation addition to the existing eight
components, not an eleventh scoring sheet or a new experimental quality grade.
The pure component calculator and its qualification rules stay unchanged.

## Source conversion and separate scientific instructions

Table2 reports NADH oxidation7 versus0.1U/mg at25°C with Fd present versus absent
and hydrogenase retained. Its footnote defines oneU as1µmol of the corresponding
endpoint per minute. Canonical rates are7,000,000 and100,000pmol/min/mg of the
purified intact Bcd/Etf preparation. Conditional arithmetic gives6.9U/mg loss
and69/70 fractional loss; this is not a qualified causal, uncertainty or reliability
score. At37°C the separate H2 endpoint5 versus<0.01U/mg yields canonical5,000,000
versus a strict upper limit10,000pmol/min/mg. Conditional outer loss[4.99,5]U/mg
and fraction[.998,1] are not confidence intervals. A distinct addback, physical
measurement/preparation identities, full nuisance coverage and sampling model
remain unknown. Do not manufacture them to make the derived cells populate.

The new recurring instruction, printed in chat before coding, is:
"Identify which activity-unit definition applies to the measured endpoint.
Select its exact quantity, molecular entity and time basis, and retain the link
to that endpoint. Do not borrow a unit definition from another readout or infer
comparability from equal units."

The investigation nominates this source relationship; deterministic readers
validate selected spans, parse the coefficient and calculate the conversion.
No blanket U alias, model-entered coefficient, silent unit relabeling or source
truth claim is authorized. The actual paper defines other units differently;
the definition must belong to the selected endpoint. Source/experimental identity
is separate from unit equality. The eight numerical formulas remain in015.

## Fixed ownership

Fresh unit owner: new literature_partner_defined_units.py and new
tests/test_literature_partner_defined_units.py only. Fresh consumer owner:
existing literature_partner_native_inputs.py, literature_partner_storage.py and
new tests/test_literature_partner_defined_inputs.py and
tests/test_literature_partner_defined_storage.py only. Coordinator: this contract,
source conversion/argument selections, episode descriptor/catalog wording,
recurring TASK, new integration examples and final independent review. All module
paths are under gene_annotation_episode/. Existing tests, core calculator, tool
graders, live processes/pins, original research packets and old history are not
owned by these coding workloads.

## Defined-unit selected input

Keep existing literature.partner.source.populate and input_mode=native_source_spans.
Both rate.unit and nonnull rate.spread.unit accept an ordinary old Witness OR
this closed object (no scientific numeric values are arguments):

```
{kind:source_defined_rate_unit, witness:Witness,
 definition:{bridge:Witness,clause:Witness,amount:NumberSelector,
   amount_unit:Witness,time_unit:Witness,endpoint:Witness,
   endpoint_entity:Witness,definition_entity:Witness}}
```

witness selects the literal U/mg header (ordinary whitespace aliases allowed).
bridge selects the complete source statement defining ONE unit; the finite
initial grammar recognizes "One unit was equivalent to" or "One unit was defined
as" (case/whitespace normalization allowed). clause is the one selected numerical
definition within that bridge, not another endpoint's clause. amount selects a
positive literal coefficient. amount_unit selects pmol,nmol or µmol/μmol/umol;
time_unit selects min/minute or s/second, with the stated per-time denominator.
Support the source's "1 µmol of NADH oxidized per min" and equivalent selected
quantity/entity/per-time clauses, including "2 µmol ferrocenium per min".
Unsupported relationship syntax is a specific failure, not an invented mapping.

bridge,clause,amount,amount_unit,time_unit and definition_entity must retain the
same source/artifact/representation and nested byte containment. Validate actual
clause order and association (amount, quantity unit, optional of, entity, optional
oxidized/reduced/formed, per, time unit); no clipped prefixes/denominators. The
bridge's ONE-unit prefix must actually introduce the selected clause. The unit
header must be a whole U/mg token; U/ml, mU/mg or clipped units are unsupported.

definition.endpoint is the same canonical witness as the arm's endpoint, not a
free identifier. endpoint_entity is contained in that endpoint witness, and its
exact NFKC-normalized molecular token matches definition_entity in the clause.
Do not infer synonyms or same entities from partial substrings. Unknown endpoint
or an unmatched entity cannot authorize a source-defined conversion. The selected
relationship remains a scientific interpretation; these checks establish source
custody and the concrete association, not its biological truth.

## Pure helper exports and exact saved shape

Export defined_rate_unit_schema(), parsed_defined_rate_unit_schema(),
read_defined_rate_unit(selection,*,sources,endpoint),
convert_defined_source_number(number,unit),
validate_defined_spread_unit(number,unit,*,sources).
Use existing _Sources, ordinary witness/NumberSelector schemas and
ExperimentalContractError. No SQL, I/O, network, model, core or episode calls.

The parsed return is the old four ParsedUnit fields plus definition:
```
{witness:EnrichedWitness,raw_unit,canonical_unit:pmol/min/mg,multiplier,
 definition:{bridge:EnrichedWitness,clause:EnrichedWitness,
   amount:ParsedNumber,amount_unit:EnrichedWitness,time_unit:EnrichedWitness,
   endpoint:EnrichedWitness,endpoint_entity:EnrichedWitness,
   definition_entity:EnrichedWitness}}
```
ParsedNumber keeps the existing exact shape. multiplier is the source coefficient
times quantity-to-pmol (1,1000,1000000) times per-minute conversion (1 or60).
Use exact rational intermediates, checking finite/nonzero representability.
Validate record consistency when converting; a caller cannot change a repeated
parsed value, coefficient, scale or boolean multiplier. Raw values and original
unit definitions remain in the saved evidence. No sampling model is introduced.

validate_defined_spread_unit rechecks actual source spread custody and any
immediately printed absolute unit. An explicit U/mg must agree with the selected
defined unit; a different supported plain rate unit must agree in canonical
dimension and scale. Percent/relative or unsupported explicit units fail. Missing
explicit unit retains the supplied common-unit association. Do not silently
ignore a different adjacent unit. The common native reader must handle an explicit
defined spread unit independently of the main value, retaining its actual scale.

## Consumer and saved authority

The native input schema accepts the new unit branch; old argument structures
remain accepted unchanged. Plain-only inputs still return extraction_v2, exactly
as in016. Any defined unit in a main rate or spread produces
literature_partner_inputs_extraction_v3. Top-level extraction fields and the
eight numerical cells remain the same. Native evidence retains the enriched
defined unit; normalized core inputs keep canonical pmol/min/mg. The existing
calculator, typed row schema and source-factor bindings are unchanged.

Include every nested definition source in stable direct-input custody using the
existing root/data/literal/interpretation order then sorted unique nested sources.
Enforce receipts, assigned-page lineage and scoped ancestors for all sources.

Storage must read v1/v2/v3. Old v2 evidence must not acquire a definition field.
Saved v3 requires at least one defined input/evidence pair; saved shape/version,
arguments/evidence, endpoint link, nested witness/selector identity, raw tokens,
coefficient/unit meanings and normalized core/canonical metadata must agree.
Validate meaningful saved relationships without original source reads, numerical
parsing/unit conversion or defining helpers. Cache shape-only schemas as in016.
The original committed operation/request/outcome hashes remain authoritative.
Replay/project/admission cannot reacquire, recalculate or reinterpret sources.

## Required checks and limits

Check the actual source coefficient1µmol/min and a source-backed coefficient2;
unsupported/clipped units/definitions; wrong endpoint or molecular entity;
cross-source/representation/containment mismatches; point/limit meanings;
independent spread units; source receipts/scope/page lineage; old v2 unchanged;
new selected native operation; exact typed parent delivery; saved-only replay
with all old/new source/calculation helpers disabled and SQL query_only. Test
tampering, transactional rollback and source-defined version relationships.

Primary cases retain incomplete coverage and unknown physical measurement IDs;
native rates/limits populate, while unjustified controlled contrasts/addback
remain unavailable. Conditional research arithmetic is printed separately from
qualified production cells. This addition does not finish A105, the literature
goal, target transfer or W05. Both model runs continue on their unchanged pins.

## Integration clarification: unselected U spread and saved authority

The unit and consumer owners found that the old plain spread guard did not
recognize adjacent U/mg as an explicit unit. The new guard therefore accepts a
plain or defined parsed unit and is used for every NEW native spread extraction,
including otherwise-v2 inputs. A plain mean with an unselected U/mg spread must
fail, not silently acquire the mean's unit. Legitimate old-only output shapes
stay exactlyv2; saved old records are not reparsed or repriced. The old standalone
scalar helper is unchanged. Add a meaningful otherwise-v2 regression case.

The consumer may additionally compare the canonical saved payload digest with
its original committed artifact metadata after verifying that existing v1/v2
publication used canonical bytes. This supplements meaningful operand/definition
relationship validation; it does not replace it or reacquire/recalculate sources.
