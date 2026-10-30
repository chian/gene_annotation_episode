# Qualification of initial graph analysis001

The original graph and pure-calculator analysis artifacts001 remain retained as conditional numerical drafts. Their raw-scale arithmetic is reproducible, but the first description did not explicitly identify its statistical-scale assumption. The current002 JSON artifacts and CASE_PACKET_001 make that qualification explicit.

The paper's general statistical method says mean averages of independent experiments; Figure6B says SD,n3 and displays CFU/mL on a log10 axis. These facts do not explicitly state the stage at which any log transformation entered the summary calculation. Therefore the following are conditional alternatives, not interchangeable scientific operands:

- Raw-count summary: central display is mean(raw CFU), upper error endpoint is mean+SD in raw CFU. Read both through the axis map, subtract in raw units, then use SD/√3 for the estimated mean SE under the reported unit basis.
- Log-count summary: central display is10^[mean(log10CFU)] and upper error endpoint is10^[mean(log10CFU)+SD(log10CFU)]. The ordinate difference identifies log-SD; neither backtransformed endpoint supplies the raw arithmetic mean/SD without further information.

The selected W upper endpoint/central separation is12pixels, K18.5pixels, R12pixels. Under the second interpretation these are log10-SDs0.140625,0.216796875,0.140625, respectively. Under the first interpretation they correspond to the conditional raw-CFU SD values in GRAPH_COMPONENTS_002. These are two interpretations of one display, not two independent assays or alternative readings to optimize a score.

An implementation should retain source-reported SD/count and observed display quantities even when the statistic's scale is unknown. It should leave the disputed dependent sampling fields unavailable or return explicitly conditional alternatives. No source was reread after the full reset to create this qualification; it is a correction to interpretation of the already read same-paper packet. No historical research or production file was changed.
