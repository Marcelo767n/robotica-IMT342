# 02. Criterio A: cinemática inversa analítica por Pieper

> Código: [`irb120/pieper.py`](../irb120/pieper.py) y [`analizar_pose.py`](../analizar_pose.py) ·
> Pruebas: [`tests/test_pieper.py`](../tests/test_pieper.py) · Ejemplo numérico: [08](08_ejemplo_resuelto_a_mano.md)

**Lo que pide la rúbrica para "Excelente":** estructura analítica; manejo correcto de las ramas (hasta 8); uso de
`atan2`; procesar todas las poses; distinguir candidatos **reales** de **admisibles**; explicar la geometría de las
ramas. Es "Insuficiente" si se usa un solver numérico o se entrega una sola solución sin justificarla.

## 1. Por qué existe una solución cerrada

El teorema de Pieper dice que un 6R tiene IK en forma cerrada si **tres ejes consecutivos se cortan en un punto**. En el
IRB 120, los ejes 4, 5 y 6 se cortan en el **centro de muñeca** W: en la tabla DH, $a_4 = a_5 = d_5 = 0$. Eso
permite **desacoplar** el problema:

- La **posición** de W depende solo de $q_1, q_2, q_3$, el brazo.
- La **orientación** se completa con $q_4, q_5, q_6$, la muñeca.

## 2. Paso 0: del TCP a la brida y al centro de muñeca

La pose que escribe el usuario es la del TCP. Primero se pasa a la brida y luego se retrocede $d_6$ por el eje $z_6$
para llegar a W:

$$
T_{tool0} = T_d\,T_z(0.150)^{-1}, \qquad p_{W} = p_{tool0} - d_6\,z_6 = p_{TCP} - (0.150 + 0.072)\,z_6
$$

