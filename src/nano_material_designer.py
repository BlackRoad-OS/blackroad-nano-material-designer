#!/usr/bin/env python3
"""
BlackRoad Nano Material Designer
Production module for designing and simulating nano-scale materials.
"""

import sqlite3
import json
import math
import sys
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List

# ANSI Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
CYAN = '\033[0;36m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

DB_PATH = os.path.expanduser("~/.blackroad/nano_materials.db")


@dataclass
class NanoMaterial:
    name: str
    composition: str
    particle_size_nm: float
    surface_area: float  # m²/g
    conductivity: float  # S/m
    band_gap: float      # eV
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class SimulationResult:
    material_name: str
    original_band_gap: float
    quantum_corrected_band_gap: float
    surface_to_volume_ratio: float
    quantum_confinement_factor: float
    effective_conductivity: float
    stability_score: float
    notes: str
    simulated_at: str


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            composition TEXT NOT NULL,
            particle_size_nm REAL NOT NULL,
            surface_area REAL NOT NULL,
            conductivity REAL NOT NULL,
            band_gap REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT NOT NULL,
            original_band_gap REAL,
            quantum_corrected_band_gap REAL,
            surface_to_volume_ratio REAL,
            quantum_confinement_factor REAL,
            effective_conductivity REAL,
            stability_score REAL,
            notes TEXT,
            simulated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


class NanoMaterialDesigner:
    def __init__(self):
        init_db()
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def add_material(self, material: NanoMaterial) -> NanoMaterial:
        material.created_at = datetime.utcnow().isoformat()
        c = self.conn.cursor()
        try:
            c.execute("""
                INSERT INTO materials (name, composition, particle_size_nm,
                    surface_area, conductivity, band_gap, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (material.name, material.composition, material.particle_size_nm,
                  material.surface_area, material.conductivity, material.band_gap,
                  material.created_at))
            self.conn.commit()
            material.id = c.lastrowid
            print(f"{GREEN}✓ Added material: {material.name}{NC}")
        except sqlite3.IntegrityError:
            print(f"{YELLOW}⚠ Material '{material.name}' already exists{NC}")
        return material

    def simulate_properties(self, name: str) -> Optional[SimulationResult]:
        mat = self.get_material(name)
        if not mat:
            print(f"{RED}✗ Material not found: {name}{NC}")
            return None

        # Quantum confinement effect: Brus equation approximation
        # ΔE = (h²π²)/(2mr²) where r = particle_size/2
        hbar = 1.0546e-34  # J·s
        me = 9.109e-31     # kg
        eV = 1.602e-19     # J
        r = (mat.particle_size_nm * 1e-9) / 2.0
        # Effective mass approximation (0.1 * me for typical semiconductor)
        eff_mass = 0.1 * me
        delta_E = (hbar**2 * math.pi**2) / (2 * eff_mass * r**2 * eV)
        quantum_corrected_bg = mat.band_gap + delta_E * 0.001

        # Surface-to-volume ratio for sphere
        svr = 3.0 / (mat.particle_size_nm / 2.0)  # nm^-1

        # Quantum confinement factor (1 = bulk, >1 = confined)
        qcf = 1.0 + (0.5 / mat.particle_size_nm)

        # Effective conductivity with surface scattering correction
        mean_free_path_nm = 10.0
        surface_scattering = 1.0 / (1.0 + mean_free_path_nm / mat.particle_size_nm)
        eff_conductivity = mat.conductivity * surface_scattering

        # Stability score: larger particles = more stable, higher band gap = more stable
        stability = min(100.0, (mat.particle_size_nm * 2.0) + (mat.band_gap * 5.0))

        notes = []
        if mat.particle_size_nm < 5.0:
            notes.append("Strong quantum confinement regime")
        if mat.surface_area > 100:
            notes.append("High surface area - suitable for catalysis")
        if eff_conductivity > 1e5:
            notes.append("High conductivity - suitable for electronics")

        result = SimulationResult(
            material_name=name,
            original_band_gap=mat.band_gap,
            quantum_corrected_band_gap=round(quantum_corrected_bg, 4),
            surface_to_volume_ratio=round(svr, 4),
            quantum_confinement_factor=round(qcf, 4),
            effective_conductivity=round(eff_conductivity, 4),
            stability_score=round(stability, 2),
            notes="; ".join(notes) if notes else "Standard properties",
            simulated_at=datetime.utcnow().isoformat()
        )

        c = self.conn.cursor()
        c.execute("""
            INSERT INTO simulations (material_name, original_band_gap,
                quantum_corrected_band_gap, surface_to_volume_ratio,
                quantum_confinement_factor, effective_conductivity,
                stability_score, notes, simulated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (result.material_name, result.original_band_gap,
              result.quantum_corrected_band_gap, result.surface_to_volume_ratio,
              result.quantum_confinement_factor, result.effective_conductivity,
              result.stability_score, result.notes, result.simulated_at))
        self.conn.commit()
        return result

    def list_materials(self) -> List[NanoMaterial]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM materials ORDER BY created_at DESC")
        rows = c.fetchall()
        return [NanoMaterial(
            id=r["id"], name=r["name"], composition=r["composition"],
            particle_size_nm=r["particle_size_nm"], surface_area=r["surface_area"],
            conductivity=r["conductivity"], band_gap=r["band_gap"],
            created_at=r["created_at"]
        ) for r in rows]

    def get_material(self, name: str) -> Optional[NanoMaterial]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM materials WHERE name = ?", (name,))
        r = c.fetchone()
        if not r:
            return None
        return NanoMaterial(
            id=r["id"], name=r["name"], composition=r["composition"],
            particle_size_nm=r["particle_size_nm"], surface_area=r["surface_area"],
            conductivity=r["conductivity"], band_gap=r["band_gap"],
            created_at=r["created_at"]
        )

    def export_to_json(self, output_path: str = "/tmp/nano_materials_export.json"):
        materials = self.list_materials()
        data = {"materials": [asdict(m) for m in materials],
                "exported_at": datetime.utcnow().isoformat(),
                "total": len(materials)}
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"{GREEN}✓ Exported {len(materials)} materials to {output_path}{NC}")
        return output_path


