"""Derived taxonomy: classpath, leaf node, UNSPSC and the attribute sequence per leaf.

This is the seed spine, not the client's 161,000-row List of Values. Two categories are
carried to full depth deliberately, mirroring the two the pack specifies end to end
(faucets and fittings), because depth beats breadth: one category classified,
attributed, described and validated proves more than a thin pass over everything.

An item type that does not resolve here is NOT guessed into the nearest bucket. It is
routed to the review queue as one mapping decision that unblocks every record sharing
that item type.
"""
from __future__ import annotations

# classpath, leaf, unspsc, item-type keywords, attribute sequence (LOV order)
LEAVES: list[tuple[str, str, str, list[str], list[str]]] = [
    # ---- abrasives & power tool accessories ------------------------------------------
    ("Tools & Equipment>Power Tool Accessories>Cut-Off Wheels", "Cut-Off Wheels", "27112800",
     ["cut off disc", "cut-off disc", "cut off wheel", "cut-off wheel", "cutoff wheel",
      "abrasive wheel", "chop saw wheel", "metal cut off"],
     ["Diameter", "Thickness", "Arbor Size", "Grit", "Material", "Maximum Speed",
      "Package Quantity", "Application"]),
    ("Tools & Equipment>Power Tool Accessories>Grinding Wheels", "Grinding Wheels", "27112801",
     ["grinding wheel", "grinding disc", "depressed center wheel", "type 27 wheel"],
     ["Diameter", "Thickness", "Arbor Size", "Grit", "Material", "Maximum Speed",
      "Package Quantity"]),
    ("Tools & Equipment>Power Tool Accessories>Sanding Discs", "Sanding Discs", "31191500",
     ["sanding disc", "abrasive disc", "stikit disc", "hook and loop disc", "film disc",
      "sanding sheet", "stikit film"],
     ["Diameter", "Grit", "Abrasive Material", "Backing", "Attachment Type",
      "Package Quantity"]),
    ("Tools & Equipment>Power Tool Accessories>Flap Discs", "Flap Discs", "31191501",
     ["flap disc", "flap wheel"],
     ["Diameter", "Arbor Size", "Grit", "Abrasive Material", "Maximum Speed",
      "Package Quantity"]),
    ("Tools & Equipment>Power Tool Accessories>Drill Bits", "Drill Bits", "27112700",
     ["drill bit", "twist bit", "hole saw", "step bit", "auger bit", "masonry bit"],
     ["Diameter", "Overall Length", "Shank Type", "Material", "Coating",
      "Package Quantity"]),
    ("Tools & Equipment>Power Tool Accessories>Saw Blades", "Saw Blades", "27112701",
     ["saw blade", "circular saw blade", "reciprocating blade", "band saw blade",
      "jig saw blade", "sawzall blade"],
     ["Diameter", "Tooth Count", "Arbor Size", "Material", "Application",
      "Package Quantity"]),
    # ---- pipe, tube & hose fittings (full-depth category) -----------------------------
    ("Plumbing>Pipe Fittings>Couplings", "Couplings", "40141600",
     ["coupling", "cplg", "coupler", "slip coupling", "repair coupling"],
     ["Nominal Size", "End Connection", "Material Construction", "Pressure Rating",
      "Schedule", "Finish", "Standard"]),
    ("Plumbing>Pipe Fittings>Elbows", "Elbows", "40141601",
     ["elbow", "ell", "90 elbow", "45 elbow", "street elbow"],
     ["Nominal Size", "Angle", "End Connection", "Material Construction",
      "Pressure Rating", "Schedule", "Finish"]),
    ("Plumbing>Pipe Fittings>Tees", "Tees", "40141602",
     ["tee", "reducing tee", "sanitary tee"],
     ["Nominal Size", "End Connection", "Material Construction", "Pressure Rating",
      "Schedule", "Finish"]),
    ("Plumbing>Pipe Fittings>Nipples", "Nipples", "40141603",
     ["nipple", "pipe nipple", "close nipple"],
     ["Nominal Size", "Overall Length", "End Connection", "Material Construction",
      "Pressure Rating", "Schedule"]),
    ("Plumbing>Pipe Fittings>Adapters", "Adapters", "40141604",
     ["adapter", "adaptor", "bushing", "reducer", "transition fitting"],
     ["Nominal Size", "Outlet Size", "End Connection", "Material Construction",
      "Pressure Rating"]),
    ("Plumbing>Pipe Fittings>Unions", "Unions", "40141605",
     ["union", "dielectric union", "ground joint union"],
     ["Nominal Size", "End Connection", "Material Construction", "Pressure Rating",
      "Seat Material"]),
    ("Plumbing>Valves>Ball Valves", "Ball Valves", "40141607",
     ["ball valve", "bv", "full port valve"],
     ["Nominal Size", "End Connection", "Body Material", "Pressure Rating",
      "Port Type", "Handle Type", "Standard"]),
    ("Plumbing>Valves>Gate Valves", "Gate Valves", "40141608",
     ["gate valve", "gv"],
     ["Nominal Size", "End Connection", "Body Material", "Pressure Rating", "Stem Type"]),
    ("Plumbing>Valves>Check Valves", "Check Valves", "40141609",
     ["check valve", "swing check", "spring check"],
     ["Nominal Size", "End Connection", "Body Material", "Pressure Rating", "Type"]),
    # ---- faucets (full-depth category) -------------------------------------------------
    ("Plumbing>Faucets>Kitchen Sink Faucets", "Kitchen Sink Faucets", "40141726",
     ["kitchen faucet", "kitchen sink faucet", "pull-down faucet", "pull down faucet",
      "pullout faucet", "bar faucet"],
     ["Series", "Number of Handles", "Mounting Type", "Number of Holes", "Spout Reach",
      "Spout Height", "Flow Rate", "Finish", "Valve Type", "ADA Compliant"]),
    ("Plumbing>Faucets>Bath Sink Faucets", "Bath Sink Faucets", "40141727",
     ["bath faucet", "lavatory faucet", "bathroom faucet", "widespread faucet",
      "centerset faucet", "vessel faucet"],
     ["Series", "Number of Handles", "Mounting Type", "Center Distance", "Spout Reach",
      "Spout Height", "Flow Rate", "Finish", "Drain Type", "ADA Compliant"]),
    ("Plumbing>Faucets>Commercial Faucets", "Commercial Faucets", "40141728",
     ["commercial faucet", "service sink faucet", "pre-rinse faucet", "metering faucet"],
     ["Series", "Mounting Type", "Spout Reach", "Flow Rate", "Finish", "Handle Type",
      "Standard"]),
    # ---- appliances --------------------------------------------------------------------
    ("Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
     "Built-In Dishwashers", "52141501",
     ["dishwasher", "built-in dishwasher", "built in dishwasher", "dw"],
     ["Series", "Mounting", "Wash Cycles", "Voltage", "Amperage", "Width",
      "Depth With Door Open", "Sound Level", "Finish", "Energy Star"]),
    ("Appliances & Consumer Electronics>Kitchen Appliances>Ranges", "Ranges", "52141502",
     ["range", "cooktop", "wall oven", "slide-in range", "freestanding range"],
     ["Series", "Fuel Type", "Number of Burners", "Oven Capacity", "Voltage", "Width",
      "Finish", "Convection"]),
    ("Appliances & Consumer Electronics>Kitchen Appliances>Refrigerators",
     "Refrigerators", "52141503",
     ["refrigerator", "fridge", "french door refrigerator", "side by side refrigerator"],
     ["Series", "Configuration", "Total Capacity", "Width", "Height", "Voltage",
      "Finish", "Energy Star"]),
    ("Appliances & Consumer Electronics>Laundry Appliances>Washers", "Washers", "52141504",
     ["washer", "washing machine", "front load washer", "top load washer"],
     ["Series", "Configuration", "Capacity", "Voltage", "Width", "Finish", "Energy Star"]),
    # ---- water heating & HVAC ------------------------------------------------------------
    ("Plumbing>Water Heaters>Electric Water Heaters", "Electric Water Heaters", "40101902",
     ["electric water heater", "elec water heater", "electric wh"],
     ["Series", "Tank Capacity", "Voltage", "Wattage", "Recovery Rate", "First Hour Rating",
      "Warranty Term"]),
    ("Plumbing>Water Heaters>Gas Water Heaters", "Gas Water Heaters", "40101903",
     ["gas water heater", "natural gas water heater", "lp water heater", "gas wh"],
     ["Series", "Tank Capacity", "Input Rating", "Recovery Rate", "First Hour Rating",
      "Vent Type", "Warranty Term"]),
    ("HVAC>Air Conditioning>Condensing Units", "Condensing Units", "40101701",
     ["condensing unit", "condenser", "ac condenser", "outdoor unit"],
     ["Series", "Cooling Capacity", "SEER Rating", "Voltage", "Phase", "Refrigerant",
      "Sound Level"]),
    ("HVAC>Air Distribution>Grilles & Registers", "Grilles & Registers", "40101601",
     ["grille", "register", "diffuser", "return air grille"],
     ["Nominal Size", "Material", "Finish", "Blade Type", "Mounting", "Damper"]),
    ("HVAC>Controls>Thermostats", "Thermostats", "41112200",
     ["thermostat", "tstat", "t-stat", "programmable thermostat"],
     ["Series", "Stages Heating", "Stages Cooling", "Voltage", "Communication",
      "Display Type", "Programmable"]),
    ("HVAC>Filtration>Air Filters", "Air Filters", "40161500",
     ["air filter", "furnace filter", "pleated filter", "media filter"],
     ["Nominal Size", "Actual Size", "MERV Rating", "Media Type", "Depth",
      "Package Quantity"]),
    # ---- electrical ----------------------------------------------------------------------
    ("Electrical>Circuit Protection>Circuit Breakers", "Circuit Breakers", "39121004",
     ["circuit breaker", "breaker", "cb", "molded case breaker"],
     ["Amperage", "Voltage", "Number of Poles", "Interrupting Rating", "Mounting",
      "Trip Type", "Frame Size"]),
    ("Electrical>Circuit Protection>Fuses", "Fuses", "39121005",
     ["fuse", "cartridge fuse", "time delay fuse", "class j fuse"],
     ["Amperage", "Voltage", "Class", "Interrupting Rating", "Speed", "Package Quantity"]),
    ("Electrical>Wiring Devices>Receptacles", "Receptacles", "39121400",
     ["receptacle", "outlet", "gfci", "duplex receptacle", "usb receptacle"],
     ["Amperage", "Voltage", "NEMA Configuration", "Colour", "Grade", "Mounting",
      "Package Quantity"]),
    ("Electrical>Wiring Devices>Switches", "Switches", "39121401",
     ["switch", "toggle switch", "dimmer", "occupancy sensor switch"],
     ["Amperage", "Voltage", "Number of Poles", "Colour", "Grade", "Package Quantity"]),
    ("Electrical>Boxes & Enclosures>Junction Boxes", "Junction Boxes", "39131700",
     ["junction box", "j-box", "outlet box", "device box", "pull box"],
     ["Nominal Size", "Material", "Cubic Capacity", "NEMA Rating", "Mounting",
      "Number of Gangs"]),
    ("Electrical>Conduit & Fittings>Conduit Fittings", "Conduit Fittings", "39131701",
     ["conduit fitting", "connector", "coupling emt", "compression connector",
      "set screw connector"],
     ["Trade Size", "Material", "Type", "Finish", "Standard", "Package Quantity"]),
    ("Electrical>Wire & Cable>Building Wire", "Building Wire", "26121600",
     ["building wire", "thhn", "thwn", "romex", "nm-b cable", "mc cable"],
     ["Wire Size", "Conductor Count", "Insulation", "Voltage Rating", "Conductor Material",
      "Length"]),
    ("Electrical>Lighting>LED Lamps", "LED Lamps", "39101600",
     ["led lamp", "led bulb", "a19 lamp", "led retrofit"],
     ["Wattage", "Luminous Flux", "Colour Temperature", "CRI", "Base Type", "Shape",
      "Dimmable", "Package Quantity"]),
    # ---- motion & power transmission ------------------------------------------------------
    ("Industrial>Bearings>Ball Bearings", "Ball Bearings", "31171500",
     ["ball bearing", "deep groove bearing", "pillow block", "flange bearing"],
     ["Bore Diameter", "Outside Diameter", "Width", "Bore Type", "Seal Type",
      "Dynamic Load Rating"]),
    ("Industrial>Motors>AC Motors", "AC Motors", "26101100",
     ["ac motor", "motor", "electric motor", "induction motor"],
     ["Power Rating", "Voltage", "Phase", "Rotational Speed", "Frame Size",
      "Enclosure", "Mounting", "Efficiency"]),
    ("Industrial>Power Transmission>V-Belts", "V-Belts", "31162000",
     ["v-belt", "v belt", "belt", "cogged belt", "banded belt"],
     ["Belt Section", "Outside Length", "Top Width", "Construction", "Package Quantity"]),
    # ---- building products -----------------------------------------------------------------
    ("Building Products>Decking>Composite Decking Boards", "Composite Decking Boards",
     "30103600",
     ["decking board", "deck board", "composite decking", "capped composite board",
      "pvc decking", "grooved deck board"],
     ["Collection", "Colour", "Profile", "Nominal Size", "Length", "Edge Type",
      "Surface Texture", "Warranty Term"]),
    ("Building Products>Decking>Deck Railing", "Deck Railing", "30103601",
     ["railing", "deck railing", "rail kit", "baluster"],
     ["Collection", "Colour", "Height", "Length", "Infill Type", "Material"]),
    ("Building Products>Fasteners>Screws", "Screws", "31161500",
     ["screw", "deck screw", "wood screw", "self drilling screw", "tek screw",
      "machine screw"],
     ["Nominal Size", "Overall Length", "Head Type", "Drive Type", "Point Type",
      "Material", "Finish", "Package Quantity"]),
    ("Building Products>Fasteners>Anchors", "Anchors", "31161501",
     ["anchor", "wedge anchor", "sleeve anchor", "drop-in anchor", "toggle bolt"],
     ["Nominal Size", "Overall Length", "Material", "Finish", "Base Material",
      "Package Quantity"]),
    # ---- safety --------------------------------------------------------------------------
    ("Safety>Personal Protective Equipment>Safety Glasses", "Safety Glasses", "46181802",
     ["safety glasses", "safety spectacles", "eye protection", "goggles"],
     ["Lens Colour", "Lens Coating", "Frame Colour", "Standard", "Package Quantity"]),
    ("Safety>Personal Protective Equipment>Work Gloves", "Work Gloves", "46181504",
     ["work glove", "gloves", "cut resistant glove", "nitrile glove"],
     ["Size", "Cut Level", "Coating", "Liner Material", "Cuff Style",
      "Package Quantity"]),
    ("Safety>Personal Protective Equipment>Hearing Protection", "Hearing Protection",
     "46181804",
     ["ear muff", "earmuff", "ear plug", "earplug", "hearing protector"],
     ["Noise Reduction Rating", "Style", "Colour", "Package Quantity"]),
    # ---- chemicals -------------------------------------------------------------------------
    ("Chemicals & Lubricants>Adhesives & Sealants>Thread Sealants", "Thread Sealants",
     "31201500",
     ["thread sealant", "pipe dope", "thread locker", "threadlocker", "pipe sealant"],
     ["Colour", "Strength", "Container Size", "Temperature Range", "Cure Time",
      "Standard"]),
    ("Chemicals & Lubricants>Lubricants>Penetrating Oils", "Penetrating Oils", "15121500",
     ["penetrating oil", "lubricant", "spray lubricant", "rust penetrant"],
     ["Container Size", "Container Type", "Temperature Range", "Package Quantity"]),
    ("Chemicals & Lubricants>Coatings>Spray Paint", "Spray Paint", "31211500",
     ["spray paint", "aerosol paint", "enamel spray", "primer spray"],
     ["Colour", "Sheen", "Container Size", "Coverage", "Base Type", "Package Quantity"]),
]

