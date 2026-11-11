# Prueba puntual de J6 con Linux, RWS y RAPID

Actualizado: 10/11/2026. Esta ruta usa HTTP Digest/RWS para escribir `pcTarget` y RAPID para ejecutar localmente. **No usa EGM ni los menús de control de RViz.** RViz puede seguir mostrando los ángulos por la ruta de lectura, pero no inicia esta prueba.

**Cierre de la sesión: prueba de movimiento no conseguida.** El monitor registró 584 muestras sin cambio articular durante aproximadamente 120 s. El último modo confirmado fue AUTO y no quedó comprobada la ejecución local en manual reducido. Ver el [diagnóstico y procedimiento corregido](CIERRE_PRUEBA_J6_2026-11-10.md). El objetivo preparado podría seguir pendiente: su estado al cierre no se leyó. No reutilizarlo en otra sesión.

**Retomar:** [próxima sesión paso a paso y plan de nueve días](PROXIMA_SESION_J6.md). Se añadió `./iniciar.sh rws_j6 diagnosticar`, de solo lectura; no cambia el módulo ni certifica ejecución o permisos locales. `--informe` permite practicar con una inspección histórica sin red.

## Estado comprobado

- Controlador real `120-101516`, RobotWare `6.12.01.00`, dirección `192.168.125.1`, tarea `T_ROB1`.
- `comprobar_recepcion`: dos ensayos PC→ABB con los mismos seis ángulos medidos, lectura de vuelta con error cero, vaciado de `pcTarget` y sin desplazamiento observado. Estado final `motoroff / AUTO / stopped`.
- El operador comunicó revisión de Guard Stop, herramienta/cables y autorización del responsable para la sesión con operador presente. Esto no equivale a una autorización permanente de sesiones futuras.
- El módulo original ya compilado usaba `MoveAbsJ ...,v5,...`. `v5` no significa 5°/s: su componente de orientación es 500°/s. Se conservó su respaldo y se creó una versión exclusiva para J6.
- La transferencia Linux del 10/11 a las 21:47 UTC fue aceptada (HTTP 200); la lectura posterior coincide con el candidato. `Module1` conserva su huella, la lista de módulos no cambió, `pcTarget` está vacío y los seis ángulos no cambiaron. El informe original marcó fallo al liberar mastership: HTTP 403, «The resource is not held by caller». El diagnóstico ya distingue esa respuesta exacta de un rechazo de transferencia; no se oculta un 403 de escritura.
- **Verificación RAPID:** el operador confirmó «Programa correcto, sin errores» al verificar en FlexPendant. Se preparó y confirmó por lectura J6 de 1,73935° a 1,83935°, con J1–J5 iguales. **Pendiente:** ejecución local y medición del primer movimiento físico. Las pruebas Python no compilan RAPID.
- **Resultado del intento:** el monitor terminó con `passed: false`; J6 permaneció en 1,73935°, con error de −0,1° y ningún cambio registrado en J1–J5. El handoff de Windows aclara que el evento 40322 era de una carga anterior ya corregida; no se identificó un error de carga actual.

## Qué limita el código

La PC prepara como máximo **±0,1° en J6**, con lectura de postura estable, motores apagados y RAPID detenido; no acumula objetivos pendientes. Conserva J6 sin reducir módulo 360 y exige estar dentro de ±398° (margen nominal de 2°). Los límites efectivos y el recorrido físico deben revisarse en el controlador.

RAPID requiere manual reducido (`OP_MAN_PROG`), consume una sola vez `pcTarget`, muestra los seis ángulos y espera una confirmación local de 15 segundos. Revisa de nuevo modo y postura. En `MoveAbsJ` sustituye **únicamente J6** en un `CJointT()` recién leído; J1–J5 y ejes externos proceden de esa lectura. Rechaza cambios de J1–J5 mayores de 0,02° y diferencias de J6 mayores de 0,11° (0,1° preparado más margen de lectura/redondeo).

