# Explicit host fixture origin for071

This additive pre-coding clarification changes only the constructor signature
shown in NATIVE_REPOSITORY_RELEASE_071:

    LiteratureRatioSourceRepository(store,run_id,*,evidence_origin="reported_source")

The keyword is host-owned and constrained to reported_source/synthetic_fixture,
matching070's exact pure reader input. It is never part of model selection or
the operation schema and supplies no scientific score. Genuine runtime binding
uses reported_source; a trusted constructed test harness uses synthetic_fixture.
Do not silently mark invented fixture bytes as primary evidence because they
were registered through a real Store/ToolRegistry action.

Population and same-key replay bind the actual original origin; changed caller
fixture origin must not relabel historical output. Persist it through070's
saved extraction and preserve the resulting typed origins. Saved read-only
projection uses the saved origin, never reacquisition or a guessed provider
name. Future integration owns descriptor/reconstruction of any explicit host
fixture binding;071 does not edit shared files. All other exact APIs, ownership,
constraints, tests and remaining-work declarations in the release stand.
