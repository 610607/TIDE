"""Share of live strict entry-0 activations with 34 filled, per checkpoint: v30_fill34.py runs..."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from v25_len import load
for p in sys.argv[1:]:
    W = load(p)
    print(p, " ".join(f"{t//1000}k:{W[t]['alive'][34]/W[t]['alive_n']*100:.0f}" for t in sorted(W)))
