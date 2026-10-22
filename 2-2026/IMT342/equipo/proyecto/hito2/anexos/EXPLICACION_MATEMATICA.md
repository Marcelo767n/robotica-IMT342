# Hito 2 — Explicación técnica y matemática completa (para la defensa)

Este documento explica, módulo por módulo, **qué hace el código**, **cómo lo hace** y **por qué
es matemáticamente correcto**, con las derivaciones completas detrás de cada fórmula. Es
material de defensa: cada resultado se conecta con la línea de código que lo implementa y con
las pruebas (`tests/`) que lo verifican numéricamente.

Alcance: la carpeta `hito2/irb120/` (Python puro, sin ROS). El mismo código, copiado sin
dependencias de ROS, es el que corre como nodo en `ros2_ws/src/irb120_hito2/`.

Robot: ABB IRB 120 (6 ejes, muñeca esférica) + pinza neumática SMC MHZ2-16D.

---

## 0. Convención y notación

- `qᵢ`: ángulo de la junta `i` (rad). `q = (q1,...,q6)`.
- `Tᵢ₋₁^i`: transformada homogénea 4×4 que lleva coordenadas del marco `i` al marco `i−1`.
- `zᵢ`: eje Z del marco `i` expresado en la base (`base_link`); es el eje de giro de la junta `i+1`.
- `oᵢ`: origen del marco `i` expresado en la base.
- `R`, `p`: bloque de rotación 3×3 y traslación 3×1 de una transformada homogénea.
- `v`, `ω`: velocidad lineal y angular (twist `[v; ω]`, 6×1).
- Todas las fórmulas siguen la convención **DH clásica** (no la modificada de Craig).

---

## 1. Cinemática directa — `dh.py`

### 1.1 De dónde sale la matriz DH

La convención DH clásica define el marco `i` a partir del marco `i−1` con **cuatro**
transformaciones elementales encadenadas, en este orden:

```
T_{i-1}^i = Rz(θᵢ) · Tz(dᵢ) · Tx(aᵢ) · Rx(αᵢ)
```

- `Rz(θ)`: rota el eje de la junta (revoluta) un ángulo `θ`.
- `Tz(d)`: traslada a lo largo del eje de la junta la distancia `d` (offset de eslabón).
- `Tx(a)`: traslada a lo largo de la normal común la distancia `a` (longitud de eslabón).
- `Rx(α)`: rota la normal común el ángulo `α` (ángulo entre ejes consecutivos).

Multiplicando las cuatro matrices 4×4 en ese orden (ver deducción en el Anexo A) se obtiene

```
T_{i-1}^i =
| cθ   -sθ·cα    sθ·sα    a·cθ |
| sθ    cθ·cα   -cθ·sα    a·sθ |
| 0     sα       cα       d    |
| 0     0        0        1    |
```

Esta es exactamente la matriz que construye `dh_transform()` en
[`dh.py:45-69`](../irb120/dh.py). No es una fórmula "mágica": es el producto algebraico de las
cuatro rotaciones/traslaciones elementales, y por eso **cualquier** manipulador serial con
articulaciones rotoides usa esta misma matriz, solo cambian los parámetros `(d, a, α, θ_offset)`.

### 1.2 Tabla DH del IRB 120

Los parámetros (en metros, transcritos de Bahani et al. 2023, tabla I) son:

| i | dᵢ (m) | aᵢ (m) | αᵢ (rad) | offset θᵢ |
|---|---|---|---|---|
| 1 | 0.290 | 0.000 | −π/2 | 0 |
| 2 | 0.000 | 0.270 | 0 | −π/2 |
| 3 | 0.000 | 0.070 | −π/2 | 0 |
| 4 | 0.302 | 0.000 | +π/2 | 0 |
| 5 | 0.000 | 0.000 | −π/2 | 0 |
| 6 | 0.072 | 0.000 | 0 | π |

Los *offsets* en las filas 2 y 6 existen porque el **cero mecánico** del robot (postura "home"
ABB) no coincide con el cero matemático de la convención DH; se suman internamente en
`dh_transform(theta_rad, parameter)` (`theta = theta_rad + parameter.theta_offset_rad`,
[`dh.py:47`](../irb120/dh.py)) para no tener que pedirle al usuario que los recuerde.

**Dato clave para toda la cinemática inversa (Pieper):** las filas 4 y 5 tienen `a4 = a5 = 0` y
`d5 = 0`. Esto significa que **los ejes de las juntas 4, 5 y 6 se cortan en un único punto**
(la "muñeca esférica"). Es la propiedad geométrica que hace posible resolver la IK de forma
analítica (sección 2).

### 1.3 Cinemática directa y por qué encadenar matrices es válido

```
T_0^6(q) = T_0^1(q1) · T_1^2(q2) · ... · T_5^6(q6)
```

Esto es simplemente la composición de cambios de marco: la posición/orientación de un punto fijo
en el marco 6, expresada en el marco 0, se obtiene aplicando sucesivamente cada cambio de marco.
Es exactamente lo que hace `forward_kinematics()` acumulando el producto en un bucle
(`transform = transform @ dh_transform(...)`, [`dh.py:83-89`](../irb120/dh.py)).

El TCP de la pinza está a `0.100 m` por delante de `tool0` sobre su eje Z (`tcp_transform()`,
[`dh.py:92-96`](../irb120/dh.py)): `T_tool0^tcp = Tz(0.100)`. Por eso
`forward_kinematics_tcp(q) = forward_kinematics(q) · Tz(0.100)`.

### 1.4 Métricas de error

