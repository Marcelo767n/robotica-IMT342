# Proyecto ABB IRB 120 · IMT-342 Robótica

Modelo cinemático, simulación en ROS 2 y control del brazo **ABB IRB 120** real desde una PC Linux.
Universidad Católica Boliviana, 2-2026. Equipo: Dayana Andrade, Mirko Ayala y Marcelo Navarro.

> **Estado final (26/11/2026).** El IRB 120 físico se controla desde la PC dentro de **RViz**: el ángulo o la pose
> pedidos pasan por la cinemática inversa propia (Pieper), se verifican con la FK propia y con el controlador, y se
> envían por RWS a un servidor RAPID propio (`LabJointRws`); el **gemelo digital** sigue al robot. La FK propia coincide
> con la pose que informa el IRC5 con un error de posición mediano de 7,5e-8 m. Entre el 16 y el 19/11 se registraron
> **265 órdenes reales, 264 con llegada confirmada** (error de llegada máximo 0,186° y mediano ≤ 0,010° por sesión). El panel
> «IRB 120» de RViz ofrece las pestañas «Mover» y «Trayectorias» (trayectorias guardadas, movimientos vistosos,
> bucle continuo, vista previa y grabación de puntos). La validación del Hito 3 es reproducible sin robot
> (`python3 -m hito3.validacion`, 34 casos). Limitaciones al final de esta página: sin GO de laboratorio firmado,
> RAPID v5 sin probar en el IRC5, celda PLC solo simulada.
> [Cómo revisar](COMO_REVISAR.md) · [Cómo funciona](docs/conexion_abb/COMO_FUNCIONA.md) · [Mapa ROS 2](docs/MAPA_ROS2.md)

## Qué se hizo en cada hito

| Hito | Resultado | Dónde está |
|---|---|---|
| **1 · Modelo y simulación** | URDF del IRB 120 con pinza, derivado de los parámetros DH; panel Qt con la pose de RViz frente a la función analítica (ΔE < 1e-6 m) | [`ros2_ws/src/irb120_hito1`](ros2_ws/src/irb120_hito1/README.md) · [docs](docs/hito1/README.md) · [entregables](entregables/hito1/) |
| **2 · Cinemática y dinámica** | Pipeline en Python puro: Pieper (8 ramas) → validación FK → trayectoria LSPB → Jacobiano y singularidades → dinámica 1R. Notebook, informe IEEE y presentación interactiva | [`hito2/`](hito2/README.md) · [informe](docs/hito2/README.md) · [entregables](entregables/hito2/README.md) |
| **3 y 4 · Robot real** (unificados por el docente como ECI-3/4) | Lectura RWS del IRC5 y gemelo digital en RViz; validación de la FK propia contra el controlador; control real desde RViz por RWS + módulo RAPID `LabJointRws` (v4 probada en el robot; v5 con una orden por tramo y `MoveL`, instalable pero sin probar); panel de RViz con «Mover» y «Trayectorias»; planificador con elección articular/lineal y reglas del Hito 2 más estrictas; Estudio CustomTkinter (análisis, gráficas, matemática en LaTeX); validación FK/IK/J con niveles de evidencia S0–S3 | [`ros2_ws/src/irb120_conexion`](ros2_ws/src/irb120_conexion/README.md) · [`irb120_control`](ros2_ws/src/irb120_control/README.md) · [`irb120_rviz_panel`](ros2_ws/src/irb120_rviz_panel/README.md) · [`hito3/`](hito3/docs/README.md) · [docs](docs/hitos_3_4/README.md) |
| Extensión (no integrada) | Celda con PLC Siemens S7-1200 como cliente de órdenes: nodos ROS 2 independientes y fuentes SCL; probada solo con un PLC simulado | [PLC_S7_1200.md](docs/PLC_S7_1200.md) · [`plc_s7_1200/`](plc_s7_1200/README.md) |

## Entregables

| Hito | Informe | Presentación | Notebook / datos |
|---|---|---|---|
| 1 | [Manual PDF](entregables/hito1/pdf/Guia_Practica_Hito1_IRB120_6_Juntas_CORREGIDA.pdf) | [Defensa PPTX](entregables/hito1/presentation/Defensa_Hito1_IRB120_6_Juntas_FINAL.pptx) | [`ros2_ws/src/irb120_hito1`](ros2_ws/src/irb120_hito1/README.md) |
| 2 | [Informe IEEE](entregables/hito2/informe_hito2_ieee.pdf) · [fuente](docs/hito2/informe_ieee/README.md) | [Presentación interactiva](entregables/hito2/Hito2_en_vivo.html) | [Notebook todo en uno](entregables/hito2/Hito2_IRB120_todo_en_uno.ipynb) · [guía de la entrega](entregables/hito2/README.md) |
| 3 y 4 | [informe_hito3_4.pdf](entregables/hito3_4/informe_hito3_4.pdf) · [fuente LaTeX](hito3/informe/informe_hito3.tex) | Por preparar (demo en vivo con `brazo sesion`) | Evidencia y validación en [`hito3/`](hito3/docs/README.md) (resultados, manifiestos, 34 casos) |

