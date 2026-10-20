# 06. Criterio D (segunda parte): singularidades y pérdida de rango

> Código: [`irb120/jacobian.py`](../irb120/jacobian.py) (`rank_analysis`, `weakest_directions`) ·
> Pruebas: [`tests/test_jacobian.py`](../tests/test_jacobian.py), [`tests/test_singularity.py`](../tests/test_singularity.py)

**Lo que pide la rúbrica para "Excelente":** usar el **rango** como criterio central (el determinante solo cuando
corresponde); un **experimento independiente** de aproximación a una singularidad conocida; explicar **qué movilidad
se pierde** y la **amplificación de velocidades, sin confundirla con torque infinito**. Es "Insuficiente" declarar
singularidad solo por observación o usar mal el determinante.

## 1. Definición

$q^*$ es singular si

$$
\operatorname{rank} J(q^*) < \operatorname{rank}_{\max} = 6
$$

Eso significa que existe al menos una dirección del twist $[v; \omega]$ que el TCP **no puede generar** con ninguna
combinación de $\dot q$.

## 2. Por qué rango con SVD y no solo determinante

La descomposición en valores singulares (SVD) es

$$
J = U\,\Sigma\,V^T = \sum_{i=1}^{6} \sigma_i\, u_i\, v_i^T, \qquad \sigma_1 \ge \dots \ge \sigma_6 \ge 0
$$

- **Rango numérico** = número de $\sigma_i > \text{tol}$. Se usa $\text{tol} = 10^{-6}$ (`RANK_TOLERANCE`).
- $v_i$ (columna de $V$): un movimiento articular unitario. $u_i$ (columna de $U$): el twist que produce, escalado
  por $\sigma_i$, porque $J v_i = \sigma_i u_i$.
- Si $\sigma_6 = 0$:
  - $u_6$ = **dirección cartesiana perdida**: ningún $\dot q$ la genera (`lost_twist_directions`).
  - $v_6$ = **movimiento articular nulo**: mueve las juntas pero el TCP queda quieto (`null_joint_motions`).

**El determinante** cumple $|\det J| = \prod \sigma_i$ (el signo lo dan $\det U$ y $\det V^T$) y solo existe porque $J$ es **cuadrada**. Además:

- No dice **cuántas** direcciones se pierden ni **cuáles**.
- Su escala depende de las unidades (mezcla m y rad) y puede ser pequeño sin que haya singularidad, o al revés.
- Se usa solo como **complemento**, para la factorización analítica de abajo.

**Unidades.** $J$ mezcla filas lineales [m/s por rad/s] y angulares [rad/s por rad/s]. El **rango** no cambia si se
reescalan las unidades, pero los valores $\sigma_i$, el número de condición y la tolerancia $10^{-6}$ sí dependen de
la escala elegida. Aquí se usa SI con longitudes en metros. Una "carga unitaria en $u_6$" es el vector $[F; M]$ de
norma 1, con $F$ en N y $M$ en N·m, en esa misma escala.

