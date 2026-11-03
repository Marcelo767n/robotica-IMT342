# 10. Guía de defensa del Hito 2

**Qué se evalúa (20 % del Hito 2, individual):** cada integrante responde por **todo** el proyecto, no solo por su
parte.

| Subcriterio | Peso | Qué tienes que demostrar |
|---|---|---|
| **G1** Pipeline | 5 % | Cómo se conectan las etapas: qué entra y qué sale de cada una |
| **G2** Matemática | 5 % | Reconstruir **al menos una ecuación** (en la pizarra, sin leer) |
| **G3** Validación / interpretación | 5 % | Cómo sabes que un número es correcto y qué significa físicamente |
| **G4** Transferencia | 5 % | Responder sobre una parte **que no programaste** |

> ⚠️ Regla de la rúbrica: quien no demuestre comprensión mínima recibe una reducción individual, **aunque el código
> funcione**. "Lo generó la IA" **no** es una respuesta válida.

---

## 1. Plan de estudio para hoy (≈ 4 h, en este orden)

| # | Qué | Dónde | Tiempo |
|---|---|---|---|
| 1 | Memorizar el pipeline en una frase (§3 de este archivo) | aquí | 10 min |
| 2 | Hacer **a mano** el ejemplo de Pieper, con calculadora | [08_ejemplo_resuelto_a_mano.md](08_ejemplo_resuelto_a_mano.md) §1–§6 | 45 min |
| 3 | Las 4 ecuaciones para la pizarra (§4) | aquí + 02, 04, 05, 07 | 45 min |
| 4 | Preguntas y respuestas (§6), primero leyendo y después tapando las respuestas | aquí | 60 min |
| 5 | Ensayar la demo (§2) con el notebook abierto | notebook | 30 min |
| 6 | Simulacro de **pose nueva** (§5) | notebook | 15 min |
| 7 | Transferencia: cada integrante explica a otro la parte que **menos** conoce | — | 30 min |

Si te falta tiempo, prioriza **2, 3 y 4**: son G2, G3 y G4.

---

## 2. Qué mostrar en la demo y en qué orden (8–10 min)

> **Apoyo visual:** `hito2/presentacion/Hito2_en_vivo.html` (doble clic; funciona sin internet) recorre lo mismo por
> criterio de la rúbrica, con el robot en 3D, la animación y los controles deslizantes. Se puede usar en lugar del
> notebook para mostrar y, si el docente pide "el código", se abre el notebook o el paquete `irb120/`. Ver
> `presentacion/README.md`.

Abrir `hito2/Hito2_IRB120_pipeline.ipynb` (ya ejecutado; no hace falta correrlo para mostrarlo).

| Min | Sección del notebook | Qué mostrar | Qué decir (una frase) |
|---|---|---|---|
| 0–1 | §1.2 y §1.3 | Pose inicial (q = 0) y celda de **ENTRADA** | "El docente escribe la pose aquí; todo lo demás se recalcula solo." |
| 1–3 | §2 tabla + §2.2 figura **8 ramas 3D** | Las 8 ramas: reales, en límites, admisibles | "Pieper analítico: 2 brazo × 2 codo × 2 muñeca; 8 reales, 1 admisible y el resto viola límites." |
| 3–4 | §3 tabla de errores + §3.1 | Errores de 1e-16; DH frente al modelo oficial de ROS-Industrial | "Toda rama se reinyecta en la FK, en posición **y** orientación. Y la FK coincide con el modelo **oficial** de ROS-Industrial, que no usa nuestra tabla DH." |
| 4–5 | §4 tabla de decisión | Criterio de 4 pasos | "Admisible → lejos de singularidad → lejos de topes → menor desplazamiento ponderado." |
| 5–6 | §5 gráfica de 3 perfiles + §5.1 movimiento 3D | q, q̇, q̈ alineados; fases | "LSPB sincronizado de tiempo mínimo; la junta 5 limita; reposo en los extremos." |
| 6–8 | §7 rango + amplificación | Rango 6 → 5; q̇4 = −q̇6; ρ ≈ 4842 | "Singularidad = pérdida de rango por SVD. Amplifica velocidad, no torque." |
| 8–10 | §8 τ(t) + 1R frente al completo | Componentes; pico; sostén | "τ = Jq̈ + mgℓc sin θ: en crucero el torque no es cero; el pico está al frenar." |