Índice de la carpeta de entregas: [entregables/README.md](entregables/README.md).

## Cómo ejecutar

Requisitos: Ubuntu con **ROS 2 Jazzy**, entorno Python 3.12 en `~/ros_py312`, `numpy` y `requests`, **customtkinter** (Estudio) y una distribución **TeX** (matemática en LaTeX; hay respaldo automático si falta). Todo se lanza con un único comando; `brazo` es un atajo a `ros2_ws/brazo.sh`.

```bash
cd ros2_ws
./brazo.sh compilar              # una sola vez: compila el panel «IRB 120» de RViz
brazo sesion                     # con el robot: TODO en un comando (enlace, AUTO guiado, RViz, panel y Estudio)
brazo sesion --simulado          # la misma sesión sin robot (robot ficticio): para revisar sin laboratorio
brazo sesion --v4                # con el robot y el módulo de respaldo v4 (ya probado: solo articular, ≤ 40° por orden)
brazo pruebas                    # ≈300 pruebas offline, sin robot ni red
brazo nodos                      # grafo ROS 2 en vivo: nodos, tópicos y quién publica o escucha
brazo demo                       # todo sin robot: RViz + panel simulado + Estudio (--plc añade la celda PLC)
brazo ayuda                      # todos los comandos y los pasos del FlexPendant
```

Otros comandos útiles: `brazo enlace` (cable, IP, ping y puerto RWS), `brazo estado`, `brazo respaldar` (copia los programas RAPID a git, solo lectura), `brazo estudio`, `brazo punto X Y Z R P Y`. Procedimiento completo en el laboratorio (FlexPendant, modos Manual/Auto, seguridad): [MOVER_DESDE_PC.md](docs/conexion_abb/MOVER_DESDE_PC.md).

## Arquitectura

```text
 RViz ── panel «IRB 120» (pestañas Mover / Trayectorias) + control 3D de la pose
   │      JSON por tópicos ROS 2: /irb120/panel/orden  →  ·  ← /irb120/panel/estado
   ▼
 Nodo irb120_panel_rws (Python) ── validación, IK de Pieper, verificación IK→FK y contra el controlador,
   │                               planificador (articular/lineal), reglas del Hito 2, ejecución por tramos
   │   ▲  buzón de puntos: RViz («Añadir a la trayectoria»), brazo punto, tópico de visión /irb120/trayectoria/punto_externo
   │   └─ Estudio CustomTkinter (HTTP local 127.0.0.1): análisis, editor, gráficas, matemática LaTeX
   │   └─ celda PLC (opcional, simulada): irb120_plc_s7 ↔ irb120_celda (TCP, telegramas 40/68 B)
   ▼  HTTP (RWS 1.0, puerto 80) por Ethernet al puerto de servicio del IRC5
 Módulo RAPID LabJointRws (ServidorPC) ── valida y ejecuta MoveAbsJ (y MoveL en la v5)
   │  la postura real se lee de vuelta cada 0,3 s
   ▼
 Gemelo digital en RViz: modelo blanco = medido, modelo naranja = objetivo / vista previa
```

Mapa completo de nodos y tópicos: [docs/MAPA_ROS2.md](docs/MAPA_ROS2.md) (imagen: [grafo_ros2.svg](docs/grafo_ros2.svg)). Contrato entre módulos de trayectorias: [ARQUITECTURA_TRAYECTORIAS.md](docs/ARQUITECTURA_TRAYECTORIAS.md).

## Organización de la carpeta

```text
proyecto/
├── README.md · COMO_REVISAR.md   portada y guía corta para el docente
├── model_manifest.yaml           versiones, modelos, evidencias y pendientes (Gate 0)
├── ros2_ws/                      código ROS 2 y script brazo.sh
│   └── src/
│       ├── irb120_hito1/         Hito 1: URDF, mallas, simulación y panel Qt
│       ├── irb120_hito2/         Hito 2 como nodos ROS (versión secundaria)
│       ├── irb120_conexion/      lectura RWS, gemelo digital, validación FK
│       ├── irb120_control/       envío al robot (RWS + RAPID), panel Python, trayectorias, Estudio, PLC, visión
│       └── irb120_rviz_panel/    panel «IRB 120» dentro de RViz (C++, pestañas Mover y Trayectorias)
├── hito2/                        Hito 2: paquete irb120 (cinemática, dinámica), notebooks, presentación
├── hito3/                        Hitos 3/4: validación FK/IK/J (validacion/), resultados, datos, manifiestos,
│                                 pruebas, documentación de evidencia (docs/) e informe (informe/)
├── plc_s7_1200/                  fuentes SCL/UDT para TIA Portal (extensión, sin compilar)
├── salidas/                      lo que genera la ejecución; trayectorias/ guarda las trayectorias (NN_nombre.json)
├── scripts/                      utilidades de diagnóstico y CAD
├── docs/                         documentación (índice en docs/README.md)
│   ├── conexion_abb/             conexión y control del robot real, evidencias
│   ├── bitacora/                 registro de las sesiones con el robot
│   ├── hito1/ · hito2/ · hitos_3_4/
│   └── organizacion/             historial de la organización de carpetas (histórico)
├── entregables/                  lo entregado en cada hito (hito1/, hito2/, hito3_4/)
├── material_docente/             guías, rúbricas y criterios publicados por el docente (hito_2, semana 12, semana 14)
├── fotos/                        fotos del robot, FlexPendant y conexiones
├── referencias/                  bibliografía
└── archivo/                      versiones anteriores (solo consulta)
```

