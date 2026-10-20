# 08. Ejemplo resuelto a mano: de $T_d$ a $\tau(t)$

Este archivo recorre **todo el pipeline con números**, con calculadora, para una pose concreta. Cada resultado se
contrastó con el código (`python analizar_pose.py 0.40 0.10 0.35 0 180 0`). Sirve como guía para que cualquier
integrante pueda **reconstruir una ecuación** en la defensa (criterio G2).

Constantes: $d_1 = 0.290$, $L_2 = a_2 = 0.270$, $a_3 = 0.070$, $d_4 = 0.302$, $d_6 = 0.072$ y TCP $= 0.150$ m.

$$
L_3 = \sqrt{0.302^2 + 0.070^2} = \sqrt{0.096104} = 0.31001\ \text{m},\qquad
\delta = \operatorname{atan2}(0.070, 0.302) = 13.050°
$$

---

## 1. La pose pedida

TCP en $p = (0.40,\ 0.10,\ 0.35)$ m, con la herramienta apuntando hacia abajo: roll $= 0$, pitch $= 180°$, yaw $= 0$.

$$
R_d = R_y(180°) = \begin{bmatrix}-1&0&0\\0&1&0\\0&0&-1\end{bmatrix}, \qquad
T_d = \begin{bmatrix}-1&0&0&0.40\\0&1&0&0.10\\0&0&-1&0.35\\0&0&0&1\end{bmatrix}
$$

El eje de la herramienta es la tercera columna: $z_6 = (0, 0, -1)$.

## 2. Paso 0: centro de muñeca

$$
p_{tool0} = p - 0.150\,z_6 = (0.40,\ 0.10,\ 0.35 + 0.150) = (0.40,\ 0.10,\ 0.500)
$$
$$
p_W = p_{tool0} - 0.072\,z_6 = (0.40,\ 0.10,\ 0.572)\ \text{m}
$$

## 3. Paso 1: brazo ($q_1, q_2, q_3$)

### $q_1$

$$
q_1^{\text{frente}} = \operatorname{atan2}(0.10,\ 0.40) = 14.036°, \qquad
q_1^{\text{atrás}} = 14.036° - 180° = -165.964°
$$

### Plano del brazo

$$
r = \sqrt{0.40^2 + 0.10^2} = 0.41231\ \text{m}, \qquad h = 0.572 - 0.290 = 0.282\ \text{m}
$$
$$
D^2 = 0.17 + 0.079524 = 0.249524 \;\Rightarrow\; D = 0.49952\ \text{m} \in [0.040,\ 0.580]\ \checkmark\ \text{(alcanzable geométricamente)}
$$

### $q_3$: ley de cosenos

$$
c = \frac{D^2 - L_2^2 - L_3^2}{2L_2L_3} = \frac{0.249524 - 0.072900 - 0.096104}{2(0.270)(0.31001)} = \frac{0.080520}{0.167403} = 0.48099
$$

$|c| \le 1$, así que las ramas son **reales**. Además $\arcsin(-0.48099) = -28.750°$.

$$
q_3^{\text{arriba}} = 13.050° - 28.750° = \mathbf{-15.700°}, \qquad
q_3^{\text{abajo}} = 13.050° + 180° + 28.750° = 221.800° \equiv \mathbf{-138.200°}
$$

### $q_2$

$\alpha = \operatorname{atan2}(r, h) = \operatorname{atan2}(0.41231, 0.282) = 55.628°$, con $\eta = 90° + q_3 - \delta$.

**Frente, codo arriba:** $\eta = 90 - 15.700 - 13.050 = 61.250°$

$$
\operatorname{atan2}(L_3\sin\eta,\ L_2 + L_3\cos\eta) = \operatorname{atan2}(0.27178,\ 0.27 + 0.14911) = \operatorname{atan2}(0.27178,\ 0.41911) = 32.961°
$$
$$
q_2 = 55.628° - 32.961° = \mathbf{22.667°}
$$

**Frente, codo abajo:** $\eta = -61.250°$, el atan2 da $-32.961°$, así que $q_2 = 55.628 + 32.961 = \mathbf{88.589°}$.