- **Error de posición**: `‖p_ref − p_medido‖₂` (norma euclídea, `position_error_m`).
- **Error de orientación** (distancia geodésica entre rotaciones): se calcula la rotación
  relativa `R_rel = R_refᵀ R_medido`, y se usa la identidad de Rodrigues inversa

  ```
  tr(R_rel) = 1 + 2cos(φ)        →   cos(φ) = (tr(R_rel) − 1) / 2
  ‖skew(R_rel − R_relᵀ)‖ = 2 sin(φ)
  φ = atan2(sin φ, cos φ)
  ```

  donde `φ` es el ángulo del eje-ángulo equivalente a `R_rel`, es decir, el ángulo mínimo que
  hay que rotar para llevar una orientación a la otra. Usar `atan2` en vez de `acos(cosφ)` evita
  la pérdida de precisión cerca de `φ = 0` (donde `acos` tiene derivada infinita). Esto es
  exactamente `rotation_error_rad()` ([`dh.py:109-121`](../irb120/dh.py)).

---

## 2. Cinemática inversa analítica de Pieper — `pieper.py`

### 2.1 Por qué existe una solución cerrada (y por qué no se usa un solver numérico)

Un manipulador de 6 ejes con **muñeca esférica** (ejes 4, 5, 6 concurrentes en un punto, visto en
§1.2) permite **desacoplar** el problema de 6 incógnitas simultáneas en dos problemas de 3
incógnitas cada uno, resueltos en cadena:

1. **Posición** del centro de muñeca → determina `q1, q2, q3` (solo geometría del "brazo").
2. **Orientación** restante → determina `q4, q5, q6` (solo geometría de la "muñeca").

Esto es el **método de Pieper** (Pieper, 1968). Es exacto, cerrado, y entrega *todas* las
configuraciones posibles (no una aproximación iterativa como Newton-Raphson o un IK numérico de
MoveIt) — por eso la guía del proyecto prohíbe usar resolvedores automáticos: aquí la matemática
está implementada a mano.

### 2.2 Paso 0 — Centro de muñeca

El TCP/`tool0` está a una distancia `d6` del centro de muñeca, medida a lo largo de `z6`
(eje de la última junta, que por construcción DH pasa por el centro de muñeca). Si `R, p` son
la rotación y posición de `tool0`:

```
p_wc = p − d6 · z6        con z6 = R[:, 2]  (tercera columna de R)
```

Esto es simplemente "retroceder" desde la brida una distancia `d6` en la dirección en que
apunta su propio eje Z. Como `a4 = a5 = d5 = 0` (§1.2), el origen del marco 4 **no depende del
ángulo `θ4`** — la traslación de DH ocurre *antes* de aplicar la rotación de la siguiente junta,
así que si `a=0`, girar esa junta no mueve el origen siguiente. Por eso `p_wc` depende
únicamente de `q1, q2, q3`: ahí está el desacople. Código: [`pieper.py:150`](../irb120/pieper.py).

### 2.3 Paso 1 — Posición: `q1`, `q2`, `q3` (hasta 4 soluciones: 2 brazo × 2 codo)

Sea `(x, y, z) = p_wc`.

**`q1` (giro de base).** Visto desde arriba, el centro de muñeca está en el ángulo
`atan2(y, x)` respecto al eje X. Pero el brazo puede alcanzar el mismo punto "por detrás"
(girando la base 180° y doblando el codo hacia el otro lado), lo que da la segunda familia de
soluciones `q1 + π` con el radio planar cambiado de signo:

```
("frente", q1 = atan2(y, x),      r = +√(x²+y²))
("atras",  q1 = atan2(y, x) + π,  r = −√(x²+y²))
```

**`q2`, `q3` (plano vertical del brazo).** Con el hombro en `S = (0, d1)` (en coordenadas
`(radio, altura)`), el codo en `E` y la muñeca en `W = (r, z − d1)`, se forma un triángulo con
lados conocidos:

- `SE = L2 = a2 = 0.270 m` (longitud del eslabón 2),
- `EW = L3 = √(d4² + a3²) = √(0.302² + 0.070²) ≈ 0.3100 m` — es la distancia directa entre el
  codo y la muñeca, pero como el eje de la junta 4 está desplazado `a3` respecto al de la junta
  3 (fila 3 de la tabla DH), el "antebrazo" no es un segmento recto de longitud `d4`: hay que
  tomar la hipotenusa `√(d4²+a3²)`,
- `SW = D = √(r² + h²)` con `h = z − d1` (distancia conocida, del objetivo).

**Ley de cosenos** en ese triángulo:

```
D² = L2² + L3² − 2·L2·L3·cos(ángulo en el codo)
```

Despejando, el código define

```
cos_term = (D² − L2² − L3²) / (2·L2·L3)
```

que es `−cos(ángulo en el codo)`. Si `|cos_term| > 1` el triángulo no se puede cerrar con esos
lados: el punto está **fuera del alcance** del brazo y no hay solución (chequeo
[`pieper.py:98-99`](../irb120/pieper.py)) — es la condición de **espacio de trabajo** expresada en
una sola desigualdad.

Por la convención de ejes DH usada aquí, el ángulo articular `q3` no coincide exactamente con el
ángulo interior del triángulo: hay un desfase `δ = atan2(a3, d4)` (el ángulo que introduce el
desplazamiento `a3` entre juntas 3 y 4) y una rotación de 90° entre cómo se mide el ángulo
geométrico y cómo se define `θ` en DH, que convierte el coseno en seno:

```
−sin(q3 − δ) = cos_term
```

Esta ecuación tiene **dos soluciones** en `[−π, π]` para cada valor de `cos_term` (son los dos
codos: `arriba` y `abajo`), exactamente como `asin(x)` tiene las dos preimágenes `β` y `π − β`:

```
base = asin(−cos_term)
codo "arriba":  q3 − δ = base
codo "abajo":   q3 − δ = π − base
```

Con `q3` fijo, se recorre el triángulo desde `S`: el ángulo entre `SE` y `SW` se obtiene
proyectando el lado `EW` sobre las direcciones perpendicular y paralela a `SE`
(`η = π/2 + q3 − δ` es el ángulo en `S` del vértice `E` dentro del triángulo):

```
q2 = atan2(r, h) − atan2(L3·sin η, L2 + L3·cos η)
```

El primer término es la dirección de `S` a `W` medida desde la vertical; el segundo es el
ángulo entre `SW` y `SE` obtenido por geometría del triángulo (tangente de componente
perpendicular sobre paralela). Código: [`pieper.py:86-109`](../irb120/pieper.py).

Combinando 2 soluciones de brazo × 2 de codo: **hasta 4 soluciones de posición**.

### 2.4 Paso 2 — Orientación: `q4`, `q5`, `q6` (2 soluciones de muñeca)

Con `q1, q2, q3` ya fijos, se conoce `R_0^3` (rotación acumulada de las primeras 3 juntas,
`_rotation_0_3()`). La rotación que falta por explicar con `q4, q5, q6` es

```
R_3^6 = (R_0^3)ᵀ · R_0^6
```

Por construcción DH, esta rotación tiene la forma de una secuencia de **Euler ZYZ**:

```
R_3^6 = Rz(q4) · Ry(−q5) · Rz(q6 + π)
```

(los signos y el `+π` vienen de los `alpha`/offsets de las filas 4-6 de la tabla DH; son
constantes fijas del robot, no una elección arbitraria).

**Extracción de ángulos de Euler ZYZ.** Para `R = Rz(φ)·Ry(θ)·Rz(ψ)` general, al multiplicar
las tres matrices se obtiene

```
R = | cφcθcψ−sφsψ   −cφcθsψ−sφcψ   cφsθ |
    | sφcθcψ+cφsψ   −sφcθsψ+cφcψ   sφsθ |
    | −sθcψ          sθsψ           cθ  |
```

de donde:

- `R[2,2] = cos θ` y `√(R[0,2]² + R[1,2]²) = |sin θ|` → `θ = atan2(±√(R02²+R12²), R22)`. El
  signo `±` es libre y da las **dos soluciones** de muñeca (`q5+`/`q5−`).
- Con `θ` conocido y `sinθ ≠ 0`: `φ = atan2(R12, R02)` (o con ambos signos negados si se tomó el
  `θ` negativo) y `ψ = atan2(R21, −R20)` (mismo criterio de signo).

Trasladado a nuestro caso (`φ=q4`, `θ=−q5`, `ψ=q6+π`), esto es exactamente
`_wrist_solutions()` ([`pieper.py:119-133`](../irb120/pieper.py)): `sin_beta = hypot(R[0,2],R[1,2])`,
`beta = atan2(±sin_beta, R[2,2])`, `q5 = −beta`, `q4 = atan2(±R12, ±R02)`,
`q6 = atan2(±R21, ∓R20) − π`.

**Caso singular `q5 = 0`.** Si `sinθ ≈ 0`, la matriz se reduce a una rotación pura alrededor de
Z: `R = Rz(φ)·Rz(ψ) = Rz(φ+ψ)`, y solo la **suma** `φ+ψ` es observable —no hay forma de separar
cuánto giró cada eje si están alineados—. El código recupera `total = φ+ψ = atan2(R10,R00)` y,
para no dejar `q4` indefinido, **conserva el `q4` de referencia** y pone todo el resto en `q6`:
`q6 = total − q4_ref − π` ([`pieper.py:123-125`](../irb120/pieper.py)). Esta es la raíz matemática de
la singularidad de muñeca que se analiza a fondo en la sección 3.

### 2.5 Filtrado, verificación y conteo final de soluciones

Cada candidato `(q1,...,q6)` crudo puede estar fuera del rango `[−π, π]` en el que se calculó
(p. ej. `q1+π` puede salirse de ese intervalo), así que `_fit_to_limits()` prueba
`ángulo + 2πk` para `k ∈ {−3,...,3}` y se queda con la representación dentro de los **límites
articulares reales** del ABB IRB 120 (p. ej. junta 6 permite ±400°, más de una vuelta) más
cercana a una referencia dada. Si ninguna vuelta cae dentro del límite, la solución se descarta.

Después, **cada solución que sobrevive se verifica sustituyéndola en la cinemática directa**
(`forward_kinematics(q)`) y comparando con el objetivo: se exige error de posición `< 1e-6 m` y
de orientación `< 1e-6 rad` (tolerancias de `FK_TOLERANCE_M` y el chequeo de
`rotation_error_rad`). Esto es una **auditoría cruzada**: la IK analítica no se "cree a sí
misma", se comprueba contra la FK del §1, que es mucho más simple y por tanto mucho más difícil
de tener mal.

**Conteo:** 2 (brazo: frente/atrás) × 2 (codo: arriba/abajo) × 2 (muñeca: `q5+`/`q5−`) = **hasta
8 soluciones**, antes de descartar por límites/alcance. Las soluciones finales se ordenan por
distancia euclídea en el espacio articular a una postura de referencia (para elegir, en
operación real, el movimiento más pequeño posible) y se eliminan duplicados numéricos
(`np.allclose`, [`pieper.py:171-176`](../irb120/pieper.py)).

### 2.6 Validación empírica

`tests/test_pieper.py` comprueba, entre otras cosas:

- `test_recovers_original_joints_and_every_solution_reaches_the_pose`: a partir de una postura
  aleatoria se calcula su pose, se invierte, y la postura original aparece entre las soluciones
  — y **todas** las soluciones devueltas realmente llevan a la misma pose.