**No mover:**
- `model_manifest.yaml` y `ros2_ws/` deben seguir juntos en esta carpeta: el código los usa para encontrar la raíz del proyecto.
- `hito2/`: el control del robot importa su cinemática (`hito2/irb120`), y `hito3/` la reutiliza.
- `docs/conexion_abb/evidencias/`: lo citan los informes y los manifiestos de `hito3/`.
- `salidas/trayectorias/`: es donde el panel y el Estudio leen y guardan las trayectorias.
- Lo generado por la ejecución (`ros2_ws/build`, `install`, `log` y `salidas/` salvo `trayectorias/`) no se versiona.

## Documentos clave

| Para… | Abrir |
|---|---|
| Revisar el proyecto en orden | [COMO_REVISAR.md](COMO_REVISAR.md) |
| Informe de los Hitos 3/4 | [informe_hito3_4.pdf](entregables/hito3_4/informe_hito3_4.pdf) · [fuente](hito3/informe/informe_hito3.tex) |
| Estado, decisiones y objetivos | [CONTEXTO_Y_OBJETIVOS.md](docs/CONTEXTO_Y_OBJETIVOS.md) |
| Entender conexiones, protocolos y cómo viaja un ángulo hasta el motor | [COMO_FUNCIONA.md](docs/conexion_abb/COMO_FUNCIONA.md) |
| Mapa de nodos y tópicos ROS 2 | [MAPA_ROS2.md](docs/MAPA_ROS2.md) |
| Operar el robot en el laboratorio | [MOVER_DESDE_PC.md](docs/conexion_abb/MOVER_DESDE_PC.md) |
| Recuperar el programa si alguien lo borra del FlexPendant | [RESPALDO_Y_RESTAURACION.md](docs/conexion_abb/RESPALDO_Y_RESTAURACION.md) |
| Evidencia y validación del Hito 3 | [hito3/docs](hito3/docs/README.md) · [autoevaluación frente a la rúbrica](hito3/docs/rubrica_autoevaluacion.md) |
| Ver qué pasó en cada sesión con el robot | [Bitácora](docs/bitacora/README.md) |
| Requisitos y gates de los Hitos 3/4 | [docs/hitos_3_4](docs/hitos_3_4/README.md) |
| Fotos del equipo y qué demuestra cada una | [fotos](fotos/README.md) |
| Material del docente | [guías, rúbricas y criterios](material_docente/README.md) |
| Todo lo demás | [índice de documentación](docs/README.md) |

## Modelo y unidades

- Parámetros DH del IRB 120-3/0.6 según Bahani (2023); TCP a **150 mm** de la brida (`tool0`) sobre su eje z.
- La FK propia coincide con el modelo oficial de ROS-Industrial (`abb_irb120_support`) hasta 1e-15 y con el controlador real en la [validación en vivo](docs/conexion_abb/VALIDACION_FK_EN_VIVO.md).
- Ángulos en grados en RAPID y en los paneles; radianes en ROS 2. Poses en mm y roll-pitch-yaw (R = Rz·Ry·Rx) respecto a la base.

## Pruebas

```bash
cd ros2_ws && ./brazo.sh pruebas          # control, panel, trayectorias, Estudio y celda; sin robot ni red
cd hito2 && python3 -m pytest              # cinemática y dinámica del Hito 2
python3 -m hito3.validacion                # validación FK/IK/J del Hito 3 (desde esta carpeta)
```

## Estado y limitaciones

- **Sin GO/NO-GO firmado.** Ninguna sesión con el robot tiene la firma del responsable del laboratorio; el movimiento en AUTO sin habilitador no cuenta con aceptación escrita. El nivel de evidencia sostenible es S3 técnico por registros, no S3 autorizado ([niveles](hito3/docs/niveles_evidencia.md)).
- **Tolerancias pendientes de aprobación** por el docente (FK/IK/J); la comparación física cubre sobre todo J1–J3 y quedan 25 muestras FUERA sin explicar.
- **TCP físico sin medir** (`tcp_verified_on_robot: false`): se usa 150 mm por decisión de diseño.
- **RAPID v5 / `MoveL` sin probar en el IRC5**: el módulo se instala, pero su sintaxis no pudo compilarse sin el controlador. Lo probado en el robot es la v4 (`brazo sesion --v4`).
- **Celda PLC solo simulada**: probada contra un PLC simulado; el FB SCL no se ha compilado en TIA Portal ni se conectó al PLC real. Queda como trabajo futuro.
- La ruta RWS + RAPID ejecuta una orden a la vez; no es control en tiempo real. EGM y `ros2_control` no se probaron.
- Los registros `jsonl` de las sesiones no están versionados; las bitácoras del 18 y 19/11 se reconstruyeron de ellos.
