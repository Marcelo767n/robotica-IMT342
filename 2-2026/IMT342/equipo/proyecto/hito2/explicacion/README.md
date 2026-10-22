# Explicación del Hito 2: código y matemática

Esta carpeta explica, **módulo por módulo**, qué hace el código del paquete `irb120`, de dónde sale cada
ecuación y cómo se comprobó que el resultado es correcto. Está pensada para preparar la defensa: según la rúbrica,
**cada integrante** debe poder explicar cualquier parte del pipeline, no solo la que programó (criterio G4).

## El pipeline

```text
T_0 = FK(HOME_Q) (pose inicial: calibración ABB, q = 0)   y   T_d (pose objetivo, la da el docente)
  │
  ▼  A. Pieper ............ 8 ramas candidatas q^(k)        → 02_A_pieper.md
  ▼  B. Validación FK ..... T(q^(k)) ≈ T_d ? → admisibles   → 03_B_validacion_fk.md
  ▼  Selección ............ una rama q_f justificada         → 02_A_pieper.md §6
  ▼  C. LSPB .............. q(t), q̇(t), q̈(t)                → 04_C_lspb.md
  ├─▶ D. Jacobiano ........ ẋ(t) = J(q(t)) q̇(t)              → 05_D_jacobiano.md
  │      └─ Singularidad .. rango J < 6 (experimento aparte) → 06_D_singularidades.md
  └─▶ E. Dinámica 1R ...... τ(t) = J q̈₂ + m g ℓc sin θ      → 07_E_dinamica_1R.md
```

Todo descansa en el modelo geométrico del robot: tabla DH, cinemática directa y TCP, en
[01_modelo_DH_y_FK.md](01_modelo_DH_y_FK.md).

El pipeline completo, con gráficas y 34 verificaciones automáticas, está en el notebook
[`../Hito2_IRB120_pipeline.ipynb`](../Hito2_IRB120_pipeline.ipynb). Trabaja con **dos poses**:

- **Pose inicial (elegida por el equipo):** la posición de calibración de ABB, con todos los ejes en 0° (`HOME_Q` en
  `dh.py`). Es la postura de referencia que ABB usa para la sincronización (`MoveAbsJ` a un jointtarget de ceros).
- **Pose objetivo:** la que da el docente. Se escribe en la sección 1.3 del notebook.

## Índice

| Archivo | Rúbrica | Código | Pruebas |
|---|---|---|---|
| [01_modelo_DH_y_FK.md](01_modelo_DH_y_FK.md) | Base de todo | `irb120/dh.py`, `irb120/transforms.py` | `tests/test_dh.py` |
| [02_A_pieper.md](02_A_pieper.md) | **A** (15 %) | `irb120/pieper.py`, `analizar_pose.py` | `tests/test_pieper.py` |
| [03_B_validacion_fk.md](03_B_validacion_fk.md) | **B** (10 %) | `irb120/validation.py` | `tests/test_validation.py` |
| [04_C_lspb.md](04_C_lspb.md) | **C** (15 %) | `irb120/lspb.py` | `tests/test_lspb.py` |
| [05_D_jacobiano.md](05_D_jacobiano.md) | **D** (20 %), primera parte | `irb120/jacobian.py` | `tests/test_jacobian.py` |
| [06_D_singularidades.md](06_D_singularidades.md) | **D** (20 %), segunda parte | `irb120/jacobian.py` | `tests/test_jacobian.py`, `tests/test_singularity.py` |
| [07_E_dinamica_1R.md](07_E_dinamica_1R.md) | **E** (15 %) | `irb120/dynamics_1r.py` (usa `dynamics.py`) | `tests/test_dynamics_1r.py` |
| [08_ejemplo_resuelto_a_mano.md](08_ejemplo_resuelto_a_mano.md) | A, B, C, D y E con números | Todos | Contrastado con el código |
| [09_guia_de_estudio_del_codigo.md](09_guia_de_estudio_del_codigo.md) | Defensa (G1–G4) | **Todos los archivos**: qué hace cada función, flujo de datos, notebook sección por sección y autoevaluación | — |
| [10_guia_defensa.md](10_guia_defensa.md) | **Defensa (G1–G4)** | Plan de estudio para el día, qué mostrar y en qué orden, ecuaciones para la pizarra, preguntas con respuestas modelo y números clave | — |

## Convenciones (valen para todos los archivos)

- **Unidades:** ángulos en rad (en grados solo al mostrarlos), longitudes en m, tiempo en s, torque en N·m.
- **Ángulos articulares:** son los ángulos ABB `q1..q6`. Los offsets DH de las filas 2 y 6 se aplican dentro de
  `dh_transform`.
- **Marco base:** `base_link`, con z hacia arriba y origen en la base del robot. La gravedad es $g = (0, 0, -9.81)$ m/s².
- **TCP:** está sobre el eje $z_6$ de la brida (`tool0`), a **0.150 m** de ella.
- **Pose deseada** $T_d$: matriz homogénea 4×4 del TCP en `base_link`. Se puede escribir como posición más
  roll-pitch-yaw, con $R = R_z(\text{yaw})\,R_y(\text{pitch})\,R_x(\text{roll})$.

## Cómo comprobar todo

Desde `hito2/`:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q tests                      # 56 pruebas
python analizar_pose.py 0.40 0.10 0.35 0 180 0  # x y z [m]  roll pitch yaw [grados]
```

## Qué está prohibido y cómo se respeta

- **No inventar datos del robot.** La tabla DH viene de Bahani et al. (2023) y coincide con las cotas del datasheet
  ABB. Los límites y velocidades por eje salen del *Product specification IRB 120*. Las masas e inercias, del CAD de
  Truc y Lam (2020). Lo que no publica el fabricante (aceleraciones articulares) se declara como **supuesto** con su
  justificación, en [04_C_lspb.md](04_C_lspb.md).
- **No usar un solver numérico como sustituto de Pieper.** La cinemática inversa es cerrada: `atan2`, `asin` y la ley
  de cosenos. No hay iteraciones ni `scipy.optimize`.
- **No declarar singularidad "por observación"** ni confundirla con torque infinito. Ver
  [06_D_singularidades.md](06_D_singularidades.md).
