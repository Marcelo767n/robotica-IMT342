"""Matemática del Hito 2 como bloques LaTeX para proyectar. Puro salvo matplotlib (sin tkinter).

Cada `bloques_*` recibe valores actuales y devuelve `Bloque`s (título, LaTeX, explicación breve).
`figura_bloque` dibuja el LaTeX con usetex si funciona; si no, con un respaldo mathtext que
dibuja matrices/tablas a mano (mathtext no admite bmatrix). Unidades: ángulos en °, posiciones
en mm (matrices homogéneas), M en kg·m², τ en N·m.
"""
import io
import os
import re
import shutil
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from irb120_control.analisis.modelo import hito2

SIGMA_AVISO = 0.04
SIGMA_BLOQUEO = 0.02
PREAMBULO = r'\usepackage{amsmath,bm}\setlength{\arraycolsep}{7pt}\renewcommand{\arraystretch}{1.2}'
CLARO = ('#111827', '#ffffff')    # (texto, fondo)
OSCURO = ('#f3f4f6', '#1f2937')
DPI = 100


@dataclass
class Bloque:
    titulo: str
    latex: str
    explicacion: str


# ---------------------------------------------------------------- formato

def _n(x, dec=3):
    s = f'{float(x):.{dec}f}'
    return s[1:] if s.startswith('-') and float(s) == 0.0 else s


def _mat(m, dec=3, entorno='bmatrix'):
    m = np.atleast_2d(np.asarray(m, dtype=float))
    filas = r' \\ '.join(' & '.join(_n(v, dec) for v in fila) for fila in m)
    return rf'\begin{{{entorno}}} {filas} \end{{{entorno}}}'


def _col(v, dec=3):
    return _mat(np.asarray(v, dtype=float).reshape(-1, 1), dec)


def _homogenea_mm(T):
    T = np.array(T, dtype=float)
    T[:3, 3] *= 1000.0
    return T


def _sci(x, dec=3):
    m, e = f'{float(x):.{dec}e}'.split('e')
    return rf'{m}\times 10^{{{int(e)}}}'


def _par(x, dec=2):
    return f'({_n(x, dec)})' if x < 0 else _n(x, dec)


# ---------------------------------------------------------------- bloques