# Trade shorthand, added as a second pass so the leaf table above stays readable.
#
# A distributor writes `Charlotte PVC 90 ELB 1/2 Sch80 S x S`, not "elbow"; `Leeson Mtr`,
# not "motor"; `Lav Fct`, not "lavatory faucet". None of this is guesswork - each entry
# is a trade abbreviation with one meaning inside its category. Keywords are matched
# longest-first on word boundaries, so the two-letter forms only fire when nothing more
# specific does.
EXTRA_KEYWORDS: dict[str, list[str]] = {
    "Cut-Off Wheels": ["cut off disc", "cutoff disc", "cut-off disc"],
    "Grinding Wheels": ["grind whl", "grinding whl"],
    "Sanding Discs": ["fibre disc", "fiber disc", "stikit", "psa disc",
                      "sand disc", "abrasive sheet"],
    "Flap Discs": ["flap wheel", "blending disc"],
    "Drill Bits": ["drl bit", "hole dozer", "jobber", "masonry bit"],
    "Saw Blades": ["recip blade", "circ saw blade", "saw bld", "band blade",
                   "lazer recip"],
    "Couplings": ["cplg", "coupler"],
    "Elbows": ["elb", "street ell"],
    "Tees": ["reducing tee"],
    "Nipples": ["nip"],
    "Adapters": ["adptr", "adaptor", "reducer bushing", "propex adptr"],
    "Unions": ["dielectric union"],
    "Ball Valves": ["bv"],
    "Gate Valves": ["gv"],
    "Check Valves": ["cv", "swing cv", "spring cv"],
    "Kitchen Sink Faucets": ["kit fct", "kitchen fct", "pulldown", "pullout"],
    "Bath Sink Faucets": ["lav fct", "lavatory fct", "bath fct"],
    "Commercial Faucets": ["svc sink fct", "service sink fct", "pre-rinse unit",
                           "prerinse", "metering fct", "fct svc"],
    "Built-In Dishwashers": ["dw", "dishwshr"],
    "Ranges": ["elec range", "gas range", "cooktop"],
    "Refrigerators": ["refrig", "french door refrig", "fridge"],
    "Washers": ["fl washer", "tl washer", "washing mach"],
    "Electric Water Heaters": ["elec wh", "electric wh", "elec water htr"],
    "Gas Water Heaters": ["gas wh", "gas water htr"],
    "Condensing Units": ["cond unit", "condenser", "outdoor unit"],
    "Grilles & Registers": ["return grille", "supply register", "diffuser"],
    "Thermostats": ["tstat", "prog tstat", "t-stat"],
    "Air Filters": ["pleated air filter", "pleated filter", "furnace fltr"],
    "Circuit Breakers": ["cb", "plug-on breaker", "qo cb", "br cb"],
    "Fuses": ["lpj fuse", "class j fuse", "td fuse"],
    "Receptacles": ["recep", "dup recep", "gfci recep", "duplex recep"],
    "Switches": ["toggle sw", "sw", "dimmer sw", "occ sensor"],
    "Junction Boxes": ["octagon box", "octagon bx", "device bx", "steel box",
                       "j-box", "jct box"],
    "Conduit Fittings": ["emt conn", "emt connector", "set screw conn",
                         "compression conn"],
    "Building Wire": ["thhn", "thwn", "nm-b", "bldg wire", "romex"],
    "LED Lamps": ["led lamp", "a19 lamp", "led bulb"],
    "Ball Bearings": ["ball brg", "brg", "pillow blk", "flange brg"],
    "AC Motors": ["mtr", "elec mtr", "tefc mtr", "induction mtr"],
    "V-Belts": ["v-belt", "v belt", "cogged belt"],
    "Composite Decking Boards": ["deck bd", "deck board", "decking bd",
                                 "composite bd"],
    "Deck Railing": ["rail kit", "railing kit", "baluster"],
    "Screws": ["deck screw", "wood screw", "tek screw", "self drilling screw"],
    "Anchors": ["strong-bolt", "kb-tz", "wedge anchor", "sleeve anchor"],
    "Safety Glasses": ["sfty glasses", "safety spec", "eye pro"],
    "Work Gloves": ["glove", "hyflex", "cut resistant glv", "work glv"],
    "Hearing Protection": ["ear muff", "earmuff", "hear prot", "ear plug"],
    "Thread Sealants": ["threadlocker", "thread locker", "thrd slnt", "pipe dope",
                        "pipe sealant"],
    "Penetrating Oils": ["penetrant", "pen oil", "spray lube"],
    "Spray Paint": ["spray enamel", "spry pnt", "aerosol enamel", "spray paint"],
}

