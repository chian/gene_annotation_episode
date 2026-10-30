# Paired extraction and numerical proposal

Unimplemented research proposal unless a current function is explicitly identified below. Fits sections of the same logical A105 scoring sheet; it does not add evidence axes or install a standalone overall scoring module. Source witnesses, custody and scientific calculations remain separate. A numerical cell is not compulsory when the paper cannot support the required estimand.

## Actual paper input and resulting cells

| Extraction input, source and meaning | Proposed populated output | Populator and implementation status |
|---|---|---|
| Fig5/main line81, S5: Ru5P39.7%, R5P60.3%; integrated equilibrium composition in HFP-containing preparation | Native fractions0.397/0.603; endpoint ratio1.51889; normalized sum1 | Ordinary deterministic percentage conversion/ratio/sum after source assignment. Research arithmetic executed in ARITHMETIC_001.json; not registered as a production reader by this workload. |
| FigS5 original bitmap: printed normalized integral1.00 and1.52 | Ratio-derived fraction0.603175; shares the same physical spectrum as the percentages | Deterministic arithmetic after literal figure-label transcription. No new peak integration or independent-validation contribution. |
| Methods line161: Bradford7mg/mL, visual HFP estimate approximately5mg/mL | Approximate nominal target/bulk mass ratio~0.714286 and conditional denominator factor~1.4 | Arithmetic demonstrated. Existing amount modules were not reread here; no claim that this exact approximate mass mixture conversion is bound in production. Approximation must survive, and no active-fraction or g role is assigned. |
| FigS7, DOCXP311, labelled five-preparation figure | Count4positive/5tested; finite cohort fraction0.8 | Count from source-assigned identities; production cohort-count reader not established here. This is no error rate or overall quality multiplier. |
| FigS8 protein/peptide identification report | RpiA7unique peptides,101/219 coverage; HFP27unique peptides,161/203 coverage; native instrument-reported counts | Narrow reported-MS-table/image reader would preserve these counts, search settings and sample identity. Specific producer not established in the eight inspected interfaces. No new Mascot/Scaffold execution, spectral-count calibration or activity share inferred. |
| Main line83 and S6, before/after purification and endpoint timings, construct and heating changes | Retained before/after observations; timing contrast not eligible as matched intrinsic-activity ratio | Source-grounded relationship judgment, with additional differences and unknown target recovery explicitly represented. Generic witnessed interpretations exist; no specific fully automated effect-isolation producer established. |
| No matched reported contaminant rate or quantitative activity bound | g=null; attributed_rate=null; isolated_share=null; corrected_activity=null | Source-information gap. Existing assay/compiled rate readers and q−g arithmetic already exist; absence does not justify building duplicate functions. |

## Proposed source contributor record

This is an illustrative typed scientific extraction contract to discuss, not an implemented schema. Every selected item has a source witness or exact null; provenance remains outside recurring TASK text.

```
contributor:
  molecule: source literal / null
  organism: source literal / null
  preparation_relationship:
    same_sample_supported | related_preparation | different | unknown | conflicting
  evidence_kind:
    molecular_identification | measured_activity | quantitative_activity_bound
  native_measurement:
    value: number / null
    unit: source unit / null
    qualifier: point | approximate | lt | le | gt | ge | nondetection | unknown
    denominator: source literal / null
  numerical_role:
    detected_alternative | same_scale_additional_contribution | unknown | conflicting
  applicability:
    endpoint: matched | different | unknown | conflicting
    scale_and_denominator: matched | different | unknown | conflicting
    conditions: matched | different | unknown | conflicting
    preparation: matched | related_with_explicit_model | different | unknown | conflicting
    component_model: additive_supported | nonadditive | unknown | conflicting
  covariance_ownership: source-bound joint estimate / null
```

The concrete case instantiates RpiA as a **molecular identification** in the HFP preparation, with role detected_alternative. Its measured_activity is null. No conversion of101/219 coverage,7peptides,27total spectra, or the cohort4/5 into same_scale_additional_contribution is authorized. MS sample-to-tagged/heated kinetic sample linkage remains unquantified: do not assume all named HFP samples are the same aliquot or preparation. Source context should retain that exact distinction.

Proposed preparation comparison additionally binds before/after construct, expression host, coexistence, purification, temperature, substrate, sampling window, target amount, contaminant amount, endpoint, calibration, blank and recovered active amount separately. Missing linked quantities are not set to equality merely because the publication intends a purification control.

## Targeted producer behavior

1. A source reader selects literal quantitative observations and their units/bounds/denominators without assigning biological causation. Figure-label, DOCX-table and MS-report readers are ordinary report readers; no biological software suite is requested.
2. The investigating episode selects the relevant physical roles and relationships. A specifically scoped judgment can explain that MS identification names a contributor without measuring its activity. This is the permitted nonnumeric interpretation; no category gets converted to0.25/0.5/0.75.
3. A deterministic assembler permits the current contaminant-rate input only when an actual source rate or supported derived same-scale rate/bound exists with the asserted applicability. Existing direct g routes remain usable. Current bounded g propagation remains an implementation limit, separately from this paper's lack of an actual g bound.
4. Applicable calculations preserve the native mixture measurement and derive a separate corrected component. They do not overwrite the original measurement or silently clamp a negative residual.

This is not a proposal to make a string-enum validator the scientific judge. It can enforce the selected contract; it cannot establish additivity or selective perturbation from a control label. The eight inspected code modules are evidence of supported routes and arithmetic only. End-to-end installed catalog, persistence and delivery of this newly proposed contributor record remain unverified and unimplemented here.

## Explicit combination and uncertainty

When its assumptions are justified for an initial-rate measurement, the scientific model is `q=E_HFP*a_HFP+g` after the applicable blank. Rearrangement supplies `(q−g)/E_HFP`. Reporter recovery and measured nuisance-condition response then give the current sheet's `(q−g)*v/(k*E_HFP*u)`. The isolating subtraction is distinct from calibration, amount normalization and comparability multipliers.

The current compiler already provides `attributed_rate=q−g`, `measured_endpoint_per_selected_amount=q/E`, `calibrated_measured_endpoint_per_selected_amount=q/(kE)` and full correction, preserving partials and shared dependencies. The numerical representation proposed here would feed those cells rather than create a new total.

For the simpler r=q−g, uncertainty is `Var(r)=Var(q)+Var(g)−2Cov(q,g)`. For a corrected activity, first-order propagation is `J Σ Jᵀ`, plus a separately justified distinct residual variance where that model calls for one. Shared calibration, mixture measurements or depletion controls can induce covariance; unknown covariance is not zero. A calculated contaminant contribution and its source measurement are the same contribution, not two pieces of verification. No variance or confidence interval can be populated here from a generic triplicate declaration alone.

No synthetic numerical mixture is introduced: this paper lacks the inputs, and an invented paired-rate example would not resolve its specific missing relationship. Actual available arithmetic appears above; actual causal-rate cells are explicitly null. The full common reliability/validity/relevance compilation remains unfinished. These source-specific values must not be summed as independent evidence or multiplied into an invented overall experimental quality score. Target relevance and transfer remain outside this source isolation calculation.