def bloques_cinematica(q_deg, herramienta='tcp'):
    h = hito2()
    dh = h['dh']
    q = np.deg2rad(np.asarray(q_deg, dtype=float))
    filas = []
    for i, (p, qi) in enumerate(zip(dh.DH_PARAMETERS, np.asarray(q_deg, dtype=float)), 1):
        off = int(round(np.rad2deg(p.theta_offset_rad)))
        form = rf'q_{i}' + (f'{off:+d}^\\circ' if off else '')
        theta = qi + off
        filas.append(' & '.join([str(i), _n(p.a_m * 1000, 0), _n(np.rad2deg(p.alpha_rad), 0),
                                 _n(p.d_m * 1000, 0), form, _n(theta, 2)]))
    tabla = (r'\begin{array}{c|ccccc} i & a_i\,[\mathrm{mm}] & \alpha_i\,[^\circ] & '
             r'd_i\,[\mathrm{mm}] & \theta_i & \theta_i\,[^\circ] \\ \hline '
             + r' \\ '.join(filas) + r' \end{array}')
    out = [Bloque('Tabla Denavit-Hartenberg', tabla,
                  'Parámetros DH clásicos del IRB 120. θ_i = q_i más un desfase fijo en los ejes 2 (−90°) y 6 (+180°); '
                  'los valores de θ_i se calculan con la pose actual.')]
    s = r'\sin'
    general = (r'{}^{i-1}A_i=R_z(\theta_i)\,T_z(d_i)\,T_x(a_i)\,R_x(\alpha_i)=\begin{bmatrix} '
               r'\cos\theta_i & -\sin\theta_i\cos\alpha_i & \sin\theta_i\sin\alpha_i & a_i\cos\theta_i \\ '
               r'\sin\theta_i & \cos\theta_i\cos\alpha_i & -\cos\theta_i\sin\alpha_i & a_i\sin\theta_i \\ '
               r'0 & \sin\alpha_i & \cos\alpha_i & d_i \\ 0 & 0 & 0 & 1 \end{bmatrix}')
    out.append(Bloque('Transformada DH general', general,
                      'Cada eslabón se describe con una rotación y una traslación sobre z y sobre x; '
                      'la fila 4 es la parte homogénea.'))
    T = np.eye(4)
    for i, (p, qi) in enumerate(zip(dh.DH_PARAMETERS, q), 1):
        A = dh.dh_transform(float(qi), p)
        T = T @ A
        out.append(Bloque(f'Matriz A{i}',
                          rf'{{}}^{{{i-1}}}A_{{{i}}}=' + _mat(_homogenea_mm(A)),
                          f'Se sustituyen a, α, d y θ de la fila {i}. La última columna (x, y, z) está en mm.'))
    T6 = dh.forward_kinematics(q)
    out.append(Bloque('Cinemática directa hasta la brida',
                      r'{}^0T_6={}^0A_1\,{}^1A_2\,{}^2A_3\,{}^3A_4\,{}^4A_5\,{}^5A_6=' + _mat(_homogenea_mm(T6)),
                      'Producto de las seis matrices: pose de la brida (tool0) respecto a la base. Posición en mm.'))
    if herramienta == 'tcp':
        out.append(Bloque('Transformada fija brida → TCP',
                          r'{}^6T_{\mathrm{TCP}}=' + _mat(_homogenea_mm(dh.tcp_transform())),
                          f'La herramienta añade {dh.TCP_Z_M * 1000:.0f} mm sobre el eje z de la brida.'))
        Ttcp = dh.forward_kinematics_tcp(q)
        out.append(Bloque('Pose del TCP',
                          r'{}^0T_{\mathrm{TCP}}={}^0T_6\,{}^6T_{\mathrm{TCP}}=' + _mat(_homogenea_mm(Ttcp)),
                          'Pose final de la punta de la herramienta respecto a la base. Posición en mm.'))
    return out


def bloques_jacobiano(q_deg):
    j = hito2()['jacobian']
    q = np.deg2rad(np.asarray(q_deg, dtype=float))
    J = j.geometric_jacobian(q)
    sig = np.linalg.svd(J, compute_uv=False)
    det = float(np.linalg.det(J))
    smin = float(sig[-1])
    kappa = float('inf') if smin == 0 else float(sig[0] / smin)
    formula = (r'J(q)=\begin{bmatrix} J_{v} \\ J_{\omega} \end{bmatrix},\quad '
               r'J_i=\begin{bmatrix} z_{i-1}\times(p_{\mathrm{TCP}}-p_{i-1}) \\ z_{i-1} \end{bmatrix},\quad '
               r'\begin{bmatrix} v \\ \omega \end{bmatrix}=J(q)\,\dot q')
    out = [Bloque('Definición del Jacobiano geométrico', formula,
                  'Columna i para una junta de rotación: z_{i-1} es su eje y p_{i-1} su origen. '
                  'Relaciona las velocidades articulares con la velocidad lineal y angular del TCP.')]
    out.append(Bloque('Jacobiano en la pose actual', 'J(q)=' + _mat(J),
                      'Filas 1-3: velocidad lineal (m/s por rad/s). Filas 4-6: velocidad angular (adimensional).'))
    out.append(Bloque('Determinante', rf'\det J(q)={_sci(det)}',
                      'Si det J = 0 el robot está en una singularidad: pierde una dirección de movimiento.'))
    sigmas = r',\quad '.join(rf'\sigma_{i}={_n(s, 4)}' for i, s in enumerate(sig, 1))
    kap = r'\infty' if np.isinf(kappa) else _n(kappa, 1)
    if smin >= SIGMA_AVISO:
        texto = f'σ_min = {smin:.4f} ≥ {SIGMA_AVISO}: lejos de singularidad, el movimiento es seguro.'
    elif smin >= SIGMA_BLOQUEO:
        texto = f'σ_min = {smin:.4f} entre {SIGMA_BLOQUEO} y {SIGMA_AVISO}: AVISO, cerca de una singularidad.'
    else:
        texto = f'σ_min = {smin:.4f} < {SIGMA_BLOQUEO}: BLOQUEO, singularidad; el movimiento cartesiano se rechaza.'
    out.append(Bloque('Valores singulares y condición',
                      r'\begin{aligned} & ' + sigmas + r' \\ & \sigma_{\min}=\sigma_6=' + _n(smin, 4)
                      + r',\quad \kappa=\frac{\sigma_{\max}}{\sigma_{\min}}=' + kap + r' \end{aligned}',
                      texto + ' (Umbrales: aviso 0,04; bloqueo 0,02.)'))
    return out