# Equivalence classes over attribute labels.
#
# "The output is constrained, not creative": attribute values must come from the
# vocabulary, and so must the LABELS. An extractor that reads `BRS` and files it under
# "Material Construction" has done the right work, but if the leaf's own sequence calls
# that attribute "Body Material" then the record has an attribute the category cannot
# filter on. Alignment moves the extracted label onto the category's word for the same
# thing - and only ever within a class, so nothing is renamed into a different meaning.
LABEL_SYNONYMS: list[list[str]] = [
    ["Material Construction", "Material", "Body Material", "Construction",
     "Abrasive Material", "Liner Material", "Conductor Material", "Blade Material",
     "Tooth Material", "Wire Type"],
    ["Colour", "Color", "Lens Colour", "Frame Colour", "Finish Colour"],
    ["Finish", "Surface Finish", "Plating"],
    ["Nominal Size", "Size", "Trade Size", "Actual Size", "Nominal Dimension"],
    ["Overall Length", "Length", "Blade Length"],
    ["Diameter", "Outside Diameter", "Wheel Diameter", "Disc Diameter"],
    ["Bore Diameter", "Bore", "Inside Diameter", "Bore Size"],
    ["Thickness", "Actual Thickness", "Wheel Thickness", "Depth of Cut"],
    ["Width", "Actual Width", "Blade Width"],
    ["Package Quantity", "Pack Quantity", "Quantity", "Package Qty"],
    ["Pressure Rating", "Working Pressure", "Maximum Pressure"],
    ["Power Rating", "Horsepower", "Motor Power"],
    ["Rotational Speed", "Maximum Speed", "Speed", "No Load Speed"],
    ["Tank Capacity", "Capacity", "Total Capacity", "Oven Capacity"],
    ["Container Size", "Volume", "Net Contents"],
    ["Voltage", "Voltage Rating", "Rated Voltage"],
    ["Amperage", "Current Rating", "Rated Current"],
    ["Wattage", "Power Consumption"],
    ["Grit", "Grade", "Grit Size"],
    ["Series", "Collection", "Product Family", "Product Line"],
    ["Standard", "Certifications", "Compliance", "Listing"],
    ["End Connection", "Connection Type", "End Type", "Connection"],
    ["Sound Level", "Noise Level", "Sound Rating"],
    ["Warranty Term", "Warranty", "Warranty Period"],
    ["Mounting Type", "Mounting", "Installation Type"],
    ["Attachment Type", "Attachment Method", "Backing Attachment"],
    ["Wire Size", "Gauge", "Conductor Size", "AWG"],
    ["Tooth Count", "Teeth", "Number of Teeth"],
    ["Thread Pitch", "Threads Per Inch", "Pitch"],
    ["Number of Handles", "Handle Count", "Handles"],
    ["Spout Reach", "Reach", "Spout Length"],
    ["Flow Rate", "GPM", "Rated Flow"],
    ["Cooling Capacity", "Tonnage", "Nominal Capacity"],
    ["MERV Rating", "MERV", "Filter Efficiency"],
    ["Profile", "Edge Type", "Edge Profile"],
    ["Surface Texture", "Texture", "Grain Pattern"],
    ["Backing", "Backing Material", "Substrate"],
]

