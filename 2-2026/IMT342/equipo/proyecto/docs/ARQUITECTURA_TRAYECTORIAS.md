# Arquitectura · trayectorias A → B → C → A, reglas del Hito 2, CustomTkinter y visión

Contrato entre módulos (20/11/2026). Rutas relativas a `ros2_ws/src/irb120_control/`.
Unidades en las interfaces: **grados, mm, s, N·m**. Dentro de los cálculos, el Hito 2 usa rad y m.

## Decisiones de las preguntas abiertas

| Pregunta | Decisión |
|---|---|
| Tolerancias | **Más estrictas que el Hito 2** (tabla abajo). Bloquean el envío; las «aviso» solo se marcan en amarillo. |
| Matemática | **LaTeX completo** (matplotlib `usetex=True`; TeX ya está instalado). Si TeX falla, cae solo a *mathtext*. |
| Visión | Cámara aún no definida. Se deja una **entrada genérica de puntos** (tópico ROS y HTTP local) en `base_link`; la calibración cámara → base queda para cuando se sepa si va fija o en la pinza. |

### Tolerancias (`irb120_control/trayectorias/reglas.py`, `TOLERANCIAS`)

| Regla | Aviso | Bloqueo | Hito 2 |
|---|---|---|---|
| σ_min(J) a lo largo del tramo | < 0,04 | < 0,02 | 0,01 |
| Número de condición κ(J) | > 150 | > 500 | — |
| Margen a los límites articulares | < 15° | < 10° | 5° |
| Velocidad articular del perfil | > 70 % de la máx. | > 85 % de la máx. | LSPB |
| Aceleración articular del perfil | > 70 % de la del perfil | > 100 % | LSPB |
| Par articular (dinámica completa) | > 70 % de τ_ref | > 100 % de τ_ref | — |
| Salto de rama en un tramo lineal | — | > 5° entre muestras consecutivas | — |
| Altura del TCP sobre la base (z) | < 100 mm | < 30 mm | — |
| Precisión IK → FK en cada punto | — | > 0,001 mm / 0,001° | 0,001 |

τ_ref es una referencia del proyecto (ABB no publica el par de los motores): 1,5 × el par de gravedad máximo
de cada eje sobre todo el espacio articular, con un mínimo de 2 N·m en la muñeca. Se documenta así en la interfaz.

## Piezas

```text
CustomTkinter «Estudio» (estudio/)            panel irb120_panel_rws (panel/)                 IRC5
  editor de puntos, reglas, gráficas,  HTTP   Panel.handle('trayectoria', ...)      RWS       LabJointRws v5
  matemática LaTeX                     ─────► re-planifica con la postura real ───────────►  pcTipo 0: MoveAbsJ fine
  planificar() local para la vista ◄───────── ejecuta tramo a tramo + verificación         pcTipo 1: MoveL fine
  previa                               estado  (sección 5 de CONTEXTO_Y_OBJETIVOS)           (sin cortes cada 40°)
          ▲                                     ▲ buzón de puntos
          │ trayectorias/ (puro, sin ROS ni GUI) │  ◄─ RViz «Añadir a la trayectoria»
          └──────────────────────────────────────┘  ◄─ /irb120/trayectoria/punto_externo (visión)
```

### 1. `irb120_control/trayectorias/` (puro: sin ROS, sin GUI, sin red)

```python
# modelo.py
@dataclass
class Punto:
    nombre: str
    pose: list[float] | None   # [x, y, z mm, roll, pitch, yaw °] del punto `herramienta` en base_link
    q: list[float] | None      # ángulos [°] si el punto se dio o capturó en ángulos (tiene prioridad)
    origen: str = 'manual'     # manual | captura | rviz | vision | angulos
    tipo: str = 'auto'         # movimiento PARA LLEGAR a este punto: auto | articular | lineal

@dataclass
class Trayectoria:
    nombre: str
    puntos: list[Punto]
    cerrar: bool = True        # A→B→C→A
    repeticiones: int = 1
    herramienta: str = 'tcp'   # tcp | brida
    def to_dict(self) -> dict; @classmethod from_dict(d); guardar(path); @classmethod cargar(path)

# reglas.py
TOLERANCIAS: Tolerancias        # dataclass congelada con la tabla de arriba
@dataclass
class Regla:  nombre: str; estado: str  # 'ok' | 'aviso' | 'falla'
              valor: float | None; limite: float | None; t: float | None; detalle: str

# planificador.py
def planificar(tray: Trayectoria, q_inicio: list[float], velocidad_pct: float,
               tol: Tolerancias = TOLERANCIAS) -> Plan
def a_ordenes(plan: Plan) -> list[dict]     # JSON para el panel:
    # {'tramo': i, 'tipo': 'articular'|'lineal', 'q': [6 °], 'pose_tool0': [x,y,z mm, qw,qx,qy,qz]}

@dataclass
class Muestras:  t, q, qd, qdd, tau (np.ndarray N×6, °, °/s, °/s², N·m), sigma, cond (N,), tcp (N×3 mm)
@dataclass
class Evaluacion: tipo: str; factible: bool; duracion_s: float; reglas: list[Regla]; muestras: Muestras | None
@dataclass
class Tramo:  indice: int; desde: str; hasta: str; q0: list; qf: list; tipo: str (elegido)
              motivo: str; opciones: dict[str, Evaluacion]; ok: bool; sugerencias: list[str]
              pose_tool0_fin: list[float]
@dataclass
class Plan:   tramos: list[Tramo]; ok: bool; resumen: str; q_puntos: list[list[float]]
              duracion_s: float; tolerancias: Tolerancias
```

