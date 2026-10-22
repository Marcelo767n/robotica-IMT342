# 09. Guía de estudio del código: qué hace cada archivo y cada función

Los archivos 01 a 08 explican la **matemática** de cada criterio de la rúbrica. Este archivo explica el **código**:
qué hay en cada archivo, qué recibe y qué devuelve cada función, en qué orden se llaman y cómo se comprueba que
funcionan. Si entiendes este documento, puedes responder "¿dónde está eso en el código?" sobre cualquier parte.

---

## 0. Plan de estudio sugerido (unas 6 horas)

| Paso | Qué leer | Tiempo | Objetivo |
|---|---|---|---|
| 1 | §1 (mapa) y §2 (flujo de datos) de este archivo | 20 min | Tener el "plano" del proyecto en la cabeza |
| 2 | `08_ejemplo_resuelto_a_mano.md`, con calculadora | 60 min | Hacer el pipeline a mano una vez |
| 3 | §3.1 `dh.py` + `01_modelo_DH_y_FK.md` | 30 min | FK: la base de todo |
| 4 | §3.3 `pieper.py` + `02_A_pieper.md` | 60 min | La parte más larga del código |
| 5 | §3.4 `validation.py` + `03_B_validacion_fk.md` | 20 min | |
| 6 | §3.5 `lspb.py` + `04_C_lspb.md` | 40 min | |
| 7 | §3.6 `jacobian.py` + `05` y `06` | 60 min | Rango, SVD y singularidad |
| 8 | §3.7–3.8 `dynamics.py`, `dynamics_1r.py` + `07` | 40 min | |
| 9 | §4: abrir el notebook y ejecutarlo sección por sección | 40 min | Ver todo funcionando |
| 10 | §6: autoevaluación, **sin mirar** | 30 min | Detectar qué falta repasar |

**Ejercicio práctico obligatorio:** cambiar `POSE_OBJETIVO` en el notebook por otra pose, por ejemplo
`(0.30, -0.25, 0.45, 0, 135, -40)`, ejecutar *Restart & Run All* y explicar en voz alta qué cambió en cada sección.
Es exactamente lo que pasará en la defensa.

---

## 1. Mapa del proyecto

```text
hito2/
├── irb120/                      ← el paquete: TODA la matemática vive aquí
│   ├── dh.py                    1. Datos del robot + cinemática directa (FK)
│   ├── transforms.py            2. Utilidades de rotaciones (rpy ↔ matriz)
│   ├── pieper.py                3. Cinemática inversa (A) + análisis de alcanzabilidad + selección
│   ├── validation.py            4. Validación de candidatos por FK (B)
│   ├── lspb.py                  5. Trayectoria LSPB (C)
│   ├── jacobian.py              6. Jacobiano, validación numérica, rango y singularidad (D)
│   ├── dynamics.py              7. Modelo dinámico COMPLETO de 6 GDL (fuente de datos y validación)
│   ├── rosi_model.py            9. Modelo OFICIAL de ROS-Industrial (verificación geométrica independiente de la FK)
│   ├── urdf_chain.py           10. Evaluador del URDF del Hito 1 (verificación de implementación)
│   └── dynamics_1r.py           8. Modelo 1R del hombro (E)
├── Hito2_IRB120_pipeline.ipynb  ← ENTREGABLE: llama al paquete en orden y grafica
├── build_pipeline_notebook.py   ← script que ESCRIBE y EJECUTA el notebook
├── analizar_pose.py             ← herramienta de terminal: ¿es alcanzable esta pose?
├── tests/                       ← 56 pruebas automáticas (pytest)
├── datos/irb120.urdf            ← URDF del Hito 1, derivado de DH (solo verifica la implementación)
├── figuras/  resultados/        ← salidas del notebook (las usa el informe IEEE)
├── explicacion/                 ← estos documentos
└── anexos/                      ← versión anterior del hito (no es el entregable)
```

**Regla de dependencias** (quién importa a quién; nunca al revés):

```text
dh.py ──► transforms.py
  │
  ├──► validation.py ──► pieper.py ──(select_solution)──► jacobian.py
  ├──► lspb.py
  └──► jacobian.py ──► dynamics.py ──► dynamics_1r.py
```

`dh.py` no depende de nadie. Si `dh.py` está bien (FK correcta), todo lo demás se puede validar contra él. Por eso
**la FK es el "patrón" con el que se verifica todo**: Pieper (B), el Jacobiano numérico (D) y la ubicación de los
centros de masa (E).

