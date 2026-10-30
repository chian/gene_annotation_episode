# Isolated HMMER API resource engineering evidence

See docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_001.md for exact results, retained failures, identity algorithms and limits. Source/test files remain separate from the live scientific implementation. The final source identity is SOURCE_IDENTITIES.json; earlier input generations are historical, never silently updated. MANIFEST.json hashes the actual published bytes, including this report and all retained generations.

Reproduction uses the project's installed dependencies and explicit local fixture service. Native fixture binary and scientific publication/target fixtures are retained. The tests do not invoke public HMMER or configured model inference. Test worker deadlines are fixture failure bounds, not runtime work budgets. Dynamic worker state/tokens and private provider reasoning are excluded.

LOG_REDACTIONS.json records any named execution-token redactions; original hashes remain in historical evidence. Historical component manifests refer to their own original inputs, while this outer manifest is authoritative for published bytes.