- El tramo 0 va desde `q_inicio` (postura medida) hasta el primer punto. Con `cerrar`, el último tramo vuelve al primero. `repeticiones` repite la vuelta (el panel la repite; el plan describe una vuelta).
- Rama de IK de cada punto: Pieper del Hito 2 (`rank_candidates`) con referencia = q del punto anterior, `min_sigma` y `min_margin_deg` de `TOLERANCIAS`.
- `articular`: LSPB del Hito 2 con `default_limits(velocidad_pct/100)`.
- `lineal`: recta en posición + slerp en orientación, perfil LSPB en el parámetro de camino con v = 250 mm/s · pct/100; IK en cada muestra con la rama más cercana a la muestra anterior; q̇, q̈ por diferencias.
- Elección automática: descarta las opciones con alguna regla en `falla`; entre las factibles, la de mayor σ_min mínimo si la otra tiene avisos de singularidad; si no, la más corta. `motivo` lo explica en una frase. Si ninguna es factible, `sugerencias` propone otra rama o un punto intermedio concreto.

### 2. RAPID `LabJointRws` v5 y cliente (`rws_mover.py`, `rws_j6.py`)

- Nuevos PERS: `pcTipo` (0 = `MoveAbsJ`, 1 = `MoveL` con `ConfL \Off`), `pcPose` (robtarget de `tool0` en `wobj0`).
- Siempre `fine` al final de la orden: **una orden por tramo**, sin cortes cada 40° (`maxPasoDeg` 360).
- `pcTarget` sigue siendo el objetivo articular esperado: el robot valida límites con él en los dos tipos.
- Módulo ≤ 4900 caracteres. Etiquetas `servidor_v5` / `servidor_v5_auto`; la sesión reinstala si encuentra la v4.
- PC: `move_tramo(mover, tipo, q_deg, pose_tool0, timeout, echo, cancel) -> {'seq', 'code', 'joints_deg', 'max_error_deg'}`.

### 3. Panel (`panel/`)

- Acciones nuevas: `trayectoria` (recibe la trayectoria y las órdenes; re-planifica con la postura real y solo ejecuta si coincide), `pausar`, `reanudar`, `vista_previa`, `buzon_tomar`.
- Estado nuevo: `trayectoria` (fase, tramo actual, vuelta, resultados por punto), `buzon` (puntos de RViz y visión con id creciente).
- RViz: menú del control 3D «Añadir a la trayectoria» → buzón.
- Visión: tópico `/irb120/trayectoria/punto_externo` (`geometry_msgs/PoseStamped`, `base_link`, m) y `POST /api/punto_externo` → buzón con `origen = 'vision'`.
- HTTP local: el testigo se guarda en `~/.cache/irb120/panel_token` (permisos 600) para que el Estudio pueda dar órdenes.

### 4. Estudio CustomTkinter (`estudio/`) · `brazo estudio`, y `brazo sesion` lo abre

Pestañas: Estado · Trayectoria (editor, capturar, buzón, guardar/cargar JSON, planificar, vista previa, enviar al panel) ·
Reglas (por tramo, verde/amarillo/rojo, motivo y sugerencias) · Gráficas (q, q̇, q̈, τ, σ_min) · Matemática (LaTeX).
No mueve el robot por sí sola: envía la trayectoria verificada al panel, que vuelve a verificar y ejecuta.
