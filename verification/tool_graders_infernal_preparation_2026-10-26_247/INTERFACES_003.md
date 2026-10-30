# Additive unit clarification — 247/003

Add numerical unit `Mnt`: one million nucleotides, exactly1e6 nt.
The selected calibration -L/requested_megabases field uses Mnt, not memory MB.
Memory MB remains decimal megabytes (1e6 bytes). These are distinct dimensions.
All other247 interfaces remain unchanged. This does not alter saved native data
or an annotation score. The shared schema UNITS includes Mnt.
