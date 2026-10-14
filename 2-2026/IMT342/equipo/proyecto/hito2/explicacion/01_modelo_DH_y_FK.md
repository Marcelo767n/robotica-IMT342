# 01. Modelo Denavit-Hartenberg y cinemática directa del ABB IRB 120

> Código: [`irb120/dh.py`](../irb120/dh.py) · Pruebas: [`tests/test_dh.py`](../tests/test_dh.py)

Todo el pipeline usa una sola función para ir de articulaciones a pose: la cinemática directa (FK). Pieper la invierte,
la validación B la usa para comprobar, el Jacobiano la deriva y la dinámica la usa para ubicar centros de masa.

## 1. La matriz DH clásica

Cada eslabón se describe con cuatro números $(\theta_i, d_i, a_i, \alpha_i)$. La transformada del marco $i-1$ al $i$ es

$$
A_i = R_z(\theta_i)\,T_z(d_i)\,T_x(a_i)\,R_x(\alpha_i) =
\begin{bmatrix}
c\theta & -s\theta\,c\alpha & s\theta\,s\alpha & a\,c\theta\\
s\theta & c\theta\,c\alpha & -c\theta\,s\alpha & a\,s\theta\\
0 & s\alpha & c\alpha & d\\
0&0&0&1
\end{bmatrix}
$$

Paso a paso:

1. $R_z(\theta)$ gira alrededor del eje de la junta, que en DH siempre es $z_{i-1}$.
2. $T_z(d)$ avanza a lo largo de ese eje.
3. $T_x(a)$ avanza a lo largo de la normal común, el nuevo $x_i$.
4. $R_x(\alpha)$ inclina el nuevo eje $z_i$ respecto del anterior.

En el código esto es `dh_transform(theta, parameter)` ([dh.py:61](../irb120/dh.py#L61)), que copia la matriz de arriba
elemento por elemento.

## 2. Tabla DH del IRB 120

Fuente: Bahani et al. (2023), Tabla I. Las cotas coinciden con el datasheet ABB: 290 mm de altura del hombro,
270 mm de brazo, 70 mm de desfase del antebrazo, 302 mm de antebrazo y 72 mm de brida.

| i | $\theta_i$ | $d_i$ [m] | $a_i$ [m] | $\alpha_i$ |
|---|---|---|---|---|
| 1 | $q_1$ | 0.290 | 0 | $-\pi/2$ |
| 2 | $q_2 - \pi/2$ | 0 | 0.270 | 0 |
| 3 | $q_3$ | 0 | 0.070 | $-\pi/2$ |
| 4 | $q_4$ | 0.302 | 0 | $+\pi/2$ |
| 5 | $q_5$ | 0 | 0 | $-\pi/2$ |
| 6 | $q_6 + \pi$ | 0.072 | 0 | 0 |

- Los **offsets** $-\pi/2$ (fila 2) y $+\pi$ (fila 6) existen porque el "cero" que define ABB no coincide con el cero
  geométrico de DH. Con estos offsets, $q = 0$ corresponde a la postura de calibración de ABB: brazo vertical y
  antebrazo horizontal.
- En el código está en `DH_PARAMETERS` ([dh.py:31](../irb120/dh.py#L31)) como una lista de `DHParameter(d, a, alpha,
  offset)`.

**Comprobación en la postura cero:** la brida queda en $x = d_4 + d_6 = 0.374$ m y
$z = d_1 + a_2 + a_3 = 0.290 + 0.270 + 0.070 = 0.630$ m. Coincide con el dibujo del datasheet. Es la prueba
`test_zero_pose_matches_paper_geometry`.

## 3. Cinemática directa

$$
T_0^6(q) = A_1(q_1)\,A_2(q_2)\,A_3(q_3)\,A_4(q_4)\,A_5(q_5)\,A_6(q_6)
$$

El producto es válido porque cada $A_i$ expresa el marco $i$ dentro del $i-1$: al encadenarlas se pasa del marco 6
al 0. Código: `forward_kinematics(q)` ([dh.py:99](../irb120/dh.py#L99)), que hace `transform = transform @ dh_transform(...)`
seis veces.

### TCP a 0.150 m

El TCP está sobre el eje $z_6$, a 0.150 m de la brida:

$$
T_{TCP}(q) = T_0^6(q)\;T_z(0.150), \qquad p_{TCP} = p_6 + 0.150\,z_6
$$

Código: `TCP_Z_M = 0.150`, `tcp_transform()` ([dh.py:108](../irb120/dh.py#L108)) y `forward_kinematics_tcp(q)`
([dh.py:115](../irb120/dh.py#L115)). La orientación del TCP es la misma que la de la brida: solo cambia la posición.

## 4. Límites y velocidades del fabricante

Fuente: ABB, *Product specification IRB 120*. Están en `JOINT_LIMITS_DEG` y `MAX_SPEED_DEG_S`
([dh.py:46](../irb120/dh.py#L46)).

| Eje | Rango [°] | Velocidad máx. [°/s] |
|---|---|---|
| 1 | −165 … +165 | 250 |
| 2 | −110 … +110 | 250 |
| 3 | −110 … +70 | 250 |
| 4 | −160 … +160 | 320 |
| 5 | −120 … +120 | 320 |
| 6 | −400 … +400 | 420 |

## 5. Medidas de error entre dos poses

Se usan en la validación B:

- **Error de posición:** $e_p = \lVert p_1 - p_2 \rVert$ en metros. Código: `position_error_m` ([dh.py:120](../irb120/dh.py#L120)).
- **Error de orientación:** el ángulo de la rotación relativa $R_1^T R_2$, que es la distancia geodésica en SO(3).
  Como $\operatorname{tr}(R) = 1 + 2\cos\phi$ y el vector $\text{vee}(R - R^T) = 2\sin\phi\,\hat{k}$, se calcula

$$
\phi = \operatorname{atan2}\!\Big(\tfrac{1}{2}\lVert \text{vee}(R-R^T)\rVert,\ \tfrac{1}{2}(\operatorname{tr}R - 1)\Big)
$$

  Se usa `atan2` en lugar de `acos` porque `acos` pierde precisión cerca de 0, que es justo donde caen los errores
  pequeños. Código: `rotation_error_rad` ([dh.py:125](../irb120/dh.py#L125)).

## 6. Entrada de la pose deseada

`pose_from_xyz_rpy_deg(x, y, z, roll, pitch, yaw)` ([transforms.py:65](../irb120/transforms.py#L65)) arma

$$
T_d = \begin{bmatrix} R_z(\psi)R_y(\vartheta)R_x(\varphi) & p\\ 0 & 1\end{bmatrix}
$$

Ejemplo: `roll = 0, pitch = 180°, yaw = 0` da $R = \operatorname{diag}(-1, 1, -1)$, es decir, la herramienta apuntando
hacia abajo ($z_6 = (0, 0, -1)$).

## Preguntas de defensa

1. *¿Por qué hay un offset de $-\pi/2$ en la junta 2?* Porque con $\theta_2 = q_2$ el cero de DH dejaría el brazo
   horizontal, y ABB define el cero con el brazo vertical.
2. *¿Cómo sabes que la tabla es correcta?* La pose cero reproduce (0.374, 0, 0.630) m del datasheet, y en el Hito 1
   se comparó contra el URDF con error < 1e-6 m.
3. *¿Qué cambia si el TCP pasa de 0.10 a 0.15 m?* Solo la posición del TCP ($+0.05\,z_6$). La orientación y el centro
   de muñeca, para una misma $q$, no cambian.
