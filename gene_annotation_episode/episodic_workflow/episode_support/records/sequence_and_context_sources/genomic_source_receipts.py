"""A107 private source and file custody for its genomic acquisitions.

A public source or native file reference is judged among the sources the reading episode holds."""

# provider: (version, private auxiliaries, origin)
_PROFILES = {
    "public.ncbi.geo": (None, True, "external"),
    "public.ncbi.sra.file": (None, True, "external"),
    "public.encode": (None, True, "external"),
    "ensembl": (None, True, "external"),
    "string": (None, True, "external"),
    "ucsc": (None, True, "external"),
    "public.ncbi.entrez": (None, True, "external"),
    "bvbrc_minhash": (None, True, "external"),
}

def _providers(value):
    if value is None:
        return tuple(_PROFILES)
    if (type(value) is not tuple or any(type(name) is not str or name not in _PROFILES for name in value)
            or len(value) != len(set(value))):
        raise ValueError("molecular_reference_providers_invalid")
    return value


def source_reference_restriction(store, permitted_record_refs, reference, namespace, *, private_only=False, providers=None):
    """Resolve the original A107 source receipt, or defer for unrelated references.

    Source-only auxiliaries are private: always denied.
    Public Source/native File handles must be among the record references the
    acting episode received (``permitted_record_refs``). A
    private-only caller defers public handles so a prior context-aware verdict
    is not overturned. Neither path creates a receipt or traverses Source refs.
    """
    if type(private_only) is not bool:
        raise ValueError("molecular_reference_private_only_invalid")
    selected = _providers(providers)
    if not isinstance(reference, str) or not selected:
        return None
    sources = [row for row in store.list("source")
        if row.get("provider") in selected and row["origin"] == _PROFILES[row["provider"]][2]
        and row.get("version") == _PROFILES[row["provider"]][0]
        and (row["id"] == reference or row.get("artifact_ref") == reference
            or row.get("request_ref") == reference or reference in row.get("auxiliary_artifact_refs", ()))]
    if not sources:
        return None
    if any(source.get("request_ref") == reference for source in sources):
        return False
    private_auxiliary = [source for source in sources if _PROFILES[source["provider"]][1]
        and reference in source.get("auxiliary_artifact_refs", ())]
    if private_auxiliary:
        return False
    if private_only:
        return None
    kind = "source" if any(source["id"] == reference for source in sources) else "artifact"
    minhash_result_source = (kind == "source" and namespace == "execution_result"
        and any(source["id"] == reference and source["provider"] == "bvbrc_minhash"
            for source in sources))
    if (namespace not in (None, kind) and not minhash_result_source
            or not isinstance(permitted_record_refs, tuple)):
        return False
    return reference in permitted_record_refs