Declara `vLabJ6 := [5,0.5,5,0.5]`: componente de orientación 0,5°/s. Esto es un parámetro de planificación ABB, no una medición de velocidad real ni una garantía de máxima velocidad articular en cualquier postura. **No se ha fijado ni medido la aceleración física en 0,5°/s²**; esa cifra corresponde a la demo LSPB. No se alteran `AccSet`, configuración de seguridad, herramienta/carga ni límites del controlador. Se conserva `tool0` del programa original; el responsable debe confirmar que corresponde al montaje físico.

## Carpeta y comandos

En cada terminal nueva:

```bash
cd "/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws"
```

`iniciar.sh` carga el entorno. La contraseña se escribe en tu terminal y no se guarda.

1. Al reconectar, comprobar enlace y estado (solo lectura):

```bash
./iniciar.sh enlace --ping
./iniciar.sh rws_j6 inspeccionar
```

2. **Solo si falta el candidato revisado**, transferir desde Linux con AUTO, motores apagados, RAPID detenido y sin objetivo pendiente:

```bash
./iniciar.sh rws_j6 actualizar_modulo
```

Guarda respaldos de `LabJointRws`, `Module1` y candidato, más un informe previo a cada POST, en `salidas/control_articular/rws_j6/respaldo_modulo_*/`. Solicita solo mastership RAPID, edita únicamente `LabJointRws`, verifica texto, `Module1`, lista de módulos, estado, objetivo vacío y postura. No inicia RAPID, no enciende motores ni cambia modo. **Editar puede restablecer el puntero.** Si ya coincide, no hace POST. No restaura ni reintenta automáticamente tras un fallo o timeout.

3. En FlexPendant, **Verificar programa**, sin Start. Resolver cualquier error antes de preparar movimiento. Mantener `Module1/main` fuera de esta prueba. Después se seleccionará expresamente `LabJointRws/ProbarObjetivo`.

**Antes de preparar otro objetivo, comprobar la operación local sin movimiento.** Leer `pcTarget` y, si queda el objetivo de la sesión anterior, vaciarlo con `limpiar` y comprobarlo con motores apagados/RAPID detenido. El operador debe poder confirmar manual reducido en la cabecera y `MANR` por RWS, seleccionar **`LabJointRws/MostrarObjetivo` desde su inicio** y ejecutar localmente esa rutina, que solo muestra datos y no contiene movimiento. Confirmar que se ven los seis valores con el objetivo vacío. Si `Debug` sigue deshabilitado, resolver ese bloqueo antes de volver al paso 4; preparar un objetivo no habilita el menú. No reutilizar el plan del 10/11.

4. Con programa verificado, postura revisada, motores apagados y RAPID detenido, preparar el primer objetivo:

```bash
./iniciar.sh rws_j6 preparar --delta 0.1
```

Este comando solo escribe y verifica `pcTarget`. No mueve. Imprime ángulos actuales/objetivo y la ruta de un informe `preparar_*.json`. Por ejemplo, con la postura observada el 10/11, J6 pasaría de 1,73935° a 1,83935°; **cada preparación usa lecturas nuevas**, no esos números históricos.

5. Iniciar el monitor antes de que el operador ejecute, usando la ruta exacta del informe anterior:

```bash
./iniciar.sh rws_j6 observar --plan /ruta/absoluta/al/preparar_FECHA.json --duracion 120
```

La ruta es un marcador a sustituir. El monitor solo lee: registra J1–J6 a 5 Hz, llegada de J6 y cambio de los otros ejes. Exige tres lecturas de llegada dentro de 0,02° después de observar desplazamiento; avisa si J1–J5 varían más de 0,02° o J6 sobrepasa el recorrido previsto más 0,02°. **No ordena una parada** ni verifica de forma fiable velocidad/aceleración con este muestreo.

