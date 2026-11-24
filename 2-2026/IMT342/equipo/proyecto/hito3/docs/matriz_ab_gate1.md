# Matriz de arquitecturas A/B y ensayo Gate 1

Basada en `w12_s02_matriz_ab__gate_1.tex`. Actualizada el 24/11/2026. Rutas relativas a `proyecto/`.

> Nomenclatura: igual que en `gate0_ficha.md`. **A = RWS + RAPID `LabJointRws`** (ruta elegida) y **B = EGM** (`abb_ros2`/`abb_libegm`). La plantilla oficial llama «Ruta A» al driver existente (RWS/EGM) y «Ruta B» al puente propio con RAPID; en esta tabla las columnas están nombradas según el proyecto, no según la plantilla.

Separación de canales (regla oficial): comando emitido desde ROS, transporte de red, estado generado por el controlador y movimiento físico son cosas distintas. Ni RViz, ni un eco de tópico, ni un `ping` prueban lectura de estado real.

## 1. Matriz comparativa (12 filas oficiales)

| # | Campo | Ruta A · RWS + RAPID `LabJointRws` | Ruta B · EGM (`abb_ros2` / `abb_libegm`) |
|---|---|---|---|
| 1 | Interfaz exacta candidata | RWS 1.0 (HTTP, Digest) en `192.168.125.1`; recursos `/rw/system`, `/rw/panel/*`, `/rw/rapid/*`, `/rw/motionsystem/mechunits/ROB_1/jointtarget`, escritura de PERS y `pcp set-pp-routine`. Programa RAPID `LabJointRws/ServidorPC`. | EGM (UDP + Protobuf) con `abb_libegm`, más RWS para configuración (`abb_rws_client`) y `ros2_control` (`abb_hardware_interface`). |
| 2 | Versiones admitidas por fuente documental | RWS 1.0 corresponde a RobotWare 6.x (la 7 usa RWS 2.0). El proyecto usa RW 6.12.01.00. Fuente: README de `abb_librws`. | `abb_libegm`: RobotWare ≥ 6.07.01 dentro de RW6, opción 689-1. `abb_ros2`: CI probada en Rolling, ramas `humble`, `iron`, `foxy`, `rolling`; no hay rama `jazzy`. |
| 3 | Prerrequisito local crítico | Opciones 616-1 PC Interface y 623-1 Multitasking; cuenta UAS con permisos de escritura; permiso RMMP (concedido por el operador) para escribir PERS en manual; mastership de RAPID. | Opción 689-1 EGM y su configuración en el controlador (dispositivo UDP, perfil EGM, señales); sesión EGM con parada segura; compilación de `abb_ros2` con dependencias fijadas. |
| 4 | Evidencia local actual del prerrequisito | 616-1 y 623-1 en la lista RWS (29/10). RMMP concedido el 16/11; escrituras PERS 204 en 16–19/11; módulo instalado y leído de vuelta (`instalar_20261117_*.json`, `instalar_20261118_*.json`). | 689-1 en la lista RWS (29/10) y RW cumple el mínimo documental. **Sin evidencia** de configuración EGM, de compilación ni de sesión EGM. |
| 5 | Canal de comando (conceptual) | PC escribe `pcTarget` (6 ángulos absolutos, 3 decimales), lo lee de vuelta y recién entonces sube `pcSeq`; el robot valida y ejecuta `MoveAbsJ` (v5: también `MoveL`). Una orden a la vez. | Consignas articulares/cartesianas por UDP cada 4 ms; el controlador sigue la trayectoria de EGM. Control continuo. |
| 6 | Canal de estado (origen, unidades, orden, timestamp) | `jointtarget` por RWS: `rax_1…rax_6` en grados, orden J1…J6; `rbCodigo`/`rbSeq` por PERS; sondeo de 0,3 s; marca de tiempo del reloj de la PC (UTC) en cada evento del registro. Sin sincronía de reloj con el controlador. | Retroalimentación EGM (posición medida) por UDP; unidades y orden según el protocolo; **no probado localmente**. |
| 7 | Prueba read-only propuesta | G1-A (enlace, `ping`, GET sin credenciales → 401) y G1-B (GET autenticado de sistema, modo, estado y `jointtarget`), contraste con FlexPendant, repetición estacionaria. | Lectura de EGM sin enviar consignas (modo solo recepción); requiere configuración previa del controlador. |
| 8 | Autorización de laboratorio necesaria | Operador autorizado y responsable del laboratorio para el acceso; GO específico para cualquier movimiento (Gate 3). | Igual, más cambio de configuración del controlador (requiere responsable de laboratorio). |
| 9 | Observable exacto y archivo de log | JSON/CSV con `jointtarget` y marca de tiempo: `evidencias/g1_rws_2026-10-29_sanitizado.json`, `g1b_contraste_flexpendant_2026-10-29.json`, `verificacion_rws_ros_tf_2026-11-03.csv`; en movimiento, `rws_mover/*.jsonl`. | Registro de paquetes EGM con secuencia y tiempo del controlador: **no existe**. |
| 10 | Criterio PASS / FAIL / BLOCKED | PASS = respuesta rastreable originada en el controlador, reproducible, sin movimiento. Cumplido en lectura (sección 2). | BLOCKED: falta configuración del controlador y compilación del driver; no se atribuye falla técnica. |
| 11 | Condiciones de aborto y NO-GO | Identidad inconsistente, 401/403 inesperado, modo distinto del autorizado, `rbCodigo` negativo, enlace perdido, instrucción del supervisor. Parar: habilitador, Stop o paro de emergencia (Ctrl+C en la PC **no** detiene el robot). | Las mismas, más pérdida de paquetes EGM y desvío respecto de la consigna. |
| 12 | Próxima acción y responsable | Obtener GO firmado y completar `checklist_seguridad.md`; probar v5 (primero un tramo articular corto a 10–20 %). Responsable: por asignar. | Decidir con el docente si EGM es exigible; si lo es, configurar EGM en el controlador y compilar `abb_ros2` sin hardware. Responsable: por asignar. |