---

## 2. Flujo de datos en el notebook

Estas son las variables globales del notebook. Saber de dónde sale cada una equivale a saber explicar el pipeline
(criterio G1).

| Variable | Tipo | Se crea en | Con qué función | Se usa en |
|---|---|---|---|---|
| `Q_HOME` | vector (6,) rad | §1.2 | `HOME_Q` de `dh.py` | Pieper (referencia), LSPB ($q_0$) |
| `T_HOME` | matriz 4×4 | §1.2 | `forward_kinematics_tcp(Q_HOME)` | Pieper de la pose inicial |
| `T_D` | matriz 4×4 | §1.3 | `pose_from_xyz_rpy_deg(*POSE_OBJETIVO)` | Pieper, validación |
| `REPORTS` | dict de `PoseReport` | §2 | `analyze_pose(T, Q_HOME)` | tablas, figuras, selección |
| `DECISIONS` | lista de 8 `BranchDecision` | §2.2 | `rank_candidates(REPORTS["Objetivo"], Q_HOME)` | figura 3D y tabla de decisión |
| `chosen` | `Candidate` | §4 | `select_solution(REPORTS["Objetivo"], Q_HOME)` | — |
| `Q0`, `QF` | vectores (6,) | §4 | `Q_HOME`, `chosen.q` | LSPB |
| `VMAX`, `AMAX` | vectores (6,) | §5 | `default_limits(SPEED_SCALE, RAMP_TIME_S)` | LSPB, verificación |
| `TRAJ` | `LspbTrajectory` | §5 | `plan_lspb(Q0, QF, VMAX, AMAX)` | todo lo que sigue |
| `T_GRID`, `Q_T`, `QD_T`, `QDD_T` | arreglos (N,) y (N,6) | §5 | `TRAJ.sample_many(T_GRID)` | Jacobiano, dinámica |
| `TWIST_T`, `RANK_T` | (N,6), (N,) | §6 | `tcp_twist`, `rank_analysis` | gráficas D |
| `EXP` | lista de dicts | §7 | experimento $q_5 \to 0$ (independiente) | tablas y figuras D |
| `MODEL` | `OneRModel` | §8 | `shoulder_model((Q0+QF)/2)` | torque |
| `TAU_IN`, `TAU_G`, `TAU` | (N,) | §8 | `MODEL.torque_components(Q_T[:,1], QDD_T[:,1])` | gráficas E |
| `CHECKS` | lista | todas | `check(etapa, texto, condición)` | resumen §9 |

**Idea clave:** la §7 (singularidad) es la única que **no** usa la trayectoria: la guía exige que el experimento de
singularidad sea **independiente**.

---

## 3. Archivo por archivo

Convención de las tablas: **Entrada → Salida**. "rad", "m" y "s" son unidades. `(6,)` es un vector de 6 elementos y
`4×4` una matriz homogénea.

### 3.1 `irb120/dh.py`: datos del robot y cinemática directa

**Constantes (datos, no cálculos):**

| Nombre | Valor | Fuente |
|---|---|---|
| `DH_PARAMETERS` | 6 filas `DHParameter(d, a, alpha, offset)` | Bahani et al. 2023 |
| `TCP_Z_M` | 0.150 | decisión del equipo |
| `HOME_Q` | `zeros(6)` | posición de calibración ABB |
| `JOINT_LIMITS_DEG` / `_RAD` | 6×2 | datasheet ABB |
| `MAX_SPEED_DEG_S` / `_RAD_S` | (250, 250, 250, 320, 320, 420) °/s | datasheet ABB |

`DHParameter` es un `@dataclass(frozen=True)`: una "ficha" inmutable con cuatro campos. `frozen` impide modificar la
tabla por accidente.

| Función | Entrada → Salida | Qué hace, paso a paso |
|---|---|---|
| `dh_transform(theta, p)` | ángulo ABB (rad), fila DH → 4×4 | 1) suma el offset de la fila; 2) arma $R_z(\theta)T_z(d)T_x(a)R_x(\alpha)$ elemento por elemento |
| `_joint_vector(q)` | cualquier iterable → (6,) | valida que haya 6 valores finitos; si no, `ValueError` |
| `forward_kinematics(q)` | (6,) rad → 4×4 | parte de $I$ y multiplica las 6 matrices DH: base → brida (`tool0`) |
| `tcp_transform()` | — → 4×4 | traslación pura $T_z(0.150)$ |
| `forward_kinematics_tcp(q)` | (6,) → 4×4 | `forward_kinematics(q) @ tcp_transform()`: base → TCP |
| `position_error_m(A, B)` | 4×4, 4×4 → m | norma de la diferencia de las columnas de posición |
| `rotation_error_rad(A, B)` | 4×4, 4×4 → rad | ángulo de $R_A^T R_B$ con `atan2(sin, cos)` |

