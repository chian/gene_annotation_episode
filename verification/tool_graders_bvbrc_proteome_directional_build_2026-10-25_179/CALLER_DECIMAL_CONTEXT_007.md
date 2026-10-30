# Deterministic ratio rendering

Root's read-only probe of C before final verification found that its inherited
Decimal context could raise Inexact for a valid 1/3 ratio when the caller enabled
that trap. The requested rounding and exact saved rational were unchanged, but
calculation depended on unrelated caller settings.

No stable combined run had started. C now uses integer long division and exact
HALF_EVEN remainder comparison for ratio text, as the A validator and B geometry
already do. It retains numerator and denominator. New full-calculation tests use
altered caller precision, exponent bounds, rounding and traps, and exact 1/8 and
3/8 halfway examples. This changes no formula or accepted interface.
