"""Rebuild a stand-in for Sample-1000_Items.xlsx.

The real 1,000-row supplied file is not in this repository. This generator produces a
catalogue with the same pathologies described in the pack, so the pipeline can be run
and measured end to end without it:

  * 6 columns, no more
  * short, abbreviated, inconsistent descriptions (mean ~38 characters)
  * ~86.5% of brand cells are placeholders, not data
  * Part_Manuf names whoever invoiced - distributors, buying co-ops and vendor
    account artefacts sit where a manufacturer should be
  * sibling rows differ in exactly one token, which is what makes attribute
    discovery possible
  * one row pairs a manufacturer with a brand it does not own

Every product line named in the prototype deck is present verbatim so the worked
examples still resolve: the Milwaukee cut-off disc, the six 3M Stikit rows, the AZEK
collection/colour matrix and the Frigidaire/Rheem contradiction.

If the real file is dropped into data/in/Sample-1000_Items.xlsx it is used instead and
this file is ignored.

    python tools/make_dataset.py
"""
from __future__ import annotations

import itertools
import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniforge import config as C  # noqa: E402
from uniforge.seed import manufacturers as seed_mfr  # noqa: E402

TARGET_ROWS = 1000
SEED = 20260823

UNBRANDED = "-- Unbranded --"
NO_UNILOG = "-- No Unilog Brand --"
NO_DIB = "-- No DIB Brand --"

# probability a brand column carries real data rather than a placeholder
P_E1_REAL = 0.250
P_UNILOG_REAL = 0.090
P_DIB_REAL = 0.065


