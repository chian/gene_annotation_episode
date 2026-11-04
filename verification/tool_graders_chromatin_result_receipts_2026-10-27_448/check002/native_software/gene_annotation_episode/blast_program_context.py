"""BLAST executable identity and alignment geometry are separate facts.

This is not an execution or API allowlist. The source-qualified aliases are
documented in verification/tool_graders_blast_collection_2026-10-26_293/.
NCBI's BlastNumber2Program, GetBlastProgramName and TBLASTN/PSI option
constructors establish the reported tokens; no version-number allowlist is used.
"""
from __future__ import annotations


_GEOMETRY = {
    "blastn": "blastn", "blastp": "blastp", "blastx": "blastx",
    "tblastn": "tblastn", "tblastx": "tblastx", "psiblast": "blastp",
    "deltablast": "blastp", "rpsblast": "blastp", "rpstblastn": "blastx",
    "blastn_vdb": "blastn", "tblastn_vdb": "tblastn",
}
_QUERIES = {name: {"sequence"} for name in _GEOMETRY}
_QUERIES.update(psiblast={"sequence", "pssm", "msa"},
                tblastn={"sequence", "pssm"}, tblastn_vdb={"sequence", "pssm"})


def resolve_blast_program_context(*, execution_program, reported_program,
                                  scientific_mode, query_kind, reference_kind,
                                  native_version) -> dict:
    """Validate an explicit scientific mode and return its geometry separately.

    Native names/version text are copied verbatim, including case. A missing
    native token remains missing. Additional PSI/DELTA pairwise modes are not
    among this contract's sixteen scientific modes and remain unsupported here.
    A resolved identity alone does not establish a supported report layout,
    native execution, profile semantics, or a deployed resource.
    """
    if not isinstance(execution_program, str) or execution_program not in _GEOMETRY:
        raise ValueError("blast_execution_program_unsupported")
    if scientific_mode not in ("pairwise", "database"):
        raise ValueError("blast_scientific_mode_invalid")
    if scientific_mode == "pairwise" and execution_program not in (
            "blastn", "blastp", "blastx", "tblastn", "tblastx"):
        raise ValueError("blast_program_mode_unsupported")
    if not isinstance(query_kind, str) or query_kind not in _QUERIES[execution_program]:
        raise ValueError("blast_program_query_kind_conflict")
    references = ({"profile"} if execution_program in ("rpsblast", "rpstblastn")
                  else {"vdb_read", "vdb_reference", "vdb_mixed"}
                  if execution_program.endswith("_vdb") else {"sequence"})
    if not isinstance(reference_kind, str) or reference_kind not in references:
        raise ValueError("blast_program_reference_kind_conflict")
    if native_version is not None and (not isinstance(native_version, str) or not native_version.strip()):
        raise ValueError("blast_native_version_invalid")
    expected = execution_program.removesuffix("_vdb")
    if expected == "tblastn" and query_kind == "pssm":
        aliases = {"psitblastn"}
    elif expected == "psiblast" and query_kind == "sequence":
        aliases = {"psiblast", "phiblastp"}
    else:
        aliases = {expected}
    if reported_program is not None:
        if not isinstance(reported_program, str) or not reported_program.strip():
            raise ValueError("blast_reported_program_invalid")
        if reported_program.lower() not in aliases:
            raise ValueError("blast_reported_program_conflict")
    if native_version is not None:
        version_program = native_version.split(maxsplit=1)[0].lower()
        known = set(_GEOMETRY) | {"psitblastn", "phiblastp"}
        if version_program in known and (version_program not in aliases or
                reported_program is not None and version_program != reported_program.lower()):
            raise ValueError("blast_native_version_program_conflict")
    return {"execution_program": execution_program, "reported_program": reported_program,
            "scientific_mode": scientific_mode, "query_kind": query_kind,
            "reference_kind": reference_kind, "native_version": native_version,
            "geometry_program": _GEOMETRY[execution_program]}


__all__ = ["resolve_blast_program_context"]
