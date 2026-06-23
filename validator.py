"""
validator.py
Validates model JSON before passing to builder.
"""

# ─────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────
REQUIRED_PARAMS = {
    "plate":            ["length", "width", "thickness"],
    "cylinder":         ["radius", "height"],
    "hex_bolt":         ["diameter", "length"],
    "hex_nut":          ["diameter"],
    "washer":           ["diameter"],
    "chamfer_box":      ["length", "width", "thickness", "chamfer_size"],
    "fillet_box":       ["length", "width", "thickness", "fillet_r"],
    "through_hole":     ["diameter", "depth"],
    "countersunk_hole": ["diameter", "depth"],
    "slot_hole":        ["diameter", "slot_length", "depth"],
    "hex_nut_trap":     ["diameter", "plate_thickness"],
}

# Hole types must only appear as cut targets (shapes[1:]) inside difference
HOLE_TYPES = {"through_hole", "countersunk_hole", "slot_hole", "hex_nut_trap"}

ALLOWED_TYPES      = set(REQUIRED_PARAMS.keys())
ALLOWED_OPERATIONS = {"union", "difference", "intersection"}
ALLOWED_FIT        = {"close", "medium", "free"}
ALLOWED_DIRECTION  = {"x", "y"}
ALLOWED_TRAP_SIDE  = {"bottom", "top"}

# Supported M sizes for diameter-based parts
SUPPORTED_M_SIZES  = {3, 4, 5, 6, 8, 10, 12, 16, 20}

DIAMETER_TYPES = {
    "hex_bolt", "hex_nut", "washer",
    "through_hole", "countersunk_hole", "slot_hole", "hex_nut_trap",
}

NUMERIC_PARAMS = [
    "length", "width", "thickness", "radius", "height",
    "diameter", "depth", "slot_length", "plate_thickness",
    "fillet_r", "chamfer_size", "across_flats", "head_height",
    "nut_height", "outer_diameter", "cs_diameter", "cs_depth",
]

INTEGER_PARAMS = ["fn"]


# ─────────────────────────────────────────
#  Main entry point
# ─────────────────────────────────────────
def validate_model(command, path="root", _is_cut=False):
    """
    Recursively validates a model command dict.
    _is_cut: True when this node is a cut target inside difference (shapes[1:]).
    Raises ValueError with a descriptive message on failure.
    """
    if not isinstance(command, dict):
        raise ValueError(f"[{path}] Expected a dict, got {type(command).__name__}.")

    if "operation" in command:
        _validate_operation(command, path)
    elif "type" in command:
        _validate_shape(command, path, _is_cut=_is_cut)
    else:
        raise ValueError(f"[{path}] Command must have either 'operation' or 'type'.")


# ─────────────────────────────────────────
#  Operation validation
# ─────────────────────────────────────────
def _validate_operation(command, path):
    op = command["operation"]

    if op not in ALLOWED_OPERATIONS:
        raise ValueError(
            f"[{path}] Invalid operation '{op}'. "
            f"Allowed: {sorted(ALLOWED_OPERATIONS)}."
        )

    if "shapes" not in command:
        raise ValueError(f"[{path}] Operation '{op}' is missing 'shapes'.")

    if not isinstance(command["shapes"], list):
        raise ValueError(f"[{path}] 'shapes' must be a list.")

    if len(command["shapes"]) == 0:
        raise ValueError(f"[{path}] 'shapes' must not be empty.")

    if op == "difference" and len(command["shapes"]) < 2:
        raise ValueError(
            f"[{path}] 'difference' requires at least 2 shapes (base + 1 cut)."
        )

    for i, shape in enumerate(command["shapes"]):
        # shapes[0] is the base, shapes[1:] are cut targets
        is_cut = (op == "difference" and i > 0)
        validate_model(shape, path=f"{path}.shapes[{i}]", _is_cut=is_cut)


