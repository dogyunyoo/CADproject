"""
gear_solver.py
Handles gear center distance, phase rotation, and mesh alignment.

Phase alignment research notes (for future multi-turn / auto-correction):

  spur_gear (BOSL2):
    - rotation_2 = 0 works for all tested cases (even+even, odd+odd).
    - BOSL2 spur_gear() generates gears with internally consistent phase.
    - Verified: 12+24, 20+30 (even+even), 7+29, 17+29 (odd+odd).
    - If misaligned, use phase_override_2 to manually adjust.
    - TODO: verify even+odd combinations.

  worm_gear (BOSL2):
    - BOSL2 worm_gear() does NOT auto-align with worm().
    - rotation = 180/gear_teeth required.
    - Verified for starts=1 and starts=2.
    - TODO: verify starts > 2, left-handed worms.

  rack (BOSL2):
    - rotation = 0, no correction needed.
    - BOSL2 rack() aligns with spur_gear() by default.

  Future multi-turn correction:
    - User says "gears not meshing" -> increment rotation by 180/teeth
      until meshed, or ask user to confirm visually.

Confidence levels:
  exact     - mathematically exact, always correct
  heuristic - works for standard BOSL2 default orientation; may fail for
              helical, profile-shifted, custom-start, or non-default cases
  delegated - computed by OpenSCAD/BOSL2 at render time (e.g. worm_dist())
  manual    - user must supply phase_override
"""

import math


# ─────────────────────────────────────────
#  Unit conversion
# ─────────────────────────────────────────
def inch_to_mm(value_inch):
    """Convert inches to millimeters."""
    return round(value_inch * 25.4, 6)

def mm_to_inch(value_mm):
    """Convert millimeters to inches."""
    return round(value_mm / 25.4, 6)


# ─────────────────────────────────────────
#  Gear outer diameter solver
#
#  BOSL2 spur_gear outer diameter formula:
#    outer_d = circ_pitch * (teeth + 2) / PI
#  Rearranged:
#    teeth = round(outer_d * PI / circ_pitch) - 2
#
#  Strategy: try preferred circ_pitch values,
#  pick the one whose resulting outer_d is closest to target.
# ─────────────────────────────────────────
PREFERRED_CIRC_PITCHES = [3, 4, 5, 6, 8, 10]

def outer_diameter_to_gear_params(outer_diameter_mm, preferred_circ_pitch=None, min_teeth=6):
    """
    Given a target outer diameter (mm), returns the best (circ_pitch, teeth) pair.

    Args:
        outer_diameter_mm:    target outer diameter in mm
        preferred_circ_pitch: if given, only try this value
        min_teeth:            minimum teeth count (default 6)

    Returns dict:
        circ_pitch, teeth, actual_outer_diameter, error_mm, error_pct
    """
    candidates = [preferred_circ_pitch] if preferred_circ_pitch else PREFERRED_CIRC_PITCHES

    best = None
    for cp in candidates:
        teeth = round(outer_diameter_mm * math.pi / cp) - 2
        if teeth < min_teeth:
            teeth = min_teeth
        actual_od = cp * (teeth + 2) / math.pi
        error_mm  = abs(actual_od - outer_diameter_mm)
        error_pct = error_mm / outer_diameter_mm * 100

        if best is None or error_mm < best["error_mm"]:
            best = {
                "circ_pitch":            cp,
                "teeth":                 teeth,
                "actual_outer_diameter": round(actual_od, 4),
                "target_outer_diameter": round(outer_diameter_mm, 4),
                "error_mm":              round(error_mm, 4),
                "error_pct":             round(error_pct, 2),
            }

    return best


# ─────────────────────────────────────────
#  Spur gear pair
# ─────────────────────────────────────────
def solve_spur_pair(
    circ_pitch, teeth_1, teeth_2,
    backlash=0,
    phase_mode="none",
    phase_override_2=None,
):
    """
    Returns center distance and rotations for a spur gear pair.

    phase_mode:
      "none"     - no phase correction (default, BOSL2 auto-aligns)
      "visual"   - same as none for spur gears
      "override" - use phase_override_2 (degrees) for gear 2
    """
    center_distance = circ_pitch * (teeth_1 + teeth_2) / (2 * math.pi) + backlash

    if phase_override_2 is not None:
        rotation_1 = 0
        rotation_2 = phase_override_2
        phase_confidence = "manual"
    elif phase_mode in ("visual", "none"):
        # BOSL2 spur_gear() automatically generates gears with correct meshing
        # phase. rotation_2 = 0 works for all tested cases.
        # Verified: 12+24, 20+30 (even+even), 7+29, 17+29 (odd+odd).
        rotation_1 = 0
        rotation_2 = 0
        phase_confidence = "exact"
    else:
        raise ValueError(f"Unknown phase_mode: '{phase_mode}'. Use 'visual', 'none', or 'override'.")

    return {
        "center_distance":    round(center_distance, 6),
        "rotation_1":         rotation_1,
        "rotation_2":         rotation_2,
        "confidence": {
            "center_distance": "exact",
            "phase":           phase_confidence,
        },
    }


