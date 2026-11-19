# Translate a selected nucleotide interval

`sequence.translate` derives one protein product from a supplied sequence under
an explicitly chosen genetic code, strand and frame. This supporting operation
does not identify biological function, establish a gene model or assign a
translation-table probability. `translation.codes` lists the installed code IDs,
names, starts and stops so the selecting episode can inspect the available
models. Reference sequences remain reference evidence when transformed.

The current callable is local `ToolRegistry` operation `sequence.translate`.
It uses installed Biopython with the existing caller limits of 20 GiB RAM and
4 GiB scratch and no wall-time limit. No remote API or HPC translation binding
is claimed by this entry.

Supply `subject_ref` for the actual input, reference, feature or sequence product
and integer `code`. Optional parameters are `strand` (`+` by default, or `-`),
`frame` (0, 1 or 2; default 0), `start` (default 0), `end` (default the supplied
sequence length) and boolean `cds` (default false). Coordinates are zero-based
and half-open in that supplied sequence. The interval must be nonempty and
inside it. The input must contain nucleotide symbols A,C,G,T,U,R,Y,S,W,K,M,B,D,
H,V,N, allowing either case. At least one complete codon must remain.

The operation selects the interval, uppercases it and treats U as T, takes its
reverse complement when requested, then skips `frame` bases from that oriented
interval's beginning. It translates complete triplets and records 0–2 unused
trailing bases. A negative strand therefore skips bases at the original
interval's high-coordinate end. With ordinary translation, internal and
terminal stop symbols are retained. Ambiguous codons can yield a specific
residue, B, Z, J, X or a stop according to their possible codons under the
selected table.

`cds=true` requires frame zero and a complete codon interval, a valid start and a
terminal stop under that code. The first accepted start is returned as M,
including alternative starts, and the final stop codon is omitted from the
protein. Extra in-frame stops cause native failure. For tables with dual-coding
stops, such as 27, 28 and 31, internal codons use their amino-acid mapping while
an accepted terminal CDS stop is omitted. These are declared native semantics,
not evidence that the sequence is a complete biological CDS. For example,
code 11 with `cds=true` translates `GTGAAATAA` to `MK`: three consumed codons,
two returned amino-acid symbols, zero returned stop symbols and one omitted
terminal stop codon.

The result publishes a feature, a reusable protein product and a coordinate
observation with the original source retained. Use returned record references
to select those artifacts. The retained numerical grading artifact separately
contains the exact input/result, effective request, frozen genetic-code table,
per-codon checks and numerical counts. It distinguishes returned `*` symbols
from a terminal stop omitted by CDS translation. Frame-skipped bases, trailing
bases and the omitted stop keep their own original locations. A codon spanning
two source segments stays split; no contiguous original span is invented.

`build_translation_sheet`, `calculate_translation_scores` and `grade_translation`
are host-side deterministic functions, not additional episode actions. The
calculator consumes a saved sheet and makes no new translation, data request
or installed-table lookup. Missing reference data leaves table-dependent checks
unknown. Missing ancestry leaves original-source correspondence unknown.
Inconsistent settings or output lengths retain actual product counts while
withholding unverified correspondence; a short output is not assumed to be a
mapped prefix. Numerical components describe this transformation and are not an
annotation-confidence score.
