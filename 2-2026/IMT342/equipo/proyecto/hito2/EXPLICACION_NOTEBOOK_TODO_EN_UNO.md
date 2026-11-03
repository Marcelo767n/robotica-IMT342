# Guía del notebook `Hito2_IRB120_todo_en_uno.ipynb`

Explica **cómo está organizado** el notebook y **qué hace el código, parte por parte**. Sirve para estudiarlo y para la
defensa individual (G1 pipeline, G2 matemática, G3 validación, G4 transferencia).

> Los números de este documento salen de la ejecución del notebook con las entradas por defecto
> (`POSE_OBJETIVO = (0.40, 0.10, 0.35, 0, 180, 0)`, `SPEED_SCALE = 0.25`, `RAMP_TIME_S = 0.25`). Si cambias las entradas,
> cambian los números, no la estructura.

---

## 1. Qué es y cómo se usa

Es **un solo pipeline continuo** del ABB IRB 120, tal como lo pide la guía del docente:

```
Td → Pieper → q → LSPB → q(t), q̇(t), q̈(t) → J(q) → Singularidades → Dinámica 1R → τ(t)
```

El notebook contiene **todo el código**: no importa el paquete `irb120/`. Es la misma lógica que `Hito2_IRB120_pipeline.ipynb`
y que los módulos de `irb120/`, que siguen intactos.

**Para ejecutarlo**

1. Abrir el notebook desde la carpeta `hito2/` (la sección Anexo lee `datos/irb120.urdf`).
2. Tener Python 3 con `numpy` y `matplotlib`.
3. *Restart & Run All*. Si una verificación falla, el notebook se detiene en esa celda (`assert` dentro de `check`).

Las figuras se guardan en `hito2/figuras_todo_en_uno/` (PDF y PNG), para no pisar las de `hito2/figuras/` del informe IEEE.

**Entradas editables** (celda «1.3 ENTRADA»):

| Variable | Qué es | Valor por defecto |
|---|---|---|
| `POSE_OBJETIVO` | pose del TCP: `(x, y, z [m], roll, pitch, yaw [°])` o una matriz 4×4 | `(0.40, 0.10, 0.35, 0, 180, 0)` |
| `SPEED_SCALE` | fracción de la velocidad máxima del datasheet | `0.25` |
| `RAMP_TIME_S` | supuesto de diseño: tiempo para que un eje alcance su `vmax` | `0.25` s |

**Convenciones:** ángulos en rad (en grados solo al mostrarlos), longitudes en m, tiempo en s, torque en N·m. Marco
`base_link` con z hacia arriba, gravedad hacia −z (9.81 m/s²). TCP a **0.150 m** de la brida `tool0`, sobre z₆.

---

## 2. Mapa del notebook

76 celdas. Cada sección corresponde a un criterio de la rúbrica (peso entre paréntesis).

| Sección | Criterio | Qué demuestra | Código que se define ahí |
|---|---|---|---|
| Portada y *setup* | F (5 %) | pipeline, convenciones, `check()` y `save()` | importaciones |
| **1.** Modelo, pose inicial y objetivo | — | tabla DH, límites, FK, entrada `Td` | `dh`, `transforms`, `validation`, marcos de juntas |
| **2.** Pieper | **A** (15 %) | 8 ramas por pose, `atan2`, real vs admisible | `pieper` |
| **3.** Validación por FK | **B** (10 %) | cada rama se reinyecta en la FK | (usa `validation`) |
| **4.** Selección de rama | A | elegir una rama con criterio explícito | `lspb`, `jacobian` |
| **5.** Trayectoria LSPB | **C** (15 %) | `q(t)`, `q̇(t)`, `q̈(t)`, fronteras, límites | (usa `lspb`) |
| **6.** Jacobiano | **D** (20 %) | `ẋ = J(q) q̇`, validación, columnas | (usa `jacobian`) |
| **7.** Experimento de singularidad | D | pérdida de rango, movilidad perdida, amplificación | (usa `jacobian`) |
| **8.** Dinámica 1R y τ(t) | **E** (15 %) | `τ = J q̈ + m g lc sin θ` sobre el LSPB | `dynamics`, `dynamics_1r` |
| **9.** Discusión y verificaciones | F | tabla de verificaciones, conclusiones | — |
| **Anexo** | F | FK frente a modelo ROS-Industrial y URDF; `analizar_pose` | `rosi_model`, `urdf_chain`, `analizar_pose` |