Aquí $z_6$ es la tercera columna de $R_d$. Código: `tool0_from_tcp` ([pieper.py:253](../irb120/pieper.py#L253)) y
`wrist_center` ([pieper.py:108](../irb120/pieper.py#L108)).

## 3. Paso 1: posición, $q_1, q_2, q_3$ (4 ramas)

### 3.1 $q_1$: brazo "frente" o "atrás"

El brazo se mueve en un plano vertical que contiene a W y al eje 1. Hay dos formas de orientar ese plano:

$$
q_1^{\text{frente}} = \operatorname{atan2}(y_W, x_W), \qquad q_1^{\text{atrás}} = q_1^{\text{frente}} + \pi
$$

Se usa `atan2` y no `atan(y/x)` porque `atan` solo devuelve $(-\pi/2, \pi/2)$ y confunde los cuadrantes: un punto en
$(-1, -1)$ daría lo mismo que $(1, 1)$. `atan2(y, x)` usa el signo de los dos argumentos y devuelve el ángulo
correcto en $(-\pi, \pi]$.

En el plano del brazo, W queda a una distancia horizontal $r = \pm\sqrt{x_W^2 + y_W^2}$ (con signo + para frente y −
para atrás) y a una altura $h = z_W - d_1$ sobre el hombro S.

### 3.2 Geometría del brazo en su plano

- Brazo: segmento S→codo de longitud $L_2 = a_2 = 0.270$ m.
- Antebrazo: del codo a W no es una recta del eje: sube $a_3 = 0.070$ y avanza $d_4 = 0.302$. Equivale a un segmento
  de longitud $L_3 = \sqrt{d_4^2 + a_3^2} = 0.31001$ m inclinado un ángulo fijo $\delta = \operatorname{atan2}(a_3, d_4) = 13.05°$.

Con la tabla DH, la cinemática directa de W en el plano es:

$$
r = L_2 \sin q_2 + L_3\cos(q_2 + q_3 - \delta), \qquad
h = L_2\cos q_2 - L_3 \sin(q_2 + q_3 - \delta)
$$

(Comprobación: con $q = 0$ queda $r = L_3\cos\delta = d_4$ y $h = L_2 + L_3\sin\delta = a_2 + a_3$.)

### 3.3 $q_3$: ley de cosenos, codo "arriba" o "abajo"

Se elevan al cuadrado y se suman las dos ecuaciones; $q_2$ desaparece:

$$
D^2 = r^2 + h^2 = L_2^2 + L_3^2 + 2L_2L_3\big[\sin q_2\cos\varphi - \cos q_2\sin\varphi\big],\quad \varphi = q_2+q_3-\delta
$$

$$
\Rightarrow\quad -\sin(q_3 - \delta) = \frac{D^2 - L_2^2 - L_3^2}{2L_2L_3} \equiv c
$$

- Si $|c| > 1$, **la rama no es real**: W está fuera del anillo $|L_2 - L_3| \le D \le L_2 + L_3$, es decir
  $0.040 \le D \le 0.580$ m. Esa es la prueba de alcanzabilidad geométrica.
- Si $|c| \le 1$, hay **dos** soluciones, porque $\sin$ toma cada valor dos veces en una vuelta:

$$
q_3^{\text{arriba}} = \delta + \arcsin(-c), \qquad q_3^{\text{abajo}} = \delta + \pi - \arcsin(-c)
$$

Geométricamente son los dos triángulos S-codo-W reflejados respecto de la recta SW, el codo arriba o abajo de esa
recta. Aquí `asin` es suficiente: el argumento ya está en $[-1, 1]$ y la segunda rama se construye explícitamente
como $\pi - (\cdot)$. Después se envuelve a $(-\pi, \pi]$.

### 3.4 $q_2$: ángulo del hombro

Medido desde la vertical, el vector S→W forma el ángulo $\alpha = \operatorname{atan2}(r, h)$. El brazo apunta a
$q_2$ y el antebrazo a $q_2 + \eta$, con $\eta = \pi/2 + q_3 - \delta$. La suma de los dos vectores debe apuntar a
$\alpha$:

$$
q_2 = \alpha - \operatorname{atan2}\big(L_3\sin\eta,\ L_2 + L_3\cos\eta\big)
$$

El segundo `atan2` es el ángulo que forma S→W con el brazo dentro del triángulo. Usar `atan2` aquí mantiene el
cuadrante correcto también cuando el codo queda "detrás" del hombro.

Código: `_arm_branches` ([pieper.py:114](../irb120/pieper.py#L114)). Recorre `("frente", "atras")` y luego
`("arriba", "abajo")`; si $|c| > 1$ devuelve la rama marcada `real=False` con `nan`.

## 4. Paso 2: orientación, $q_4, q_5, q_6$ (2 ramas de muñeca)

Con $q_1, q_2, q_3$ conocidos, $R_0^3$ es conocida y lo que falta es

$$
R_3^6 = (R_0^3)^T R_d
$$

De la tabla DH, filas 4 a 6:

$$
R_3^6 = R_z(q_4)R_x(\tfrac{\pi}{2})\;R_z(q_5)R_x(-\tfrac{\pi}{2})\;R_z(q_6+\pi) = R_z(q_4)\,R_y(-q_5)\,R_z(q_6 + \pi)
$$

porque $R_x(\frac{\pi}{2})R_z(q_5)R_x(-\frac{\pi}{2})$ es una rotación de $q_5$ alrededor de
$R_x(\frac{\pi}{2})\hat z = -\hat y$. Es una secuencia de **Euler ZYZ** con $a = q_4$, $b = -q_5$ y $c = q_6 + \pi$:

$$
R_z(a)R_y(b)R_z(c) =
\begin{bmatrix}
\cdot & \cdot & c_a s_b\\
\cdot & \cdot & s_a s_b\\
-s_b c_c & s_b s_c & c_b
\end{bmatrix}
$$

De la tercera columna y la tercera fila:

$$
s_b = \pm\sqrt{R_{13}^2 + R_{23}^2},\quad b = \operatorname{atan2}(s_b, R_{33}),\quad
a = \operatorname{atan2}\Big(\tfrac{R_{23}}{s_b}, \tfrac{R_{13}}{s_b}\Big),\quad
c = \operatorname{atan2}\Big(\tfrac{R_{32}}{s_b}, \tfrac{-R_{31}}{s_b}\Big)
$$

- El signo $\pm$ de $s_b$ da las **dos ramas de muñeca** (la "muñeca volteada"). Como $b = -q_5$, el signo de $s_b$
  es el **opuesto** al de $q_5$. Las ramas se nombran por el signo **real** de $q_5$: `q5+` ($q_5 > 0$, $s_b < 0$) y
  `q5-` ($q_5 < 0$, $s_b > 0$). Lo garantiza la prueba `test_wrist_labels_match_the_sign_of_q5`. Las dos dan la misma
  orientación final: $(q_4, q_5, q_6)$ y $(q_4 + \pi, -q_5, q_6 + \pi)$.
- En el código no se divide por $s_b$: se multiplican los argumentos de `atan2` por el signo, que es equivalente y no
  falla cuando $s_b$ es pequeño.
- **Singularidad de muñeca** ($s_b \approx 0$, es decir $q_5 = 0$): los ejes 4 y 6 quedan alineados y solo se
  determina $q_4 + q_6$. El código fija $q_4$ igual al de referencia, calcula $q_6$ y marca `singular_wrist=True`.

Código: `_rotation_0_3` ([pieper.py:142](../irb120/pieper.py#L142)) y `_wrist_solutions` ([pieper.py:149](../irb120/pieper.py#L149)).

## 5. Las 8 ramas: real frente a admisible

$2\ (\text{brazo}) \times 2\ (\text{codo}) \times 2\ (\text{muñeca}) = 8$ candidatos.
`enumerate_candidates` ([pieper.py:180](../irb120/pieper.py#L180)) **siempre devuelve los 8**, en orden fijo:

| Rama | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Brazo | frente | frente | frente | frente | atrás | atrás | atrás | atrás |
| Codo | arriba | arriba | abajo | abajo | arriba | arriba | abajo | abajo |
| Muñeca | q5+ | q5− | q5+ | q5− | q5+ | q5− | q5+ | q5− |

Cada candidato (`Candidate`, [pieper.py:68](../irb120/pieper.py#L68)) se clasifica así:

1. **Real:** la ley de cosenos tiene solución ($|c| \le 1$). Si no lo es, no existe ningún $q$.
2. **Dentro de límites:** para cada junta se busca un representante $q_i + 2\pi k$ dentro de los límites del
   fabricante (`_fit_to_limits`, [pieper.py:97](../irb120/pieper.py#L97)). Esto importa en la junta 6, que gira
   ±400° y tiene varias vueltas válidas: se elige la más cercana a la postura de referencia. Si alguna junta no cabe,
   se anota en `out_of_limits`.
3. **Verificado por FK:** es el criterio B. Ver [03_B_validacion_fk.md](03_B_validacion_fk.md).

**Admisible = real + dentro de límites + verificado por FK.**

`analyze_pose(T_d)` ([pieper.py:337](../irb120/pieper.py#L337)) hace las tres cosas y devuelve un `PoseReport` con
la tabla de 8 filas (`.table()`) y un veredicto (`.verdict`):

- `ALCANZABLE: k de 8 ramas son admisibles.`
- `NO ALCANZABLE: la distancia hombro-muñeca ... está fuera de [0.040, 0.580] m.` Ninguna rama es real.
- `NO ALCANZABLE: existe geométricamente, pero todas las ramas violan límites articulares (juntas [...])`.

Así **cualquier pose** que escriba el docente se procesa y se clasifica, y nunca hay que adivinar por qué falló.

## 6. Pose inicial y selección de la configuración objetivo

**Pose inicial.** Es la posición de calibración de ABB, con todos los ejes en 0° (`HOME_Q` en
[dh.py](../irb120/dh.py)). Se **elige** como pose inicial porque es la postura de referencia de ABB para la sincronización: el robot se lleva a
ella con `MoveAbsJ` y un jointtarget de ceros para verificar los contadores de revolución. Es una elección del equipo,
no una "home" obligatoria del fabricante. Su pose del TCP es $T_0 = FK(0)$: TCP en (0.524, 0, 0.630) m con la herramienta apuntando hacia $+x$.

Pieper también se aplica a $T_0$ y recupera $q = 0$ (rama 1, la única admisible). Como en $q = 0$ los ejes 4 y 6 están
alineados ($q_5 = 0$), la rama sale marcada `singular_wrist`: solo $q_4 + q_6$ queda determinado y se toma $q_4$ de
la referencia. Lo comprueba la prueba `test_home_pose_is_calibration_position_and_is_recovered`.

**Configuración objetivo: de 8 ramas a 1.** `rank_candidates(report, HOME_Q)`
([pieper.py:377](../irb120/pieper.py#L377)) evalúa **las 8 ramas** y devuelve, para cada una, si es
admisible, $\sigma_{\min}(J)$, el margen al límite articular más cercano, el desplazamiento ponderado, el $t_f$ del
LSPB y su estado (elegida, apta o el motivo del descarte). `select_solution`
([pieper.py:438](../irb120/pieper.py#L438)) devuelve la que queda en el puesto 1.

**Criterio propuesto** (filtros en orden y luego un costo):

| Paso | Regla | Justificación |
|---|---|---|
| 1 | **Admisible**: real, dentro de límites y verificada por FK | Obligatorio. Si no es real, la postura no existe; si viola límites, el robot no la puede adoptar; si no pasa la FK, no es solución |
| 2 | **Lejos de singularidad**: $\sigma_{\min}(J) \ge 0.01$ | $\lVert\dot q\rVert \le \lVert\dot x\rVert/\sigma_{\min}$: con $\sigma_{\min} \ge 0.01$, la amplificación de velocidad queda acotada a 100× ([06](06_D_singularidades.md)). Terminar cerca de una singularidad haría que cualquier corrección o movimiento posterior exija velocidades enormes |
| 3 | **Lejos de los topes**: margen $\ge 5°$ en las 6 juntas | El controlador real usa límites de software y el seguimiento tiene error. Una postura pegada a un tope no deja margen para corregir ni para seguir hacia otra pose |
| 4 | **Mínimo desplazamiento ponderado** $\lVert W(q - q_0)\rVert$, con $W = \operatorname{diag}(1,1,1,\tfrac12,\tfrac12,\tfrac12)$; desempate por mayor $\sigma_{\min}$ | Menor recorrido es menos tiempo, menos energía y menos volumen barrido (menos riesgo de colisión), y evita "voltear" brazo o muñeca. Las juntas 1 a 3 mueven unos 12 kg y las de la muñeca menos de 3 kg: por eso pesan el doble |

**¿Por qué no minimizar $t_f$?** El tiempo del LSPB lo fija una sola junta (a menudo la muñeca) y depende del
supuesto de $a_{\max}$. Se reporta, pero no decide. **¿Y si ninguna pasa los filtros 2 y 3?** Se relaja primero el
margen y después $\sigma_{\min}$, y el estado lo indica ("margen relajado"). Así, una pose alcanzable nunca queda sin
solución.

En el notebook (sección 4) la tabla muestra las 8 ramas con estas columnas. La figura `A_ocho_ramas_3d` dibuja el
robot en cada rama: verde la elegida, azul las aptas y rojo discontinuo las que violan límites.

## 7. Herramienta para el docente

```bash
python analizar_pose.py X Y Z ROLL PITCH YAW      # m y grados
python analizar_pose.py 0.40 0.10 0.35 0 180 0
```

Imprime $T_d$, $p_W$, la distancia hombro-muñeca frente al rango alcanzable, la tabla de las 8 ramas (real, límites,
$q$ en grados, $e_p$, $e_R$, aceptada), el veredicto y la rama que se seleccionaría desde la pose inicial ($q = 0$).

## 8. Pruebas automáticas (`tests/test_pieper.py`)

| Prueba | Qué demuestra |
|---|---|
| `test_recovers_original_joints...` | 200 $q$ aleatorios: el $q$ original aparece entre las soluciones y todas cumplen FK |
| `test_always_eight_candidates_in_fixed_order` | Siempre hay 8 ramas, distintas, numeradas 1 a 8 |
| `test_every_real_branch_reproduces_the_pose_even_outside_limits` | Toda rama real reproduce $T_d$ por FK, incluso las que violan límites, así que la geometría es correcta |
| `test_unreachable_pose_has_no_real_branch` | Pose a 1 m: ninguna rama real, veredicto "fuera de" |
| `test_pose_that_exists_only_outside_joint_limits` | Pose geométricamente posible pero bloqueada por límites ($q_3 = 90° > 70°$) |
| `test_home_pose_is_calibration_position_and_is_recovered` | Desde $T_0 = FK(0)$, Pieper recupera $q = 0$ y la marca como muñeca singular |
| `test_rejects_matrices_that_are_not_rigid_poses` | Rechaza matrices que no son poses rígidas: $\det R \ne 1$, $R$ no ortonormal o última fila incorrecta |
| `test_wrist_labels_match_the_sign_of_q5` | La etiqueta `q5+`/`q5-` coincide con el signo real de $q_5$ |
| `test_ranking_covers_eight_branches_and_picks_one` | Se evalúan las 8 ramas, se elige exactamente una y las descartadas tienen motivo |
| `test_wrist_singularity_q5_zero_is_solved` | En $q_5 = 0$ se marca `singular_wrist` y se sigue resolviendo |
| `test_selection_prefers_closest_admissible_branch` | La selección recupera la rama de la postura de referencia |

## Preguntas de defensa

1. *¿Por qué son 8 y no infinitas soluciones?* Para una pose genérica: 2 orientaciones del plano del brazo × 2
   triángulos del codo × 2 signos de $\sin q_5$. Solo hay infinitas en una singularidad, por ejemplo $q_5 = 0$, donde
   solo importa $q_4 + q_6$.
2. *¿Qué significa que una rama no sea real?* Que $|c| > 1$: ningún triángulo de lados $L_2$, $L_3$ y $D$ existe.
3. *¿Por qué una rama real puede no ser admisible?* Porque la matemática no conoce los topes mecánicos: el ángulo
   existe, pero el motor no puede llegar a él.
4. *¿Por qué `atan2`?* Porque conserva el cuadrante usando los signos de los dos argumentos y no se indefine cuando
   $x = 0$.
5. *¿Dónde está el desacople?* En que $p_W$ no depende de $q_4, q_5, q_6$: por eso primero se resuelve el brazo y
   después la muñeca.