**Dónde se usa:** prácticamente en todos los archivos. **Prueba:** `tests/test_dh.py`, que verifica que la FK de
$q = 0$ da (0.374, 0, 0.630), que $R$ es ortonormal con $\det = 1$ y que rechaza 5 ángulos.

### 3.2 `irb120/transforms.py`: rotaciones

| Función | Entrada → Salida | Uso en el proyecto |
|---|---|---|
| `rpy_to_matrix(r, p, y)` | rad → 3×3 | $R = R_z(y)R_y(p)R_x(r)$ |
| `pose_from_xyz_rpy_deg(x, y, z, r, p, yaw)` | m, ° → 4×4 | **arma la pose del docente** ($T_d$) |
| `matrix_to_rpy_deg(R)` | 3×3 → (r, p, y) ° | mostrar orientaciones (pose inicial) |
| `pose_matrix(pos, R)` | → 4×4 | junta $R$ y $p$ en una matriz homogénea |
| `assert_rigid_transform(T)` | 4×4 → 4×4 o `ValueError` | **valida la entrada**: forma, finitud, última fila, $R^TR = I$, $\det R = 1$. La llaman `analyze_pose` y `enumerate_candidates` |
| `quaternion_to_matrix`, `matrix_to_quaternion` | | heredadas del Hito 1 (ROS); no se usan en el Hito 2 |

### 3.3 `irb120/pieper.py`: cinemática inversa (criterio A)

**Constantes geométricas** calculadas de la tabla DH: `D1 = 0.290`, `L2 = 0.270`, `A3 = 0.070`, `D4 = 0.302`,
`D6 = 0.072`, `L3 = √(D4² + A3²) = 0.31001`, `DELTA = atan2(A3, D4) = 13.05°`, `REACH_MIN_M = |L2 − L3|` y
`REACH_MAX_M = L2 + L3`.

**Tipos de datos:**

- `Candidate`: **una de las 8 ramas**, con `branch` (1 a 8), `arm`, `elbow`, `wrist`, `real`, `q_raw` (ángulos
  envueltos), `q` (ajustado a límites o `None`), `out_of_limits` (juntas que no caben), `singular_wrist` y
  `cos_elbow` (el $c$ de la ley de cosenos). La propiedad `within_limits` es `real and q is not None`.
- `IKSolution`: una solución admisible "limpia" (q, brazo, codo, muñeca). La devuelve `inverse_kinematics`.
- `PoseReport`: **todo lo que se sabe de una pose**: `candidates` (8), `checks` (8 `FKCheck` o `None`),
  `wrist_center` y `shoulder_to_wrist_m`. Propiedades: `admissible`, `reachable`, `geometrically_reachable`,
  `verdict` (texto) y `table()` (filas para imprimir).

**Funciones, en el orden en que se ejecutan dentro de `analyze_pose`:**

```text
analyze_pose(T_tcp, q_ref)
 ├─ tool0_from_tcp(T_tcp)              T_tool0 = T_tcp · Tz(0.150)⁻¹
 ├─ enumerate_candidates(T_tool0, q_ref)
 │    ├─ wrist_center(T_tool0)         p_W = p_tool0 − d6·z6
 │    ├─ _arm_branches(p_W)            4 ramas (frente/atrás × arriba/abajo): q1, q2, q3, real?, c
 │    └─ por cada rama real:
 │         ├─ _rotation_0_3(q1,q2,q3)  R_0^3 con las 3 primeras matrices DH
 │         ├─ R_3^6 = R_0^3ᵀ · R
 │         ├─ _wrist_solutions(R_3^6)  2 ramas (q5+, q5−): q4, q5, q6 por Euler ZYZ
 │         └─ _fit_to_limits(...)      por junta: q + 2πk dentro de límites (o None)
 ├─ fk_check(T_tcp, q) por cada rama real     (validation.py)
 └─ PoseReport(...)
```

