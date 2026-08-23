"""Approved manufacturer + brand pairs, with exact legal casing and marks.

Three jobs are served from one table:

  1. normalise a messy supplier string to a canonical manufacturer, then pick the
     paired brand (where an item has no brand, the manufacturer name is used);
  2. own the brand -> parent-manufacturer relation, which is what makes the
     contradiction check possible ("FRIGIDAIRE(R) is Electrolux, not Rheem");
  3. own the manufacturer -> domain relation, which is what makes the sourcing
     hierarchy enforceable before a request is made.

Casing, suffixes and (R)/(TM) marks are part of the data, not decoration.
"""
from __future__ import annotations

# (manufacturer_name, mfr_code, brand_name, brand_code, primary_domain, sector, aliases)
ENTRIES: list[tuple[str, str, str, str, str, str, list[str]]] = [
    # ---- abrasives / power tool accessories -----------------------------------------
    ("Milwaukee Tool", "MILW", "Milwaukee\u00ae", "MLWK", "milwaukeetool.com", "power tools",
     ["milwaukee", "milw", "milwaukee electric tool", "milwaukee accessory", "mlw"]),
    ("3M Company", "3MCO", "3M\u2122", "3MMM", "3m.com", "abrasives",
     ["3m", "3-m", "three m", "3mabr", "minnesota mining"]),
    ("Saint-Gobain Abrasives, Inc.", "SGAB", "Norton\u00ae", "NRTN", "nortonabrasives.com", "abrasives",
     ["norton", "saint gobain", "saint-gobain", "norton abrasives"]),
    ("Weiler Abrasives Group", "WEIL", "Weiler\u00ae", "WLER", "weilerabrasives.com", "abrasives",
     ["weiler", "weiler brush"]),
    ("Walter Surface Technologies", "WLTR", "Walter\u00ae", "WLTS", "walter.com", "abrasives",
     ["walter", "walter surface"]),
    ("Freud America, Inc.", "FRUD", "Diablo\u00ae", "DBLO", "diablotools.com", "cutting tools",
     ["diablo", "freud", "freud america"]),
    ("Lenox Tools", "LNOX", "LENOX\u00ae", "LNXT", "lenoxtools.com", "cutting tools",
     ["lenox", "lenox tools", "american saw"]),
    # ---- power tools ----------------------------------------------------------------
    ("Stanley Black & Decker, Inc.", "SBDC", "DEWALT\u00ae", "DWLT", "dewalt.com", "power tools",
     ["dewalt", "de walt", "stanley black decker", "black & decker", "dwt"]),
    ("Robert Bosch Tool Corporation", "BSCH", "Bosch\u00ae", "BSCT", "boschtools.com", "power tools",
     ["bosch", "robert bosch", "bosch tool"]),
    ("Makita U.S.A., Inc.", "MKTA", "Makita\u00ae", "MKTB", "makitatools.com", "power tools",
     ["makita", "makita usa"]),
    ("Emerson Electric Co.", "EMRS", "RIDGID\u00ae", "RIDG", "ridgid.com", "pipe tools",
     ["ridgid", "rigid", "emerson", "ridge tool"]),
    ("Emerson Electric Co.", "EMRS", "Greenlee\u00ae", "GRNL", "greenlee.com", "electrical tools",
     ["greenlee", "green lee", "textron greenlee"]),
    ("Klein Tools, Inc.", "KLEN", "Klein Tools\u00ae", "KLNT", "kleintools.com", "hand tools",
     ["klein", "klein tools", "kleintools"]),
    ("Ideal Industries, Inc.", "IDEL", "IDEAL\u00ae", "IDLI", "idealind.com", "electrical tools",
     ["ideal", "ideal industries", "ideal ind"]),
    ("Techtronic Industries Co. Ltd.", "TTID", "RYOBI\u00ae", "RYBI", "ryobitools.com", "power tools",
     ["ryobi", "techtronic"]),
    ("Hilti, Inc.", "HILT", "Hilti\u00ae", "HLTI", "hilti.com", "anchors",
     ["hilti", "hilti inc"]),
    ("Illinois Tool Works Inc.", "ITWI", "Ramset\u00ae", "RMST", "ramset.com", "anchors",
     ["ramset", "itw ramset"]),
    ("Illinois Tool Works Inc.", "ITWI", "Paslode\u00ae", "PSLD", "paslode.com", "fastening",
     ["paslode", "itw paslode"]),
    ("Simpson Strong-Tie Company Inc.", "SSTC", "Simpson Strong-Tie\u00ae", "SSTB",
     "strongtie.com", "structural connectors", ["simpson", "simpson strong tie", "strong-tie"]),
    # ---- appliances -----------------------------------------------------------------
    ("Electrolux Home Products, Inc.", "ELUX", "FRIGIDAIRE\u00ae", "FRGD", "frigidaire.com",
     "major appliances", ["frigidaire", "electrolux", "frigidaire professional", "pdsh"]),
    ("Whirlpool Corporation", "WHRL", "Whirlpool\u00ae", "WHPL", "whirlpool.com",
     "major appliances", ["whirlpool", "whirpool"]),
    ("Whirlpool Corporation", "WHRL", "KitchenAid\u00ae", "KTAD", "kitchenaid.com",
     "major appliances", ["kitchenaid", "kitchen aid"]),
    ("GE Appliances", "GEAP", "GE\u00ae", "GEAB", "geappliances.com", "major appliances",
     ["ge appliances", "general electric appliances", "ge app"]),
    ("Rheem Manufacturing Company", "RHEM", "Rheem\u00ae", "RHMB", "rheem.com",
     "water heating & HVAC", ["rheem", "rheem manufacturing", "rheem mfg"]),
    ("Rheem Manufacturing Company", "RHEM", "Ruud\u00ae", "RUUD", "ruud.com",
     "water heating & HVAC", ["ruud"]),
    ("A. O. Smith Corporation", "AOSM", "A. O. Smith\u00ae", "AOSB", "hotwater.com",
     "water heating", ["ao smith", "a.o. smith", "a o smith", "aosmith"]),
    ("Bradford White Corporation", "BRDW", "Bradford White\u00ae", "BRDB", "bradfordwhite.com",
     "water heating", ["bradford white", "bradford-white"]),
    # ---- decking & building products -------------------------------------------------
    ("The AZEK Company LLC", "AZEK", "AZEK\u00ae", "AZKB", "azekexteriors.com", "decking",
     ["azek", "azek company", "azek exteriors"]),
    ("The AZEK Company LLC", "AZEK", "TimberTech\u00ae", "TMBT", "timbertech.com", "decking",
     ["timbertech", "timber tech"]),
    ("Trex Company, Inc.", "TREX", "Trex\u00ae", "TRXB", "trex.com", "decking",
     ["trex", "trex company"]),
    ("James Hardie Building Products Inc.", "JHRD", "HardiePlank\u00ae", "HRDP",
     "jameshardie.com", "siding", ["james hardie", "hardie", "hardieplank"]),
    # ---- plumbing: fittings, valves, fixtures ----------------------------------------
    ("NIBCO INC.", "NIBC", "NIBCO\u00ae", "NBCO", "nibco.com", "valves & fittings",
     ["nibco", "nib co"]),
    ("Mueller Industries, Inc.", "MULR", "Mueller\u00ae", "MULB", "muellerindustries.com",
     "copper tube & fittings", ["mueller", "mueller industries", "mueller streamline"]),
    ("Charlotte Pipe and Foundry Company", "CHPF", "Charlotte Pipe\u00ae", "CHPB",
     "charlottepipe.com", "plastic pipe & fittings", ["charlotte pipe", "charlotte", "chp"]),
    ("Viega LLC", "VIEG", "Viega\u00ae", "VIEB", "viega.us", "press fittings",
     ["viega", "viega llc"]),
    ("Uponor, Inc.", "UPON", "Uponor\u00ae", "UPNB", "uponor.com", "PEX systems",
     ["uponor", "wirsbo"]),
    ("Anvil International, LLC", "ANVL", "Anvil\u00ae", "ANVB", "anvilintl.com", "pipe fittings",
     ["anvil", "anvil international", "gruvlok"]),
    ("Victaulic Company", "VICT", "Victaulic\u00ae", "VICB", "victaulic.com", "grooved piping",
     ["victaulic", "vic"]),
    ("Aalberts integrated piping systems Americas", "AALB", "Apollo\u00ae", "APLO",
     "apollovalves.com", "valves", ["apollo", "apollo valves", "conbraco"]),
    ("Watts Water Technologies, Inc.", "WATT", "Watts\u00ae", "WTTB", "watts.com",
     "water control", ["watts", "watts water", "watts regulator"]),
    ("Zurn Industries, LLC", "ZURN", "Zurn\u00ae", "ZRNB", "zurn.com", "commercial plumbing",
     ["zurn", "zurn industries", "wilkins"]),
    ("Sloan Valve Company", "SLON", "Sloan\u00ae", "SLNB", "sloan.com", "flushometers",
     ["sloan", "sloan valve"]),
    ("Moen Incorporated", "MOEN", "Moen\u00ae", "MOEB", "moen.com", "faucets",
     ["moen", "moen inc"]),
    ("Masco Corporation of Indiana", "MSCO", "Delta\u00ae", "DLTA", "deltafaucet.com", "faucets",
     ["delta", "delta faucet", "masco"]),
    ("Kohler Co.", "KOHL", "KOHLER\u00ae", "KHLB", "kohler.com", "faucets & fixtures",
     ["kohler", "kohler co"]),
    ("LIXIL Water Technology Americas", "LIXL", "American Standard\u00ae", "AMST",
     "americanstandard-us.com", "faucets & fixtures",
     ["american standard", "americanstandard", "lixil"]),
    ("Chicago Faucet Company", "CHGF", "Chicago Faucets\u00ae", "CHGB", "chicagofaucets.com",
     "commercial faucets", ["chicago faucet", "chicago faucets"]),
    ("T&S Brass and Bronze Works, Inc.", "TSBR", "T&S\u00ae", "TSBB", "tsbrass.com",
     "commercial faucets", ["t&s brass", "t and s brass", "ts brass"]),
    # ---- pumps & hydronics ------------------------------------------------------------
    ("Xylem Inc.", "XYLM", "Bell & Gossett\u00ae", "BLGS", "bellgossett.com", "hydronics",
     ["bell & gossett", "bell and gossett", "b&g", "xylem"]),
    ("Taco Comfort Solutions", "TACO", "Taco\u00ae", "TACB", "tacocomfort.com", "hydronics",
     ["taco", "taco comfort"]),
    ("Grundfos Pumps Corporation", "GRND", "Grundfos\u00ae", "GRNB", "grundfos.com", "pumps",
     ["grundfos", "grundfos pumps"]),
    ("Zoeller Pump Company", "ZOEL", "Zoeller\u00ae", "ZOEB", "zoeller.com", "pumps",
     ["zoeller", "zoeller pump"]),
    # ---- HVAC --------------------------------------------------------------------------
    ("Carrier Corporation", "CARR", "Carrier\u00ae", "CARB", "carrier.com", "HVAC",
     ["carrier", "carrier corp"]),
    ("Trane U.S. Inc.", "TRNE", "Trane\u00ae", "TRNB", "trane.com", "HVAC",
     ["trane", "trane us"]),
    ("Lennox Industries Inc.", "LENX", "Lennox\u00ae", "LNXB", "lennox.com", "HVAC",
     ["lennox", "lennox industries"]),
    ("Resideo Technologies, Inc.", "RSDO", "Honeywell Home\u00ae", "HNYH", "honeywellhome.com",
     "controls", ["honeywell home", "resideo", "honeywell"]),
    ("Johnson Controls, Inc.", "JCIN", "Johnson Controls\u00ae", "JCIB", "johnsoncontrols.com",
     "controls", ["johnson controls", "jci", "penn"]),
    ("Greenheck Fan Corporation", "GRNH", "Greenheck\u00ae", "GRHB", "greenheck.com",
     "air movement", ["greenheck", "greenheck fan"]),
    # ---- electrical ---------------------------------------------------------------------
    ("Schneider Electric USA, Inc.", "SCHN", "Square D\u00ae", "SQRD", "se.com", "electrical",
     ["square d", "squared", "schneider", "schneider electric"]),
    ("Eaton Corporation", "EATN", "Eaton\u00ae", "EATB", "eaton.com", "electrical",
     ["eaton", "cutler hammer", "cutler-hammer"]),
    ("Eaton Corporation", "EATN", "Bussmann\u00ae", "BSMN", "eaton.com", "circuit protection",
     ["bussmann", "buss", "cooper bussmann"]),
    ("ABB Inc.", "ABBI", "ABB\u00ae", "ABBB", "abb.com", "electrical",
     ["abb", "abb inc", "thomas & betts", "thomas and betts", "t&b"]),
    ("Hubbell Incorporated", "HUBL", "Hubbell\u00ae", "HUBB", "hubbell.com", "electrical",
     ["hubbell", "hubbell inc", "raco", "bell"]),
    ("Leviton Manufacturing Co., Inc.", "LEVT", "Leviton\u00ae", "LEVB", "leviton.com",
     "wiring devices", ["leviton", "leviton mfg"]),
    ("Legrand North America, LLC", "LGRD", "Wiremold\u00ae", "WRMD", "legrand.us",
     "raceway", ["wiremold", "legrand", "pass & seymour", "pass and seymour"]),
    ("Panduit Corp.", "PNDT", "Panduit\u00ae", "PNDB", "panduit.com", "cable management",
     ["panduit", "panduit corp"]),
    ("Rockwell Automation, Inc.", "RCKW", "Allen-Bradley\u00ae", "ALBR", "rockwellautomation.com",
     "automation", ["allen bradley", "allen-bradley", "rockwell", "a-b"]),
    ("Littelfuse, Inc.", "LTLF", "Littelfuse\u00ae", "LTLB", "littelfuse.com",
     "circuit protection", ["littelfuse", "littel fuse"]),
    ("Phoenix Contact USA", "PHNX", "Phoenix Contact\u00ae", "PHXB", "phoenixcontact.com",
     "terminal blocks", ["phoenix contact", "phoenixcontact"]),
    ("Southwire Company, LLC", "SWIR", "Southwire\u00ae", "SWRB", "southwire.com", "wire & cable",
     ["southwire", "south wire"]),
    # ---- motion & power transmission ------------------------------------------------------
    ("SKF USA Inc.", "SKFU", "SKF\u00ae", "SKFB", "skf.com", "bearings", ["skf", "skf usa"]),
    ("The Timken Company", "TMKN", "Timken\u00ae", "TMKB", "timken.com", "bearings",
     ["timken", "timken company"]),
    ("RBC Bearings Incorporated", "RBCB", "Dodge\u00ae", "DODG", "rbcbearings.com", "bearings",
     ["dodge", "rbc bearings", "dodge bearings"]),
    ("ABB Motors and Mechanical Inc.", "ABBM", "Baldor-Reliance\u00ae", "BLDR", "baldor.abb.com",
     "motors", ["baldor", "baldor reliance", "reliance electric"]),
    ("Regal Rexnord Corporation", "RGLR", "Leeson\u00ae", "LESN", "regalrexnord.com", "motors",
     ["leeson", "regal rexnord", "regal beloit"]),
    ("Gates Corporation", "GATS", "Gates\u00ae", "GATB", "gates.com", "belts & hose",
     ["gates", "gates corp", "gates rubber"]),
    ("WEG Electric Corp.", "WEGE", "WEG\u00ae", "WEGB", "weg.net", "motors", ["weg", "weg electric"]),
    # ---- chemicals, adhesives, coatings -----------------------------------------------------
    ("Henkel Corporation", "HNKL", "LOCTITE\u00ae", "LCTT", "henkel-adhesives.com", "adhesives",
     ["loctite", "henkel", "loc tite"]),
    ("Illinois Tool Works Inc.", "ITWI", "Permatex\u00ae", "PRMX", "permatex.com", "sealants",
     ["permatex", "itw permatex"]),
    ("RPM International Inc.", "RPMI", "Rust-Oleum\u00ae", "RSTO", "rustoleum.com", "coatings",
     ["rust-oleum", "rust oleum", "rustoleum", "rpm"]),
    ("The Sherwin-Williams Company", "SHRW", "Sherwin-Williams\u00ae", "SHWB",
     "sherwin-williams.com", "coatings", ["sherwin williams", "sherwin-williams", "sherwin"]),
    ("PPG Industries, Inc.", "PPGI", "PPG\u00ae", "PPGB", "ppg.com", "coatings",
     ["ppg", "ppg industries"]),
    ("WD-40 Company", "WD40", "WD-40\u00ae", "WD4B", "wd40.com", "lubricants",
     ["wd-40", "wd 40", "wd40"]),
    # ---- safety -----------------------------------------------------------------------------
    ("Honeywell Safety Products USA, Inc.", "HNSP", "North\u00ae", "NRTH", "honeywell.com",
     "PPE", ["north safety", "honeywell safety", "north"]),
    ("MSA Safety Incorporated", "MSAS", "MSA\u00ae", "MSAB", "msasafety.com", "PPE",
     ["msa", "msa safety", "mine safety"]),
    ("Ansell Limited", "ANSL", "Ansell\u00ae", "ANSB", "ansell.com", "PPE",
     ["ansell", "ansell ltd"]),
    ("3M Company", "3MCO", "Peltor\u2122", "PLTR", "3m.com", "PPE", ["peltor", "3m peltor"]),
    # ---- fasteners --------------------------------------------------------------------------
    ("PrimeSource Building Products, Inc.", "PRMS", "Grip-Rite\u00ae", "GRPR", "grip-rite.com",
     "fasteners", ["grip rite", "grip-rite", "primesource"]),
    ("Stanley Black & Decker, Inc.", "SBDC", "Powers Fasteners\u00ae", "PWRF", "dewalt.com",
     "anchors", ["powers fasteners", "powers"]),
]

