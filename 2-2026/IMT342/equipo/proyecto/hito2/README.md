# Hito 2 — Python puro (sin ROS)

Cinemática inversa de **Pieper**, trayectorias **LSPB**, Jacobiano, dinámica y análisis de la singularidad `q5 = 0`
del ABB IRB 120. Solo necesita Python 3 y NumPy; los notebooks añaden Matplotlib y Jupyter.

## Contenido

```text
hito2/
├── irb120/                          # paquete Python (solo NumPy)
│   ├── dh.py                        # tabla DH y cinemática directa (a tool0 y al TCP de la pinza)
│   ├── pieper.py                    # cinemática inversa analítica, hasta 8 soluciones
│   ├── lspb.py                      # perfil LSPB sincronizado con límites de v y a
│   ├── jacobian.py                  # Jacobiano 6x6, det J, cond(J), SingularityError
│   ├── dynamics.py                  # M(q), c(q, q̇), g(q) y torques (incluye la pinza SMC MHZ2-16D)
│   └── transforms.py                # rpy, cuaterniones y matrices de pose
├── notebooks/
│   ├── 01_cinematica_inversa_pieper.ipynb   # IK de Pieper: ejemplos, alcance y validación de 1000 poses
│   ├── 02_trayectorias_lspb.ipynb           # LSPB: perfiles, sincronía y efecto de los límites
│   └── 03_singularidad_q5.ipynb             # PASAPORTE: divergencia de velocidades y torques en q5 = 0
├── tests/                           # 24 pruebas (pytest)
├── build_notebooks.py               # regenera y deja listos los tres notebooks
└── requirements.txt
```

Los notebooks ya están ejecutados: se pueden leer en VS Code o en GitHub sin correr nada.

## Cómo ejecutarlo

Desde esta carpeta (`hito2/`):

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q tests                 # 24 pruebas
jupyter lab notebooks/                    # abrir y ejecutar los notebooks
```

Uso rápido desde Python:

```python
import numpy as np
from irb120.dh import forward_kinematics_tcp
from irb120.pieper import inverse_kinematics_tcp
from irb120.lspb import plan_lspb

q = np.deg2rad([30, -20, 15, 40, -35, 60])
T = forward_kinematics_tcp(q)                          # pose del TCP
sol = inverse_kinematics_tcp(T, q)[0]                  # solución más cercana a q
traj = plan_lspb(np.zeros(6), np.array(sol.q), np.deg2rad([75, 75, 75, 96, 96, 126]), 3.0)
print(traj.tf, traj.sample(traj.tf / 2)[0])
```

Qué hace cada módulo, con ejemplos y las fórmulas, está en
[`docs/hito2/guia_hito2.md`](../docs/hito2/guia_hito2.md).

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
