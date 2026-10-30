# Additive absent-unit and physical-role clarification

No-data sources return endpoint_unit=exposure_unit=unreported, replacing the
interface001 placeholder fraction codes. Qualitative PCR evidence must not
acquire a fabricated fraction unit. Calculator accepts unreported dimensional
codes only when all corresponding native values are absent. Actual retained
dataset units still require one of the finite measured-unit codes in001.

Derived endpoint contrasts require known distinct physical keys for their
participating arm measurements. Missing key gives
role_measurement_identity_unreported; using a single observation as distinct
reference/perturbed/restored arms gives role_measurement_not_distinct. Native
points survive those unavailable contrasts. This is observation identity, not
an independence assumption or extra runtime gate. Shared exposure measurements
remain allowed when actual units/values agree; they are not independent data.

Both reader and calculator reject qualitative_only with numeric W/K/R. Unknown
or conflicting calibration status can retain native supplied points but does
not establish a quantitative source effect. Bounds/confidence remain unknown.