# --------------------------------------------------------------------------------------
# Product lines. Each is a template with named axes; siblings are drawn from the axis
# cross-product, which is precisely the signal the family/axis stage looks for.
# --------------------------------------------------------------------------------------
# (line_id, mfr, pn_pattern, desc_template, axes, weight)
LINES: list[tuple[str, str, str, str, dict[str, list[str]], int]] = [

    # ============ abrasives / power tool accessories =================================
    ("milw-cutoff", "Milwaukee Tool", "49-94-{n4}",
     'Milw {dia}"x{thk}"x{arb}" Metal Cut Off Disc',
     {"dia": ['4-1/2', '5', '6', '9'], "thk": ['.045', '.062'], "arb": ['7/8', '5/8']}, 9),

    # Same product line, but these rows state the pack quantity while the rows above
    # stay silent about it. That asymmetry is what gives sibling propagation something
    # real to do - and what gives the manufacturer document something to overrule.
    ("milw-cutoff-pk", "Milwaukee Tool", "49-94-{n4}",
     'Milw {dia}"x{thk}"x{arb}" Cut Off Disc 10/pk',
     {"dia": ['4-1/2', '5', '6'], "thk": ['.045'], "arb": ['7/8']}, 4),

    ("3m-stikit", "3M Company", "3MABR-71000{n5}",
     '3M 775L Stikit Film [{grit}] - Cubitron II 50 Disc/Box',
     {"grit": ['P80 ', 'P120', 'P150', 'P180', 'P220', 'P320']}, 6),

    ("3m-cubitron-fibre", "3M Company", "3MABR-71001{n5}",
     '3M Cubitron II Fibre Disc {dia}in {grit} 25/bx',
     {"dia": ['4-1/2', '5', '7'], "grit": ['36', '60', '80', '120']}, 8),

    ("norton-flap", "Saint-Gobain Abrasives, Inc.", "NOR-{n6}",
     'Norton Blaze Flap Disc {dia} x {arb} T29 {grit}g',
     {"dia": ['4-1/2', '5'], "arb": ['7/8'], "grit": ['40', '60', '80', '120']}, 7),

    ("weiler-wire", "Weiler Abrasives Group", "WLR-{n5}",
     'Weiler Knot Wire Cup Brush {dia}in {arb} CS',
     {"dia": ['2-3/4', '3', '4'], "arb": ['5/8-11', 'M10x1.25']}, 5),

    ("diablo-blade", "Freud America, Inc.", "D{n4}X",
     'Diablo {dia}" {teeth}T Circ Saw Blade Wood',
     {"dia": ['6-1/2', '7-1/4', '10', '12'], "teeth": ['24', '40', '60', '80']}, 8),

    ("lenox-recip", "Lenox Tools", "LNX-{n6}",
     'LENOX Lazer Recip Blade {len}in {tpi}TPI 5pk',
     {"len": ['6', '8', '9', '12'], "tpi": ['10', '14', '18', '24']}, 8),

    ("milw-holesaw", "Milwaukee Tool", "49-56-{n4}",
     'Milw Hole Dozer Hole Saw {dia}in Bi-Metal',
     {"dia": ['3/4', '1', '1-1/4', '1-1/2', '2', '2-1/2', '3', '4']}, 8),

    ("dewalt-bit", "Stanley Black & Decker, Inc.", "DW{n5}",
     'DeWalt Cobalt Drill Bit {dia}in Jobber 135deg',
     {"dia": ['1/8', '5/32', '3/16', '1/4', '5/16', '3/8', '1/2']}, 7),

    # ============ pipe fittings & valves =============================================
    ("nibco-brs-cplg", "NIBCO INC.", "N{n6}",
     '{sz} CPLG BRS {psi}# NIBCO',
     {"sz": ['1/4', '3/8', '1/2', '3/4', '1', '1-1/4', '1-1/2', '2'],
      "psi": ['150', '300']}, 10),

    ("charlotte-pvc-elb", "Charlotte Pipe and Foundry Company", "PVC0{n5}",
     'Charlotte PVC {ang} ELB {sz} Sch{sch} S x S',
     {"ang": ['90', '45'], "sz": ['1/2', '3/4', '1', '1-1/2', '2', '3', '4'],
      "sch": ['40', '80']}, 12),

    ("mueller-cu-tee", "Mueller Industries, Inc.", "MU-{n6}",
     'Mueller Wrot Cu Tee {sz} CxCxC',
     {"sz": ['1/2', '3/4', '1', '1-1/4', '1-1/2', '2']}, 7),

    ("anvil-nipple", "Anvil International, LLC", "AV{n6}",
     'Anvil Blk Nipple {sz} x {len}in Sch40',
     {"sz": ['1/8', '1/4', '1/2', '3/4', '1', '1-1/4', '2'],
      "len": ['1-1/2', '2', '3', '4', '6', '12']}, 11),

    ("apollo-bv", "Aalberts integrated piping systems Americas", "70LF-{n4}",
     'Apollo BV {sz} FP {psi}# BRS Lever',
     {"sz": ['1/4', '1/2', '3/4', '1', '1-1/4', '1-1/2', '2'], "psi": ['600']}, 8),

    ("nibco-gate", "NIBCO INC.", "NG{n6}",
     'NIBCO GV {sz} BRS {psi}# SWT',
     {"sz": ['1/2', '3/4', '1', '1-1/4'], "psi": ['125', '200']}, 6),

    ("watts-cv", "Watts Water Technologies, Inc.", "WTS{n6}",
     'Watts Swing CV {sz} BRS Sldr',
     {"sz": ['1/2', '3/4', '1', '1-1/2', '2']}, 5),

    ("viega-press", "Viega LLC", "VG{n6}",
     'Viega ProPress {sz} Cplg w/o Stop Cu',
     {"sz": ['1/2', '3/4', '1', '1-1/4', '1-1/2', '2']}, 6),

    ("uponor-pex-adapt", "Uponor, Inc.", "UP{n6}",
     'Uponor ProPEX Adptr {sz} x {out} MIP Brass',
     {"sz": ['1/2', '3/4', '1'], "out": ['1/2', '3/4', '1']}, 7),

    ("victaulic-cplg", "Victaulic Company", "VIC-{n5}",
     'Victaulic Style 77 Cplg {sz} Ductile Galv',
     {"sz": ['2', '2-1/2', '3', '4', '6', '8']}, 6),

    # ============ faucets =============================================================
    ("moen-kitchen", "Moen Incorporated", "{n4}{fin}",
     'Moen {series} Kit Fct Pulldown 1H {fin}',
     {"series": ['Arbor', 'Adler', 'Sleek'], "fin": ['SRS', 'CH', 'MB', 'BN']}, 9),

    ("delta-bath", "Masco Corporation of Indiana", "DL{n4}-{fin}",
     'Delta {series} Lav Fct 2H {ctr}in {fin}',
     {"series": ['Windemere', 'Lahara', 'Trinsic'], "ctr": ['4', '8'],
      "fin": ['CZ', 'SS', 'RB', 'PC']}, 10),

    ("kohler-kitchen", "Kohler Co.", "K-{n5}-{fin}",
     'KOHLER {series} Kit Fct 1H Pullout {fin}',
     {"series": ['Simplice', 'Bellera', 'Crue'], "fin": ['VS', 'CP', 'BL']}, 7),

    ("chicago-comm", "Chicago Faucet Company", "CF{n4}-{n2}",
     'Chicago Fct Svc Sink Fct {reach}in Spout Rough Chr',
     {"reach": ['6', '8', '12']}, 4),

    ("ts-prerinse", "T&S Brass and Bronze Works, Inc.", "B-{n4}",
     'T&S Pre-Rinse Unit {hose}in Hose Wall Mt',
     {"hose": ['44', '68']}, 3),

    # ============ appliances ===========================================================
    ("frigidaire-dw", "Rheem Manufacturing", "PDSH{n4}AF",
     'PDSH{n4}AF Dishwasher SS - Display Only',
     {}, 4),

    ("frigidaire-range", "Electrolux Home Products, Inc.", "FCRE{n4}AS",
     'Frigidaire {wid}in Elec Range {fin} {burn}Brnr',
     {"wid": ['24', '30'], "fin": ['SS', 'WH', 'BK'], "burn": ['4', '5']}, 7),

    ("whirlpool-washer", "Whirlpool Corporation", "WFW{n4}HW",
     'Whirlpool {cap}cf FL Washer {fin}',
     {"cap": ['4.5', '5.0'], "fin": ['WH', 'CHR']}, 4),

    ("ge-fridge", "GE Appliances", "GFE{n2}JYM{n2}",
     'GE {cap}cf French Door Refrig {fin}',
     {"cap": ['22.1', '25.6', '27.0'], "fin": ['SS', 'BK', 'WH']}, 6),

    ("kitchenaid-dw", "Whirlpool Corporation", "KDTM{n3}PPS",
     'KitchenAid {db}dBA DW {cyc}Cyc SS Tub',
     {"db": ['39', '44', '47'], "cyc": ['3', '5']}, 5),

    # ============ water heating & HVAC ==================================================
    ("rheem-elec-wh", "Rheem Manufacturing Company", "XE{n2}M{n2}H{n2}",
     'Rheem Elec WH {gal}gal {volt}V {watt}W',
     {"gal": ['30', '40', '50', '80'], "volt": ['240'], "watt": ['4500', '5500']}, 8),

    ("aosmith-gas-wh", "A. O. Smith Corporation", "GCR-{n2}",
     'AO Smith Gas WH {gal}gal {btu}BTU Atmos',
     {"gal": ['30', '40', '50'], "btu": ['32000', '36000', '40000']}, 7),

    ("bradford-elec-wh", "Bradford White Corporation", "RE{n3}S6",
     'Bradford Wht Elec WH {gal}gal {volt}V',
     {"gal": ['40', '50', '65'], "volt": ['208', '240']}, 5),

    ("carrier-cond", "Carrier Corporation", "24ABC6{n3}",
     'Carrier Cond Unit {ton}Ton {seer}SEER R410A',
     {"ton": ['1.5', '2', '2.5', '3', '4', '5'], "seer": ['14', '16']}, 9),

    ("trane-cond", "Trane U.S. Inc.", "4TTR{n1}B{n3}",
     'Trane Condenser {ton}Ton {seer}SEER 208/230V',
     {"ton": ['2', '3', '4'], "seer": ['14', '16']}, 6),

    ("honeywell-tstat", "Resideo Technologies, Inc.", "TH{n4}U{n4}",
     'Honeywell Prog Tstat {hstg}H/{cstg}C 24V',
     {"hstg": ['1', '2', '3'], "cstg": ['1', '2']}, 6),

    ("filter-pleated", "Honeywell Safety Products USA, Inc.", "FC{n3}A{n4}",
     'Pleated Air Filter {sz} MERV{merv} 12pk',
     {"sz": ['16x25x1', '20x20x1', '20x25x1', '16x25x4', '20x25x4'],
      "merv": ['8', '11', '13']}, 12),

    ("greenheck-grille", "Greenheck Fan Corporation", "GH{n5}",
     'Greenheck Return Grille {sz} Alum Wht',
     {"sz": ['12x12', '14x14', '20x20', '24x24']}, 5),

    # ============ electrical ============================================================
    ("squared-breaker", "Schneider Electric USA, Inc.", "QO{n3}{pole}",
     'Sq D QO CB {amp}A {pole}P {volt}V Plug-On',
     {"amp": ['15', '20', '30', '40', '50', '60'], "pole": ['1', '2'],
      "volt": ['120/240']}, 11),

    ("eaton-breaker", "Eaton Corporation", "BR{amp}{pole}",
     'Eaton BR CB {amp}A {pole}P 10kAIC',
     {"amp": ['15', '20', '30', '50'], "pole": ['1', '2']}, 7),

    ("bussmann-fuse", "Eaton Corporation", "LPJ-{amp}SP",
     'Bussmann LPJ Fuse {amp}A {volt}V Class J TD',
     {"amp": ['15', '20', '30', '60', '100'], "volt": ['600']}, 6),

    ("leviton-recep", "Leviton Manufacturing Co., Inc.", "T{n4}-{col}",
     'Leviton Dup Recep {amp}A {volt}V TR {col}',
     {"amp": ['15', '20'], "volt": ['125'], "col": ['W', 'I', 'BK', 'GY']}, 9),

    ("hubbell-gfci", "Hubbell Incorporated", "GFR{amp}{col}",
     'Hubbell GFCI Recep {amp}A Self-Test {col}',
     {"amp": ['15', '20'], "col": ['W', 'I', 'BK']}, 6),

    ("leviton-switch", "Leviton Manufacturing Co., Inc.", "PS{n3}-{col}",
     'Leviton Toggle Sw {amp}A {pole} {col} Comm',
     {"amp": ['15', '20'], "pole": ['1P', '3W'], "col": ['W', 'I', 'BR']}, 8),

    ("raco-box", "Hubbell Incorporated", "RAC{n4}",
     'RACO Steel Octagon Box {dep}in {ci}ci',
     {"dep": ['1-1/2', '2-1/8'], "ci": ['15.5', '21.0']}, 4),

    ("emt-connector", "ABB Inc.", "TB{n4}",
     'T&B EMT Conn {sz}in Set Screw Steel 25pk',
     {"sz": ['1/2', '3/4', '1', '1-1/4', '2']}, 6),

    ("southwire-thhn", "Southwire Company, LLC", "SW{n6}",
     'Southwire THHN {awg}AWG {strand} {col} 500ft',
     {"awg": ['12', '10', '8'], "strand": ['STR', 'SOL'],
      "col": ['BLK', 'WHT', 'GRN']}, 10),

    ("led-a19", "Hubbell Incorporated", "LED{n2}A19{n3}",
     'LED A19 Lamp {watt}W {lum}lm {kelv}K Dimm',
     {"watt": ['8', '9', '11'], "lum": ['800', '1100'],
      "kelv": ['2700', '3000', '4000', '5000']}, 10),

    # ============ motion & power transmission ==============================================
    ("skf-bearing", "SKF USA Inc.", "620{n1}-2RS",
     'SKF Ball Brg {bore}mm Bore {od}mm OD 2RS',
     {"bore": ['20', '25', '30', '35'], "od": ['47', '52', '62', '72']}, 7),

    ("baldor-motor", "ABB Motors and Mechanical Inc.", "VM{n4}",
     'Baldor Mtr {hp}HP {rpm}RPM {volt}V 3PH TEFC',
     {"hp": ['1/2', '1', '2', '3', '5'], "rpm": ['1750', '3450'],
      "volt": ['230/460']}, 9),

    ("leeson-motor", "Regal Rexnord Corporation", "C{n6}",
     'Leeson Mtr {hp}HP {rpm}RPM {frame} 1PH',
     {"hp": ['1/3', '1/2', '3/4'], "rpm": ['1725'],
      "frame": ['56C', '56J', '48Y']}, 6),

    ("gates-belt", "Gates Corporation", "{sect}{n4}",
     'Gates {sect} V-Belt {len}in OL Cogged',
     {"sect": ['AX', 'BX', 'A', 'B'], "len": ['32', '38', '44', '50', '56']}, 9),

    # ============ decking ==================================================================
    ("azek-deck", "The AZEK Company LLC", "AZ{coll3}{n4}",
     'AZEK {coll} Deck Bd {col} {prof} {len}ft',
     {"coll": ['Harvest', 'Landmark', 'Vintage'],
      "col": ['Brownstone', 'Coastline', 'Mahogany', 'Weathered Teak', 'Slate Gray',
              'Castle Gate'],
      "prof": ['Grooved', 'Square'], "len": ['12', '16', '20']}, 22),

    ("timbertech-rail", "The AZEK Company LLC", "TT{n6}",
     'TimberTech Rail Kit {ht}in {len}ft {col}',
     {"ht": ['36', '42'], "len": ['6', '8'],
      "col": ['White', 'Black', 'Brown']}, 7),

    ("trex-deck", "Trex Company, Inc.", "TRX{n5}",
     'Trex {coll} Deck Board {col} {len}ft Grooved',
     {"coll": ['Enhance', 'Select', 'Transcend'],
      "col": ['Beach Dune', 'Rocky Harbor', 'Spiced Rum', 'Island Mist'],
      "len": ['12', '16', '20']}, 12),

    # ============ fasteners =================================================================
    ("griprite-deck-screw", "PrimeSource Building Products, Inc.", "GR{n6}",
     'Grip-Rite Deck Screw #{gau} x {len}in {fin} {qty}lb',
     {"gau": ['8', '9', '10'], "len": ['1-5/8', '2', '2-1/2', '3'],
      "fin": ['TAN', 'GRN', 'ZP'], "qty": ['1', '5', '25']}, 14),

    ("simpson-anchor", "Simpson Strong-Tie Company Inc.", "STB2-{n5}",
     'Simpson Strong-Bolt2 Anchor {dia}in x {len}in {qty}bx',
     {"dia": ['1/4', '3/8', '1/2', '5/8'], "len": ['2-1/4', '3', '3-3/4', '5'],
      "qty": ['20', '50', '100']}, 11),

    ("hilti-anchor", "Hilti, Inc.", "HIL{n6}",
     'Hilti KB-TZ2 Anchor {dia} x {len} SS304',
     {"dia": ['3/8', '1/2'], "len": ['3', '3-3/4', '5']}, 5),

    # ============ safety ======================================================================
    ("msa-glasses", "MSA Safety Incorporated", "MSA{n6}",
     'MSA Safety Glasses {lens} AF Lens Blk Frame',
     {"lens": ['Clear', 'Grey', 'Amber', 'Mirror']}, 5),

    ("ansell-glove", "Ansell Limited", "AN{n2}-{n3}",
     'Ansell HyFlex Glove Sz{sz} Cut A{cut} PU Palm',
     {"sz": ['7', '8', '9', '10', '11'], "cut": ['2', '4', '5']}, 9),

    ("peltor-muff", "3M Company", "PEL{n5}",
     '3M Peltor Ear Muff NRR{nrr} {style}',
     {"nrr": ['24', '26', '30'], "style": ['Over-Head', 'Cap-Mount', 'Neckband']}, 6),

    # ============ chemicals ====================================================================
    ("loctite-thread", "Henkel Corporation", "LOC{n6}",
     'Loctite {num} Threadlocker {col} {ml}ml',
     {"num": ['242', '243', '271', '290'], "col": ['BLU', 'RED', 'GRN'],
      "ml": ['10', '50', '250']}, 10),

    ("rustoleum-spray", "RPM International Inc.", "RO{n6}",
     'Rust-Oleum Spray Enamel {col} {sheen} 12oz',
     {"col": ['Black', 'White', 'Gray', 'Red', 'Almond'],
      "sheen": ['Gloss', 'Satin', 'Flat']}, 10),

    ("wd40-oil", "WD-40 Company", "WD{n5}",
     'WD-40 Penetrant {sz}oz {typ}',
     {"sz": ['8', '11', '12'], "typ": ['Smart Straw', 'Aerosol']}, 4),

    ("permatex-sealant", "Illinois Tool Works Inc.", "PTX{n5}",
     'Permatex Pipe Sealant PTFE {ml}ml {col}',
     {"ml": ['50', '250'], "col": ['WHT', 'BLU']}, 3),
]

