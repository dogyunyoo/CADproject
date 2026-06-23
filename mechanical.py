import math

# Small offset to prevent z-fighting in difference operations
EPSILON = 0.01

# ─────────────────────────────────────────
#  Helper: hexagonal prism
#  across_flats: distance between parallel faces
# ─────────────────────────────────────────
def _hex_prism(across_flats, height, fn=6):
    r = (across_flats / 2) / math.cos(math.pi / 6)
    return f"cylinder(r={round(r,4)}, h={height}, center=false, $fn={fn});"


# ─────────────────────────────────────────
#  ISO standard dimension tables
# ─────────────────────────────────────────

# ISO 4014: (across_flats, head_height)
BOLT_SPEC = {
    3:  (5.5,  2.0),  4:  (7.0,  2.8),  5:  (8.0,  3.5),
    6:  (10.0, 4.0),  8:  (13.0, 5.3),  10: (17.0, 6.4),
    12: (19.0, 7.5),  16: (24.0, 10.0), 20: (30.0, 12.5),
}

# ISO 4032: (across_flats, nut_height)
NUT_SPEC = {
    3:  (5.5,  2.4),  4:  (7.0,  3.2),  5:  (8.0,  4.0),
    6:  (10.0, 5.0),  8:  (13.0, 6.5),  10: (17.0, 8.0),
    12: (19.0, 10.0), 16: (24.0, 13.0), 20: (30.0, 16.0),
}

# ISO 7089: (outer_diameter, thickness)
WASHER_SPEC = {
    3:  (7.0,  0.5),  4:  (9.0,  0.8),  5:  (10.0, 1.0),
    6:  (12.0, 1.6),  8:  (16.0, 1.6),  10: (20.0, 2.0),
    12: (24.0, 2.5),  16: (30.0, 3.0),  20: (37.0, 3.0),
}

# ISO 10642: (countersink_diameter, countersink_depth)
COUNTERSUNK_SPEC = {
    3:  (6.0,  1.7),  4:  (8.0,  2.3),  5:  (10.0, 2.8),
    6:  (12.0, 3.3),  8:  (16.0, 4.4),  10: (20.0, 5.5),
    12: (24.0, 6.5),  16: (30.0, 8.8),  20: (36.0, 10.8),
}

# ISO 273 medium fit clearance diameters
CLEARANCE_SPEC = {
    3: 3.4,  4: 4.5,  5: 5.5,  6: 6.6,
    8: 9.0,  10: 11.0, 12: 13.5, 16: 17.5, 20: 22.0,
}

FIT_OFFSET = {"close": -0.1, "medium": 0.0, "free": 0.3}


# ─────────────────────────────────────────
#  1. Hex bolt
#     Shaft starts at z=0 going up.
#     Head sits below z=0.
# ─────────────────────────────────────────
def generate_hex_bolt(diameter, length, across_flats=None, head_height=None, fn=100):
    d = int(diameter)
    if across_flats is None or head_height is None:
        if d not in BOLT_SPEC:
            raise ValueError(f"M{d} not in standard table. Specify across_flats and head_height manually.")
        af, hh = BOLT_SPEC[d]
        across_flats = across_flats or af
        head_height  = head_height  or hh

    shaft = f"cylinder(r={diameter/2}, h={length}, center=false, $fn={fn});"
    head  = _hex_prism(across_flats, head_height)
    head_translated = f"translate([0, 0, -{head_height}]){{{head}}};"

    return f"""
    union(){{
        {shaft}
        {head_translated}
    }}
    """


# ─────────────────────────────────────────
#  2. Hex nut
# ─────────────────────────────────────────
def generate_hex_nut(diameter, across_flats=None, nut_height=None, fn=100):
    d = int(diameter)
    if across_flats is None or nut_height is None:
        if d not in NUT_SPEC:
            raise ValueError(f"M{d} not in standard table.")
        af, nh = NUT_SPEC[d]
        across_flats = across_flats or af
        nut_height   = nut_height   or nh

    outer = _hex_prism(across_flats, nut_height)
    hole  = f"translate([0, 0, -{EPSILON}]){{cylinder(r={diameter/2}, h={nut_height + 2*EPSILON}, center=false, $fn={fn});}};"

    return f"""
    difference(){{
        {outer}
        {hole}
    }}
    """