**Atrás:** como $r$ pasa a ser $-0.41231$, $\alpha = -55.628°$. Codo arriba: $q_2 = -55.628 - 32.961 = \mathbf{-88.589°}$.
Codo abajo: $q_2 = -55.628 + 32.961 = \mathbf{-22.667°}$.

### Comprobación del brazo (FK plana) para frente-arriba

Con $\varphi = q_2 + q_3 - \delta = 22.667 - 15.700 - 13.050 = -6.083°$:

$$
r = 0.270\sin 22.667° + 0.31001\cos(-6.083°) = 0.10406 + 0.30826 = 0.41232\ \checkmark
$$
$$
h = 0.270\cos 22.667° - 0.31001\sin(-6.083°) = 0.24915 + 0.03285 = 0.28200\ \checkmark
$$

## 4. Paso 2: muñeca ($q_4, q_5, q_6$), rama frente-arriba

### $R_0^3$

Multiplicando las tres primeras matrices DH, con $\sigma = q_2 + q_3$:

$$
R_0^3 = \begin{bmatrix}
\sin\sigma\cos q_1 & \sin q_1 & \cos q_1\cos\sigma\\
\sin q_1\sin\sigma & -\cos q_1 & \sin q_1\cos\sigma\\
\cos\sigma & 0 & -\sin\sigma
\end{bmatrix}
$$

Con $\sigma = 22.667 - 15.700 = 6.967°$ ($\sin\sigma = 0.12129$, $\cos\sigma = 0.99262$) y $q_1 = 14.036°$
($\cos = 0.97014$, $\sin = 0.24254$):

$$
R_0^3 = \begin{bmatrix} 0.11767 & 0.24254 & 0.96298\\ 0.02942 & -0.97014 & 0.24075\\ 0.99262 & 0 & -0.12129\end{bmatrix}
$$

### $R_3^6 = (R_0^3)^T R_d$

Multiplicar por $R_d = \operatorname{diag}(-1, 1, -1)$ por la derecha solo cambia el signo de las columnas 1 y 3:

$$
R_3^6 = \begin{bmatrix} -0.11767 & 0.02942 & -0.99262\\ -0.24254 & -0.97014 & 0\\ -0.96298 & 0.24075 & 0.12129\end{bmatrix}
$$

### Euler ZYZ: $R_3^6 = R_z(q_4)R_y(-q_5)R_z(q_6 + \pi)$

$R_{13} = -0.99262$, $R_{23} = 0$, $R_{33} = 0.12129$, $R_{31} = -0.96298$, $R_{32} = 0.24075$, así que
$|s_b| = \sqrt{R_{13}^2 + R_{23}^2} = 0.99262$.

Como $b = -q_5$, el signo de $s_b$ es el **opuesto** al de $q_5$. Las ramas se nombran por el signo de $q_5$:

| | Rama `q5+` ($s_b = -0.99262$) | Rama `q5-` ($s_b = +0.99262$) |
|---|---|---|
| $b = \operatorname{atan2}(s_b, R_{33})$ | $-83.034°$, así $q_5 = +83.034°$ | $83.034°$, así $q_5 = -83.034°$ |
| $q_4 = \operatorname{atan2}(R_{23}/s_b,\ R_{13}/s_b)$ | $\operatorname{atan2}(0, +1) = 0°$ | $\operatorname{atan2}(0, -1) = 180°$ |
| $q_6 + \pi = \operatorname{atan2}(R_{32}/s_b,\ -R_{31}/s_b)$ | $\operatorname{atan2}(-0.24075, -0.96298) = -165.964°$, así $q_6 = -345.964° \equiv 14.036°$ | $\operatorname{atan2}(0.24075, 0.96298) = 14.036°$, así $q_6 = -165.964°$ |
| ¿En límites? | **Sí** | **No**: $q_4 = 180° > 160°$ |

Las dos ramas son la misma orientación, con la muñeca "volteada": $(q_4 + 180°, -q_5, q_6 + 180°)$.

## 5. Las 8 ramas (tabla completa, la que imprime el código)

