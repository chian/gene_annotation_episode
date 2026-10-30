# Additive manifest self-entry correction

The root235 and root236 `ROOT_MANIFEST_002.json` files inadvertently included a hash of their own newly opened empty file. Those self entries are invalid and must not be used as verification. The underlying progress, source, test and public-status records were not changed. Both original manifests remain preserved; each directory's manifest003 hashes the completed records before opening its own output and excludes itself. Use manifest003 for current artifact verification.
