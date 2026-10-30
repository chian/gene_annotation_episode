# Observed zero coordinate versus valid protein coordinate

Additive root clarification for reader worker172, 2026-10-25.

The accepted correction002 distinguishes primitive lexical validity from
scientific consistency. A displayed coordinate token `0` is an observed integer,
although it is not a usable one-based protein coordinate. Preserve its value0
as a present cell and require `coordinate_out_of_bounds`; require other applicable
span/symbol consistency issues as well. Its query/HSP becomes partial without
erasing independent cells. Closed coordinate storage may therefore admit0;
validated usable protein coordinates still start at1.

Do not classify the lexically valid token0 as `invalid_native_number`. Negative
or malformed tokens outside the contract's declared unsigned integer grammar
remain invalid cells with their exact source text retained. This clarification
does not relax geometry admission or change an actual native observation.
