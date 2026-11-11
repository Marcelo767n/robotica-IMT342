# Handoff del ABB IRB 120 con Linux, ROS 2 y RWS

**Fecha:** 10 de noviembre de 2026  
**Objetivo:** enviar seis ángulos articulares desde Linux al ABB IRB 120 y comprobar la recepción antes de una prueba física supervisada.

## Estado al cerrar esta sesión

- RobotStudio se conectó al IRC5 físico **120-101516**, en **192.168.125.1**, con **RobotWare 6.12.01.00**.
- El módulo **LabJointRws** quedó cargado y corregido en **T_ROB1**. RobotStudio verificó la tarea y reportó **«Sin errores»**. El FlexPendant mostró el módulo y la variable **pcTarget**.
- La escritura y lectura de vuelta de un objetivo desde Linux siguen pendientes. La lectura RWS desde Linux ya figuraba en el handoff original, pero no se repitió desde Linux en esta sesión.
- Durante la intervención en RobotStudio no se ejecutaron rutinas ni se enviaron órdenes de movimiento. Después, el usuario reportó un fallo durante su prueba física. La última foto en modo automático muestra **Motors Off** y **Stopped (Speed 100%)**.

## Diagnóstico del intento de movimiento reportado

El usuario informó después que la prueba física falló. Aún falta saber si el brazo permaneció quieto, si inició un movimiento y se detuvo, o si ejecutó una trayectoria distinta de la esperada. Tampoco tenemos el registro de eventos de ese intento, la salida del cliente Linux ni el objetivo enviado. El resultado «Sin errores» de RobotStudio verifica la sintaxis y la semántica de la tarea en el momento de la carga. La ejecución física sigue sin validar.

