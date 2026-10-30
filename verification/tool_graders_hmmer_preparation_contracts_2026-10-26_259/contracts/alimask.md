# alimask — proposed exact contract

Four modes: `mask_alignment` (--alirange), `mask_model` (--modelrange),
`model_to_alignment` (--model2ali), `alignment_to_model` (--ali2model). Ranges
are one-based inclusive start/end pairs, comma separated; preserve each request
occurrence even when overlapping. Input is one complete MSA, initially Stockholm;
native reads only the FIRST MSA, so multi-record input must be explicitly rejected
for a whole-input contract or reported as first-record-only, never silently
declared completely transformed. Native input `-` requires --informat. Mask modes
require a positional output MSA; mapping modes take input only and produce text.
`-o` redirects the descriptive header, but mapping printf rows still go to stdout.
Retain both outputs if -o is selected. Output format is selectable; only formats
preserving MM can fulfill a mask-annotation contract. Stockholm is the proven one.

Mask modes add `#=GC MM` characters `m` and `.`. Default replaces the existing mask;
--appendmask takes its union with requested positions. Model ranges map endpoints
to alignment columns and mask ALL columns between mapped endpoints, including
inserts. Model-coordinate construction uses --hand RF or --fast weighted occupancy,
--symfrac, --fragthresh and weighting options; do not equate model and alignment
coordinates. Preserve RF, MM, sequence rows, GS weights and original inputs.

Sheet: input/output MSA occurrence and sequence membership; alen (columns), nseq
(records); complete original/result MM; ordered requested intervals; model-to-
alignment correspondence if actually derivable; returned mapping endpoints and
explicit no-map category. --ali2model prints the first/last MAPPED alignment
coordinates in the requested interval, which may differ from requested endpoints.
Units are alignment columns or model positions explicitly; no significance score.

Functions: `parse_alimask_mapping(text, *, operation, occurrence)`;
`populate_alimask_sheet(*, operation, input_alignment, output_alignment=None,
mapping_stdout=None)`; `calculate_alimask_components(sheet, *, parameters)`.
Separate calculations count the union of requested mask columns, actual masked
columns, newly masked/removed/retained columns, and fraction `masked/alen`; map
length=`end-start+1`. Recompute a --hand map from RF non-gap columns. A --fast map
needs the actual algorithm/weights/fragment treatment; if those are not retained
or implemented faithfully, mapping verification is unknown, not guessed. Validate
sequence and alphabet preservation separately because native fragment marking may
change missing/gap symbols in model-coordinate modes. Keep actual changed strings.

Checks: equal row lengths/MM width; exact union semantics; bounds and start<=end;
same input/output MSA identity/membership; overlapping/duplicate intervals;
unknown output grammar; truncated Stockholm; required RF missing; source has
fixed arrays for 100 ranges with no bound check, so a faithful safe binding must
enforce its native capacity. Source --ali2model scan has no model_len bound in its
initial scan; requests wholly after the last match position require an explicit
unsupported/unsafe-native case rather than fabricated zero/no-map output.

COMMON.md supplies envelope/resource/failure and preparation result handoff.
Consumers may explicitly select the masked MSA for hmmbuild; its MM annotation
is preparation, not an independent function observation. No native call occurs
inside parsing/calculation. Full `alimask.c` and actual -h output were read.

Native examples: `native/alimask_alignment` on 14 columns, ranges 2-4,4-6,
produced MM `.mmmmm........`: 5/14=0.35714285714285715 masked columns, 5 added,
0 removed. `native/alimask_model` with --hand range2-4 masks three columns;
both `native/alimask_model2ali` and `native/alimask_ali2model` report 2..4 ->2..4.
All four modes returned native exit0. These are native examples, not implemented
parser/calculator or episode integration verification.