**Código para mostrar si lo piden** (abrir el archivo en la línea indicada):

| Pregunta probable | Archivo y función |
|---|---|
| "¿Dónde está Pieper?" | `irb120/pieper.py`: `wrist_center` (l. 109), `_arm_branches` (l. 115, ley de cosenos), `_wrist_solutions` (l. 150, Euler ZYZ), `enumerate_candidates` (l. 183) |
| "¿Cómo eligen la rama?" | `irb120/pieper.py`: `rank_candidates` (l. 377) |
| "¿Cómo validan?" | `irb120/validation.py`: `fk_check` (l. 45) |
| "¿La FK?" | `irb120/dh.py`: `dh_transform` (l. 66) y `forward_kinematics` (l. 104) |
| "¿El LSPB?" | `irb120/lspb.py`: `sample` (l. 50, las 3 fórmulas) y `plan_lspb` (l. 143, bisección) |
| "¿El Jacobiano?" | `irb120/jacobian.py`: `geometric_jacobian` (l. 35, z × (p − o)), `rank_analysis` (l. 170, SVD) |
| "¿El 1R?" | `irb120/dynamics_1r.py`: `shoulder_model` (l. 70) y `torque_components` (l. 55) |

**Comprobación en vivo (30 s):**

```bash
cd hito2 && source .venv/bin/activate
python analizar_pose.py 0.40 0.10 0.35 0 180 0   # tabla de 8 ramas + rama elegida
python -m pytest -q tests                        # 56 pruebas
```

---

## 3. G1: el pipeline en una frase (memorizar)

> "Partimos de la **pose inicial** (posición de calibración, q = 0) y de la **pose objetivo** $T_d$. **Pieper**
> separa posición y orientación con el centro de muñeca y da **8 ramas**. Cada rama se **verifica con la FK**. De las
> admisibles **elegimos una** con un criterio, $q_f$. El **LSPB** une $q_0$ y $q_f$ y da $q(t), \dot q(t),
> \ddot q(t)$. Con eso, el **Jacobiano** da la velocidad del TCP $\dot x = J\dot q$ y, en un experimento aparte,
> estudiamos la **singularidad** por pérdida de rango. Con $q_2(t)$ y $\ddot q_2(t)$ del mismo LSPB, el modelo
> **1R** da el torque del hombro $\tau(t)$."

| Etapa | Entra | Sale | Función |
|---|---|---|---|
| A Pieper | $T_d$ | 8 candidatos | `analyze_pose` |
| B FK | candidato | $e_p$, $e_R$, ¿acepta? | `fk_check` |
| Selección | admisibles + $q_0$ | $q_f$ | `rank_candidates` / `select_solution` |
| C LSPB | $q_0$, $q_f$, $v_{\max}$, $a_{\max}$ | $q(t), \dot q(t), \ddot q(t)$ | `plan_lspb` |
| D Jacobiano | $q(t), \dot q(t)$ | $\dot x(t)$, rango | `geometric_jacobian`, `rank_analysis` |
| E Dinámica | $q_2(t), \ddot q_2(t)$ | $\tau_{in}, \tau_g, \tau$ | `shoulder_model`, `torque_components` |

---

## 4. G2: las 4 ecuaciones para la pizarra

Cada integrante debe poder hacer **al menos dos** sin mirar.

**(1) Pieper, codo (ley de cosenos)**, de [02 §3](02_A_pieper.md):

$$
p_W = p_{TCP} - (0.150 + d_6)\,z_6,\quad D^2 = r^2 + h^2,\quad
-\sin(q_3 - \delta) = \frac{D^2 - L_2^2 - L_3^2}{2L_2L_3} = c
$$

con $L_3 = \sqrt{d_4^2 + a_3^2} = 0.310$ m y $\delta = \operatorname{atan2}(a_3, d_4) = 13.05°$. Si $|c| > 1$, la
rama no existe. Si $|c| \le 1$, hay 2 codos.

**(2) LSPB**, de [04 §2](04_C_lspb.md):

