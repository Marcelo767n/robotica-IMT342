# Hito 2: cinemática inversa de Pieper, LSPB y singularidad q5 = 0

> Guía detallada con ejemplos de cada módulo: [guia_hito2.md](guia_hito2.md).

Requisito (Guía PFI, Hito 2): nodo ROS en Python que reciba una pose, ejecute
Pieper y genere una trayectoria LSPB; pasaporte: notebook que muestre la
divergencia analítica de velocidades y torques en `q5 = 0`.

## Paquete `irb120_hito2`

| Módulo | Contenido |
|---|---|
| `kinematics/pieper.py` | IK analítica por Pieper (sin MoveIt ni solvers numéricos) |
| `kinematics/jacobian.py` | Jacobiano geométrico, `det J`, número de condición, `SingularityError` |
| `dynamics.py` | `M(q)`, `c(q, q̇)`, `g(q)` y torques; parámetros CAD de Truc y Lam (2020) |
| `trajectory/lspb.py` | LSPB sincronizado con límites de velocidad y aceleración |
| `kinematics/collision.py` | Autocolisión y mesa con los meshes `collision` del CAD |
| `nodes/ik_trajectory_node.py` | `PoseStamped` → Pieper → LSPB → `/irb120/joint_commands_deg` |
| `nodes/send_target.py` | Publica una pose objetivo desde terminal |

## Método de Pieper para el IRB 120

Los ejes 4, 5 y 6 se cortan en el centro de muñeca `p_wc = p_tool0 - d6·z6`.

1. **Posición** (q1, q2, q3). `q1 = atan2(y, x)` o `+π` (brazo atrás). En el plano
   vertical del brazo, `L2 = 0.270`, `L3 = √(d4² + a3²)` y `δ = atan2(a3, d4)`.
   La ley de cosenos da `-sin(q3 - δ) = (D² - L2² - L3²)/(2·L2·L3)`, con dos
   soluciones de codo, y luego `q2 = α - atan2(L3 sin η, L2 + L3 cos η)` con
   `η = π/2 + q3 - δ`.
2. **Orientación** (q4, q5, q6). `R₃⁶ = R₀³ᵀ R = Rz(q4) Ry(-q5) Rz(q6 + π)`, un
   Euler ZYZ con dos soluciones de muñeca (`q5 > 0` y `q5 < 0`).
3. Se obtienen hasta 8 soluciones. Se ajustan a los límites articulares (con
   vueltas de 2π), se verifican contra la FK DH (`< 1e-6 m`) y se ordenan por
   cercanía a la postura actual. El TCP se resuelve con `T_tool0 = T_tcp·Tz(-0.100)⁻¹`.

En `q5 = 0` solo `q4 + q6` queda determinado: la solución se marca
`singular_wrist=True` y conserva `q4` de referencia.

## LSPB

Todas las juntas comparten `tf` y `tb`, con `V = Δq/(tf - tb)` y `a = V/tb`.
El menor `tf` factible se halla por bisección respetando `|V| ≤ vmax` y
`|a| ≤ amax`. Por defecto el nodo usa el 30 % de la velocidad máxima ABB y
`3 rad/s²`.

## Singularidad de muñeca

Con el centro de muñeca como referencia, `J` es triangular por bloques:
`det J = -sin(q5)·det(Jp_brazo)`. En `q5 = 0`:

- `q̇ = J⁻¹ v` crece como `1/|sin q5|` (pendiente log-log medida: −0.97).
- `q̈` y el torque dinámico `τ - g` crecen como `1/sin² q5` (pendiente medida: −2.00).
- Para `q5 = 0` exacto, `joint_velocity` lanza `SingularityError`.

Evidencia ejecutada: [`notebooks/hito2_singularidad_q5.ipynb`](../../notebooks/hito2_singularidad_q5.ipynb).
Los parámetros inerciales son aproximaciones por CAD más la masa de la pinza SMC MHZ2-16D (115 g):
sirven para la tendencia, no como identificación del robot real.

## Uso

```bash
cd ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select irb120_hito1 irb120_hito2
source install/setup.bash
ros2 launch irb120_hito2 hito2.launch.py
```

En otra terminal (con los dos `source`), pinza hacia abajo por defecto:

```bash
ros2 run irb120_hito2 send_target 0.25 -0.15 0.30
ros2 topic echo /irb120/ik_status
```

Una pose inalcanzable (por ejemplo `5 0 0`) se rechaza con `SIN SOLUCION` sin
mover el robot. Para reproducir el notebook:

```bash
python3 -m venv --system-site-packages .venv-notebooks
.venv-notebooks/bin/pip install -r notebooks/requirements.txt
.venv-notebooks/bin/jupyter lab notebooks/hito2_singularidad_q5.ipynb
```
