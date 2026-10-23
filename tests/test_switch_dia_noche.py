"""
Pruebas unitarias para el widget SwitchDiaNoche y la integración de temas.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from ui.switch_dia_noche import SwitchDiaNoche
from web.app import app


class TestSwitchDiaNoche(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_switch_initial_state(self):
        switch_day = SwitchDiaNoche(checked=False)
        self.assertFalse(switch_day.isChecked())
        self.assertEqual(switch_day.progreso, 0.0)

        switch_night = SwitchDiaNoche(checked=True)
        self.assertTrue(switch_night.isChecked())
        self.assertEqual(switch_night.progreso, 1.0)

    def test_switch_toggle(self):
        switch = SwitchDiaNoche(checked=False)
        toggled_values = []
        switch.toggled.connect(lambda val: toggled_values.append(val))

        switch.toggle()
        self.assertTrue(switch.isChecked())
        self.assertEqual(toggled_values, [True])

        switch.toggle()
        self.assertFalse(switch.isChecked())
        self.assertEqual(toggled_values, [True, False])

    def test_switch_anima_el_progreso_antes_de_completar(self):
        switch = SwitchDiaNoche(checked=False)
        animaciones_finalizadas = []
        switch.animationFinished.connect(animaciones_finalizadas.append)
        switch.show()

        switch.toggle()
        QTest.qWait(120)
        self.assertGreater(switch.progreso, 0.0)
        self.assertLess(switch.progreso, 1.0)
        self.assertEqual(animaciones_finalizadas, [])

        QTest.qWait(450)
        self.assertEqual(switch.progreso, 1.0)
        self.assertEqual(animaciones_finalizadas, [True])

    def test_web_routes_and_static_switch_assets(self):
        client = app.test_client()
        rutas = [
            '/',
            '/inventario',
            '/pos',
            '/reportes',
            '/static/css/switch.css',
            '/static/css/accessibility.css',
            '/static/img/cloud_1.svg',
            '/static/img/cloud_2.svg',
            '/static/img/cloud_3.svg',
            '/static/img/cloud_4.svg',
            '/static/img/stars.svg',
        ]
        for r in rutas:
            res = client.get(r)
            self.assertEqual(res.status_code, 200, f"Error en ruta: {r}")

    def test_web_pages_include_accessibility_landmarks_and_styles(self):
        client = app.test_client()
        for ruta in ('/', '/inventario', '/pos', '/reportes'):
            response = client.get(ruta)
            html = response.get_data(as_text=True)
            self.assertIn('class="skip-link"', html)
            self.assertIn('id="main-content"', html)
            self.assertIn('/static/css/accessibility.css', html)
            self.assertIn('</style>', html)

    def test_switch_exposes_accessible_name_and_keyboard_instructions(self):
        switch = SwitchDiaNoche()
        self.assertTrue(switch.accessibleName())
        self.assertIn("Espacio", switch.accessibleDescription())
        QTest.keyClick(switch, Qt.Key_Space)
        self.assertTrue(switch.isChecked())


if __name__ == '__main__':
    unittest.main()