LABEL_CLASS: dict[str, int] = {}
for _i, _cls in enumerate(LABEL_SYNONYMS):
    for _lbl in _cls:
        LABEL_CLASS.setdefault(_lbl.lower(), _i)


def align_label(label: str, sequence: list[str]) -> str:
    """Move an extracted label onto the leaf's own word for the same attribute."""
    if not label or not sequence:
        return label
    if label in sequence:
        return label
    cls = LABEL_CLASS.get(label.lower())
    if cls is None:
        return label
    for candidate in sequence:
        if LABEL_CLASS.get(candidate.lower()) == cls:
            return candidate
    return label


# One leaf the raw catalogue needs that the table above did not carry.
EXTRA_LEAVES: list[tuple[str, str, str, list[str], list[str]]] = [
    ("Tools & Equipment>Power Tool Accessories>Wire Brushes", "Wire Brushes",
     "27112802",
     ["wire cup brush", "cup brush", "wire brush", "knot wire", "wheel brush",
      "end brush"],
     ["Diameter", "Arbor Size", "Wire Type", "Wire Diameter", "Knot Type",
      "Maximum Speed", "Package Quantity"]),
]

# Words that mean "this is the item type" when they end a description.
ITEM_TYPE_STOPWORDS = {
    "display", "only", "new", "assy", "assembly", "kit", "w", "with", "for", "and",
    "in", "of", "the", "type", "series", "pack", "pk", "ea", "each", "box", "bx",
}