| Función | Detalle importante para explicarla |
|---|---|
| `_wrap_pi(a)` | lleva cualquier ángulo a $(-\pi, \pi]$ |
| `_fit_to_limits(a, lo, hi, ref)` | prueba $a + 2\pi k$ con $k = -3..3$ y elige el que cae en $[lo, hi]$ y está más cerca de `ref`. Importa sobre todo para $q_6$ (±400°) |
| `_arm_branches(p_W)` | para frente y atrás calcula $c$; si $|c| > 1$ marca las 2 ramas de codo como **no reales** (`nan`). Si no, `asin(-c)` da el codo "arriba" y `π - asin(-c)` el "abajo"; luego $q_2$ con dos `atan2` |
| `_wrist_solutions(R36, q4_ref)` | caso normal: dos soluciones según el signo de $\sin\beta$; como $\beta = -q_5$, la etiqueta `q5+`/`q5-` se asigna por el signo **real** de $q_5$. Caso **singular** ($\sin\beta < 10^{-9}$): $q_5 = 0$ y solo $q_4 + q_6$ está definido, así que se toma $q_4$ = referencia |
| `enumerate_candidates` | **siempre devuelve 8** `Candidate`, en orden fijo; las ramas no reales quedan con `q_raw = None` |
| `inverse_kinematics(T_tool0, ref)` | atajo: solo las admisibles, ordenadas por cercanía a `ref` y sin duplicados |
| `inverse_kinematics_tcp` | lo mismo, partiendo de la pose del TCP |
| `analyze_pose(T_tcp, ref)` | la función principal: enumera, valida por FK y arma el reporte |
| `limit_margin_deg(q)` | menor distancia de alguna junta a su límite, en grados |
| `rank_candidates(report, ref)` | **evalúa las 8 ramas** y devuelve una lista de `BranchDecision`: admisible, $\sigma_{\min}$, margen, costo $\lVert W(q - ref)\rVert$, $t_f$ del LSPB, estado (`ELEGIDA` / `apta` / motivo del descarte) y puesto. Filtros: admisible → $\sigma_{\min} \ge 0.01$ → margen $\ge 5°$ → menor costo |
| `select_solution(report, ref)` | devuelve la rama del puesto 1 de `rank_candidates` |

**Pruebas:** `tests/test_pieper.py` tiene 16 pruebas. Por ejemplo: las 8 ramas siempre presentes; todas las ramas
reales pasan FK; pose fuera de alcance; pose bloqueada por límites; recuperación del home; singularidad de muñeca.

### 3.4 `irb120/validation.py`: validación por FK (criterio B)

| Nombre | Qué es |
|---|---|
| `POSITION_TOL_M = ROTATION_TOL_RAD = 1e-6` | criterio de aceptación |
| `FKCheck` | resultado: `position_error_m`, `rotation_error_rad`, `frobenius_error`; propiedad `accepted` (los dos primeros < 1e-6) |
| `fk_check(T_d, q, tcp=True)` | calcula la FK de `q` (al TCP o a la brida) y la compara con `T_d` |
| `RoundTripStats` / `round_trip_test(n, seed)` | genera `n` configuraciones aleatorias dentro de límites → FK → IK → FK. Cuenta cuántas se resuelven y cuántas recuperan el $q$ original, y registra el peor error |

`round_trip_test` importa `pieper` **dentro** de la función. Es a propósito: `pieper` importa `validation`, y si
`validation` importara `pieper` arriba del archivo se formaría un ciclo de imports.

### 3.5 `irb120/lspb.py`: trayectoria (criterio C)

