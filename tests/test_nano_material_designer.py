#!/usr/bin/env python3
"""Tests for BlackRoad Nano Material Designer."""

import os
import sys
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import nano_material_designer as nmd


def _make_tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return f.name


class TestNanoMaterialDataclass(unittest.TestCase):
    def test_defaults_are_none(self):
        m = nmd.NanoMaterial(
            name="T", composition="TiO2",
            particle_size_nm=5.0, surface_area=200.0,
            conductivity=1e4, band_gap=3.2,
        )
        self.assertIsNone(m.id)
        self.assertIsNone(m.created_at)

    def test_simulation_result_fields(self):
        r = nmd.SimulationResult(
            material_name="X", original_band_gap=1.1,
            quantum_corrected_band_gap=1.5, surface_to_volume_ratio=0.6,
            quantum_confinement_factor=1.1, effective_conductivity=5000.0,
            stability_score=75.0, notes="ok", simulated_at="2024-01-01",
        )
        self.assertEqual(r.stability_score, 75.0)
        self.assertEqual(r.notes, "ok")


class TestInitDb(unittest.TestCase):
    def test_tables_created(self):
        path = _make_tmp_db()
        try:
            nmd.DB_PATH = path
            nmd.init_db()
            conn = sqlite3.connect(path)
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            conn.close()
            self.assertIn("materials", tables)
            self.assertIn("simulations", tables)
        finally:
            os.unlink(path)

    def test_init_idempotent(self):
        path = _make_tmp_db()
        try:
            nmd.DB_PATH = path
            nmd.init_db()
            nmd.init_db()  # second call must not raise
        finally:
            os.unlink(path)


class TestNanoMaterialDesigner(unittest.TestCase):
    def setUp(self):
        self.path = _make_tmp_db()
        nmd.DB_PATH = self.path
        self.d = nmd.NanoMaterialDesigner()

    def tearDown(self):
        self.d.close()
        os.unlink(self.path)

    def _mat(self, name="Silver NP"):
        return nmd.NanoMaterial(
            name=name, composition="Ag",
            particle_size_nm=10.0, surface_area=50.0,
            conductivity=6.3e7, band_gap=0.1,
        )

    def test_add_material_assigns_id(self):
        m = self.d.add_material(self._mat())
        self.assertIsNotNone(m.id)
        self.assertGreater(m.id, 0)

    def test_add_material_sets_created_at(self):
        m = self.d.add_material(self._mat())
        self.assertIsNotNone(m.created_at)

    def test_add_duplicate_no_exception(self):
        self.d.add_material(self._mat("Dup"))
        self.d.add_material(self._mat("Dup"))  # should warn, not raise

    def test_get_material_roundtrip(self):
        self.d.add_material(self._mat("QD-CdSe"))
        fetched = self.d.get_material("QD-CdSe")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.composition, "Ag")
        self.assertEqual(fetched.particle_size_nm, 10.0)

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(self.d.get_material("ghost"))

    def test_list_empty(self):
        self.assertEqual(self.d.list_materials(), [])

    def test_list_after_adds(self):
        self.d.add_material(self._mat("M1"))
        self.d.add_material(self._mat("M2"))
        self.assertEqual(len(self.d.list_materials()), 2)

    def test_simulate_computes_quantum_correction(self):
        self.d.add_material(nmd.NanoMaterial(
            name="GaAs", composition="GaAs",
            particle_size_nm=8.0, surface_area=120.0,
            conductivity=1e4, band_gap=1.42,
        ))
        r = self.d.simulate_properties("GaAs")
        self.assertIsNotNone(r)
        self.assertGreater(r.quantum_corrected_band_gap, r.original_band_gap)
        self.assertGreater(r.surface_to_volume_ratio, 0)

    def test_simulate_nonexistent_returns_none(self):
        self.assertIsNone(self.d.simulate_properties("nope"))

    def test_strong_confinement_note_for_tiny_particle(self):
        self.d.add_material(nmd.NanoMaterial(
            name="TinyQD", composition="CdS",
            particle_size_nm=2.0, surface_area=500.0,
            conductivity=1.0, band_gap=2.5,
        ))
        r = self.d.simulate_properties("TinyQD")
        self.assertIn("quantum confinement", r.notes.lower())

    def test_stability_score_bounded(self):
        self.d.add_material(self._mat("BigPart"))
        r = self.d.simulate_properties("BigPart")
        self.assertLessEqual(r.stability_score, 100.0)
        self.assertGreaterEqual(r.stability_score, 0.0)

    def test_export_json_structure(self):
        self.d.add_material(self._mat("ExportMat"))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            self.d.export_to_json(path)
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["total"], 1)
            self.assertIn("materials", data)
            self.assertIn("exported_at", data)
        finally:
            os.unlink(path)

    def test_export_empty_db(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            self.d.export_to_json(path)
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["total"], 0)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
