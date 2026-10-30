# Supplied invocation consistency

Additive root clarification for G1, 2026-10-27. Native execution authority stays
with the host. Pure parsing checks whether supplied metadata contradicts the
scientific meaning of a complete, all-positive, unstranded outer-span table.

The supplied-output route may have no realized argv and explicitly declared
complete output. It need not have been executed by this workflow. Do not require
execution receipts, a particular path, or canonical-file artifacts when they are
unknown and therefore null under the accepted contract.

When a nonempty realized argv is supplied, it cannot silently contradict that
table meaning. Recognize the declared bedtools intersect invocation with one
`-a` operand, one `-b` operand and `-wo`, with optional `-sorted`. Option order
does not affect this check. The `intersectBed` executable spelling is an
equivalent invocation prefix. Sorting is an execution detail; an otherwise
compatible supplied unsorted invocation does not change the numerical mode.
This is a small check for the verified invocation family, not a general CLI
interpreter or an authority decision.

Additional options that this contract does not interpret cannot establish its
complete scientific population. In particular, strand/block/fraction restrictions
must not claim the complete unfiltered population merely because returned rows
have valid positive widths. Preserve valid rows, mark the result partial and
attach `unsupported_input_format` at `/receipt/realized_argv`, with stage parse,
the actual argv as observed_value and the accepted mode as expected_value.
This does not require discarding valid rows or preventing lower-bound quantities
when those rows have verified original endpoint/width correspondence. Missing
metadata and explicitly incompatible metadata remain different cases.

The live host separately enforces the exact original selected invocation,
resource, attempt and files. G2's initial bound argv remains precisely the plain
`intersect -a A -b B -wo -sorted` verified in packet421.