Código: `rank_analysis(J)` ([jacobian.py:170](../irb120/jacobian.py#L170)) devuelve `singular_values`, `rank`,
`is_singular`, `condition_number`, `lost_twist_directions` y `null_joint_motions`.

## 3. Las tres singularidades del IRB 120 (de dónde salen)

Con el punto de referencia en el centro de muñeca W, $J$ es **triangular por bloques**: las juntas 4 a 6 no mueven W,
así que $J_{v,4..6} = 0$:

$$
J_W = \begin{bmatrix} J_{11} & 0 \\ J_{21} & J_{22}\end{bmatrix} \Rightarrow
\det J = \det J_{11}\cdot\det J_{22}
$$

El determinante no depende del punto de referencia: cambiar del TCP a W multiplica por una matriz de determinante 1.
Calculando cada bloque (comprobado numéricamente en `test_determinant_factorizes...`):

$$
\det J = \underbrace{L_2 L_3\cos(q_3 - \delta)\; r_W}_{\det J_{11}\ (\text{brazo})} \cdot \underbrace{(-\sin q_5)}_{\det J_{22} = \det[z_3\ z_4\ z_5]}
$$

con $r_W = L_2\sin q_2 + L_3\cos(q_2 + q_3 - \delta)$, la distancia horizontal de W al eje 1.

| Singularidad | Condición | Qué pasa físicamente | ¿Dentro de límites? |
|---|---|---|---|
| **Muñeca** | $q_5 = 0$ | Ejes 4 y 6 **colineales** ($z_5 = z_3$): dos motores hacen lo mismo | Sí ($q_5 \in [-120°, 120°]$). Incluye la postura cero |
| **Codo** | $\cos(q_3 - \delta) = 0 \Rightarrow q_3 = \delta - 90° = -76.95°$ | Brazo **totalmente estirado**: borde exterior del espacio de trabajo | Sí ($q_3 \ge -110°$) |
| **Hombro** | $r_W = 0$ | W sobre el eje 1: girar la base no mueve W | Sí |

Prueba de la de codo: `test_elbow_singularity_when_arm_is_stretched`.

## 4. Experimento computacional independiente (el que pide la rúbrica)

Se elige la **singularidad de muñeca**, porque es la más común en operación y la más clara de interpretar. Las
juntas 1 a 4 y 6 se fijan en una postura regular $q = (30°, -20°, 15°, 40°, q_5, 60°)$ y se recorre la secuencia

$$
q_5 \in \{45°, 30°, 20°, 10°, 5°, 3°, 1°, 0.3°, 0.1°, 0.03°, 0.01°, 0°\}
$$

En cada punto se registra:

1. $\sigma_1, \dots, \sigma_6$ y el **rango**: 6 en todos los puntos menos en $q_5 = 0$, donde baja a **5**.
2. $\sigma_6$: decrece proporcionalmente a $\sin q_5$.
3. El número de condición $\kappa = \sigma_1/\sigma_6$, que crece como $1/\sin q_5$.
4. $\det J$ como complemento, junto a la curva teórica $-\sin q_5 \det J_{11}$.

Gráficas (en el notebook): $\sigma_i$ frente a $q_5$ en escala log y rango frente a $q_5$ (escalón 6 → 5).

### 4.1 ¿Qué movilidad se pierde?

En $q_5 = 0$, $z_5 = z_3$, así que las velocidades angulares que puede aportar la muñeca solo están en el plano
generado por $z_3$ y $z_4$. **Se pierde la rotación alrededor de $z_3 \times z_4$.** La dirección perdida $u_6$ que
da la SVD, expresada con el **centro de muñeca W** como punto de referencia (`geometric_jacobian(q, "wrist")`), tiene
una parte angular exactamente paralela a $z_3 \times z_4$ (comprobado numéricamente, $|\cos| = 1$) y además una parte
lineal, porque $J$ acopla brazo y muñeca: el twist inalcanzable es una combinación de los dos. Con el TCP como
referencia, la parte angular se mezcla con la palanca W→TCP y el paralelismo es solo aproximado ($|\cos| \approx 0.995$).

El movimiento nulo es $v_6 \propto (0, 0, 0, 1, 0, -1)$: **$\dot q_4 = -\dot q_6$**, los dos motores giran en sentidos
opuestos y se cancelan. El TCP no se mueve. Está verificado en
`test_wrist_singularity_loses_one_rank_with_q4_minus_q6_null_motion`.

### 4.2 Amplificación de velocidad

Para producir un twist unitario en la dirección más débil, $u_6$:

$$
\dot q = J^{-1} u_6 = \frac{1}{\sigma_6}\,v_6 \quad\Rightarrow\quad \lVert \dot q\rVert = \frac{1}{\sigma_6} \propto \frac{1}{|\sin q_5|}
$$

Código: `weakest_directions(J)` ([jacobian.py:177](../irb120/jacobian.py#L177)) y la prueba
`test_velocity_amplification_is_inverse_of_sigma_min`. Valores medidos: $\sigma_6/\sin q_5 \approx 0.150$, constante en
toda la secuencia. Para saber si la velocidad exigida es posible hay que comparar **junta por junta** con el
datasheet, no la norma del vector: $\rho = \max_i |\dot q_i|/v_{\max,i}$. Para un twist unitario en $u_6$ con
$q_5 = 0.01°$, los ejes 4 y 6 deberían girar a $\dot q_4 \approx -\dot q_6 \approx 27\,040$ rad/s, es decir,
$\rho \approx 4\,842$ veces su máximo. $\rho$ es proporcional a la magnitud del twist pedido: el notebook informa
desde qué $q_5$ se supera el datasheet para 1 y para 0.1 unidades. En log-log, la
pendiente de $\lVert\dot q\rVert$ frente a $q_5$ es $-1$.

### 4.3 Lo que NO significa: torque infinito

- La singularidad es una propiedad **cinemática** de $J$. Lo que diverge es la **velocidad articular** necesaria para
  ciertos twists cartesianos.
- En **estática**, $\tau = J^T F$. En la singularidad, $J^T u_6 = \sigma_6 v_6 = 0$: una fuerza o momento en la
  dirección perdida $u_6$ **no requiere torque** porque la estructura la soporta. En esa dirección el robot es
  "rígido", no débil.
- Los torques solo crecen si **se insiste** en seguir una trayectoria **cartesiana** a través de la singularidad:
  $\ddot q = J^{-1}(\ddot x - \dot J\dot q)$ explota y con él $M\ddot q$. Es consecuencia de la exigencia de
  velocidad y aceleración, no de la singularidad en sí. El notebook anterior del anexo mostraba ese caso; aquí se
  aclara la causa.
- Nuestra trayectoria LSPB es **articular**: puede cruzar $q_5 = 0$ sin que nada diverja, porque no se invierte $J$.

## Preguntas de defensa

1. *¿Cómo sabes que es singular?* Porque el rango numérico de $J$ por SVD baja de 6 a 5 ($\sigma_6 < 10^{-6}$), no
   porque "se vea raro".
2. *¿Qué se pierde en $q_5 = 0$?* Una dirección de rotación ($z_3\times z_4$); además aparece el movimiento interno
   $\dot q_4 = -\dot q_6$, que no mueve el TCP.
3. *¿Por qué no usar solo el determinante?* No dice cuántas ni cuáles direcciones se pierden, depende de las
   unidades y solo existe para matrices cuadradas.
4. *¿El robot se rompe en una singularidad?* No. Pierde una dirección de movimiento local. Las velocidades
   articulares se disparan solo si se pide moverse en esa dirección; los torques estáticos no.
5. *¿Qué diferencia hay entre singularidad y pico de torque?* La singularidad es geometría ($J$ pierde rango). El pico
   de torque es dinámica: masa por aceleración más gravedad (ver [07](07_E_dinamica_1R.md)). Pueden ocurrir uno sin
   el otro.
