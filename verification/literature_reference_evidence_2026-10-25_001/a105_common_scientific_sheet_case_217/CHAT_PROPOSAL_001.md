They should be **parts of one A105 scoring sheet**. Experiment-specific readers and calculators fill its relevant sections. Attribution means how well the observed effect is isolated to the molecule or intended change; relevance asks whether that observation answers the stated functional question. Neither substitutes for validity, comparability or uncertainty. The current implementation does not yet join all of this into an adequate common sheet.

Here is a concrete proposed common-sheet calculation using the retained P450cam paper. The mutant and WT proteins were assayed separately with electron-transfer partners. The product was chemically identified; NADH consumption was another endpoint. Product per NADH is useful, but by itself says nothing quantitative about contamination, precision or denominator accuracy.

| Numerical component | T252N versus WT | T252N/V253T versus WT | What it evaluates |
|---|---:|---:|---|
| Product turnover, Table3 |92/206=0.446602|132/206=0.640777|Observed relative product activity under the source comparison|
| Fitted saturation turnover, Table2 |54/124=0.435484|165/124=1.330645|Retention at saturation, a distinct functional resolution|
| Low-substrate efficiency, Table2 |(54/96)/(124/30)=0.136089|(165/388)/(124/30)=0.102885|Retention in the low-substrate kinetic limit|

The double mutant's saturation turnover can be high while low-substrate efficiency is low. These are different functional assertions, not contradictory repeats or alternative quality grades.

A second question is whether weaker binding could explain the product-activity loss. The paper gives Kd values WT1.8, N34 and double12µM. It specifies 2mM camphor for the NADH assay, but does not explicitly bind that concentration or the binding-preparation conditions to the product measurements. We can therefore calculate an explicitly conditional sensitivity case, not an observed correction:

`occupancy = S/(S+Kd)`, with stipulated free S=2000µM and a one-site equilibrium model.

| Conditional assessment | T252N | Double mutant |
|---|---:|---:|
| Binding-only predicted product ratio, occupancy_mutant/occupancy_WT |0.984169|0.994930|
| Observed product ratio minus that prediction |−0.537567|−0.354154|
| Residual activity ratio, observed/binding prediction |0.453786|0.644042|

These numbers test a named explanation. Under those assumptions, occupancy loss alone is small compared with product-activity loss. The residual still includes possible active-fraction, preparation, calibration and background effects; it does not isolate a catalytic-chemistry defect.

The proposed common sheet would connect the sections through an explicit response model where supported:

`observed product − other contributions = recovery × active fraction × nuisance response × occupancy × post-binding activity`.

Consequently, the test/reference post-binding activity ratio is the background-subtracted product ratio multiplied by the reference/test recovery, active-fraction, nuisance-response and occupancy ratios. Each factor needs its own relevant measurement or declared model. Missing controls stay missing; they do not become 0 or1. The full corrected ratio is unavailable for this paper.

For reliability, propagate the actual joint uncertainty of these same operands. For example, the log residual `D=ln(product ratio)−ln(occupancy ratio)` combines the complementary experiments. With an applicable joint variance, `D/sqrt(Var(D))` measures standardized disagreement with the binding-only explanation. The paper does not supply that covariance, so this cell is unavailable. Authentic-standard identification also supplies no numerical recovery or identity-error rate, and no numerical no-P450 blank or active fraction is reported. Those source gaps are different from the unfinished common-sheet binding/calculator/integration work.

The next implementation should add this assertion-and-assay comparison to the existing A105 compiler and preserve the numerical components, unknowns and shared measurements in one sheet. It should not merely add another extractor. The full proposal includes the scientific links, populated cells, exact function IO and separate investigation instructions. It is a proposal for feedback, not completed A105 or a change to the fixed goal.
