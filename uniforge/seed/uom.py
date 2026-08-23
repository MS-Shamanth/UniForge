"""Approved unit-of-measure abbreviations, grouped by measurement type.

The only permitted way to write a unit anywhere in the output. Two house rules are
enforced in code, not asked for in a prompt:

  1. exactly one space between the magnitude and the unit  -> "24 in", never "24in"
  2. one canonical spelling per unit                        -> inches / IN. / inch / "  ->  in

`ALIASES` is deliberately generous on the input side and strict on the output side.
"""
from __future__ import annotations

# measurement_type -> (canonical abbreviation, [aliases], example capture form)
UOM_TABLE: list[tuple[str, str, list[str], str]] = [
    # ---- length -------------------------------------------------------------------
    ("Length", "in", ["inch", "inches", "in.", '"', "''", "ins", "inchs"], "24 in"),
    ("Length", "ft", ["foot", "feet", "ft.", "'", "fts"], "8 ft"),
    ("Length", "yd", ["yard", "yards", "yd.", "yds"], "3 yd"),
    ("Length", "mm", ["millimeter", "millimetre", "millimeters", "mm."], "12 mm"),
    ("Length", "cm", ["centimeter", "centimetre", "centimeters", "cm."], "30 cm"),
    ("Length", "m", ["meter", "metre", "meters", "m."], "2 m"),
    ("Length", "mi", ["mile", "miles"], "1 mi"),
    ("Length", "mil", ["mils", "thou"], "5 mil"),
    ("Length", "micron", ["microns", "um", "µm"], "40 micron"),
    # ---- weight -------------------------------------------------------------------
    ("Weight", "lb", ["lbs", "pound", "pounds", "lb.", "#"], "12 lb"),
    ("Weight", "oz", ["ounce", "ounces", "oz."], "16 oz"),
    ("Weight", "g", ["gram", "grams", "gm", "gms"], "500 g"),
    ("Weight", "kg", ["kilogram", "kilograms", "kgs", "kilo"], "5 kg"),
    ("Weight", "ton", ["tons", "tonne", "tonnes", "tn"], "2 ton"),
    ("Weight", "gr", ["grain", "grains"], "50 gr"),
    # ---- area ---------------------------------------------------------------------
    ("Area", "sq in", ["square inch", "square inches", "in2", "in²", "sqin"], "12 sq in"),
    ("Area", "sq ft", ["square foot", "square feet", "ft2", "ft²", "sqft", "sf"], "20 sq ft"),
    ("Area", "sq yd", ["square yard", "square yards", "yd2", "sqyd"], "4 sq yd"),
    ("Area", "sq m", ["square meter", "square metre", "m2", "m²", "sqm"], "6 sq m"),
    # ---- volume -------------------------------------------------------------------
    ("Volume", "gal", ["gallon", "gallons", "gals", "gal."], "5 gal"),
    ("Volume", "qt", ["quart", "quarts", "qts"], "2 qt"),
    ("Volume", "pt", ["pint", "pints", "pts"], "1 pt"),
    ("Volume", "fl oz", ["fluid ounce", "fluid ounces", "floz", "fl. oz."], "8 fl oz"),
    ("Volume", "L", ["liter", "litre", "liters", "litres", "l"], "3 L"),
    ("Volume", "mL", ["milliliter", "millilitre", "milliliters", "ml"], "250 mL"),
    ("Volume", "cu in", ["cubic inch", "cubic inches", "in3", "cuin"], "30 cu in"),
    ("Volume", "cu ft", ["cubic foot", "cubic feet", "ft3", "cuft", "cf"], "4 cu ft"),
    ("Volume", "cu yd", ["cubic yard", "cubic yards", "yd3", "cuyd"], "2 cu yd"),
    # ---- flow ---------------------------------------------------------------------
    ("Flow Rate", "gpm", ["gallons per minute", "gal/min", "g.p.m."], "1.8 gpm"),
    ("Flow Rate", "gph", ["gallons per hour", "gal/hr"], "50 gph"),
    ("Flow Rate", "cfm", ["cubic feet per minute", "ft3/min", "c.f.m."], "300 cfm"),
    ("Flow Rate", "cfh", ["cubic feet per hour", "ft3/hr"], "90 cfh"),
    ("Flow Rate", "lpm", ["liters per minute", "l/min"], "6 lpm"),
    ("Flow Rate", "scfm", ["standard cfm", "std cfm"], "10 scfm"),
    # ---- pressure -----------------------------------------------------------------
    ("Pressure", "psi", ["pounds per square inch", "lb/in2", "p.s.i.", "#"], "150 psi"),
    ("Pressure", "psig", ["psi gauge", "psi-g"], "125 psig"),
    ("Pressure", "kPa", ["kilopascal", "kilopascals", "kpa"], "1000 kPa"),
    ("Pressure", "bar", ["bars"], "10 bar"),
    ("Pressure", "in wc", ["inches water column", "in w.c.", "iwc", "in. wc"], "5 in wc"),
    ("Pressure", "mm Hg", ["millimeters mercury", "mmhg"], "760 mm Hg"),
    # ---- electrical ---------------------------------------------------------------
    ("Voltage", "V", ["volt", "volts", "vac", "vdc", "v"], "120 V"),
    ("Current", "A", ["amp", "amps", "ampere", "amperes", "a"], "15 A"),
    ("Current", "mA", ["milliamp", "milliamps", "milliampere", "ma"], "500 mA"),
    ("Power", "W", ["watt", "watts", "w"], "60 W"),
    ("Power", "kW", ["kilowatt", "kilowatts", "kw"], "1.5 kW"),
    ("Power", "hp", ["horsepower", "h.p."], "1/2 hp"),
    ("Frequency", "Hz", ["hertz", "hz", "cycles"], "60 Hz"),
    ("Resistance", "ohm", ["ohms", "Ω"], "100 ohm"),
    ("Apparent Power", "VA", ["volt-ampere", "volt amperes", "va"], "40 VA"),
    ("Apparent Power", "kVA", ["kilovolt-ampere", "kva"], "15 kVA"),
    ("Battery Capacity", "Ah", ["amp hour", "amp hours", "ampere-hour", "ah"], "5 Ah"),
    ("Battery Capacity", "mAh", ["milliamp hour", "mah"], "2000 mAh"),
    ("Wire Size", "AWG", ["american wire gauge", "awg", "ga awg"], "12 AWG"),
    ("Phase", "ph", ["phase", "phases", "ø"], "3 ph"),
    # ---- temperature --------------------------------------------------------------
    ("Temperature", "deg F", ["fahrenheit", "degrees f", "°f", "f", "deg. f"], "180 deg F"),
    ("Temperature", "deg C", ["celsius", "centigrade", "degrees c", "°c", "deg. c"], "82 deg C"),
    ("Temperature", "K", ["kelvin", "kelvins"], "3000 K"),
    # ---- time ---------------------------------------------------------------------
    ("Time", "sec", ["second", "seconds", "s", "secs"], "30 sec"),
    ("Time", "min", ["minute", "minutes", "mins"], "15 min"),
    ("Time", "hr", ["hour", "hours", "hrs", "h"], "8 hr"),
    ("Time", "day", ["days"], "30 day"),
    ("Time", "mo", ["month", "months", "mos"], "12 mo"),
    ("Time", "yr", ["year", "years", "yrs"], "10 yr"),
    # ---- rotation / cycles ---------------------------------------------------------
    ("Rotational Speed", "rpm", ["revolutions per minute", "r.p.m.", "rev/min"], "13300 rpm"),
    ("Rotational Speed", "opm", ["oscillations per minute", "orbits per minute"], "20000 opm"),
    ("Rotational Speed", "spm", ["strokes per minute"], "3000 spm"),
    ("Rotational Speed", "bpm", ["blows per minute", "beats per minute"], "4900 bpm"),
    ("Rotational Speed", "ipm", ["impacts per minute"], "3400 ipm"),
    # ---- torque -------------------------------------------------------------------
    ("Torque", "in-lb", ["inch pound", "inch pounds", "in lb", "inlb", "in.-lb."], "150 in-lb"),
    ("Torque", "ft-lb", ["foot pound", "foot pounds", "ft lb", "ftlb", "ft.-lb."], "1200 ft-lb"),
    ("Torque", "Nm", ["newton meter", "newton metre", "n-m", "nm"], "60 Nm"),
    # ---- sound / light -------------------------------------------------------------
    ("Sound Level", "dBA", ["a-weighted decibel", "db(a)", "dba"], "47 dBA"),
    ("Sound Level", "dB", ["decibel", "decibels", "db"], "90 dB"),
    ("Sound Level", "sone", ["sones"], "1.5 sone"),
    ("Luminous Flux", "lm", ["lumen", "lumens"], "800 lm"),
    ("Illuminance", "fc", ["foot-candle", "footcandle", "foot candles"], "50 fc"),
    ("Illuminance", "lx", ["lux"], "500 lx"),
    ("Colour Rendering", "CRI", ["color rendering index", "cri"], "90 CRI"),
    # ---- angle / speed --------------------------------------------------------------
    ("Angle", "deg", ["degree", "degrees", "°"], "45 deg"),
    ("Linear Speed", "fpm", ["feet per minute", "ft/min"], "6500 fpm"),
    ("Linear Speed", "sfpm", ["surface feet per minute"], "6000 sfpm"),
    ("Linear Speed", "mph", ["miles per hour"], "60 mph"),
    # ---- energy / thermal ----------------------------------------------------------
    ("Heat", "BTU", ["british thermal unit", "btus", "btu"], "40000 BTU"),
    ("Heat", "BTUH", ["btu per hour", "btu/hr", "btuh"], "36000 BTUH"),
    ("Heat", "MBH", ["thousand btu per hour", "mbh"], "80 MBH"),
    ("Energy", "kWh", ["kilowatt hour", "kilowatt-hours", "kwh"], "270 kWh"),
    ("Energy", "J", ["joule", "joules"], "12 J"),
    ("Cooling Capacity", "ton", ["tons cooling", "tonnage"], "3 ton"),
    ("Efficiency", "SEER", ["seasonal energy efficiency ratio", "seer"], "16 SEER"),
    ("Efficiency", "EER", ["energy efficiency ratio", "eer"], "12 EER"),
    ("Efficiency", "AFUE", ["annual fuel utilization efficiency", "afue"], "96 AFUE"),
    ("Efficiency", "HSPF", ["heating seasonal performance factor", "hspf"], "9 HSPF"),
    # ---- thread / gauge ------------------------------------------------------------
    ("Thread Pitch", "tpi", ["threads per inch", "t.p.i."], "18 tpi"),
    ("Thread Type", "NPT", ["national pipe thread", "npt", "n.p.t."], "1/2 in NPT"),
    ("Thread Type", "NPSM", ["npsm"], "3/4 in NPSM"),
    ("Thread Type", "BSP", ["british standard pipe", "bsp"], "1 in BSP"),
    ("Gauge", "ga", ["gauge", "gage", "ga."], "16 ga"),
    # ---- abrasives / cutting -------------------------------------------------------
    ("Grit", "grit", ["grits", "grit size"], "120 grit"),
    ("Tooth Count", "tpi", ["teeth per inch"], "24 tpi"),
    ("Tooth Count", "T", ["tooth", "teeth"], "60 T"),
    # ---- counts / packaging ---------------------------------------------------------
    ("Count", "ea", ["each", "eaches", "ea."], "1 ea"),
    ("Count", "pc", ["piece", "pieces", "pcs", "pc."], "10 pc"),
    ("Count", "pk", ["pack", "packs", "pkg", "package"], "3 pk"),
    ("Count", "pr", ["pair", "pairs"], "1 pr"),
    ("Count", "set", ["sets"], "1 set"),
    ("Count", "dz", ["dozen", "dozens", "doz"], "1 dz"),
    ("Count", "bx", ["box", "boxes", "bxs"], "1 bx"),
    ("Count", "cs", ["case", "cases"], "1 cs"),
    ("Count", "ctn", ["carton", "cartons"], "1 ctn"),
    ("Count", "bdl", ["bundle", "bundles"], "1 bdl"),
    ("Count", "rl", ["roll", "rolls"], "1 rl"),
    ("Count", "sht", ["sheet", "sheets"], "50 sht"),
    ("Count", "bag", ["bags"], "1 bag"),
    ("Count", "tube", ["tubes"], "1 tube"),
    ("Count", "kit", ["kits"], "1 kit"),
    ("Count", "pl", ["pallet", "pallets"], "1 pl"),
    ("Count", "cd", ["card", "cards"], "1 cd"),
    ("Count", "ct", ["count", "counts"], "100 ct"),
    # ---- misc ----------------------------------------------------------------------
    ("Ratio", "%", ["percent", "percentage", "pct"], "95 %"),
    ("Density", "lb/cu ft", ["pounds per cubic foot", "pcf"], "2 lb/cu ft"),
    ("Coverage", "sq ft/gal", ["square feet per gallon"], "350 sq ft/gal"),
    ("Viscosity", "cP", ["centipoise", "cps"], "500 cP"),
    ("Conductivity", "uS/cm", ["microsiemens per centimeter"], "50 uS/cm"),
    ("Hardness", "Shore A", ["shore a durometer", "shore-a"], "70 Shore A"),
    ("Capacity", "cfm/ton", ["cfm per ton"], "400 cfm/ton"),
    ("Vacuum", "in Hg", ["inches mercury", "inhg"], "29 in Hg"),
]