### Por qué el código de LSPB y Jacobiano aparece en la sección 4

El notebook respeta el orden de la consigna, pero hay dos dependencias reales que obligan a definir código antes:

- **`rank_candidates` (sección 4)** descarta ramas cuya trayectoria no es factible o que están cerca de una singularidad.
  Para eso llama a `plan_lspb` y a `smallest_singular_value`, así que ambos deben existir antes de ejecutar esa sección.
  Por eso `lspb` y `jacobian` se definen al inicio de la sección 4. El **análisis** (gráficas, rango, experimento) sigue en
  las secciones 5, 6 y 7.
- **`joint_frames` (sección 1)**: la geometría de ramas de la sección 2.1 dibuja los orígenes de los marcos. Por eso esa
  función, que es la primera del módulo del Jacobiano, se define en la sección 1; el resto del Jacobiano viene después.

---

## 3. Explicación por partes

### 3.0 Setup (`check` y `save`)

- `check(etapa, descripción, condición)` registra cada verificación en la lista `CHECKS` y hace `assert`: si algo falla, el
  notebook se detiene en esa etapa. Al final (sección 9) se imprime la tabla completa: **32/32 verificaciones aprobadas**
  en el cuerpo del notebook, más 3 en el Anexo.
- `save(fig, nombre)` guarda cada figura en PDF (para el informe) y PNG.

### 3.1 Modelo del robot (`dh.py`)

**Datos y procedencia** (la guía prohíbe inventar parámetros): tabla DH de Bahani et al. (2023), que coincide con las cotas
del datasheet; límites y velocidades por eje del *Product specification IRB 120* de ABB; TCP a 0.150 m, decisión del equipo.

**Tabla DH clásica** (`DH_PARAMETERS`, una `DHParameter` por junta; `θᵢ = qᵢ + offset`):

| i | d [m] | a [m] | α | offset θ |
|---|---|---|---|---|
| 1 | 0.290 | 0 | −90° | 0 |
| 2 | 0 | 0.270 | 0 | −90° |
| 3 | 0 | 0.070 | −90° | 0 |
| 4 | 0.302 | 0 | +90° | 0 |
| 5 | 0 | 0 | −90° | 0 |
| 6 | 0.072 | 0 | 0 | +180° |

**`dh_transform(θ, parámetro)`** arma la matriz DH clásica `Rz(θ) Tz(d) Tx(a) Rx(α)`:

```
[ cθ   −sθ cα    sθ sα   a cθ ]
[ sθ    cθ cα   −cθ sα   a sθ ]
[ 0      sα       cα      d   ]
[ 0      0        0       1   ]
```

- **`forward_kinematics(q)`**: multiplica las 6 matrices → pose `base_link → tool0`. `_joint_vector` valida que `q` tenga 6
  valores finitos.
- **`tcp_transform()` y `forward_kinematics_tcp(q)`**: añaden una traslación pura de `TCP_Z_M = 0.150` m sobre z de la brida.
- **`position_error_m`** y **`rotation_error_rad`**: error de posición (norma euclídea) y de orientación (distancia
  geodésica en SO(3), con `atan2(sin, cos)` del ángulo de `R_refᵀ R`). Son la base de la validación del criterio B.
- **`JOINT_LIMITS_DEG`** y **`MAX_SPEED_DEG_S`**: límites y velocidades máximas del datasheet por eje.
- **`HOME_Q = 0`**: posición de calibración de ABB. En ella `q₅ = 0`, o sea que **la pose inicial es una singularidad
  de muñeca** (se usa a propósito en la sección 6).

**Verificación del modelo:** `FK(q = 0)` da la brida en (0.374, 0, 0.630) m, igual que el datasheet. El TCP queda en
(0.524, 0, 0.630) m con roll-pitch-yaw (0°, 90°, 0°).

### 3.2 Poses y validación (`transforms.py`, `validation.py`)

