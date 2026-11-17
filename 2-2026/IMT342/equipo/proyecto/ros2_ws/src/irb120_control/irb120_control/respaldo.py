"""Copia de seguridad de los módulos RAPID del controlador (solo lectura por RWS).

    ./brazo.sh respaldar

Guarda cada módulo de la tarea T_ROB1 (programa y sistema) con su huella SHA-256 en
ros2_ws/src/irb120_control/rapid/respaldo_controlador/<fecha>/ para versionarlo en git.
Solo hace GET: no pide mastership ni RMMP, no cambia modo, motores, puntero ni ejecución.
No sustituye la copia completa del sistema desde el FlexPendant (Copia de seguridad y
restauración), que además guarda configuración, calibración y RobotWare.
"""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

from irb120_conexion.comunicacion.lectura_rws import error_details, state_records
from irb120_conexion.nodos.lectura_articular.puente_rws import build_base_url

TASK = 'T_ROB1'
DEFAULT_DIR = Path(__file__).resolve().parents[1] / 'rapid/respaldo_controlador'
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}')
TEMP = re.compile(r'/hd0a/TEMP[A-Za-z0-9_.-]+')
MAX_BYTES = 2_000_000


class Fallo(Exception):
    pass


class Respaldo:
    def __init__(self, session, base, timeout=5.):
        self.session, self.base, self.timeout = session, base, timeout

    def get(self, path, **params):
        response = self.session.get(self.base + path, params={'json': '1', **params},
                                    timeout=self.timeout, allow_redirects=False)
        if response.status_code != 200:
            raise Fallo(f'GET {path}: HTTP {response.status_code}; {error_details(response.text)}')
        return state_records(response.text)

    def identity(self):
        row = next((r for r in self.get('/rw/system') if r.get('_type') == 'sys-system-li'), {})
        return {'name': row.get('name'), 'rwversionname': row.get('rwversionname')}

    def modules(self):
        rows = self.get('/rw/rapid/modules', task=TASK)
        result = []
        for row in rows:
            name = row.get('name', '')
            if not NAME.fullmatch(name):
                raise Fallo(f'Nombre de módulo inesperado: {name!r}')
            result.append({'name': name, 'type': row.get('type', '')})
        return result

    def text(self, name):
        """Texto del módulo: en RW6 llega directo o como archivo temporal en /hd0a/TEMP…"""
        if not NAME.fullmatch(name):
            raise Fallo(f'Nombre de módulo inesperado: {name!r}')
        for row in self.get(f'/rw/rapid/modules/{name}', resource='module-text', task=TASK):
            if 'module-text' in row:
                return row['module-text']
            if 'file-path' not in row:
                continue
            path = unquote(row['file-path']).strip('"')
            if not TEMP.fullmatch(path):
                raise Fallo(f'Ruta temporal no reconocida para {name}.')
            for resource in ('/fileservice' + path, '/fileservice/' + path):
                response = self.session.get(self.base + resource, timeout=self.timeout, allow_redirects=False)
                if response.status_code == 404:
                    continue
                if response.status_code != 200:
                    raise Fallo(f'GET del temporal de {name}: HTTP {response.status_code}')
                if len(response.content) > MAX_BYTES:
                    raise Fallo(f'{name} supera {MAX_BYTES} bytes.')
                try:
                    return response.content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    return response.content.decode('latin-1')
            raise Fallo(f'No se pudo leer el temporal de {name}.')
        raise Fallo(f'La respuesta de {name} no trae texto ni archivo temporal.')

    def save(self, folder):
        folder.mkdir(parents=True, exist_ok=True)
        manifest = {'creado_utc': datetime.now(timezone.utc).isoformat(), 'tarea': TASK,
                    'controlador': self.identity(), 'modulos': [], 'fallos': []}
        for module in self.modules():
            try:
                source = self.text(module['name'])
            except Fallo as exc:
                manifest['fallos'].append({'modulo': module['name'], 'error': str(exc)})
                continue
            suffix = '.sys' if 'sys' in module['type'].lower() else '.mod'
            path = folder / (module['name'] + suffix)
            path.write_text(source, encoding='utf-8')
            manifest['modulos'].append({'modulo': module['name'], 'tipo': module['type'], 'archivo': path.name,
                                        'lineas': source.count('\n') + 1,
                                        'sha256': hashlib.sha256(source.encode()).hexdigest()})
        (folder / 'respaldo.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                                              encoding='utf-8')
        return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', default='192.168.125.1')
    parser.add_argument('--user', default='Default User')
    parser.add_argument('--http-port', type=int, default=80, help='Distinto de 80 solo en 127.0.0.1')
    parser.add_argument('--salida', type=Path, help='Carpeta destino (por defecto rapid/respaldo_controlador/<fecha>)')
    args = parser.parse_args(argv)
    try:
        base = build_base_url(args.host, args.http_port)
    except ValueError as exc:
        parser.error(str(exc))
    folder = args.salida or DEFAULT_DIR / datetime.now().strftime('%Y-%m-%d_%H%M')
    import requests
    from requests.auth import HTTPDigestAuth
    password = getpass.getpass(f'Contraseña RWS de "{args.user}" (solo lectura, no se guarda): ')
    with requests.Session() as session:
        session.trust_env = False
        session.auth = HTTPDigestAuth(args.user, password)
        try:
            manifest = Respaldo(session, base).save(folder)
        except (Fallo, requests.RequestException, OSError) as exc:
            print('DETENIDO:', exc)
            return 2
        finally:
            try:
                session.get(base + '/logout', timeout=2., allow_redirects=False)
            except Exception:
                pass
    print(f"Controlador {manifest['controlador']['name']} | RobotWare {manifest['controlador']['rwversionname']}")
    for row in manifest['modulos']:
        print(f"  {row['archivo']:<24} {row['lineas']:>5} líneas  {row['sha256'][:16]}…")
    for row in manifest['fallos']:
        print(f"  NO GUARDADO {row['modulo']}: {row['error']}")
    print('Carpeta:', folder)
    print('SOLO LECTURA: no se cambió nada en el controlador. Añadir la carpeta a git para conservarla.')
    return 0 if not manifest['fallos'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
