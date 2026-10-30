# Root fixture boundary correction002

Original probe001 remains unchanged. Its synthetic graph interval was constructed
with Python float addition/subtraction, so the actual saved endpoints differ by
rounding from the nominal printed3.95/4.15 description. Its point/cancellation,
local point/conflict and covariance findings remain valid. Probe002 constructs
the synthetic decimal endpoints with exact Fraction arithmetic before finite
export and asserts the actual dictionary[3.95,4.15]. This is fixture precision
repair, not a production/calculator/paper-data change or an actual graph read.
