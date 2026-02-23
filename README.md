# blackroad-nano-material-designer

A production-grade Python module for designing, cataloguing, and simulating nano-scale materials. Built for materials scientists and AI-driven lab automation, it combines a persistent SQLite store with quantum-physics calculations to give accurate predictions of nano-particle properties at scale.

The core simulation engine implements a Brus-equation approximation to model quantum confinement effects, surface-to-volume ratios, and conductivity corrections due to surface scattering. Results are graded with a stability score that factors in particle size and band-gap energy, making it straightforward to rank candidate materials before committing to physical synthesis.

Part of the **BlackRoad OS** developer toolchain — every command is scriptable, all data lives in a local SQLite database, and the JSON export format is ready for downstream ML pipelines.

## Features

- **Material registry** — add and query nano-materials (name, composition, particle size, surface area, conductivity, band gap)
- **Quantum simulation** — Brus-equation band-gap correction, surface-to-volume ratio, quantum confinement factor, effective conductivity
- **Stability scoring** — 0–100 score derived from particle size and band gap
- **Anomaly notes** — automatic flags for strong quantum confinement, high surface area, high conductivity regimes
- **JSON export** — dump entire material library with simulation metadata
- **SQLite persistence** — zero-config local database at `~/.blackroad/nano_materials.db`
- **CLI interface** — scriptable commands: `list`, `add`, `simulate`, `export`

## Installation

```bash
# Clone and install (stdlib only — no extra deps required)
git clone https://github.com/BlackRoad-OS/blackroad-nano-material-designer.git
cd blackroad-nano-material-designer
python3 src/nano_material_designer.py
```

Run the test suite:

```bash
pip install pytest
pytest tests/ -v
```

## Usage

```bash
# List all stored materials
python3 src/nano_material_designer.py list

# Add a material: name composition size_nm surface_area conductivity band_gap
python3 src/nano_material_designer.py add "CdSe-QD" "CdSe" 3.5 450.0 1.2 1.74

# Add a bulk silver nanoparticle
python3 src/nano_material_designer.py add "Ag-NP" "Ag" 20.0 25.0 63000000 0.0

# Run quantum simulation on a material
python3 src/nano_material_designer.py simulate "CdSe-QD"

# Export entire library to JSON
python3 src/nano_material_designer.py export /tmp/materials.json
```

### Example simulation output

```
=== Simulation: CdSe-QD ===
  Band Gap (original):  1.74 eV
  Band Gap (quantum):   2.0312 eV
  Surface/Volume Ratio: 0.5714 nm⁻¹
  Quantum Confinement:  1.1429x
  Eff. Conductivity:    0.6667 S/m
  Stability Score:      15.7/100
  Notes: Strong quantum confinement regime; High surface area - suitable for catalysis
```

## API

### `NanoMaterial`
Dataclass representing a material entry:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Unique material name |
| `composition` | `str` | Chemical formula |
| `particle_size_nm` | `float` | Diameter in nanometres |
| `surface_area` | `float` | BET surface area m²/g |
| `conductivity` | `float` | Electrical conductivity S/m |
| `band_gap` | `float` | Band gap in eV |

### `NanoMaterialDesigner`

| Method | Description |
|---|---|
| `add_material(m)` | Persist a `NanoMaterial` to the database |
| `get_material(name)` | Retrieve by name, or `None` |
| `list_materials()` | All materials ordered by creation date |
| `simulate_properties(name)` | Run quantum simulation, return `SimulationResult` |
| `export_to_json(path)` | Export library to JSON file |

## License

MIT © BlackRoad OS, Inc.