# ─────────────────────────────────────────
#  3. Washer
# ─────────────────────────────────────────
def generate_washer(diameter, outer_diameter=None, thickness=None, fn=100):
    d = int(diameter)
    if outer_diameter is None or thickness is None:
        if d not in WASHER_SPEC:
            raise ValueError(f"M{d} not in standard table.")
        od, th = WASHER_SPEC[d]
        outer_diameter = outer_diameter or od
        thickness      = thickness      or th

    outer = f"cylinder(r={outer_diameter/2}, h={thickness}, center=false, $fn={fn});"
    hole  = f"translate([0, 0, -{EPSILON}]){{cylinder(r={diameter/2}, h={thickness + 2*EPSILON}, center=false, $fn={fn});}};"

    return f"""
    difference(){{
        {outer}
        {hole}
    }}
    """


# ─────────────────────────────────────────
#  4. Hex nut trap
#     Hexagonal pocket for nut press-fit + bolt through-hole.
#     Used for 3D-printed parts where threads cannot be printed.
#     trap_side: "bottom" (pocket opens downward) | "top"
# ─────────────────────────────────────────
def generate_hex_nut_trap(diameter, plate_thickness, across_flats=None, nut_height=None,
                           trap_side="bottom", fn=100):
    d = int(diameter)
    if across_flats is None or nut_height is None:
        if d not in NUT_SPEC:
            raise ValueError(f"M{d} not in standard table.")
        af, nh = NUT_SPEC[d]
        across_flats = across_flats or af
        nut_height   = nut_height   or nh

    bolt_hole = f"translate([0, 0, -{EPSILON}]){{cylinder(r={diameter/2}, h={plate_thickness + 2*EPSILON}, center=false, $fn={fn});}};"

    if trap_side == "bottom":
        hex_pocket = f"translate([0, 0, -{EPSILON}]){{{_hex_prism(across_flats, nut_height + EPSILON, fn=6)}}};"
    else:  # top
        hex_pocket = f"translate([0, 0, {plate_thickness - nut_height}]){{{_hex_prism(across_flats, nut_height + EPSILON, fn=6)}}};"

    return f"""
    union(){{
        {hex_pocket}
        {bolt_hole}
    }}
    """


# ─────────────────────────────────────────
#  5. Through hole (clearance hole)
#     Slightly larger than bolt diameter per ISO 273.
#     fit: "close" | "medium" (default) | "free"
# ─────────────────────────────────────────
def generate_through_hole(diameter, depth, fit="medium", fn=100):
    d = int(diameter)
    if d not in CLEARANCE_SPEC:
        raise ValueError(f"M{d} not in clearance table.")

    clearance_r = (CLEARANCE_SPEC[d] + FIT_OFFSET.get(fit, 0.0)) / 2
    hole = f"translate([0, 0, -{EPSILON}]){{cylinder(r={round(clearance_r,4)}, h={depth + 2*EPSILON}, center=false, $fn={fn});}};"
    return hole


# ─────────────────────────────────────────
#  6. Countersunk hole
#     Bolt head sits flush with the plate surface.
#     Cone opens upward from the top face.
# ─────────────────────────────────────────
def generate_countersunk_hole(diameter, depth, cs_diameter=None, cs_depth=None, angle=90, fn=100):
    d = int(diameter)
    if cs_diameter is None or cs_depth is None:
        if d not in COUNTERSUNK_SPEC:
            raise ValueError(f"M{d} not in countersunk table.")
        cd, cdepth = COUNTERSUNK_SPEC[d]
        cs_diameter = cs_diameter or cd
        cs_depth    = cs_depth    or cdepth

    clearance_r = CLEARANCE_SPEC.get(d, diameter + 0.5) / 2

    shaft_hole = f"translate([0, 0, -{EPSILON}]){{cylinder(r={round(clearance_r,4)}, h={depth + 2*EPSILON}, center=false, $fn={fn});}};"
    cone = (f"translate([0, 0, {depth - cs_depth}]){{"
            f"cylinder(r1={clearance_r}, r2={cs_diameter/2}, h={cs_depth + EPSILON}, center=false, $fn={fn});}};")

    return f"""
    union(){{
        {shaft_hole}
        {cone}
    }}
    """


