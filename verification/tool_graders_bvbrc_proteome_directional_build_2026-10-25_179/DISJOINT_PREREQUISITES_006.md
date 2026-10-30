# Native disjoint-HSP aggregate prerequisites

The native disjoint-HSP sum uses ordinary conflict > invalid > missing cause
precedence. Preserve known invalid string/geometry prerequisites and their
reasons rather than calling every unavailable sum missing. Inspect actual
per-block counts and coordinate cells, since an HSP's valid-subset union can
remain a value while another block is invalid. Native I/DI, coordinate overlap,
continuity and native-versus-trace agreement remain separate prerequisites.

This does not change005's specific compatible-map identity precondition.
No original measurement, usable neighboring result or history is erased.