# Cross-category attribute labels that are safe to name deterministically once the
# induced axis pattern is recognised. Anything not in here is presented to a human.
AXIS_NAME_HINTS: list[tuple[str, str]] = [
    (r"^P\d{2,4}$", "Grit"),
    (r"^\d{2,4}\s*grit$", "Grit"),
    (r"^\d+(?:\.\d+)?\s*(?:in|mm|ft)$", "Nominal Size"),
    (r"^\d+/\d+\s*(?:in)?$", "Nominal Size"),
    (r"^\d+(?:\.\d+)?\s*V$", "Voltage"),
    (r"^\d+(?:\.\d+)?\s*A$", "Amperage"),
    (r"^\d+(?:\.\d+)?\s*W$", "Wattage"),
    (r"^\d+(?:\.\d+)?\s*hp$", "Power Rating"),
    (r"^\d+(?:\.\d+)?\s*gal$", "Tank Capacity"),
    (r"^\d+(?:\.\d+)?\s*gpm$", "Flow Rate"),
    (r"^\d+(?:\.\d+)?\s*rpm$", "Rotational Speed"),
    (r"^\d+(?:\.\d+)?\s*dBA$", "Sound Level"),
    (r"^\d+(?:\.\d+)?\s*ga$", "Gauge"),
    (r"^\d+\s*AWG$", "Wire Size"),
    (r"^MERV\s*\d+$", "MERV Rating"),
    (r"^\d+\s*pc$", "Package Quantity"),
    (r"^\d+\s*T$", "Tooth Count"),
    (r"^\d+\s*tpi$", "Thread Pitch"),
]

