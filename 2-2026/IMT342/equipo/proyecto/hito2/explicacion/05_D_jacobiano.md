# 05. Criterio D (primera parte): Jacobiano geométrico $\dot x = J(q)\,\dot q$

> Código: [`irb120/jacobian.py`](../irb120/jacobian.py) · Pruebas: [`tests/test_jacobian.py`](../tests/test_jacobian.py)

**Lo que pide la rúbrica para "Excelente":** Jacobiano implementado de forma consistente, con **al menos una
validación**, e **interpretación de sus columnas**. La singularidad está en [06](06_D_singularidades.md).

## 1. Qué relaciona

$$
\dot x = \begin{bmatrix} v \\ \omega \end{bmatrix} = J(q)\,\dot q, \qquad J \in \mathbb{R}^{6\times 6}
$$

- $v$ es la velocidad lineal del **TCP** [m/s] y $\omega$ la velocidad angular de la herramienta [rad/s], las dos
  expresadas en `base_link`.
- Es un mapeo **lineal y local**: $J$ cambia con $q$, pero en cada instante transforma velocidades articulares en
  velocidades cartesianas.

## 2. Construcción columna a columna (junta de revolución)

Si solo se mueve la junta $i$ con velocidad $\dot q_i$, el robot gira como un sólido rígido alrededor del eje
$z_{i-1}$, que pasa por $o_{i-1}$. La velocidad de un punto $p$ de ese sólido es $\omega \times r$, así que:

$$
J_i = \begin{bmatrix} J_{v,i} \\ J_{\omega,i}\end{bmatrix} = \begin{bmatrix} z_{i-1}\times(p_{TCP} - o_{i-1}) \\ z_{i-1}\end{bmatrix}
$$

y por superposición, al ser lineal, $\dot x = \sum_i J_i\,\dot q_i$.

