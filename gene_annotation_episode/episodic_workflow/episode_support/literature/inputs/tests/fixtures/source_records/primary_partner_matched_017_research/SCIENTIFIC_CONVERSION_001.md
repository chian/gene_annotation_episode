# Research conversion: one Bcd/Etf paper, conditional partner contrasts

This is a primary-source research packet, not an implemented sheet, production
reader, model-backed LiteratureEpisode, new axis or credit calculation. The
parent has not yet performed its own post-paper reset or adopted this conversion.
No second experimental paper was opened. The retained chem_bcd_etf packet was
followed by a complete16-document reset; the primary Methods, Table2, Results
and Discussion were then inspected, followed by a second complete reset before
this interpretation. Both reset records retain actual document hashes. The
active attachment goal and current ten-axis/A101 boundary were read last.

The primary source is Li et al., J Bacteriol190:843–850, DOI10.1128/JB.01417-07,
[PMC2223550](https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/). The publisher's
paper is retained as the actual acquired PMC HTML, with a deterministic text
projection and exact byte witnesses. This is not a PDF acquisition or a new
transcription of numerical assay data. Primary acquisition returned HTTP200;
an additional browser reopen encountered a challenge page and is not treated
as a scientific source.

## Experimental objects and directed inference

The studied subject is the intact, natively purified butyryl-CoA dehydrogenase/
Etf complex from Clostridium kluyveri DSM555 grown on ethanol/acetate. This is
not an isolated recombinant Bcd monomer, mutant replacing wild type, or a mixture
of mutant and wild-type alleles. Partial protein sequencing identifies Bcd
CKL_0455, EtfA CKL_0457 and EtfB CKL_0456 in the complex. No engineered construct
boundaries or tag are reported for this native purification.

For the proposed partner comparison, the changed molecule is added ferredoxin
from Clostridium pasteurianum. Bcd/Etf and the other assay components coexist
with it; ferredoxin does not replace another tested protein. Hydrogenase from
C.pasteurianum is held present on both sides. The inference is therefore about
an intact Bcd/Etf preparation's endpoint under this defined reconstitution,
not a universal EtfA/EtfB requirement or an endogenous partner identity in another
organism. The paper reports qualitative loss of activity in separated subunit
fractions, but no quantitative subunit omission/addback series. That statement
cannot supply zero-valued Bcd-only or Etf-only arms.

## A matched nominal protocol with a defined measured endpoint

Table2's NADH-oxidation block reports7U/mg for Fd+Hyd and0.1U/mg for Hyd alone.
The latter is the Fd-absent arm with hydrogenase retained; using the no-addition
row would remove two molecules. Table2's footnote explicitly specifies the
following common nominal assay attributes:

| Attribute | NADH oxidation pair |
| --- | --- |
| Temperature and volume |25°C;1ml |
| Buffer |50mM Tris-HCl,pH7.5 |
| NADH / crotonyl-CoA |0.1mM /0.1mM |
| FAD / DTT |5µM /2mM |
| Purified Bcd/Etf amount |0.01mg |
| Hydrogenase |0.4U from C.pasteurianum, present in both selected rows |
| Intended changed variable |20µM Fd added versus absent |
| Readout |Photometric NADH oxidation; Methods specify340nm and extinction coefficient6.2mM⁻¹cm⁻¹ |
| Initiation and oxygen handling |Crotonyl-CoA addition; assays described as strictly anoxic |

The normalization is per mg of purified Bcd/Etf preparation protein, as the
specified subject protein mass in the common assay; it is not mg ferredoxin or
hydrogenase. One NADH-oxidation unit means1µmol NADH oxidized per minute. Thus
the displayed rates have the dimension µmol NADH/min/mg Bcd/Etf preparation.
Mass identity and the identity/purity of its active fraction remain distinct:
the paper does not show that every molecule in that mass is active.

These common method attributes support a nominal Fd-removal comparison. They
do not prove that every nuisance variable was controlled. The source does not
identify Table2's individual preparation/batch IDs, enzyme ages, physical run
IDs, row-level repeat counts, blank subtraction, or sampling uncertainty.
Table rows identify reported assay conditions; they do not themselves provide
an independent-preparation count or license inventing physical-measurement IDs.
Whether source row identity is sufficient for the current core's physical-ID
contract is an explicit parent interpretation, not established by different
number positions. Do not set condition coverage to complete from table layout
alone. Keep unestablished preparation/handling correspondence unresolved.

## Numerical conversion into the existing eight components

The following is **conditional research arithmetic**, assuming the displayed
table values and nominal comparison are accepted for the stated operands. It
is not a claim that the current reader has populated qualified derived cells.

