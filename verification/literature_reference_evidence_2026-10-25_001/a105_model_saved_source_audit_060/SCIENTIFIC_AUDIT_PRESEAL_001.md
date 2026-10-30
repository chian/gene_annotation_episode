# Scientific audit of model030 selected populations29 and31

The selected numbers and endpoint-specific unit conversion are correct for the
published H2 assay. Their functional meaning is narrower than a loss of intrinsic
Bcd/Etf activity: one comparison removes the hydrogenase that produces the
observed H2, while the other removes the electron carrier. These are two omission
contrasts in one published assay series, sharing the same reference observation.
They are not independent replication or a complete experimental reliability score.

This audit inspected the actual saved model selections, not an operator-prepared
replacement. The original run and its pin remain untouched. No new model call,
episode action,scientific population,parent return or credit was created.

## Source, inspection and reset

Li et al., *Coupled Ferredoxin and Crotonyl Coenzyme A (CoA) Reduction with NADH
Catalyzed by the Butyryl-CoA Dehydrogenase/Etf Complex from Clostridium kluyveri*,
Journal of Bacteriology190:843–850(2008), DOI10.1128/JB.01417-07,
[original source](https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/).

The original030 source is source_0b8cba800e58dcd678d58126. Its198495-byte retained
HTML and54148-byte deterministic text are authenticated by the original artifact
metadata. Own060 read all403 retained text lines, the actual original HTML Table2,
and the selected numerical/meaning/unit-definition packet. No figure pixels,
supplement,second paper or network acquisition was inspected. Figure captions
and Results were read as part of the full source text, without treating them as
new digitized measurements.

Before scientific conversion, own060 then read the COMPLETE applicable authority
set,current696-line sheet,complete current experimental contracts,native rate
reader and rate calculator,active goal again and latest human instructions LAST.
RESET_READ_RECEIPT_001.json records49/49 fully displayed chunks,301657bytes and
26 document entries. The read count is not source coverage or experimental credit.
The historical sheet's target-transfer,pooling and candidate formulas are not
adopted by this scoped audit.

## Actual experimental arrangement

The assayed preparation is native purified butyryl-CoA dehydrogenase/Etf complex
from C. kluyveri DSM555, grown on ethanol and acetate. This is a purified
multisubunit preparation, not an isolated Bcd polypeptide. The paper identifies
the41,36 and28kDa subunits through partial protein sequencing as Bcd,EtfA andEtfB.
No engineered allele,construct boundaries,tag or quantified active fraction is
reported for these selected rates. The model correctly leaves construct and
physical measurement/preparation identity fields unknown rather than supplying
an inferred construct.

Both experiments retain that complex in the assay. Added ferredoxin and
hydrogenase coexist with it; neither replaces its Bcd or Etf subunits. The helper
proteins are from C. pasteurianum. The paper reports purified/commercial
ferredoxin gave essentially identical results, but does not identify a lot or
independent preparation count for each selected Table2 number.

Table2's H2/ferredoxin-reduction section and footnotea specify0.5ml at37°C:
50mM Tris-HCl pH7.5,2mM DTT,2.5mM NADH,1mM crotonyl-CoA,10μM FAD and0.05mg
purified Bcd/Etf preparation. Where indicated,50μM ferredoxin and1.6U hydrogenase
are added. Reactions begin by addition of crotonyl-CoA. General H2 Methods
specify anoxic sealed serum bottles,gas/liquid equilibration by shaking,and gas
chromatography at1-minute sampling intervals. A chromatographic standard curve
is mentioned, but no numerical calibration recovery/error distribution for
these rates is supplied.

Normalization is per mg of the Bcd/Etf preparation added to the assay, not per
mg total mixed protein including added hydrogenase or per mol active Bcd.
The source's Bradford protein assay establishes a preparation protein measure;
it does not establish active-site amount or a turnover number. The50μg input is
common across these H2 mixtures. It must not be borrowed from the0.01mg/25°C
NADH-oxidation or TTC sections of the same table.

