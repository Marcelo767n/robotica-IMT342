# Próxima sesión: resolver la ejecución local y comprobar J6

Preparado el **10/11/2026**. El equipo dispone de nueve días y ahora no tiene acceso al brazo. El primer resultado pendiente es un desplazamiento físico J6 de +0,1° recibido desde Linux y confirmado con lecturas reales. [Cierre del intento anterior](CIERRE_PRUEBA_J6_2026-11-10.md).

## Qué está preparado en la PC

- Recepción RWS y transferencia de `LabJointRws` ya comprobadas en el ABB.
- Nueva acción `rws_j6 diagnosticar`: solo GET, estado de modo/motores/RAPID, versión del módulo y objetivo pendiente. Guarda informe e inspección. No solicita mastership ni cambia datos del controlador.
- Análisis de informes guardados sin red y sin contraseña mediante `--informe`.
- 21 pruebas locales aprobadas. Incluyen AUTO/MANR/MANF, Guard Stop, objetivo pendiente, lecturas incompletas, aislamiento de GET y transferencia con errores. Esto no prueba la ejecución física ni el estado actual del ABB.
- No se cambió el módulo RAPID para este diagnóstico. No hace falta volver a cargarlo si la lectura confirma la versión J6 revisada.

## Antes de ir al laboratorio

Coordinar una visita con el operador que conozca el selector de modo y el arranque manual del IRC5. Llevar Linux con el repositorio y acceso a Windows/RobotStudio como apoyo si hubiera que revisar permisos, tarea o un error nuevo de programa. Preparar el recorrido de la herramienta/cables con el responsable para esa sesión.

En la [foto existente del gabinete](../../fotos/equipo/850210285_1128959306485660_255701484691959323_n.jpg), el **selector con llave está en el panel frontal derecho, a la izquierda del pulsador rojo de parada de emergencia**. La foto es del inventario, no muestra el estado actual. El operador debe confirmar la posición de manual reducido mediante la cabecera del FlexPendant y RWS; no inferirla solo del ángulo de la llave.

Se puede practicar ahora el diagnóstico de la inspección histórica, desde `proyecto/`:

```bash
bash ros2_ws/iniciar.sh rws_j6 diagnosticar \
  --informe docs/conexion_abb/evidencias/rws_j6_inspection_2026-11-10.json
```

Esa inspección se tomó **antes** de actualizar el módulo y preparar el objetivo. Por eso muestra AUTO y `original_v5`; no representa el estado final ni actual. Se identifica en pantalla como archivo histórico. Código de salida 2 indica requisitos de la revisión local incompletos, no un intento de mover.

## Secuencia al llegar

Entrar en esta carpeta en cada terminal nueva:

```bash
cd "/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws"
```

### 1. Leer el estado antes de preparar un objetivo

```bash
./iniciar.sh enlace --ping
./iniciar.sh rws_j6 diagnosticar
```

La contraseña se introduce solo en la terminal. Conservar el informe que se imprime.

| Resultado | Acción que resuelve el siguiente bloqueo |
|---|---|
| No conecta / 401 | Resolver enlace o credenciales antes de evaluar el arranque |
| Identidad o módulo no coinciden | Inspeccionar y contrastar versión; no volver a cargar a ciegas |
| Objetivo pendiente | Revisarlo y vaciarlo con el comando de abajo, únicamente con motores apagados y RAPID detenido |
| AUTO | El operador cambia el selector a manual reducido; repetir diagnóstico y comprobar `MANR` |
| Guard Stop, emergencia u otro estado | El responsable identifica la causa en la celda y eventos actuales; conservar detalle. No modificar protecciones para habilitar el programa |
| MANR, RAPID detenido, objetivo vacío y módulo J6 revisado | Comprobar `Debug` y la rutina local de solo visualización. El diagnóstico no verifica por sí mismo permisos, puntero ni habilitación |

Para vaciar un objetivo anterior, después de confirmar motores apagados y RAPID detenido:

```bash
./iniciar.sh rws_j6 limpiar
./iniciar.sh rws_j6 diagnosticar
```

`limpiar` escribe únicamente el valor vacío en `pcTarget`; no es un comando de parada.

### 2. Probar la operación local sin movimiento

