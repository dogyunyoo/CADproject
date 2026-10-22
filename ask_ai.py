"""
ask_ai.py
Converts natural language input to CAD JSON using Claude API.
"""

import os 
import json
import subprocess
from dotenv import load_dotenv
import anthropic

from validator import validate_and_report
from main import build, save_scad
from gear_solver import inch_to_mm, outer_diameter_to_gear_params

# ─────────────────────────────────────────
#  Load API key from .env (You must have an .env file for your api-key)
# ─────────────────────────────────────────
load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise EnvironmentError("ANTHROPIC_API_KEY not found in .env file.")

client = anthropic.Anthropic(api_key=api_key)

# ─────────────────────────────────────────
#  Load JSON rule as system prompt
# ─────────────────────────────────────────
RULE_PATH = os.path.join(os.path.dirname(__file__), "JSON_rule.txt")
with open(RULE_PATH, "r", encoding="utf-8") as f:
    JSON_RULE = f.read()

SYSTEM_PROMPT = f"""You are a CAD JSON generator.
Convert the user's natural language description into a valid CAD JSON object.

Follow this specification exactly:
{JSON_RULE}

Output JSON only. No explanation, no markdown, no code blocks.
Just the raw JSON object starting with {{ and ending with }}.
"""

# OpenSCAD executable path
OPENSCAD_PATH = r"C:\Program Files\OpenSCAD\openscad.exe"


# ─────────────────────────────────────────
#  Pre-processor: detect inch values and inject gear solver hints
# ─────────────────────────────────────────
import re

def preprocess_input(user_input: str) -> str:
    """
    Detects inch values in user input and appends gear solver hints.
    e.g. "2 inch outer diameter gear" -> appends best circ_pitch+teeth suggestion
    """
    hints = []

    # Detect inch patterns: e.g. "2 inch", "2-inch", "2"", "2in"
    inch_pattern = re.compile(
        r'([\d.]+)[\s-]*(?:inch(?:es)?|in\b|")',
        re.IGNORECASE
    )
    matches = inch_pattern.findall(user_input)

    # Convert all inch values to mm
    if matches:
        conversions = []
        for val_str in matches:
            val_inch = float(val_str)
            val_mm   = inch_to_mm(val_inch)
            conversions.append(f"{val_inch} inch = {val_mm} mm")
        hints.append("Unit conversions: " + ", ".join(conversions))

    # If "outer diameter" or "OD" + inch -> suggest gear params
    od_pattern = re.compile(
        r'([\d.]+)\s*(?:inch(?:es)?|in\b|").*?(?:outer\s*diameter|OD|gear)',
        re.IGNORECASE
    )
    od_match = od_pattern.search(user_input)
    if not od_match:
        # Also try reversed: "gear ... 2 inch outer diameter"
        od_pattern2 = re.compile(
            r'(?:outer\s*diameter|OD|gear).*?([\d.]+)\s*(?:inch(?:es)?|in\b|")',
            re.IGNORECASE
        )
        od_match = od_pattern2.search(user_input)

    if od_match:
        od_inch = float(od_match.group(1))
        od_mm   = inch_to_mm(od_inch)
        result  = outer_diameter_to_gear_params(od_mm)
        hints.append(
            f"For {od_inch} inch ({od_mm} mm) outer diameter gear: "
            f"use circ_pitch={result['circ_pitch']}, teeth={result['teeth']} "
            f"(actual outer_d={result['actual_outer_diameter']} mm, "
            f"error={result['error_mm']} mm)"
        )

    if hints:
        hint_str = "\n[Pre-computed hints - use these values directly]\n" + "\n".join(hints)
        return user_input + hint_str

    return user_input


# ─────────────────────────────────────────
#  Core function: natural language -> JSON
# ─────────────────────────────────────────
def ask_ai(user_input: str, max_retries: int = 2) -> dict:
    """
    Sends user_input to Claude API and returns a validated JSON dict.
    Retries up to max_retries times if validation fails.
    """
    last_error = None
    last_response_text = ""

    for attempt in range(1, max_retries + 1):
        print(f"[ask_ai] Attempt {attempt}/{max_retries}...")

        # Build messages
        messages = [{"role": "user", "content": user_input}]

        # If previous attempt failed, append error feedback
        if last_error:
            messages.append({"role": "assistant", "content": last_response_text})
            messages.append({
                "role": "user",
                "content": f"The JSON you generated failed validation: {last_error}\nPlease fix it and return valid JSON only."
            })

        # Call Claude API
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        last_response_text = response.content[0].text.strip()

        # Strip markdown code blocks if present
        if last_response_text.startswith("```"):
            last_response_text = last_response_text.split("```")[1]
            if last_response_text.startswith("json"):
                last_response_text = last_response_text[4:]
            last_response_text = last_response_text.strip()

        print(f"[debug] Raw response: {last_response_text[:200]}")

        # Parse JSON
        try:
            result = json.loads(last_response_text)
        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON syntax: {e}"
            print(f"[ask_ai] JSON parse error: {last_error}")
            continue

        # Validate
        is_valid, error = validate_and_report(result)
        if is_valid:
            print(f"[ask_ai] Valid JSON generated on attempt {attempt}.")
            return result
        else:
            last_error = error
            print(f"[ask_ai] Validation failed: {last_error}")

    raise ValueError(f"Failed to generate valid JSON after {max_retries} attempts. Last error: {last_error}")


# ─────────────────────────────────────────
#  Save result to model.json
# ─────────────────────────────────────────
def ask_ai_and_save(user_input: str, output_path: str = "model.json") -> dict:
    user_input = preprocess_input(user_input)
    result = ask_ai(user_input)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[ask_ai] Saved to {output_path}")
    return result


# ─────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────
if __name__ == "__main__": # python runs this file -> true
    print("=== CAD AI JSON Generator ===")
    print("Describe the part you want to make :")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input(">>> ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        try:
            # 1. natural language -> JSON
            result = ask_ai_and_save(user_input)
            print("\nGenerated JSON:")
            print(json.dumps(result, ))

            # 2. JSON -> part.scadindent=2
            model = build(result)
            save_scad(model)

            # 3. Open part.scad in OpenSCAD (immediate)
            if os.path.exists(OPENSCAD_PATH):
                subprocess.Popen([OPENSCAD_PATH, "part.scad"])
                print("[ask_ai] OpenSCAD opened.")

                # 4. Generate STL in background (non-blocking)
                subprocess.Popen(
                    [OPENSCAD_PATH, "-o", "part.stl", "part.scad"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print("[ask_ai] STL generating in background. Check part.stl when ready.\n")
            else:
                print(f"OpenSCAD not found at {OPENSCAD_PATH}. Open part.scad manually.\n")

        except ValueError as e:
            print(f"[Error] {e}\n")