The observed endpoint is H2 formation. Ferredoxin reduction is inferred through
coupling to the hydrogenase reaction; it is not a direct optical measurement of
ferredoxin redox state. Hydrogenase both makes the measured gas and supplies a
route for oxidation of reduced ferredoxin. Its omission changes the reporter
reaction and the coupled system's electron sink. This distinction is material
to effect isolation even though the physical gas endpoint is the same.

## What the model actually selected

At the coherent readonly capture,2026-10-26T19:32:04.431164Z,the child episode was
active with no completion. Its assignment requests source-reference evidence and
five descriptive rate components,not current-target credit. Both operations
are actual completed literature.rate.source.populate selections in
episode_76758a673dea6a01ef47fb2b7252facac1945c143bf2a10ebea32ab9bc9c4343.

| Selected decision | Reference | Test | Intended difference established by the two table rows |
| --- | --- | --- | --- |
|29|Fd+Hyd,5U/mg|Fd,0.02U/mg|Omit hydrogenase while ferredoxin remains|
|31|Fd+Hyd,5U/mg|Hyd,<0.01U/mg|Omit ferredoxin while hydrogenase remains|

The model selects the H2-forming clause of Table2's actual multi-endpoint unit
definition:1U corresponds to1μmol H2 formed/min. It does not apply the NADH or
TTC definition merely because the same unit symbol occurs. Thus5U/mg becomes
5μmol H2/min/mg and0.02U/mg becomes0.02μmol H2/min/mg; the scale is1 for this
canonical unit. These are real table entries, not the coefficient1 in the unit
definition or an unrelated protocol number.

In the retained text, the selected H2 section heading is bytes18477–18556,
Fd0.02 is18578–18582,Hyd<0.01 is18587–18592,and full-mixture5 is18602–18603.
The section's Table2 title and normalization support start earlier; its endpoint
unit clause is19868–19896 and full unit-definition sentence19772–19897.
All intervals are UTF8 half-open extents. The source artifact identity and exact
quotations are retained in PUBLIC_SELECTED_ACTIONS_001.json and the original
saved payloads. Original HTML Table2 independently verifies the row/column
association rather than relying only on a flattened text numeral.

The selected intended_change witness is only the literal full-mixture label
Fd+Hyd. It authenticates text but by itself does not identify *which* component
was omitted. The two selected condition rows supply that distinction. A future
interpretation instruction should require the explicit comparison and each
component's assay role; the broad label must not become a mechanistic conclusion.

## Paired extraction fields and numerical components

Let a be the full-mixture H2-specific rate and b the indicated omission mixture's
rate. These are descriptive rates under the declared Table2 protocol. Arithmetic
combines them through a−b,b/a,and1−b/a; it does not multiply an intuitive
applicability grade into them.

| Required extraction and relationship | Existing numerical cell/calculation | Saved value for29 | What the number evaluates |
| --- | --- | ---: | --- |
|Actual full-mixture datum5; correct H2 unit definition; preparation mass denominator|reference_rate=a|5μmol H2/min/mg|Magnitude of the coupled system's observed gas formation|
|Actual Fd-only datum0.02 under the same H2 protocol|test_rate=b|0.02μmol H2/min/mg|Residual gas formation when hydrogenase is omitted|
|Same physical endpoint and normalization; identified deliberate omission|rate_difference=a−b|4.98μmol H2/min/mg|Difference in measured coupled H2 response associated with that omission|
|Reference denominatora=5,nonzero|retained_fraction=b/a|0.004|0.4% of the reference gas rate remains|
|The same numerator/denominator,not another experiment|fractional_decrease=1−b/a|0.996|99.6% reduction in the measured gas endpoint|

