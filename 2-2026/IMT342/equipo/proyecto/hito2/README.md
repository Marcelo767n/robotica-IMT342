# Hito 2 — Pipeline del ABB IRB 120 en Python puro (sin ROS)

Pipeline completo de la guía oficial del Hito 2 (IMT-342), con **dos poses**: la pose inicial (posición de
calibración ABB, todos los ejes en 0°, constante `HOME_Q`) y la pose objetivo que da el docente:
`T_d → Pieper (8 ramas) → validación FK → LSPB → Jacobiano / singularidad → dinámica 1R → τ(t)`.
Solo necesita Python 3 y NumPy; los notebooks añaden Matplotlib y Jupyter. TCP a **0.150 m** de la brida.

## Contenido: qué es cada cosa

Leyenda: 🎓 **presentación/entrega** (lo que se entrega o se muestra en la defensa) · ⚙️ **código** (necesario para que
el notebook funcione) · ✅ **verificación** · 📖 **explicación/estudio** (para el equipo) · 🗄️ **histórico** (no se
entrega).

```text
hito2/
├── 🎓 Hito2_IRB120_pipeline.ipynb      ENTREGABLE 1: notebook integrado, ya ejecutado (33 verificaciones)
├── 🎓 figuras/                          figuras que exporta el notebook (PDF/PNG); las usa el informe
│     A_ramas_brazo, A_ocho_ramas_3d, A_conteo_ramas        (criterio A)
│     B_errores_fk                                          (B)
│     C_lspb_perfiles, C_uso_limites, C_movimiento_3d        (C)
│     D_twist_trayectoria, D_singularidad_rango, D_amplificacion   (D)
│     E_torque_1R, E_1R_vs_completo, E_efecto_velocidad      (E)
├── 🎓 resultados/                       valores y tablas LaTeX que exporta el notebook (los lee el informe)
├── ⚙️ irb120/                           paquete Python: TODA la matemática
│     dh.py · transforms.py · pieper.py · validation.py · lspb.py · jacobian.py
│     dynamics.py · dynamics_1r.py · urdf_chain.py
├── ⚙️ build_pipeline_notebook.py        escribe y ejecuta el notebook desde cero
├── ⚙️ analizar_pose.py                  CLI: ¿es alcanzable esta pose? (8 ramas + rama elegida)
├── ⚙️ requirements.txt                  dependencias (Python 3, NumPy, Matplotlib, Jupyter, pytest)
├── ✅ tests/                            54 pruebas automáticas (pytest)
├── ✅ datos/irb120.urdf                 URDF del Hito 1, solo para verificar la FK de forma independiente
├── 📖 explicacion/                      un .md por criterio (01–08) + guía de estudio del código (09)
├── 📖 README.md                         este archivo
└── 🗄️ anexos/                           notebooks de la versión anterior del hito (no son la entrega)
```

**Entregables según la guía oficial:** (1) el notebook `.ipynb`, que necesita junto a él la carpeta `irb120/` (no
funciona aislado); (2) el **informe IEEE en PDF**, que está en
[`../docs/hito2/informe_ieee/informe_hito2_ieee.pdf`](../docs/hito2/informe_ieee/README.md) (el `.tex` lee
`figuras/` y `resultados/` de esta carpeta); (3) la **defensa** oral, para la que sirven `explicacion/` y el notebook.
ROS, RViz y Gazebo **no** se requieren.

**Probado con** Python 3.12.3, NumPy 2.5.4 y Matplotlib 3.11.2. El notebook imprime las versiones al ejecutarse.

## Cómo ejecutarlo

Desde esta carpeta (`hito2/`):

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q tests                        # 54 pruebas
jupyter lab Hito2_IRB120_pipeline.ipynb          # editar POSE_OBJETIVO (sección 1.3) y Restart & Run All
python build_pipeline_notebook.py                # o regenerarlo y ejecutarlo sin abrir Jupyter
python analizar_pose.py 0.40 0.10 0.35 0 180 0    # x y z [m]  roll pitch yaw [grados]
```

Uso rápido desde Python:

```python
import numpy as np
from irb120.dh import HOME_Q
from irb120.transforms import pose_from_xyz_rpy_deg
from irb120.pieper import analyze_pose, select_solution
from irb120.lspb import plan_lspb, default_limits

T_d = pose_from_xyz_rpy_deg(0.40, 0.10, 0.35, 0, 180, 0)
report = analyze_pose(T_d)                 # 8 ramas verificadas por FK
print(report.verdict)
q_f = np.array(select_solution(report, HOME_Q).q)          # desde la pose inicial
traj = plan_lspb(HOME_Q, q_f, *default_limits())
print(traj.tf, traj.tb)
```

La explicación de cada módulo está en [`explicacion/`](explicacion/README.md).

## Relación con el resto del repositorio

**La versión válida para el Hito 2 es esta carpeta (`hito2/`).** El paquete ROS 2 `ros2_ws/src/irb120_hito2` es de
la versión anterior del hito: se conserva por el Hito 1 y como integración opcional (nodo, RViz y verificador de
colisiones con el CAD), pero **ya no es igual** a este código. Usa un TCP de 0.100 m (aquí es 0.150 m) y no tiene la
enumeración de 8 ramas, la validación de entradas, el criterio de selección ni el modelo 1R. No hay que copiar código
entre los dos. Del Hito 1 solo se reutiliza el URDF (`datos/irb120.urdf`) y su evaluador (`irb120/urdf_chain.py`),
para verificar la FK.

## Qué son `build/`, `install/` y `_local_setup_util_ps1.py`

Al abrir `proyecto/ros2_ws` en el explorador de VS Code aparecen `build` e `install` desplegados. Esas dos
carpetas, igual que `log`, **se generan solas al ejecutar `colcon build`** y no forman parte del código del
proyecto (están ignoradas por git). Lo que se ve ahí puede ser una compilación vieja, por ejemplo una que solo trae
`irb120_hito1`. El archivo `_local_setup_util_ps1.py` también lo genera ROS al compilar: no es parte del proyecto
y no hace falta abrirlo ni editarlo.

El código fuente real está en `ros2_ws/src` (paquetes `irb120_hito1` e `irb120_hito2`) y, para el Hito 2 en
Python puro, en esta carpeta `hito2/`.
