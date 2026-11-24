"""Modelo puro (sin Tk) de la pestaña Validación: lee los CSV del Hito 3 y prepara tablas, resumen y detalle."""
import csv
import os
from pathlib import Path
import re
import subprocess
import sys

try:
    from irb120_conexion.rutas import PROJECT
except Exception:  # fuera del árbol del proyecto
    PROJECT = Path(__file__).resolve().parents[5]

ESTADOS = ('verificado', 'parcial', 'fallido', 'no ejecutado', 'bloqueado')
NIVELES = ('S0', 'S1', 'S2', 'S3')
TIMEOUT_S = 120

# clave -> (título, archivo CSV, [(título de columna, [alias posibles], ancho)], [figuras])
BLOQUES = {
    'fk': ('FK (P1)', 'P1_fk.csv',
           [('Caso', ['ID'], 90), ('Fuente', ['Ref/Src'], 150), ('e_p [m]', ['e_p_m'], 85),
            ('e_R [rad]', ['e_R_rad'], 85)],
           ['fk_real_errores_N1_N2.png', 'fk_d_tcp_d_ord.png', 'fk_fuera_diagnostico.png']),
    'ik': ('IK (P2)', 'P2_ik.csv',
           [('Pose', ['ID_pose'], 60), ('Rama', ['rama'], 62), ('Configuración', ['config'], 185),
            ('e_p [m]', ['e_p_propia_m'], 85), ('e_R [rad]', ['e_R_propia_rad'], 85),
            ('Solución', ['estado_solucion'], 120)],
           ['ik_ramas_residuos.png']),
    'jac': ('Jacobiano (P3)', 'P3_jacobiano.csv',
            [('Caso', ['ID'], 110), ('eJv [m/rad]', ['eJv_m_rad'], 100), ('eJw [rad/rad]', ['eJw_rad_rad'], 105),
             ('Paso h', ['h_error_FD'], 120)],
            ['jacobiano_errores_separados.png', 'jacobiano_fd_curva_visual4.png']),
    'sing': ('Singularidad (P4)', 'P4_singularidad.csv',
             [('Caso', ['ID'], 90), ('Subespacio', ['subespacio'], 120), ('Rango', ['r_max'], 62),
              ('σmín/σmáx', ['sigma_min_sobre_max'], 95), ('Efecto en velocidad', ['efecto_velocidad'], 200)],
             ['singularidad_svd_tau.png']),
    'todos': ('Todos los casos', 'validation_cases.csv',
              [('Caso', ['case_id'], 110), ('Tipo', ['case_type'], 190), ('e_p [m]', ['position_error_m'], 85),
               ('e_R [rad]', ['orientation_error_rad'], 85)],
              []),
}
ORDEN = ('fk', 'ik', 'jac', 'sing', 'todos')
ALIAS_ID = ('ID', 'ID_pose', 'case_id')
ALIAS_ESTADO = ('Decision', 'decision', 'acceptance_result', 'estado_P5')


def descubrir_carpeta(carpeta=None):
    """Carpeta hito3/ (con resultados/ dentro): argumento, IRB120_HITO3 o PROJECT/hito3."""
    for c in (carpeta, os.environ.get('IRB120_HITO3')):
        if c:
            return Path(c)
    return Path(PROJECT) / 'hito3'


