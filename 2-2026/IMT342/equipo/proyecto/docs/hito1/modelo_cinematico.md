# Modelo cinemático corregido del ABB IRB 120

## Alcance del Hito 1

La cadena cinemática del brazo tiene seis juntas revolutas (`joint_1` a
`joint_6`) y seis marcos móviles (`link_1` a `link_5` y `tool0`). `base_link`
es el marco de referencia base y no se cuenta como una junta. Cada junta
revoluta tiene un único `origin`; los `visual` y `collision` son meshes STL ya
expresados en el marco de su eslabón, sin `origin` propio.

Además del brazo, el URDF incluye la pinza neumática (entregable de la Guía
PFI), acoplada a `tool0` con dos juntas **fijas**, que no son grados de
libertad: `gripper_mount` (sin `origin`, el marco de `gripper_link` coincide con
`tool0`) y `gripper_tcp_joint`, cuyo único offset es una traslación sobre Z de
`tool0` hasta el punto de agarre `gripper_tcp`. En total el URDF tiene 9 links
y 8 juntas (6 revolutas + 2 fijas). Así:

\[
T_{TCP}(q)=T_{DH}(q)\,T_z(z_{TCP}),\qquad z_{TCP}=0.150\ \text{m}
\]

El valor de \(z_{TCP}\) se define solo en `config/tcp.yaml`, compartido por el Xacro, la
DH, el validador y el Hito 2. Es una convención del modelo: no está medido en la pinza
real (`verified_on_robot: false`).

La geometría de la pinza es un modelo paramétrico propio, no el CAD de la pinza
real. Los bloques `collision` usan meshes simplificados del CAD; no hay masas ni
inercias.

## Tabla DH clásica

Se usa:

\[
A_i(q_i)=R_z(q_i+o_i)T_z(d_i)T_x(a_i)R_x(\alpha_i)
\]

| Eje | Offset `o` | `d` [m] | `a` [m] | `alpha` [rad] |
|---:|---:|---:|---:|---:|
| 1 | `0` | 0.290 | 0.000 | `-pi/2` |
| 2 | `-pi/2` | 0.000 | 0.270 | `0` |
| 3 | `0` | 0.000 | 0.070 | `-pi/2` |
| 4 | `0` | 0.302 | 0.000 | `pi/2` |
| 5 | `0` | 0.000 | 0.000 | `-pi/2` |
| 6 | `pi` | 0.072 | 0.000 | `0` |

La cinemática directa matemática es:

\[
T_{DH}(q)=A_1(q_1)A_2(q_2)A_3(q_3)A_4(q_4)A_5(q_5)A_6(q_6)
\]

## Cómo se convierte DH a coordenadas URDF

URDF representa una junta revoluta como:

\[
T_i^{URDF}(q_i)=O_iR_z(q_i)
\]

donde `O_i` es el `<origin xyz="..." rpy="...">` fijo y `Rz(q_i)` proviene de
`<axis xyz="0 0 1">`. Para evitar marcos auxiliares se define
`B_i=Tz(d_i)Tx(a_i)Rx(alpha_i)` y se pasa el `B_i` de cada fila al `origin` de
la junta siguiente. Los offsets de `theta` se combinan en esos origins.

| Junta | Transformación fija `O_i` | `xyz` URDF [m] | `rpy` URDF [rad] |
|---:|---|---|---|
| J1 | `I` | `0 0 0` | `0 0 0` |
| J2 | `B1 Rz(-pi/2)` | `0 0 0.290` | `-pi/2 -pi/2 0` |
| J3 | `B2` | `0.270 0 0` | `0 0 0` |
| J4 | `B3` | `0.070 0 0` | `-pi/2 0 0` |
| J5 | `B4` | `0 0 0.302` | `pi/2 0 0` |
| J6 | `B5 Rz(pi) Tz(0.072)` | `0 0.072 0` | `pi/2 0 pi` |

La última traslación puede incluirse antes de `Rz(q6)` porque `a6=0`,
`alpha6=0` y una traslación sobre Z conmuta con una rotación sobre Z. Por eso
`joint_6` puede terminar directamente en `tool0`, sin un `tool0_fixed`.

La igualdad que se verifica numéricamente es:

\[
O_1R_z(q_1)O_2R_z(q_2)\cdots O_6R_z(q_6)=T_{DH}(q)
\]

## Por qué los visuales no tienen `origin`

Solo los `origin` de `<joint>` pertenecen a la cinemática y provienen de DH
(uno por grado de libertad; el séptimo `origin` es el offset fijo del TCP). Los
STL de `meshes/` se re-expresaron en el marco de cada eslabón con
`scripts/import_cad.py`, de modo que `<visual>` y `<collision>` solo referencian
el mesh y no añaden traslaciones ni rotaciones. La prueba
`test_cad_meshes_fit_the_kinematic_skeleton` comprueba, con tolerancia de 1 cm,
que el origen de la junta siguiente cae dentro de la caja envolvente del mesh de
`link_1`, `link_2` y `link_4`. Los antiguos valores de masa `4.248 kg`, centro
de masa e inercias pertenecen a un modelo dinámico y se retiraron.

## Cálculo del error

Para la misma configuración `q`, se calculan independientemente `T_DH(q)` y
`T_URDF(q)`. Si sus posiciones son `p_DH` y `p_URDF`, el error posicional es:

\[
e_p=\lVert p_{DH}-p_{URDF}\rVert_2=
\sqrt{(\Delta x)^2+(\Delta y)^2+(\Delta z)^2}
\]

Para orientación se usa el giro relativo
`R_rel = R_DH^T R_URDF` y su distancia angular:

\[
e_R=\operatorname{atan2}\left(\frac{\lVert vee(R_{rel}-R_{rel}^T)\rVert}{2},
\frac{tr(R_{rel})-1}{2}\right)
\]

El criterio del Hito 1 es `e_p < 1e-6 m`.

## Dos configuraciones justificadas

### Prueba A: postura de trabajo

`qA=[30,-20,15,40,-35,60]°`. Activa los seis ejes, evita que los errores se
oculten por la simetría de la pose cero y deja el extremo elevado y delante del
robot. Representa una postura de aproximación o manipulación.

### Prueba B: postura plegada crítica

`qB=[90,-60,60,90,60,180]°`. También activa los seis ejes, pero pliega el brazo
y acerca `tool0` al eje de la base. Sirve para detectar signos y offsets
incorrectos y para estudiar la proximidad a la base.

La validación de Hito 1 comprueba la pose. La comprobación de colisión con los
meshes `collision` del CAD vive en `irb120_hito2/kinematics/collision.py`
(paquete del Hito 2).

## Límites articulares

| Eje | Rango [°] | Velocidad máxima [°/s] |
|---:|---:|---:|
| 1 | `[-165, 165]` | 250 |
| 2 | `[-110, 110]` | 250 |
| 3 | `[-110, 70]` | 250 |
| 4 | `[-160, 160]` | 320 |
| 5 | `[-120, 120]` | 320 |
| 6 | `[-400, 400]` | 420 |

## Fuentes

- A. Bahani et al., “The Inverse Kinematics Evaluation of 6-DOF Robots…”,
  2023: [paper local](../../referencias/bibliografia/IJMERR-V12N2-121.pdf).
- ABB, *Product specification IRB 120*, 3HAC035960-001 Rev. S.