- `test_generic_pose_has_up_to_eight_distinct_solutions`: el conteo de §2.5 se cumple.
- `test_unreachable_pose_returns_no_solution`: una pose fuera de alcance devuelve lista vacía
  en vez de un número sin sentido.
- `test_wrist_singularity_q5_zero_is_solved`: el caso del §2.4 no rompe el solver.

---

## 3. Jacobiano geométrico y singularidad de muñeca — `jacobian.py`

### 3.1 Construcción del Jacobiano

El **Jacobiano geométrico** `J(q)` (6×6) relaciona la velocidad articular con el *twist*
(velocidad lineal + angular) de un punto del efector:

```
[v; ω] = J(q) · q̇
```

Para una junta rotoide `i`, su contribución al movimiento del punto de interés `p_e` es un giro
rígido: si solo se mueve la junta `i` (las demás fijas), el punto `p_e` (rígidamente unido más
allá de la junta `i`) gira con velocidad angular `ω_i = q̇ᵢ·z_{i-1}` alrededor del eje que pasa
por `o_{i-1}` con dirección `z_{i-1}`. La velocidad lineal de un punto de un cuerpo rígido que
gira así es `v = ω × (p_e − o_{i-1})`. Por linealidad (las contribuciones de cada junta se
suman), la columna `i` del Jacobiano es:

```
Jᵢ = [ z_{i-1} × (p_e − o_{i-1}) ]
     [ z_{i-1}                   ]
```

exactamente lo que construye `geometric_jacobian()`
(`jacobian[:3,index] = cross(axis, point-origin); jacobian[3:,index] = axis`,
[`jacobian.py:41-47`](../irb120/jacobian.py)), usando los marcos obtenidos de la cadena DH
(`joint_frames`).

`reference` elige qué punto `p_e` se usa: el TCP de la pinza, `tool0`, o el centro de muñeca
(`wrist`) — este último es clave para el análisis de singularidad.

### 3.2 Por qué el Jacobiano es triangular por bloques (referencia = muñeca)

Si se toma como punto de interés el **centro de muñeca** (que coincide con el origen del marco
4, ver §2.2), entonces para las juntas 4, 5 y 6 —cuyos ejes **pasan por ese mismo punto** (es la
propiedad de muñeca esférica)— el término `(p_e − o_{i-1})` es el vector nulo o paralelo al eje,
y `z_{i-1} × (p_e − o_{i-1}) = 0`. Es decir: mover la muñeca (juntas 4-6) **no traslada** el
centro de muñeca, solo lo reorienta. Por lo tanto:

```
J(q, ref=muñeca) = | Jp_brazo (3×3)     0 (3×3)        |
                    | Jw_brazo (3×3)   [z3 z4 z5] (3×3) |
```

(columnas 1-3 = contribución del brazo, columnas 4-6 = contribución de la muñeca; bloque
superior derecho nulo). El determinante de una matriz triangular por bloques es el producto de
los determinantes de los bloques diagonales:

```
det J = det(Jp_brazo) · det[z3 z4 z5]
```

### 3.3 Por qué `det[z3 z4 z5] = ± sin(q5)`

En la parametrización ZYZ de la muñeca (§2.4), `z4` (eje de la junta 5, que es el eje "Y" de la
rotación `Ry(−q5)`) es, por construcción de Euler ZYZ, **perpendicular tanto a `z3` como a
`z5`** (el eje intermedio de cualquier secuencia de Euler es perpendicular a los otros dos por
definición). Además, `z3` y `z5` difieren entre sí exactamente por una rotación de ángulo `q5`
alrededor de `z4`. Para tres vectores unitarios con esa relación, el triple producto escalar
(que mide el volumen con signo del paralelepípedo que forman) se reduce a:

```
det[z3 z4 z5] = z3 · (z4 × z5) = ± sin(q5)
```

(intuición: con `z4` fijo como "polo", `z3` y `z5` viven en el plano perpendicular a `z4`
separados por el ángulo `q5`; el producto triple de tres vectores ortonormales en esa
configuración es exactamente el seno del ángulo entre los dos que no son el polo). Por tanto:

```
det J(q) = ± sin(q5) · det(Jp_brazo(q1,q2,q3))
```

Esta es la fórmula central de la singularidad, verificada en código por
`determinant()`/`arm_position_determinant()` ([`jacobian.py:50-67`](../irb120/jacobian.py)) y por el
test `test_determinant_factorizes_as_sin_q5_times_arm_determinant` (error numérico ~1e-17 en
posturas aleatorias, según el notebook del pasaporte).

### 3.4 Qué significa que `q5 = 0`

Cuando `q5 = 0`, los ejes de las juntas 4 y 6 quedan **colineales** (`z3 = z5`): girar la junta 4
y girar la junta 6 produce el mismo efecto sobre la orientación del efector (son redundantes en
ese instante). El Jacobiano **pierde un rango** (dimensión 5 en vez de 6): hay direcciones del
espacio de twists que ningún `q̇` puede producir, y existen combinaciones de `q̇` (p. ej.
`q̇4 = 1, q̇6 = −1`, el resto 0) que no producen *ningún* movimiento del efector. Formalmente,
`J` no es invertible, así que `q̇ = J⁻¹·[v;ω]` **no existe** como solución única.