**`transforms.py`**
- `pose_from_xyz_rpy_deg(x, y, z, roll, pitch, yaw)`: construye `Td` con `R = Rz(yaw) Ry(pitch) Rx(roll)` (convención ROS).
- `matrix_to_rpy_deg`: la operación inversa (maneja el *gimbal lock*).
- `assert_rigid_transform`: rechaza cualquier `Td` que no sea una pose rígida válida: forma 4×4, valores finitos, última fila
  `[0,0,0,1]`, `RᵀR = I` y `det R = +1`, con tolerancia 1e-6. Pieper llama a esta función antes de resolver.

**`validation.py`**: el criterio de aceptación del criterio B.

- `fk_check(Td, q)` reinyecta `q` en la FK y mide tres errores: `e_p` (posición, m), `e_R` (orientación, rad) y `e_F`
  (norma de Frobenius de `T(q) − Td`, indicador global).
- `FKCheck.accepted` es verdadero solo si **`e_p < 1e-6 m` y `e_R < 1e-6 rad`**. Se exigen ambas: validar solo la posición
  dejaría pasar una muñeca mal orientada (ver la prueba de la sección 3).
- `round_trip_test(1000)`: genera 1000 configuraciones aleatorias dentro de límites, calcula `T = FK(q)`, resuelve la IK y
  vuelve a verificar por FK.

**`joint_frames(q)`** (primera parte del módulo del Jacobiano): devuelve las transformadas `T₀ⁱ` para `i = 0..6`. La usan la
geometría de ramas, el Jacobiano y la dinámica.

### 3.3 Criterio A: cinemática inversa de Pieper (`pieper.py`)

El IRB 120 tiene **muñeca esférica** (ejes 4, 5 y 6 concurrentes), así que el problema se desacopla en posición (q₁–q₃) y
orientación (q₄–q₆). Sin MoveIt ni solvers numéricos: es derivación analítica.

**Constantes geométricas:** `D1 = 0.290`, `L2 = 0.270`, `A3 = 0.070`, `D4 = 0.302`, `D6 = 0.072`,
`L3 = √(D4² + A3²) = 0.310`, `DELTA = atan2(A3, D4)`. El alcance hombro–muñeca va de `|L2 − L3| = 0.040` m a
`L2 + L3 = 0.580` m.

**Paso 0: centro de muñeca.** `wrist_center`: `p_wc = p_tool0 − d6 · z₆`. Depende solo de `q₁, q₂, q₃`.

**Paso 1: brazo (`_arm_branches`)** → 4 ramas (2 brazo × 2 codo):
- `q₁ = atan2(y, x)` (brazo **frente**) o `atan2(y, x) + π` con radio negativo (brazo **atrás**). Se usa `atan2` para
  conservar el cuadrante.
- En el plano vertical del brazo, la **ley de cosenos** da
  `cos_term = (r² + h² − L2² − L3²) / (2 L2 L3)` (con `h = z − D1`). Si `|cos_term| > 1` la rama **no existe** (`real = False`).
- Si existe, `−sin(q₃ − δ) = cos_term` tiene dos soluciones: codo **arriba** y codo **abajo**. Luego se obtiene `q₂`.

**Paso 2: muñeca (`_wrist_solutions`)**: `R₃⁶ = R₀³ᵀ R` se descompone como Euler ZYZ, `Rz(q₄) Ry(−q₅) Rz(q₆ + π)`, y da
2 soluciones (**q5+** y **q5−**). Si `sin β ≈ 0` (`q₅ = 0`) la muñeca es singular: solo `q₄ + q₆` queda determinado y se fija
`q₄` con una referencia.

**Las 8 ramas = 2 (brazo) × 2 (codo) × 2 (muñeca).** `enumerate_candidates` devuelve **siempre las 8**, en orden fijo,
cada una como `Candidate` con:

| Campo | Significado |
|---|---|
| `real` | la rama existe geométricamente (`\|cos\| ≤ 1`) |
| `q_raw` | ángulos envueltos a (−π, π] |
| `q` | representante `q + 2πk` dentro de los límites, el más cercano a la referencia; `None` si alguna junta no cabe |
| `out_of_limits` | juntas (1–6) sin representante dentro de límites |

