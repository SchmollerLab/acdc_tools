from typing import Union

from math import log10, floor

def round_to_significant(n, n_significant=1):
    return round(n, n_significant-int(floor(log10(abs(n))))-1)