import json
from mechanical import (
    generate_hex_bolt, generate_hex_nut, generate_washer,
    generate_hex_nut_trap, generate_through_hole,
    generate_countersunk_hole, generate_slot_hole,
    generate_chamfer_box, generate_fillet_box,
)

# ─────────────────────────────────────────
#  OpenSCAD primitives
# ─────────────────────────────────────────
def generate_plate(length, width, thickness, center=True):
    return f"cube([{length}, {width}, {thickness}], center={str(center).lower()});"

def generate_cylinder(radius, height, center=True, fn=100):
    return f"cylinder(r={radius}, h={height}, center={str(center).lower()}, $fn={fn});"

def translate(shape_code, x=0, y=0, z=0):
    return f"translate([{x}, {y}, {z}]){{{shape_code}}};"

def rotate(shape_code, x=0, y=0, z=0):
    return f"rotate([{x}, {y}, {z}]){{{shape_code}}};"

def difference(base_code, *cut_codes):
    cuts = "\n".join(cut_codes)
    return f"""
    difference(){{
        {base_code}
        {cuts}
    }}
    """

def union(*shapes):
    shape_text = "\n".join(shapes)
    return f"""
    union(){{
        {shape_text}
    }}
    """

def intersection(*shapes):
    shape_text = "\n".join(shapes)
    return f"""
    intersection(){{
        {shape_text}
    }}
    """

def save_scad(scad_code, filename="part.scad"):
    with open(filename, "w") as file:
        file.write(scad_code)
    print(f"{filename} generated.")


# ─────────────────────────────────────────
#  JSON -> OpenSCAD builder
# ─────────────────────────────────────────
def build(command):
    if "operation" in command:
        return build_model(command)
    else:
        return build_shape(command)

def build_shape(shape_command):
    shape_type = shape_command["type"]
    center = shape_command.get("center", True)

    # Primitives
    if shape_type == "plate":
        shape = generate_plate(
            shape_command["length"], shape_command["width"],
            shape_command["thickness"], center=center)

    elif shape_type == "cylinder":
        shape = generate_cylinder(
            shape_command["radius"], shape_command["height"],
            center=center, fn=shape_command.get("fn", 100))

    # Solid parts
    elif shape_type == "hex_bolt":
        shape = generate_hex_bolt(
            diameter     = shape_command["diameter"],
            length       = shape_command["length"],
            across_flats = shape_command.get("across_flats"),
            head_height  = shape_command.get("head_height"),
            fn           = shape_command.get("fn", 100))

    elif shape_type == "hex_nut":
        shape = generate_hex_nut(
            diameter     = shape_command["diameter"],
            across_flats = shape_command.get("across_flats"),
            nut_height   = shape_command.get("nut_height"),
            fn           = shape_command.get("fn", 100))

    elif shape_type == "washer":
        shape = generate_washer(
            diameter       = shape_command["diameter"],
            outer_diameter = shape_command.get("outer_diameter"),
            thickness      = shape_command.get("thickness"),
            fn             = shape_command.get("fn", 100))

    elif shape_type == "chamfer_box":
        shape = generate_chamfer_box(
            length       = shape_command["length"],
            width        = shape_command["width"],
            thickness    = shape_command["thickness"],
            chamfer_size = shape_command["chamfer_size"],
            center       = center)

    elif shape_type == "fillet_box":
        shape = generate_fillet_box(
            length    = shape_command["length"],
            width     = shape_command["width"],
            thickness = shape_command["thickness"],
            fillet_r  = shape_command["fillet_r"],
            center    = center,
            fn        = shape_command.get("fn", 32))

    # Hole types (used as cut targets in difference)
    elif shape_type == "hex_nut_trap":
        shape = generate_hex_nut_trap(
            diameter        = shape_command["diameter"],
            plate_thickness = shape_command["plate_thickness"],
            across_flats    = shape_command.get("across_flats"),
            nut_height      = shape_command.get("nut_height"),
            trap_side       = shape_command.get("trap_side", "bottom"),
            fn              = shape_command.get("fn", 100))

    elif shape_type == "through_hole":
        shape = generate_through_hole(
            diameter = shape_command["diameter"],
            depth    = shape_command["depth"],
            fit      = shape_command.get("fit", "medium"),
            fn       = shape_command.get("fn", 100))

    elif shape_type == "countersunk_hole":
        shape = generate_countersunk_hole(
            diameter    = shape_command["diameter"],
            depth       = shape_command["depth"],
            cs_diameter = shape_command.get("cs_diameter"),
            cs_depth    = shape_command.get("cs_depth"),
            fn          = shape_command.get("fn", 100))

    elif shape_type == "slot_hole":
        shape = generate_slot_hole(
            diameter    = shape_command["diameter"],
            slot_length = shape_command["slot_length"],
            depth       = shape_command["depth"],
            direction   = shape_command.get("direction", "x"),
            fn          = shape_command.get("fn", 100))

    else:
        raise ValueError(f"Unknown shape type: '{shape_type}'")

    # Apply transforms: rotation first, then position
    if "rotation" in shape_command:
        rx, ry, rz = shape_command["rotation"]
        shape = rotate(shape, rx, ry, rz)

    if "position" in shape_command:
        x, y, z = shape_command["position"]
        shape = translate(shape, x, y, z)

    return shape


def build_model(model_command):
    operation = model_command["operation"]
    shapes = [build(cmd) for cmd in model_command["shapes"]]

    if operation == "union":
        return union(*shapes)
    elif operation == "difference":
        return difference(shapes[0], *shapes[1:])
    elif operation == "intersection":
        return intersection(*shapes)
    else:
        raise ValueError(f"Unknown operation: '{operation}'")


# ─────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────
if __name__ == "__main__":
    with open("model.json", "r") as file:
        model_command = json.load(file)

    model = build(model_command)
    save_scad(model)