DISTRIBUTOR_POOL = seed_mfr.DISTRIBUTOR_NAMES
ACCOUNT_ARTEFACT = [
    "{mfr_short} Accessory ({acct})",
    "{mfr_short} Div ({acct})",
    "{mfr_short} Direct",
    "{mfr_short} Program {acct}",
]


def _pn_token(rng: random.Random, key: str) -> str:
    if key == "n1":
        return str(rng.randint(1, 9))
    if key == "n2":
        return f"{rng.randint(10, 99)}"
    if key == "n3":
        return f"{rng.randint(100, 999)}"
    if key == "n4":
        return f"{rng.randint(1000, 9999)}"
    if key == "n5":
        return f"{rng.randint(10000, 99999)}"
    if key == "n6":
        return f"{rng.randint(100000, 999999)}"
    return key


def _fill_pn(pattern: str, combo: dict[str, str], rng: random.Random) -> str:
    out = pattern
    for key in ("n6", "n5", "n4", "n3", "n2", "n1"):
        while "{" + key + "}" in out:
            out = out.replace("{" + key + "}", _pn_token(rng, key), 1)
    for k, val in combo.items():
        token = val.strip().replace(" ", "")
        out = out.replace("{" + k + "}", token)
        out = out.replace("{" + k + "3}", token[:3].upper())
    # leftovers such as {coll3}
    import re
    out = re.sub(r"\{[a-z0-9_]+\}", lambda m: _pn_token(rng, "n3"), out)
    return out


