# Additive native ordinate edge and difference-unit clarification

These corrections apply to FIGURE_MEASUREMENT_INTERFACES_013.md before final
verification. No prior scientific receipt or source image is replaced.

1. A unique retained qualifying run that begins at roi.top does not establish
   its upper mean edge: the ROI may start inside a taller bar. Preserve the
   retained run and selection, but set pixel_edge=null and cell unavailable
   with reason truncated_mean_edge. Do not use the ROI boundary as a measured
   mean edge. The full source/ROI above the run must expose a nonqualifying row.
2. Subtracting graph-derived relative_turnover_percent ordinates returns a
   derived cell with unit relative_turnover_percentage_points. It is a signed
   difference in percentages, not a relative percent change. Other difference
   units remain arbitrary_signal or nanomolar as appropriate. Calibration and
   graph-derived input units remain the original three codes. Derived output
   cannot masquerade as a graph-derived input.
3. Validate image container integrity using Pillow verify before reopening for
   decode/counting, including truncated PNG footer or corrupt chunk detection.
   Coordinate, ROI and calibration checks still precede pixel counting.

The two-pixel edge tolerance is a declared sensitivity convention conditional
on the chosen axes/RGB threshold/ROI. It is neither an empirical error model
nor a bound on every possible digitization or source-publication error.
