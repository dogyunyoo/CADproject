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

## 6. Installation & Requirements
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
## Usage

## Validation & Error Handling
## Limitations
## Future Development
