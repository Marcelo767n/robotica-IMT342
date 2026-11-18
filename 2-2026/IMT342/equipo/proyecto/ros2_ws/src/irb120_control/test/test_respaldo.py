"""Copia de seguridad de módulos RAPID: solo GET, texto directo o por archivo temporal."""
import json
import tempfile
import unittest
from pathlib import Path

from irb120_control.respaldo import Fallo, Respaldo


class Response:
    def __init__(self, rows=None, status=200, content=None):
        self.status_code = status
        self.text = json.dumps({'_embedded': {'_state': rows or []}})
        self.content = content if content is not None else self.text.encode()


class Controller:
    def __init__(self):
        self.calls = []
        self.names = [('LabJointRws', 'ProgMod'), ('Module1', 'ProgMod'), ('BASE', 'SysMod')]

    def get(self, url, params=None, timeout=None, allow_redirects=None):
        assert allow_redirects is False
        path = url.replace('http://127.0.0.1', '')
        self.calls.append(('GET', path))
        if path == '/rw/system':
            return Response([{'_type': 'sys-system-li', 'name': '120-101516', 'rwversionname': '6.12.01.00'}])
        if path == '/rw/rapid/modules':
            return Response([{'_type': 'rap-module-info-li', 'name': n, 'type': t} for n, t in self.names])
        if path == '/rw/rapid/modules/LabJointRws':
            return Response([{'_type': 'rap-module-text', 'module-text': 'MODULE LabJointRws\nENDMODULE'}])
        if path == '/rw/rapid/modules/Module1':
            return Response([{'_type': 'rap-module-text', 'file-path': '"%2Fhd0a%2FTEMP_mod1.mod"'}])
        if path == '/fileservice/hd0a/TEMP_mod1.mod':
            return Response(content='MODULE Module1\nENDMODULE'.encode())
        if path == '/rw/rapid/modules/BASE':
            return Response([{'_type': 'rap-module-text', 'file-path': '"/etc/passwd"'}])
        return Response(status=404)

    def post(self, *args, **kwargs):
        raise AssertionError('El respaldo nunca hace POST')


class RespaldoTest(unittest.TestCase):
    def test_saves_modules_and_reports_failures(self):
        controller = Controller()
        with tempfile.TemporaryDirectory() as folder:
            manifest = Respaldo(controller, 'http://127.0.0.1').save(Path(folder))
            saved = {row['archivo'] for row in manifest['modulos']}
            self.assertEqual(saved, {'LabJointRws.mod', 'Module1.mod'})
            self.assertIn('MODULE Module1', (Path(folder) / 'Module1.mod').read_text())
            self.assertEqual(manifest['fallos'][0]['modulo'], 'BASE')  # ruta no reconocida: no se sigue
            self.assertTrue((Path(folder) / 'respaldo.json').exists())
        self.assertTrue(all(call[0] == 'GET' for call in controller.calls))
        self.assertNotIn(('GET', '/fileservice/etc/passwd'), controller.calls)

    def test_url_encoded_text_is_decoded(self):
        from irb120_control.respaldo import decode
        self.assertEqual(decode('%0aMODULE%20Module1%0a%0aENDMODULE'), '\nMODULE Module1\n\nENDMODULE')
        self.assertEqual(decode('MODULE A\n  x := 50%;\nENDMODULE'), 'MODULE A\n  x := 50%;\nENDMODULE')

    def test_rejects_odd_module_names(self):
        controller = Controller(); controller.names = [('../x', 'ProgMod')]
        with self.assertRaises(Fallo):
            Respaldo(controller, 'http://127.0.0.1').modules()


if __name__ == '__main__':
    unittest.main()
