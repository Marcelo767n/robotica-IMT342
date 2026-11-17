# Proyecto ABB IRB 120 · IMT-342 Robótica

Modelo cinemático, simulación en ROS 2 y control del brazo **ABB IRB 120** real desde una PC Linux.
Universidad Católica Boliviana, 2-2026. Equipo: Dayana Andrade, Mirko Ayala y Marcelo Navarro.

> **Estado (17/11/2026):** el IRB 120 físico ya se mueve con ángulos enviados desde la PC.
> El 16/11 ejecutó 24 órdenes con llegada confirmada (error ≤ 0,016° por orden). Desde el 17/11 todo
> el control se hace dentro de **RViz**: se escriben ángulos o una pose cartesiana (cinemática inversa
> propia) y el **gemelo digital** se mueve a la vez que el robot. [Cómo funciona](docs/conexion_abb/COMO_FUNCIONA.md)
> · [Bitácora del primer movimiento](docs/bitacora/2026-11-16_primer_movimiento_real.md)

## Qué se hizo en cada hito

| Hito | Resultado | Dónde está |
|---|---|---|
| **1 · Modelo y simulación** | URDF del IRB 120 con pinza, derivado de los parámetros DH; panel Qt con la pose de RViz frente a la función analítica (ΔE < 1e-6 m) | [`ros2_ws/src/irb120_hito1`](ros2_ws/src/irb120_hito1/README.md) · [docs](docs/hito1/README.md) |
| **2 · Cinemática y dinámica** | Pipeline en Python puro: Pieper (8 ramas) → validación FK → trayectoria LSPB → Jacobiano y singularidades → dinámica 1R. Notebook e informe IEEE | [`hito2/`](hito2/README.md) · [informe](docs/hito2/README.md) |
| **3 · Conexión con el robot real** | Lectura de los ángulos del controlador IRC5 por RWS, gemelo digital en RViz y validación de la FK propia contra el controlador | [`ros2_ws/src/irb120_conexion`](ros2_ws/src/irb120_conexion/README.md) · [docs](docs/conexion_abb/README.md) |
| **4 · Control del robot real** | Envío de objetivos articulares por RWS a un servidor RAPID propio (`LabJointRws`), panel de control en RViz, IK de Pieper sobre poses cartesianas | [`ros2_ws/src/irb120_control`](ros2_ws/src/irb120_control/README.md) · [`irb120_rviz_panel`](ros2_ws/src/irb120_rviz_panel/README.md) |

## Mover el robot (o practicar sin él)

Requisitos: Ubuntu con ROS 2 Jazzy, Python 3 con `requests` y `numpy`. Todo se lanza con un único script:

```bash
cd ros2_ws
./brazo.sh compilar      # una vez: compila el panel de RViz
./brazo.sh simulado      # sin robot: RViz + panel con un robot ficticio
./brazo.sh enlace        # con el robot: cable, IP, ping y puerto RWS
./brazo.sh respaldar     # con el robot: copia los programas RAPID a git (solo lectura)
./brazo.sh panel         # con el robot: RViz + panel conectado al IRC5
./brazo.sh ayuda         # todos los comandos y los pasos del FlexPendant
```

Procedimiento completo en el laboratorio (FlexPendant, modos Manual/Auto, seguridad):
[MOVER_DESDE_PC.md](docs/conexion_abb/MOVER_DESDE_PC.md).

```text
 RViz (panel «IRB 120» + control 3D)
        │  JSON por tópicos ROS 2 (/irb120/panel/orden, /irb120/panel/estado)
        ▼
 Nodo Python irb120_panel_rws ── validación, IK de Pieper, división en tramos ≤ 5°
        │  HTTP (RWS 1.0, puerto 80) por Ethernet al puerto de servicio del IRC5
        ▼
 Módulo RAPID LabJointRws (ServidorPC) ── valida y ejecuta MoveAbsJ
        │  la postura real se lee de vuelta y se publica en ROS 2
        ▼
 Gemelo digital en RViz
```

