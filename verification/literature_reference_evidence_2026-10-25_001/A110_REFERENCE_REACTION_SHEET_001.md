# A110 experimental reaction constraints: first executable subset

Additive proposal applying A110026 equations3,5,6,7. This is not all of A110,
an adopted annotation-credit policy, a balance validator or a target-transfer
calculation. Original sheet026 and reader crosswalk remain preserved.

## Primary source and experimental distinctions

Knorr et al., PMC6265302, DOI10.1038/s41467-018-07563-6. Root reviewed all47
body paragraphs, the full supplementary text, original Fig3 and supplementary
Fig2,3,7 and Table3 images, then the full mandatory authority/current-sheet
reset (primary_csid_requirements/PARENT_RESET_001.json).

Purified recombinant CsiD carries an N-terminal6His tag, cloned from BW25113
and expressed in BL21(DE3). NMR used10mM glutarate and10mM alpha-ketoglutarate
in20mM ammonium acetate pH7.25,300K; Fig2 specifies overnight incubation.
Supplementary Fig2 reports succinic acid:L-2-hydroxyglutaric acid=1:1.
This is a reported product-pair ratio, not separately measured substrate
consumption, an oxygen/product coupling yield or a pathway flux. Its independent
replication, sampling SD and quantitative recovery are unreported. Product
identity from NMR/LC-MS and enantiomer discrimination complement that ratio;
they are not additional independent repetitions of it. The separate oxygen
electrode assay conditions and activity cannot be inserted as its denominator.

Purified C-terminal6His LhgO reduces UQ1; methods report100uM UQ1 and650nM
enzyme, and supplementary Fig7 reports0.33+/-0.002umol/min/mg and Vmax5.1nmol/min.
The stated plus/minus kind is unspecified. Assay volume and complete usable
resource inventory are not given there. Do not multiply concentrations into
total amounts without volume or treat enzyme/FAD as consumed once per turnover.
No detectable oxygen consumption by purified LhgO has no quantified detection
limit: it is neither exactzero nor an upper limit of zero. Membrane oxygen
consumption includes respiratory-chain coupling. DCPIP is an artificial acceptor
readout, not directly measured alpha-ketoglutarate production.

Native membrane quinone-pool changes were measured after1h at25C under nitrogen,
with150ug membrane protein in200uL and5mM L2HG or succinate. Those pools do not
establish a steady flux or respiratory throughput. Do not combine this volume
with the separate purified-enzyme kinetic assay.

Source conflict: Results Par8 says HQNO above80uM abolished oxygen and DCPIP
readouts; Fig3d shows residual DCPIP activity at100uM while oxygen reaches the
plotted baseline. Preserve text and image disagreement. No precise graph value
or dose-response score is extracted in this increment.

Supplementary Table3 uses mean+/-SD,n>=3; exactn unknown. Dashes mean not
detectable, with no numerical limit. AVA/valine separation prevents unlabeled
AVA/total quantification; its delta-gabT637+/-68uM must not be relabeled total
AVA. Mixed13C/15N mass shifts and precursor impurity do not satisfy the older
UbiUV oxygen-binomial isotope operator. No isotope-flux or pathway-yield score
is inferred here.

## Numerical cells and limited interpretation

For corrected, same-basis numeratorN and positive denominatorH, y=N/H. An
already reported ratio enters as such, with its reporting/measurement scope.
Retain calibration/correction limitations; no unit background or recovery is
invented. For each named claim/alternative prediction mu, retain residual
y-mu and squared residual. Raw independent units give e=mean((y-mu)^2).
Known summary mean,m,SD,s,and exact independentn give
e=(m-mu)^2+(n-1)*s^2/n. Unknownn orSD leaves e unknown; nominal squared
mean residual is retained separately. A direct measurement explicitly declared
as one independent unit is different from a source summary with unknownn.

s=(e_alt-e_claim)/(e_alt+e_claim), bothzero=>0. Fixed named alternatives
combine by minimum; absent alternatives remain unknown. Also retain every
absolute error: positive relative contrast is not absolute validity. No claim
that the score is a probability, a calibrated quality scale or annotation credit.

Simple same-period resource capacity z=min(U_i/a_i) for strictlypositive
consumption coefficients; demandv>0 gives f=min(1,z/v), s_supply=2f-1.
Each resource must belong to the same declared amount/rate basis and compartment.
Unknown resources remain constraints: known finite caps give an upper bound,
never measured sufficiency. Explicit bounds can produce conservative coverage
enclosures. Bounds are physical domains, not confidence intervals. Regeneration,
competition and inaccessible supply require their measured model; they are not
inferred from reagent listings. No network optimization is implemented here.

Primary NMR example: reportedy=1,predictionmu=1, nominalresidual=0, nominal
squaredresidual=0. e, comparison score, correction-qualified coupling and
native resource coverage remain unknown. This original source is not a
synthetic matched-positive example.

Explicit synthetic check from sheet026: y=[.7,.9],mu_claim=1,mu_alt=.5 gives
e_claim=.05,e_alt=.10,s=1/3. UsableU=[12,6]umol,a=[1,1],demand10umol gives
z=6,f=.6,s_supply=.2. The arithmetic is illustrative, not paper data.

## Reader/judgment instructions, kept separate from sheet arithmetic

Identify the assayed molecule, construct and exact experimental system. Name
what the numerator and denominator count, whether they are supplied, consumed,
formed, or instrument signals, and whether their units/time windows match.
Distinguish a reported product-pair ratio from reaction yield. Preserve raw
source values, uncertainty kind, independent-unit identities and contradictions.
Only designate independent units when the source establishes that design.
For a resource question identify usable amount/capacity, consumption coefficient,
compartment, duration, competition and regeneration; supplied reagents alone
do not establish intracellular sufficiency. Provide named alternative accounts
and their prediction meanings only when scientifically specified. Return unknown
when the source cannot answer the question. Calculators, not the model, compute
ratios/errors/budgets. No candidate annotation is required to start reading.

## Completion and handoff

Source fields, numerical functions, selected persistence, prompt rendering and
typed return/reopen are separate deliverables. This document alone implements
none. Source identities retain dependencies with A105. Later W05 work owns
combination with other axes and target correspondence. No A101 implementation,
A109 restoration, new axis/episode, controller change or historical repricing.
