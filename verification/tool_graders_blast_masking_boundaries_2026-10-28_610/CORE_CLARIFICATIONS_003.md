# Additive core clarification 003 — genome-size integer width

This narrowly corrects the integer-width sentence in CORE_CLARIFICATIONS_002.md.
The proposed positive `windowmasker / create_counts` `genome_size` parameter is
an integer in **[1, 2**63 - 1] or null**. The NCBI configuration declares it using
`CArgDescriptions::eInteger` and reads it with `AsInt8` (the retained pinned
`win_mask_config.cpp`, declaration near lines 94–96 and initialization near 374).
Do not limit it to a signed 32-bit value because this first native test is tiny.

The signed 32-bit limit applies only to options whose source actually reads the
value with `AsInteger` or otherwise establishes that bound; `eInteger` alone
does not establish a 32-bit limit. The explicit narrower `unit` limit [1,16] remains.
No other shape, option, native mode, resource binding or numerical meaning changes.