Con el objetivo vacío y el modo manual reducido confirmado, abrir en FlexPendant:

**Editor de programas → T_ROB1 → LabJointRws → MostrarObjetivo → Debug → PP to Routine.**

El operador comprueba que el puntero está al comienzo de **MostrarObjetivo** y realiza su procedimiento local de ejecución. La rutina solo muestra los seis valores con `TPWrite`; no contiene `MoveAbsJ`.

**Resultado exigido:** ver los mensajes de J1–J6 y poder terminar la rutina. Esta es la prueba del recorrido local que faltó la vez anterior. No preparar otro objetivo si sigue sin poder completarse.

Si RWS confirma `MANR` pero `Debug` sigue deshabilitado, conservar una foto de la cabecera y del editor. Revisar con el operador/RobotStudio la tarea seleccionada, el usuario/permisos, el acceso de escritura y cualquier error actual de programa. No son causas ya demostradas; son los datos que faltan para aislar ese caso. El evento 40322 histórico estaba resuelto y no debe tratarse como un error nuevo sin comprobar su detalle y fecha.

### 3. Preparar y comprobar el primer giro

Solo tras completar el paso anterior, el operador deja motores apagados/RAPID detenido y sigue el procedimiento de escritura RWS comprobado. Si usa AUTO para escribir, después debe volver a confirmar MANR antes de la ejecución local.

```bash
./iniciar.sh rws_j6 preparar --delta 0.1
```

Comprobar la lectura de vuelta y conservar la ruta del **nuevo** informe. El objetivo debe modificar solo J6 desde los ángulos actuales; no reutilizar el plan anterior.

Iniciar el monitor con ese archivo, sustituyendo el marcador:

```bash
./iniciar.sh rws_j6 observar --plan /ruta/absoluta/al/nuevo/preparar_FECHA.json --duracion 120
```

El operador selecciona el inicio de **LabJointRws/ProbarObjetivo** mediante PP to Routine en manual reducido. Ejecuta según el procedimiento del laboratorio y revisa los seis ángulos antes de confirmar **Mover**. El monitor solo lee; no ordena parada.

**Resultado exigido:** desplazamiento medido J6 de aproximadamente +0,1°, llegada dentro de 0,02° durante tres lecturas, J1–J5 sin cambio superior a 0,02°, confirmación del operador y registro guardado. Una ausencia de movimiento no aprueba la prueba aunque la comunicación funcione.

Si falla, conservar el mensaje exacto y el informe de diagnóstico del estado del fallo. Revisar por etapas: objetivo recibido → modo → inicio de rutina → pregunta Mover → instrucción de movimiento → llegada. No repetir Start sobre un estado desconocido.

## Uso de los nueve días

| Plazo de trabajo | Entrega o condición para continuar |
|---|---|
| Días 1–2 | Preparación offline terminada y visita coordinada con operador; localizar selector y ensayar la secuencia documental |
| Primera visita, preferiblemente dentro de los días 2–3 | Completar `MostrarObjetivo` local y, si pasa, primer J6 +0,1° con registro |
| Días 4–6 | Corregir el bloqueo específico que se haya registrado y repetir la prueba; reservar una segunda visita para no depender de una única oportunidad |
| Días 7–9 | Repetibilidad, visualización del estado real en RViz y evidencia/informe; ampliar el alcance únicamente tras comprobar el primer movimiento |

Estos plazos son una propuesta de trabajo, no una reserva de laboratorio ni una garantía de movimiento. La disponibilidad del equipo y la resolución de estados del controlador determinan el avance. El resultado prioritario es un primer movimiento reproducible y medido.

## Referencias de estados

[ABB RWS: modos](https://developercenter.robotstudio.com/api/rwsApi/panel_opmode_get_page.html), [estado del controlador](https://developercenter.robotstudio.com/api/rwsApi/panel_ctrlstate_get_page.html), [ejecución RAPID](https://developercenter.robotstudio.com/api/rwsApi/rapid_execution_get_page.html). La cabecera manual y la ejecución por PP to Routine están descritas en el [manual ABB IRC5/FlexPendant](https://bpb-us-e1.wpmucdn.com/wp.txstate.edu/dist/3/3147/files/2020/12/ABB-Robot-Operation-Manual.pdf), apartados 3.2.5 y 5.8.5.