def bloques_lspb(q0_deg, qf_deg, velocidad_pct):
    h = hito2()
    lspb = h['lspb']
    q0 = np.deg2rad(np.asarray(q0_deg, dtype=float))
    qf = np.deg2rad(np.asarray(qf_deg, dtype=float))
    vmax, amax = lspb.default_limits(float(velocidad_pct) / 100.0)
    tr = lspb.plan_lspb(q0, qf, vmax, amax)
    d = np.abs(tr.displacement) / vmax
    k = int(np.argmax(d))
    q0d, qfd = np.rad2deg(q0), np.rad2deg(qf)
    V, a = np.rad2deg(tr.cruise_velocity), np.rad2deg(tr.blend_acceleration)
    tb, tf = tr.tb, tr.tf
    simb = (r'\begin{aligned} q(t)&=q_0+\frac{1}{2}\,a\,t^2,&& \quad 0\leq t<t_b \\ '
            r'q(t)&=q_0+V\,\left(t-\frac{t_b}{2}\right),&& \quad t_b\leq t\leq t_f-t_b \\ '
            r'q(t)&=q_f-\frac{1}{2}\,a\,(t_f-t)^2,&& \quad t_f-t_b<t\leq t_f \end{aligned}')
    out = [Bloque('Perfil LSPB (trapecio de velocidad)', simb,
                  'Tres tramos: acelera con a constante, crucero a velocidad V y frena. '
                  'Con V = Δq/(t_f−t_b) y a = V/t_b; todos los ejes comparten t_b y t_f.')]
    j = k + 1
    num = (rf'\begin{{aligned}} t_b&={_n(tb, 3)}\,\mathrm{{s}},\quad t_f={_n(tf, 3)}\,\mathrm{{s}} \\ '
           rf'V_{j}&={_n(V[k], 2)}\,^\circ/\mathrm{{s}},\quad a_{j}={_n(a[k], 2)}\,^\circ/\mathrm{{s}}^2 \\ '
           rf'q_{j}(t)&={_n(q0d[k], 2)}+\frac{{1}}{{2}}\,{_par(a[k])}\,t^2,&& \quad 0\leq t<{_n(tb, 3)} \\ '
           rf'q_{j}(t)&={_n(q0d[k], 2)}+{_par(V[k])}\,(t-{_n(tb / 2, 3)}),&& \quad {_n(tb, 3)}\leq t\leq {_n(tf - tb, 3)} \\ '
           rf'q_{j}(t)&={_n(qfd[k], 2)}-\frac{{1}}{{2}}\,{_par(a[k])}\,({_n(tf, 3)}-t)^2,&& \quad {_n(tf - tb, 3)}<t\leq {_n(tf, 3)} '
           r'\end{aligned}')
    out.append(Bloque(f'Valores numéricos del eje {j} (domina el tiempo)', num,
                      f'El eje {j} es el que más tarda al {float(velocidad_pct):.0f} % de la velocidad máxima; '
                      'fija t_b y t_f para todos.'))
    filas = [' & '.join([str(i + 1), _n(q0d[i], 2), _n(qfd[i], 2), _n(qfd[i] - q0d[i], 2), _n(V[i], 2), _n(a[i], 2)])
             for i in range(6)]
    tabla = (r'\begin{array}{c|ccccc} \mathrm{eje} & q_0\,[^\circ] & q_f\,[^\circ] & \Delta q\,[^\circ] & '
             r'V\,[^\circ/\mathrm{s}] & a\,[^\circ/\mathrm{s}^2] \\ \hline ' + r' \\ '.join(filas) + r' \end{array}')
    out.append(Bloque('Los seis ejes sincronizados', tabla,
                      f'Todos terminan juntos en t_f = {tf:.3f} s; los ejes con menos recorrido van más lentos.'))
    return out