These five cells depend on two published numbers. In particular,0.004 and0.996
sum to1 and are alternative descriptions,not two independent reliability factors.
The value0.996 cannot be interpreted as99.6% confidence in molecular function,
99.6% Bcd catalytic loss,or a measured fraction of signal attributable solely
to Bcd. Removing the H2-producing catalyst creates a distinct effect-isolation
question. The preparation-level gas comparison remains useful numerical evidence
about the coupled assay's component dependence.

For31,the actual saved reference is again5. The test datum is a strict upper
limit<0.01,so test_rate.value is null,threshold0.01,boundlt. The saved
rate_difference,retained_fraction andfractional_decrease points remain null
with censored_measurement. This is correct for the installed reader/calculator's
finite point-contrast route: it does not turn the limit into an exact0 or0.01.

For clarity about possible later numerical treatment, **audit-only descriptive
printed-summary arithmetic**, holding the printed reference5 fixed,would give
b/a<0.002 and a−b>4.99. Those are not current saved cells,implemented censored
likelihoods,confidence intervals or identified bounds on unknown true means.
They require a separately declared bound representation in a future supported
route. This audit neither changes the saved outputs nor adopts that extension.

### Uncertainty,model and dependence

Neither selected Table2 rate has a stated SD,SEM,CI or per-row independent
replicate count. The model leaves uncertainty unreported,countnull,sampling
basisunspecified,dependenceunknown andobservation_modelnone. Accordingly:

- Mean-SE cells are null with mean_uncertainty_unreported.
- For29,difference_se is null with dependence_unknown; no diagonal covariance
  or independent-sample model is fabricated.
- Conditional profile and bounded index cells remain null. A large ratio or
  fraction cannot supply their missing noise/model inputs.
- For31,censoring additionally prevents a point difference or its standard error.

The paper expressly states absolute and relative activities varied across
preparations,the complex was labile,reactions could have a lag and rates were
not always proportional to enzyme amount. These qualifications prohibit treating
the reported specific activity as a universal linear turnover law or assigning
zero uncertainty. They do not numerically specify a variance. The report of
losing50% activity over2–3days at4°C describes a separate stability observation;
it is not a measured correction factor for either selected Table2 arm.

Both operations reuse exactly the same source artifact and byte extent for
the full-mixture5. This proves reuse of the same **published observation
representation**,even though the underlying preparation/run identity and
replicate count remain unknown. It rules out treating the two contrast records
as independent full-mixture replicates. The common reference uncertainty would
induce covariance between their contrasts if modeled; its value is unknown.
Equal labels or equal numerical values are not the basis of this conclusion:
the original source locator is identical.

## Bearing on annotation quality and remaining limitations

**Comparability.** The source specifies a common H2 assay protocol and common
Bcd/Etf preparation input for the listed mixtures. The intended difference is
the stated partner omission; that difference is signal,not a comparability
penalty. Actual preparation age,batch identity,active fraction and replicate
matching for individual rows remain unknown. No numerical outside-change
comparability correction can be extracted from those unknowns. The common
nominal50μg dose is not a proof that active Bcd amounts were identical.

**Effect isolation.** The assays establish that high H2 formation by the full
mixture depends on added ferredoxin and hydrogenase. The no-Hyd comparison alone
does not distinguish failure of upstream ferredoxin reduction from absence of
the reporter/electron sink. The no-Fd comparison is informative about the role
of the electron carrier in the coupled chain. Neither isolates an individual
Bcd/Etf subunit or proves physiological partner necessity in C. kluyveri: helper
proteins here come from C. pasteurianum. There is no native-genome or coexpression
grader in this audit.

**Claim relevance and specificity.** These outputs support a scoped statement
about the purified complex operating in a coupled NADH/crotonyl-CoA/Fd/Hyd
system. They do not establish direct intrinsic H2-forming activity of Bcd,
a monomeric enzyme function,a Kcat,a binding constant,universal substrate
specificity,or a target-to-reference transfer. The fixed target remains gene001;
this reference experiment supplies no sequence/structure correspondence score.