# ─────────────────────────────────────────
#  Worm + worm gear pair
# ─────────────────────────────────────────
def solve_worm_pair(
    circ_pitch, worm_d, gear_teeth,
    starts=1,
    phase_mode="visual",
    phase_override_gear=None,
):
    """
    Returns OpenSCAD expression for center distance (via BOSL2 worm_dist())
    and rotation values for worm + worm gear.
    """
    center_expr = (
        f"worm_dist(circ_pitch={circ_pitch}, d={worm_d}, "
        f"teeth={gear_teeth}, starts={starts})"
    )

    worm_rotation = [0, 90, 0]

    if phase_override_gear is not None:
        gear_rotation_z = phase_override_gear
        phase_confidence = "manual"
    elif phase_mode == "visual":
        # BOSL2 worm_gear() does NOT auto-align with worm().
        # Manual rotation of 180/gear_teeth degrees is required.
        # Verified for starts=1 and starts=2.
        # TODO: verify for starts > 2, left-handed worms.
        gear_rotation_z = 180 / gear_teeth
        phase_confidence = "heuristic"
    elif phase_mode == "none":
        gear_rotation_z = 0
        phase_confidence = "exact"
    else:
        raise ValueError(f"Unknown phase_mode: '{phase_mode}'.")

    return {
        "center_distance_expr": center_expr,
        "worm_rotation":        worm_rotation,
        "gear_rotation_z":      gear_rotation_z,
        "confidence": {
            "center_distance": "delegated_to_bosl2",
            "phase":           phase_confidence,
        },
    }


# ─────────────────────────────────────────
#  Rack + pinion pair
# ─────────────────────────────────────────
def solve_rack_pair(
    circ_pitch, pinion_teeth,
    backlash=0,
    phase_mode="none",
    phase_override_pinion=None,
):
    """
    Returns rack Y offset and pinion rotation for a rack & pinion pair.
    No phase rotation needed - BOSL2 rack() aligns with spur_gear() by default.
    """
    pitch_radius  = circ_pitch * pinion_teeth / (2 * math.pi)
    rack_y_offset = -(pitch_radius + backlash)

    if phase_override_pinion is not None:
        pinion_rotation_z = phase_override_pinion
        phase_confidence  = "manual"
    else:
        pinion_rotation_z = 0
        phase_confidence  = "exact"

    return {
        "rack_y_offset":     round(rack_y_offset, 6),
        "pinion_rotation_z": pinion_rotation_z,
        "confidence": {
            "center_distance": "exact",
            "phase":           phase_confidence,
        },
    }


# ─────────────────────────────────────────
#  Self-test
# ─────────────────────────────────────────
if __name__ == "__main__":
    import json

    print("=== inch_to_mm ===")
    print(f"2 inch = {inch_to_mm(2)} mm")
    print(f"0.26 inch = {inch_to_mm(0.26)} mm")

    print("\n=== outer_diameter_to_gear_params ===")
    target = inch_to_mm(2)  # 2 inch = 50.8mm
    r = outer_diameter_to_gear_params(target)
    print(f"Target: {target}mm (2 inch)")
    print(json.dumps(r, indent=2))

    print("\n=== outer_diameter_to_gear_params (preferred circ_pitch=4) ===")
    r = outer_diameter_to_gear_params(target, preferred_circ_pitch=4)
    print(json.dumps(r, indent=2))

    print("\n=== spur_pair ===")
    r = solve_spur_pair(circ_pitch=5, teeth_1=12, teeth_2=24)
    print(json.dumps(r, indent=2))

    print("\n=== worm_pair ===")
    r = solve_worm_pair(circ_pitch=5, worm_d=20, gear_teeth=30, starts=2)
    print(json.dumps(r, indent=2))

    print("\n=== rack_pair ===")
    r = solve_rack_pair(circ_pitch=5, pinion_teeth=16)
    print(json.dumps(r, indent=2))