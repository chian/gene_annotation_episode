"""Exact descriptive balances for Figure 2D soluble CcCdP products."""
from __future__ import annotations
REPORTED = ('g2_initial', 'g2', 'g3', 'g4', 'g5', 'g6', 'pi', 'g2_sd', 'g3_sd', 'g4_sd', 'g5_sd', 'g6_sd', 'pi_sd')
DERIVED = ('g2_loss', 'soluble_product_molecules', 'acceptor_accounting_ratio', 'acceptor_balance_remainder', 'soluble_added_glucosyl_equivalents', 'soluble_glucosyl_accounting_ratio', 'glucosyl_balance_remainder', 'nominal_donor_to_soluble_yield')
COMPONENTS = REPORTED + DERIVED
