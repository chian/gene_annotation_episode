# A105 Fluc source-evidence audit, current implementation

This is an additive audit under the immutable user-supplied literature goal.
The retained Stockbridge et al. 2013 eLife paper packet, its additive
corrections, and the current channel/ion numerical contracts were examined.
It is not a declaration that A105 or a general reliability score is complete.

## Experiment and numerical meanings

The studied electrical preparation is purified, reconstituted Fluc-Ec2 from
an *E. coli* virulence plasmid, expressed in *E. coli* BL21-DE3. A low-density
bilayer experiment reports a representative dominant 1.8 pA insertion step
relative to a closed level at −200 mV, and a salt-gradient reversal summary of
53 ± 1 mV. The reversal summary comes from separate bilayers; the ±1 is not
identified as SD, SEM or a known covariance. The paper reports about 7 pS.
The selected source calculation is `1000 × 1.8 / abs(−200 − 53) =
1800/253 = 7.1146245059 pS` chord conductance. Treating −200 mV as the whole
driving force would give 9 pS and change the denominator. The source's 7 pS
and the calculated 7.1146 pS share the same physical current evidence.

The current also gives `1.8e−12 / 1.602176634e−19 = 1.1234716334e7`
elementary charge equivalents/s. That arithmetic does not establish the exact
fluoride-carried fraction, active channel count, pore count, membrane-native
rate, or activity per protein molecule. Its charge and chord cells are two
views of one current step, not two independent assays. Chord variance needs
amplitude, voltage and reversal covariance under the actual sampling ownership;
the printed reversal spread alone cannot fill it.

The separate liposome electrode experiment compares F and Cl efflux. The
source's Discussion reports F turnover above 30,000/s and Cl turnover below
30 ions/s. Under the paper's common-assay/unit interpretation their printed
thresholds divide to a nominal ratio above 1000. The F estimate is qualified
by dead time and vesicle-size assumptions. The source's wording applies to
“Fluc proteins” at paper-summary level; these selected bounds are not yet
construct-specific Ec2 measurements. The underlying chloride detector
threshold and unitary-turnover derivation are not supplied here. Consequently
the nominal ratio is not an exact physical or confidence lower bound, and Cl
nondetection is not zero activity. The source's approximate biionic
permeability-ratio lower limit around 100 and combined selectivity claim above
10^4 are distinct source interpretations, not additional independent repeats
or quantities recomputable from the two threshold numbers alone.

## Template placement and combination limits

The ion pair populates A105 **functional distinction/specificity** as a
qualified nominal threshold ratio, with two native bounded operands. The
current/voltage/reversal triple populates **signal and assay-condition
normalization** as chord conductance; current alone populates a charge-flow
quantity. All source identities, construct scope, condition applicability,
units, censoring and dependencies must travel with these numbers. A possible
fluoride flux equation would multiply charge equivalents by the fluoride
current fraction and the attribution fraction to the intended channel, but
those factors are unmeasured and the resulting cell remains unknown. A
liposome released fraction would divide `(plateau−initial)` by
`(detergent−initial)`; this packet has not selected those source values, and
the resulting fraction would not be an initial rate because the fast response
exceeds instrument dead time.

Electrical and chemical endpoints address different weaknesses: charge-flow
timing and unit events versus direct ion appearance. Their different membrane,
counterion, voltage-control and readout arrangements prevent unqualified
cross-assay division. The same paper does not establish independent protein
preparations for each selected observation. A closed-channel baseline is not
a protein-free control. No measured contaminant current, ion-attribution
fraction, joint covariance, native-membrane correspondence or overall A105
reliability/validity/relevance compilation follows from these selected data.

## Current implementation and verification

`literature_channel_inputs.py` and `literature_channel_calculations.py` have
electrical source selectors, unit checks, chord and charge arithmetic, and
conditional covariance propagation. `literature_channel_storage.py` binds a
selected LiteratureEpisodes operation, typed requested rows and cold saved
reconstruction. Its existing tests use synthetic electrical source text;
the newly assigned original-source electrical integration check is pending.

The separate `literature_ion_discrimination_*` path already reads the paper's
original XML threshold and reported-ratio statements, preserves approximate
and paper-summary scope, and returns a nominal ratio without promoting a
physical bound. Root independently ran its original-source pure test and the
three parameterizations of the selected original-source test: **4 passed in
45.45 s**. These are controlled selections, not a configured model's source
decision. The common `literature_a105_worksheet.py` currently lists nine
source formats and does not include the channel or ion format. That is a
compilation/interface gap; nine formats do not mean nine independent assays
or nine A105 scoring sheets.

## Reset provenance

After reading the retained Fluc paper packet and before the interpretation
above, root reread the complete immutable user goal; root AGENTS; complete
EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION, TOOL_KNOWLEDGE and
TASK_AND_STEERING; the TASK/STEERING and evidence-axis-review amendments;
both verbatim direction/recovery records; the complete W04 evidence-axis
instructions; the earlier numerical A105 example; complete per-paper AGENTS;
and SOURCE_CORRECTIONS. Root then read the current A105 worksheet, channel
reader/calculator/storage/prompt/render, ion calculation contract, and the
latest user instruction to continue. A prior combined tool display had
truncation, so the affected authority files were read again in separate
complete outputs before interpretation. No `GOAL.md` was used.