`condition_number(q) = σ_max/σ_min` (cociente de valores singulares, vía SVD) crece sin límite
al acercarse a la singularidad — es la medida estándar en robótica de "qué tan cerca" se está de
perder un grado de libertad; `smallest_singular_value` es `σ_min`, que tiende a 0.
`SingularityError` se lanza cuando `σ_min < 1e-9`
(`solve_with_jacobian()`, [`jacobian.py:70-82`](../irb120/jacobian.py)): es la forma de que el
código "falle ruidosamente" en vez de devolver un número sin sentido (`J⁻¹` con `det J ≈ 0`
amplifica errores numéricos arbitrariamente).

### 3.5 Por qué `q̇` diverge como `1/|sin q5|`

Para una matriz invertible, `J⁻¹ = adj(J)/det(J)` (matriz adjunta sobre determinante). Cerca de
`q5=0`, `det J → 0` linealmente en `sin q5` (§3.3) mientras que `adj(J)` permanece acotada (sus
entradas son productos de elementos de `J`, que son finitos). Por tanto:

```
‖J⁻¹‖ ~ 1/|det J| ~ 1/|sin q5|      ⟹      ‖q̇‖ = ‖J⁻¹ · twist‖ ~ 1/|sin q5|
```

El notebook del pasaporte mide esta pendiente en escala log-log y obtiene **−0.97** (≈ −1), lo
que confirma empíricamente la ley `‖q̇‖ ∝ 1/|sin q5|¹` predicha por la teoría.

---

## 4. Trayectoria LSPB — `lspb.py`

### 4.1 Por qué LSPB y no, por ejemplo, un polinomio de grado 5

LSPB (*Linear Segment with Parabolic Blends*) acota **directamente** velocidad y aceleración
máximas con parámetros físicos (`vmax`, `amax`) y su tiempo mínimo se calcula en forma cerrada
(salvo una bisección simple), sin resolver un sistema de ecuaciones con condiciones de borde en
posición/velocidad/aceleración como requeriría un polinomio de 5º grado. Es también el perfil
más simple que logra: velocidad continua en todo instante (sin impulsos de aceleración), tiempo
total mínimo dados los límites, y arranque/parada suaves.

### 4.2 Ecuaciones de cada tramo

Para una junta con desplazamiento `D = qf − q0`, tiempo total `tf` y tiempo de mezcla
(parabólico) `tb`:

```
0 ≤ t < tb:          q(t) = q0 + ½ a t²                       (acelera a `a` constante)
tb ≤ t ≤ tf−tb:       q(t) = q0 + ½ a tb² + V(t − tb)          (velocidad constante V)
tf−tb < t ≤ tf:      q(t) = qf − ½ a (tf − t)²                 (frena a `−a`, simétrico)
```

**Continuidad de velocidad en `t = tb`**: la rampa da `v(tb⁻) = a·tb`; el tramo recto exige
`v(tb⁺) = V`. Igualando: `V = a·tb`, es decir `a = V/tb`.

**Simplificación del tramo recto**: sustituyendo `a·tb² = V·tb` en la ecuación de ese tramo,

```
q0 + ½ V tb + V(t − tb) = q0 + V(t − tb/2)
```

que es exactamente la expresión que usa `sample()` ([`lspb.py:50`](../irb120/lspb.py)).

**Desplazamiento total = área bajo el perfil trapezoidal de velocidad.** El perfil de velocidad
sube de 0 a `V` en `tb`, se mantiene en `V` durante `tf−2tb`, y baja de `V` a 0 en `tb` — un
trapecio simétrico. Su área (= desplazamiento total `D`) es exactamente `V·(tf − tb)` (la
rampa de subida y la de bajada juntas aportan lo mismo que un tramo rectangular de ancho `tb` a
altura `V`, así que el área total equivale a un rectángulo de ancho `(tf−tb)` y alto `V`). Por
tanto:

```
V = D / (tf − tb)          y          a = V / tb
```

que son exactamente `cruise_velocity` y `blend_acceleration`
([`lspb.py:36-41`](../irb120/lspb.py)).

### 4.3 Tiempo mínimo factible (bisección)

Combinando `a = V/tb` y `V = D/(tf−tb)`:

```
a = D / [tb·(tf − tb)]      ⟺      tb·(tf − tb) = D/a =: K
```

Esto es una ecuación cuadrática en `tb`: `tb² − tf·tb + K = 0`, cuya raíz menor (la física: el
tramo de mezcla debe ser menor o igual a la mitad del tiempo total) es

```
tb = [ tf − √(tf² − 4K) ] / 2
```

— exactamente `blend_time()` ([`lspb.py:72-73`](../irb120/lspb.py)). Para que exista una raíz real
se necesita `tf² ≥ 4K`; y para que `V ≤ vmax` se necesita `tf − tb ≥ D/vmax =: Dv`
(`cruise_term`). Ambas condiciones son **monótonas crecientes en `tf`**: dar más tiempo total
nunca puede volver infactible un movimiento que ya era factible con menos tiempo (siempre se
puede "ir más lento"). Esa monotonía es justo lo que permite usar **bisección** para encontrar
el menor `tf` factible (`feasible()`, [`lspb.py:75-87`](../irb120/lspb.py)): se duplica un límite
superior hasta que sea factible, y se bisecta 100 veces entre el límite infactible y el factible.

### 4.4 Sincronización entre juntas

`plan_lspb` recibe `vmax`/`amax` **por junta** pero calcula un único `tf` y `tb` usando el
`max` sobre las 6 juntas de `D_i/amax_i` (`accel_term`) y `D_i/vmax_i` (`cruise_term`) — es
decir, se diseña la trayectoria para la junta más exigente, y las demás juntas usan el mismo
`(tf, tb)` pero con una `V`, `a` menores (no saturan sus límites). Así las 6 juntas **arrancan y
llegan exactamente al mismo tiempo**, lo que mantiene la trayectoria en el espacio articular como
una línea recta (cada junta es una función afín de las demás durante todo el movimiento) y evita
que el TCP se desvíe de forma impredecible del camino recto articular.