**Real ≠ admisible.** Una rama es **admisible** si es real, está dentro de límites **y** pasa la validación por FK
(`PoseReport.accepted`).

- `analyze_pose(Td, q_ref)` enumera las 8 ramas, las verifica por FK y devuelve un `PoseReport` con el veredicto
  (`reachable`, `verdict`) y `table()` para imprimir la tabla resumen.
- `inverse_kinematics` y `inverse_kinematics_tcp` devuelven solo las admisibles, ordenadas por cercanía a la referencia.

**Resultado con las entradas por defecto:**
- **Pose inicial** (`q = 0`): distancia hombro–muñeca 0.4548 m (dentro de [0.040, 0.580]); **1 de 8 ramas admisible**. Pieper
  recupera `q = 0`.
- **Pose objetivo**: distancia hombro–muñeca 0.4995 m. Las **8 ramas existen** (`real`) pero solo **1 es admisible**
  (el veredicto impreso es «ALCANZABLE: 1 de 8 ramas son admisibles»); las otras 7 violan el límite de alguna junta
  (por ejemplo, la rama 2 deja `q₄ = 180°` fuera de ±160°).

**Sección 2.1 (geometría de ramas):** `arm_points` y `plot_arm_branches` dibujan, proyectados en el plano vertical del brazo,
los 4 brazos posibles (frente/atrás × arriba/abajo), resaltando los admisibles.

### 3.4 Criterio B: validación sistemática por FK

La celda recorre las 16 ramas reales (8 por pose) y arma una tabla con `e_p`, `e_R` y `‖T − Td‖_F`. **Todas** reproducen su
pose con errores del orden de 1e-16 (por debajo de la tolerancia 1e-6).

Dos pruebas muestran que el criterio **sí detecta errores**:

| Candidato fabricado | `e_p` | `e_R` | Resultado |
|---|---|---|---|
| error de 1e-3 rad en `q₁` | 4.12e-4 m | 1.00e-3 rad | rechazado |
| error de 1e-2 rad solo en `q₆` | 7.85e-17 m | 1.00e-2 rad | rechazado |

El segundo caso es el importante: **la posición queda intacta y solo la orientación delata el error**, por eso el criterio
compara pose completa.

**Ida y vuelta:** `q` aleatorio → FK → IK → FK sobre 1000 configuraciones: **1000/1000 resueltas** y el `q` original se
recupera en las 1000.

### 3.5 Selección de la configuración (`rank_candidates`, `select_solution`)

Entre las admisibles hay que **justificar** cuál se usa. Criterios, en este orden:

1. **Admisible** (real, en límites, verificada por FK): obligatorio.
2. **Lejos de singularidad:** `σ_min(J) ≥ 1e-2`.
3. **Lejos de los topes:** margen articular ≥ 5° en las 6 juntas.
4. Entre las que pasan 1–3: **menor desplazamiento ponderado** `‖W (q − q_ref)‖`, con `W = (1, 1, 1, 0.5, 0.5, 0.5)`
   (mover la muñeca cuesta menos). Desempate por mayor `σ_min`.

Si ninguna pasa 2 y 3, primero se relaja el margen y luego `σ_min`, y el estado lo indica (para no quedarse sin solución
cuando la pose sí es alcanzable). Cada rama recibe un `BranchDecision` con su estado: «ELEGIDA», «apta» o el motivo del descarte.

**Resultado:** rama 1 (frente / arriba / q5+), `‖W(q − q₀)‖ = 0.9120`, `σ_min = 0.1167`:

`q_f = [14.036, 22.667, −15.700, 0, 83.034, 14.036]°`

### 3.6 Criterio C: trayectoria LSPB (`lspb.py`)

**LSPB** = *Linear Segment with Parabolic Blends*: arranque parabólico, tramo lineal (crucero), frenado parabólico.
Todas las juntas **comparten `t_f` y `t_b`**, así que llegan a la vez. Para la junta *i* con desplazamiento `Dᵢ`:

