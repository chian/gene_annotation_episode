# Original-source electrical application187

The current179 electrical reader and calculator accept the selected, unmodified
Fluc source measurements. The deliberately incompatible biionic pairing retains
its reported reversal measurement and makes its inappropriate chord calculation
unavailable. No production file was edited, source text normalized, graph
digitized, numerical fallback supplied or model inference performed.

The source is Stockbridge, Robertson, Kolmakova-Partensky and Miller,
[A family of fluoride-specific ion channels with dual-topology architecture](https://doi.org/10.7554/eLife.01084)
(2013), distributed under CC BY3.0. Its retained XML and the
[formal correction](https://doi.org/10.7554/eLife.01700) match the assigned byte
hashes. The correction swaps specified La1/La2 labels in Figure1A; it is not a
new experiment and does not change the selected Ec2 electrical quantities.

## Experimental definitions

The measured protein is Fluc-Ec2 from an *E. coli* virulence plasmid,
YP_001481330.1. It was expressed in *E. coli* BL21-DE3 using a synthetic construct
with the reported C-terminal LysC/His-tag tail. The selected electrical traces'
tag-cleavage state, exact native construct boundaries and active fraction remain
unknown. The other construct names in the common Methods sentence do not mean
that those proteins coexist with Ec2 in this measurement.

The current-step measurement uses Ec2 liposomes at0.1microgram protein/mg lipid,
fused into planar POPE/POPG bilayers. The source specifies300mM NaF cis and30mM
NaF trans, with trans as electrical ground. The nominal concentration ratio
must remain distinct from the source's stated eightfold ionic activity gradient.
The voltage is−200mV. The1.8pA value describes the dominant insertion-step
magnitude, not a mean across independent protein preparations or the actual
time-averaged current of all substates.

Figure3 defines zero current as the mean level of the fully closed channel.
That definition does not quantify a protein-free bilayer background. The source
reports63 insertion events from approximately50 bilayers; neither number is an
independent-protein-preparation count. The four-preparation count from the
separate Poisson-dump experiment is not borrowed. The observed unit is not
normalized to a polypeptide or pore: the source leaves one versus two parallel
pores unresolved despite the dimer evidence.

The53±1mV salt-gradient reversal and119±3mV biionic reversal come from the
distinct arrangements named in Figure2. Applying the former to the stated
single-channel salt-gradient condition is a source-supported conditional
interpretation across those experiments, not a claim of one bilayer,
one acquisition or independent errors. The selected caption does not name an
error type for the printed spreads.

## Paired extraction and numerical cells

`SOURCE_NATIVE_SELECTIONS_001.json` contains exact source-byte witnesses and
character selections within those witnesses. Numeric operation arguments are
not entered values. `apply_original_001.py::build_selections(raw,source_ref)`
can use the actual source reference created by a later authorized store.

| Numerical cell | Original selection or combination | Populated result | Meaning for evidence evaluation |
|---|---|---:|---|
| Current-step magnitude | Results, dominant insertion steps |1.8pA| The electrical signal under the stated baseline and arrangement; not isolated ion flux |
| Applied voltage | Figure3 title |−200mV| Retains the actual driving-condition sign convention |
| Salt-gradient reversal | Figure2 caption |53mV, printed spread1mV| Distinct source measurement; the spread is retained as unspecified |
| Reported conductance | Results, equivalent reported conductance |7pS| Source-reported result, retained separately from recalculated chord |
| Absolute driving voltage |abs(−200−53)|253mV| The applicable denominator for the defined chord |
| Defined chord conductance |1000×1.8/253|7.1146245059288535pS| Conditional nominal current/voltage combination; not an I–V slope or general validity score |
| Charge-equivalent rate |1.8×10⁻¹²/(1.602176634×10⁻¹⁹)|11234716.334029373 elementary-charge equivalents/s| Electrical charge flow; no automatic fluoride-flux or per-pore attribution |
| Chord variance | Requires the full applicable covariance of I,V,E|Unavailable| No covariance or error model is manufactured from the printed spreads |
| Chord standard uncertainty |sqrt(chord variance)|Unavailable| No sampling confidence level is implied |

The exact decimal-rational arithmetic preserves printed operands through the
calculation. It does not make them exact physical values. The reported7pS and
derived7.1146pS are dependent representations of these observations and must not
be counted as independent verification. Their displayed difference is not an
experimentally established bias or contradiction.

This is actual numerical combination inside A105's electrical measurement and
uncertainty sections. It supplies no universal reliability category, function
probability, target-transfer weight or final annotation credit.

## Contrasting arrangement

The second selection deliberately pairs the salt-gradient current/voltage with
the original119mV biionic reversal. It selects the119 and its printed3mV spread
at their own original positions. The source caption can witness both values
without making them the same measurement: their saved physical keys differ.

The reader retains119mV. The calculator returns
`different_electrical_arrangements` for the inappropriate chord rather than
using that value as the salt-gradient reversal. This constructed incompatible
pairing is a validation case using reported measurements, not a new experiment
or a synthetic scientific measurement.

## Attribution, relevance and remaining limits

The electrical result bears on an ion-conducting activity of the studied Ec2
preparation. The source's protein-reconstitution dependence and ion-selectivity
experiments address attribution and ion identity, while a closed-channel
baseline alone does not establish protein-free background removal. Complementary
anion-electrode and electrical experiments address different weaknesses; they
are not automatically independent replication of one endpoint.

The authors' approximately10^7 fluoride-ions/s interpretation is preserved with
its source witness in `EXPERIMENTAL_DEFINITIONS_001.json`. The implementation's
charge-equivalent cell is deliberately not relabeled as directly isolated
fluoride flux. The numerical extraction of that separate approximate inferred
ion-turnover assertion is not implemented by this application.

No occupancy-times-current flux bound, per-pore turnover, GHK permeability
calculation, initial flux from instrument dead time, or confidence bound from
reported selectivity limits is introduced. Open-state fractions and amplitude
distributions would need their actual joint ownership and meanings before a
state-averaged throughput calculation. Release, selectivity and other transport
assays remain separate unfinished coverage.

The current exact source selections encountered no unsupported typography or
approximate-number failure for these four electrical operands. This does not
establish general approximate, graph or image reading. The source witnesses and
selected input data are local application records; exact requested child-return
projection, recurrence of the full TASK in selected episodes, observation
accounting, saved repository reconstruction and cold-factory integration have
not been implemented or proved by187. A later binding must not expose private
raw operands merely because a derived component was requested.

## Verification and custody

`APPLICATION_001.log` records a successful single application. The checks compare
the implemented chord and charge conversion against independent Fraction
arithmetic, preserve the unspecified spread, verify the distinct reversal keys,
and require the incompatible chord to be unavailable. These are original-source
application checks, not configured-model scientific execution.

`POST_PACKET_RESET_001.json` records this agent's own complete post-packet reset.
The first overlong combined reset output was truncated and not counted; its
documents were reread successfully. All code and output changes are under the
owned187 directory. The immutable goal and all production source files remain
unchanged. Neither A105 adequacy nor whole-goal completion is claimed.
