# A110 source conversion 01: NfnAB

Status: proposed sheet arithmetic, not accepted scoring policy. Sources: Wang et al., DOI [10.1128/JB.00612-10](https://doi.org/10.1128/JB.00612-10), [PMC2944534](https://pmc.ncbi.nlm.nih.gov/articles/PMC2944534/). Separate correction: DOI [10.1128/JB.02550-14](https://doi.org/10.1128/JB.02550-14), [PMC4334188](https://pmc.ncbi.nlm.nih.gov/articles/PMC4334188/).

The outcome sought here is a numerical test of a proposed reaction's electron and cofactor account. Activity magnitude itself belongs to A105; subunit presence belongs to A107. Neither is awarded a second independent score here.

## Experimental definition

The tested reaction uses purified recombinant *Clostridium kluyveri* DSM555 NfnAB, expressed together in *E. coli*, with tags on both subunits, and FeS reconstitution. NfnA and NfnB coexist in the assay. This is not wild-type/mutant replacement. Ferredoxin and hydrogenase came from *C. pasteurianum*. The relevant comparison changes limiting cofactor amounts and reaction direction, not the protein genotype. Base assays were anaerobic, 37 °C, pH 7.0. The forward and reverse assays differ in enzyme amount, measurement technique and regeneration system, so they are complementary tests rather than matched independent repeats.

## Source values and derived cells

| Source location | Reported numerical quantity | Defined derived quantity | Value and limitations |
|---|---|---|---|
| Fig. 3A caption | About 1.1 µmol NAD+ supplied per 1 µmol H2 at endpoint | H2/NAD+ supplied | 0.909091 mol/mol; supplied NAD+ is not a direct simultaneous consumption measurement |
| Fig. 3B caption | About 2.2 µmol NADPH supplied per 1 µmol H2 at endpoint | H2/NADPH supplied | 0.454545 mol/mol |
| Fig. 4A caption | About 0.11 µmol NADH supplied per 0.10 µmol net NAD(P)H formed | net reduced-pyridine-nucleotide increase/NADH supplied | 0.909091 mol/mol; net is NADPH formation minus NADH loss |
| Fig. 4B caption | About 0.22 µmol NADP+ supplied per 0.10 µmol net NAD(P)H formed | net reduced-pyridine-nucleotide increase/NADP+ supplied | 0.454545 mol/mol |
| Fig. 6 and Discussion | 5 mol reduced ferredoxin allocated as 2 to HydA, 2.5 to NfnAB, 0.5 to Rnf | allocation residual | 5 − (2 + 2.5 + 0.5) = 0 mol; this is the authors' proposed scheme, not measured branch flux |
| Discussion | Conditional available energy magnitude 100 kJ/mol; ATP synthesis cost 60–80 kJ/mol ATP; proposed gain 1.25 ATP | possible ATP ceiling | 100/[80,60] = [1.25,1.666667] mol ATP/mol pathway turnover; costs and substrate scenario are not measured in this experiment |

The actual product/consumed-substrate ratios would require recovered residual substrate and gas recovery. Do not silently relabel the supplied amounts as exact consumption. Slope uncertainty, preparation count and raw plotted data are not numerical inputs supplied in the inspected text. The narrative reports reproducibility across preparations, but that is not a numeric n.

## Proposed conversion into a numerical scoring component

For a declared chemical quantity y, claim prediction c and specific alternative prediction a, define squared errors e_c=(y−c)^2 and e_a=(y−a)^2, in the same squared units. Define the **signed chemical discrimination cell**

    s = (e_a − e_c)/(e_a + e_c).

This is a proposed bounded numerical contrast, not a probability or native publication score. If both errors are zero, set s=0 because the observation does not distinguish the models. Scaling all three values into another molar unit leaves s unchanged. Unknown alternative prediction leaves s unknown. An unnamed universe of alternatives does not receive a fabricated numerical prediction.

The reverse coupled reaction predicts H2/NADPH=0.5 when the hydrogenase reports one H2 per two-electron ferredoxin reduction. A simple uncoupled transfer of both electrons of each NADPH to ferredoxin predicts 1.0. Using the approximate Fig. 3B value:

    y=5/11; c=1/2; a=1
    e_c=1/484; e_a=36/121
    s_reverse=143/145=0.986206897.

This tests this particular uncoupled account. It does not exclude unspecified side reactions. Using supplied substrate in place of consumed substrate and assuming complete hydrogenase reporting are explicit measurement-model assumptions.

The coupled forward reaction predicts net NAD(P)H change/NADH supplied=1. A simple NADH→NADP+ transhydrogenation predicts net change 0 (one NADPH formed, one NADH consumed). From Fig. 4A:

    y=10/11; c=1; a=0
    e_c=1/121; e_a=100/121
    s_forward=99/101=0.980198020.

These two chemical questions receive a proposed equal split within one stoichiometry block:

    S_stoich=(s_reverse+s_forward)/2=14399/14645=0.983202458.

The denominator two counts two prespecified reaction-direction constraints; it is not a paper or laboratory count. Figs. 3A and 4B remain internal checks on the same reactions, not extra independent evidence. This block can later enter the joined sheet's explicit weighted sum. It cannot by itself fill native pathway supply or organism-transfer cells.

## Bookkeeping distinct from experiment

The proposed overall reaction is

    Fd_red(2−) + NADH + 2 NADP+ + H+ → Fd_ox + NAD+ + 2 NADPH.

Half-reaction addition gives 2 e− from reduced ferredoxin and 2 e− from NADH, balanced by 4 e− consumed reducing two NADP+. The unchanged NAD and NADP molecular skeletons cancel separately. With relative redox-charge notation, both sides sum to +1; the H+ accounts for the net one hydrogen difference. This is an exact algebraic conservation check of the stated account, not experimental proof of catalysis and not a full ionic-speciation calculation.

## Comparability, isolation, uncertainty and dependence

Comparability is a separate question from effect isolation. Each molar comparison uses one assay's own denominator. Cross-direction measurements are not pooled as if made under identical regeneration conditions. A numerical correction between directions is unavailable, so the block reports the mean of two named constraints, not a common effect estimate.

Effect isolation concerns the link between the measured readout and the chemical amount. Hydrogenase couples ferredoxin reduction to H2; gas calibration and recovery, ferredoxin redox state and regeneration systems are part of that measurement model. The 380-nm measurement observes a difference of two pyridine-nucleotide quantities, not NADPH alone. The paper explicitly identifies ferredoxin absorbance interference in a different rate assay; its 8-versus-23 U/mg discrepancy must not be scored here as a stoichiometric contradiction. Complementary independent chemical quantification would constrain these limitations; it is not a compulsory itinerary.

No slope SD/SE/CI is reported in the inspected numerical captions. Therefore the displayed s values are approximate point calculations with statistical uncertainty unknown. They must not receive an invented confidence interval. The joined sheet defines interval propagation when bounds become available; absent bounds remain missing. Repeated technical gas samples are not biological/preparation replicates. The same underlying slope values and activity data retain shared-evidence links to A105.

## Inspection and reset record

Primary inspection: main Abstract/Introduction, complete Methods, complete Results including Table 1, all six figure captions and complete Discussion; text extraction lines 90–145 and 130–1470. Plot pixels were not digitized, and reference papers were not read. A linked correction was separately read in full; it corrects affiliation only.

Complete authority rereads occurred (1) initially, (2) after primary inspection and before opening the correction, and (3) after correction inspection before this conversion. Truncated combined outputs were repaired by complete separate rereads. The exact authority list and call records are in `authority_reads.md`. Latest goal attachment and the human goal reminder were read last.

## Additive resource-budget illustration from the same observation

The Fig. 3B quantities also fill a narrowly scoped **supplied-NADPH budget for the reported endpoint**. The coupled account requires 2 mol NADPH per mol H2; the source reports approximately 2.2 µmol supplied for 1 µmol H2. On that retrospective endpoint basis:

    U_NADPH = 2.2 µmol supplied
    a_NADPH = 2 µmol NADPH/µmol H2
    v* = 1 µmol H2, the reported endpoint to be accounted for
    z_NADPH = U/a = 1.1 µmol H2
    f_NADPH = min(1,1.1/1) = 1
    s_supply,NADPH = 2f−1 = 1.

The source-reported inputs are approximate; the stoichiometric requirement and scoring transformation are the declared model/proposal. This budget asks only whether the **supplied amount** can cover that endpoint under the stated stoichiometry. It does not measure how much was consumed, usable intracellular supply, regeneration capacity, all other assay resources or a future physiological demand. The endpoint is explicitly retrospective, not a planning requirement inferred before the assay.

The residual supplied amount relative to that requirement is 2.2−2×1=0.2 µmol. It is a calculated surplus, not a measured residual substrate amount. This entire budget is another representation of the Fig. 3B observation already used in s_reverse. Its separate compilation weight is exactly zero in the joined NfnAB example: adding it as an independent favorable constraint would count the same chemical measurement again.
