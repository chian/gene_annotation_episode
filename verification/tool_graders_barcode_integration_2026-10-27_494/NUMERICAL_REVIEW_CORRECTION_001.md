# Missing-population units correction

Root review of the complete calculator found that its failed-sheet branch
inferred units from field-name substrings. It incorrectly returned reads for
pair_count, cluster_count and barcode-type counts. An unavailable measurement
must retain the same units as that field when available. Native population
counts also keep their declared observed source category rather than becoming
derived simply because no valid population was retained.

Root now owns this narrow correction in barcode_calculators.py and a focused
regression in test_barcode_calculators.py after491 closed its work. Successful
population calculations and all public field/function contracts remain intact.
491/check004's60-pass receipt remains historical;492's exact frozen native
software is unchanged.494/check001 was frozen before this correction. New
bounded numerical verification must establish the corrected branch.