# Buying groups, co-ops and distributors that appear in Part_Manuf because the field
# names whoever invoiced the goods. These are never valid manufacturers.
DISTRIBUTOR_NAMES = [
    "Jam Industrial Supply",
    "Appliance Dealers Cooperative",
    "Affiliated Distributors",
    "Blue Hawk Cooperative",
    "IMARK Group",
    "NetPlus Alliance",
    "Omni Cooperative",
    "SupplyForce",
    "United Supply Group",
    "Winsupply Inc.",
    "Hardware Wholesalers Inc",
    "Midwest Fastener Wholesale",
    "Pacific Coast Distributing",
    "Great Lakes Industrial Sourcing",
    "Southeast MRO Distributors",
    "Atlantic Trading Company",
    "Summit Supply Partners",
    "Keystone Industrial Warehouse",
    "Tri-State Plumbing Wholesale",
    "National Appliance Buying Group",
]

DISTRIBUTOR_KEYWORDS = [
    "industrial supply", "supply co", "supply company", "supply partners",
    "cooperative", "co-op", "buying group", "dealers cooperative",
    "distributors", "distributing", "distribution",
    "wholesale", "wholesalers", "warehouse", "trading company", "trading co",
    "sourcing", "mro", "alliance", "affiliated", "group inc", "imports",
    "winsupply", "supplyforce", "netplus",
]

# Vendor-account artefacts that ride along in Part_Manuf: "Milwaukee Accessory (4031)".
ACCOUNT_SUFFIX_TOKENS = [
    "accessory", "accessories", "acct", "account", "vendor", "div", "division",
    "dist", "direct", "program", "line",
]


def build_entries() -> list[dict]:
    out = []
    for mfr, mcode, brand, bcode, domain, sector, aliases in ENTRIES:
        out.append({
            "manufacturer_name": mfr,
            "manufacturer_code": mcode,
            "brand_name": brand,
            "brand_code": bcode,
            "domain": domain,
            "sector": sector,
            "aliases": aliases,
        })
    return out


def manufacturer_domains() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for mfr, _mc, _b, _bc, domain, _s, _a in ENTRIES:
        out.setdefault(mfr, set()).add(domain)
    return out


def brand_owner() -> dict[str, str]:
    """brand_name -> manufacturer_name. The relation the contradiction check runs on."""
    return {brand: mfr for mfr, _mc, brand, _bc, _d, _s, _a in ENTRIES}


def sector_of() -> dict[str, str]:
    return {mfr: sector for mfr, _mc, _b, _bc, _d, sector, _a in ENTRIES}