def leer_csv(ruta):
    """Lista de dicts; [] si el archivo no existe o está dañado (nunca lanza)."""
    try:
        with open(ruta, newline='', encoding='utf-8') as f:
            return [{(k or '').strip(): (v or '').strip() for k, v in fila.items() if k is not None}
                    for fila in csv.DictReader(f)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def normalizar_estado(texto):
    t = (texto or '').strip().lower()
    for clave, estado in (('verific', 'verificado'), ('parcial', 'parcial'), ('fall', 'fallido'),
                          ('bloque', 'bloqueado'), ('no ejec', 'no ejecutado'), ('pendiente', 'no ejecutado'),
                          ('no alcanz', 'no ejecutado')):
        if clave in t:
            return estado
    return ''


def nivel_de(texto):
    m = re.search(r'S[0-3]', texto or '')
    return m.group(0) if m else ''


def numero(texto, max_car=60):
    """Formato compacto: números a 4 cifras significativas, texto recortado."""
    s = (texto or '').strip()
    try:
        x = float(s)
    except ValueError:
        s = s.replace('\n', ' ')
        return s if len(s) <= max_car else s[:max_car - 1] + '…'
    if x == 0:
        return '0'
    return f'{x:.2e}' if abs(x) < 1e-3 or abs(x) >= 1e5 else f'{x:.4g}'


def candidatos_id(ident):
    """FK-L1 → FK-L; J-N1-tcp → J-N1: ids de caso a probar, del más al menos específico."""
    vistos, sal = set(), []
    for c in (ident, ident.rsplit('-', 1)[0] if '-' in ident else '', re.sub(r'\d+$', '', ident)):
        if c and c not in vistos:
            vistos.add(c)
            sal.append(c)
    return sal


class Fila:
    def __init__(self, ident, caso, celdas, estado, nivel, crudo):
        self.id, self.caso, self.celdas, self.estado, self.nivel, self.crudo = ident, caso, celdas, estado, nivel, crudo


class Tabla:
    def __init__(self, titulo, columnas, filas, figuras):
        self.titulo, self.columnas, self.filas, self.figuras = titulo, columnas, filas, figuras


class Modelo:
    """Resultados cargados de una carpeta hito3/. `hay_datos` es False si no hay ninguno de los CSV."""

    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        self.res = self.carpeta / 'resultados'
        self.casos = {}                  # case_id -> fila de casos_estado_evidencia.csv
        self.tablas = {}
        self.cargar()

    @property
    def hay_datos(self):
        return bool(self.casos) or any(t.filas for t in self.tablas.values())

    def cargar(self):
        self.casos = {}
        for f in leer_csv(self.res / 'casos_estado_evidencia.csv'):
            if f.get('case_id'):
                self.casos[f['case_id']] = f
        self.tablas = {c: self._tabla(c) for c in ORDEN}

    def _tabla(self, clave):
        titulo, archivo, cols, figs = BLOQUES[clave]
        filas_csv = leer_csv(self.res / archivo)
        presentes = [c for c in cols if any(a in f for f in filas_csv[:1] for a in c[1])] if filas_csv else []
        columnas = [('Estado', 100), ('Nivel', 58)] + [(t, w) for t, _a, w in presentes]
        filas = []
        for crudo in filas_csv:
            ident = next((crudo[k] for k in ALIAS_ID if crudo.get(k)), '')
            caso = next((c for c in candidatos_id(ident) if c in self.casos), '')
            datos = self.casos.get(caso, {})
            estado = normalizar_estado(datos.get('estado_P5')) or normalizar_estado(
                next((crudo[k] for k in ALIAS_ESTADO if crudo.get(k)), ''))
            nivel = nivel_de(datos.get('nivel_evidencia', ''))
            celdas = [estado or '—', nivel or '—']
            for _t, alias, _w in presentes:
                celdas.append(numero(next((crudo[a] for a in alias if crudo.get(a)), '')) or '—')
            filas.append(Fila(ident, caso, celdas, estado, nivel, crudo))
        figuras = [self.res / 'figuras' / f for f in figs]
        return Tabla(titulo, columnas, filas, [p for p in figuras if p.is_file()])

    def resumen(self):
        """(contadores de estado P5, contadores de nivel S0–S3) sobre casos_estado_evidencia.csv."""
        est = {e: 0 for e in ESTADOS}
        niv = {n: 0 for n in NIVELES}
        for c in self.casos.values():
            e = normalizar_estado(c.get('estado_P5'))
            if e:
                est[e] += 1
            n = nivel_de(c.get('nivel_evidencia'))
            if n:
                niv[n] += 1
        return est, niv

    def manifiesto(self, caso):
        if not caso:
            return None
        ruta = self.carpeta / 'manifiestos' / f'{caso}.yaml'
        try:
            return ruta.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            return None

    def detalle(self, fila):
        """Texto del panel de detalle de una fila: motivo, evidencia, datos de la fila y manifiesto YAML."""
        c = self.casos.get(fila.caso, {})
        t = [f'Caso: {fila.id}' + (f'   (manifiesto {fila.caso})' if fila.caso and fila.caso != fila.id else ''),
             f'Estado P5: {fila.estado or "sin estado"}   ·   Evidencia: {c.get("nivel_evidencia") or "—"}']
        if c.get('tipo'):
            t.append(f'Tipo: {c["tipo"]}')
        if c.get('justificacion'):
            t += ['', 'Motivo / justificación:', c['justificacion']]
        extra = [f'  {k}: {v}' for k, v in fila.crudo.items() if v and len(v) < 160]
        if extra:
            t += ['', 'Datos de la fila:'] + extra
        man = self.manifiesto(fila.caso)
        t += ['', 'Manifiesto (hito3/manifiestos/%s.yaml):' % fila.caso if man else
              'Manifiesto: no existe para este caso.']
        if man:
            t.append(man.rstrip())
        return '\n'.join(t)


def ejecutar_validacion(carpeta_hito3, timeout=TIMEOUT_S):
    """Corre `python3 -m hito3.validacion` con cwd = proyecto (padre de hito3/). (ok, salida corta). No lanza."""
    raiz = Path(carpeta_hito3).resolve().parent
    try:
        r = subprocess.run([sys.executable if sys.executable else 'python3', '-m', 'hito3.validacion'], cwd=raiz,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f'Tiempo agotado ({timeout} s).'
    except OSError as exc:
        return False, f'No se pudo ejecutar: {exc}'
    salida = ((r.stdout or '') + (r.stderr or '')).strip()
    return r.returncode == 0, salida[-1500:] if salida else f'código {r.returncode}'