### 4.5 Validación

`tests/test_lspb.py`: condiciones de borde en reposo, saturación de exactamente una junta en los
límites, continuidad de posición y velocidad en los empalmes `t=tb` y `t=tf−tb`, sincronía entre
juntas, e integración numérica de la velocidad para verificar que reproduce el desplazamiento
total (chequeo independiente de las fórmulas cerradas).

---

## 5. Dinámica Lagrangiana — `dynamics.py`

### 5.1 La ecuación de movimiento

Para un manipulador rígido, el formalismo de Lagrange (`L = T − U`, energía cinética menos
potencial) lleva a la ecuación estándar:

```
τ = M(q) q̈ + c(q, q̇) + g(q)
```

`M(q)` es la matriz de masa/inercia generalizada, `c(q,q̇)` agrupa los términos centrífugos y de
Coriolis, `g(q)` es el par necesario para sostener el peso del robot en la postura `q`.

### 5.2 Energía cinética y `M(q)`

La energía cinética total es la suma, por eslabón, de la energía de traslación del centro de
masa más la de rotación alrededor de él:

```
T = ½ Σᵢ [ mᵢ·vᵀ_ci·v_ci + ωᵀᵢ·I_ci·ωᵢ ]
```

Como el robot es una cadena serial, la velocidad del centro de masa del eslabón `i` y su
velocidad angular son **lineales en `q̇`**, a través de sus propios Jacobianos (idéntico
razonamiento que en §3.1, pero con `p_e` = centro de masa del eslabón `i`, y solo sumando
columnas hasta la junta `i`): `v_ci = Jv_i(q)·q̇`, `ω_i = Jw_i(q)·q̇`. Sustituyendo:

```
T = ½ q̇ᵀ · [ Σᵢ ( mᵢ·Jvᵢᵀ·Jvᵢ + Jwᵢᵀ·R_i·Iᵢ·R_iᵀ·Jwᵢ ) ] · q̇  =  ½ q̇ᵀ M(q) q̇
```

donde `R_i·Iᵢ·R_iᵀ` rota el tensor de inercia del eslabón (dado en su propio marco) a la base —
es exactamente `inertia_base = rotation @ link.inertia_kg_m2 @ rotation.T` en
`mass_matrix()` ([`dynamics.py:95-100`](../irb120/dynamics.py)). El resultado se simetriza
(`0.5·(M+Mᵀ)`) para eliminar asimetrías puramente numéricas: `M` es simétrica y definida positiva
por construcción física (es una forma cuadrática de energía, siempre ≥ 0, y > 0 salvo reposo
total), propiedad que verifica `test_mass_matrix_is_symmetric_positive_definite`.

### 5.3 Energía potencial y `g(q)`

`U(q) = Σᵢ mᵢ·g·hᵢ(q)`, con `hᵢ(q)` la altura (coordenada Z) del centro de masa del eslabón `i`,
que depende de `q` a través de la cinemática directa. El par gravitacional es

```
g(q) = ∂U/∂q,   componente j:  Σᵢ mᵢ·g· ∂hᵢ/∂qⱼ
```

Pero `∂hᵢ/∂qⱼ` es exactamente la fila Z del Jacobiano lineal del centro de masa `i`
(`Jvᵢ[2,:]`, porque `ḣᵢ = Jvᵢ[2,:]·q̇` relaciona la velocidad articular con la velocidad vertical
del centro de masa). Por eso `gravity_vector()` es
`Σᵢ mᵢ·g·Jvᵢ[2,:]` ([`dynamics.py:103-107`](../irb120/dynamics.py)) — no es una fórmula aparte, es
la misma Jacobiana de posición reutilizada.

### 5.4 Términos de Coriolis/centrífugos `c(q, q̇)`

De las ecuaciones de Euler-Lagrange aplicadas a `T(q,q̇) = ½ q̇ᵀM(q)q̇`:

```
d/dt(∂T/∂q̇) − ∂T/∂q = Ṁ(q)q̇ − ½ ∇_q(q̇ᵀ M(q) q̇)
```

(el primer término sale de derivar `M(q)q̇` en el tiempo —`Ṁq̇ + Mq̈`—, y el segundo es la
derivada parcial respecto a `q` de la energía cinética a `q̇` fijo). Separando la parte en
`q̈` (que va a `M(q)q̈`), lo que queda es exactamente

```
c(q, q̇) = Ṁ(q) q̇ − ½ ∇_q(q̇ᵀ M(q) q̇)
```

El código no deriva `M(q)` simbólicamente (sería un álgebra enorme con 6 eslabones); en su lugar
usa **diferencias centrales** para `∂M/∂qₖ` con paso `1e-6`
(`coriolis_vector()`, [`dynamics.py:110-126`](../irb120/dynamics.py)): el error de una diferencia
central es `O(paso²) ≈ 1e-12`, muy por debajo de la precisión necesaria, y evita escribir a mano
las derivadas de una matriz 6×6 que depende de 6 variables. Con `∂M/∂qₖ` para cada `k`, se forma
`Ṁq̇ = Σₖ q̇ₖ·(∂M/∂qₖ)·q̇` y el gradiente `[q̇ᵀ(∂M/∂q₁)q̇, ..., q̇ᵀ(∂M/∂q₆)q̇]`, que es
exactamente lo que calcula el código.

### 5.5 Parámetros inerciales y la pinza SMC MHZ2-16D

Las masas, centros de masa e inercias de los 6 eslabones (`_PAPER_LINKS`) son aproximaciones por
CAD publicadas en Truc y Lam (2020), ecuación 18 — **no** son una identificación real del robot
físico; sirven para mostrar la *tendencia cualitativa* (la divergencia en la singularidad), no
valores cuantitativos certificados.