| Nombre | Entrada → Salida | Qué hace |
|---|---|---|
| `LspbTrajectory(q0, qf, tf, tb)` | dataclass | guarda los 4 parámetros; todo lo demás se deriva de ellos |
| `.displacement` | → (6,) | $D = q_f - q_0$ |
| `.cruise_velocity` | → (6,) | $V = D/(t_f - t_b)$ |
| `.blend_acceleration` | → (6,) | $a = V/t_b$ |
| `.sample(t)` | s → (q, q̇, q̈) | las 3 fórmulas por tramo (`if t < tb … elif … else`); fuera de $[0, t_f]$ devuelve reposo $(q_0 \text{ o } q_f, 0, 0)$ |
| `.sample_many(times)` | (N,) → tres (N,6) | `sample` sobre muchos instantes, para graficar |
| `.phase(t)` | s → texto | `"acelera"`, `"crucero"`, `"frena"` o `"reposo"` (fuera de $[0, t_f]$) |
| `plan_lspb(q0, qf, vmax, amax)` | → `LspbTrajectory` | calcula $K = \max D/a_{\max}$ y $D_v = \max D/v_{\max}$; busca por **bisección** el menor $t_f$ factible; $t_b$ es la raíz menor de $t_b(t_f - t_b) = K$ |
| `default_limits(scale, ramp)` | → (vmax, amax) | vmax = scale × datasheet; amax = vmax / ramp |
| `LspbCheck` / `check_trajectory(traj, vmax, amax)` | → reporte | errores en las fronteras, velocidades en los extremos, saltos en $t_b$ y $t_f - t_b$, márgenes de límites; `passed` lo resume |

**Detalle de implementación:** dentro de `plan_lspb` hay dos funciones internas, `blend_time(tf)` y `feasible(tf)`.
La bisección hace 100 iteraciones de "partir el intervalo a la mitad y quedarse con la mitad que sigue siendo
factible". **Pruebas:** `tests/test_lspb.py` (10).

### 3.6 `irb120/jacobian.py`: Jacobiano y singularidad (criterio D)

| Función | Entrada → Salida | Qué hace |
|---|---|---|
| `joint_frames(q)` | (6,) → lista de 7 matrices 4×4 | $T_0^0 = I, T_0^1, \dots, T_0^6$ (FK acumulada) |
| `geometric_jacobian(q, ref)` | → 6×6 | columna $i$ = $[z_{i-1}\times(p - o_{i-1});\ z_{i-1}]$; `ref` puede ser `"tcp"`, `"tool0"` o `"wrist"` |
| `numerical_jacobian(q)` | → 6×6 | **validación**: diferencias centrales de la FK; la parte angular sale de $\dot RR^T$ con `_vee` |
| `tcp_twist(q, q̇)` | → (6,) | $\dot x = J\dot q$ |
| `rank_analysis(J, tol)` | → `RankAnalysis` | SVD; `rank` = número de $\sigma > 10^{-6}$; `lost_twist_directions` (columnas de $U$) y `null_joint_motions` (columnas de $V$) |
| `weakest_directions(J)` | → ($\sigma_{\min}$, $u$, $v$) | la dirección más débil, para la amplificación $1/\sigma_{\min}$ |
| `determinant`, `smallest_singular_value`, `condition_number` | → número | complementos |
| `arm_position_determinant(q)` | → número | $\det$ del bloque 3×3 del brazo (referencia en $W$) = $L_2L_3\cos(q_3 - \delta)\,r_W$ |
| `solve_with_jacobian`, `joint_velocity` | → $\dot q$ | resuelven $J\dot q = \dot x$; lanzan `SingularityError` si $\sigma_{\min} < 10^{-9}$ |
| `jacobian_dot(q, q̇)` | → 6×6 | $\dot J$ numérico; solo lo usa `dynamics.cartesian_demand` (caso de seguimiento cartesiano de los anexos y de `test_singularity.py`) |

**Pruebas:** `tests/test_jacobian.py` (7) y `tests/test_singularity.py` (8).

### 3.7 `irb120/dynamics.py`: modelo completo de 6 GDL (referencia)

En la rúbrica **no** es el modelo que se evalúa (ese es el 1R), pero cumple dos funciones:

1. Guarda los **datos CAD** por eslabón (`_PAPER_LINKS`: masa, centro de masa e inercia de Truc y Lam 2020) y la
   pinza (`GRIPPER_MASS_KG`, `GRIPPER_COM_M`). `_with_gripper` suma la pinza al eslabón 6 usando
   `_parallel_axis` (Steiner).
2. **Valida** el 1R: `mass_matrix(q)` da $M(q)$, `gravity_vector(q)` da $g(q)$ y `inverse_dynamics(q, q̇, q̈)` da
   $\tau = M\ddot q + c + g$. `coriolis_vector` calcula $c$ por diferencias finitas de $M$.

`_com_jacobians(q)` es el Jacobiano de cada centro de masa: lo mismo que `geometric_jacobian`, pero apuntando al
centro de masa de cada eslabón en lugar del TCP.

### 3.8 `irb120/dynamics_1r.py`: modelo 1R del hombro (criterio E)

