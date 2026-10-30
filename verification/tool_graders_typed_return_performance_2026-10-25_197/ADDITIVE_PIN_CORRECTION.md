# Additive correction from root, 2026-10-25

Root's reviewed correction, verbatim:

> You are right; my instruction that the Comparative pin must remain unchanged was wrong because its declared closure includes communication.py. Do not alter dependency lists or disguise the change. Preserve proteome v1/v2 pins; report the exact NEW Comparative digest, unchanged scientific modules, and old186 pin as historical. Tests/any later fresh Workflow must use the correct new digest explicitly, while old182/186 receipts and sources stay untouched. Record this correction additively in your evidence. Trace/copy only the existing missing Mauve fixture with its provenance/hash into197, then rerun the affected test; do not reinterpret missing fixture as an implementation pass.

The original194 contract and historical186 sources remain unchanged. This correction concerns the new candidate's declared dependency digest; it authorizes no parser, calculator, schema, controller or dependency-list change.
