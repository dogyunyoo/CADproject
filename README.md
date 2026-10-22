# CADproject (OpenSCAD)
version.1

# AI-Assisted Parametric CAD Generation

A Python-based system that converts natural-language engineering descriptions into parametric 3D CAD models using an LLM API, a structured JSON representation, and OpenSCAD.

**Developer:** Dogyun Yoo  
**Started:** June 2026  
**Status:** Active Development

## 1. Overview
This project explores the automation of parametric CAD generation from natural-language engineering requirements.

Instead of manually writing OpenSCAD code, users can describe a mechanical component in plain English. The system converts the description into a structured JSON specification, validates the generated parameters, and produces an OpenSCAD model for visualization and STL export.

The project focuses on combining LLM-assisted generation with rule-based geometry processing and engineering calculations.

## 2. System Architecture
Natural Language Input -> Input Processing (Unit Conversion / Gear Hints) -> Claude API -> Structured CAD JSON -> JSON Validator (access pass or fail)

-> CAD Geometry Builder -> OpenSCAD (.scad) & STL Export (.stl)

## 3. Key Features
### Natural-Language CAD Generation

- Converts engineering descriptions into structured CAD parameters using the Claude API.
- Uses a custom CAD JSON specification.
- Supports input preprocessing, including inch-to-millimeter conversion and gear parameter hints.

### JSON Validation

- Checks generated JSON against supported CAD structures and parameter requirements.
- Provides error feedback and retries generation when validation fails.
- Separates LLM-generated specifications from downstream CAD construction.

### Parametric Mechanical Components

The project includes support for several mechanical features, including:

- Plates and cylinders
- Hex bolts, nuts, and washers
- Through-holes, countersunk holes, and slots
- Chamfered and filleted boxes
- Boolean and geometric transformations
- Gear-related parameters and assembly calculations

### Gear-Solving Module

The dedicated `gear_solver.py` module provides calculations for mechanical gear configurations, including:

- Gear parameters estimated from a target outer diameter
- Spur gear center distance
- Gear orientation and phase alignment
- Worm gear placement and alignment calculations
- Unit conversions

Some gear alignment configurations use heuristics or require manual adjustments.

## Supported Mechanical Components

## 4. Example Outputs
The following examples demonstrate different CAD generation and mechanical modeling capabilities.

### Example 1: L-Bracket

![Generated L-Bracket](Example%201_Lbracket.png)

A parametric mounting bracket demonstrating basic geometric operations, hole placement, and Boolean subtraction.

### Example 2: Spur Gear Pair

![Generated Spur Gear Pair](Example%202.png)

A two-gear assembly demonstrating parametric gear geometry and center-distance calculations.

### Example 3: Worm Gear Assembly

![Generated Worm Gear Assembly](Example%203.png)

A worm gear arrangement demonstrating geometric positioning, axis alignment, and rotation calculations.

### Example 4: Rack and Pinion

![Generated Rack and Pinion](Example%204.png)

A rack-and-pinion configuration demonstrating parametric gear components and their spatial arrangement.

### Example 5: Mechanical Plate

![Generated Mechanical Plate](Example%205.png)

A mechanical plate demonstrating features such as mounting holes, countersinks, and fastening geometry.

## 5. Installation & Requirements
### Requirements

- Python
- OpenSCAD
- BOSL2 for supported gear-related functionality
- Anthropic API key

Install the required Python packages:

```bash
pip install anthropic python-dotenv
```

Install OpenSCAD and configure BOSL2 according to its documentation.

### API Configuration

Create a `.env` file in the project directory:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

**Never commit your actual API key to GitHub.**

The current implementation expects OpenSCAD at:

```text
C:\Program Files\OpenSCAD\openscad.exe
```

Users with a different installation path must update `OPENSCAD_PATH` in `ask_ai.py`.

## 6. Usage
Run the interactive CAD generator:

```bash
python ask_ai.py
```

Enter a natural-language description of the desired component.

The system attempts to generate and validate a CAD JSON specification, writes `model.json`, and generates `part.scad`.

If OpenSCAD is found at the configured executable path, the script opens the model and launches STL generation in the background.

**Note:** STL export may continue after the command returns. Check that `part.stl` has been generated successfully before using it.

## 7. Validation & Error Handling
LLM-generated CAD descriptions may contain invalid JSON, missing parameters, or unsupported structures.

To reduce these failures, the system:

1. Parses the generated JSON.
2. Checks its structure using `validator.py`.
3. Returns validation errors to the LLM.
4. Retries generation up to a configured limit.
5. Passes validated output to the CAD builder.

This approach aims to improve the structural reliability of LLM-generated CAD specifications.

## 8. Limitations
- The system relies on an external LLM API and internet connectivity.
- Geometric correctness is not guaranteed by JSON validation alone.
- Some gear configurations use heuristic alignment.
- OpenSCAD currently uses a Windows-specific executable path.
- STL export runs asynchronously without a completed-export verification step.
- Physical manufacturability and mechanical performance are not automatically verified.

## 9. Future Development
Planned improvements include:

- Automated geometric validation of generated CAD models
- More robust gear meshing and assembly verification
- Cross-platform OpenSCAD execution
- Improved automated testing and error recovery
- Expansion of parametric mechanical components
- Benchmarking CAD generation accuracy and reliability

## 10. Technologies
**Language:** Python  
**LLM:** Anthropic Claude API  
**CAD Engine:** OpenSCAD  
**Geometry Library:** BOSL2  
**Data Representation:** JSON

## 11. Project Background
This project was initiated in June 2026 as an independent engineering software development project.

Its long-term objective is to investigate how AI-assisted specification generation, parametric geometry, and rule-based engineering computations can support more automated mechanical design workflows.

