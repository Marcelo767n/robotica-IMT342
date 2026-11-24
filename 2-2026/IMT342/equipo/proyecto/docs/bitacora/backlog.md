# Backlog hacia la próxima sesión de laboratorio

Preparado el 24/11/2026. Máximo tres tareas prioritarias por equipo, según la plantilla `w12_s02_bitacora_backlog_w13.tex`; el resto va como cola. **Todos los responsables y suplentes están «por asignar»**: los debe decidir el equipo. Criterio PASS/FAIL/BLOCKED según la plantilla; hoy ninguna tarea se ha ejecutado.

## Tareas prioritarias

| # | Hipótesis técnica a someter a prueba | Responsable y suplente | Dependencia / permiso | Procedimiento permitido | Evidencia verificable | Criterio | Incertidumbre remanente | Siguiente decisión según resultado |
|---|---|---|---|---|---|---|---|---|
| 1 | El laboratorio autoriza por escrito el trabajo en AUTO sin habilitador y la sesión tiene GO. | por asignar / por asignar | Responsable del laboratorio y operador autorizado | Entregar `hito3/docs/checklist_seguridad.md` (sección 5) y recibirlo firmado; preguntar de forma expresa por AUTO sin habilitador y velocidad máxima | PDF/escaneo firmado en el repositorio; nombre del operador | PASS: firma GO con alcance. FAIL: NO-GO o no autoriza AUTO. BLOCKED: sin acceso | Si el laboratorio exige manual reducido con habilitador | Si NO-GO: solo trabajo offline; si limita a manual: usar `./brazo.sh instalar` (manual) |
| 2 | La v5 compila en el IRC5 y un tramo articular corto (10–20 %) llega con error similar al de la v4 (≤ 0,07°). | por asignar / por asignar | Tarea 1 en PASS; Stop + Motors Off para instalar | `./brazo.sh sesion`; *Comprobar programa* en el FlexPendant; un tramo articular corto; luego un `MoveL` corto desde el Estudio; registrar con `opmode` | `jsonl` copiados a carpeta versionada, foto/video fechado, informe de *Comprobar programa* | PASS: sin errores de sintaxis y llegada con código 2 en ambos tipos. FAIL: error de compilación o `rbCodigo` negativo | `ConfL \Off` y orientación tras `MoveL`; duración real | Si FAIL: restaurar la v4 desde el respaldo (procedimiento en `docs/conexion_abb/RESPALDO_Y_RESTAURACION.md`; la v4 está en `salidas/control_articular/rws_mover/LabJointRws_auto.mod`) y corregir offline |
| 3 | Con GO y observador, el movimiento queda **observado de forma independiente** (video fechado) y los logs guardan modo y estado. | por asignar / por asignar | Tarea 1; que el código registre `opmode`/`ctrlstate` (mejora pendiente) | Grabar video de una tanda; anotar quién está en el FlexPendant; comparar con el `jsonl` | Video, `jsonl` con `opmode`, bitácora de la sesión | PASS: video coincide con las órdenes registradas. BLOCKED: sin permiso de grabar | Que el laboratorio no permita grabar | Si BLOCKED: acta firmada del operador describiendo el movimiento |

## Cola (no urgente, por orden de impacto en la rúbrica)

| # | Tarea | Dominio rúbrica | Dependencia |
|---|---|---|---|
| 4 | Registrar `opmode`, `ctrlstate` y el valor leído de `pcTarget` en cada orden del `jsonl` | 4 | Ninguna (código) |
| 5 | Copiar los `jsonl` (sanitizados) y los hashes a una carpeta versionada; la carpeta actual está en `.gitignore` | 4 | Ninguna |
| 6 | Averiguar qué pasó con la orden 59 del 18/11 (sin resultado) | 4 | `./brazo.sh eventos` con el robot |
| 7 | Probar «detener y reanudar RAPID» a propósito para confirmar la corrección del 403 | 3 | Tarea 1 |
| 8 | Leer la placa del gabinete y System Info; registrar el modelo/revisión del controlador (Gate 0, ítem 2) | 1 | Operador |
| 9 | Pedir el procedimiento local, el manual de la versión y el antecedente del proyecto de ajedrez (Gate 0, ítems 12 y 14) | 1 | Docente / laboratorio |
| 10 | Medir el `tooldata` real por RWS y comparar con el TCP de 0,150 m | 2 | Operador |
| 11 | Ampliar la validación FK a posturas que muevan J4–J6 y explicar las 25 muestras FUERA | 2 | Ver `hito3/resultados` |
| 12 | Pedir al docente la aprobación de las tolerancias de FK/IK/J | 2 | Docente |
| 13 | Compilar el bloque SCL en TIA Portal y probar el telegrama con un PLC (real o PLCSIM) | 3 | Licencia/PLC |
| 14 | Si el docente exige EGM: configurar EGM en el controlador y compilar `abb_ros2` sin hardware | 1, 3 | Docente / operador |
| 15 | Completar la matriz RACI (responsables y suplentes) y preparar la defensa individual | 5 | Equipo |
| 16 | Rellenar el manifiesto de cada experimento con `hito3/docs/manifiesto_experimento_plantilla.yaml` | 2, 4 | Ninguna |

## Exit ticket (preguntas individuales para ensayar)

1. Dato concreto del controlador ya verificado con fuente, o el bloqueo exacto y quién lo autoriza.
2. Una prueba de comunicación sin movimiento y su observable que distingue estado real de simulación.
3. Una condición NO-GO vigente hoy.
4. Una razón geométrica por la que dos FK correctas pueden diferir (base `{B}`, TCP).
