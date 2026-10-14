# 07. Criterio E: dinámica reducida 1R del hombro y torque $\tau(t)$

> Código: [`irb120/dynamics_1r.py`](../irb120/dynamics_1r.py) (con datos de [`irb120/dynamics.py`](../irb120/dynamics.py)) ·
> Pruebas: [`tests/test_dynamics_1r.py`](../tests/test_dynamics_1r.py)

**Lo que pide la rúbrica para "Excelente":** usar el **modelo 1R trabajado en clase**; documentar **supuestos y
parámetros**; calcular el torque a partir de $q, \dot q, \ddot q$ del LSPB; **separar e interpretar las
contribuciones**; presentar $\tau(t)$ y relacionarlo con la trayectoria. Es "Insuficiente" un torque sin modelo
claro, con parámetros sin procedencia o que confunde singularidad con torque.

## 1. El modelo de clase (deducción por Euler-Lagrange)

Péndulo de un grado de libertad. El ángulo $\theta$ se mide **desde la vertical inferior**, así que $\theta = 0$ es
colgando hacia abajo. La masa es $m$, el centro de masa está a $\ell_c$ del eje y la inercia respecto del eje es $J$.

1. **Energía cinética:** $T = \tfrac12 J\dot\theta^2$, con $J = I_c + m\ell_c^2$ por el teorema de Steiner.
2. **Energía potencial**, tomando como referencia el punto más bajo: la altura del centro de masa es
   $-\ell_c\cos\theta$, así que $V = mg\ell_c(1 - \cos\theta)$.
3. **Lagrangiano:** $\mathcal{L} = T - V$.
4. **Euler-Lagrange:**

$$
\frac{d}{dt}\frac{\partial\mathcal L}{\partial\dot\theta} - \frac{\partial\mathcal L}{\partial\theta} = \tau
\;\Rightarrow\; \frac{d}{dt}(J\dot\theta) + mg\ell_c\sin\theta = \tau
$$

$$
\boxed{\tau = \underbrace{J\,\ddot\theta}_{\text{inercial}} + \underbrace{m g \ell_c\sin\theta}_{\text{gravitacional}}}
$$

**¿Por qué no aparece $\dot\theta$?** Porque $J$ no depende de $\theta$: en un solo grado de libertad,
$\partial T/\partial\theta = 0$ y no hay términos de Coriolis ni centrífugos. Esos términos aparecen solo en cadenas
de varios eslabones, donde la inercia que "ve" una junta cambia con la postura de las otras. Tampoco se modela
fricción.

## 2. Cómo se reduce el IRB 120 a un 1R

| Decisión | Justificación |
|---|---|
| El actuador es la **junta 2 (hombro)** | Su eje es horizontal, así que la gravedad actúa de lleno, y carga con casi todo el robot |
| Todo lo que cuelga del hombro (eslabones 2 a 6 + pinza) es **un solo cuerpo rígido** | Hipótesis del modelo 1R: las juntas 3 a 6 se **congelan** en una configuración de referencia $q_{\text{ref}}$ |
| $q_{\text{ref}}$ = punto medio del movimiento, $(q_0 + q_f)/2$ | Representa la postura "promedio" durante el LSPB. En el notebook se muestra la sensibilidad usando $q_0$ o $q_f$ |
| $\theta = q_2 + \varphi_0$ | Con el cuerpo congelado, girar la junta 2 un ángulo $\Delta$ gira el centro de masa el mismo $\Delta$. $\varphi_0$ es el ángulo del centro de masa cuando $q_2 = 0$ |

## 3. Parámetros: de dónde salen (no se inventan)

Fuente: parámetros CAD por eslabón de Truc y Lam (2020) (masa, centro de masa e inercia en cada marco DH), los mismos
de `dynamics.py`, más la pinza SMC MHZ2-16D (0.115 kg, hoja de datos del fabricante) sumada al eslabón 6.

| Eslabón | 2 | 3 | 4 | 5 | 6 + pinza | **Total $m$** |
|---|---|---|---|---|---|---|
| Masa [kg] | 5.412 | 4.077 | 1.832 | 0.755 | 0.019 + 0.115 | **12.210** |

