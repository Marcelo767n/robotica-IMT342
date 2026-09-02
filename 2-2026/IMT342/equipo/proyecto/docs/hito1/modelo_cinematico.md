# Modelo cinemático del ABB IRB 120

## Convención adoptada

Se utiliza Denavit–Hartenberg clásico:

\[
{}^{i-1}T_i = R_z(\theta_i)\,T_z(d_i)\,T_x(a_i)\,R_x(\alpha_i)
\]

La tabla procede de Bahani et al., Tabla I, y está expresada en unidades SI:

| Eje | Ángulo efectivo | `d` [m] | `a` [m] | `alpha` [rad] |
|---:|---:|---:|---:|---:|
| 1 | `q1` | 0.290 | 0.000 | `-pi/2` |
| 2 | `q2 - pi/2` | 0.000 | 0.270 | `0` |
| 3 | `q3` | 0.000 | 0.070 | `-pi/2` |
| 4 | `q4` | 0.302 | 0.000 | `pi/2` |
| 5 | `q5` | 0.000 | 0.000 | `-pi/2` |
| 6 | `q6 + pi` | 0.072 | 0.000 | `0` |

Los tópicos ROS publican los ángulos reales `q1...q6`. Los offsets de los ejes 2
y 6 se aplican dentro del modelo. Así, la postura ABB de calibración
`q=[0,0,0,0,0,0]` produce para `tool0`:

```text
[x, y, z] = [0.374, 0.000, 0.630] m
```

El centro de muñeca excluye `d6`, por lo que queda en `[0.302, 0, 0.630] m`,
coincidiendo con la posición A de la especificación del fabricante.

## Correspondencia DH–URDF

URDF aplica el movimiento articular después de su `origin`. Para representar DH
sin ambigüedad, cada fila se descompone en tres elementos:

```text
joint_i:          Rz(q_i)
theta_offset_i:   Rz(offset_i)
dh_i:             Tz(d_i) Tx(a_i) Rx(alpha_i)
```

Los únicos joints móviles del brazo son `joint_1` a `joint_6`. Los frames
intermedios son fijos y hacen visible la derivación matemática. La pinza añade
dos joints prismáticos independientes y un `tcp_link` fijo a `0.160 m` de
`tool0` sobre su eje Z.

## Parámetros dinámicos aproximados

Truc y Lam estimaron mediante CAD los siguientes parámetros. Se incluyen en el
URDF como aproximación académica, no como datos certificados para controlar el
robot real:

| Cuerpo | Masa [kg] | Centro de masa [m] |
|---|---:|---|
| Base | 8.659 | no publicado |
| Link 1 | 4.248 | `[0, 0.054, 0]` |
| Link 2 | 5.412 | `[-0.169, 0, 0]` |
| Link 3 | 4.077 | `[-0.012, 0, 0.023]` |
| Link 4 | 1.832 | `[0, -0.007, 0]` |
| Link 5 | 0.755 | `[0, 0, 0]` |
| Link 6 | 0.019 | `[0, 0, -0.007]` |

Las matrices de inercia completas están transcritas en
`urdf/irb120.macro.xacro`. No se asigna una inercia inventada a la base ni a la
pinza provisional.

## Límites usados

Los rangos y velocidades máximas se tomaron de la especificación oficial ABB
3HAC035960-001 Rev. S:

| Eje | Rango [°] | Velocidad máxima [°/s] |
|---:|---:|---:|
| 1 | `[-165, 165]` | 250 |
| 2 | `[-110, 110]` | 250 |
| 3 | `[-110, 70]` | 250 |
| 4 | `[-160, 160]` | 320 |
| 5 | `[-120, 120]` | 320 |
| 6 | `[-400, 400]` | 420 |

Los esfuerzos `100 N·m` presentes en el URDF son valores de compatibilidad para
visualización, no límites certificados. No deben usarse para control dinámico.

## Fuentes

- A. Bahani et al., “The Inverse Kinematics Evaluation of 6-DOF Robots…”, 2023:
  [paper local](../../documentosGuia/IJMERR-V12N2-121.pdf).
- L. N. Truc y N. T. Lam, “Quasi-physical modeling of robot IRB 120…”, 2020:
  [paper local](../../documentosGuia/Quasi-physical_modeling_of_robot_IRB_120_using_Sim.pdf).
- ABB, *Product specification IRB 120*, 3HAC035960-001 Rev. S:
  [documento oficial](https://library.e.abb.com/public/6aed5e91083f4fceb358eea2fe4c1bab/3HAC035960%20PS%20IRB%20120-en.pdf).
