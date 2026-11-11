# Proyecto ABB IRB 120 · IMT-342

Modelo cinemático, simulación ROS 2 e integración con el brazo ABB IRB120-3/0.6. La prioridad actual es completar la primera ejecución física J6 mediante RWS + RAPID. Actualización documental: **10 de noviembre de 2026**.

**[Bitácora del 10/11: avances, prueba fallida y pendientes](AVANCE_2026-11-10.md).** La recepción de ángulos y la transferencia del módulo se comprobaron, pero el movimiento físico no se consiguió. El monitor registró 584 muestras sin desplazamiento y el último modo confirmado fue AUTO. Se preparó un diagnóstico de solo lectura y una [secuencia para la próxima sesión](docs/conexion_abb/PROXIMA_SESION_J6.md).

## Empezar aquí

**Próxima sesión con el brazo (11/11):** [mover el IRB 120 desde la PC: FlexPendant paso a paso y órdenes](docs/conexion_abb/MOVER_DESDE_PC.md). Sustituye la prueba J6 de ±0,1°.

**ROS 2 organizado por nodos:** [estructura y arranque único](ros2_ws/README.md). El seguimiento físico en RViz fue reportado exitoso el 03/11 y la [comparación FK propia frente al controlador](docs/conexion_abb/VALIDACION_FK_EN_VIVO.md) cuenta con evidencia del 04/11. La prueba pendiente es la ejecución física J6 descrita en la bitácora actual.

**Prueba de comunicación preparada para el laboratorio (30/10):** [FlexPendant → robot → RViz y panel de ángulos](docs/conexion_abb/PRUEBA_COMUNICACION_EN_VIVO.md).

**Avance del 03/11:** lectura del ABB real publicada en ROS y contrastada con TF (28 muestras, error máximo `7.11e-15°`). Se añadió `--ignore-joint-state` para reproducir la consulta GET `ignore=1` que resolvió el HTTP 400 en la prueba del usuario. [Procedimiento actualizado y evidencia](docs/conexion_abb/PRUEBA_COMUNICACION_EN_VIVO.md). Las tablas del corte documental del 22/10 que siguen abajo son históricas.

| Necesito… | Abrir |
|---|---|
| Saber qué conocemos del brazo y cómo conectarlo | [Conexión ABB: decisión, requisitos y procedimiento](docs/conexion_abb/README.md) |
| Ver las fotos y qué demuestra cada una | [Catálogo de evidencia fotográfica](fotos/README.md) |
| Preparar la semana 12 y los Hitos 3/4 integrados | [Estado y plan Hitos 3/4](docs/hitos_3_4/README.md) |
| Trabajar en la entrega del Hito 2 | [Paquete y notebook vigentes](hito2/README.md) · [Informe IEEE](docs/hito2/informe_ieee/README.md) |
| Abrir el material del docente | [Guías, plantillas y rúbricas](<archivos que hay que presentar/README.md>) |
| Encontrar las entregas del equipo | [Índice de entregables](entregables/README.md) |
| Usar la simulación del Hito 1 | [Instrucciones ROS](docs/hito1/README.md) |
| Entender dónde se trasladaron los archivos | [Mapa y registro de organización](docs/organizacion/README.md) |

## Inventario histórico y pendientes al 22/10

| Elemento | Estado |
|---|---|
| Manipulador | IRB120-3/0.6, serie 120-101516; placa fotografiada |
| Opciones del controlador | **689-1 EGM, 616-1 PC Interface y 623-1 Multitasking** visibles en FlexPendant |
| Red de servicio | **192.168.125.1/24**, sin gateway; pantalla fotografiada |
| Puerto | Etiqueta **X2 Service 10/100** legible; no se realizó conexión desde Linux |
| RobotWare completo | **6.12.01.00**, transcrito por el usuario desde System properties el 22/10; lectura RWS pendiente |
| Controlador exacto y revisión | Pendientes de placa; IRC5 Compact es identificación visual provisional |
| Integración física | **No verificada**; diagnóstico de lectura preparado y probado offline |
| Driver ROS 2 | `PickNikRobotics/abb_ros2`, candidato condicionado a versión y adaptación al IRB 120 |
| Entorno Linux | Ubuntu 26.04.1 y Jazzy observados; compatibilidad del driver por comprobar |

La guía docente distingue G0 inventario, G1 lectura sin movimiento, G2 validación FK/IK/J, G3 movimiento con GO del laboratorio y G4 tarea repetible. El estado `Manual / Guard Stop / Stopped` corresponde al momento de las fotos. La captura de Backup and Restore muestra el menú, no un respaldo realizado.

## Carpetas

```text
proyecto/
├── README.md
├── model_manifest.yaml            # Versiones, modelos, evidencias y pendientes
├── hito2/                         # Código, notebook, figuras y resultados actuales
├── ros2_ws/                       # Paquetes ROS existentes
├── scripts/                       # Diagnóstico ABB y utilidades
├── docs/
│   ├── conexion_abb/              # Conexión, inventario y evidencias
│   ├── hito1/                     # Modelo y uso de la simulación
│   ├── hito2/                     # Informe IEEE y revisiones
│   ├── hitos_3_4/                 # Plan ECI-3/4
│   └── organizacion/              # Traslados y verificaciones
├── fotos/
│   ├── equipo/                    # Robot, placas y gabinete
│   ├── flexpendant/               # Opciones y pantallas
│   └── conexiones/                # Puertos y cableado
├── archivos que hay que presentar/
│   ├── hito_2/                    # Documentos originales del docente
│   └── actualizacion_semana_12/   # Guías y rúbrica de Hitos 3/4
├── entregables/                   # Índice del equipo y finales de Hito 1
├── referencias/                   # Bibliografía y repositorios
└── archivo/                       # Versiones y generación histórica
```

## Modelos y unidades

Hito 1 (ROS) y Hito 2 usan TCP a **0.150 m** de `tool0` (antes el paquete ROS usaba 0.100 m); en `irb120_hito1` la fuente única es `config/tcp.yaml`. Es un valor de modelo: el TCP físico sigue pendiente. Hay que alinear base, herramienta, orden, signos y offsets articulares antes de comparar contra el controlador. [Manifiesto](model_manifest.yaml).

El acuerdo entre DH y un URDF derivado del mismo DH comprueba implementaciones de la cadena, pero no aporta por sí mismo una fuente geométrica independiente del robot ni validación física ABB. Para el Hito 2, la verificación geométrica independiente de la FK se hace contra el **modelo oficial de ROS-Industrial** (`abb_irb120_support`): coinciden en pose completa hasta 1e-15 (ver `hito2/irb120/rosi_model.py`).

## Primera herramienta disponible

Desde la raíz, este comando guarda únicamente información de la PC:

```bash
python3 scripts/abb_lectura_rws.py --output docs/conexion_abb/evidencias/inventario_pc.json
```

La futura prueba contra el controlador se describe en la [guía de conexión](docs/conexion_abb/README.md), después de comprobar enlace Ethernet y acceso supervisado; contrastar RobotWare con la respuesta del controlador. El script no arranca RAPID, motores ni EGM. Sus ocho pruebas offline están registradas; no equivalen a una prueba sobre el brazo.

Los [documentos del docente](<archivos que hay que presentar/README.md>) son referencias. Las [versiones anteriores](archivo/README.md) son antecedentes. Los entornos virtuales y directorios de compilación permanecen en sus ubicaciones y están excluidos de Git.
