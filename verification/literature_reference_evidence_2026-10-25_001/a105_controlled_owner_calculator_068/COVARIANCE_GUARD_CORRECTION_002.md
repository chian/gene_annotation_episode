# Additive covariance-binding correction002

Pin001 and its actual68-pass execution remain unchanged. Subsequent edge review
found repeated RoleCovariance bindings could use incompatible physical unit
dimensions when both canceled mean units were unknown. The contrast was already
blocked later, but malformed supplied covariance lacked its direct binding error.
The new focused counterexample actually failed before repair; stdout/stderr and
exit status are retained. New code rejects covariance_unit_mismatch for those
repeated bindings. A positive case confirms genuinely missing canceled numbers/
mean units do NOT block valid same-dimension RoleCovariance or A-C/V. This is a
provided-covariance identity guard, not a new gate on missing unused quantities.

Checkout test run after repair:70 passed in0.44s. Final coherent execution is
pin002, with the original helper and exact004 declarations unchanged.