def print_material(m: NanoMaterial):
    print(f"  {CYAN}{m.name}{NC} | {m.composition} | "
          f"{YELLOW}{m.particle_size_nm}nm{NC} | "
          f"BG: {m.band_gap}eV | σ: {m.conductivity} S/m")


def print_simulation(r: SimulationResult):
    print(f"\n{CYAN}=== Simulation: {r.material_name} ==={NC}")
    print(f"  Band Gap (original):  {r.original_band_gap} eV")
    print(f"  Band Gap (quantum):   {GREEN}{r.quantum_corrected_band_gap} eV{NC}")
    print(f"  Surface/Volume Ratio: {r.surface_to_volume_ratio} nm⁻¹")
    print(f"  Quantum Confinement:  {r.quantum_confinement_factor}x")
    print(f"  Eff. Conductivity:    {r.effective_conductivity} S/m")
    print(f"  Stability Score:      {r.stability_score}/100")
    print(f"  Notes: {YELLOW}{r.notes}{NC}")


def cmd_list(designer: NanoMaterialDesigner):
    materials = designer.list_materials()
    if not materials:
        print(f"{YELLOW}No materials found. Use 'add' to create one.{NC}")
        return
    print(f"\n{CYAN}=== Nano Materials ({len(materials)}) ==={NC}")
    for m in materials:
        print_material(m)


def cmd_add(designer: NanoMaterialDesigner, args: List[str]):
    if len(args) < 6:
        print(f"{RED}Usage: add <name> <composition> <size_nm> <surface_area> "
              f"<conductivity> <band_gap>{NC}")
        return
    m = NanoMaterial(name=args[0], composition=args[1],
                     particle_size_nm=float(args[2]), surface_area=float(args[3]),
                     conductivity=float(args[4]), band_gap=float(args[5]))
    designer.add_material(m)


def cmd_simulate(designer: NanoMaterialDesigner, args: List[str]):
    if not args:
        print(f"{RED}Usage: simulate <material_name>{NC}")
        return
    result = designer.simulate_properties(args[0])
    if result:
        print_simulation(result)


def main():
    designer = NanoMaterialDesigner()
    args = sys.argv[1:]
    if not args:
        print(f"{CYAN}BlackRoad Nano Material Designer{NC}")
        print("Commands: list, add, simulate, export")
        designer.close()
        return
    cmd = args[0]
    rest = args[1:]
    if cmd == "list":
        cmd_list(designer)
    elif cmd == "add":
        cmd_add(designer, rest)
    elif cmd == "simulate":
        cmd_simulate(designer, rest)
    elif cmd == "export":
        path = rest[0] if rest else "/tmp/nano_materials_export.json"
        designer.export_to_json(path)
    else:
        print(f"{RED}Unknown command: {cmd}{NC}")
    designer.close()


if __name__ == "__main__":
    main()
