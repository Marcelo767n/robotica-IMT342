# Guía del Hito 2: cinemática inversa, trayectorias y singularidad

Guía de lo que se hizo, qué se aplicó, cómo funciona cada archivo y cómo usarlo. Todas las
salidas de ejemplo son las que imprime el código real (ABB IRB 120, ROS 2 Jazzy).

## 1. Qué pide el Hito 2 y qué se entregó

| Requisito (Guía PFI) | Entregado | Dónde |
|---|---|---|
| Nodo ROS en Python que reciba una pose | `ik_trajectory_node` (`geometry_msgs/PoseStamped`) | `nodes/ik_trajectory_node.py` |
| Ejecutar Pieper (sin MoveIt) | Solver analítico, hasta 8 soluciones | `kinematics/pieper.py` |
| Generar trayectoria LSPB | LSPB sincronizado con límites | `trajectory/lspb.py` |
| Notebook: divergencia de velocidades y torques en q5 = 0 | Notebook ejecutado con gráficas y aserciones | `notebooks/hito2_singularidad_q5.ipynb` |
| Extra aplicado | Jacobiano, dinámica, autocolisión con el CAD real | `jacobian.py`, `dynamics.py`, `collision.py` |

Reglas "anti-caja negra" respetadas: no se usa MoveIt ni un resolvedor numérico; la IK es
analítica y está programada en Python/NumPy.

## 2. Mapa del paquete `irb120_hito2`

```text
ros2_ws/src/irb120_hito2/
├── irb120_hito2/
│   ├── kinematics/
│   │   ├── pieper.py        # IK analítica (Pieper)
│   │   ├── jacobian.py      # J(q), det J, número de condición, SingularityError
│   │   ├── collision.py     # autocolisión + mesa con los meshes collision del CAD
│   │   └── transforms.py    # rpy / cuaternión / matriz homogénea
│   ├── trajectory/lspb.py   # perfil LSPB sincronizado
│   ├── dynamics.py          # M(q), c(q, q̇), g(q), torques
│   └── nodes/
│       ├── ik_trajectory_node.py   # nodo principal
│       └── send_target.py          # utilidad de terminal para enviar poses
├── launch/hito2.launch.py   # Hito 1 (sin sliders) + nodo IK
└── test/                    # 24 pruebas (Pieper, LSPB, singularidad, colisión)
```

El paquete reutiliza del Hito 1 la cinemática directa (`irb120_hito1.kinematics.dh`): la
tabla DH, `forward_kinematics` (hasta `tool0`) y `forward_kinematics_tcp` (hasta el TCP de
la pinza, `Tz(0.100 m)` más allá de `tool0`).

## 3. Flujo de datos

```text
/irb120/target_pose ──► ik_trajectory_node ──► /irb120/joint_commands_deg ──► joint_state_source (Hito 1)
 (PoseStamped, TCP)      │ 1. Pieper (hasta 8 q)                                     │
                         │ 2. descarta límites y colisiones                          ▼
                         │ 3. elige la q más cercana a la actual                /joint_states
                         │ 4. plan LSPB q_actual → q_meta                            │
                         ▼                                                           ▼
            /irb120/planned_trajectory (JointTrajectory)       robot_state_publisher → RViz / TF
            /irb120/ik_status (String)                         fk_validator (DH vs URDF vs TF)
```

| Tópico | Tipo | Sentido | Contenido |
|---|---|---|---|
| `/irb120/target_pose` | `PoseStamped` | entrada | Pose del TCP en `base_link` (metros y cuaternión) |
| `/joint_states` | `JointState` | entrada | Postura actual (punto de partida del LSPB) |
| `/irb120/joint_commands_deg` | `Float64MultiArray` | salida, 50 Hz | Seis ángulos en grados |
| `/irb120/planned_trajectory` | `JointTrajectory` | salida | Plan completo (posición, velocidad, aceleración cada 50 ms) |
| `/irb120/ik_status` | `String` | salida | Resultado: soluciones, elegida, error FK, tiempos |

