# Gene prediction with Pyrodigal

`genes.predict` runs Pyrodigal on the supplied sequence or selected interval.
Select `meta` or `single` and the genetic code explicitly. These are distinct
prediction models; the operation does not substitute one after a failed run.
The existing local execution binding enforces the caller's memory and scratch
limits. A short input can be unsuitable for single-genome model training;
preserve that failure rather than inventing candidates or changing mode.

Each candidate retains its interval, strand, partial-boundary flags,
translation, native model score and native confidence percentage. The
confidence describes the native gene prediction, not the correctness of a
functional annotation. Predictions remain candidates.

The numerical sheet keeps both the worker's zero-based, half-open coordinates
within the submitted region and their coordinates in the original sequence.
It measures candidate nucleotide length, protein length excluding stop
symbols, internal stops and terminal stops. The region's coding coverage is
the union of valid candidate intervals divided by the submitted nucleotide
length, so overlaps and repeated intervals do not multiply coverage. Missing
or invalid candidate fields remain explicit; coverage from only the valid
subset is marked incomplete. An empty successful prediction differs from a
failed prediction.

Preserve the complete native candidate list and populated numerical sheet.
Return the parent's requested candidate measurements and coordinate mappings.
Native score values and derived measurements remain separate; no function
confidence or annotation-credit formula is assigned by this tool.
