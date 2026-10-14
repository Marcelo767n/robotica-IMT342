# 04. Criterio C: trayectoria LSPB

> Código: [`irb120/lspb.py`](../irb120/lspb.py) · Pruebas: [`tests/test_lspb.py`](../tests/test_lspb.py)

**Lo que pide la rúbrica para "Excelente":** construir el perfil con **parámetros justificados**; obtener
$q, \dot q, \ddot q$; cumplir las **condiciones de frontera** (reposo al inicio y al final); graficar e interpretar;
código y ecuaciones consistentes. Es "Insuficiente" un perfil discontinuo o usar una función de biblioteca sin
entenderla. Aquí todo está implementado a mano.

## 1. Qué es un LSPB

*Linear Segment with Parabolic Blends*: cada junta va de $q_0$ (pose inicial, calibración ABB: $q_0 = 0$) a $q_f$
(configuración elegida para la pose del docente) en tres fases:

| Fase | Intervalo | $\ddot q$ | $\dot q$ | $q$ |
|---|---|---|---|---|
| Arranque (parábola) | $0 \le t < t_b$ | $+a$ | $a t$ | $q_0 + \tfrac12 a t^2$ |
| Crucero (recta) | $t_b \le t \le t_f - t_b$ | $0$ | $V$ | $q_0 + V\,(t - \tfrac{t_b}{2})$ |
| Frenado (parábola) | $t_f - t_b < t \le t_f$ | $-a$ | $a(t_f - t)$ | $q_f - \tfrac12 a (t_f - t)^2$ |

con $V = a\,t_b$ (al terminar el arranque, la velocidad debe ser la de crucero).