def _short_mfr(mfr: str) -> str:
    return mfr.split(",")[0].split(" Inc")[0].split(" LLC")[0].split(" Co.")[0].strip()


def _part_manuf(rng: random.Random, mfr: str, line_id: str) -> str:
    """Part_Manuf names whoever invoiced, so it is frequently not the manufacturer."""
    # Pinned rows from the deck.
    if line_id == "milw-cutoff":
        return "Milwaukee Accessory (4031)"
    if line_id == "3m-stikit":
        return "Jam Industrial Supply"
    if line_id == "frigidaire-dw":
        return "Rheem Manufacturing"
    r = rng.random()
    if r < 0.18:
        return rng.choice(DISTRIBUTOR_POOL)
    if r < 0.30:
        tmpl = rng.choice(ACCOUNT_ARTEFACT)
        return tmpl.format(mfr_short=_short_mfr(mfr), acct=rng.randint(1000, 9999))
    if r < 0.36:
        # casing / spacing noise on an otherwise correct name
        s = _short_mfr(mfr)
        return rng.choice([s.upper(), s.lower(), s.replace(" ", "  "), s + " ."])
    return mfr


def _brand_cells(rng: random.Random, brand_hint: str) -> tuple[str, str, str]:
    e1 = brand_hint if rng.random() < P_E1_REAL else UNBRANDED
    ul = brand_hint if rng.random() < P_UNILOG_REAL else NO_UNILOG
    db = brand_hint if rng.random() < P_DIB_REAL else NO_DIB
    return e1, ul, db