# ─────────────────────────────────────────
#  7. Slot hole
#     Elongated hole for positional adjustment.
#     slot_length: total length including both end circles.
#     direction: "x" | "y"
# ─────────────────────────────────────────
def generate_slot_hole(diameter, slot_length, depth, direction="x", fn=100):
    d = int(diameter)
    clearance_r = CLEARANCE_SPEC.get(d, diameter + 0.5) / 2
    center_dist = slot_length - diameter

    if center_dist < 0:
        raise ValueError("slot_length must be greater than diameter.")

    h      = depth + 2 * EPSILON
    r      = round(clearance_r, 4)
    offset = round(center_dist / 2, 4)

    if direction == "x":
        c1  = f"translate([{-offset}, 0, -{EPSILON}]){{cylinder(r={r}, h={h}, center=false, $fn={fn});}};"
        c2  = f"translate([{offset},  0, -{EPSILON}]){{cylinder(r={r}, h={h}, center=false, $fn={fn});}};"
        box = f"translate([{-offset}, {-r}, -{EPSILON}]){{cube([{center_dist}, {2*r}, {h}], center=false);}};"
    else:  # "y"
        c1  = f"translate([0, {-offset}, -{EPSILON}]){{cylinder(r={r}, h={h}, center=false, $fn={fn});}};"
        c2  = f"translate([0, {offset},  -{EPSILON}]){{cylinder(r={r}, h={h}, center=false, $fn={fn});}};"
        box = f"translate([{-r}, {-offset}, -{EPSILON}]){{cube([{2*r}, {center_dist}, {h}], center=false);}};"

    return f"""
    union(){{
        {c1}
        {c2}
        {box}
    }}
    """


# ─────────────────────────────────────────
#  8. Chamfer box
#     Rectangular box with 45-degree chamfers on top edges.
# ─────────────────────────────────────────
def generate_chamfer_box(length, width, thickness, chamfer_size, center=False, fn=4):
    base = f"cube([{length}, {width}, {thickness}], center=false);"
    c = chamfer_size

    def corner_cut(cx, cy):
        return (f"translate([{cx}, {cy}, {thickness - c}])"
                f"{{cylinder(r1={c}, r2=0, h={c + EPSILON}, center=false, $fn=4);}};")

    cuts = "\n        ".join([
        corner_cut(0,      0),
        corner_cut(length, 0),
        corner_cut(0,      width),
        corner_cut(length, width),
    ])

    shape = f"""
    difference(){{
        {base}
        {cuts}
    }}
    """

    if center:
        shape = f"translate([{-length/2}, {-width/2}, {-thickness/2}]){{{shape}}};"

    return shape


# ─────────────────────────────────────────
#  9. Fillet box
#     Rectangular box with rounded vertical edges.
# ─────────────────────────────────────────
def generate_fillet_box(length, width, thickness, fillet_r, center=False, fn=32):
    r = fillet_r

    def corner_cyl(cx, cy):
        return (f"translate([{cx}, {cy}, 0])"
                f"{{cylinder(r={r}, h={thickness}, center=false, $fn={fn});}};")

    inner_l = length - 2 * r
    inner_w = width  - 2 * r

    parts = "\n        ".join([
        f"translate([{r}, 0, 0]){{cube([{inner_l}, {width}, {thickness}], center=false);}};",
        f"translate([0, {r}, 0]){{cube([{length}, {inner_w}, {thickness}], center=false);}};",
        corner_cyl(r,          r),
        corner_cyl(length - r, r),
        corner_cyl(r,          width - r),
        corner_cyl(length - r, width - r),
    ])

    shape = f"""
    union(){{
        {parts}
    }}
    """

    if center:
        shape = f"translate([{-length/2}, {-width/2}, {-thickness/2}]){{{shape}}};"

    return shape