# ─────────────────────────────────────────
#  Shape validation
# ─────────────────────────────────────────
def _validate_shape(command, path, _is_cut=False):
    shape_type = command["type"]

    if shape_type not in ALLOWED_TYPES:
        raise ValueError(
            f"[{path}] Unknown type '{shape_type}'. "
            f"Allowed: {sorted(ALLOWED_TYPES)}."
        )

    # Hole types must only be used as cut targets inside difference
    if shape_type in HOLE_TYPES and not _is_cut:
        raise ValueError(
            f"[{path}] '{shape_type}' is a hole type and must only be used "
            f"as a cut target inside 'difference' (shapes[1:]), "
            f"not as a standalone shape or base shape."
        )

    # Required parameters
    for param in REQUIRED_PARAMS[shape_type]:
        if param not in command:
            raise ValueError(
                f"[{path}] '{shape_type}' is missing required parameter '{param}'."
            )

    # Numeric parameters: must be int or float (not bool), positive
    for param in NUMERIC_PARAMS:
        if param in command:
            val = command[param]
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(
                    f"[{path}] '{param}' must be a number, got {type(val).__name__}."
                )
            if val <= 0:
                raise ValueError(
                    f"[{path}] '{param}' must be positive, got {val}."
                )

    # Integer parameters: must be int (not bool), positive
    for param in INTEGER_PARAMS:
        if param in command:
            val = command[param]
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(
                    f"[{path}] '{param}' must be an integer, got {type(val).__name__} ({val})."
                )
            if val <= 0:
                raise ValueError(
                    f"[{path}] '{param}' must be a positive integer, got {val}."
                )

    # diameter must be a whole number (M-size integer)
    if "diameter" in command:
        val = command["diameter"]
        if isinstance(val, float) and not val.is_integer():
            raise ValueError(
                f"[{path}] 'diameter' must be a whole number (M-size), got {val}. "
                f"Supported sizes: {sorted(SUPPORTED_M_SIZES)}."
            )

    # Supported M size check for diameter-based types
    if shape_type in DIAMETER_TYPES:
        d = int(command["diameter"])
        # Only enforce when optional overrides are NOT all provided
        has_full_override = _has_full_manual_override(command, shape_type)
        if not has_full_override and d not in SUPPORTED_M_SIZES:
            raise ValueError(
                f"[{path}] Unsupported M size M{d} for '{shape_type}'. "
                f"Supported: {sorted(SUPPORTED_M_SIZES)}. "
                f"To use a non-standard size, provide all optional dimension parameters manually."
            )

    # Shape-specific constraints
    _validate_shape_constraints(command, shape_type, path)

    # Transform fields
    _validate_transforms(command, path)


def _has_full_manual_override(command, shape_type):
    """
    Returns True if the user has provided all optional dimension overrides,
    meaning the ISO table lookup is not needed.
    """
    overrides = {
        "hex_bolt":         ["across_flats", "head_height"],
        "hex_nut":          ["across_flats", "nut_height"],
        "washer":           ["outer_diameter", "thickness"],
        "through_hole":     [],   # always uses table; no full override possible
        "countersunk_hole": ["cs_diameter", "cs_depth"],
        "slot_hole":        [],   # always uses table
        "hex_nut_trap":     ["across_flats", "nut_height"],
    }
    required_overrides = overrides.get(shape_type, [])
    return all(p in command for p in required_overrides) and len(required_overrides) > 0


# ─────────────────────────────────────────
#  Shape-specific constraints
# ─────────────────────────────────────────
def _validate_shape_constraints(command, shape_type, path):

    if shape_type == "slot_hole":
        d  = command["diameter"]
        sl = command["slot_length"]
        if sl <= d:
            raise ValueError(
                f"[{path}] 'slot_length' ({sl}) must be greater than 'diameter' ({d})."
            )
        direction = command.get("direction", "x")
        if direction not in ALLOWED_DIRECTION:
            raise ValueError(
                f"[{path}] 'direction' must be 'x' or 'y', got '{direction}'."
            )

    if shape_type == "through_hole":
        fit = command.get("fit", "medium")
        if fit not in ALLOWED_FIT:
            raise ValueError(
                f"[{path}] 'fit' must be one of {sorted(ALLOWED_FIT)}, got '{fit}'."
            )

    if shape_type == "hex_nut_trap":
        trap_side = command.get("trap_side", "bottom")
        if trap_side not in ALLOWED_TRAP_SIDE:
            raise ValueError(
                f"[{path}] 'trap_side' must be 'bottom' or 'top', got '{trap_side}'."
            )

    if shape_type == "fillet_box":
        l, w, r = command["length"], command["width"], command["fillet_r"]
        if r >= l / 2:
            raise ValueError(
                f"[{path}] 'fillet_r' ({r}) must be less than length/2 ({l/2})."
            )
        if r >= w / 2:
            raise ValueError(
                f"[{path}] 'fillet_r' ({r}) must be less than width/2 ({w/2})."
            )

    if shape_type == "chamfer_box":
        l, w, t, c = command["length"], command["width"], command["thickness"], command["chamfer_size"]
        if c >= min(l, w, t) / 2:
            raise ValueError(
                f"[{path}] 'chamfer_size' ({c}) is too large for the box dimensions."
            )