| Existing component | NADH endpoint candidate |
| --- | ---: |
| reference_rate,W |7U/mg =7,000,000pmol NADH/min/mg |
| omitted_rate,O |0.1U/mg =100,000pmol NADH/min/mg |
| partner_loss,W−O |6.9U/mg =6,900,000pmol NADH/min/mg |
| partner_loss_fraction,(W−O)/W |69/70 ≈0.985714 |
| addback_rate,A |Unknown: no distinct addback measurement identified |
| addback_gain,A−O |Unknown |
| addback_fraction,(A−O)/(W−O) |Unknown |
| restored_reference_fraction,(A−O)/W |Unknown |

The loss fraction measures Fd-associated dependence of this measured NADH
endpoint under the selected assay conditions. It is not function probability,
experimental reliability, final annotation credit, or proof that the complex
cannot oxidize NADH by another route. If a distinct A becomes available later,
the existing primitive formula(A−O)/W combines loss and restoration without
counting the shared O twice. Here missing A prevents that combination; W must
not also be labeled addback merely because its mixture contains added Fd.

The same table has a second **different endpoint**: H2 formation measured with
Hyd1.6U held present. At37°C its Fd+Hyd row is5U/mg and Hyd-only row is<0.01U/mg.
Common nominal conditions are0.5ml,50mM Tris-HClpH7.5,2mMDTT,2.5mMNADH,
1mMcrotonyl-CoA,10µMFAD,0.05mgBcd/Etf and50µMFd when added. One unit now means
1µmol H2/min, and the same subject preparation mass defines mg. Conditional
nonnegative omission domain[0,0.01]U/mg yields outer loss[4.99,5]U/mg and
fraction[0.998,1]. The printed strict< is retained; using a closed outer domain
does not turn it into an observed zero or a confidence interval. The4.99 lower
edge is an outer bound, not an attained strict-limit endpoint.

NADH and H2 components must retain different endpoint identities and condition
sets. They are complementary readouts of a coupled system, not independent
replicates to average or multiply as two proofs. H2 formation requires the
indicator hydrogenase; its absence cannot distinguish loss of upstream Fd
reduction from inability to report that reduction. The present selected pair
holds hydrogenase present, but still evaluates a coupled readout.

## Qualifications that extraction must retain

The NADH table row contains7(14):14 is the value at37°C, explained by the
temperature footnote. It is not SD, SEM, replicate count or a second25°C rate.
The25°C omission0.1 must not be divided into14 to fabricate a matched effect.

Results prose gives0.3–0.4U/mg without both Fd and Hyd, while Table2 gives0.1
for its no-addition row. The prose concerns a double omission, not the selected
Hyd-retained omission, and the paper supplies no reconciliation that permits
replacing the selected0.1. Retain both statements and their provenance; do not
average them, call them technical replicates, or infer an uncertainty interval.

The authors explicitly describe preparation-to-preparation variability, enzyme
lability, reaction lags and rate nonproportionality to added enzyme. No row-level
SD/SEM/CI or independent-preparation n is supplied in Table2. Both primary pairs
therefore have unreported spread and unquantified preparation/measurement
uncertainty. The two tested ferredoxin sources are described as producing similar
results; that does not establish row-specific independent replicates.

Product mass spectrometry and subunit identification complement a coupled
activity inference; they do not supply a numerical contaminant fraction or prove
that the single Bcd chain owns every observed activity. A direct, quantitative
separated-component reconstitution, preparation-specific controls and rate/amount
linearity would address distinct attribution/comparability gaps. This paper's
qualitative subunit separation does not provide those missing numerical operands.

## Paired extraction fields and implementation gap

Retain source row/block identity; directed subject and partner; exact endpoint;
subject preparation mass denominator; partner state/amount; constant Hyd amount;
shared protocol factors; unreported preparation/run identity; numerical point or
strict limit; temperature-specific interpretation of parentheses; and endpoint-
specific activity-unit definition. Native values and provenance remain usable
even where the core's qualification requirements leave derived cells unknown.

Current literature.partner.source.populate supports explicit rate-unit spellings
such as µmol/min/mg. The actual table says U/mg, with U defined in a separate
footnote. Neither pretending that U/mg is a literal µmol/min/mg quote nor installing
a universal U alias is appropriate. A future reader needs an explicitly selected,
source-backed unit-definition relationship identifying which endpoint's U is
used. Its deterministic conversion can then use1µmol/min perU and the preserved
mg denominator. This is an identified implementation gap, not implemented source
population. No production code or current sheet contract was changed here.