## 2. Ensayo Gate 1 (8 puntos oficiales) y resultado real

**Pregunta de Gate 1.** ¿Puede la interfaz obtener, de forma autorizada y repetible, una señal real de estado o identidad del controlador ABB sin ordenar movimiento?

**Ensayos realizados** (ruta A, todos de solo lectura):

| Ensayo | Fecha | Evidencia |
|---|---|---|
| G1-A: enlace y respuesta RWS sin credenciales | 29/10/2026 | `docs/conexion_abb/evidencias/g1a_enlace_2026-10-29.json` |
| G1-B: lectura RWS autenticada y contraste con FlexPendant | 29/10/2026 | `g1_rws_2026-10-29_sanitizado.json`, `g1b_contraste_flexpendant_2026-10-29.json` |
| RWS → ROS → TF, robot quieto, sin comandos | 03/11/2026 | `verificacion_rws_ros_tf_2026-11-03.json` y `.csv` |
| Lectura repetida en la comparación FK (1365 muestras) | 04/11/2026 | `fk_real_2026-11-04_224412Z_resumen.json`, `_muestras.jsonl` |

| # | Punto del protocolo | Qué se hizo y qué se observó | Resultado | Evidencia |
|---|---|---|---|---|
| 1 | Objetivo limitado: lectura de identidad/estado en solo lectura, sin trayectoria ni motores | Solo GET sobre `/rw/system`, `/rw/panel/ctrlstate`, `/rw/panel/opmode`, `/rw/rapid/execution`, `/rw/motionsystem/mechunits` y `…/ROB_1/jointtarget`. `mode: read_only`, `movement_authorized: false`. | PASS | `g1_rws_2026-10-29_sanitizado.json` |
| 2 | Precondiciones: protocolo soportado, red autorizada, operador habilitado presente, modo conforme, separación de interfaces de escritura | Protocolo soportado y red punto a punto: sí. **No consta** operador/supervisor presente: el JSON del contraste dice que el usuario indicó que no había operador presente en el FlexPendant el 29/10. No hay registro de autorización institucional. Estado del controlador: AUTO, motores apagados, RAPID detenido. | BLOCKED en la parte de autorización/supervisión (la lectura se ejecutó igual; esta precondición no está documentada y debe registrarse) | `g1b_contraste_flexpendant_2026-10-29.json`; `gate0_ficha.md` ítems 11, 15 |
| 3 | Entrada: solicitud definida por la documentación de la versión (sin inventar llamadas de API) | Peticiones GET de RWS 1.0 documentadas por ABB; `/rw/system` y `…/jointtarget` con `?json=1`. | PASS | `docs/conexion_abb/README.md` (fuentes ABB); `g1_rws_2026-10-29_sanitizado.json` |
| 4 | Observables: fuente, identidad, valor numérico y timestamp, consistencia, log, modo y unidades | Identidad `120-101516`, RobotWare 6.12.01.00, `ROB_1` activo; `jointtarget` J1…J6 = 55,3011; 16,9464; 0,6433; −45,4282; −63,6680; 9,1318 grados; modo AUTO, `motoroff`, `stopped`; marca `observed_at_utc` 2026-10-29T21:35:16Z. | PASS | `g1_rws_2026-10-29_sanitizado.json` |
| 5 | Criterio PASS: respuesta rastreable del controlador físico, reproducible, sin movimiento | Contraste con la pantalla Jogging (foto del FlexPendant): diferencia máxima 0,0036° (resolución de pantalla 0,01°; tolerancia propuesta 0,1°). Repetición estacionaria el 03/11: 28 muestras sincronizadas RWS/ROS/TF, diferencia máxima 7,1e-15°, rango por eje 0,0°, `motion_commands_sent: false`. | PASS (lectura de estado validada; no implica control de trayectoria) | `g1b_contraste_flexpendant_2026-10-29.json`; `verificacion_rws_ros_tf_2026-11-03.csv` |
| 6 | Criterio FAIL: intento autorizado que no produce el observable | El único resultado negativo fue el GET sin credenciales (HTTP 401), esperado y registrado; no es un FAIL del ensayo. No hubo intento autorizado sin observable en G1. | Sin FAIL | `g1a_enlace_2026-10-29.json` |
| 7 | Criterio BLOCKED: prerrequisito o autorización no disponible | Al cierre de G1-A (29/10) la lectura quedó BLOCKED por falta de usuario y contraseña UAS del operador; se levantó el mismo día al conseguir la cuenta. | BLOCKED (histórico, resuelto el 29/10) | `g1a_enlace_2026-10-29.json` (`gate: G1-A completado; G1-B pendiente de credenciales UAS`) |
| 8 | Condición de aborto: inconsistencia de identidad, error de permisos, comportamiento inesperado o instrucción del supervisor | Ninguna se activó. No hay protocolo local escrito contra el cual contrastarlo. | Sin disparo; protocolo local pendiente | `gate0_ficha.md` ítem 12 |

**Alcance de la conclusión.** Lectura de estado real validada por RWS (S1) y retransmitida por ROS/TF (S2) con el robot quieto. **No** se concluye control de trayectoria ni autorización de movimiento. Dos limitaciones que conviene decir en la defensa: el contraste con el FlexPendant del 29/10 se hizo con una foto de la pantalla y sin operador presente; y el seguimiento del gemelo en RViz del 03/11 es un reporte del usuario, no una observación instrumentada (`model_manifest.yaml`: `rviz_physical_following`).

## 3. Lo que falta para cerrar Gate 1 sin reservas

1. Registrar el operador/supervisor y la autorización de acceso de una sesión de solo lectura (ítems 11 y 15 de la ficha Gate 0).
2. Repetir el contraste con el FlexPendant con un operador presente y firmar el registro (`checklist_seguridad.md`).
3. Si se decide perseguir la ruta B, definir y ejecutar un G1 de EGM en solo recepción.
