# Proposed paired extraction and numerical additions for this A106 gap

Research proposal for parent review, not new governing instructions, approval requirements or adopted scoring weights. It preserves the current source-effect point formula and excludes target transfer/W05/candidate aggregation.

## Investigation meaning, distinct from the sheet

A relevant interpretation prompt should ask which panel and time each outcome concerns; which copy was removed/restored; what the CFU/OD/lag denominator is; whether values summarize raw or transformed observations; what each error bar means; which biological/experimental units are repeated; and whether arm/time observations are paired. Match reported summary uncertainty to its own endpoint and panel. Similar starting cells, an empty vector or a nonsignificant comparison do not numerically bound every nuisance. Native versus restored amounts must be measured on a commensurate basis before filling a comparability factor.

Those are concrete aspect-specific questions. They do not ask a model to generate arithmetic, a universal relevance grade or a free-form final score.

## Paired fields and cells

| Source information to extract | Numerical cell/calculation | Scientific meaning and missing behavior |
| --- | --- | --- |
| Actual observed endpoint, unit, arm,time; summary kind; mean scale/transform and its source support; exact number span or table cell; graph recipe if needed | Existing W/K/R and linked native summaries | Preserve raw CFU-density means; mean(log count) is not log(mean count). Graph-only means are graph-derived; absent extraction function is unfinished work |
| Error-bar/spread kind, magnitude and scale (raw endpoint or transformed statistic); source panel/caption | Per-arm reported_SD or reported_SEM cell, with origin and status | Preserve SD versus SEM and untyped/unknown. A reported confidence interval remains an interval with its stated level; it does not automatically supply variance |
| Number of independent units; exact repetition basis and source support; technical subreadings distinct | Count plus estimated variance of each mean | For source-supported independent experiment summaries, SD²/n; for a reported SEM, SEM². Unknown n blocks SD→SE, but need not block a directly reported SEM |
| Genuine pairing/block/unit identities across arms and time; supported covariance or raw matched values | Mean covariance matrix with original observation ownership | Unknown covariance stays unknown. Author-reported n does not establish independent arms. A repeated time course is not n independent assays |
| Raw table of unit IDs, arm/time, observations, technical readings and actual denominator | Unit summaries, then mean/sample covariance | Aggregate technical readings within their declared unit. For n independent paired vectors X_j, sample covariance S divided by n gives the covariance estimator for the vector mean. Different unmatched arms must not be artificially paired |
| W/K mean variances and Cov(W,K), when supplied/supported | variance_perturbation_difference=V_W+V_K−2C_WK; SE=sqrt(variance) | Valid estimate source/status retained. If only marginal SEs are known, an explicitly algebraic unknown-covariance range may be returned; it is not a confidence interval |
| R/K mean variances and Cov(R,K) | variance_restoration_difference=V_R+V_K−2C_RK | The same K contributes to both differences; no duplicate independent-control credit |
| Joint covariance of W/K/R, if supported | Cov(W−K,R−K)=C_WR−C_WK−C_KR+V_K | Preserve shared denominator/control effects even under a later explicitly supported independent-arm model |
| Same W/K/R and a justified approximation or full observation model | Conditional uncertainty of theta/restoration ratio | For theta, derivative `[2K/(W+K)^2,−2W/(W+K)^2,0]`; for f=(R−K)/(W−K), derivative `[-(R−K)/(W−K)^2,(R−W)/(W−K)^2,1/(W−K)]`. J C Jᵀ is first-order propagation, not an exact interval or universal normal model |
| Source/graph reading precision independent of reported biological spread | Separate digitization interval/reading-choice record | Uncertainty about locating a mean/error endpoint does not become SD, extra n or biological sampling covariance. Reuse the same axis calibration variables across all means/endpoints |
| Real nuisance amount comparison and applicable endpoint-scale nuisance bounds, including uncertainty/dependence | Existing C/I and `a=s*theta*r*C*I` | Unknown amounts or nuisance bounds stay unknown. Reported SE alone does not populate C/I or a confidence interval for this clipped/minimum product |

A finite version needs an explicit source-supported raw/transformed summary definition and uncertainty coordinate scale, with unknown/conflicting states. It could add per-observation records containing measurement identity, exact source selector, endpoint/unit,time/arm, value/summary-kind/scale, uncertainty kind+magnitude+unit+source, count and repetition basis. A separate covariance declaration would retain ordered original observation IDs, covariance values/source, estimated/known/unknown status and pairing basis. Model arguments nominate source fields; deterministic readers parse scientific numbers. Raw-source rows remain source data rather than model-authored measurements.

Retain optional inputs and the existing v1 interface through an explicit new version; do not silently reinterpret old `uncertainty_basis=unreported` or existing records. The proposal does not choose that public version name or allocate coding ownership. Extraction contracts and the sheet extension should be agreed together before a fresh implementation workload.

## Worked source-specific consequences

Figure6B reports SD,n3. If the mean and SD summarize raw CFU-density observations, each mean's estimated variance is SD²/3 under the reported independent-experiment basis. The source statistic scale is not explicit in the inspected material; log display coordinates alone must not settle it. Figure6A reports SEM,n3: its mean variance is SEM²; dividing that by3 again would be an error. A number transformed from a logarithmic axis must be in raw CFU units before subtracting an SD endpoint. If the statistic were instead the mean of log observations, recovering the raw arithmetic mean would require additional information, not exponentiation by assumption.

Conditionally on that raw-scale interpretation, for Figure6B120h's explicitly nominated graph readings, W≈3.9e7,K≈7.9e6,R≈4.1e7CFU/mL; SDs≈1.5e7,5.1e6,1.6e7. Derived SE estimates are≈8.5e6,2.9e6,9.0e6. The nominal point effect and restoration components survive. Unknown C_WK prevents a unique perturbation-difference variance; its plug-in algebraic range is[(SE_W−SE_K)²,(SE_W+SE_K)²], approximately[3.1e13,1.3e14](CFU/mL)^2. This is neither zero uncertainty nor a statistical coverage interval.

These are estimated variances from three experiments, not known population noise variances. No known-normal profile score or normal confidence interval is selected merely because these cells exist.

## Remaining concrete gaps

- A source reader for the proposed per-panel summary/uncertainty fields is not implemented by this research.
- The case's manual log-axis mean/error-endpoint recipe is reproducible analysis, not a production reader. A production implementation must preserve explicitly chosen axis transform, physical plotted quantity and error endpoints; it cannot force this plot through a linear-axis contract.
- Original colony counts, dilution/volume, raw unit-level replicates and cross-arm/time covariance were not found in the inspected materials. A raw-table summary path is useful generally but cannot invent a raw table for this paper.
- General joint uncertainty for the current nonlinear clipped restoration index remains a separate required function if supported inputs are later provided. A local reported SD/SEM addition must not be represented as having completed it.
- The numerical return must carry requested uncertainty cells and their meanings/unknowns through the ordinary typed boundary and reconstruct from saved facts without source reacquisition or recalculation. No new episode, observation, scheduler or final credit policy is needed.