La pinza (115 g, dato de hoja de fabricante) se fusiona con el eslabón 6 usando el **teorema de
ejes paralelos**:

```
I_P = I_cm + m·(‖d‖²·I₃ − d·dᵀ)
```

(la inercia de un cuerpo rígido respecto a un punto `P` desplazado `d` de su propio centro de
masa es la inercia en el centro de masa más un término que depende de la masa y del desplazamiento).
Para combinar dos cuerpos (muñeca + pinza) en uno solo:

1. Nuevo centro de masa combinado: promedio ponderado por masa de ambos centros de masa
   (`_with_gripper`, [`dynamics.py:64-71`](../irb120/dynamics.py)).
2. Se traslada la inercia de **cada** cuerpo (muñeca, pinza) desde su propio centro de masa
   hasta el nuevo centro de masa combinado, usando el teorema de ejes paralelos una vez por
   cuerpo (`_parallel_axis()` llamada dos veces).
3. Se suman ambas inercias trasladadas: por superposición, la inercia de un sistema compuesto
   respecto a un punto es la suma de las inercias de sus partes respecto a ese mismo punto.

Esto asume que la pinza es una masa puntual rígidamente unida al eslabón 6 (gira exactamente
igual que él) — razonable para una pinza neumática pequeña comparada con el eslabón.

### 5.6 Por qué el torque diverge cuadráticamente (`1/sin²q5`) cerca de la singularidad

`cartesian_demand()` ([`dynamics.py:142-155`](../irb120/dynamics.py)) encadena:

```
q̇ = J⁻¹ v                    (diverge ~ 1/|sin q5|, §3.5)
q̈ = J⁻¹ (a − J̇·q̇)           (J̇ se calcula por diferencia direccional a lo largo de q̇)
τ  = M(q)·q̈ + c(q,q̇) + g(q)
```

Como `J̇` se evalúa desplazándose en la dirección de `q̇` (que ya es grande cerca de la
singularidad), el término `J̇·q̇` también crece con `1/|sin q5|`; al aplicarle otra vez `J⁻¹`
(que aporta un factor adicional `1/|sin q5|`), `q̈` —y por tanto el torque dominante `M·q̈`—
crece como el **producto** de ambos factores: `~ 1/sin²(q5)`. El notebook del pasaporte mide
esta pendiente log-log y obtiene **−2.00**, confirmando exactamente el exponente 2 predicho.

### 5.7 Validación

`tests/test_singularity.py` comprueba, además de la factorización del determinante (§3.3): que
`M(q)` es simétrica y definida positiva en posturas aleatorias; que la masa de la pinza queda
correctamente fusionada en el eslabón 6; que `c(q,q̇)=0` cuando `q̇=0` (sin movimiento no hay
fuerzas centrífugas/Coriolis, consistencia física básica); y que la demanda de torque dinámico
efectivamente diverge al acercarse a `q5=0`.

---

## 6. Síntesis: por qué *todo* diverge en `q5 = 0`

Un único hecho geométrico —los ejes de las juntas 4 y 6 se alinean cuando `q5=0`— se propaga en
cascada por todo el sistema:

```
q5 → 0
   ⟹ det J = ±sin(q5)·det(Jp_brazo) → 0         (§3.3)
   ⟹ J pierde rango; σ_min(J) → 0                (§3.4)
   ⟹ q̇ = J⁻¹v  ~ 1/|sin q5|  → ∞                 (§3.5)
   ⟹ q̈ = J⁻¹(a − J̇q̇)  ~ 1/sin²(q5)  → ∞         (§5.6)
   ⟹ τ ≈ M·q̈ + ...  ~ 1/sin²(q5)  → ∞            (§5.6)
   ⟹ Pieper solo determina q4+q6, no q4 y q6 por separado  (§2.4)
```

Es la misma causa raíz vista desde cuatro ángulos distintos (cinemática inversa, Jacobiano,
cinemática de velocidad, dinámica), y el notebook `notebooks/03_singularidad_q5.ipynb`
("pasaporte") muestra exactamente esta cadena con gráficas y mediciones numéricas (pendientes
−0.97 y −2.00 en log-log, consistentes con los exponentes teóricos −1 y −2).

---

## 7. Preguntas probables de la defensa (con la matemática detrás)

**¿Por qué Pieper y no una IK numérica (Newton-Raphson, MoveIt)?**
Porque el IRB 120 tiene muñeca esférica (§1.2, `a4=a5=d5=0`), lo que permite desacoplar
posición/orientación y resolver en forma cerrada (§2.1). Una IK numérica no está prohibida por
limitación técnica, sino porque la guía exige demostrar la matemática, y aquí es posible hacerlo
exactamente.

**¿Por qué hasta 8 soluciones y no más/menos?**
2 configuraciones de brazo (frente/atrás, signo de `q1` y del radio) × 2 de codo (arriba/abajo,
las dos raíces de la ley de cosenos, §2.3) × 2 de muñeca (`q5` positivo o negativo, las dos
raíces de `θ=acos(R22)`, §2.4). Es el producto de tres decisiones binarias independientes.

**¿Cómo se elige una solución entre las 8?**
Se descartan las que violan límites articulares o alcance, se verifican contra la FK (§2.5), y
de las que quedan se toma la más cercana (norma euclídea en el espacio articular) a la postura
actual del robot — minimiza el movimiento necesario.