# 22 house-style rules from the abbreviations standard, encoded where they are testable.
STYLE_RULES = [
    ("space-before-unit", "One space between magnitude and unit: 24 in, not 24in."),
    ("single-canonical-form", 'One approved abbreviation per unit: inches / IN. / " -> in.'),
    ("no-trailing-period", "Abbreviations carry no trailing period: in, not in."),
    ("fraction-hyphen", "Mixed numbers hyphenate the fraction: 50-1/4 in."),
    ("dimension-separator", "Dimensions join with ' x ': 24 in W x 24-1/4 in D."),
    ("degree-words", "Temperature is written deg F / deg C, never the ° glyph."),
    ("registered-mark-kept", "Brand marks (® / ™) are preserved exactly as approved."),
    ("caps-invoice", "Invoice descriptions are ALL CAPS and <= 40 characters."),
    ("no-invented-unit", "A unit not on the approved list may not be written."),
    ("qualifier-suffix", "Dimensional qualifiers follow the unit: 24 in W, 47 dBA."),
]


def build_alias_map() -> dict[str, str]:
    """lowercased alias -> canonical abbreviation. Canonicals map to themselves."""
    out: dict[str, str] = {}
    for _mt, canonical, aliases, _ex in UOM_TABLE:
        out.setdefault(canonical.lower(), canonical)
        for a in aliases:
            out.setdefault(a.lower(), canonical)
    return out


def approved_units() -> set[str]:
    return {canonical for _mt, canonical, _a, _e in UOM_TABLE}


def measurement_types() -> dict[str, str]:
    """canonical abbreviation -> measurement type"""
    return {canonical: mt for mt, canonical, _a, _e in UOM_TABLE}