Si hubo movimiento inesperado, contacto o una parada durante el recorrido, mantener el equipo detenido y conservar el registro para que lo revise el responsable de la celda antes de repetir la prueba. El evento histórico `40322` fue un error de carga de la primera versión y se resolvió antes de esta prueba. El `Guard Stop` se observó en una foto anterior. Para asociarlo al nuevo fallo hace falta el evento con su hora y los mensajes inmediatamente anteriores. [ABB, diagnóstico del IRC5 por registro de eventos](https://library.e.abb.com/public/e6617595547fc6c2c1257cc5004451bd/Operating%20manual_Trouble%20shooting_3HAC020738-001_revK_en.pdf)

| Observación en el intento | Qué comprobar |
|---|---|
| El POST da error o el GET inmediato devuelve otro valor | Guardar el código HTTP y el cuerpo de ambos. Verificar el acceso de escritura RAPID, la ruta exacta del símbolo y el formato del objetivo. |
| Aparece `Seleccione modo manual reducido.` | La rutina entró en la comprobación de modo y salió antes de consumir el objetivo. Registrar el modo mostrado en la cabecera. |
| Aparece `Sin objetivo o diferencia mayor a 1 grado.` | El objetivo estaba vacío o al menos un eje superaba 1° de diferencia. Comparar los seis ángulos absolutos en grados con la postura real. Si se copiaron valores de RViz o ROS 2, comprobar la conversión de radianes a grados y el orden y signo de los ejes. |
| Se muestra la confirmación y la rutina sale sin llegar a `MoveAbsJ` | Registrar si se eligió `Cancelar`, si pasaron 15 segundos o si apareció `Cambio de modo o de posicion. Prueba cancelada.`. |
| Tras el intento, `pcTarget` vuelve a `9E+09` | La rutina borra el objetivo antes de validar la distancia y antes de pedir confirmación. El valor por sí solo no determina si hubo movimiento. Por eso la lectura de vuelta se hace antes de ejecutar la rutina. |
| En la pantalla figura `T_ROB1/Module1/main` | Confirmar qué rutina indicaba el puntero cuando se pulsó `Start`. `Module1/main` pertenece al programa existente y su código completo no se inspeccionó en esta sesión. |
| Aparece un error de ejecución o el brazo se mueve de forma inesperada | Guardar el evento exacto, la instrucción señalada, el objetivo de seis ejes y la postura anterior. Revisar esos datos con el operador antes de volver a habilitar movimiento. |

El primer paso para retomar es obtener una foto de **Menú ABB → Event Log** con el evento del intento abierto, su código y los mensajes inmediatamente anteriores. Anotar también si hubo movimiento, qué rutina estaba seleccionada y si se llegó a ver el botón **Mover**. Con los motores apagados se puede repetir la prueba de escritura y lectura de abajo para comprobar por separado el enlace RWS.

## Punto de partida y alternativas

El handoff original registraba un manipulador **IRB 120-3/0.6**, un controlador identificado visualmente como **IRC5 Compact**, las opciones **689-1 EGM**, **616-1 PC Interface**, **623-1 Multitasking** y el controlador **UDPUC**. También documentaba un puente RWS que publica posiciones en RViz y RobotStudio instalado en Windows. La placa del controlador quedó pendiente de verificación.

| Ruta | Uso | Trabajo necesario |
|---|---|---|
| RWS + RAPID | Enviar una postura de seis ángulos y verificarla | Linux escribe un objetivo RAPID por HTTP. El programa del IRC5 ejecuta el movimiento cuando el operador lo autoriza. |
| TCP + RAPID Socket Messaging | Enviar objetivos puntuales mediante un protocolo propio | Definir mensajes, confirmaciones y manejo de desconexiones. |
| EGM + UDP | Seguir referencias articulares continuas | Configurar UDPUC, activar la sesión desde RAPID y preparar el cliente UDP con egm.proto. Se puede probar primero solo la recepción de EGM Position Stream. |
| abb_ros2 | Integrar el control continuo con ros2_control | Validar primero EGM. Adaptar la descripción y la configuración de ejes, porque el ejemplo documentado es para un **IRB 1200**, distinto del **IRB 120**. |

Elegimos **RWS + RAPID** para la primera demostración de una postura. RobotStudio se utilizó para cargar y verificar el módulo. En adelante, Linux puede comunicarse directamente con el IRC5. El FlexPendant también permite cargar un módulo mediante USB con **Editor de programas → Módulos → Archivo → Cargar módulo**.

## Qué hicimos en el IRC5

1. Desde Windows, verificamos el enlace Ethernet. La PC tenía **192.168.125.203/24**. El controlador respondió **2 de 2 pings** en **1–2 ms**. RWS devolvió **401 Unauthorized** con una solicitud de autenticación Digest, que confirmó que el servicio HTTP estaba accesible.
2. RobotStudio detectó el controlador físico por el puerto de servicio. El usuario inició sesión y concedió acceso temporal de escritura desde el FlexPendant.
3. Revisamos **T_ROB1** y agregamos **LabJointRws.mod** con **Cargar módulo**, conservando el programa existente y **Module1/main**.
4. La primera carga generó el evento **40322**. **Verificar programa** ubicó dos diagnósticos de sintaxis en la misma condición de la línea 36. Cambiamos la negación después de **OR** por una comparación explícita con **FALSE**.
5. En el primer intento de aplicar la corrección, cancelamos para conservar el puntero de programa. Más tarde, con autorización expresa, volvimos a solicitar escritura y aplicamos la corrección aceptando el restablecimiento del puntero.
6. RobotStudio reportó **«Comprobado: … T_ROB1 Sin errores»**. El IRC5 registró **Módulo editado** y **Punto de programa restablecido**. Liberamos el acceso de escritura.
7. Las fotos del FlexPendant confirmaron **LabJointRws** como módulo de programa y **pcTarget** como **jointtarget**.

## Cómo funciona el módulo

Archivo: [LabJointRws.mod](LabJointRws.mod).

- **pcTarget** guarda un objetivo absoluto en grados, en orden **J1 a J6**. El valor inicial **9E+09** en los ejes indica que todavía no hay objetivo preparado.
- **MostrarObjetivo** muestra los seis valores guardados en el FlexPendant.
- **ProbarObjetivo** exige modo manual reducido, toma el objetivo una sola vez y limpia el valor guardado. Comprueba una diferencia máxima de **1° por eje**, pide confirmación local y vuelve a comprobar posición y modo antes de llamar a **MoveAbsJ**. El límite es una restricción del ensayo, no una comprobación de trayectoria libre.
- El **puntero RAPID** indica desde dónde se ejecutará el programa al pulsar **Start**. Seleccionar el puntero por sí solo no inicia una rutina.

## Código RAPID completo aplicado desde RobotStudio

Este bloque reproduce el contenido funcional de `LabJointRws.mod` aplicado al controlador y verificado en `T_ROB1`. La primera versión difería en la condición de la segunda comprobación. A continuación figura el cambio exacto que resolvió los diagnósticos de sintaxis.

```diff
-        IF OpMode() <> OP_MAN_PROG OR NOT ObjetivoCercano(objetivo.robax, actual.robax) THEN
+        IF OpMode() <> OP_MAN_PROG OR ObjetivoCercano(objetivo.robax, actual.robax) = FALSE THEN
```

```rapid
MODULE LabJointRws
    CONST jointtarget noTarget := [[9E9,9E9,9E9,9E9,9E9,9E9],[9E9,9E9,9E9,9E9,9E9,9E9]];
    CONST num maxDeltaDeg := 1;
    PERS jointtarget pcTarget := [[9E9,9E9,9E9,9E9,9E9,9E9],[9E9,9E9,9E9,9E9,9E9,9E9]];

    PROC MostrarObjetivo()
        MostrarEjes pcTarget.robax;
    ENDPROC

    PROC ProbarObjetivo()
        VAR jointtarget objetivo;
        VAR jointtarget actual;
        VAR num respuesta := 0;
        VAR errnum motivo := 0;

        IF OpMode() <> OP_MAN_PROG THEN
            TPWrite "Seleccione modo manual reducido.";
            RETURN;
        ENDIF

        objetivo := pcTarget;
        pcTarget := noTarget;
        actual := CJointT();
        IF NOT ObjetivoCercano(objetivo.robax, actual.robax) THEN
            TPWrite "Sin objetivo o diferencia mayor a 1 grado.";
            RETURN;
        ENDIF

        MostrarEjes objetivo.robax;
        TPReadFK respuesta,"Ejecutar el objetivo mostrado?",stEmpty,stEmpty,stEmpty,"Mover","Cancelar"\MaxTime:=15\BreakFlag:=motivo;
        IF motivo <> 0 OR respuesta <> 4 THEN
            RETURN;
        ENDIF

        actual := CJointT();
        IF OpMode() <> OP_MAN_PROG OR ObjetivoCercano(objetivo.robax, actual.robax) = FALSE THEN
            TPWrite "Cambio de modo o de posicion. Prueba cancelada.";
            RETURN;
        ENDIF

        objetivo.extax := actual.extax;
        MoveAbsJ objetivo,v5,fine,tool0;
        TPWrite "Movimiento terminado.";
    ENDPROC

    LOCAL PROC MostrarEjes(robjoint ejes)
        TPWrite "Objetivo absoluto en grados:";
        TPWrite "J1"\Num:=ejes.rax_1;
        TPWrite "J2"\Num:=ejes.rax_2;
        TPWrite "J3"\Num:=ejes.rax_3;
        TPWrite "J4"\Num:=ejes.rax_4;
        TPWrite "J5"\Num:=ejes.rax_5;
        TPWrite "J6"\Num:=ejes.rax_6;
    ENDPROC

    LOCAL FUNC bool ObjetivoCercano(robjoint destino, robjoint actual)
        RETURN Abs(destino.rax_1 - actual.rax_1) <= maxDeltaDeg AND
               Abs(destino.rax_2 - actual.rax_2) <= maxDeltaDeg AND
               Abs(destino.rax_3 - actual.rax_3) <= maxDeltaDeg AND
               Abs(destino.rax_4 - actual.rax_4) <= maxDeltaDeg AND
               Abs(destino.rax_5 - actual.rax_5) <= maxDeltaDeg AND
               Abs(destino.rax_6 - actual.rax_6) <= maxDeltaDeg;
    ENDFUNC
ENDMODULE
```

## Qué muestran las fotos más recientes

- En **Manual**, el FlexPendant mostraba **Guard Stop**, **Stopped (Speed 100%)** y el editor de **pcTarget** con su valor inicial. La causa de la parada de protección queda por revisar en **Menú ABB → Event Log** con el responsable del laboratorio.
- En **Auto**, mostraba **Motors Off**, **Stopped (Speed 100%)** y **T_ROB1/Module1/main**. Ese estado no identifica la causa del **Guard Stop** anterior.
- **Too Many Views** indica que el FlexPendant ya tiene seis vistas abiertas. Se puede pulsar **OK**, reutilizar una pestaña **Program Data** abierta o cerrar una vista duplicada con la **X**.

## Siguiente paso: probar RWS desde Linux con el brazo detenido

Mantener **RAPID detenido y los motores apagados**. Salir del editor de **pcTarget** con **Cancel** para que la comprobación se haga desde Linux. Usar la cuenta autorizada del laboratorio. Curl solicita la contraseña localmente.

```bash
read -r -p 'Usuario RWS: ' usuario
base='http://192.168.125.1'
url="$base/rw/rapid/symbol/data/RAPID/T_ROB1/LabJointRws/pcTarget"

# Consultar los ejes actuales. También se puede usar el puente RWS existente.
curl --fail-with-body --digest --cookie '' --user "$usuario" \
  "$base/rw/rapid/tasks/T_ROB1/motion?resource=jointtarget"

# Introducir esos mismos seis valores en grados, separados por comas.
read -r -p 'J1,J2,J3,J4,J5,J6 en grados: ' angulos
curl --fail-with-body --digest --cookie '' --user "$usuario" \
  --data-urlencode "value=[[$angulos],[9E9,9E9,9E9,9E9,9E9,9E9]]" \
  "$url?action=set"

# Verificar el valor guardado. También se puede inspeccionar en Program Data.
curl --fail-with-body --digest --cookie '' --user "$usuario" "$url"
```

La prueba se cumple cuando el último **GET** devuelve los seis valores enviados. Si el **POST** falla por permisos o acceso de escritura RAPID, registrar el código HTTP y el mensaje del controlador. El envío por RWS solo escribe la variable.

Antes de repetir la prueba física, revisar el fallo reportado con el responsable. Una vez identificada la causa, confirmar el modo **manual reducido**, el ajuste de velocidad y que la celda está despejada. En automático, la vista mostrada corresponde al programa existente **Module1/main**.

## Referencias

- [ABB RWS, leer posición articular](https://developercenter.robotstudio.com/api/rwsApi/rapid_motion_get_jointtarget_page.html)
- [ABB RWS, escribir variable RAPID](https://developercenter.robotstudio.com/api/rwsApi/rapid_symbol_data_set_page.html)
- [ABB RWS, leer variable RAPID](https://developercenter.robotstudio.com/api/rwsApi/rapid_symbol_data_get_page.html)
- [ABB, manual EGM para RobotWare 6](https://library.e.abb.com/public/fc6f8da4578b413cb68700526ab7e758/3HAC073319%20AM%20Externally%20Guided%20Motion%20RW6-en.pdf)
- [ABB, referencia RAPID](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf)
- [ABB, manual del IRC5](https://library.e.abb.com/public/531d8ac9d3624b6a84c3250ac48bfbcf/3HAC047136%20PM%20IRC5-en.pdf)
- [PickNik, abb_ros2](https://github.com/PickNikRobotics/abb_ros2)