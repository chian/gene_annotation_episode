# A105 calibration case: section meanings and numerical conversion

Implementation/research evidence only. This document neither replaces the immutable user goal nor adopts a universal grade. A105 remains incomplete. The preceding goal turn answered the user's architecture question but changed no authoritative state: classify it as **no progress**. This turn resumes concrete scientific and engineering verification.

## Experimental definitions

Source: Application of WST-8 based colorimetric NAD(P)H detection for quantitative dehydrogenase assays, DOI 10.1186/s12858-019-0108-1, PMC6454709. Original retained XML SHA256: 86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698. Root inspected the original selected paragraphs, Tables 2–4 and original Figure 3 before this interpretation and then performed the required authority reset.

The G6PD is human, heterologously expressed in E. coli BL21(DE3), affinity purified, and quantified using Bradford protein measurement. The precise allele, construct boundaries, active fraction and numerical purity remain unresolved. Expression host and source organism are different facts. A gel appearance does not supply zero contamination or a measured active fraction.

The WST-8/1-mPMS endpoint is formazan absorbance at 450 nm, with 600 nm reference. NADPH reducing capacity is the reporter's immediate quantity. It does not directly identify the sugar product or establish productive stoichiometry. A reference wavelength is not the matched no-reaction blank.

## Populated section components

| Section/question | Original operands | Component and combination | Value | Limits |
|---|---|---|---|---|
| Calibration validity: NADPH detection in buffer | Table 2: prepared 8.6 nmol; measured 8.72 nmol | r=M/N; percent bias=100*(r-1); inverse recovery=1/r | 1.013953488372093; +1.395348837209302%; 0.9862385321100917 | All three reuse the same two operands. No independent validation follows from inverting recovery. |
| Precision at that level | Table 2 reported within-run CV 0.8%, between-run CV 1.7% | Retain reported CV and repetition basis; fraction=percent/100 | 0.008; 0.017 | Raw replicate/preparation data unavailable. Technical measurements across days are not independent biological preparations. |
| Control-signal separation | Table 2 reported Z-prime at 8.6 nmol | Source formula 1-3*(SD_positive+SD_negative)/abs(mean_positive-mean_negative) | Reported 0.99; not recomputed | Raw means/SD absent. Algebra permits negative values; the source's claimed 0–1 range and acceptance threshold are not adopted. Not functional confidence. |
| Calibration relation | Original Fig.3B printed fit | A=m*N+b; m=0.0999 absorbance/nmol, b=0.0166 absorbance | Reported R-squared 0.9994 | Raw residuals, slope uncertainty and calibration covariance unavailable. R-squared alone does not measure absolute bias or product specificity. |
| Enzyme activity recovery in serum | Table 4 G6PD: expected 1.024 nmol/min, measured 1.235 +/- 0.004 nmol/min, SD | r_activity=M/N; excess=M-N | 1.2060546875; 0.211 nmol/min | Enzyme spike, not isolated reporter standard. Mixture of enzyme response and detection response. |
| Precision of serum measured activity | Same measured activity and SD | SD/M | 0.003238866396761134 = 0.3238866396761134% | Describes measured-rate spread; no uncertainty of expected denominator or full recovery uncertainty follows. |
| Cross-method comparability | Table 3 purified G6PD WST-8 12.51 +/- 0.36 vs UV 14.88 +/- 0.39 nmol/min/ug | WST8/UV; relative difference=ratio-1 | 0.8407258064516129; -0.1592741935483871 | Non-intended enzyme concentration ratio (0.1/0.150)/(0.5/1)=4/3. Not isolated detector gain. |

Other Table 2 NADPH levels provide recovery checks 4.39/4.3=1.0209302325581395 and 12.98/12.9=1.006201550387597. These levels characterize a calibration setting; neither point count nor triplicate readings establishes independent preparation count.

## Justified numerical compilation

For a source-established linear calibration A=m*N+b, the inferred amount is N=(A-b)/m. If sample and matched no-reaction blank share the same applicable calibration, the endpoint rate is:

    rate = ((A_sample-b)/m - (A_blank-b)/m) / time
         = (A_sample-A_blank)/(m*time).

The intercept cancels once. Do not subtract it again from a response already blank-corrected. This expression evaluates measured endpoint rate; it is not annotation credit or a probability of function.

For a separately established multiplicative recovery r applicable to that same quantity and matrix, a justified corrected quantity is Q_corrected=Q_measured/r. The source buffer-standard recovery cannot silently correct the complete enzyme reaction or serum matrix. A measured calibration slope and a recovery computed using that slope may share error; applying both without a distinct residual-bias meaning can double-correct. Product-attributed activity would additionally require a quantitatively linked product contribution, not merely a product name.

The numerical sample/blank absorbances, applicable same-matrix linkage and quantitative product attribution are not established for this compilation. Consequently corrected functional activity is unavailable. Missing source linkage is distinct from the unimplemented pair-to-calibration-sheet reader described below. No absent factor becomes one.

## Contradictory or unresolved representations

Table 4 reports recovery 120.57 +/- 0.33%, while its displayed means yield 120.60546875%. Treating expected 1.024 as fixed would give 0.004/1.024*100=0.390625 percentage points, not 0.33. Preserve the reported recovery/spread and displayed-operand calculation separately; unrounded values and denominator uncertainty are unknown. Do not overwrite the source or infer an uncertainty model that resolves the discrepancy.

Table 3 specific activity 12.51 multiplied by the stated 0.2 ug enzyme spike gives 2.502 nmol/min, whereas Table 4 expected activity is 1.024. The derivation/linkage is unresolved; compatible units alone do not authorize substitution.

Substrate omission is described but numerical blank values are absent. The source also describes reporter interference by reducing compounds without NAD(P)H. Substrate omission alone does not isolate substrate-dependent reporter chemistry. Relevant complementary controls include a same-matrix reporter-standard recovery and a no-enzyme reaction containing the substrate; a product-specific measurement addresses a separate functional-identity weakness. These are possible scientific investigations, not mandatory runtime steps or gates.

## Sheet and implementation implications

One logical A105 sheet needs separately interpreted numerical sections for calibration/method validity, precision/uncertainty, comparability, effect attribution and assertion-specific relevance. This is a mapping of the user's required meanings, not five new evidence axes or new overall scalar grades. The scientific meaning and dependency of each number must survive the typed return. Assay-specific components can populate several sections; that does not make repeated representations independent evidence.

Current activity correction code consumes an already reported dimensionless k. The source reader cannot yet derive and bind k from a selected prepared/measured calibration pair while retaining whether it is reporter recovery, enzyme-activity recovery, applicable matrix, held-out validation and original operand sharing. The existing NADH extinction calculator has a different optical relation and must not be applied to WST-8 formazan by name or unit resemblance. These are implementation limitations, not statements that the paper lacks every relevant calibration fact.

The next calibration implementation must pair exact source fields with recovery, signed bias and justified inverse correction; preserve reported precision and derived/report conflicts; distinguish control type; leave unsupported applicability unknown; and deliver through existing LiteratureEpisodes without modifying W05 or controllers. A combined A105 sheet and common subscore compilation remain unfinished. This review does not establish scientific adequacy or expand to A106.
