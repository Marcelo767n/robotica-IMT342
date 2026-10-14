# Hito 2 — Pipeline del ABB IRB 120 en Python puro (sin ROS)

Pipeline completo de la guía oficial del Hito 2 (IMT-342), con **dos poses**: la pose inicial (posición de
calibración ABB, todos los ejes en 0°, constante `HOME_Q`) y la pose objetivo que da el docente:
`T_d → Pieper (8 ramas) → validación FK → LSPB → Jacobiano / singularidad → dinámica 1R → τ(t)`.
Solo necesita Python 3 y NumPy; los notebooks añaden Matplotlib y Jupyter. TCP a **0.150 m** de la brida.

## Contenido

```text
hito2/
├── irb120/                  # paquete Python (solo NumPy)
│   ├── dh.py                # tabla DH, FK a tool0 y al TCP, límites y velocidades del datasheet
│   ├── pieper.py            # IK analítica: 8 ramas, real/admisible, analyze_pose, select_solution   (A)
│   ├── validation.py        # validación de candidatos por FK y prueba de ida y vuelta              (B)
│   ├── lspb.py              # LSPB sincronizado, comprobaciones y límites justificados              (C)
│   ├── jacobian.py          # Jacobiano, validación numérica, rango por SVD, direcciones perdidas   (D)
│   ├── dynamics_1r.py       # modelo 1R del hombro con parámetros del CAD                           (E)
│   ├── dynamics.py          # modelo completo M, c, g (fuente de parámetros y validación del 1R)
│   └── transforms.py        # rpy, cuaterniones y matrices de pose
├── Hito2_IRB120_pipeline.ipynb   # ENTREGABLE: notebook integrado, ejecutado (32 verificaciones)
├── build_pipeline_notebook.py    # regenera y ejecuta el notebook de inicio a fin
├── figuras/                 # figuras exportadas por el notebook (PDF/PNG) para el informe IEEE
├── analizar_pose.py         # CLI: escribe una pose y te dice si es alcanzable (tabla de 8 ramas)
├── explicacion/             # un .md por módulo: código + matemática paso a paso + ejemplo a mano
├── tests/                   # 49 pruebas (pytest)
├── anexos/                  # notebooks y explicación de la versión anterior del hito
└── requirements.txt
```

## Cómo ejecutarlo

Desde esta carpeta (`hito2/`):

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q tests                        # 49 pruebas
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

El código de esta carpeta es el mismo que usa el paquete ROS 2 `ros2_ws/src/irb120_hito2`, copiado aquí sin
dependencias de ROS. Para el Hito 2 **no hace falta ROS**. El paquete ROS se conserva por el Hito 1 y como
integración opcional (nodo, RViz y verificador de colisiones con el CAD). Si se cambia el código de un lado, hay
que copiarlo al otro.

## Qué son `build/`, `install/` y `_local_setup_util_ps1.py`

Al abrir `proyecto/ros2_ws` en el explorador de VS Code aparecen `build` e `install` desplegados. Esas dos
carpetas, igual que `log`, **se generan solas al ejecutar `colcon build`** y no forman parte del código del
proyecto (están ignoradas por git). Lo que se ve ahí puede ser una compilación vieja, por ejemplo una que solo trae
`irb120_hito1`. El archivo `_local_setup_util_ps1.py` también lo genera ROS al compilar: no es parte del proyecto
y no hace falta abrirlo ni editarlo.

El código fuente real está en `ros2_ws/src` (paquetes `irb120_hito1` e `irb120_hito2`) y, para el Hito 2 en
Python puro, en esta carpeta `hito2/`.