$$
V = \frac{q_f - q_0}{t_f - t_b},\quad a = \frac{V}{t_b},\quad
q(t) = q_0 + \tfrac12 a t^2\ (t < t_b)
$$

Por qué $t_f - t_b$: en las dos mezclas se avanza a media velocidad, así que el área del trapecio es $V(t_f - t_b)$.

**(3) Columna del Jacobiano**, de [05 §2](05_D_jacobiano.md):

$$
J_i = \begin{bmatrix} z_{i-1}\times(p - o_{i-1})\\ z_{i-1}\end{bmatrix}
$$

Ejemplo a mano en $q = 0$: $J_1 = (0, 0.524, 0 \mid 0, 0, 1)$.

**(4) Dinámica 1R (Euler-Lagrange)**, de [07 §1](07_E_dinamica_1R.md):

$$
T = \tfrac12 J\dot\theta^2,\quad V = mg\ell_c(1 - \cos\theta)\ \Rightarrow\
\tau = J\ddot\theta + mg\ell_c\sin\theta,\quad J = I_c + m\ell_c^2
$$

---

## 5. Si el docente da una pose nueva (3 minutos)

1. En el notebook, §1.3, cambiar `POSE_OBJETIVO = (x, y, z, roll, pitch, yaw)` (m y grados).
2. *Kernel → Restart & Run All* (≈ 20–30 s).
3. Leer, en este orden:
   - el veredicto de §2 (¿alcanzable? si no, por qué: alcance o límites);
   - la tabla de decisión de §4 (rama elegida y por qué);
   - $t_f$ y la junta crítica en §5;
   - el pico de torque y la fase en §8.
4. Si la pose **no es alcanzable**, el notebook se detiene con el motivo. **Eso también es una respuesta correcta:**
   explicar si falla por alcance ($D > 0.580$ m) o por límites articulares.
5. Comprobación rápida desde la terminal: `python analizar_pose.py x y z roll pitch yaw`.

---

## 6. Preguntas probables y respuestas modelo

### A. Pieper

**¿Por qué 8 soluciones?** Brazo frente/atrás (2) × codo arriba/abajo (2) × muñeca $q_5 > 0$ / $q_5 < 0$ (2).
Desacoplar con el centro de muñeca es posible porque los ejes 4, 5 y 6 se cortan en un punto ($a_4 = a_5 = d_5 = 0$).

**¿Por qué 8 reales pero 1 admisible?** La matemática no conoce los topes mecánicos. En el ejemplo, las ramas
"atrás" necesitan $q_1 = -165.96°$, cuando el límite es ±165°; las de codo abajo necesitan $q_3 = -138.2°$, cuando el
límite es −110°; y la muñeca volteada necesita $q_4 = 180°$, cuando el límite es ±160°.

**¿Por qué `atan2` y no `atan`?** `atan` solo devuelve $(-90°, 90°)$ y pierde el cuadrante. `atan2(y, x)` usa los
dos signos y devuelve el ángulo correcto en $(-180°, 180°]$.

**¿Qué pasa en $q_5 = 0$?** Los ejes 4 y 6 quedan alineados y solo se determina $q_4 + q_6$: hay infinitas
soluciones. El código fija $q_4$ igual al de referencia y marca `singular_wrist`.

**¿Qué criterio usaron para elegir?** Admisible → $\sigma_{\min} \ge 0.01$ (amplificación ≤ 100×) → margen ≥ 5° a los
topes → menor $\lVert W(q - q_0)\rVert$, con más peso para las juntas 1 a 3, que mueven unos 12 kg. No usamos el $t_f$
mínimo porque lo fija una sola junta y depende del supuesto de $a_{\max}$.

### B. Validación

**¿Cómo sabes que la IK es correcta?** Cada rama real se reinyecta en la FK y se compara **posición y orientación**,
con tolerancia $10^{-6}$. Los errores son de $10^{-16}$. Además, la prueba de ida y vuelta con 1000 configuraciones
aleatorias siempre recupera el $q$ original.

