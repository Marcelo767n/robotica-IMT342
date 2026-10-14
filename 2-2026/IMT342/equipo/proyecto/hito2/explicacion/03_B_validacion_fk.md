# 03. Criterio B: validación de candidatos por cinemática directa

> Código: [`irb120/validation.py`](../irb120/validation.py) (y su uso en [`pieper.py`](../irb120/pieper.py)) ·
> Pruebas: [`tests/test_validation.py`](../tests/test_validation.py)

**Lo que pide la rúbrica para "Excelente":** verificar **sistemáticamente** los candidatos; comparar **posición y
orientación**; documentar el error y el criterio de aceptación; identificar inconsistencias. Es "Insuficiente"
aceptar soluciones de IK sin validarlas.

## 1. Idea

La IK se dedujo a mano y tiene ramas, envolturas de ángulo ($2\pi$) y casos especiales. Cualquier error de signo
produciría un $q$ que "parece" una solución pero no lo es. La forma independiente de comprobarlo es **reinyectar**
el candidato en la cinemática directa, que es un simple producto de matrices sin ramas, y comparar con lo pedido:

$$
\boxed{T\big(q^{(k)}\big) \stackrel{?}{\approx} T_d}
$$

## 2. Métricas (paso a paso)

Para cada candidato real $q^{(k)}$:

1. Calcular $T = $ `forward_kinematics_tcp(q)`, que es la FK al TCP de 0.150 m.
2. **Error de posición:** $e_p = \lVert p(q) - p_d \rVert_2$ [m].
3. **Error de orientación:** $e_R = \angle\big(R_d^T R(q)\big)$ [rad], el ángulo de la rotación que falta para pasar
   de la orientación pedida a la obtenida (ver [01 §5](01_modelo_DH_y_FK.md)). **Comparar solo la posición no
   alcanza:** girar $q_6$ mueve la orientación sin mover el TCP. La prueba
   `test_orientation_only_error_is_detected` lo demuestra: con $e_p = 0$ y $e_R = 0.01$ rad, el candidato se rechaza.
4. **Indicador global:** $e_F = \lVert T(q) - T_d\rVert_F$ (sin unidades, mezcla m y rad), útil para una sola columna
   resumen.

## 3. Criterio de aceptación

$$
e_p < 10^{-6}\ \text{m} \quad\text{y}\quad e_R < 10^{-6}\ \text{rad}
$$

**¿Por qué $10^{-6}$?**

- Es mucho menor que la repetibilidad del IRB 120 (±0.01 mm = $10^{-5}$ m): un error así no se puede ver en el
  robot real.
- Es mucho mayor que el ruido de redondeo de punto flotante: una FK de 6 matrices da errores de $10^{-16}$ a
  $10^{-15}$.

Un candidato correcto debería dar errores del orden de $10^{-16}$. Si un candidato da, por ejemplo, $10^{-3}$, es un
**error de la deducción, no de redondeo**. Esa es la "inconsistencia" que la rúbrica pide detectar.

Código: `POSITION_TOL_M`, `ROTATION_TOL_RAD`, `FKCheck.accepted` ([validation.py:33](../irb120/validation.py#L33)) y
`fk_check(target, q)` ([validation.py:45](../irb120/validation.py#L45)).

## 4. Qué se valida y con qué $q$

En `analyze_pose` ([pieper.py:337](../irb120/pieper.py#L337)) se valida **toda rama real**, incluso las que violan
límites, usando su $q$ crudo. Así se separan dos preguntas distintas:

| Pregunta | Herramienta |
|---|---|
| ¿La matemática de la rama es correcta? | FK de $q_{\text{raw}}$: $e_p, e_R \approx 10^{-16}$ |
| ¿El robot puede adoptar esa rama? | Límites articulares |

Si una rama real **fallara** la FK, el reporte lo mostraría (`e_p` grande, `aceptada = no`) y señalaría un error en
la IK, no una limitación del robot.

## 5. Validación masiva: prueba de ida y vuelta

`round_trip_test(samples, seed)` ([validation.py:67](../irb120/validation.py#L67)):

1. Genera $q$ aleatorios uniformes **dentro de los límites**.
2. Calcula $T = FK(q)$. Esa pose es alcanzable por construcción.
3. Resuelve la IK y verifica cada solución por FK.
4. Cuenta: poses resueltas, cuántas veces aparece el **$q$ original** entre las soluciones y el peor $e_p$ y $e_R$.

Resultado esperado: el 100 % de las poses resueltas, el 100 % con el $q$ original recuperado y errores máximos
< $10^{-9}$ m. Prueba: `test_round_trip_recovers_every_random_configuration`.

## Preguntas de defensa

1. *¿Cómo sabes que tu IK es correcta?* Cada candidato se reinyecta en la FK, que es independiente y no tiene ramas,
   y se compara posición **y** orientación con una tolerancia de $10^{-6}$. Además, en la prueba de ida y vuelta se
   recupera siempre el $q$ original.
2. *¿Por qué no basta con la posición?* Porque $q_6$ (y otras combinaciones de la muñeca) cambian la orientación sin
   mover el TCP.
3. *¿Qué harías si una rama real no pasa la FK?* Es un error de signo, de offset o de cuadrante en la IK: se revisa
   el paso del brazo comparando $p_W$, y luego el de la muñeca comparando $R_3^6$.