```
Vᵢ = Dᵢ / (t_f − t_b)        aᵢ = Vᵢ / t_b

0 ≤ t < t_b           q = q₀ + a t² / 2                 (acelera)
t_b ≤ t ≤ t_f − t_b   q = q₀ + V (t − t_b / 2)          (crucero)
t_f − t_b < t ≤ t_f   q = q_f − a (t_f − t)² / 2        (frena)
```

- **`default_limits(speed_scale, ramp_time_s)`** da `vmax = speed_scale · velocidad_datasheet` y
  `amax = vmax / ramp_time_s`. ABB **no publica** aceleraciones articulares: `amax` es un **supuesto declarado**
  (cada eje alcanza `vmax` en `ramp_time_s`).
- **`plan_lspb(q0, qf, vmax, amax)`** busca el **menor `t_f` factible** por **bisección** (la factibilidad es monótona en
  `t_f`), de modo que `|Vᵢ| ≤ vmaxᵢ` y `|aᵢ| ≤ amaxᵢ` en todas las juntas.
- **`LspbTrajectory.sample(t)`** devuelve `(q, q̇, q̈)`; fuera de `[0, t_f]` el robot está **en reposo**.
  `sample_many` hace lo mismo para un arreglo de tiempos. `phase(t)` dice si está en acelera/crucero/frena/reposo.
- **`check_trajectory`** verifica fronteras en reposo (`q(0) = q₀`, `q(t_f) = q_f`, `q̇ = 0` en ambos extremos),
  continuidad de `q` y `q̇` en los empalmes y respeto de límites. Devuelve `LspbCheck`; `.passed` resume todo.

**Resultado:** `t_f = 1.2879 s`, `t_b = 0.2500 s`, crucero `0.7879 s`. La **junta crítica es la 5**: con un
desplazamiento de 83.034° usa el 100 % de su `vmax` (80°/s) y de su `amax` (320°/s²), y por eso fija `t_f`. Las demás
quedan por debajo (por ejemplo, la junta 2 usa el 35 %) y la junta 4 no se mueve. Se grafican `q(t)`, `q̇(t)`, `q̈(t)`
alineadas, con las fases sombreadas, más el uso de límites por junta. Las verificaciones de la etapa C comprueban
`q(0) = q₀`, `q(t_f) = q_f`, reposo en las fronteras, continuidad de `q` y `q̇` en los empalmes (saltos del orden de 1e-9)
y respeto de `vmax` y `amax`.

### 3.7 Criterio D (parte 1): Jacobiano (`jacobian.py`)

`J(q)` es 6×6 y relaciona `q̇` con el twist `[v; ω]` del TCP: **`ẋ = J(q) q̇`**.

- **`geometric_jacobian(q, reference)`** (`'tcp'`, `'tool0'` o `'wrist'`): columna `i` =
  `[ zᵢ₋₁ × (p − oᵢ₋₁) ; zᵢ₋₁ ]`, con `zᵢ₋₁` y `oᵢ₋₁` tomados de `joint_frames`. La parte lineal es la velocidad que da la
  junta `i` por su palanca hasta el punto de referencia; la angular es el eje de giro.
- **`numerical_jacobian`** calcula `J` por **diferencias centrales de la FK**, con una fórmula independiente
  (`dR/dt Rᵀ = [ω]×`). Sirve como validación: en `q_f` la diferencia máxima entre ambos es **1.40e-10**.
- **`tcp_twist(q, q̇)`** = `J q̇`.
- **Rango por SVD:** `rank_analysis(J)` cuenta los `σᵢ > 1e-6` y devuelve también las **direcciones perdidas**
  (columnas de `U` con `σ ≈ 0`: twists que el TCP no puede generar) y los **movimientos nulos** (columnas de `V` con
  `σ ≈ 0`: `q̇` que no mueven el TCP).
- **`weakest_directions`** da `σ_min` y su dirección; la **amplificación de velocidad es `1/σ_min`**.
- **`determinant`** y **`condition_number`** se usan como **complemento**. El criterio central es el **rango**, porque el
  determinante de un `J` cuadrado no dice cuántas direcciones se pierden ni cuáles.
