# Explicit selected interpreter startup

Additive mechanical correction,2026-10-27. C3's accepted producer argv is
`[selected_python, -B, -S, -m, gene_annotation_episode.native_chromatin_interaction_driver, exact_plan_path]`.
The earlier439 nominal argv omitted `-S`.

The selected environment now explicitly supplies immutable implementation
sources, reference NumPy/h5py paths and schema-dependency paths in the declared
order. Disabling site startup keeps unrecorded .pth startup from changing that
selection. C3 verifies actual imported versions/locations and freezes the
required dependency files. No package installation, resource choice or new
episode decision is implicit in this argv construction.

Saved calculation retains its separate finite worker and closed saved plan.
It receives only saved sheet/table data and selected calculation parameters,
not producer executable paths or original input access.
