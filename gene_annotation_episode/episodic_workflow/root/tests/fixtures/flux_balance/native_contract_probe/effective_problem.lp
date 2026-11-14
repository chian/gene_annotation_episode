\* Problem: Unknown *\

Minimize
 obj: + 0.25 IN - 0.25 IN_reverse_c86ee - OUT + OUT_reverse_ef373

Subject To
 A_c: + AB_reverse_b86fc - AB - IN_reverse_c86ee + IN = 1
 B_c: + OUT_reverse_ef373 - OUT - AB_reverse_b86fc + AB = 0
 net_cap: - OUT_reverse_ef373 - AB_reverse_b86fc + OUT + AB <= 12
 split_cap: + IN_reverse_c86ee + IN <= 9
 aux_link: + aux - OUT + OUT_reverse_ef373 = 0

Bounds
 0 <= IN <= 8
 0 <= IN_reverse_c86ee <= 10
 AB_reverse_b86fc = 0
 OUT_reverse_ef373 = 0

End