Código: `LspbTrajectory.sample(t)` ([lspb.py:50](../irb120/lspb.py#L50)) escribe exactamente esas tres filas.
`sample_many(times)` evalúa muchos instantes de una vez para graficar y `phase(t)` dice en qué fase está $t$.

## 2. Deducción de las ecuaciones (paso a paso)

1. **Arranque:** se parte del reposo ($q(0) = q_0$, $\dot q(0) = 0$) con aceleración constante $a$. Integrando dos
   veces: $\dot q = a t$ y $q = q_0 + \frac12 a t^2$.
2. **Fin del arranque:** en $t_b$, $\dot q = a t_b = V$ y $q(t_b) = q_0 + \frac12 V t_b$.
3. **Crucero:** velocidad constante $V$ desde ese punto: $q = q_0 + \frac12 V t_b + V(t - t_b) = q_0 + V(t - \frac{t_b}{2})$.
4. **Frenado:** por simetría, desde el reposo final hacia atrás: $q = q_f - \frac12 a (t_f - t)^2$.
5. **Empalme del crucero con el frenado** en $t = t_f - t_b$:

$$
q_0 + V\big(t_f - \tfrac{3}{2}t_b\big) = q_f - \tfrac12 V t_b
\;\Rightarrow\; \boxed{V = \frac{q_f - q_0}{t_f - t_b}}, \qquad \boxed{a = \frac{V}{t_b}}
$$

Así, con $(q_0, q_f, t_f, t_b)$ queda todo determinado (`cruise_velocity` y `blend_acceleration`,
[lspb.py:43](../irb120/lspb.py#L43)). Para que exista la fase de crucero hace falta $t_b \le t_f/2$; si
$t_b = t_f/2$, el perfil es triangular.

## 3. Continuidad y condiciones de frontera

- $q$ es continua en $t_b$ y $t_f - t_b$ por construcción (pasos 3 y 5).
- $\dot q$ es continua: vale $V$ a ambos lados de cada empalme.
- $\ddot q$ **salta**: de $a$ a $0$ en $t_b$, de $0$ a $-a$ en $t_f - t_b$, y también en $0$ y $t_f$. El LSPB es
  $C^1$, no $C^2$. Esto se ve en la dinámica: la componente inercial del torque tiene escalones (ver
  [07](07_E_dinamica_1R.md)).
- **Reposo en las fronteras:** $\dot q(0) = a\cdot 0 = 0$ y $\dot q(t_f) = a\cdot 0 = 0$.

`check_trajectory(traj, vmax, amax)` ([lspb.py:96](../irb120/lspb.py#L96)) lo **comprueba numéricamente**:
$|q(0) - q_0|$, $|q(t_f) - q_f|$, $|\dot q(0)|$, $|\dot q(t_f)|$, el salto de $q$ y de $\dot q$ evaluando a
$\pm 10^{-9}$ s de cada empalme, y los márgenes $v_{\max} - |V|$ y $a_{\max} - |a|$. La propiedad `passed` exige que
todo eso sea menor que $10^{-6}$ y que los márgenes sean $\ge 0$.

## 4. Sincronización de las 6 juntas

Todas las juntas usan el **mismo $t_f$ y el mismo $t_b$**, así que arrancan y llegan a la vez. Cada una tiene su
propio $V_i = D_i/(t_f - t_b)$ y su $a_i = V_i/t_b$, con $D_i = q_{f,i} - q_{0,i}$. En el espacio articular el
movimiento es una recta: $q(t) = q_0 + s(t)\,(q_f - q_0)$, con el mismo $s(t) \in [0, 1]$ para todas. La prueba
`test_all_joints_move_synchronously` verifica que en $t_f/2$ cada junta está exactamente a mitad de camino.

## 5. Tiempo mínimo que respeta los límites

Restricciones por junta, con $D_i = |q_{f,i} - q_{0,i}|$:

$$
|V_i| \le v_{\max,i} \iff t_f - t_b \ge \frac{D_i}{v_{\max,i}}, \qquad
|a_i| \le a_{\max,i} \iff t_b\,(t_f - t_b) \ge \frac{D_i}{a_{\max,i}}
$$

Se define $K = \max_i D_i/a_{\max,i}$ y $D_v = \max_i D_i/v_{\max,i}$, el peor caso entre las juntas. Para un $t_f$
dado se elige el **menor** $t_b$ que cumple la condición de aceleración con igualdad:

$$
t_b(t_f - t_b) = K \;\Rightarrow\; t_b = \frac{t_f - \sqrt{t_f^2 - 4K}}{2} \quad (\text{exige } t_f^2 \ge 4K)
$$

y luego se exige $t_f - t_b \ge D_v$. Esa factibilidad es **monótona** en $t_f$ (más tiempo nunca empeora), así que el
$t_f$ mínimo se encuentra por **bisección** (`plan_lspb`, [lspb.py:130](../irb120/lspb.py#L130)).

**Caso cerrado útil:** si la misma junta $j$ satura velocidad y aceleración, entonces $t_b = v_{\max,j}/a_{\max,j}$ y
$t_f = D_j/v_{\max,j} + t_b$.

## 6. Parámetros justificados (`default_limits`, [lspb.py:118](../irb120/lspb.py#L118))

| Parámetro | Valor | Procedencia |
|---|---|---|
| $v_{\max,i}$ | $0.25 \times$ (250, 250, 250, 320, 320, 420) °/s | Datasheet ABB por eje, por un factor de velocidad del **25 %**, como el *speed override* del controlador. Es un valor conservador para un movimiento de laboratorio o de prueba. |
| $a_{\max,i}$ | $v_{\max,i} / 0.25\ \text{s}$ | **Supuesto declarado:** ABB **no publica** aceleraciones articulares. Se asume que cada eje puede alcanzar su $v_{\max}$ en una rampa de 0.25 s. |

Los dos factores se pueden cambiar: `default_limits(speed_scale, ramp_time_s)`. En el notebook se mostrará el efecto
de variarlos sobre $t_f$, $t_b$ y el torque.

## 7. Interpretación de las gráficas

- $q(t)$: tiene forma de "S" suave. Las parábolas en los extremos evitan arrancar y frenar en seco.
- $\dot q(t)$: trapecio con rampa, meseta en $V$ y rampa de bajada. El área bajo la curva es $D$, y la prueba
  `test_numerical_integration_matches_position` lo comprueba integrando numéricamente.
- $\ddot q(t)$: escalones $+a$, $0$, $-a$. Los esfuerzos inerciales aparecen solo en las mezclas.

## Preguntas de defensa

1. *¿Por qué $V = D/(t_f - t_b)$ y no $D/t_f$?* Porque durante las mezclas se avanza "a media velocidad": el área del
   trapecio es $V(t_f - t_b)$.
2. *¿Qué pasa si $t_b > t_f/2$?* Las parábolas se solapan: no existe LSPB con esa $a$ y hace falta más $t_f$ o más
   aceleración.
3. *¿Es continuo el perfil?* $q$ y $\dot q$ sí; $\ddot q$ no (tiene escalones), y eso aparece como escalones del
   torque inercial.
4. *¿De dónde salen $v_{\max}$ y $a_{\max}$?* $v_{\max}$ del datasheet ABB (escalado al 25 %); $a_{\max}$ es un
   supuesto declarado, porque ABB no la publica.