def bloques_dinamica(q_deg, qd_deg_s, qdd_deg_s2):
    dy = hito2()['dynamics']
    q = np.deg2rad(np.asarray(q_deg, dtype=float))
    qd = np.deg2rad(np.asarray(qd_deg_s, dtype=float))
    qdd = np.deg2rad(np.asarray(qdd_deg_s2, dtype=float))
    M = dy.mass_matrix(q)
    c = dy.coriolis_vector(q, qd)
    g = dy.gravity_vector(q)
    tau = M @ qdd + c + g
    ec = (r'\tau=M(q)\,\ddot q+C(q,\dot q)\,\dot q+G(q)\quad\Rightarrow\quad '
          r'q=' + _col(np.rad2deg(q), 1) + r',\ \dot q=' + _col(np.rad2deg(qd), 1)
          + r',\ \ddot q=' + _col(np.rad2deg(qdd), 1))
    out = [Bloque('Dinámica inversa', ec,
                  'Torque que exigen las articulaciones: inercia, Coriolis/centrífuga y gravedad. '
                  'Entradas en ° , °/s y °/s² (se convierten a rad).'),
           Bloque('Matriz de inercia', r'M(q)=' + _mat(M, 5),
                  'Simétrica y definida positiva (kg·m², 5 decimales); depende de la postura. Ejes 1-3 con mayor inercia.'),
           Bloque('Torques resultantes (N·m)',
                  r'\tau=' + _col(M @ qdd, 3) + r'+' + _col(c, 3) + r'+'
                  + _col(g, 3) + r'=' + _col(tau, 3),
                  'De izquierda a derecha: inercia, Coriolis, gravedad y su suma τ (N·m). '
                  'Con q̇ = q̈ = 0 sólo queda la gravedad.')]
    return out


# ---------------------------------------------------------------- renderizado

def _sin_tex_forzado():
    return os.environ.get('IRB120_SIN_TEX', '') not in ('', '0')


@lru_cache(maxsize=1)
def _prueba_usetex():
    if not (shutil.which('latex') and shutil.which('dvipng')):
        return False
    try:
        with matplotlib.rc_context({'text.usetex': True, 'text.latex.preamble': PREAMBULO}):
            fig = Figure(figsize=(1, 1))
            fig.text(.5, .5, r'$\begin{bmatrix}x\end{bmatrix}$', usetex=True)
            fig.savefig(io.BytesIO(), format='png')
        matplotlib.rcParams['text.latex.preamble'] = PREAMBULO  # el dibujo posterior (Tk) también lo necesita
        return True
    except Exception:
        return False


def usar_latex():
    """True si usetex funciona (prueba real, cacheada). IRB120_SIN_TEX=1 lo desactiva."""
    return False if _sin_tex_forzado() else _prueba_usetex()


_TOKEN = re.compile(r'\\begin\{(\w+)\}(?:\{([^}]*)\})?|\\end\{\w+\}|\\\\')