# Colour and finish lexicons let the co-occurrence engine name two very common groups
# without a human, which is why 48 induced attributes need only 46 names.
COLOUR_WORDS = {
    "black", "white", "grey", "gray", "brown", "brownstone", "coastline", "mahogany",
    "teak", "slate", "chestnut", "walnut", "cedar", "redwood", "sandstone", "graphite",
    "silver", "bronze", "chrome", "nickel", "brass", "copper", "gold", "red", "blue",
    "green", "yellow", "orange", "ivory", "almond", "clear", "amber", "smoke",
    "espresso", "driftwood", "pewter", "titanium", "gunmetal", "stainless",
}

FINISH_WORDS = {
    "polished", "brushed", "satin", "matte", "gloss", "semi-gloss", "flat", "oiled",
    "chrome", "nickel", "bronze", "brass", "stainless", "galvanized", "galvanised",
    "zinc", "black-oxide", "anodized", "anodised", "powder-coated", "painted",
    "unfinished", "mill", "plated", "epoxy",
}


def build_leaves() -> list[dict]:
    out = []
    for classpath, leaf, unspsc, keywords, attrs in LEAVES + EXTRA_LEAVES:
        parts = classpath.split(">")
        keywords = list(dict.fromkeys(keywords + EXTRA_KEYWORDS.get(leaf, [])))
        out.append({
            "classpath": classpath,
            "leaf_node": leaf,
            "unspsc": unspsc,
            "dept": parts[0],
            "class": parts[1] if len(parts) > 1 else "",
            "fine": parts[2] if len(parts) > 2 else "",
            "keywords": keywords,
            "attribute_sequence": attrs,
            "category_code": f"{parts[0][:3].upper()}-{leaf[:4].upper()}",
        })
    return out