**¿Y si la FK misma estuviera mal?** La comparamos con el **modelo oficial de ROS-Industrial** del IRB 120
(`abb_irb120_support`), que está hecho con traslaciones y ejes de los planos de ABB, **sin** nuestra tabla DH.
Coinciden en posición y orientación hasta $10^{-15}$, así que la tabla DH es correcta. La comparación con el URDF del
Hito 1 solo prueba el **código**, porque ese URDF se derivó de la misma tabla DH: no hay que venderla como
independiente.

**¿Por qué no basta comparar la posición?** Porque girar $q_6$ cambia la orientación sin mover el TCP. Lo
demostramos con un candidato que tiene error solo en $q_6$: $e_p = 0$, pero se rechaza por $e_R = 0.01$ rad.

**¿Por qué $10^{-6}$?** Es 10 veces menor que la repetibilidad del robot (0.01 mm) y está muy por encima del redondeo
($10^{-16}$). Un error de deducción daría errores de $10^{-2}$.

### C. LSPB

**¿Por qué posición y velocidad son continuas, pero la aceleración salta?** En los empalmes la velocidad vale $V$ a
ambos lados, pero la aceleración pasa de $a$ a 0 (y de 0 a $-a$). El LSPB es $C^1$, no $C^2$. Por eso el torque
inercial tiene escalones.

**¿De dónde salen $v_{\max}$ y $a_{\max}$?** $v_{\max}$ es el datasheet ABB por eje al 25 %. ABB no publica
$a_{\max}$, así que es un **supuesto declarado**: alcanzar $v_{\max}$ en 0.25 s.

**¿Cómo se sincronizan las juntas?** Todas comparten $t_f$ y $t_b$; cada una tiene su propio $V_i$ y $a_i$. La junta
crítica (la 5 en el ejemplo) llega a su límite y fija $t_f = 1.288$ s.

**¿Y si el movimiento es muy corto?** El perfil sale triangular ($t_b = t_f/2$, sin crucero). El notebook lo detecta.

### D. Jacobiano y singularidad

**¿Qué significa una columna de J?** Es la velocidad del TCP cuando solo esa junta gira a 1 rad/s. $\lVert
J_{v,i}\rVert$ es la distancia del TCP al eje $i$: las juntas 1 a 3 posicionan y las 4 a 6 orientan.

**¿Cómo validaron J?** Con diferencias finitas de la FK (error $10^{-10}$), con columnas calculadas a mano en $q = 0$ y
comparando $J_v\dot q$ con $dp/dt$ a lo largo del LSPB.

**¿Cómo saben que hay singularidad?** Por el **rango** de $J$ calculado con SVD: el número de $\sigma_i > 10^{-6}$
baja de 6 a 5 en $q_5 = 0$. El determinante es solo un complemento: $|\det J| = \prod \sigma_i$, que no dice cuántas
direcciones se pierden ni cuáles.

**¿Qué significa físicamente $\dot q_4 = -\dot q_6$ en $q_5 = 0$?** Los ejes 4 y 6 están alineados: si giran en
sentidos opuestos, sus efectos se cancelan y el TCP no se mueve. Ese es el movimiento interno (espacio nulo). A la vez
se pierde la rotación alrededor de $z_3 \times z_4$.

**¿La singularidad implica torque infinito?** **No.** Lo que diverge es la velocidad articular necesaria para moverse
en la dirección perdida: $\lVert\dot q\rVert = 1/\sigma_6 \propto 1/\sin q_5$, y con $q_5 = 0.01°$ resulta
$\rho \approx 4842$ veces el máximo de los ejes 4 y 6. En estática, $\tau = J^TF$ y $J^Tu_6 = \sigma_6 v_6 \to 0$: una
carga en esa dirección **no** necesita torque. El torque solo crece si se obliga al robot a seguir una trayectoria
cartesiana a través de la singularidad.

**¿El LSPB tiene problemas por partir de $q = 0$, que es singular?** No. El LSPB es articular y no invierte $J$.

### E. Dinámica 1R

**¿Por qué aparece torque en crucero si la aceleración es cero?** Por la gravedad: $\tau_g = mg\ell_c\sin\theta$
depende de la posición. En el ejemplo, $|\tau|$ va de 9.7 a 17.6 N·m durante el crucero.