- `solve_with_jacobian` / `joint_velocity` resuelven `q̇ = J⁻¹ twist` y lanzan `SingularityError` si `σ_min < 1e-9`.

**Resultados de la sección 6:**
- `v = J_v q̇` coincide con la derivada numérica de `p(q(t))` con error máximo **1.97e-10 m/s** sobre toda la trayectoria.
- **Rango de J:** vale 5 solo en `t ≈ 0` (la pose inicial tiene `q₅ = 0`) y 6 en el resto.
- La sección incluye la lectura de columnas: `‖J_v,i‖` es la distancia del TCP al eje `i`.

### 3.8 Criterio D (parte 2): experimento de singularidad (sección 7)

Es un experimento **independiente** de la trayectoria: una secuencia de poses que se acercan a una singularidad conocida,
la de muñeca (`q₅ → 0`).

- **Secuencia:** `q₅ = 45°, 30°, 20°, 10°, 5°, 3°, 1°, 0.3°, 0.1°, 0.03°, 0.01°, 0°`, con
  `q_base = (30, −20, 15, 40, 0, 60)°`.
- **Qué se registra por pose:** rango, `σ₁`, `σ₅`, `σ₆`, número de condición y `det J` (comparado con el `det` teórico
  `det(Jp_brazo) · (±sin q₅)`). El rango es 6 hasta `q₅ = 0`, donde **cae a 5**; `σ₆ → 0`.
- **7.1 Movilidad perdida:** en `q₅ = 0` el movimiento nulo es `q̇₄ = −q̇₆` con el brazo quieto (los dos motores giran en
  sentido opuesto y se cancelan). La parte angular del twist perdido es paralela a `z₃ × z₄` (`|cos| = 1.000000`). El
  TCP no se mueve con ese `q̇`.
- **7.2 Amplificación de velocidad:** para generar una unidad de twist en la dirección perdida hace falta
  `‖q̇‖ ∝ 1/sin q₅`. Pendiente log-log medida **−1.000** (teoría: −1). Ejemplo: 13.7 rad/s a `q₅ = 30°`, 382.7 rad/s a
  1°, 38 240 rad/s a 0.01°.
- **Singularidad ≠ torque infinito.** En esa dirección perdida el torque estático tiende a 0; lo que diverge es la
  **velocidad articular necesaria**. Esta distinción la pide la rúbrica (E: «confusión entre singularidad y torque» es
  *insuficiente*).
- **7.3 Complemento:** singularidad de codo (brazo estirado) en `q₃ = δ − 90° = −76.950°`, con `σ₆ → 0` al acercarse.

### 3.9 Criterio E: dinámica 1R del hombro (`dynamics_1r.py`, `dynamics.py`)

**Modelo 1R de la clase**: un péndulo con ángulo `θ` medido desde la vertical inferior:

```
τ = J q̈ + m g lc sin θ          con  J = Ic + m lc²   y   θ = q₂ + φ₀
```

`shoulder_model(q_ref)` **no inventa parámetros**: congela las juntas 3–6 en `q_ref` y calcula, con los datos CAD de
Truc y Lam (2020) más la pinza SMC MHZ2-16D (115 g, hoja de datos):

- `m`: masa de los eslabones 2 a 6 (el 6 ya incluye la pinza).
- `lc`: distancia perpendicular del eje de la junta 2 al centro de masa.
- `Ic`: inercia respecto al eje de la junta 2 (teorema de ejes paralelos) menos `m lc²`.
- `φ₀`: ángulo que relaciona `θ` con `q₂` según la postura congelada.

El notebook usa `q_ref = (q₀ + q_f)/2`. Resultado: **m = 12.210 kg, lc = 0.2491 m, Ic = 0.4479 kg·m², J = 1.2053 kg·m²,
φ₀ = −163.815°, m g lc = 29.832 N·m.** También se muestra la sensibilidad a la postura congelada (con `q_ref = q₀` sale
`lc = 0.2420 m`, `J = 1.1486 kg·m²`).

**`OneRModel.torque_components(q₂, q̈₂)`** separa `τ = τ_in + τ_g`:
- `τ_in = J q̈₂` (inercial: solo aparece cuando acelera o frena),
- `τ_g = m g lc sin θ` (gravitacional: depende de la postura, no de la velocidad).

