# Selected-read mapping with minimap2

`reads.map` maps one explicitly selected original-read population against the
supplied reference sequences. It requires a configured minimap2 executable in
the current local binding. Select map-ont, map-pb, map-hifi, lr:hq, map-iclr or
sr and any exposed overrides explicitly. These presets do not classify the
input. This binding stages FASTA and uses `--frag=no`; sr is unpaired here,
and read-quality values are not used by the mapping program. Preparation and
execution retain the caller's local memory and scratch limits.

Every reported placement is retained, including secondary and overlapping
placements. The numerical sheet keeps native PAF matching bases and block
length separately from full CIGAR columns, gaps and paired positions. Minimap2
can exclude ambiguous symbols from its native block count. The `nn` ambiguity
quantity remains separate. CIGAR M supplies paired geometry, not equality;
`cs` describes differences in the native normalized alphabet, where N=N does
not establish equality of the original ambiguous symbols.

Coverage names distinguish whole-operand span, paired positions and aligned
positions. Reference skips are separate from deletions. Query coordinates on
the minus strand remain positions in the original query. MAPQ 255 is unknown;
zero remains a reported value. Native MAPQ and alignment scores do not measure
confidence in a proposed gene function, and MAPQ has limitations for multipart
indexes. The P/S/I/i categories do not establish independence or provide a SAM
supplementary flag.

Per-query interval unions avoid counting overlapping placements repeatedly.
Native completion and parsing completeness accompany counts; empty partial
output does not establish an absence. Complete PAF, numerical sheets and exact
row associations remain retained. Return requested measurements and relevant
qualifications, rather than all raw rows or full sheets in a prompt.