| Rama | Brazo | Codo | Muñeca | $q$ [°] | ¿Real? | Límites | $e_p$ [m] | $e_R$ [rad] | ¿Admisible? |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **frente** | **arriba** | **q5+** | **(14.04, 22.67, −15.70, 0.00, 83.03, 14.04)** | sí | **sí** | 8e-17 | 2e-16 | **SÍ** |
| 2 | frente | arriba | q5− | (14.04, 22.67, −15.70, 180.00, −83.03, −165.96) | sí | no: J4 | 6e-17 | 2e-16 | no |
| 3 | frente | abajo | q5+ | (14.04, 88.59, −138.20, 0.00, 139.61, 14.04) | sí | no: J3, J5 | 1e-16 | 3e-16 | no |
| 4 | frente | abajo | q5− | (14.04, 88.59, −138.20, 180.00, −139.61, −165.96) | sí | no: J3, J4, J5 | 1e-16 | 3e-16 | no |
| 5 | atrás | arriba | q5+ | (−165.96, −88.59, −15.70, 180.00, 165.71, 14.04) | sí | no: J1, J4, J5 | 1e-16 | 2e-16 | no |
| 6 | atrás | arriba | q5− | (−165.96, −88.59, −15.70, 0.00, −165.71, −165.96) | sí | no: J1, J5 | 8e-17 | 2e-16 | no |
| 7 | atrás | abajo | q5+ | (−165.96, −22.67, −138.20, −180.00, 109.13, 14.04) | sí | no: J1, J3, J4 | 2e-16 | 3e-16 | no |
| 8 | atrás | abajo | q5− | (−165.96, −22.67, −138.20, 0.00, −109.13, −165.96) | sí | no: J1, J3 | 1e-16 | 1e-16 | no |

**Lectura:**

- Las 8 ramas son **reales** y **todas** reproducen $T_d$ por FK con errores de $10^{-16}$: la matemática es correcta.
- Solo **una** es admisible. Las de "atrás" fallan por **menos de 1°** en la junta 1 ($|-165.96| > 165$); las de codo
  abajo fallan porque $q_3 = -138.2° < -110°$.
- **Veredicto: ALCANZABLE, 1 de 8 ramas admisibles.** Se selecciona la rama 1 con el criterio de
  [02 §6](02_A_pieper.md): es admisible, está lejos de singularidades ($\sigma_{\min}(J) = 0.117 \ge 0.01$), tiene
  37° de margen al límite más cercano ($q_5 = 83°$ frente a 120°) y es la de menor desplazamiento (en este caso, la
  única que queda).

## 6. Validación por FK (criterio B)

Se reinyecta $q^{(1)} = (14.036, 22.667, -15.700, 0, 83.034, 14.036)°$ en la FK:

$$
T(q^{(1)}) = \begin{bmatrix}-1&0&0&0.400\\0&1&0&0.100\\0&0&-1&0.350\\0&0&0&1\end{bmatrix}
\quad\Rightarrow\quad e_p = 7.9\times10^{-17}\ \text{m},\ e_R = 2.0\times10^{-16}\ \text{rad} < 10^{-6}\ \checkmark
$$

Detalle curioso: $q_4 = 0$ y $q_1 = q_6$. Con la herramienta vertical, la muñeca solo tiene que "deshacer" el giro de
la base para que $x_6$ quede alineado con $-x_0$.

## 7. LSPB desde la posición de calibración $q_0 = 0$ (criterio C)

$D = q_f - q_0 = (14.036, 22.667, -15.700, 0, 83.034, 14.036)° = (0.24498, 0.39561, -0.27402, 0, 1.44921, 0.24498)$ rad.

Límites con `default_limits()`, es decir, 25 % del datasheet y rampa de 0.25 s:

- $v_{\max} = (1.0908, 1.0908, 1.0908, 1.3963, 1.3963, 1.8326)$ rad/s
- $a_{\max} = v_{\max}/0.25 = (4.3633, 4.3633, 4.3633, 5.5851, 5.5851, 7.3304)$ rad/s²

Peor junta:

- $D_i/v_{\max,i}$ es máximo en J5: $1.44921/1.39626 = 1.03793$ s.
- $D_i/a_{\max,i}$ es máximo también en J5: $0.25948$ s².

Como **la misma junta satura los dos límites**, se aplica el caso cerrado:

$$
t_b = \frac{v_{\max,5}}{a_{\max,5}} = 0.25\ \text{s}, \qquad t_f = \frac{D_5}{v_{\max,5}} + t_b = 1.03793 + 0.25 = \mathbf{1.2879\ s}
$$

El código lo obtiene por bisección y da 1.28792 s. Para la junta 2 (hombro):

$$
V_2 = \frac{0.39561}{1.2879 - 0.25} = 0.38116\ \text{rad/s} \le 1.0908\ \checkmark, \qquad
a_2 = \frac{V_2}{t_b} = 1.52462\ \text{rad/s}^2 \le 4.3633\ \checkmark
$$

Puntos de control:

- $q_2(t_b) = \tfrac12(1.52462)(0.25)^2 = 0.047644$ rad $= 2.730°$
- $q_2(t_f/2) = 0.38116\,(0.64396 - 0.125) = 0.19780$ rad $= 11.333°$, justo la mitad de 22.667°
- $q_2(t_f) = 22.667°$, con $\dot q_2(t_f) = 0$

## 8. Torque 1R del hombro (criterio E)

Parámetros con $q_{\text{ref}} = (q_0 + q_f)/2$ (ver [07](07_E_dinamica_1R.md)): $J = 1.2053$ kg·m²,
$mg\ell_c = 12.21 \times 9.81 \times 0.24906 = 29.832$ N·m y $\varphi_0 = -163.815°$.

| Instante | Fase | $q_2$ [°] | $\theta$ [°] | $\tau_{in} = J\ddot q_2$ | $\tau_g = mg\ell_c\sin\theta$ | $\tau$ [N·m] |
|---|---|---|---|---|---|---|
| $0^+$ | arranque | 0.000 | −163.815 | $1.2053 \times 1.52462 = +1.838$ | $29.832\times(-0.27874) = -8.316$ | **−6.478** |
| $t_f/2$ | crucero | 11.333 | −152.481 | 0 | $29.832\times(-0.46204) = -13.784$ | **−13.784** |
| $t_f^-$ | frenado | 22.667 | −141.148 | $1.2053 \times (-1.52462) = -1.838$ | $29.832\times(-0.62731) = -18.714$ | **−20.552** |

**Interpretación:**

- $\theta \approx -164°$ significa que el centro de masa está casi encima del hombro. Al inclinar el brazo hacia
  adelante ($q_2$ crece), $\theta$ se aleja de la vertical, $|\sin\theta|$ crece y **el esfuerzo gravitacional
  aumenta**: de 8.3 a 18.7 N·m.
- En el **arranque**, la inercia (+1.84) se opone a la gravedad (−8.32): el torque neto es **menor** que el estático.
- En el **crucero**, $\ddot q = 0$ pero $\tau = -13.8$ N·m: **velocidad constante no es torque cero**.
- En el **frenado**, la inercia (−1.84) **se suma** a la gravedad: aquí está el **pico** de $|\tau| = 20.6$ N·m.
- La parte inercial es pequeña (unos 1.8 N·m) frente a la gravitacional, porque el movimiento al 25 % es lento.
  Domina la gravedad.

## 9. Jacobiano en la configuración final (criterio D, rápido)

En $q_f$, $q_5 = 83°$, así que $\sin q_5 \approx 0.99$ y la muñeca está lejos de su singularidad. Además
$q_3 - \delta = -28.75°$ (lejos de $-90°$, el codo no está estirado) y $r_W = 0.412$ m $\ne 0$ (W fuera del eje 1).
Por lo tanto $\operatorname{rank} J(q_f) = 6$.

En cambio $q_0 = 0$ **es singular** ($q_5 = 0$, rango 5). El LSPB articular parte de ahí sin problema, porque no
invierte $J$. Es otra muestra de que singularidad ≠ torque infinito.