**¿Qué significa que el Jacobiano sea "triangular por bloques"?**
Que, tomando el centro de muñeca como punto de referencia, mover las juntas de la muñeca (4,5,6)
no traslada ese punto, solo lo reorienta — consecuencia directa de que sus ejes pasan por él
(§3.2). Eso permite factorizar el determinante en un bloque de "brazo" y uno de "muñeca" (§3.3).

**¿Por qué el determinante es exactamente `sin(q5)` y no otra función?**
Por la geometría de la secuencia de Euler ZYZ de la muñeca: el eje intermedio (`z4`) es
perpendicular a los otros dos, que a su vez difieren entre sí por el ángulo `q5` alrededor de
`z4` — el triple producto de esa configuración da `sin(q5)` (§3.3).

**¿Qué pasa exactamente en `q5=0`?**
El Jacobiano pierde un rango (los ejes 4 y 6 quedan colineales, giran "lo mismo"); no existe
`q̇=J⁻¹v` único; y en la IK de Pieper solo `q4+q6` queda determinado (§2.4, §3.4).

**¿Por qué LSPB y no un polinomio de orden mayor?**
Porque acota velocidad y aceleración con parámetros físicos directos (`vmax`, `amax`) y el
tiempo mínimo factible se obtiene en forma cerrada + una bisección trivial, aprovechando que la
factibilidad es monótona en `tf` (§4.3) — no hace falta resolver un sistema de ecuaciones de
borde de orden superior.

**¿Por qué todas las juntas comparten `tf` y `tb`?**
Para que lleguen exactamente a la vez y el camino en el espacio articular sea una línea recta
(evita desviaciones impredecibles del TCP respecto al camino esperado) (§4.4).

**¿De dónde sale `M(q)q̈ + c(q,q̇) + g(q)`?**
De las ecuaciones de Euler-Lagrange aplicadas a `T−U` de un sistema multicuerpo rígido en
cadena: `M(q)` sale de la energía cinética cuadrática en `q̇` (§5.2), `g(q)` del gradiente de la
energía potencial (§5.3), y `c(q,q̇)` de los términos que quedan al derivar `T` en el tiempo y
restar la derivada parcial respecto a `q` (§5.4).

**¿Por qué se usan diferencias finitas en vez de derivar `M(q)` a mano?**
Porque `M(q)` depende de 6 variables y derivarla simbólicamente a mano (o sus símbolos de
Christoffel) es un álgebra enorme y propensa a errores; la diferencia central con paso `1e-6`
tiene error `O(10⁻¹²)`, muchísimo más fino que cualquier tolerancia relevante del robot (§5.4).

**¿Qué tan confiable es la dinámica numéricamente?**
Cualitativamente sí (reproduce la tendencia de divergencia con los exponentes correctos, §5.6);
cuantitativamente no, porque las inercias son aproximaciones por CAD de un paper, no una
identificación del robot físico real (§5.5).

**¿Qué pinza se modeló y por qué importa?**
SMC MHZ2-16D, pinza neumática paralela de doble efecto, 115 g (dato de hoja de datos),
fusionada con el eslabón 6 por el teorema de ejes paralelos (§5.5); su masa entra dentro de la
carga adicional admisible de 0.3 kg del IRB 120.

---

## Anexo A — Producto completo de las 4 matrices DH elementales

```
Rz(θ)·Tz(d) =
| cθ  -sθ  0   0 |
| sθ   cθ  0   0 |
| 0    0   1   d |
| 0    0   0   1 |

(Rz(θ)·Tz(d))·Tx(a) =
| cθ  -sθ  0   a·cθ |
| sθ   cθ  0   a·sθ |
| 0    0   1   d    |
| 0    0   0   1    |

(Rz(θ)·Tz(d)·Tx(a))·Rx(α) =
| cθ   -sθ·cα    sθ·sα    a·cθ |
| sθ    cθ·cα   -cθ·sα    a·sθ |
| 0     sα       cα       d    |
| 0     0        0        1    |
```

que es la matriz implementada en `dh_transform()` ([`dh.py:45-69`](../irb120/dh.py)).

## Anexo B — Referencias citadas en el código

- Tabla DH: Bahani et al. (2023), Tabla I.
- Parámetros inerciales: Truc y Lam, *Turk J Elec Eng & Comp Sci* 28 (2020), ecuación 18.
- Pinza: SMC MHZ2-16D, hoja de datos del fabricante (115 g).
- Método de cinemática inversa: Pieper, D. L. (1968), *The kinematics of manipulators under
  computer control* (tesis doctoral, Stanford) — origen del método de desacople para muñecas
  esféricas usado en §2.

## Anexo C — Mapa código ↔ sección de este documento

| Archivo | Sección |
|---|---|
| `irb120/dh.py` | §1 |
| `irb120/pieper.py` | §2 |
| `irb120/jacobian.py` | §3 |
| `irb120/lspb.py` | §4 |
| `irb120/dynamics.py` | §5 |
| `irb120/transforms.py` | utilidades de rotación usadas en ejemplos (rpy, cuaterniones) |
| `tests/test_dh.py`, `test_pieper.py`, `test_lspb.py`, `test_singularity.py` | validación numérica de cada sección |
| `notebooks/01_cinematica_inversa_pieper.ipynb` | evidencia de §2 (1000 poses) |
| `notebooks/02_trayectorias_lspb.ipynb` | evidencia de §4 |
| `notebooks/03_singularidad_q5.ipynb` | evidencia de §3, §5 y §6 (el "pasaporte") |

Documentación complementaria (uso, API, ejemplos ejecutables) en
[`docs/hito2/guia_hito2.md`](../../archivo/hito2_ros_anterior/documentacion/guia_hito2.md) y
[`docs/hito2/metodo_y_resultados.md`](../../archivo/hito2_ros_anterior/documentacion/metodo_y_resultados.md).
