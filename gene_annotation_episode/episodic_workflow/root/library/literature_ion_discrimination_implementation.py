"""The explicit Root release of the original ion implementation operands.

Fresh population attests the installed files. Saved reconstruction validates
the recorded release map without reading source or recalculating science.
"""
import hashlib
from pathlib import Path

from gene_annotation_episode.domain import ContractError

VERSION = 'ion_discrimination_root_implementation_v2'
_FILES = {
    'library/literature_ion_discrimination_numbers.py': '2497b48cea654b97bf280e1236f376400c3b46be51f94cdf1a88b9f6ce5ce3bb',
    'library/literature_ion_discrimination_inputs.py': 'f85a68c7a62abe81efba8957a467acb2641454be5cb1212c568209dc84371e39',
    'library/literature_ion_discrimination_input_contracts.py': 'f9363dbe8365285545e1acd0d566450e3e34baa89c169a4f073b2c027259434c',
    'library/literature_ion_discrimination_calculations.py': 'c10bc4c1ab0606d1ffaee5ca851257273c1311c25c9d602070b434f94a0c0996',
    'library/literature_ion_discrimination_prompt.py': '44797ebe7a49fc732e31deb61ebdebeffd608733e5246b650040b512c12cf99b',
}


def prospective():
    root = Path(__file__).parents[1]
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in _FILES}
    if actual != _FILES:
        raise ContractError('ion_discrimination_prospective_dependency_mismatch')
    return {'version': VERSION, 'files': actual}


def retained(receipt):
    if receipt != {'version': VERSION, 'files': _FILES}:
        raise ContractError('ion_saved_original_receipt_mismatch')