| Nombre | Qué es |
|---|---|
| `OneRModel` | `mass_kg` ($m$), `lc_m` ($\ell_c$), `inertia_com_kg_m2` ($I_c$), `phi0_rad` ($\varphi_0$), `q_ref` |
| `.inertia_kg_m2` | $J = I_c + m\ell_c^2$ |
| `.pendulum_angle(q2)` | $\theta = q_2 + \varphi_0$ |
| `.torque_components(q2, q̈2)` | → ($\tau_{in}$, $\tau_g$, $\tau$) |
| `.max_gravity_torque` | $mg\ell_c$ |
| `shoulder_model(q_ref)` | **construye el modelo** a partir de los datos CAD: (1) ejes con `joint_frames`; (2) por eslabón 2 a 6, su centro de masa e inercia en la base; (3) suma de masas y del momento de primer orden; (4) $\ell_c$ = distancia perpendicular al eje 2; (5) $J$ = inercias proyectadas en el eje + Steiner; (6) $\theta$ con `atan2` respecto de la vertical inferior |

**Pruebas:** `tests/test_dynamics_1r.py` (4): por ejemplo, $J = M_{22}$ y $\tau_g = g_2$ del modelo completo, y en
crucero $\tau = \tau_g \neq 0$.

### 3.8b Verificaciones externas de la FK: `rosi_model.py` y `urdf_chain.py`

- **`irb120/rosi_model.py`** guarda la tabla de juntas del **modelo oficial de ROS-Industrial** (`ROSI_JOINTS`: origen
  y eje de cada junta, copiados del xacro de `abb_irb120_support`, con la URL en `SOURCE_URL`).
  `rosi_forward_kinematics(q)` multiplica `Trasl(xyz)·Rot(eje, q)` por junta (con `_axis_rotation`, fórmula de
  Rodrigues) y al final `Ry(90°)` para `tool0`. **Es una fuente geométrica independiente:** si coincide con
  `forward_kinematics`, la tabla DH es correcta.
- **`irb120/urdf_chain.py` + `datos/irb120.urdf`** son copias del Hito 1. `load_joints` lee cada `<joint>` del XML
  y `chain_transform` encadena origins y ejes. Ese URDF **se derivó de nuestra tabla DH**, así que coincidir con él
  solo prueba que el **código** está bien, no la geometría.

Las dos están en el notebook §3.1 y en `tests/test_urdf_crosscheck.py`.

### 3.9 `analizar_pose.py`: herramienta de terminal

```bash
python analizar_pose.py X Y Z ROLL PITCH YAW
```

`main()`: lee los 6 números con `argparse`, arma $T_d$ con `pose_from_xyz_rpy_deg`, llama a `analyze_pose`, imprime la
tabla de 8 ramas y el veredicto, y llama a `select_solution(report, HOME_Q)`. Es útil en la defensa para responder en
segundos si una pose es alcanzable.

### 3.10 `build_pipeline_notebook.py`: el generador del notebook

El notebook **no se edita a mano**: este script lo escribe celda por celda (`md(...)` y `code(...)`) con `nbformat`,
lo **ejecuta** de principio a fin con `ExecutePreprocessor` y lo guarda ya ejecutado. Ventaja: siempre se puede
reconstruir desde cero y se garantiza que corre completo (criterio F). Si quieren cambiar un texto del notebook,
cámbienlo en este script y vuelvan a ejecutarlo (`python build_pipeline_notebook.py`).

### 3.11 `tests/`: las 56 pruebas

`python -m pytest -q tests`. Cada archivo `test_X.py` prueba el módulo `X.py`. Una prueba es una función
`test_...` que llama al código y usa `assert...` para comprobar un resultado conocido: la FK de $q = 0$, que un $q$
aleatorio se recupera, que el rango cae a 5, etc. Si alguien rompe una fórmula, la prueba lo detecta.

---

## 4. El notebook, sección por sección