**Interpretación sobre el LSPB** (`τ(t)` con `q₂(t)` y `q̈₂(t)` de la sección 5):

| Instante | Fase | τ_in | τ_g | τ total |
|---|---|---|---|---|
| 0.0000 s | acelera | +1.838 | −8.316 | −6.478 N·m |
| 0.6440 s | crucero | 0 | −13.784 | −13.784 N·m |
| 1.2879 s | frena | −1.838 | −18.714 | −20.552 N·m |

El mayor esfuerzo ocurre **al final**, donde la gravedad pesa más y el frenado se le suma. Durante el crucero el torque es
solo gravitacional.

**Validación del 1R frente al modelo completo.** `dynamics.py` implementa el modelo Lagrangiano de las 6 juntas,
`τ = M(q) q̈ + c(q, q̇) + g(q)`: `mass_matrix` (suma de aportes `m JvᵀJv + Jwᵀ I Jw` por eslabón), `gravity_vector`
(vía la fila z de `Jv`), `coriolis_vector` (por diferencias finitas de `M`) e `inverse_dynamics`. Se usa **solo para
validar**: el 1R reproduce `τ₂` del modelo completo con **error RMS 0.637 N·m (4.5 % del RMS de τ₂)**, máximo 1.174 N·m. La
diferencia viene de lo que el 1R deja fuera: mientras el hombro se mueve, las juntas 3–6 también se mueven (acoplamientos y
términos de Coriolis/centrífugos).

**Efecto de la velocidad:** al escalar la velocidad (0.10 a 1.00 del `vmax`), `τ_g` se queda en 18.714 N·m (no depende de la
velocidad) y `τ_in` crece con el cuadrado de la velocidad (0.294 → 29.403 N·m).

### 3.10 Sección 9: resumen de verificaciones

Imprime la tabla `CHECKS` (etapa · descripción · ✔/✘) con el total `32/32 verificaciones aprobadas`, y recoge las
conclusiones del pipeline.

### 3.11 Anexo: verificación independiente y analizador de poses

Respalda la validez del modelo (criterio F):

- **`rosi_model.py`**: la FK del **modelo oficial de ROS-Industrial** (`abb_irb120_support`), construida con traslaciones
  puras y ejes de giro, **sin parámetros DH**. Es una fuente geométrica independiente de nuestra tabla DH.
  Con 200 configuraciones aleatorias dentro de límites, la diferencia máxima es **1.2e-15**; los límites articulares
  coinciden con los del xacro oficial.
- **`urdf_chain.py`**: evalúa la cadena cinemática del **URDF del Hito 1** (`datos/irb120.urdf`). Como ese URDF se derivó de
  la tabla DH, esta comparación verifica la **implementación** (otro código), no la geometría. Con 100 configuraciones el
  error es **1.0e-15**. Si el notebook no se ejecuta desde `hito2/`, esta comparación se omite con un aviso.
- **`analizar_pose(x, y, z, roll, pitch, yaw)`**: el analizador del script `analizar_pose.py` como función. Imprime la
  tabla de las 8 ramas y el veredicto, y la rama seleccionada desde la pose inicial.

---

## 4. Resultados del caso por defecto (resumen)

| Etapa | Resultado |
|---|---|
| Pose inicial `q = 0` | TCP en (0.524, 0, 0.630) m, singularidad de muñeca (`q₅ = 0`) |
| Pieper, pose objetivo | 1 de 8 ramas admisible: frente / arriba / q5+ |
| `q_f` | `[14.036, 22.667, −15.700, 0, 83.034, 14.036]°`, `σ_min = 0.1167` |
| LSPB | `t_f = 1.2879 s`, `t_b = 0.25 s`, junta crítica J5 (100 % de `vmax` y `amax`), límites respetados |
| Jacobiano | `J` analítico vs numérico 1.40e-10; `v = J_v q̇` vs derivada de `p(q(t))` 1.97e-10 m/s; rango 5 solo en `t ≈ 0` |
| Singularidad de muñeca | rango 6 → 5; `‖q̇‖ ∝ 1/sin q₅` (pendiente −1.000); torque estático en la dirección perdida → 0 |
| Dinámica 1R | `J = 1.2053 kg·m²`, `m g lc = 29.832 N·m`; `τ` entre −6.5 y −20.6 N·m |
| 1R vs completo | error RMS 4.5 % |
| Anexo | FK(DH) = ROS-Industrial (1.2e-15) y = URDF Hito 1 (1.0e-15) |

