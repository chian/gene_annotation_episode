# Additive calibration population component — 247/005

B adds component total_calibration_chunk_count (Value, unit count), equal to
floor(requested_megabases*100+0.5), from selected -L in Mnt and native10,000-nt
chunk size. This is the total generated chunk population before partitioning.
partition_chunk_count remains the count of chunks assigned to the selected
partition. actual_calibration_nt labels the relevant actual selected population,
not automatically the whole requested total. The exact input parameters and
denominators remain separately inspectable. No duration or confidence transfer
is inferred from these native workload sizes.
