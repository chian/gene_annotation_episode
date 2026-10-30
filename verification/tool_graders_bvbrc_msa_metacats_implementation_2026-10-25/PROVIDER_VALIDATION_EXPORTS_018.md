# Detached provider parameter and saved-component validation

Accepted additive interface clarification, 2026-10-25. Provider workloads C/D
must expose validators for the exact parameters and complete saved Components
already specified in CALCULATIONS_001.md and its accepted provider extensions.
The previous sheet and calculator signatures remain unchanged.

```python
# bvbrc_msa_provider_contracts.py
validate_msa_parameters(parameters: dict) -> dict
validate_msa_components(components: dict, *, sheet: dict) -> dict
# bvbrc_metacats_provider_contracts.py
validate_metacats_parameters(parameters: dict) -> dict
validate_metacats_components(components: dict, *, sheet: dict) -> dict
```

Parameter validation checks the exact closed provider-specific tagged union,
unique request IDs and declared dependency graph (including wrong-kind or cyclic
references) without executing calculations. Provider-local native PValuePlan
uses the accepted additive PROVIDER_PARAMETER_CLARIFICATIONS_002.md. Cross-analysis
family planning remains solely in the bundle layer.

Saved-component validation returns detached values and checks the exact sheet
analysis, original requests, requested populations and result kinds/identities,
plus existing complete native/shared mathematical result validators. It retains
independent successes and typed missing/failed dependencies. It never calls a
grader/calculator, parser, acquisition, native program or LLM. A passing validator
is not proof of external source custody or that a new statistical result has
been independently recomputed.

Consumers are each calculate_* entry point and the later shared bundle
projection/return functions, which validate saved sheets/components before
copying originally requested facts. Parameter schema generation and original
SlotRef compilation remain bundle responsibilities; no expression interpreter
or additional workflow layer is introduced. These exports use the already owned
provider contract files and require no additional shared-file owner.
