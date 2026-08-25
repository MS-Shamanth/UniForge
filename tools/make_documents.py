"""Build the cached manufacturer-document corpus in data/docs/.

WHAT THESE FILES ARE
--------------------
Reconstructed stand-ins for manufacturer product pages. The original project cached
real pages; those caches went with the project folder. Every document here carries
`"reconstructed": true` in index.json and the UI labels it as such, because a sourced
value is only ever worth what its source is worth.

To replace them with genuine caches:

    $env:UNIFORGE_ALLOW_FETCH = "1"
    python -m uniforge.cli source --fetch --discover

That path only ever requests domains that pass the sourcing gate, writes the same index
format, and clears the `reconstructed` flag as it goes.

WHY THEIR SHAPE MATTERS AND THEIR WORDING DOES NOT
--------------------------------------------------
Nothing in the extractor is tuned to these strings. What it relies on is structure that
real manufacturer pages share: the part number named in the body, a `Label: Value`
specification block, a bulleted feature list, a marketing paragraph, and links to spec
sheets and safety data sheets. Point it at a real cached page with those parts and it
behaves identically.

TWO FACTS ARE PLANTED ON PURPOSE
--------------------------------
Both exist to prove the layers check each other rather than merely run:

  * Milwaukee states Package Quantity = 25 pc where cross-row inference concluded 10.
    The document wins, and the disagreement is written into the evidence trail.
  * Milwaukee writes '5/8" DKO Arbor'. That is the only evidence which expands DKO,
    an abbreviation the pipeline otherwise refuses to guess.

    python tools/make_documents.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniforge import config as C  # noqa: E402

NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# --------------------------------------------------------------------------------------
# Profiles. One entry per product line we hold documents for.
#
#   parse    regex over Part_Desc; named groups become template variables
#   defaults fallbacks when the regex misses
#   specs    the Label: Value block. A line whose template needs a missing variable is
#            dropped rather than emitted with a hole in it.
# --------------------------------------------------------------------------------------
P: dict[str, dict] = {

    "milw-cutoff": dict(
        brand="Milwaukee", domain="milwaukeetool.com",
        url="https://www.milwaukeetool.com/Products/Accessories/Grinding-and-Cutting/{mpn}",
        parse=r'(?P<dia>[\d\-/]+)"x(?P<thk>[.\d]+)"x(?P<arb>[\d/]+)"',
        defaults=dict(dia="5", thk=".045", arb="7/8"),
        title='{dia} in. x {thk} in. x {arb} in. Metal Cut-Off Wheel, Type 1, 25 Pack',
        marketing=(
            "The MILWAUKEE Metal Cut-Off Wheel is engineered for fast, burr-free cuts "
            "in ferrous metal, stainless steel and threaded rod. Double fibreglass "
            "reinforcement resists side-load fracture, and a hardened aluminum oxide "
            "grain holds its edge through repeated passes so operators change wheels "
            "less often."),
        features=[
            "Fast, burr-free cutting in ferrous metals and stainless steel",
            "Double fibreglass reinforcement resists side-load fracture",
            "Aluminum oxide grain rated 36/40 balances cut rate against wheel life",
            "Type 1 flat profile for straight cutting",
            "Fits {arb} in. arbor angle grinders and cut-off tools",
            'Also offered with a 5/8" DKO Arbor for larger grinders',
            "Maximum operating speed matched to wheel diameter",
            "Burst tested to ANSI B7.1",
            "Built for high-cycle production and maintenance work",
            "Packaged 25 per box for shop use",
        ],
        specs=[
            ("Diameter", "{dia} in"), ("Thickness", "{thk} in"),
            ("Arbor Size", "{arb} in"), ("Grit", "36/40"),
            ("Abrasive Material", "Aluminum Oxide"), ("Wheel Type", "Type 1 Flat"),
            ("Maximum Speed", "13300 rpm"),
            ("Material Application", "Ferrous Metal, Stainless Steel, Threaded Rod"),
            ("Reinforcement", "Double Fibreglass"),
            ("Package Quantity", "25 pc"),
            ("Standard", "ANSI B7.1"), ("Country of Origin", "United States"),
            ("Warranty Term", "1 yr"),
        ],
        apps=["Cutting ferrous metal stock", "Cutting stainless steel",
              "Cutting threaded rod and rebar"],
        docs=[("Specification Sheet",
               "https://www.milwaukeetool.com/-/media/Products/{mpn}-spec.pdf"),
              ("Safety Data Sheet",
               "https://www.milwaukeetool.com/-/media/SDS/{mpn}-sds.pdf")],
    ),

    # Deliberately identical to milw-cutoff, including "Package Quantity: 25 pc".
    # The supplied rows in this line say 10 per pack; the manufacturer's own page says
    # the box holds 25. The document outranks the inference, and the disagreement is
    # recorded rather than smoothed over.
    "milw-cutoff-pk": dict(
        brand="Milwaukee", domain="milwaukeetool.com",
        url="https://www.milwaukeetool.com/Products/Accessories/Grinding-and-Cutting/{mpn}",
        parse=r'(?P<dia>[\d\-/]+)"x(?P<thk>[.\d]+)"x(?P<arb>[\d/]+)"',
        defaults=dict(dia="5", thk=".045", arb="7/8"),
        title='{dia} in. x {thk} in. x {arb} in. Metal Cut-Off Wheel, Type 1, 25 Pack',
        marketing=(
            "The MILWAUKEE Metal Cut-Off Wheel is engineered for fast, burr-free cuts "
            "in ferrous metal, stainless steel and threaded rod. Double fibreglass "
            "reinforcement resists side-load fracture, and a hardened aluminum oxide "
            "grain holds its edge through repeated passes."),
        features=[
            "Fast, burr-free cutting in ferrous metals and stainless steel",
            "Double fibreglass reinforcement resists side-load fracture",
            "Aluminum oxide grain rated 36/40",
            "Type 1 flat profile for straight cutting",
            "Fits {arb} in. arbor angle grinders and cut-off tools",
            'Also offered with a 5/8" DKO Arbor for larger grinders',
            "Burst tested to ANSI B7.1",
            "Shop box holds 25 wheels",
        ],
        specs=[
            ("Diameter", "{dia} in"), ("Thickness", "{thk} in"),
            ("Arbor Size", "{arb} in"), ("Grit", "36/40"),
            ("Abrasive Material", "Aluminum Oxide"), ("Wheel Type", "Type 1 Flat"),
            ("Maximum Speed", "13300 rpm"),
            ("Material Application", "Ferrous Metal, Stainless Steel, Threaded Rod"),
            ("Reinforcement", "Double Fibreglass"),
            ("Package Quantity", "25 pc"),
            ("Standard", "ANSI B7.1"), ("Country of Origin", "United States"),
            ("Warranty Term", "1 yr"),
        ],
        apps=["Cutting ferrous metal stock", "Cutting stainless steel"],
        docs=[("Specification Sheet",
               "https://www.milwaukeetool.com/-/media/Products/{mpn}-spec.pdf"),
              ("Safety Data Sheet",
               "https://www.milwaukeetool.com/-/media/SDS/{mpn}-sds.pdf")],
    ),

    "3m-stikit": dict(
        brand="3M", domain="3m.com",
        url="https://www.3m.com/3M/en_US/p/d/{slug}/",
        parse=r"\[(?P<grit>P\d+)\s*\]",
        defaults=dict(grit="P150"),
        title="3M Stikit Film Disc 775L, {grit}, 6 in x NH, Die 600Z, 50 per carton",
        marketing=(
            "3M Stikit Film Disc 775L pairs 3M Precision Shaped Grain with a durable "
            "3 mil polyester film backing for a consistent, uniform finish on primer, "
            "body filler and clear coat. The pressure-sensitive adhesive backing lets "
            "an operator change discs in seconds."),
        features=[
            "3M Precision Shaped Grain cuts faster and lasts longer than conventional grain",
            "3 mil polyester film backing resists tearing and edge curl",
            "Pressure-sensitive adhesive attachment for fast disc changes",
            "Uniform finish with minimal scratch variation",
            "Load-resistant coating extends useful life on soft fillers",
            "Compatible with 3M Stikit disc pads and random-orbital sanders",
            "Die 600Z, no centre hole",
            "Sold 50 discs per carton",
        ],
        specs=[
            ("Diameter", "6 in"), ("Grit", "{grit}"), ("Grade", "{grit}"),
            ("Abrasive Material", "Ceramic Aluminum Oxide"),
            ("Backing", "3 mil Polyester Film"),
            ("Attachment Type", "Stikit Pressure Sensitive Adhesive"),
            ("Series", "775L"), ("Product Family", "Cubitron II"),
            ("Die Cut", "600Z"), ("Centre Hole", "No Hole"),
            ("Package Quantity", "50 pc"), ("Country of Origin", "United States"),
        ],
        apps=["Primer sanding", "Body filler shaping", "Clear coat finishing"],
        docs=[("Technical Data Sheet",
               "https://multimedia.3m.com/mws/media/{slug}-tds.pdf"),
              ("Safety Data Sheet",
               "https://multimedia.3m.com/mws/media/{slug}-sds.pdf")],
    ),

    "3m-cubitron-fibre": dict(
        brand="3M", domain="3m.com",
        url="https://www.3m.com/3M/en_US/p/d/{slug}/",
        parse=r"Disc (?P<dia>[\d\-/]+)in (?P<grit>\d+)",
        defaults=dict(dia="4-1/2", grit="60"),
        title="3M Cubitron II Fibre Disc 982C, {grit}+, {dia} in x 7/8 in, 25 per carton",
        marketing=(
            "3M Cubitron II Fibre Disc 982C uses electrostatically oriented precision "
            "shaped ceramic grain that slices through metal rather than ploughing it, "
            "cutting cooler and lasting substantially longer than conventional ceramic "
            "discs on carbon steel and stainless."),
        features=[
            "Precision Shaped Grain slices through metal for a cooler cut",
            "Cuts faster with less operator pressure",
            "Heavy-duty fibre backing for aggressive stock removal",
            "Performs on carbon steel, stainless steel and aluminium",
            "Reduces total abrasive cost per part",
            "25 discs per carton",
        ],
        specs=[
            ("Diameter", "{dia} in"), ("Arbor Size", "7/8 in"), ("Grit", "{grit}+"),
            ("Abrasive Material", "Precision Shaped Ceramic Grain"),
            ("Backing", "Fibre"), ("Series", "982C"),
            ("Product Family", "Cubitron II"), ("Maximum Speed", "13300 rpm"),
            ("Package Quantity", "25 pc"), ("Country of Origin", "United States"),
        ],
        apps=["Weld removal", "Bevelling", "Heavy stock removal"],
        docs=[("Technical Data Sheet",
               "https://multimedia.3m.com/mws/media/{slug}-tds.pdf")],
    ),

    "norton-flap": dict(
        brand="Norton", domain="nortonabrasives.com",
        url="https://www.nortonabrasives.com/en-us/products/{slug}",
        parse=r"Disc (?P<dia>[\d\-/]+) x (?P<arb>[\d/]+) T29 (?P<grit>\d+)g",
        defaults=dict(dia="4-1/2", arb="7/8", grit="60"),
        title="Norton Blaze Flap Disc, Type 29, {dia} in x {arb} in, {grit} Grit",
        marketing=(
            "Norton Blaze flap discs pair Norton SG ceramic alumina grain with a rigid "
            "backing plate to hold an aggressive cut rate on stainless and high-alloy "
            "steel, where conventional zirconia discs glaze over."),
        features=[
            "Norton SG ceramic alumina grain sustains the cut rate",
            "Type 29 conical shape for blending at 15 to 35 degrees",
            "High-strength backing plate resists deflection",
            "Cooler cutting reduces heat discolouration on stainless",
            "Trimmable backing extends usable life",
        ],
        specs=[
            ("Diameter", "{dia} in"), ("Arbor Size", "{arb} in"),
            ("Grit", "{grit} grit"), ("Abrasive Material", "Ceramic Alumina"),
            ("Disc Type", "Type 29 Conical"), ("Maximum Speed", "13300 rpm"),
            ("Backing Material", "Fibreglass"), ("Package Quantity", "10 pc"),
        ],
        apps=["Weld blending", "Edge chamfering"],
        docs=[("Specification Sheet",
               "https://www.nortonabrasives.com/spec/{slug}.pdf")],
    ),

    "diablo-blade": dict(
        brand="Diablo", domain="diablotools.com",
        url="https://www.diablotools.com/products/{slug}",
        parse=r'(?P<dia>[\d\-/]+)" (?P<teeth>\d+)T',
        defaults=dict(dia="7-1/4", teeth="40"),
        title="Diablo {dia} in. x {teeth} Tooth Circular Saw Blade for Wood",
        marketing=(
            "The Diablo circular saw blade uses a TiCo hi-density carbide blend and a "
            "laser-cut, tensioned steel plate to hold a true line through framing "
            "lumber and sheet goods, with a Perma-Shield coating that shrugs off pitch "
            "build-up."),
        features=[
            "TiCo hi-density carbide teeth for extended edge life",
            "Laser-cut stabiliser vents cut noise and vibration",
            "Perma-Shield non-stick coating resists heat, gumming and corrosion",
            "Tensioned plate keeps the blade true at speed",
            "Thin kerf reduces load on the saw motor",
        ],
        specs=[
            ("Diameter", "{dia} in"), ("Tooth Count", "{teeth} T"),
            ("Arbor Size", "5/8 in"), ("Kerf", "0.071 in"),
            ("Maximum Speed", "8500 rpm"), ("Tooth Material", "TiCo Carbide"),
            ("Application", "Wood, Plywood, OSB"), ("Package Quantity", "1 ea"),
        ],
        apps=["Framing", "Ripping sheet goods"],
        docs=[("Specification Sheet", "https://www.diablotools.com/spec/{slug}.pdf")],
    ),

    "milw-holesaw": dict(
        brand="Milwaukee", domain="milwaukeetool.com",
        url="https://www.milwaukeetool.com/Products/Accessories/Hole-Dozer/{mpn}",
        parse=r"Saw (?P<dia>[\d\-/]+)in",
        defaults=dict(dia="1"),
        title="MILWAUKEE HOLE DOZER Bi-Metal Hole Saw, {dia} in.",
        marketing=(
            "HOLE DOZER hole saws carry a thick, rigid backing plate and a "
            "variable-pitch bi-metal tooth pattern that clears chips fast in wood, "
            "metal and plastic without binding."),
        features=[
            "Bi-metal construction for long life in metal",
            "Rip guard teeth resist tooth strippage",
            "Thick backing plate reduces flex",
            "Two plug ejection slots make slug removal quick",
            "Colour-coded size marking for fast identification",
        ],
        specs=[
            ("Diameter", "{dia} in"), ("Cutting Depth", "1-5/8 in"),
            ("Material", "Bi-Metal"), ("Shank Type", "Quick Change Arbor"),
            ("Application", "Wood, Metal, Plastic"), ("Package Quantity", "1 ea"),
            ("Country of Origin", "United States"),
        ],
        apps=["Boring for conduit", "Boring for plumbing penetrations"],
        docs=[("Specification Sheet",
               "https://www.milwaukeetool.com/-/media/{mpn}-spec.pdf")],
    ),

    "nibco-brs-cplg": dict(
        brand="NIBCO", domain="nibco.com",
        url="https://www.nibco.com/products/{slug}",
        parse=r"^(?P<sz>[\d\-/]+) CPLG BRS (?P<psi>\d+)#",
        defaults=dict(sz="1/2", psi="150"),
        title="NIBCO Bronze Coupling, {sz} in, Solder x Solder, {psi} psi",
        marketing=(
            "A cast bronze coupling for potable water, hydronic heating and "
            "low-pressure steam service, machined to ASME B16.18 socket dimensions so "
            "it seats squarely on Type K, L and M copper tube."),
        features=[
            "Cast bronze body for corrosion resistance in potable water",
            "Solder x solder socket ends to ASME B16.18",
            "Lead-free composition compliant with NSF/ANSI 61 and 372",
            "Suitable for hydronic heating and low-pressure steam",
            "Full socket depth for a reliable capillary joint",
        ],
        specs=[
            ("Nominal Size", "{sz} in"), ("End Connection", "Solder x Solder"),
            ("Material Construction", "Cast Bronze"),
            ("Pressure Rating", "{psi} psi"), ("Maximum Temperature", "250 deg F"),
            ("Standard", "ASME B16.18, NSF/ANSI 61"), ("Finish", "Mill"),
            ("Lead Free", "Yes"), ("Package Quantity", "1 ea"),
        ],
        apps=["Potable water distribution", "Hydronic heating"],
        docs=[("Specification Sheet", "https://www.nibco.com/spec/{slug}.pdf")],
    ),

    "charlotte-pvc-elb": dict(
        brand="Charlotte Pipe", domain="charlottepipe.com",
        url="https://www.charlottepipe.com/products/{slug}",
        parse=r"(?P<ang>\d+) ELB (?P<sz>[\d\-/]+) Sch(?P<sch>\d+)",
        defaults=dict(ang="90", sz="1", sch="40"),
        title="Charlotte Pipe PVC Schedule {sch} {ang} Degree Elbow, {sz} in, Socket",
        marketing=(
            "Rigid PVC Schedule {sch} pressure fitting for cold-water distribution, "
            "irrigation and industrial process lines, moulded to ASTM D2466 socket "
            "dimensions."),
        features=[
            "Schedule {sch} PVC for pressure service",
            "Socket ends to ASTM D2466",
            "NSF-61 listed for potable cold water",
            "Chemical resistance suited to industrial process lines",
            "Moulded in the United States",
        ],
        specs=[
            ("Nominal Size", "{sz} in"), ("Angle", "{ang} deg"),
            ("End Connection", "Socket x Socket"),
            ("Material Construction", "PVC"), ("Schedule", "Schedule {sch}"),
            ("Pressure Rating", "150 psi"), ("Maximum Temperature", "140 deg F"),
            ("Standard", "ASTM D2466, NSF 61"),
            ("Country of Origin", "United States"),
        ],
        apps=["Cold water distribution", "Irrigation"],
        docs=[("Specification Sheet",
               "https://www.charlottepipe.com/spec/{slug}.pdf")],
    ),

    "apollo-bv": dict(
        brand="Apollo", domain="apollovalves.com",
        url="https://www.apollovalves.com/products/{slug}",
        parse=r"BV (?P<sz>[\d\-/]+) FP (?P<psi>\d+)#",
        defaults=dict(sz="1/2", psi="600"),
        title="Apollo Bronze Ball Valve, {sz} in, Full Port, {psi} psi WOG, Lever Handle",
        marketing=(
            "A two-piece bronze ball valve with a full-port chrome-plated brass ball "
            "and reinforced PTFE seats, rated for water, oil and gas service, with a "
            "blowout-proof stem and a packing gland that stays serviceable in place."),
        features=[
            "Full port for minimal pressure drop",
            "Chrome-plated brass ball and blowout-proof stem",
            "Reinforced PTFE seats and thrust washer",
            "Adjustable packing gland serviceable in place",
            "Vinyl-coated lever handle",
            "Lead-free bronze body",
        ],
        specs=[
            ("Nominal Size", "{sz} in"), ("End Connection", "FNPT x FNPT"),
            ("Body Material", "Bronze"), ("Pressure Rating", "{psi} psi"),
            ("Port Type", "Full Port"), ("Handle Type", "Lever"),
            ("Ball Material", "Chrome Plated Brass"),
            ("Seat Material", "Reinforced PTFE"),
            ("Maximum Temperature", "406 deg F"),
            ("Standard", "MSS SP-110, NSF/ANSI 61"), ("Package Quantity", "1 ea"),
        ],
        apps=["Water shutoff", "Compressed air isolation"],
        docs=[("Specification Sheet",
               "https://www.apollovalves.com/spec/{slug}.pdf")],
    ),

    "moen-kitchen": dict(
        brand="Moen", domain="moen.com",
        url="https://www.moen.com/products/{slug}",
        parse=r"Moen (?P<series>\S+) Kit Fct Pulldown 1H (?P<fin>\S+)",
        defaults=dict(series="Arbor", fin="SRS"),
        title="Moen {series} One-Handle Pulldown Kitchen Faucet, {finish}, 1.5 gpm",
        marketing=(
            "The Moen {series} kitchen faucet pairs a high-arc spout with a Reflex "
            "pulldown wand that retracts smoothly and docks securely, and a Duralock "
            "quick-connect system that seats the supply lines without tools."),
        features=[
            "Reflex system for smooth operation and secure docking",
            "Power Clean spray technology increases spray force",
            "Duralock quick-connect installation",
            "1255 Duralast cartridge for drip-free performance",
            "Single-handle lever for one-hand temperature control",
            "Escutcheon included for one or three hole installation",
            "Limited lifetime warranty on finish and function",
        ],
        specs=[
            ("Series", "{series} Series"), ("Number of Handles", "1"),
            ("Mounting Type", "Deck Mount"), ("Number of Holes", "1 or 3"),
            ("Spout Reach", "9-1/4 in"), ("Spout Height", "15-1/2 in"),
            ("Flow Rate", "1.5 gpm"), ("Finish", "{finish}"),
            ("Valve Type", "1255 Duralast Cartridge"), ("ADA Compliant", "Yes"),
            ("Standard", "ASME A112.18.1, NSF/ANSI 61"),
            ("Warranty Term", "Limited Lifetime"),
        ],
        apps=["Residential kitchen sink"],
        docs=[("Installation Guide", "https://www.moen.com/install/{slug}.pdf"),
              ("Specification Sheet", "https://www.moen.com/spec/{slug}.pdf")],
    ),

    "kohler-kitchen": dict(
        brand="KOHLER", domain="kohler.com",
        url="https://www.kohler.com/en/products/{slug}",
        parse=r"KOHLER (?P<series>\S+) Kit Fct 1H Pullout (?P<fin>\S+)",
        defaults=dict(series="Simplice", fin="VS"),
        title="KOHLER {series} Single-Handle Pull-Down Kitchen Faucet, {finish}",
        marketing=(
            "KOHLER {series} combines a three-function pull-down sprayhead with a "
            "high-arch swing spout and a MasterClean sprayface that resists mineral "
            "build-up, so the spray pattern stays even through years of hard-water "
            "service."),
        features=[
            "Three-function sprayhead: stream, sweep spray and pause",
            "MasterClean sprayface resists mineral build-up",
            "DockNetik magnetic docking secures the sprayhead",
            "ProMotion technology for a lightweight, quiet hose",
            "Ceramic disc valve exceeds industry longevity standards",
        ],
        specs=[
            ("Series", "{series}"), ("Number of Handles", "1"),
            ("Mounting Type", "Deck Mount"), ("Number of Holes", "1 or 3"),
            ("Spout Reach", "9-1/2 in"), ("Spout Height", "15-3/8 in"),
            ("Flow Rate", "1.5 gpm"), ("Finish", "{finish}"),
            ("Valve Type", "Ceramic Disc"), ("ADA Compliant", "Yes"),
            ("Standard", "ASME A112.18.1, NSF/ANSI 372"),
            ("Warranty Term", "Limited Lifetime"),
        ],
        apps=["Residential kitchen sink"],
        docs=[("Specification Sheet", "https://www.kohler.com/spec/{slug}.pdf")],
    ),

    "delta-bath": dict(
        brand="Delta", domain="deltafaucet.com",
        url="https://www.deltafaucet.com/products/{slug}",
        parse=r"Delta (?P<series>\S+) Lav Fct 2H (?P<ctr>\d+)in (?P<fin>\S+)",
        defaults=dict(series="Windemere", ctr="4", fin="SS"),
        title="Delta {series} Two-Handle {ctr} in. Centerset Bathroom Faucet, {finish}",
        marketing=(
            "The Delta {series} lavatory faucet uses a Diamond Seal valve with a "
            "diamond-coated ceramic disc, which keeps water off the internal waterway "
            "and holds a drip-free seal for the life of the fixture."),
        features=[
            "DIAMOND Seal Technology reduces leak points",
            "InnoFlex PEX waterways keep water inside the faucet",
            "WaterSense labelled at 1.2 gpm",
            "Two-handle operation with metal lever handles",
            "Pop-up drain assembly included",
        ],
        specs=[
            ("Series", "{series}"), ("Number of Handles", "2"),
            ("Mounting Type", "Deck Mount"), ("Center Distance", "{ctr} in"),
            ("Spout Reach", "4-3/4 in"), ("Spout Height", "5-1/2 in"),
            ("Flow Rate", "1.2 gpm"), ("Finish", "{finish}"),
            ("Drain Type", "Pop-Up Included"), ("ADA Compliant", "Yes"),
            ("Standard", "ASME A112.18.1, EPA WaterSense"),
            ("Warranty Term", "Limited Lifetime"),
        ],
        apps=["Residential bathroom lavatory"],
        docs=[("Specification Sheet", "https://www.deltafaucet.com/spec/{slug}.pdf")],
    ),

    "azek-deck": dict(
        brand="AZEK", domain="azekexteriors.com",
        url="https://www.azekexteriors.com/products/decking/{slug}",
        parse=(r"AZEK (?P<coll>\S+) Deck Bd (?P<colour>.+?) "
               r"(?P<prof>Grooved|Square) (?P<length>\d+)ft"),
        defaults=dict(coll="Harvest", colour="Brownstone", prof="Grooved", length="16"),
        title=("AZEK {coll} Collection Decking, {colour}, {prof} Edge, "
               "1 in x 5-1/2 in x {length} ft"),
        marketing=(
            "AZEK {coll} Collection decking is a capped PVC board with no wood flour "
            "in the core, so it will not rot, cup or absorb moisture. The Alloy Armour "
            "surface in {colour} resists scratches, stains and fading, and stays "
            "measurably cooler underfoot than capped composite alternatives."),
        features=[
            "100 percent capped PVC construction with no wood flour",
            "Will not rot, cup, splinter or absorb moisture",
            "Alloy Armour Technology resists scratches, stains and mould",
            "Stays cooler underfoot than capped composite decking",
            "{prof} edge profile for hidden or face fastening",
            "Reversible board with two distinct wood-grain patterns",
            "Made with recycled material",
            "50 year limited product warranty and 50 year limited fade and stain warranty",
        ],
        specs=[
            ("Collection", "{coll} Collection"), ("Colour", "{colour}"),
            ("Profile", "{prof} Edge"), ("Nominal Size", "1 in x 5-1/2 in"),
            ("Actual Thickness", "0.94 in"), ("Actual Width", "5.5 in"),
            ("Length", "{length} ft"), ("Edge Type", "{prof}"),
            ("Surface Texture", "Wood Grain"),
            ("Material Construction", "Capped Cellular PVC"),
            ("Warranty Term", "50 yr"), ("Country of Origin", "United States"),
        ],
        apps=["Residential decking", "Rooftop deck", "Poolside decking"],
        docs=[("Specification Sheet",
               "https://www.azekexteriors.com/spec/{slug}.pdf"),
              ("Installation Guide",
               "https://www.azekexteriors.com/install/{slug}.pdf")],
    ),

    "trex-deck": dict(
        brand="Trex", domain="trex.com",
        url="https://www.trex.com/products/decking/{slug}",
        parse=r"Trex (?P<coll>\S+) Deck Board (?P<colour>.+?) (?P<length>\d+)ft",
        defaults=dict(coll="Enhance", colour="Beach Dune", length="16"),
        title=("Trex {coll} Composite Decking, {colour}, Grooved Edge, "
               "1 in x 5-1/2 in x {length} ft"),
        marketing=(
            "Trex {coll} decking wraps a wood-and-polyethylene core in a protective "
            "shell, giving {colour} boards a surface that resists fading, staining, "
            "scratching and mould without sealing, staining or painting."),
        features=[
            "Shell-protected composite resists fade, stain, scratch and mould",
            "No sealing, staining or painting required",
            "Made from 95 percent recycled material",
            "Grooved edge for hidden fastening",
            "25 year limited residential warranty",
        ],
        specs=[
            ("Collection", "{coll}"), ("Colour", "{colour}"),
            ("Profile", "Grooved Edge"), ("Nominal Size", "1 in x 5-1/2 in"),
            ("Length", "{length} ft"),
            ("Material Construction", "Wood-Polymer Composite"),
            ("Surface Texture", "Wood Grain"), ("Warranty Term", "25 yr"),
        ],
        apps=["Residential decking"],
        docs=[("Specification Sheet", "https://www.trex.com/spec/{slug}.pdf")],
    ),

    "rheem-elec-wh": dict(
        brand="Rheem", domain="rheem.com",
        url="https://www.rheem.com/products/residential/{slug}",
        parse=r"(?P<gal>\d+)gal (?P<volt>\d+)V (?P<watt>\d+)W",
        defaults=dict(gal="50", volt="240", watt="5500"),
        title=("Rheem Performance {gal} Gallon Electric Water Heater, {volt} V, "
               "{watt} W, 6 Year Warranty"),
        marketing=(
            "A {gal} gallon residential electric water heater with two {watt} watt "
            "copper immersion elements, a factory-installed temperature and pressure "
            "relief valve, and a premium-grade anode rod for extended tank life in "
            "aggressive water."),
        features=[
            "Two copper immersion heating elements for fast recovery",
            "Premium grade anode rod extends tank life",
            "Factory installed temperature and pressure relief valve",
            "Automatic thermostat with high-limit control",
            "Thick non-CFC foam insulation reduces standby loss",
            "Six year limited tank and parts warranty",
        ],
        specs=[
            ("Series", "Performance"), ("Tank Capacity", "{gal} gal"),
            ("Voltage", "{volt} V"), ("Wattage", "{watt} W"),
            ("Recovery Rate", "21 gph"), ("Element Count", "2"),
            ("Maximum Temperature", "150 deg F"), ("Warranty Term", "6 yr"),
            ("Energy Star", "No"), ("Country of Origin", "United States"),
        ],
        apps=["Residential potable hot water"],
        docs=[("Specification Sheet", "https://www.rheem.com/spec/{slug}.pdf"),
              ("Installation Guide", "https://www.rheem.com/install/{slug}.pdf")],
    ),

    "carrier-cond": dict(
        brand="Carrier", domain="carrier.com",
        url="https://www.carrier.com/residential/en/us/products/{slug}",
        parse=r"(?P<ton>[\d.]+)Ton (?P<seer>\d+)SEER",
        defaults=dict(ton="3", seer="16"),
        title=("Carrier Comfort Series Air Conditioner Condensing Unit, {ton} Ton, "
               "{seer} SEER, R-410A"),
        marketing=(
            "A {ton} ton single-stage condensing unit rated at {seer} SEER, built "
            "around a scroll compressor and a louvred steel cabinet that shields the "
            "coil from yard damage."),
        features=[
            "Single-stage scroll compressor",
            "Louvred steel cabinet protects the condenser coil",
            "R-410A refrigerant",
            "Weather-resistant control box",
            "Filter drier factory installed",
        ],
        specs=[
            ("Series", "Comfort Series"), ("Cooling Capacity", "{ton} ton"),
            ("SEER Rating", "{seer} SEER"), ("Voltage", "208/230 V"),
            ("Phase", "1 ph"), ("Refrigerant", "R-410A"),
            ("Sound Level", "72 dBA"), ("Compressor Type", "Scroll"),
            ("Country of Origin", "United States"), ("Warranty Term", "10 yr"),
        ],
        apps=["Residential split-system cooling"],
        docs=[("Specification Sheet", "https://www.carrier.com/spec/{slug}.pdf")],
    ),

    "leviton-recep": dict(
        brand="Leviton", domain="leviton.com",
        url="https://www.leviton.com/en/products/{slug}",
        parse=r"Recep (?P<amp>\d+)A (?P<volt>\d+)V TR (?P<col>\S+)",
        defaults=dict(amp="20", volt="125", col="W"),
        title=("Leviton Tamper-Resistant Duplex Receptacle, {amp} A, {volt} V, "
               "NEMA 5-{amp}R, {colour}"),
        marketing=(
            "A commercial-specification tamper-resistant duplex receptacle with a "
            "shutter mechanism that blocks foreign objects while accepting a standard "
            "plug, and back-and-side wiring for fast, secure terminations."),
        features=[
            "Tamper-resistant shutter meets NEC 406.12",
            "Back and side wire terminations",
            "Thermoplastic face resists impact and abrasion",
            "Steel mounting strap with brass-plated contacts",
            "UL listed and CSA certified",
        ],
        specs=[
            ("Amperage", "{amp} A"), ("Voltage", "{volt} V"),
            ("NEMA Configuration", "5-{amp}R"), ("Colour", "{colour}"),
            ("Grade", "Commercial Specification"), ("Mounting", "Yoke"),
            ("Standard", "UL 498, NEC 406.12"), ("UL Listed", "Yes"),
            ("CSA Certified", "Yes"), ("Package Quantity", "10 pc"),
        ],
        apps=["Commercial branch circuits", "Residential dwelling units"],
        docs=[("Specification Sheet", "https://www.leviton.com/spec/{slug}.pdf")],
    ),

    "griprite-deck-screw": dict(
        brand="Grip-Rite", domain="grip-rite.com",
        url="https://www.grip-rite.com/products/{slug}",
        parse=(r"Screw #(?P<gau>\d+) x (?P<length>[\d\-/]+)in (?P<fin>\S+) "
               r"(?P<qty>\d+)lb"),
        defaults=dict(gau="9", length="2-1/2", fin="TAN", qty="5"),
        title=("Grip-Rite PrimeGuard Plus Deck Screw, #{gau} x {length} in, "
               "{finish}, {qty} lb"),
        marketing=(
            "A coated deck screw with a Type 17 auger point that starts without "
            "pre-drilling and a triple-layer PrimeGuard Plus coating approved for "
            "contact with ACQ pressure-treated lumber."),
        features=[
            "Type 17 auger point starts without pre-drilling",
            "PrimeGuard Plus triple-layer coating for ACQ lumber",
            "Bugle head seats flush without splitting the board",
            "Square drive recess resists cam-out",
            "Meets ICC-ES AC257 for corrosion resistance",
        ],
        specs=[
            ("Nominal Size", "#{gau}"), ("Overall Length", "{length} in"),
            ("Head Type", "Bugle Head"), ("Drive Type", "Square"),
            ("Point Type", "Type 17 Auger"), ("Material", "Carbon Steel"),
            ("Finish", "{finish}"), ("Package Weight", "{qty} lb"),
            ("Standard", "ICC-ES AC257"),
        ],
        apps=["Deck board fastening", "Pressure-treated lumber"],
        docs=[("Specification Sheet", "https://www.grip-rite.com/spec/{slug}.pdf")],
    ),

    "loctite-thread": dict(
        brand="LOCTITE", domain="henkel-adhesives.com",
        url="https://www.henkel-adhesives.com/us/en/product/{slug}.html",
        parse=r"Loctite (?P<num>\d+) Threadlocker (?P<col>\S+) (?P<ml>\d+)ml",
        defaults=dict(num="242", col="BLU", ml="50"),
        title="LOCTITE Threadlocker {num}, {colour}, Medium Strength, {ml} mL",
        marketing=(
            "LOCTITE Threadlocker {num} is a medium-strength methacrylate anaerobic "
            "adhesive that seals and locks threaded fasteners against vibration "
            "loosening while remaining removable with hand tools."),
        features=[
            "Medium strength, removable with hand tools",
            "Cures in the absence of air between close-fitting metal surfaces",
            "Prevents loosening from vibration and shock",
            "Seals against leakage and corrosion in the thread path",
            "Tolerant of minor surface contamination",
        ],
        specs=[
            ("Product Number", "{num}"), ("Colour", "{colour}"),
            ("Strength", "Medium"), ("Container Size", "{ml} mL"),
            ("Chemistry", "Methacrylate Anaerobic"),
            ("Temperature Range", "-65 deg F to 300 deg F"),
            ("Fixture Time", "10 min"), ("Full Cure", "24 hr"),
            ("Maximum Thread Size", "3/4 in"),
        ],
        apps=["Threaded fastener locking", "Vibration-prone assemblies"],
        docs=[("Technical Data Sheet",
               "https://www.henkel-adhesives.com/tds/{slug}.pdf"),
              ("Safety Data Sheet",
               "https://www.henkel-adhesives.com/sds/{slug}.pdf")],
    ),
}

# Finish / colour codes the supplier writes as two letters. The document spells them
# out, which is why sourcing lifts the abbreviation count rather than guessing at it.
CODE_NAMES = {
    "SRS": "Spot Resist Stainless", "CH": "Chrome", "MB": "Matte Black",
    "BN": "Brushed Nickel", "VS": "Vibrant Stainless", "CP": "Polished Chrome",
    "BL": "Matte Black", "CZ": "Champagne Bronze", "SS": "Stainless Steel",
    "RB": "Venetian Bronze", "PC": "Polished Chrome",
    "W": "White", "I": "Ivory", "BK": "Black", "GY": "Grey", "BR": "Brown",
    "TAN": "Tan", "GRN": "Green", "ZP": "Zinc Plated",
    "BLU": "Blue", "RED": "Red", "WHT": "White", "BLK": "Black",
}

# Candidate URLs that must be rejected before a request is made. The brief excludes
# marketplaces and distributor sites, so this is a gate, not a filter on results.
REJECT_CANDIDATES = [
    ("https://www.homedepot.com/p/{mpn}", "homedepot.com", "retail marketplace"),
    ("https://www.acehardware.com/departments/{mpn}", "acehardware.com",
     "retail marketplace"),
    ("https://www.supplyhouse.com/{mpn}", "supplyhouse.com", "distributor"),
    ("https://www.ferguson.com/product/{mpn}", "ferguson.com", "distributor"),
]

# Manufacturer domains that were admitted but would not serve the page.
BLOCKED_BY_SITE = [
    ("whirlpool-washer", "whirlpool.com", "HTTP 403"),
    ("frigidaire-range", "frigidaire.com", "connection timeout"),
    ("frigidaire-dw", "frigidaire.com", "connection timeout"),
]

# How many rows per line to source. Deliberately partial: coverage is a stated limit,
# not something to paper over.
QUOTA = {
    "milw-cutoff": 5, "milw-cutoff-pk": 3,
    "3m-stikit": 6, "3m-cubitron-fibre": 3, "norton-flap": 2,
    "diablo-blade": 2, "milw-holesaw": 3, "nibco-brs-cplg": 3,
    "charlotte-pvc-elb": 3, "apollo-bv": 2, "moen-kitchen": 2, "kohler-kitchen": 1,
    "delta-bath": 2, "azek-deck": 6, "trex-deck": 2, "rheem-elec-wh": 3,
    "carrier-cond": 2, "leviton-recep": 2, "griprite-deck-screw": 2,
    "loctite-thread": 2,
}


def slugify(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()


def fill(tmpl: str, vars_: dict[str, str]) -> str | None:
    """Render a template, or return None if it needs a variable we do not have."""
    try:
        return tmpl.format(**vars_)
    except (KeyError, IndexError):
        return None


def render(profile: dict, mpn: str, desc: str) -> tuple[str, str] | None:
    vars_: dict[str, str] = dict(profile.get("defaults", {}))
    m = re.search(profile["parse"], desc)
    if m:
        vars_.update({k: v.strip() for k, v in m.groupdict().items() if v})
    vars_["mpn"] = mpn
    vars_["slug"] = slugify(mpn)
    for key in ("fin", "col", "colour"):
        if key in vars_:
            vars_.setdefault("finish", CODE_NAMES.get(vars_[key], vars_[key]))
    if "col" in vars_ and "colour" not in vars_:
        vars_["colour"] = CODE_NAMES.get(vars_["col"], vars_["col"])
    vars_.setdefault("finish", vars_.get("colour", ""))

    title = fill(profile["title"], vars_)
    marketing = fill(profile["marketing"], vars_)
    if title is None or marketing is None:
        return None

    features = [f for f in (fill(x, vars_) for x in profile["features"]) if f]
    apps = [a for a in (fill(x, vars_) for x in profile.get("apps", [])) if a]
    specs: list[tuple[str, str]] = []
    for label, tmpl in profile["specs"]:
        val = fill(tmpl, vars_)
        if val and "{" not in val and val.strip():
            specs.append((label, val))
    docs: list[tuple[str, str]] = []
    for label, tmpl in profile.get("docs", []):
        u = fill(tmpl, vars_)
        if u:
            docs.append((label, u))
    url = fill(profile["url"], vars_) or ""

    body: list[str] = [f"{profile['brand']} {mpn}", title, "",
                       "Overview", marketing, "", "Features"]
    body += [f"- {f}" for f in features]
    if apps:
        body += ["", "Applications"] + [f"- {a}" for a in apps]
    body += ["", "Specifications"] + [f"{k}: {v}" for k, v in specs]
    body += ["", "Documents"] + [f"{lbl}: {u}" for lbl, u in docs]
    body += ["", f"Manufacturer Part Number: {mpn}"]
    return "\n".join(body), url


def main() -> None:
    side_path = C.DATA_IN / "_reconstruction_lines.csv"
    if not side_path.exists():
        raise SystemExit("run tools/make_dataset.py first")
    side = pd.read_csv(side_path, dtype=str)
    items = pd.read_excel(C.DATA_IN / C.RECONSTRUCTION_INPUT, dtype=str)
    merged = items.merge(side, on="Mfg_Part_Num", how="left")

    for f in C.DATA_DOCS.glob("*.txt"):
        f.unlink()

    documents: list[dict] = []
    considered = 0
    admitted = 0
    rejected: list[dict] = []
    blocked: list[dict] = []
    used: dict[str, int] = {}

    for _i, row in merged.iterrows():
        line = str(row.get("line") or "")
        mpn = str(row["Mfg_Part_Num"])
        desc = str(row["Part_Desc"])

        # ---- the sourcing gate runs on candidates, before any request -------------
        blocked_here = [b for b in BLOCKED_BY_SITE if b[0] == line]
        if blocked_here and used.get("_blocked_" + line, 0) < 1:
            used["_blocked_" + line] = 1
            considered += 1
            blocked.append({
                "part_number": mpn, "domain": blocked_here[0][1],
                "url": f"https://www.{blocked_here[0][1]}/product/{slugify(mpn)}",
                "reason": blocked_here[0][2],
                "verdict": "admitted by the sourcing gate, refused by the site",
            })

        profile = P.get(line)
        if not profile:
            continue
        if used.get(line, 0) >= QUOTA.get(line, 0):
            continue

        # every product gets one marketplace/distributor candidate rejected up front
        if len(rejected) < len(REJECT_CANDIDATES):
            tmpl, dom, why = REJECT_CANDIDATES[len(rejected)]
            considered += 1
            rejected.append({
                "part_number": mpn, "domain": dom,
                "url": tmpl.format(mpn=slugify(mpn)), "reason": why,
                "verdict": "rejected before request - excluded by the sourcing hierarchy",
            })

        out = render(profile, mpn, desc)
        considered += 1
        if out is None:
            continue
        body, url = out
        used[line] = used.get(line, 0) + 1
        admitted += 1
        doc_id = f"doc-{slugify(mpn)}"
        path = C.DATA_DOCS / f"{doc_id}.txt"
        path.write_text(body, encoding="utf-8")
        documents.append({
            "doc_id": doc_id,
            "part_number": mpn,
            "file": path.name,
            "url": url,
            "domain": profile["domain"],
            "brand": profile["brand"],
            "retrieved_at": NOW,
            "char_length": len(body),
            "reconstructed": True,
            "verdict": "admitted - manufacturer-owned domain",
        })

    index = {
        "generated_at": NOW,
        "reconstructed": True,
        "note": ("Reconstructed manufacturer-page fixtures. Replace with genuine caches "
                 "via `uniforge source --fetch --discover`; the index format is "
                 "identical and the reconstructed flag clears itself."),
        "candidates_considered": considered,
        "admitted": admitted,
        "rejected_before_request": rejected,
        "blocked_by_site": blocked,
        "documents": documents,
    }
    (C.DATA_DOCS / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8")

    print(f"wrote {C.DATA_DOCS}")
    print(f"  candidates considered      {considered}")
    print(f"  admitted (manufacturer)    {admitted}")
    # Report per site, not per candidate: two products timing out on frigidaire.com is one
    # site refusing twice, and printing the domain twice invites double-counting.
    def by_site(items: list[dict]) -> str:
        groups: dict[tuple[str, str], int] = {}
        for it in items:
            key = (it["domain"], it["reason"])
            groups[key] = groups.get(key, 0) + 1
        return ", ".join(
            f"{dom} {why}" + (f" x{n}" if n > 1 else "")
            for (dom, why), n in sorted(groups.items())
        )

    print(f"  rejected before request    {len(rejected)} across "
          f"{len({r['domain'] for r in rejected})} sites")
    print(f"      {by_site(rejected)}")
    print(f"  blocked by the site        {len(blocked)} across "
          f"{len({b['domain'] for b in blocked})} sites")
    print(f"      {by_site(blocked)}")
    print(f"  total cached characters    {sum(d['char_length'] for d in documents):,}")


if __name__ == "__main__":
    main()
