# HFP/IMP nominal amounts: source review028

The original source supports two separately assigned, point-form nominal recipe
concentrations: **8.4 μM HFP** and **8.8 μM IMP**, added to the respective flasks
of the one-pot assay. They are not the endpoints of an 8.4–8.8 μM interval.
This conclusion follows the original retained HTML paragraph p0195 and its exact
text projection, not the earlier successful scripted assay output or025's pass.

## Experiment and source relationship

The molecules are Aquifex aeolicus PP17/HFP and PP11/IMP, heterologously expressed
in E. coli. The paper describes native-form constructs in pET20b with a stop
before the C-terminal histidine tag; it separately describes a tagged HFP
preparation for the contaminant-isomerase investigation. Do not silently assign
that latter tagged construct to the one-pot assay. No tested-organism genotype
perturbation is implied by this purified-enzyme comparison.

The one-pot mixture contains RibBA, RibD, lumazine synthase, riboflavin synthase,
GTP, Ru5P and NADPH in 50 mM Hepes pH8.0 and10 mM MgSO4. HFP and IMP replace
one another across vessels in this comparison; the paper does not say both
phosphatases coexist in each assay flask. The intended comparison is phosphatase
identity and its effect on pathway product formation. The nominal enzyme
concentration also differs and must therefore qualify amount comparability.

The critical source sentence says that the mixture is divided **between two
flasks**, followed by separate HFP and IMP amount/entity pairs and addition to
**each respective flask**. Here “between” governs the allocation among vessels.
It does not introduce a numerical concentration range. The broad prefix regex
incorrectly consumes from that preposition through a later conjunction. For
IMP it additionally consumes the preceding HFP quantity/entity pair.

Both flasks are made anaerobic under argon and incubated at55°C for4.5h.
Riboflavin is assessed spectrophotometrically by the screening method; the main
text contrasts a riboflavin signal with HFP against its absence with IMP. That
is not a quantitative zero for IMP or a measured rate ratio. The recipe says
one-pot assays were completed in triplicate, without establishing independent
preparations or supplying concentration SD/SEM/covariance.

The source also says400 μl starting reaction buffer and two flasks of250 μl
each. Preserve those reported statements. This review neither repairs the
volume accounting nor computes nmol from it. The reported μM values are usable
as nominal molar concentration reports without resolving that volume wording.
The exact stock/preparation aliquot, active fraction and monomer-versus-dimer
molar convention behind these nominal reports are not established here.

## Exact custody and locations

- DOI:10.1016/j.jbc.2025.108443; PMC12051542; Experimental procedures,
  **One-pot assay**, original HTML **p0195**.
- Original retained HTML:/tmp/episode-published-cases/specificity/raw/PMC12051542.html;
  SHA256:ccba0fb19356c840512ddcdc05924d00060fc4bcd52e31a79106932e7c6d649e.
- Exact UTF8 text projection:/tmp/episode-published-cases/specificity/raw/PMC12051542.txt;
  SHA256:cdf6419babae49be1235b38b89370e16346766edf1483614cef3183b85898e12.
- HFP amount:bytes[49870,49877), `8.4 μM`; subject:bytes[49878,49881), `HFP`.
- IMP amount:bytes[49886,49893), `8.8 μM`; subject:bytes[49894,49897), `IMP`.
- Short pair witness:bytes[49870,49897), `8.4 μM HFP and 8.8 μM IMP`.
  This witness contains the pairs but is insufficient alone to establish the
  separate-vessel relationship; retain the whole allocation/addition sentence.
- Incubation witness:bytes[50036,50052), `55 °C for 4.5 h`.
-027 replay source identity:source_dccb4ee9a6a961f77ad6e354;
  text artifact:artifact_cdf6419babae49be1235b38b89370e16346766edf1483614cef3183b85898e12.

The companion custody artifact records the exact complete sentence offsets.
025's original supplement-access exception remains preserved: retained response
was HTML, not the requested DOCX. **The supplement remains uninspected.**

## Convert to the existing A105 numerical sheet

Keep investigation instructions, sheet meanings and populating functions
separate. The reader selects and retains the actual molecule, construct where
supported, preparation where supported, reported recipe basis, assay, intended
identity change, actual vessel arrangement, conditions, exact number/unit spans,
point/limit/approximation status, uncertainty and observation identity.

For the existing between-arm nominal-molar comparison, use HFP as numerator
and IMP as denominator; the orientation is explicit, not a source-derived
preference for one protein. Derived quantities below use exact decimal
arithmetic on the reported concentration operands:

| Existing numerical cell | Calculation | Value | Meaning |
|---|---|---:|---|
| numerator_amount | source nominal HFP concentration |8.4 μM|Reported HFP recipe concentration|
| denominator_amount | source nominal IMP concentration |8.8 μM|Reported IMP recipe concentration|
| amount_difference |8.4−8.8|−0.4 μM|Signed nominal concentration imbalance|
| amount_ratio |8.4/8.8|21/22≈0.954545|Relative nominal concentration, HFP/IMP|
| reciprocal_amount_ratio |8.8/8.4|22/21≈1.047619|Same comparison with reversed orientation|
| conditional_mass_denominator_factor |not applicable|unavailable|No same-stock target/total-mass relationship|
| variance and standard-uncertainty cells |require owned covariance|unavailable|No SD/SEM/covariance is reported for these amounts|