---

## 5. Supuestos y procedencia de los datos

La rúbrica E pide «parámetros con procedencia» y la guía prohíbe inventar. Lo que **no** viene de una fuente es un supuesto
declarado:

| Dato | Procedencia |
|---|---|
| Tabla DH | Bahani et al. (2023), Tabla I |
| Límites y velocidades por eje | ABB, *Product specification IRB 120* |
| Masas, centros de masa e inercias | Truc y Lam (2020), aproximaciones por CAD, ec. 18 |
| Pinza (115 g) | hoja de datos SMC MHZ2-16D (su centro de masa está aproximado como el cuerpo de la pinza) |
| TCP a 0.150 m de la brida | decisión del equipo |
| `amax = vmax / 0.25 s` | **supuesto de diseño** (ABB no publica aceleraciones articulares) |
| `SPEED_SCALE = 0.25` | **supuesto de diseño** (como un *speed override*) |
| Postura congelada del 1R `(q₀ + q_f)/2` | **decisión de modelado**; la sensibilidad se muestra en la sección 8 |

---

## 6. Preguntas que conviene saber responder (defensa)

- **G1, pipeline:** ¿qué entra y qué sale de cada etapa? `Td → 8 ramas → admisibles → una rama q_f → LSPB → J(q(t)) y rango →
  τ(t)`. La salida de cada etapa es la entrada de la siguiente.
- **G2, matemática:** reconstruir la ley de cosenos del codo, la matriz DH, las fórmulas del LSPB o `τ = J q̈ + m g lc sin θ`.
- **G3, validación:** ¿cómo se sabe que una `q` es correcta? Se reinyecta en la FK y se comparan posición **y** orientación
  contra tolerancia 1e-6. ¿Y que el modelo geométrico es correcto? Se compara con una fuente independiente (ROS-Industrial).
- **G3, física:** ¿qué significa que el rango de `J` baje a 5? El TCP pierde una dirección de movimiento y la velocidad
  articular requerida crece como `1/sin q₅`; no es torque infinito.
- **G4, transferencia:** cualquier parte distinta de la que programaste. Por eso el notebook está en un solo archivo y por
  etapas.

---

## 7. Limitaciones y detalles a tener en cuenta

- **Una sola pose objetivo.** La guía dice «se deberán procesar múltiples poses dadas por el docente»; el notebook procesa la
  pose inicial más **una** pose objetivo editable. Para varias poses habría que recorrer una lista.
- **La pose inicial es singular** (`q₅ = 0`). Es deliberado (es la posición de calibración de ABB) y explica el rango 5 en `t ≈ 0`.
- **Aviso de Matplotlib.** La celda de la geometría de ramas (2.1) muestra un `UserWarning` por definir dos veces
  `linestyle`. Es inofensivo y no afecta a los resultados.
- **El modelo 1R es una aproximación:** deja fuera el movimiento simultáneo de las juntas 3–6 y los términos de Coriolis.
  Su error frente al modelo completo en este caso es del 4.5 % (RMS).
- **Los parámetros inerciales** son aproximaciones por CAD: sirven para evidenciar tendencias, no como identificación del robot real.

---

## 8. Dónde está cada cosa

| Archivo | Contenido |
|---|---|
| `Hito2_IRB120_todo_en_uno.ipynb` | este notebook (todo el código incluido) |
| `Hito2_IRB120_pipeline.ipynb` y `irb120/` | versión modular original, sin cambios |
| `explicacion/` | explicación detallada por tema (DH, Pieper, LSPB, Jacobiano, dinámica, defensa) |
| `figuras_todo_en_uno/` | figuras que genera este notebook |
| `datos/irb120.urdf` | URDF del Hito 1 que lee el Anexo |