**Complementary experiments.** The same paper's NADH-oxidation subsection,
alternative acceptor TTC,substrate omission and mass-spectrometric product check
address different aspects of electron flow and crotonyl/butyryl conversion.
Their protocol temperatures,amounts,readout molecules and unit definitions must
be retained separately. For example,NADH Fd+Hyd7 at25°C(or14 at37°C) must not be
substituted for H2 Fd+Hyd5. These experiments can constrain the reporter-omission
interpretation,not automatically count as independent repeats of the H2 rate.
Direct ferredoxin-redox measurement or a supported separately measured reporter
response would help isolate that missing relationship. No new such measurement
or correction is manufactured here.

**Numerical compilation.** The existing source rate difference and ratio/fraction
formulas are fully specified and their saved values are reproduced. A statistical
evidence index remains unavailable without actual uncertainty/dependence/model
support. The sheet's corrected-activity equation a=(q−g)/(kEh) cannot be populated
by relabeling the no-Hyd0.02 as a measured contaminant blank g or assigning
recoveryk=1,condition responseh=1 or active amountE from missing inputs. The
partner omission is the intended experimental change,not a measured h penalty.
No new overall grade,likelihood,weight or final A105/W05 scalar is defined by
these data. This is a genuine remaining component-population gap,not permission
for a default0/1 or a categorical replacement.

## Concrete interpretation-instruction proposal for the future reader consumer

This is a proposed scoped scientific instruction,not a coded prompt or runtime
gate,and it does not insert the entire scoring sheet into TASK:

> Determine which measured endpoint changes when each named component is omitted
> from this assay. Identify the native assayed preparation,the complete reference
> and omission mixtures,and which molecules coexist. Read the exact unit
> definition for that endpoint and its normalization denominator. For each changed
> component,decide whether it catalyzes the asserted upstream reaction,produces
> the measured reporter signal,serves as an electron carrier/sink,or has an
> unresolved role; a component may have several roles. Explain from the supplied
> Methods and table which inference the numerical contrast supports. Preserve
> unknown physical/active amounts,uncertainty and preparation identities. Treat
> repeated source cells as shared data and complementary endpoints as distinct
> measurements. A reporter omission does not by itself measure intrinsic
> upstream activity loss or molecule-specific signal attribution.

Allowed future interpretation meanings should distinguish
measured_system_endpoint_only,upstream_activity_isolated,reporter_role_unresolved
andconflicting,in addition to independently declared component roles. Their
source witnesses and actual interpretation belong beside the numerical cells;
these enum labels themselves are not scores. A concrete future typed contract
and its native return consumer still need separate design/review. No such new
field or implementation is silently added in this audit.

## Actual proof and its limits

SOURCE_AND_ARITHMETIC_RECEIPT_001.json independently verifies all658 files of
the original030 pin,all78 selected witness occurrences,the original HTML Table2
row associations,exact reference locator reuse,and exact decimal arithmetic.
Actual imports are from030's pin. The audit freshly runs its unchanged pure
reader and calculator against the captured original source bytes; both complete
extractions and both complete sheets equal the saved model-selected payloads.
This is explicitly a new **offline audit recomputation**,not source-free runtime
reconstruction and not another native selected operation.

The original saved requests,payloads and public selected results agree. No
operator operands were injected into the model run. The model's real choices
have been checked rather than replaced. The capture used SQLite mode=ro directly,
not a Store constructor that installs tables. The active run may continue to
write independently; no whole-live-database stability claim is made.

This proves source correctness of these descriptive numbers and identifies their
scientific limits. It does not prove parent typed delivery,C4 first-receipt
authentication,source-free readonly post-return reconstruction,controller
completion,all model decisions,all available graders,complete A105 reliability,
later literature axes or the full goal. Those remain the parent's integration
and completion responsibilities.