def _parsear(latex):
    """Líneas -> piezas: ('t', texto) | ('m', entorno, spec, filas, lineas_h); `&` de una línea -> ('&',)."""
    s = latex.strip()
    for env in ('aligned', 'gathered'):
        if s.startswith(rf'\begin{{{env}}}') and s.endswith(rf'\end{{{env}}}'):
            s = s[len(env) + 8:-(len(env) + 6)]
    lineas, actual, pos = [], [], 0

    def texto(t):
        partes = t.split('&')
        for i, p in enumerate(partes):
            if i:
                actual.append(('&',))
            if p.strip():
                actual.append(('t', p.strip()))
    while True:
        m = _TOKEN.search(s, pos)
        if not m:
            texto(s[pos:])
            break
        texto(s[pos:m.start()])
        if m.group(0) == r'\\':
            lineas.append(actual)
            actual = []
            pos = m.end()
            continue
        env, spec = m.group(1), m.group(2) or ''
        fin = s.index(rf'\end{{{env}}}', m.end())
        cuerpo = s[m.end():fin]
        filas, hs = [], set()
        for r in re.split(r'\\\\', cuerpo):
            if r'\hline' in r:
                hs.add(len(filas))
                r = r.replace(r'\hline', '')
            if r.strip():
                filas.append([c.strip() for c in r.split('&')])
        actual.append(('m', env, spec, filas, hs))
        pos = fin + len(rf'\end{{{env}}}')
    if actual:
        lineas.append(actual)
    return lineas


def _fig_usetex(latex, tamano, color, fondo):
    fig = Figure(dpi=DPI, facecolor=fondo)
    canvas = FigureCanvasAgg(fig)
    with matplotlib.rc_context({'text.usetex': True, 'text.latex.preamble': PREAMBULO}):
        t = fig.text(0, 0, rf'$\displaystyle {latex}$', fontsize=tamano, color=color, usetex=True,
                     ha='left', va='bottom')
        bb = t.get_window_extent(canvas.get_renderer())
        pad = tamano * DPI / 72 * 0.6
        W, H = bb.width + 2 * pad, bb.height + 2 * pad
        fig.set_size_inches(W / DPI, H / DPI)
        t.set_position((pad / W, pad / H))
        canvas.draw()
    return fig