The ratio numerically describes amount comparability outside the intended
identity change. It is not an overall relevance/reliability grade. These aliases
share operands and are not independent evidence to add together. They cannot
multiply an endpoint into a corrected activity without an appropriate source-
supported amount-response model. In particular, **8.8/8.4 must not become an
automatic correction to the HFP riboflavin signal**. There is no source-supported
combination of this amount ratio with an activity ratio in this bounded case.
The missing amount-response/active-concentration relationship remains a real
limitation for later numerical compilation; no fixed categorical substitute is
introduced and W05/final annotation-credit aggregation stays outside scope.

Effect isolation remains separate. Similar nominal loading does not establish
purity, active-site concentration or that every activity in the preparations
belongs to the labeled protein. The main text's contamination controls address
the apparent isomerase attribution, rather than turning nominal concentration
into an effect-isolation multiplier. The approximate5/7mg/ml stock comparison
cannot be applied to either nominal molar amount without actual preparation and
normalization linkage. Repeated source representations are the same report.

## Additive correction to retained selections

The numerical HFP/IMP assignment in025/027 is supported. No correction of those
two reported values is warranted. Qualify027's short `nominal_pair` assignments:
they identify the two amount/entity pairs, but the short quote alone does not
establish separate vessels, actual shared conditions or the intended identity
comparison. Use the complete sentence and assay paragraph as relationship
witnesses. Do not overwrite prior selections, passes, failures or receipts.

The diagnostic error is truthful about current software rejection; it is not
scientific evidence that the source quantities form an interval. Until a shared
guard correction is agreed, preserve the partial/unavailable program outcome.

## Proposed guarded parser interface, before any coding

Use **one shared pure numerical-range classifier** called by both the shared
`_relation` interval check and native `_number`'s repeated interval check. Keep
the original full field contexts, exact source bytes, offsets and all other
numeric/qualifier/unit guards. No amount-specific alternate parser, witness
cropping, bypass flag or HFP-number exception is justified.

Proposed interface: `_between_numeric_scope(prefix, suffix)` returns one of
`numeric_interval`, `non_numeric_coordination`, `unresolved`, without calculating
or assigning any scientific operand. Invoke it only for the broad
`between ... and` candidate. A narrow syntactic implementation must distinguish
the numerical endpoints joined by `and` from a completed nonnumerical object
of `between` followed by another coordinated clause. Reject `numeric_interval`
and `unresolved` through the existing interval error; waive only this one broad
candidate for positively recognized `non_numeric_coordination`. The direct
`between/from/range/CI`, dash and `to` guards still apply independently.

The distinction must consider both sides of the selected scalar and preserve
outside qualifiers. A direct numerical first endpoint after `between`, including
recognized approximation/comparator wrappers, remains an interval candidate
even if its upper endpoint has a unit, entity or other modifier. An unexplained
intervening phrase must remain unresolved. A list's entity labels alone do not
disprove a range. Positive coordination recognition needs a completed
nonnumerical allocation object and an independently completed quantity-addition
clause; recognizing nouns or verbs must remain a finite generic lexical grammar,
not a paper-specific regular expression or an LLM interpretation override.

If a maintainable conservative grammar cannot establish that distinction, retain
the current partial failure rather than weakening genuine range protection.
This is a proposal, not a settled implementation or a passing parser claim.

All contrasts below are **synthetic proposed tests**, not source measurements:

| Full context, selected numerical tokens | Required result |
|---|---|
|`The mix was divided between two vessels of 180 μl each and 3.2 μM enzyme A and 4.6 μM enzyme B were added to the respective vessels.`;3.2,4.6|Separate points after positive clause recognition|
|`The buffer was distributed between three wells, and 3.2 μM A, 4.6 μM B and 5.1 μM C were added to their respective wells.`;3.2,4.6,5.1|Separate points; no hardcoded pair count|
|`The concentration was between 3.2 and 4.6 μM.`;3.2,4.6|Reject either interval endpoint|
|`The concentration was between approximately 3.2 μM and 4.6 μM.`;3.2,4.6|Reject either endpoint; retain approximation context|
|`between 3.2 μM A and 4.6 μM B`;3.2,4.6|Reject/unresolved; entity labels do not authorize points|
|`between a low concentration and 4.6 μM`;4.6|Unresolved/reject; unknown first endpoint|
|`between 3.2 on day one and 4.6 μM on day two`;4.6|Unresolved/reject; no greedy noun-list escape|
|`The mix was divided between two vessels and <3.2 μM A and approximately 4.6 μM B were added to each respective vessel.`;3.2,4.6|Retain limit/approximation; never exact points|
|`The mix was divided between two vessels and 3.2–4.6 μM A was added.`;3.2,4.6|Reject range independently of allocation clause|
|`The mix was divided between two vessels and 3.2 to 4.6 μM A was added.`;3.2,4.6|Reject range independently of allocation clause|
|`A received 3.2 μM and B received 4.6 μM.`;3.2,4.6|Ordinary separate points; no `between` candidate|

Source/read provenance is in RESET_AND_CUSTODY_001.json. No production, test,
shared consumer, pin, saved run or earlier research record was edited. No
configured-model run, import-based diagnostic or new source acquisition occurred.