## Organización de la carpeta

```text
proyecto/
├── README.md                     esta página
├── model_manifest.yaml           versiones, modelos, evidencias y pendientes (Gate 0)
├── ros2_ws/                      código ROS 2 y script brazo.sh
│   └── src/
│       ├── irb120_hito1/         Hito 1: URDF, mallas, simulación y panel Qt
│       ├── irb120_hito2/         Hito 2 como nodos ROS (versión secundaria)
│       ├── irb120_conexion/      Hito 3: lectura RWS, gemelo digital, validación FK
│       ├── irb120_control/       Hito 4: envío al robot (RWS + RAPID), panel en Python, EGM
│       └── irb120_rviz_panel/    Hito 4: panel «IRB 120» dentro de RViz (C++)
├── hito2/                        Hito 2: paquete irb120 (cinemática, dinámica), notebooks, figuras
├── scripts/                      utilidades de diagnóstico y CAD
├── docs/                         toda la documentación (índice en docs/README.md)
│   ├── conexion_abb/             conexión y control del robot real, evidencias
│   ├── bitacora/                 registro de las sesiones con el robot
│   ├── hito1/ · hito2/ · hitos_3_4/
│   └── organizacion/             historial de la organización de carpetas
├── entregables/                  lo entregado en cada hito (PDF, PPTX, notebook)
├── archivos que hay que presentar/   guías y rúbricas originales del docente
├── fotos/                        fotos del robot, FlexPendant y conexiones
├── referencias/                  bibliografía
└── archivo/                      versiones anteriores (solo consulta)
```

Notas de organización:
- `model_manifest.yaml` y `ros2_ws/` deben seguir juntos en esta carpeta: el código los usa para encontrar la raíz del proyecto.
- `hito2/` no se mueve: el control del robot importa su cinemática (`hito2/irb120`).
- Lo que genera la ejecución (`ros2_ws/build`, `install`, `log` y `salidas/`) no se versiona.

## Documentos clave

| Para… | Abrir |
|---|---|
| Entender conexiones, protocolos y cómo viaja un ángulo hasta el motor | [COMO_FUNCIONA.md](docs/conexion_abb/COMO_FUNCIONA.md) |
| Operar el robot en el laboratorio | [MOVER_DESDE_PC.md](docs/conexion_abb/MOVER_DESDE_PC.md) |
| Recuperar el programa si alguien lo borra del FlexPendant | [RESPALDO_Y_RESTAURACION.md](docs/conexion_abb/RESPALDO_Y_RESTAURACION.md) |
| Ver qué pasó en cada sesión con el robot | [Bitácora](docs/bitacora/README.md) |
| Requisitos y gates de los Hitos 3/4 | [docs/hitos_3_4](docs/hitos_3_4/README.md) |
| Fotos del equipo y qué demuestra cada una | [fotos](fotos/README.md) |
| Material del docente | [guías y rúbricas](<archivos que hay que presentar/README.md>) |
| Todo lo demás | [índice de documentación](docs/README.md) |

## Modelo y unidades

- Parámetros DH del IRB 120-3/0.6 según Bahani (2023); TCP a **150 mm** de la brida (`tool0`) sobre su eje z.
- La FK propia coincide con el modelo oficial de ROS-Industrial (`abb_irb120_support`) hasta 1e-15 y con el controlador real en la [validación en vivo](docs/conexion_abb/VALIDACION_FK_EN_VIVO.md).
- Ángulos en grados en RAPID y en los paneles; radianes en ROS 2. Poses en mm y roll-pitch-yaw (R = Rz·Ry·Rx) respecto a la base.

## Pruebas

```bash
cd ros2_ws && ./brazo.sh pruebas          # control y panel, sin robot ni red
cd hito2 && python3 -m pytest              # cinemática y dinámica del Hito 2
```