def _fig_mathtext(latex, tamano, color, fondo):
    fig = Figure(dpi=DPI, facecolor=fondo)
    canvas = FigureCanvasAgg(fig)
    rend = canvas.get_renderer()
    fs = tamano * DPI / 72
    gx, gy = 0.9 * fs, 0.5 * fs

    def txt(s):
        t = fig.text(0, 0, f'${s}$', fontsize=tamano, color=color, ha='left', va='center')
        bb = t.get_window_extent(rend)
        return t, bb.width, bb.height

    lineas = []   # cada línea: lista de cajas dict(w, h, dibujar(x, yc))
    for linea in _parsear(latex):
        cajas, ancla = [], None
        for pz in linea:
            if pz[0] == '&':
                ancla = ancla if ancla is not None else sum(c['w'] + 0.35 * fs for c in cajas)
            elif pz[0] == 't':
                t, w, h = txt(pz[1])
                cajas.append({'w': w, 'h': h, 'draw': lambda x, y, t=t: t.set_position((x / W, y / H))})
            else:
                _, env, spec, filas, hs = pz
                nc = max(len(f) for f in filas)
                celdas = [[txt(c) if c else (None, 0, 0) for c in f + [''] * (nc - len(f))] for f in filas]
                cw = [max(c[1] for c in col) for col in zip(*celdas)]
                rh = max(c[2] for f in celdas for c in f)
                wi = sum(cw) + gx * (nc - 1)
                hi = rh * len(filas) + gy * (len(filas) - 1)
                br = env.endswith('matrix')
                pad = 0.6 * fs if br else 0.3 * fs
                num = env != 'array' and all(re.fullmatch(r'-?\d+(\.\d+)?', c) for f in filas for c in f if c)
                bars = []
                if env == 'array':
                    idx = 0
                    for ch in spec:
                        if ch == '|':
                            bars.append(idx)
                        elif ch.isalpha():
                            idx += 1

                def dib(x, yc, celdas=celdas, cw=cw, rh=rh, wi=wi, hi=hi, pad=pad, br=br, hs=hs, bars=bars,
                        env=env, nc=nc, num=num):
                    x0 = x + pad
                    top = yc + hi / 2
                    xs = [x0 + sum(cw[:j]) + gx * j for j in range(nc)]
                    for i, f in enumerate(celdas):
                        y = top - i * (rh + gy) - rh / 2
                        for j, (t, w, _h) in enumerate(f):
                            if t is None:
                                continue
                            if env == 'array':
                                t.set_position(((xs[j] + (cw[j] - w) / 2) / W, y / H))
                            elif num:
                                t.set_position(((xs[j] + cw[j] - w) / W, y / H))
                            else:
                                t.set_position(((xs[j] + (cw[j] - w) / 2) / W, y / H))
                    lw = max(1.0, tamano / 10)

                    def ln(xa, ya, xb, yb):
                        fig.add_artist(Line2D([xa / W, xb / W], [ya / H, yb / H], color=color, lw=lw,
                                              transform=fig.transFigure))
                    if br:
                        tick = 0.35 * fs
                        for xb, sg in ((x + 0.12 * fs, 1), (x + pad + wi + pad - 0.12 * fs, -1)):
                            ln(xb, top + gy / 2, xb, top - hi - gy / 2)
                            ln(xb, top + gy / 2, xb + sg * tick, top + gy / 2)
                            ln(xb, top - hi - gy / 2, xb + sg * tick, top - hi - gy / 2)
                    for i in hs:
                        yl = top - i * (rh + gy) + gy / 2
                        ln(x, yl, x + wi + 2 * pad, yl)
                    for b in bars:
                        xb = xs[b] - gx / 2 - (0 if b else 0)
                        ln(xb, top + gy / 2, xb, top - hi - gy / 2)
                cajas.append({'w': wi + 2 * pad, 'h': hi + gy, 'draw': dib})
        lineas.append((cajas, ancla))
    ancla_max = max((a or 0) for _, a in lineas)
    ancho = 0
    for cajas, a in lineas:
        ancho = max(ancho, (ancla_max - (a or 0)) + sum(c['w'] + 0.35 * fs for c in cajas))
    altos = [max([c['h'] for c in cajas] + [fs]) for cajas, _ in lineas]
    pad = 0.6 * fs
    gl = 0.5 * fs
    W = ancho + 2 * pad
    H = sum(altos) + gl * (len(altos) - 1) + 2 * pad
    fig.set_size_inches(W / DPI, H / DPI)
    y = H - pad
    for (cajas, a), alto in zip(lineas, altos):
        yc, x = y - alto / 2, pad + ancla_max - (a or 0)
        for c in cajas:
            c['draw'](x, yc)
            x += c['w'] + 0.35 * fs
        y -= alto + gl
    canvas.draw()
    return fig


def figura_bloque(bloque, tamano=18, oscuro=False, usetex=None):
    """Figure (sin pyplot) con el LaTeX del bloque, del tamaño justo del contenido.

    usetex=None -> usar_latex(); True/False fuerza la ruta (False = respaldo mathtext).
    """
    color, fondo = OSCURO if oscuro else CLARO
    if usetex is None:
        usetex = usar_latex()
    elif usetex:
        usetex = _prueba_usetex()
    return (_fig_usetex if usetex else _fig_mathtext)(bloque.latex, tamano, color, fondo)


def png_bloque(bloque, ruta, tamano=18, oscuro=False, usetex=None):
    figura_bloque(bloque, tamano, oscuro, usetex).savefig(ruta, dpi=DPI, facecolor='auto')
    return ruta


_CACHE_PNG = {}


def png_bytes_bloque(bloque, tamano=18, oscuro=False, usetex=None):
    """PNG en memoria cacheado por (latex, tamaño, tema, ruta); para CTkImage/PIL."""
    clave = (bloque.latex, tamano, bool(oscuro), usar_latex() if usetex is None else bool(usetex))
    if clave not in _CACHE_PNG:
        buf = io.BytesIO()
        figura_bloque(bloque, tamano, oscuro, usetex).savefig(buf, format='png', dpi=DPI, facecolor='auto')
        _CACHE_PNG[clave] = buf.getvalue()
    return _CACHE_PNG[clave]
