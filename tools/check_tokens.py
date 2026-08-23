"""Quick tokenizer check on the descriptions the deck quotes."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniforge import trade_tokens as TT  # noqa: E402

CASES = [
    'Milw 5"x.045"x7/8" Metal Cut Off Disc',
    '3M 775L Stikit Film [P150] - Cubitron II 50 Disc/Box',
    'AZEK Harvest Deck Bd Weathered Teak Grooved 20ft',
    '1/2 CPLG BRS 150# NIBCO',
    'Rheem Elec WH 50gal 240V 5500W',
    'Pleated Air Filter 20x25x1 MERV13 12pk',
    'PDSH4816AF Dishwasher SS - Display Only',
]

for text in CASES:
    print()
    print(text)
    print("  skeleton:", TT.skeleton(text))
    for t in TT.tokenize(text):
        flag = " <- measure" if t.is_measure else ""
        print(f"    {t.kind:9} {t.text!r:14} [{t.start}:{t.end}]{flag}")