Paso a paso en el código ([jacobian.py:35](../irb120/jacobian.py#L35)):

1. `joint_frames(q)` ([jacobian.py:27](../irb120/jacobian.py#L27)) acumula $T_0^0 = I, T_0^1, \dots, T_0^6$.
2. Para la junta $i$, `axis = frames[i-1][:3, 2]` es $z_{i-1}$ (tercera columna de la rotación) y
   `origin = frames[i-1][:3, 3]` es $o_{i-1}$.
3. $p_{TCP}$ es la brida desplazada 0.150 m por $z_6$.
4. Columna = `[np.cross(axis, p - origin), axis]`.

`reference="wrist"` usa $p = p_W$ en lugar del TCP. Sirve para separar el brazo de la muñeca (ver [06](06_D_singularidades.md)).

## 3. Interpretación de las columnas

- **Columna $i$ = "qué le hace la junta $i$ al TCP"** cuando gira a 1 rad/s y las demás están quietas.
  - $J_{v,i}$ es tangente a la circunferencia que describe el TCP alrededor del eje $i$. Su módulo es
    (distancia del TCP al eje) × 1 rad/s: **cuanto más lejos del eje, más velocidad lineal**.
  - $J_{\omega,i} = z_{i-1}$: la herramienta gira alrededor del eje de la junta.
- Las juntas 4, 5 y 6 tienen sus ejes cerca del TCP, así que **mueven poco** la posición y sobre todo orientan. Las
  juntas 1, 2 y 3 tienen brazos de palanca grandes: **posicionan**.

### Validación a mano en $q = 0$

Marcos en $q = 0$ (salen de la FK). El TCP está en $p = (0.374 + 0.150,\ 0,\ 0.630) = (0.524, 0, 0.630)$:

| $i$ | $z_{i-1}$ | $o_{i-1}$ | $p - o_{i-1}$ | $J_{v,i} = z\times(p-o)$ |
|---|---|---|---|---|
| 1 | (0,0,1) | (0,0,0) | (0.524, 0, 0.630) | **(0, 0.524, 0)** |
| 2 | (0,1,0) | (0,0,0.290) | (0.524, 0, 0.340) | **(0.340, 0, −0.524)** |
| 3 | (0,1,0) | (0,0,0.560) | (0.524, 0, 0.070) | **(0.070, 0, −0.524)** |
| 4 | (1,0,0) | (0,0,0.630) | (0.524, 0, 0) | **(0, 0, 0)** |
| 5 | (0,1,0) | (0.302,0,0.630) | (0.222, 0, 0) | **(0, 0, −0.222)** |
| 6 | (1,0,0) | (0.302,0,0.630) | (0.222, 0, 0) | **(0, 0, 0)** |

Ejemplo de la columna 2: $(0,1,0)\times(0.524, 0, 0.340) = (1\cdot0.340 - 0\cdot0,\ 0\cdot0.524 - 0\cdot0.340,\ 0\cdot0 - 1\cdot0.524) = (0.340, 0, -0.524)$.

Lectura física:

- Columna 1: girar la base mueve el TCP en $+y$ a 0.524 m/s, porque el radio es 0.524 m.
- Columna 2: inclinar el hombro hacia adelante lleva el TCP hacia adelante ($+x$) y hacia abajo ($-z$).
- Columnas 4 y 6: el TCP está **sobre** sus ejes, así que no se mueve; solo gira.
- Las columnas 4 y 6 son **idénticas** en $q = 0$: $[0;\,(1,0,0)]$. **La postura cero del IRB 120 es una
  singularidad de muñeca** ($q_5 = 0$, ver [06](06_D_singularidades.md)).

Esta columna está fijada en la prueba `test_hand_column_at_zero_pose`.

## 4. Validaciones numéricas

1. **Diferencias finitas de la FK** (`numerical_jacobian`, [jacobian.py:116](../irb120/jacobian.py#L116)). Es un
   cálculo totalmente independiente de la fórmula $z \times (p - o)$:

   $$
   J_{v,i} \approx \frac{p(q + h e_i) - p(q - h e_i)}{2h}, \qquad
   [\omega_i]_\times \approx \frac{R(q + h e_i) - R(q - h e_i)}{2h}\,R(q)^T
   $$

   La segunda fórmula usa que $\dot R R^T = [\omega]_\times$ es antisimétrica; `_vee` extrae $\omega$ de ella. En
   30 configuraciones aleatorias, $\lVert J - J_{\text{num}}\rVert_\infty < 10^{-8}$ (el error de truncamiento es
   del orden de $h^2$). Prueba: `test_matches_finite_differences_of_fk`.
2. **Predicción de desplazamiento:** $\Delta p \approx J_v\,\dot q\,\Delta t$ con $\Delta t = 10^{-6}$ s. Prueba:
   `test_twist_predicts_tcp_displacement`.
3. **Columna a mano** en $q = 0$ (tabla anterior).

## 5. Uso en el pipeline

`tcp_twist(q, q_dot)` ([jacobian.py:136](../irb120/jacobian.py#L136)) evalúa $\dot x(t) = J(q(t))\,\dot q(t)$ sobre
la trayectoria LSPB. En el notebook se grafica $\lVert v(t)\rVert$ y se contrasta con la derivada numérica de
$p(q(t))$ (otra validación). Además se sigue $\sigma_{\min}(J(q(t)))$ para mostrar que la trayectoria elegida no
pasa cerca de una singularidad, o identificar dónde lo hace.

## Preguntas de defensa

1. *¿Qué significa la columna 5?* Es la velocidad del TCP cuando solo gira la junta 5: con 0.222 m de palanca
   (brida + TCP), el TCP se mueve 0.222 m/s por cada rad/s.
2. *¿Por qué $J_\omega$ es simplemente $z$?* Porque cada junta aporta una rotación alrededor de su eje, y las
   velocidades angulares se suman como vectores.
3. *¿Cómo validaste J?* Con diferencias finitas de la FK (independientes de la fórmula), con una columna hecha a mano
   en $q = 0$ y con la predicción de desplazamiento.
4. *¿Por qué $J$ es $6\times6$?* Tiene 6 velocidades articulares (columnas) y 6 componentes del twist $[v;\omega]$
   (filas). El rango máximo es 6.