6. El operador pasa a **manual reducido**, selecciona la rutina **`LabJointRws/ProbarObjetivo`** y sigue el procedimiento local de habilitación del laboratorio. Revisa los seis valores y confirma **Mover** en el FlexPendant. La PC no selecciona el puntero ni pulsa Start. La autorización local expira a los 15 segundos de la pregunta. Si cambió la postura, cancelar y preparar de nuevo desde una lectura actual.

   Ruta del FlexPendant: **ABB → Editor de programas → T_ROB1 → Módulos → LabJointRws → Rutinas → ProbarObjetivo → Mostrar código**, y luego **Depurar → PP a rutina** (en inglés, **Debug → PP to Routine**). El menú de depuración requiere modo manual. La flecha de programa debe quedar al comienzo de `ProbarObjetivo`, para pasar por sus guardas y confirmación; no colocar PP directamente en `MoveAbsJ`. Después el operador habilita e inicia según el procedimiento del laboratorio y responde a la pregunta que aparece en la ventana del operador.

   Para consultar el ángulo real: **ABB → Movimiento (Jogging) → Formato de posición → ángulos/grados**, unidad `ROB_1`; leer la fila del eje 6 en **Posición**. Consultar esa pantalla no requiere accionar el joystick. Los valores del objetivo se muestran cuando corre `ProbarObjetivo`; el terminal Linux ya muestra medido/objetivo/error. Ruta documentada en el [manual ABB IRC5/FlexPendant, apartados 3.2.7, 4.6.9 y 5.8.5](https://bpb-us-e1.wpmucdn.com/wp.txstate.edu/dist/3/3147/files/2020/12/ABB-Robot-Operation-Manual.pdf) (copia del manual ABB alojada por Texas State University).

7. Contrastar resultado con FlexPendant y el registro del monitor. Tras una cancelación o duda, no repetir Start: detener localmente, apagar motores según el procedimiento y vaciar el objetivo:

```bash
./iniciar.sh rws_j6 limpiar
./iniciar.sh rws_j6 inspeccionar
```

## Ante fallos

HTTP 401/403 de escritura significa revisar permisos UAS/mastership; el código no solicita RMMP automáticamente ni conmuta modos. HTTP 415 en el intento inicial se corrigió declarando `application/x-www-form-urlencoded` también en las solicitudes sin cuerpo de mastership.

Tras timeout de edición o escritura, inspeccionar antes de cualquier nuevo intento: la operación puede haberse aplicado. Los informes identifican solicitudes aceptadas, rechazadas o inciertas. No pulsar Start para «ver si funciona». El respaldo local de módulos no sustituye un backup completo del sistema ABB.

Los recorridos de 5°/10° siguen reservados a la demo. Esta sesión prueba primero recepción y un desplazamiento de J6 de 0,1°; cualquier ampliación requiere revisar resultados y recorrido con el responsable.

## Archivos y fuentes

- Implementación: `ros2_ws/src/irb120_control/irb120_control/rws_j6.py`.
- Candidato instalado por texto: `ros2_ws/src/irb120_control/rapid/rws_j6/LabJointRws.mod`.
- Original: `docs/conexion_abb/evidencias/LabJointRws_original_2026-11-10.mod`.
- Registros de sesión: `salidas/control_articular/rws_j6/`.
- Evidencia resumida y hashes: [rws_j6_2026-11-10.json](evidencias/rws_j6_2026-11-10.json).

ABB: [escritura de variable RAPID](https://developercenter.robotstudio.com/api/rwsApi/rapid_symbol_data_set_page.html), [edición de texto de un módulo](https://developercenter.robotstudio.com/api/rwsApi/rapid_module_set_moudle_text_page.html), [mastership por dominio](https://developercenter.robotstudio.com/api/rwsApi/msh_domain_request_page.html), [liberación](https://developercenter.robotstudio.com/api/rwsApi/msh_domain_release_page.html), [manual RAPID RW6, speeddata/v5](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf).
