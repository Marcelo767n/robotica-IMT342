# Hitos 3 y 4 integrados · ECI-3/4

**Corte del 10/11:** [bitácora del avance y resultado de la sesión](../../AVANCE_2026-11-10.md). Se verificaron recepción RWS y transferencia del módulo J6, pero el intento no consiguió movimiento físico. Sigue pendiente G3. [Procedimiento para la próxima visita](../conexion_abb/PROXIMA_SESION_J6.md).

**Actualización 04/11:** enlace RWS y publicación física ROS/TF comprobados; el usuario reportó exitoso el seguimiento visual del brazo con RViz. La [comparación FK propia/pose ABB](../conexion_abb/VALIDACION_FK_EN_VIVO.md) ya tiene [evidencia física registrada](../conexion_abb/evidencias/fk_real_2026-11-04_224412Z_informe.md): las últimas 100 muestras estacionarias pasan el criterio estricto. Se conservan 25 muestras previas FUERA; falta completar la campaña con variación de J4–J6. El código está organizado en [nodos ROS 2](../../ros2_ws/README.md).

Prioridad actual: cerrar la validación física FK y preparar el control EGM por etapas, primero articular y después mediante IK propia y visión. El material de semana 12 se conserva como antecedente de requisitos e inventario. La nueva fecha exacta del Hito 2 no se ha confirmado en estos documentos.

## Documentos de trabajo

- [Requisitos ECI-3/4 resumidos desde W12-S01](REQUISITOS_ECI34.md): rúbrica, gates y entregables.
- [Plan de control EGM, IK propia y visión](PLAN_CONTROL_EGM_IK_VISION.md): secuencia de pruebas, criterios y preparación antes del primer comando físico.
- [Comandos de laboratorio](../conexion_abb/COMANDOS_LABORATORIO.md) y [control articular desde RViz](../../ros2_ws/src/irb120_control/README.md): demo y recepción EGM sin envío antes del control físico.
- [Investigación y procedimiento de conexión](../conexion_abb/README.md).
- [Plan semanal, hipótesis, rúbrica y pruebas](../conexion_abb/plan_semana_12.md).
- [Inventario Gate 0](../conexion_abb/gate0_inventario.csv).
- [Manifiesto](../../model_manifest.yaml) y [fotos](../../fotos/README.md).
- [Casos Gate 2 predefinidos](../conexion_abb/validation_cases.csv).
- [Material original W12-S01](<../../archivos que hay que presentar/actualizacion_semana_12/>).

## Estado de los gates

| Gate | Evidencia disponible | Pendiente |
|---|---|---|
| G0 · inventario | Robot y red fotografiados; RobotWare 6.12.01.00 y opciones contrastados por RWS real | Revisión exacta del controlador, backup, operador/protocolo y compatibilidad del driver |
| G1 · lectura | Ethernet y RWS reales; contraste de ejes con FlexPendant; ROS/TF estacionario instrumentado; seguimiento RViz reportado exitoso por el usuario | Mantener comprobación de estado/vigencia y documentar cada sesión; EGM todavía no probado |
| G2 · modelos | FK/IK/J propios, referencia ROS-Industrial y comparación física FK/ABB en tool0: 100 muestras finales estacionarias dentro del criterio | Investigar 25 muestras FUERA, ampliar posturas especialmente J4–J6, completar validación IK/J y TCP físico para la tarea |
| G3 · movimiento | RViz → supervisor → EGM UDP simulado: 24 pruebas, ensayos individuales J1–J6, displays/TF y perfiles simulados 5°/10° a 0.5°/s y 0.5°/s²; sin movimiento físico desde PC | Completar G2 y configuración/handshake/parada EGM en controlador, límites reales y GO del laboratorio |
| G4 · tarea | Sin implementación demostrada | Tablero repetible después de G3; visión opcional |

La presencia de EGM confirma esa opción instalada. No confirma que la versión del protocolo sea compatible ni que se haya establecido una sesión.