**¿Por qué no aparece $\dot q$ en la ecuación?** Porque en este 1R la inercia $J$ es constante. Si dependiera de $q$,
aparecería $\tfrac12 M'(q)\dot q^2$.

**¿De dónde salen $m$, $\ell_c$ y $J$?** Se calculan con el CAD por eslabón de Truc y Lam (2020) más la pinza SMC
(0.115 kg), aplicando Steiner. No se inventó ningún valor. Resultado: $m = 12.21$ kg, $\ell_c = 0.249$ m y
$J = 1.205$ kg·m².

**¿Qué se congela y qué no demuestra el 4.5 %?** Se congelan las juntas 3 a 6 en la postura media. El 4.5 % es la
diferencia con el modelo completo **con los mismos datos CAD**: mide cuánto se pierde al reducir el modelo, **no**
cuánto se parece al robot real, porque no medimos torques reales.

**¿Dónde está el pico y por qué?** Al final del frenado: $\tau_{in} = -1.84$ y $\tau_g = -18.71$ tienen el mismo
signo y se suman, dando −20.55 N·m. Una vez detenido queda solo el sostén, −18.71 N·m. Al arrancar se oponen y
dan −6.48 N·m.

**¿Qué pasa si se mueve más rápido?** $\tau_{in}$ crece con el cuadrado de la velocidad (al 100 %: 29.4 N·m, más que
la gravedad); $\tau_g$ no cambia.

---

## 7. Frases que NO hay que decir (trampas de la rúbrica)

| ❌ No decir | ✅ Decir |
|---|---|
| "En la singularidad el torque es infinito" | "Se amplifica la velocidad articular; el torque estático en la dirección perdida tiende a 0" |
| "Es singular porque det J = 0" (y nada más) | "El rango por SVD baja de 6 a 5; el det es un complemento" |
| "Velocidad constante ⇒ torque cero" | "En crucero queda el torque gravitacional" |
| "Las 8 soluciones son válidas" | "8 reales; admisibles solo las que respetan límites y pasan la FK" |
| "Usamos un solver" | "Pieper analítico: `atan2`, `asin` y ley de cosenos" |
| "El URDF del Hito 1 es una verificación independiente" | "La independiente es la del modelo oficial de ROS-Industrial; el URDF del Hito 1 solo verifica el código" |
| "Lo hizo la IA" / "eso lo hizo mi compañero" | Explicar la ecuación o la validación con tus palabras |
| "El 1R está validado con el robot real" | "Está contrastado con el modelo completo con los mismos datos CAD" |

---

## 8. Números clave (pose de ejemplo: TCP (0.40, 0.10, 0.35) m, herramienta hacia abajo)

| Dato | Valor |
|---|---|
| Pose inicial | q = 0 → TCP (0.524, 0, 0.630) m; es una singularidad ($q_5 = 0$) |
| Centro de muñeca / alcance | $p_W$ = (0.40, 0.10, 0.572), $D$ = 0.4995 m ∈ [0.040, 0.580] |
| Ramas | 8 reales, 1 admisible: **rama 1** frente/arriba/q5+ |
| $q_f$ | (14.04, 22.67, −15.70, 0, 83.03, 14.04)° |
| Selección | $\sigma_{\min}$ = 0.117, margen 37° |
| Errores FK | ~$10^{-16}$; DH frente al modelo oficial ROS-I ~$10^{-15}$; ida y vuelta 1000/1000 |
| LSPB | $t_f$ = 1.288 s, $t_b$ = 0.25 s, junta crítica J5 |
| Singularidad | rango 6 → 5; $\sigma_6 \approx 0.150\sin q_5$; $\dot q_4 = -\dot q_6$; $\rho \approx 4842$ con $q_5 = 0.01°$ |
| 1R | $m$ = 12.21 kg, $\ell_c$ = 0.249 m, $J$ = 1.205 kg·m², $mg\ell_c$ = 29.8 N·m |
| Torque | inicio −6.48 · crucero (mitad) −13.78 · $t_f^-$ **−20.55** · sostén −18.71 N·m; 1R frente a completo: 4.5 % RMS |
| Verificaciones | notebook 34/34 · pruebas 56/56 |