| § | Qué calcula | Qué verifica (`check`) | Rúbrica |
|---|---|---|---|
| 0 | importa el paquete, define `save()` y `check()` | — | F |
| 1.1 | imprime la tabla DH, los límites y la FK(0) | FK(0) = datasheet | — |
| 1.2 | `T_HOME` = FK(posición de calibración) | — | — |
| 1.3 | **ENTRADA** `POSE_OBJETIVO` → `T_D` | — | — |
| 2 | `analyze_pose` de las 2 poses; tablas de 8 ramas; figura de ramas en el plano; **§2.2: las 8 configuraciones en 3D** | 8 ramas por pose; home recuperado; objetivo alcanzable (si no, se detiene con un mensaje) | A |
| 3 | errores FK de todas las ramas reales; candidatos fabricados con error; ida y vuelta (1000); **§3.1: DH frente al modelo oficial ROS-Industrial y al URDF del Hito 1** | todas pasan; los erróneos se rechazan | B |
| 4 | `rank_candidates` sobre las 8 ramas → tabla de decisión → `QF` | la elegida reproduce $T_d$ | A |
| 5 | `plan_lspb`; tabla por junta; 3 gráficas alineadas; uso de límites; **§5.1: movimiento 3D y trayectoria del TCP** | fronteras, reposo, continuidad, límites, $t_b \le t_f/2$ | C |
| 6 | $J(q_f)$ frente a numérico; columnas a mano; $\dot x(t)$ y rango a lo largo del LSPB | 4 verificaciones | D |
| 7 | experimento $q_5 \to 0$; SVD; espacio nulo; amplificación; codo | rango 6 → 5, factorización del det, $\dot q_4 = -\dot q_6$, pendiente −1, torque estático → 0 | D |
| 8 | `shoulder_model`; $\tau(t)$ por componentes; 1R frente al completo; efecto de la velocidad | $J = M_{22}$, crucero ≠ 0, escala $\lambda^2$ | E |
| 9 | tabla singularidad frente a torque; resumen de verificaciones; **exporta `resultados/`** para el informe | — | F |

---

## 5. Recursos de Python y NumPy que aparecen (para no trabarse leyendo)

| Recurso | Dónde | Qué significa |
|---|---|---|
| `@dataclass(frozen=True)` | casi todos los archivos | clase "contenedor de datos" inmutable; genera `__init__` automáticamente |
| `@property` | `Candidate.within_limits`, `LspbTrajectory.cruise_velocity`… | un método que se lee como atributo (sin paréntesis) |
| `A @ B` | todos | producto de matrices |
| `np.cross(a, b)` | Jacobiano | producto vectorial $a \times b$ |
| `np.linalg.svd(J)` | `rank_analysis` | devuelve $U$, $\sigma$ (ordenados de mayor a menor) y $V^T$ |
| `atan2(y, x)` | Pieper | ángulo con cuadrante correcto |
| `np.deg2rad`, `np.rad2deg` | todos | conversión de unidades (internamente todo va en rad) |
| `T[:3, :3]`, `T[:3, 3]`, `T[:3, 2]` | todos | rotación, posición y eje $z$ de una matriz homogénea |
| `Q_T[:, 1]` | notebook | columna de la junta 2 en todos los instantes |
| `x if cond else y` | varios | if en una sola línea |

---

## 6. Autoevaluación (responder sin mirar; las respuestas están en §3 y en 01–08)

**Archivos y funciones**
1. ¿Qué función arma la pose del docente a partir de x, y, z, roll, pitch y yaw? ¿En qué archivo está?
2. ¿Por qué `enumerate_candidates` devuelve siempre 8 elementos, aunque la pose sea inalcanzable?
3. ¿Qué diferencia hay entre `q_raw` y `q` en un `Candidate`?
4. ¿Qué hace `_fit_to_limits` y por qué importa sobre todo para la junta 6?
5. ¿Por qué `round_trip_test` importa `pieper` dentro de la función?
6. ¿Qué devuelve `rank_analysis` y qué significan `null_joint_motions` y `lost_twist_directions`?
7. ¿Qué dos números definen por completo un `LspbTrajectory` además de $q_0$ y $q_f$?
8. ¿Cómo encuentra `plan_lspb` el $t_f$ mínimo?
9. ¿Por qué existe `dynamics.py` si la rúbrica pide el modelo 1R?
10. ¿Qué hace `build_pipeline_notebook.py` y por qué el notebook no se edita a mano?

**Flujo (G1)**
11. Recorre el pipeline nombrando, para cada flecha, la función que la implementa.
12. ¿Qué sección del notebook no usa la trayectoria y por qué?

**Validación (G3)**
13. Nombra una validación por cada criterio, de A a E, y la prueba de `tests/` que la respalda.

**Transferencia (G4):** elige el módulo que **menos** conoces y explícaselo a otro integrante en 3 minutos, sin
mirar.