# ─────────────────────────────────────────
#  Transform validation
# ─────────────────────────────────────────
def _validate_transforms(command, path):
    for field in ["position", "rotation"]:
        if field in command:
            val = command[field]
            if not isinstance(val, list) or len(val) != 3:
                raise ValueError(f"[{path}] '{field}' must be a list of 3 numbers.")
            for i, v in enumerate(val):
                if not isinstance(v, (int, float)):
                    raise ValueError(
                        f"[{path}] '{field}[{i}]' must be a number, got {type(v).__name__}."
                    )

    if "center" in command:
        if not isinstance(command["center"], bool):
            raise ValueError(f"[{path}] 'center' must be a boolean (true/false).")


# ─────────────────────────────────────────
#  Public helper
# ─────────────────────────────────────────
def validate_and_report(command):
    """
    Returns (is_valid: bool, error_message: str | None).
    Use this in API endpoints for clean error responses.
    """
    try:
        validate_model(command)
        return True, None
    except ValueError as e:
        return False, str(e)


# ─────────────────────────────────────────
#  Self-test
# ─────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        # ── Should PASS ──
        ("Valid difference with holes", True, {
            "operation": "difference",
            "shapes": [
                {"type": "fillet_box", "length": 80, "width": 50, "thickness": 8, "fillet_r": 5, "center": False},
                {"type": "through_hole", "diameter": 6, "depth": 8, "position": [20, 25, 0]},
                {"type": "slot_hole", "diameter": 6, "slot_length": 20, "depth": 8, "direction": "x", "position": [50, 25, 0]},
                {"type": "hex_nut_trap", "diameter": 6, "plate_thickness": 8, "position": [20, 25, 0]},
            ]
        }),
        ("Valid L-bracket", True, {
            "operation": "union",
            "shapes": [
                {"type": "plate", "length": 60, "width": 20, "thickness": 5, "center": False},
                {"type": "plate", "length": 60, "width": 20, "thickness": 5, "center": False, "rotation": [0, -90, 0]},
            ]
        }),

        # ── Should FAIL ──
        ("Hole as standalone shape", False, {
            "type": "through_hole", "diameter": 6, "depth": 8
        }),
        ("Hole as base of difference", False, {
            "operation": "difference",
            "shapes": [
                {"type": "through_hole", "diameter": 6, "depth": 8},
                {"type": "cylinder", "radius": 3, "height": 10},
            ]
        }),
        ("Hole inside union", False, {
            "operation": "union",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "through_hole", "diameter": 6, "depth": 5},
            ]
        }),
        ("Unsupported M size M7", False, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "through_hole", "diameter": 7, "depth": 5},
            ]
        }),
        ("fn as float", False, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "through_hole", "diameter": 6, "depth": 5, "fn": 50.5},
            ]
        }),
        ("Missing required param", False, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "through_hole", "diameter": 6},
            ]
        }),
        ("slot_length too small", False, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "slot_hole", "diameter": 6, "slot_length": 4, "depth": 5},
            ]
        }),
        ("fillet_r too large", False, {
            "type": "fillet_box", "length": 20, "width": 10, "thickness": 5, "fillet_r": 10
        }),
        ("difference with 1 shape only", False, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5}
            ]
        }),
        ("bool as length", False, {
            "type": "plate", "length": True, "width": 40, "thickness": 5
        }),
        ("bool as fn", False, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "through_hole", "diameter": 6, "depth": 5, "fn": True},
            ]
        }),
        ("diameter as float (non-integer)", False, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "through_hole", "diameter": 6.5, "depth": 5},
            ]
        }),
        ("diameter as float but whole number (6.0 allowed)", True, {
            "operation": "difference",
            "shapes": [
                {"type": "plate", "length": 60, "width": 40, "thickness": 5},
                {"type": "through_hole", "diameter": 6.0, "depth": 5},
            ]
        }),
    ]

    print("=" * 55)
    print("Validator self-test")
    print("=" * 55)
    all_passed = True
    for name, expect_valid, command in tests:
        is_valid, error = validate_and_report(command)
        status = "PASS" if is_valid == expect_valid else "FAIL"
        if status == "FAIL":
            all_passed = False
        result = "valid" if is_valid else f"invalid: {error}"
        print(f"[{status}] {name}\n       -> {result}")
    print("=" * 55)
    print("All tests passed." if all_passed else "Some tests FAILED.")
