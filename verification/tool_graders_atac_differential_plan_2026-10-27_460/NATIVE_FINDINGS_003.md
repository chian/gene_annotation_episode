# Actual MACS2 preparation and native measurements

These are retained implementation observations for fixed row B-L125, not a
completed scoring sheet, production tool binding, biological finding or goal
amendment. Only the original user-supplied attachment defines the goal.

## Completed native attempts

Prerequisite001: terminal/quiescent exit0; observed service wall73.460512788s,
observed scratch629161984 bytes. Sources and interpreter/launcher pins unchanged.
The isolated environment actually reports MACS2 2.2.9.1 under Python3.11.13.
Its source distribution matches the published SHA256
8d56bc37fb823fc6387d78138ce968405c54a0a8cd9776682705fd0983252d16.

Native001: terminal/quiescent exit0; observed service wall3.88220334s,
observed scratch23937024 bytes. Frozen probe/application sources and all selected
installed package/interpreter files remained unchanged. It executed four actual
MACS2 CLI commands and one separately declared native score-array export.
Both runs used20GiB RAM, zero swap,4GiB monitored scratch and no wall limit.
Scratch observation is not a hard filesystem quota. Full commands, input bytes,
native files and receipts remain under their original attempt directories.

## Coordinate defect demonstrated with explicit tracks

Native001/explicit_tracks contains five100bp input intervals on chrToy[0,500).
The supplied depth values are1 and2 million synthetic reads, giving native
condition factors1 and0.5. These are explicit fixture values, not measurements
inferred from bedGraph. The unchanged native program returns:

| Meaning in the supplied tracks | Input interval (0-based, half-open) | Actual native BED interval | Native BED score |
|---|---|---|---:|
| Condition1 signal20 versus condition2 signal2 |100–200|0–100|17.7408|
| Condition2 signal40 versus condition1 signal2 |300–400|200–300|12.1487|
| Similar scaled signals,10 versus20 |200–300|100–200|5.42506e-07|

The full native diagnostic arrays preserve positions[0,100,200,300,400], rather
than the actual segment ends[100,200,300,400,500]. The array's second signed
between-condition likelihood value is17.7408447265625. Its fourth is
-12.148710250854492. Native BED files round these values and invert the sign for
the condition2 category. The three original BED files, full four input tracks,
and four native NumPy arrays are retained. This is a demonstrated position
displacement in the selected native version, not an assumed coordinate convention.

The corresponding native source is MACS2/IO/ScoreTrack.pyx:build_chromosome.
It passes pre_p to add as endpos before advancing pre_p to the next boundary.
The consuming peak caller interprets stored positions as interval ends. The
input/output case above establishes the practical consequence independently of
that reading. Raw native files must remain unchanged; their reported coordinates
must not be silently relabeled as validated accessibility intervals.

Other exact observed version semantics: three differential filenames selected
with -o are respected. The --o-prefix source implementation adds a cutoff suffix
that the command help omits. Native likelihoods add pseudocount0.01 before
per-condition depth scaling and store individual float32 components. Native
classification uses three comparisons and a length-weighted region score; it
does not estimate variation among biological replicates.

## Actual BAM run and depth measurements

The two coordinate-sorted BAMs use a declared12,000bp synthetic chromosome and
30bp single-end records. Condition1 has105 supplied records, including5 duplicate
coordinates; condition2 has200. Actual callpeak XLS outputs report:

| Condition | Native total tags | Native tags after keep-dup1 | Depth passed to bdgdiff (millions) | Relative depth factor |
|---|---:|---:|---:|---:|
|1|105|100|0.0001|1|
|2|200|200|0.0002|0.5|

Depth operands were extracted from each actual XLS after-filtering count, not
substituted from the BAM generator's requested counts. Native callpeak used -B,
BAM, nomodel, shift-100, extsize200, q0.05 and explicit output/temp directories.
No matched background BAM was supplied; the returned control_lambda tracks are
native background models, not observations from a control sample. Full tracks,
peak tables and differential files remain available with exact sample roles.

## Required next work

Define the scoring sheet and pure input/calculation ports against these actual
outputs before assigning parallel implementation. Retain all track values,
actual sample/reference/condition mappings, depth denominators and numerical
components. Expose native BED records as reported with the demonstrated defect;
derive valid region coordinates from the actual common track partition in a
separately named, verified calculation. Do not patch historical native bytes,
select another executable silently, or propagate the bad coordinates simply to
match native output. Exact formula/precision and native-versus-corrected return
fields still need their implementation contract and numerical checks.

Missing, excluded, failed, incomplete and zero regions need separate outcomes.
Recalculation must use the saved complete tracks and explicit parameters, with
no reacquisition or repeated callpeak. Tool information, production launch/result
binding and requested receiving-episode display remain unfinished. No row was
added to the implemented112/308 count by either native attempt.