Parámetros del nodo:

| Parámetro | Defecto | Significado |
|---|---|---|
| `speed_scale` | `0.3` | Fracción de la velocidad máxima ABB (250/250/250/320/320/420 °/s) |
| `max_accel_rad_s2` | `3.0` | Aceleración máxima por junta |
| `publish_rate_hz` | `50.0` | Frecuencia de los comandos |
| `check_collisions` | `true` | Descarta soluciones con autocolisión o que toquen la mesa |
| `collision_margin_m` | `0.005` | Distancia mínima aceptada entre piezas |

## 4. Cinemática inversa de Pieper (`kinematics/pieper.py`)

**Idea.** El IRB 120 tiene muñeca esférica: los ejes 4, 5 y 6 se cortan en un punto, el
*centro de muñeca*. Eso desacopla el problema en dos partes sencillas.

**Paso 0: centro de muñeca.** Dada la pose de `tool0` (`R`, `p`):

```text
p_wc = p − d6 · R[:,2]        (d6 = 0.072 m; la tercera columna de R es z6)
```

**Paso 1: q1, q2, q3 (posición).**

- `q1 = atan2(y, x)`; la solución "brazo atrás" es `q1 + π` con el radio cambiado de signo.
- Con `r = ±√(x²+y²)` y `h = z − d1` se resuelve el plano vertical del brazo. Longitudes:
  `L2 = 0.270`, `L3 = √(d4² + a3²) = 0.3100`, y `δ = atan2(a3, d4)`.
- Ley de cosenos: `−sin(q3 − δ) = (r² + h² − L2² − L3²) / (2·L2·L3)`. Dos signos dan dos
  soluciones de codo (`arriba` / `abajo`). Si el lado derecho sale fuera de [−1, 1], el punto
  está fuera del alcance y no hay solución.
- `q2 = atan2(r, h) − atan2(L3·sin η, L2 + L3·cos η)` con `η = π/2 + q3 − δ`.

**Paso 2: q4, q5, q6 (orientación).** Con `R03` ya conocida:

```text
R36 = R03ᵀ · R = Rz(q4) · Ry(−q5) · Rz(q6 + π)
```

Es una descomposición de Euler ZYZ. Se obtienen dos soluciones de muñeca (`q5+` y `q5−`).

**Paso 3: filtrado.** Cada candidato se lleva a los límites articulares (probando vueltas de
2π), se verifica con la cinemática directa (error < 1e-6 m y 1e-6 rad) y se ordena por
cercanía a la postura de referencia. Resultado: lista de `IKSolution`
(`q`, `arm`, `elbow`, `wrist`, `singular_wrist`).

**Muñeca singular (q5 = 0).** Solo se conoce `q4 + q6`; la solución se marca
`singular_wrist=True` y conserva el `q4` de referencia.

### Ejemplo A: ida y vuelta con la postura A del Hito 1

```python
import numpy as np
from irb120_hito1.kinematics.dh import forward_kinematics_tcp
from irb120_hito2.kinematics.pieper import inverse_kinematics_tcp

q = np.deg2rad([30, -20, 15, 40, -35, 60])
T = forward_kinematics_tcp(q)                      # pose del TCP
for s in inverse_kinematics_tcp(T, q):             # q como referencia
    print(s.arm, s.elbow, s.wrist, np.rad2deg(s.q).round(2))
```

```text
frente arriba q5+ [ 30.   -20.    15.    40.   -35.    60.  ]   <- la original, primera
atras  arriba q5+ [-150.   -80.11  15.   -21.84 -82.27 -82.41]
atras  arriba q5- [-150.   -80.11  15.   158.16  82.27  97.59]
frente arriba q5- [  30.   -20.    15.  -140.    35.  -120.  ]
```

Las cuatro llevan el TCP exactamente a la misma pose; el resto de las ocho candidatas se
descartó por límites articulares. La primera siempre es la más cercana a la referencia.

### Ejemplo B: pose objetivo "pinza hacia abajo"

