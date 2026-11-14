"""Pure data contracts for Infernal model preparation and inspection.

These helpers define numerical cells and artifact provenance. They do not
execute programs, interpret scientific confidence, or decide episode actions.
Program-specific parsing and calculation live in the three owning modules.
"""
from __future__ import annotations
PROGRAM_MODES = {'cmbuild': frozenset({'build', 'refine'}), 'cmcalibrate': frozenset({'calibrate', 'forecast', 'memory_estimate', 'split_commands', 'partition_scores', 'merge_scores'}), 'cmconvert': frozenset({'ascii', 'binary', 'legacy_ascii', 'maximum_likelihood_hmm', 'filter_hmm'}), 'cmemit': frozenset({'sample_unaligned', 'sample_aligned', 'consensus'}), 'cmfetch': frozenset({'single_key', 'key_file', 'index'}), 'cmpress': frozenset({'press'}), 'cmstat': frozenset({'summary', 'scores_at_evalue', 'scores_at_pvalue', 'evalues_at_score', 'evalues_at_ga', 'evalues_at_nc', 'evalues_at_tc'})}
