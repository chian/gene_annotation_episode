# A105 calibration numerical sections: original-source review

This review applies the fixed goal after root's complete post-packet reset in POST_PACKET_RESET_001.json. It is implementation/scientific evidence, not a replacement objective or a completed whole-A105 sheet.

Source: Application of WST-8 based colorimetric NAD(P)H detection for quantitative dehydrogenase assays, DOI 10.1186/s12858-019-0108-1, PMC6454709. Root independently reread original Methods/Results paragraphs and complete Tables 2–4, all 14 original admitted rows, and both complete saved extractions. The source XML hash is 86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698. Final 006 and fully read 004 extracts are identical; their typed forms differ only in the selected-publication sheet references. They are repeated engineering representations of the same original measurements, not independent experiments.

## Definitions and numerical scope

The enzyme is human G6PD, expressed in E. coli BL21(DE3), affinity purified, and quantified by Bradford assay. Original source organism, expression host, assayed preparation and active enzyme amount are distinct. The selected source does not establish an allele, full construct boundaries, numerical purity or an active fraction.

The standard control prepares NADPH in Tris buffer and measures a formazan optical response using WST-8/1-mPMS. The enzyme assay reports a calibrated NAD(P)H production rate from its optical response; it does not directly identify the sugar product. The reporter's reference wavelength is not a numerical reaction blank. A described blank procedure does not supply a measured zero background or zero contamination.

The second control adds G6PD to fetal bovine serum and reports a rate after subtraction of the serum-only rate. Its analyte/control subject is the enzyme; the endpoint is the reported NAD(P)H production rate detected optically. It combines enzyme activity, matrix response and reporter response. It is not a direct reporter-standard experiment and does not isolate detector gain.

## Populated numerical cells

| Actual control | Source operands | Calculation | Value and scoring meaning |
|---|---|---|---|
| NADPH buffer standard, Table 2 | prepared 8.6 nmole; measured 8.72 nmole | M/N; 100*(M/N-1) | recovery 218/215=1.0139534884; relative bias 60/43=+1.3953488372%. Numerical detection recovery against that prepared amount. |
| G6PD activity spike in serum, Table 4 | expected 1.024 nmole/min; measured 1.235 nmole/min | M/N; 100*(M/N-1) | apparent activity recovery 1235/1024=1.2060546875; +20.60546875% relative to the stated expectation. Not isolated detector bias. |
| Serum measured-rate precision | measured SD 0.004 nmole/min and mean 1.235 nmole/min; source global mean±SD definition | SD/M | 4/1235=0.0032388664, or 0.32388664%. Repeatability of the reported measured rate, not full recovery uncertainty. |
| Reported versus displayed serum recovery | reported 120.57%; displayed means above | M/N-reported_percent/100 | 227/640000=0.0003546875 fraction, or 0.03546875 percentage points. Both representations survive. |

Legacy spellings `nmole` and `nmole/min` are retained exactly in source witnesses and normalized without changing quantity. Complete-token aliases were required; cutting `nmol` out of `nmole` would have been an invalid witness. Root also found that the alias needed consistent dimensional rejection in a fraction field: an explicitly printed amount cannot become a recovery percentage just because another header says percent. The final guard corrects that case.

## How the numbers combine

These components have explicit arithmetic relationships. Recovery M/N and its bias M/N-1 are alternative views of the same two observations. An applicable measured quantity Q could be corrected as Q/r. For the buffer pair, the inverse factor is 215/218=0.9862385321. That arithmetic alone does not establish that the factor applies to an enzyme reaction or another matrix. This operation supplies no linked target measurement, so `correction_for_other_measurement` remains unavailable for both controls.

The serum measured-rate SD yields SD/M but does not supply Var(M/N). The expected rate's uncertainty, covariance with M and raw joint repetitions are missing from this selected calculation. No independence or zero denominator uncertainty is assumed. If one explicitly fixed the denominator only as a hypothetical illustration, the displayed SD would give 0.390625 percentage points, while the source prints 0.33. That hypothetical calculation is not substituted for the reported spread or actual recovery variance. Unrounded data and denominator relationships remain unresolved.

The stated expected serum rate also cannot be replaced by Table 3 specific activity times spike mass merely because units fit. The separate Table 3 value 12.51 nmole/min/ug times 0.2 ug is 2.502 nmole/min; Table 4 expectation is 1.024. The source linkage/derivation is not established. The typed limitation explicitly retains that unresolved basis.

## Reliability, validity, attribution and relevance

The standard recovery/bias belongs to calibration validity under its actual buffer conditions. The measured SD/CV belongs to precision under its actual repetition basis. The activity-spike recovery belongs to a matrix activity-response section. These meanings are separately retained in the numerical return; the existence of separate storage modules does not make extra evidence axes.

A small CV can coexist with an offset against the stated expectation. Precision therefore cannot erase a calibration or comparability weakness. Neither result quantifies productive sugar-product formation or isolates every molecular contribution. Relevant complementary experiments would measure reporter-standard recovery in the complete applicable matrix, substrate-dependent response without enzyme, and an independently identified/quantified product. They address different weaknesses and are not automatically independent repetitions of one endpoint. This is scientific guidance, not a required episode itinerary or runtime gate.

The source describes triplicate work and five successive days for standard precision. That is not 15 independently prepared biological samples. Calibration recovery, bias and inverse reuse operands; the same source data in two stored sheets remain shared measurements. No publication count, generic category weight or invented function probability is supplied.

## Implemented versus remaining work

The selected operation now targets the paired extraction/calculation and numerical sections through existing LiteratureEpisodes. It returns exact requested cells and source meanings; root's separate frozen integration verification is in progress. The controlled example requests seven components from each of two controls. Extra internal cells are not silently delivered to the parent. The parent retains its own TASK and receives the admitted numerical facts as STEERING.

The buffer table reports within-run and between-run CV, but this operation has no dedicated fields for those source-reported precision statistics. Its unavailable SD-derived CV means that absolute SD was not supplied to this operation, not that the paper omits precision. Reported Z-prime and linear-fit slope/intercept conversion also remain distinct implementation gaps. The existing NADH extinction converter is not the WST-8 formazan calibration model. These limits remain explicit in the prior 172 gap record.

A common whole-A105 numerical sheet, appropriate assay-specific compilation and scientific coverage are still unfinished. This calibration increment does not establish A105 adequacy or finish the other literature responsibilities. Final annotation credit and target correspondence remain outside this work.