def _brand_hint(desc: str, mfr: str) -> str:
    tok = desc.split()[0]
    return tok if tok and not tok[0].isdigit() else _short_mfr(mfr)


def build_rows() -> list[dict]:
    rng = random.Random(SEED)
    rows: list[dict] = []
    seen_pn: set[str] = set()

    total_weight = sum(w for *_x, w in LINES)
    for line_id, mfr, pn_pattern, desc_tmpl, axes, weight in LINES:
        quota = max(1, round(TARGET_ROWS * weight / total_weight))
        if axes:
            keys = list(axes.keys())
            combos = list(itertools.product(*(axes[k] for k in keys)))
            rng.shuffle(combos)
            combos = combos[:quota]
            dicts = [dict(zip(keys, c)) for c in combos]
        else:
            dicts = [{} for _ in range(quota)]

        for combo in dicts:
            desc = desc_tmpl
            for k, val in combo.items():
                desc = desc.replace("{" + k + "}", val)
            pn = _fill_pn(pn_pattern, combo, rng)
            # a description template may itself embed the part-number stem
            import re
            desc = re.sub(r"\{n\d\}", lambda m: pn[-4:], desc)
            if pn in seen_pn:
                continue
            seen_pn.add(pn)
            hint = _brand_hint(desc, mfr)
            e1, ul, db = _brand_cells(rng, hint)
            rows.append({
                "Mfg_Part_Num": pn,
                "Part_Desc": desc,
                "E1_Brand": e1,
                "Unilog_Brand": ul,
                "DIB_Brand": db,
                "Part_Manuf": _part_manuf(rng, mfr, line_id),
                "_line": line_id,
                "_axes": dict(combo),
            })

    # ---- pin the exact rows the prototype deck quotes --------------------------------
    pinned = [
        {"Mfg_Part_Num": "49-94-0013",
         "Part_Desc": 'Milw 5"x.045"x7/8" Metal Cut Off Disc',
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Milwaukee Accessory (4031)", "_line": "milw-cutoff"},
        {"Mfg_Part_Num": "49-94-0030",
         "Part_Desc": 'Milw 6"x.045"x7/8" Metal Cut Off Disc',
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Milwaukee Accessory (4031)", "_line": "milw-cutoff"},
        {"Mfg_Part_Num": "49-94-4505",
         "Part_Desc": 'Milw 4-1/2"x.045"x7/8" Metal Cut Off Disc',
         "E1_Brand": "Milw", "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Milwaukee Accessory (4031)", "_line": "milw-cutoff"},
        {"Mfg_Part_Num": "3MABR-7100075678",
         "Part_Desc": "3M 775L Stikit Film [P150] - Cubitron II 50 Disc/Box",
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Jam Industrial Supply", "_line": "3m-stikit"},
        {"Mfg_Part_Num": "3MABR-7100045865",
         "Part_Desc": "3M 775L Stikit Film [P120] - Cubitron II 50 Disc/Box",
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Jam Industrial Supply", "_line": "3m-stikit"},
        {"Mfg_Part_Num": "3MABR-7100048736",
         "Part_Desc": "3M 775L Stikit Film [P80 ] - Cubitron II 50 Disc/Box",
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Jam Industrial Supply", "_line": "3m-stikit"},
        {"Mfg_Part_Num": "3MABR-7100075690",
         "Part_Desc": "3M 775L Stikit Film [P180] - Cubitron II 50 Disc/Box",
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Jam Industrial Supply", "_line": "3m-stikit"},
        {"Mfg_Part_Num": "3MABR-7100075692",
         "Part_Desc": "3M 775L Stikit Film [P220] - Cubitron II 50 Disc/Box",
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Jam Industrial Supply", "_line": "3m-stikit"},
        {"Mfg_Part_Num": "3MABR-7100145365",
         "Part_Desc": "3M 775L Stikit Film [P320] - Cubitron II 50 Disc/Box",
         "E1_Brand": UNBRANDED, "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Jam Industrial Supply", "_line": "3m-stikit"},
        # The contradiction. Row 1 of the client's own reference file pairs a
        # water-heater manufacturer with a kitchen-appliance brand.
        {"Mfg_Part_Num": "PDSH4816AF",
         "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
         "E1_Brand": "FRIGIDAIRE", "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Rheem Manufacturing", "_line": "frigidaire-dw"},
        # Two more genuine contradictions, planted the same way real ones arrive.
        {"Mfg_Part_Num": "K-596-VS",
         "Part_Desc": "KOHLER Simplice Kit Fct 1H Pullout VS",
         "E1_Brand": "KOHLER", "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Moen Incorporated", "_line": "kohler-kitchen"},
        {"Mfg_Part_Num": "QO120CP",
         "Part_Desc": "Sq D QO CB 20A 1P 120/240V Plug-On",
         "E1_Brand": "Square D", "Unilog_Brand": NO_UNILOG, "DIB_Brand": NO_DIB,
         "Part_Manuf": "Eaton Corporation", "_line": "squared-breaker"},
    ]
    have = {r["Mfg_Part_Num"] for r in rows}
    rows = [r for r in rows if r["Mfg_Part_Num"] not in {p["Mfg_Part_Num"] for p in pinned}]
    rows = pinned + rows

    # ---- trim / pad to exactly TARGET_ROWS -------------------------------------------
    if len(rows) > TARGET_ROWS:
        head = rows[:len(pinned)]
        tail = rows[len(pinned):]
        rng.shuffle(tail)
        rows = head + tail[:TARGET_ROWS - len(head)]
    elif len(rows) < TARGET_ROWS:
        # pad with additional axis draws from the widest lines
        i = 0
        while len(rows) < TARGET_ROWS:
            line_id, mfr, pn_pattern, desc_tmpl, axes, _w = LINES[i % len(LINES)]
            i += 1
            if not axes:
                continue
            combo = {k: rng.choice(vals) for k, vals in axes.items()}
            desc = desc_tmpl
            for k, val in combo.items():
                desc = desc.replace("{" + k + "}", val)
            pn = _fill_pn(pn_pattern, combo, rng)
            import re
            desc = re.sub(r"\{n\d\}", lambda m: pn[-4:], desc)
            if pn in {r["Mfg_Part_Num"] for r in rows}:
                continue
            hint = _brand_hint(desc, mfr)
            e1, ul, db = _brand_cells(rng, hint)
            rows.append({
                "Mfg_Part_Num": pn, "Part_Desc": desc,
                "E1_Brand": e1, "Unilog_Brand": ul, "DIB_Brand": db,
                "Part_Manuf": _part_manuf(rng, mfr, line_id), "_line": line_id,
                "_axes": dict(combo),
            })

    # order: pinned rows first (so the deck's row 1 really is row 1), then shuffled
    head = rows[:len(pinned)]
    tail = rows[len(pinned):]
    rng.shuffle(tail)
    return head + tail


def main() -> None:
    rows = build_rows()
    for r in rows:
        r.pop("_axes", None)
    df = pd.DataFrame(rows)[C.INPUT_COLUMNS + ["_line"]]
    lines = df["_line"].copy()

    # Sidecar: generator metadata, consumed ONLY by tools/make_documents.py so it can
    # build plausible document fixtures. The pipeline never reads it - if it did, the
    # discovery stages would be marking their own homework.
    side = df[["Mfg_Part_Num", "_line"]].rename(columns={"_line": "line"})
    side.to_csv(C.DATA_IN / "_reconstruction_lines.csv", index=False)

    df = df.drop(columns=["_line"])
    out = C.DATA_IN / C.RECONSTRUCTION_INPUT
    df.to_excel(out, index=False, sheet_name="Sheet1")

    # profile, printed so the numbers can be checked against the deck's framing
    brand_cells = df[["E1_Brand", "Unilog_Brand", "DIB_Brand"]].values.ravel()
    placeholders = sum(1 for c in brand_cells
                       if str(c).strip().startswith("--"))
    desc_len = df["Part_Desc"].str.len()
    dist_kw = tuple(seed_mfr.DISTRIBUTOR_KEYWORDS)
    masked = sum(1 for v in df["Part_Manuf"]
                 if any(k in str(v).lower() for k in dist_kw)
                 or "(" in str(v))

    print(f"wrote {out}")
    print(f"  rows                      {len(df)}")
    print(f"  unique part numbers       {df['Mfg_Part_Num'].nunique()}")
    print(f"  product lines             {lines.nunique()}")
    print(f"  brand cells               {len(brand_cells)}")
    print(f"  placeholder brand cells   {placeholders} "
          f"({placeholders / len(brand_cells) * 100:.1f}%)")
    print(f"  mean Part_Desc length     {desc_len.mean():.1f} chars "
          f"(min {desc_len.min()}, max {desc_len.max()})")
    print(f"  Part_Manuf needing work   {masked} ({masked / len(df) * 100:.1f}%)")


if __name__ == "__main__":
    main()