Cálculo en `shoulder_model(q_ref)` ([dynamics_1r.py:70](../irb120/dynamics_1r.py#L70)), paso a paso:

1. Con la FK en $q_{\text{ref}}$ se obtienen el eje $\hat a = z_1$ de la junta 2 y un punto suyo $o_1$.
2. Para cada eslabón $k = 2..6$: su centro de masa en la base es $c_k = T_0^k\,\bar c_k$, y su inercia en la base es
   $R_k I_k R_k^T$.
3. **Masa:** $m = \sum m_k$.
4. **Centro de masa del conjunto:** $\bar r = \frac{1}{m}\sum m_k (c_k - o_1)$. Se le quita la componente a lo largo
   del eje: $r_\perp = \bar r - (\bar r\cdot\hat a)\hat a$, y $\ell_c = \lVert r_\perp\rVert$.
5. **Inercia respecto del eje** (Steiner, eslabón por eslabón):
   $J = \sum_k \big[\hat a^T R_k I_k R_k^T \hat a + m_k\,d_{k,\perp}^2\big]$, donde $d_{k,\perp}$ es la distancia del
   centro de masa $k$ al eje 2. Después, $I_c = J - m\ell_c^2$.
6. **Ángulo desde la vertical inferior:** $\theta_{\text{ref}} = \operatorname{atan2}\big(\hat a\cdot(\hat d\times r_\perp),\ \hat d\cdot r_\perp\big)$
   con $\hat d = (0, 0, -1)$, y $\varphi_0 = \theta_{\text{ref}} - q_{2,\text{ref}}$.

Valores para el ejemplo del archivo [08](08_ejemplo_resuelto_a_mano.md) ($q_{\text{ref}}$ = punto medio):

| $m$ | $\ell_c$ | $I_c$ | $J = I_c + m\ell_c^2$ | $\varphi_0$ | $mg\ell_c$ |
|---|---|---|---|---|---|
| 12.210 kg | 0.2491 m | 0.4479 kg·m² | 1.2053 kg·m² | −163.81° | 29.83 N·m |

$\theta \approx -164°$ significa que el centro de masa está **casi encima** del eje del hombro, a unos 16° de la
vertical superior: el brazo del IRB 120 trabaja como un **péndulo invertido**.

## 4. Validación del modelo reducido

Con las juntas congeladas, el modelo 1R debe coincidir **exactamente** con el modelo Lagrangiano completo de 6 GDL
(`dynamics.py`) en la junta 2:

$$
J = M_{22}(q_{\text{ref}}), \qquad mg\ell_c\sin\theta = g_2(q_{\text{ref}})
$$

En 30 configuraciones aleatorias coinciden hasta $10^{-10}$ (prueba `test_matches_full_model_for_joint_two`). Esto
valida $m$, $\ell_c$, $J$ y $\varphi_0$, incluido el signo. Más pruebas:

- `test_hanging_down_needs_no_static_torque`: en $\theta = 0$, $\tau = 0$; en $\theta = 90°$, $\tau = mg\ell_c$.
- `test_components_add_up_and_cruise_torque_is_pure_gravity`: con $\ddot q = 0$, $\tau = \tau_g \ne 0$.

Lo que el 1R **no** captura: el movimiento simultáneo de las juntas 3 a 6 durante el LSPB, que cambia $\ell_c$ y $J$,
y el acoplamiento dinámico entre juntas. En el notebook se comparará $\tau_{1R}(t)$ con el $\tau_2(t)$ del modelo
completo para cuantificar ese error.

## 5. Evaluación sobre el LSPB

Con $q_2(t)$ y $\ddot q_2(t)$ del LSPB ([04](04_C_lspb.md)):

$$
\tau_{in}(t) = J\,\ddot q_2(t), \qquad \tau_g(t) = mg\ell_c\sin\big(q_2(t) + \varphi_0\big), \qquad \tau = \tau_{in} + \tau_g
$$

Como $\varphi_0$ es constante, $\ddot\theta = \ddot q_2$. Código:
`OneRModel.torque_components(q2, q2_ddot)` ([dynamics_1r.py:55](../irb120/dynamics_1r.py#L55)).

### Interpretación (por fases del LSPB)

| Fase | $\ddot q_2$ | $\tau_{in}$ | $\tau_g$ | Comentario |
|---|---|---|---|---|
| Arranque | $+a$ | $+Ja$ (constante) | Varía con $\theta$ | La inercia se opone o se suma a la gravedad según el signo |
| Crucero | 0 | **0** | $\ne 0$ | **Velocidad constante NO implica torque cero**: el motor sigue sosteniendo el peso |
| Frenado | $-a$ | $-Ja$ | Varía con $\theta$ | Si el signo coincide con $\tau_g$, aparece el **pico** de esfuerzo |

- $\tau_{in}$ tiene **escalones** en $0$, $t_b$, $t_f - t_b$ y $t_f$, porque $\ddot q$ del LSPB es discontinua.
- $\tau_g$ es suave y depende solo de la **posición**: es máximo cuando el centro de masa está horizontal
  ($\theta = \pm 90°$) y nulo cuando está vertical.
- En reposo, en $t = 0$ y $t = t_f$ con $\ddot q$ ya en cero, el torque es solo gravitacional.

## 6. Singularidad frente a esfuerzo dinámico

| | Singularidad (D) | Pico de torque (E) |
|---|---|---|
| Naturaleza | Cinemática: geometría de $J(q)$ | Dinámica: masa, aceleración y gravedad |
| Criterio | $\operatorname{rank}J < 6$ | $\lvert\tau\rvert$ grande frente a la capacidad del motor |
| Depende de | Solo de $q$ | De $q$ y $\ddot q$, es decir, del perfil temporal |
| Efecto | Se pierde una dirección de movimiento; $\dot q$ se amplifica para ciertos $\dot x$ | El motor debe dar más esfuerzo |
| ¿Se evita bajando la velocidad? | **No** (es una propiedad de la postura) | **En parte**: menos $a$ implica menos $\tau_{in}$, pero $\tau_g$ queda |

## Preguntas de defensa

1. *¿Por qué $\dot q$ no aparece en $\tau$?* En 1 GDL, $J$ es constante: no hay Coriolis ni centrífuga.
2. *Durante el crucero $\ddot q = 0$. ¿Por qué el torque no es cero?* Por la gravedad: $mg\ell_c\sin\theta$ depende
   de la posición, no de la aceleración.
3. *¿De dónde sacaste $m$, $\ell_c$ y $J$?* Del CAD por eslabón de Truc y Lam (2020) más la pinza del datasheet SMC,
   combinados con Steiner. No se inventó ningún valor, y coinciden con $M_{22}$ y $g_2$ del modelo completo.
4. *¿Qué signo tiene la contribución inercial al frenar?* El opuesto al de la velocidad: $-Ja$. Si $\tau_g$ tiene ese
   mismo signo, se suman y aparece el pico.
5. *¿Un torque alto indica una singularidad?* No. Son fenómenos distintos (tabla §6).