```python
from irb120_hito2.kinematics.transforms import rpy_to_matrix, pose_matrix
T = pose_matrix((0.25, -0.15, 0.30), rpy_to_matrix(0, np.pi, 0))   # z del TCP hacia abajo
sol = inverse_kinematics_tcp(T, np.zeros(6))[0]
print(np.rad2deg(sol.q).round(2))          # [-30.96 -1.21 30.74 -0. 60.47 -30.96]
print(forward_kinematics_tcp(sol.q)[:3, 3])  # [ 0.25 -0.15  0.3 ]  -> error ~1e-16 m
```

## 5. Perfil LSPB (`trajectory/lspb.py`)

LSPB = *Linear Segment with Parabolic Blends*: arranque a aceleración constante, tramo a
velocidad constante y frenado simétrico. Todas las juntas **comparten** `tf` y `tb`, así
que llegan a la vez y el TCP no se desvía del camino articular.

```text
V_i = Δ_i / (tf − tb)        a_i = V_i / tb
0 ≤ t < tb          q = q0 + a t²/2
tb ≤ t ≤ tf − tb    q = q0 + V (t − tb/2)
tf − tb < t ≤ tf    q = qf − a (tf − t)²/2
```

`plan_lspb(q0, qf, vmax, amax)` busca por bisección el menor `tf` factible (la factibilidad
crece con `tf`), con `tb = (tf − √(tf² − 4K))/2`, `K = max(Δ_i / amax_i)`. Devuelve un
`LspbTrajectory` con `.sample(t) → (q, q̇, q̈)`, `.tf`, `.tb`, `.cruise_velocity` y
`.blend_acceleration`.

### Ejemplo C

```python
from irb120_hito2.trajectory.lspb import plan_lspb
vmax = np.deg2rad([250, 250, 250, 320, 320, 420]) * 0.3
t = plan_lspb(np.zeros(6), np.deg2rad([60, -40, 20, 90, 30, -120]), vmax, 3.0)
print(round(t.tf, 3), round(t.tb, 3))         # 1.685 0.733
print(np.rad2deg(t.cruise_velocity).round(1)) # [63. -42. 21. 94.5 31.5 -126.]  °/s
print(t.blend_acceleration.round(3))          # [1.5 -1. 0.5 2.25 0.75 -3.]   rad/s²
print(np.rad2deg(t.sample(t.tf / 2)[0]))      # [30. -20. 10. 45. 15. -60.]  (punto medio)
```

La junta 6 (la que más se mueve) es la que satura: su aceleración llega a `3 rad/s²`. Las
demás llevan la misma duración con menos velocidad y aceleración.

## 6. Jacobiano y singularidad (`kinematics/jacobian.py`)

`geometric_jacobian(q, reference)` devuelve la matriz 6×6 que relaciona `q̇` con el twist
`[v; ω]` en `base_link` (`reference` = `'tcp'`, `'tool0'` o `'wrist'`). La columna `i` es
`[zᵢ₋₁ × (pₑ − oᵢ₋₁); zᵢ₋₁]`, con los marcos obtenidos de la tabla DH.

Tomando el centro de muñeca como referencia, `J` es triangular por bloques:

```text
det J = det(Jp_brazo[3×3]) · det[z3 z4 z5] = − sin(q5) · det(Jp_brazo)
```

Cuando `q5 = 0` los ejes 4 y 6 quedan colineales y `J` pierde un rango:

- `q̇ = J⁻¹ v` crece como `1/|sin q5|`.
- `q̈ = J⁻¹(a − J̇ q̇)` y el torque crecen como `1/sin² q5`.
- En `q5 = 0` exacto, `joint_velocity` lanza `SingularityError` (la matriz no es invertible).

### Ejemplo D: velocidad al acercarse a la singularidad

