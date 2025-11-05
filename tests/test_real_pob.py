#!/usr/bin/env python3
"""
Test script for decoding and evaluating a real PoB code
"""

from src.pob.codec import decode_pob_code, encode_pob_code
from src.pob.caller import PoBCalculator

# Real PoB code from user
REAL_POB_CODE = "eNrtfVuT2ziy8HP0K1hTdb4Xj23cQeaz95TmPo4nHs_FTvKSAklwxJgiFZKaS7b2v58GSEmkRpQ4t63sJrtVjobsbgCNvgMg3v3v7ThxrnVexFn6fgu_QVuOToMsjNOr91uXFwev3a3__cfg3akqR5-inWmcmDf_GHz3zv52En2tk_dbHqCVKr_S5ZcZKvorPJuotBzpLD1Rv2X5YRa-37oY6Z08TvUPQGbL8VUaxuX7rf1cjeN8ywkSVRQ_qrF-v3U-UmF2s+WoItBp