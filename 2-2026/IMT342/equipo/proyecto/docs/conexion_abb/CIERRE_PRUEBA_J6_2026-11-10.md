# Cierre de la prueba J6 del 10 de noviembre de 2026

**Resultado: el objetivo de movimiento físico no se consiguió.** La comunicación y la preparación del objetivo se verificaron, pero no se demostró la ejecución de `MoveAbsJ` ni el giro de J6. El usuario confirmó que el brazo no se movió. No presentar esta sesión como control físico conseguido.

## Evidencia y alcance

| Etapa | Resultado de la sesión |
|---|---|
| RWS Linux ↔ IRC5 `120-101516`, RW `6.12.01.00` | Verificado mediante lecturas y escrituras autenticadas |
| Escritura de los seis ángulos actuales y lectura de vuelta | Dos ensayos aprobados; error cero y objetivo vaciado |
| Transferencia de la versión J6 de `LabJointRws` | HTTP 200 y texto leído de vuelta coincidente; `Module1` conserva su huella |
| Verificación del programa en FlexPendant | El usuario comunicó «Programa correcto, sin errores»; no hay informe de compilador exportado de esa acción |
| Preparación de J6 +0,1° | HTTP 204, objetivo 1,83935° y lectura de vuelta coincidente; J1–J5 iguales |
| Seguimiento del primer objetivo | **No aprobado:** 584 muestras durante aproximadamente 120 s, J6 constante en 1,73935° y error final −0,1°; ningún cambio en los otros cinco ejes |
| Modo manual reducido, puntero al inicio y confirmación Mover | No quedaron comprobados durante el intento |
| Movimiento físico, velocidad y aceleración reales | No verificados |

La ventana registrada corresponde a las **17:51–17:53, hora de Bolivia (UTC−4)**. Se conserva el informe original del monitor con `passed: false` y el motivo «Tiempo agotado sin llegada comprobada». El registro no determina por sí solo qué ocurrió fuera de esos dos minutos; el reporte posterior del usuario es que no se consiguió movimiento.

## Dónde quedó bloqueada la prueba

Las últimas fotos del editor mostraban `Auto / Motors Off / Stopped`, con `Debug` deshabilitado. Al consultar explícitamente el modo, el usuario respondió **Auto**. No se documentó después una transición confirmada a manual reducido.

ABB documenta que `Debug` está disponible en manual y que ejecutar una rutina específica requiere manual y programa detenido. Además, nuestro `ProbarObjetivo` contiene una guarda `OpMode() <> OP_MAN_PROG`: en automático devuelve el control antes de consumir el objetivo y antes del movimiento. [Manual ABB IRC5/FlexPendant, apartados 3.2.5 y 5.8.5](https://bpb-us-e1.wpmucdn.com/wp.txstate.edu/dist/3/3147/files/2020/12/ABB-Robot-Operation-Manual.pdf). RWS identifica manual reducido como `MANR`. [ABB: modos de operación](https://developercenter.robotstudio.com/api/rwsApi/panel_opmode_get_page.html).

**Bloqueo observado:** no se consiguió completar el recorrido local desde AUTO hacia la selección y ejecución de la rutina en manual reducido. Esto explica el `Debug` deshabilitado observado. No demuestra una avería del selector, ausencia de permisos, un fallo de `MoveAbsJ`, ni que el Guard Stop histórico siga activo. No hay evidencia para atribuir el fallo a cinemática, límites, EGM o a pérdida de comunicación.

## Qué aclara el informe de Windows

Se conserva el [handoff recibido](evidencias/handoff_windows_2026-11-10.md) como antecedente. Indica que el evento **40322** correspondía a la primera carga con una condición RAPID incorrecta, que se corrigió y verificó sin errores. Pedir reiteradamente revisar ese evento como posible bloqueo actual, sin contrastar primero su historia, desvió el diagnóstico. Solo un evento nuevo y su detalle podrían establecer otro error de carga.

El bloque RAPID de ese documento es la versión original: máximo 1° por eje y `v5`. Después Linux instaló una versión distinta: preparación máxima ±0,1° de J6, conservación de J1–J5 y `vLabJ6` con componente de orientación de 0,5°/s. El handoff no sustituye esa versión ni prueba su ejecución física. Conservar ambas versiones identificadas; no cargar el bloque original como si fuera la última revisión.

## Corrección del procedimiento

El procedimiento de hoy preparó un objetivo antes de confirmar que el operador podía completar la selección de rutina y su ejecución local. Eso dejó un objetivo pendiente mientras se resolvía la navegación del FlexPendant. El siguiente ensayo debe probar primero ese recorrido con una rutina que solo muestra datos.

1. **Al reconectar, leer estado y versión real del módulo.** No asumir que siguen vigentes la postura, el modo ni la autorización de la sesión anterior.
2. **Comprobar y vaciar el objetivo anterior**, con RAPID detenido y motores apagados. No se dispone de una lectura de `pcTarget` al cierre: podría seguir pendiente. La ausencia de movimiento no demuestra que esté vacío. Usar `inspeccionar`, y `limpiar` cuando corresponda; comprobar el resultado.
3. **Completar primero la operación local sin orden de movimiento:** el responsable confirma manual reducido en la cabecera y `MANR` por RWS, comprueba el estado real de las protecciones y selecciona `LabJointRws/MostrarObjetivo` desde el comienzo. Esa rutina solo usa `TPWrite`; no contiene `MoveAbsJ`. Confirmar que se puede ejecutar localmente y ver los seis valores, conservando el objetivo vacío. No cambiar protecciones ni eliminar guardas para habilitar los menús.
4. **Solo después preparar una nueva prueba J6**, desde lecturas actuales, con motores apagados y RAPID detenido. Si el procedimiento de escritura requiere AUTO, el operador realiza la transición y luego vuelve a confirmar manual reducido antes de la ejecución local. No reutilizar el objetivo o el plan de hoy.
5. **Verificar la versión, seleccionar el inicio de `ProbarObjetivo`, iniciar el monitor y ejecutar localmente** según el procedimiento del laboratorio. Conservar los mensajes de confirmación y la instrucción/evento exactos si se detiene. La llegada debe quedar comprobada por las lecturas y por el operador.

No se modificó el código RAPID en esta revisión ni se contactó al controlador. No hay resultado nuevo de movimiento. Los comandos detallados están en la [guía J6](PRUEBA_J6_RWS_RAPID.md).

## Registros conservados

- [Resumen y huellas de evidencia](evidencias/rws_j6_2026-11-10.json).
- [Objetivo preparado y confirmado](evidencias/rws_j6_preparacion_2026-11-10.json).
- [Resultado no aprobado del monitor](evidencias/rws_j6_observacion_2026-11-10.json).
- [584 muestras originales](evidencias/rws_j6_observacion_2026-11-10_muestras.jsonl).