```python
from irb120_hito2.kinematics import jacobian as J
twist = np.array([0.10, 0.05, 0.02, 0.30, 0.20, 0.10])
for e in (0.1, 0.01, 0.001):
    q5 = q.copy(); q5[4] = e
    print(e, round(J.determinant(q5), 6), round(np.linalg.norm(J.joint_velocity(q5, twist)), 2))
```

```text
0.1    -0.00169   2.68      <- cada vez que q5 baja 10×,
0.01   -0.000169  20.33        |det J| baja 10× y ‖q̇‖ sube ~10×
0.001  -1.7e-05   197.36
```

## 7. Dinámica (`dynamics.py`)

Modelo Lagrangiano `τ = M(q) q̈ + c(q, q̇) + g(q)` con masas, centros de masa e inercias por
CAD de Truc y Lam (2020) en los marcos DH de los eslabones 1 a 6, más la pinza **SMC MHZ2-16D** (115 g, centro de masa a 0.040 m de la brida) fusionada con el eslabón 6 por ejes paralelos (`LINKS`; `LINKS_NO_GRIPPER` reproduce el paper):

- `mass_matrix(q)`: `Σ mᵢ JvᵀJv + Jwᵀ R I Rᵀ Jw` (simétrica y definida positiva).
- `gravity_vector(q)`: `Σ mᵢ g Jv[z]`.
- `coriolis_vector(q, q̇)`: `Ṁ q̇ − ½ ∇q(q̇ᵀ M q̇)` por diferencias finitas.
- `inverse_dynamics(q, q̇, q̈)` y `cartesian_demand(q, twist, accel)`, que calcula
  `(q̇, q̈, τ)` necesarios para seguir un twist y una aceleración cartesianos.

Los parámetros son aproximaciones: sirven para ver la **tendencia** (divergencia), no para
identificar el robot real. El torque de la junta 4 crece ×100 por década de `q5`.

## 8. Autocolisión (`kinematics/collision.py`)

`CollisionChecker` carga los meshes `collision` del CAD real, muestrea su superficie y, para
una postura `q`, mide la distancia mínima entre piezas no vecinas más el plano de la mesa
(`z = 0`).

```python
from irb120_hito2.kinematics.collision import CollisionChecker
c = CollisionChecker()
c.in_collision(np.deg2rad([30, -20, 15, 40, -35, 60]))            # False
c.colliding_pairs(np.deg2rad([0, 100, 60, 0, 0, 0]))
# [('base_link', 'link_4'), ('mesa', 'gripper_link')]
```

El nodo la usa para descartar soluciones de Pieper en colisión. Es una prueba conservadora
de proximidad superficial; no calcula interpenetración exacta.

## 9. Nodo `ik_trajectory_node`

Al recibir una pose: (1) valida el `frame_id` (`base_link`) y el cuaternión; (2) llama a
`inverse_kinematics_tcp` tomando la postura actual como referencia; (3) si
`check_collisions`, queda con la primera solución sin colisión; (4) calcula el error FK de
la elegida; (5) planifica el LSPB desde la postura actual y publica el plan completo; (6) un
temporizador a 50 Hz publica `q(t)` en grados hasta `tf` y anuncia "Trayectoria completada".

Una pose nueva durante un movimiento replanifica desde la postura actual. Los errores
(sin solución, todas en colisión, cuaternión nulo, sin `/joint_states`) se informan en
`/irb120/ik_status` y el robot no se mueve.

### Ejemplo E: sesión completa

```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select irb120_hito1 irb120_hito2
source install/setup.bash
ros2 launch irb120_hito2 hito2.launch.py            # RViz + validador + nodo IK
```

En otra terminal (con los dos `source`):

```bash
ros2 run irb120_hito2 send_target 0.25 -0.15 0.30   # x y z; por defecto pinza hacia abajo
ros2 run irb120_hito2 send_target 0.30 0.10 0.25 0 180 45   # con roll pitch yaw en grados
ros2 topic echo /irb120/ik_status
```

Salida de estado esperada para el primer comando:

