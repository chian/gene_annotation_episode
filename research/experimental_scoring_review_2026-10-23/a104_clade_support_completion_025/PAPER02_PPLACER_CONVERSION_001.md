# Paper 02: pplacer measurements relevant to A104

Matsen, Kodner and Armbrust (2010), *pplacer*, DOI
<https://doi.org/10.1186/1471-2105-11-538>. Inspected the relevant definitions,
algorithm, uncertainty, simulation and table passages of the 28-page author
manuscript <https://matsen.fhcrc.org/pplacer/pplacer.pdf>. The PMC landing page
returned a challenge. No claim of a separately inspected publisher version,
downloaded dataset, visually inspected screenshot, or executed pplacer run.

This method comparison uses a fixed reference tree/alignment and an aligned
query, rather than a protein perturbation experiment. Placement location is
the variable. The manuscript also evaluates simulated reads with known origin.
No biological genotype, coexistence construct or functional assay is an A104
operand here.

Equation 3 normalizes optimized edge likelihoods by their sum. Equations 1–2
instead integrate attachment position and pendant length with a prior for
posterior placement. Equation 4 defines EDPL as the double weighted sum of
distances between attachment positions, divided by total reference-tree
length. Native weights condition on the supplied tree/alignment/model.

**Proposed conversion after the full authority reset:** sum native weight on
the declared crown's interior edges. Retain EDPL as placement dispersion, not
another multiplier of that same uncertainty. Its inter-attachment distances
do not measure the query's pendant length; this is an inference from the
definition. Record pendant and query-to-reference distances separately for
the user's outlier limitation. A reference-relative distance attenuation would
be our numerical proposal, not a pplacer probability of function. Fixed-tree
and functional-reference uncertainty remain separate inputs.

The complete post-paper reread is recorded in
`AUTHORITY_RESET_PAPER02_001.json`. The latest human steering was read last,
before this conversion. No new runtime gate or requirement to run this method
is introduced.