```text
1 soluciones Pieper; elegida frente/arriba/q5- q=[-30.96, -1.21, 30.74, -0.0, 60.47, -30.96] deg
| error FK=1.36e-16 m | LSPB tf=1.19 s tb=0.56 s
```

Casos rechazados:

```text
SIN SOLUCION para (5.000, 0.000, 0.000) m: fuera del alcance o de los limites articulares.
1 soluciones Pieper, todas en colision (p. ej. [('mesa', 'gripper_link')]); no se mueve el robot.
```

(el segundo con `send_target 0.20 0.0 -0.05`, bajo la mesa).

`send_target X Y Z [R P Y]` usa `rpy_deg` por defecto `0 180 0`, que apunta el eje Z de la
pinza hacia abajo. `rpy_to_matrix` usa la convención ROS `Rz(yaw)·Ry(pitch)·Rx(roll)`.

## 10. Notebook del pasaporte

`notebooks/hito2_singularidad_q5.ipynb` (ya ejecutado, con salidas):

1. Verifica `det J = −sin q5 · det Jp_brazo` en posturas aleatorias (error ~1e-17).
2. Barre `q5 → 1e-6`: `σmin(J)`, `cond(J)` y `‖q̇‖` (pendiente log-log medida: −0.97).
3. Muestra el `SingularityError` en `q5 = 0` exacto (rango 5).
4. Grafica `‖q̈‖` y el torque dinámico (pendiente medida: −2.00).
5. Muestra Pieper en muñeca singular: con cualquier `q4` de referencia, `q4 + q6` queda
   fijo (70° en el ejemplo).
6. Dibuja un perfil LSPB hacia una postura cercana a la singularidad.

Para reproducirlo:

```bash
python3 -m venv --system-site-packages .venv-notebooks
.venv-notebooks/bin/pip install -r notebooks/requirements.txt
.venv-notebooks/bin/jupyter lab notebooks/hito2_singularidad_q5.ipynb
```

`notebooks/build_notebook.py` regenera el `.ipynb` desde cero.

## 11. Pruebas y verificación

```bash
bash scripts/check_proyecto.sh        # compila, 39 pruebas, verify_model, xacro
```

| Archivo | Qué comprueba |
|---|---|
| `test_pieper.py` | 200 posturas: recupera `q`, cada solución llega a la pose; alcance; muñeca singular |
| `test_lspb.py` | Extremos con velocidad 0, límites, continuidad, sincronía, integral de la velocidad |
| `test_singularity.py` | `det J = −sin q5 · det Jp`, rango, 1/sin q5, M simétrica y definida positiva, Coriolis, torque |
| `test_collision.py` | Poses de validación libres; agachado y muñeca plegada colisionan |

## 12. Preguntas probables en la defensa

**¿Por qué Pieper y no una IK numérica?** La Guía prohíbe resolvedores automáticos y la
muñeca esférica permite una solución cerrada, exacta y con todas las configuraciones.

**¿Por qué hay hasta 8 soluciones?** 2 (brazo frente/atrás) × 2 (codo) × 2 (muñeca ±q5).

**¿Cómo se elige una?** La más cercana a la postura actual que respete límites y no
colisione, para minimizar el movimiento.

**¿Por qué LSPB y no un polinomio?** Acota velocidad y aceleración con parámetros directos
y el tiempo mínimo se calcula en forma cerrada (más bisección).

**¿Qué pasa en `q5 = 0`?** `J` pierde rango, `q̇` y `τ` divergen (`1/sin q5` y `1/sin² q5`)
y Pieper solo determina `q4 + q6`.

**¿Qué pinza se asumió?** La SMC MHZ2-16D: pinza paralela neumática de doble efecto, muy
usada en robots pequeños, de 115 g, dentro de la carga adicional de 0.3 kg del IRB 120.
Su masa es dato de hoja de datos; su geometría en el URDF sigue siendo paramétrica (el CAD
lo publica SMC en su web).

**¿Qué tan fiable es la dinámica?** Cualitativamente sí; cuantitativamente no, porque los
parámetros inerciales son estimaciones por CAD.
