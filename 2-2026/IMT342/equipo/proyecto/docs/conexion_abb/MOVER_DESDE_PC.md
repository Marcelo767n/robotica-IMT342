# Mover el IRB 120 desde la PC · guía de la próxima sesión

Preparado el **11/11/2026**. Sustituye la prueba puntual J6 de ±0,1° ([cierre del 10/11](CIERRE_PRUEBA_J6_2026-11-10.md)) por una ruta pensada para **mover el brazo desde Linux, orden tras orden**, sin volver a tocar el puntero de programa en cada movimiento.

> **Estado:** código y módulo RAPID nuevos, con 16 pruebas offline más una prueba de punta a punta contra un ABB simulado en loopback. **Todavía no se ejecutó en el IRC5 real.** La compilación del módulo la confirma el FlexPendant con *Comprobar programa*.

## 1. Por qué no se movió el 10/11

| Causa | Evidencia | Qué cambia ahora |
|---|---|---|
| **El controlador estaba en AUTO.** `ProbarObjetivo` empieza con `IF OpMode() <> OP_MAN_PROG THEN RETURN`, y en AUTO el menú *Depurar* (PP to Routine) está deshabilitado. | Fotos y RWS: `AUTO / Motors Off`, `Debug` gris, puntero en `Module1/main`. Monitor: 584 muestras con J6 inmóvil. | La guía obliga a pasar a manual reducido antes de arrancar y `rws_mover estado` lo comprueba. |
| **Faltaba el permiso RMMP.** En manual, ABB solo deja escribir variables PERS por RWS a un cliente remoto con RMMP aceptado en el FlexPendant. Las escrituras del 10/11 funcionaron porque se hicieron en **AUTO**. | Todas las escrituras registradas tienen `opmode: AUTO`. | `rws_mover` pide RMMP y lo mantiene vivo (sondeo cada 2 s en un hilo). |
| **El ensayo era casi invisible.** +0,1° de J6 a 0,5°/s y una sola orden por arranque. Además, la rutina borra `pcTarget` antes de validar, así que cada fallo obliga a preparar otro objetivo. | Diseño de `LabJointRws` J6. | El módulo v2 es un servidor en bucle: hasta 10° por orden, y la PC divide los recorridos largos. |

**Conclusión:** ni la comunicación ni la cinemática fallaron. Falló la operación local (modo y puntero), y el procedimiento no contemplaba RMMP para escribir en manual.

### ¿Estaba bien el código RAPID que usaste?

- **La sintaxis está bien.** Las dos versiones (la original de Windows y la J6) pasaron *Verificar programa*. `TPReadFK ... "Mover","Cancelar"` devuelve 4 para «Mover», así que la comparación `respuesta <> 4` es correcta. El error 40322 venía de `OR NOT f(...)`: en RAPID, `NOT` tiene menor precedencia que `OR`. La corrección con `= FALSE` es válida.
- **La lógica también es correcta, pero no servía para mover el robot desde la PC:**
  1. Solo funciona en manual reducido. En AUTO sale sin mensaje visible si no se mira la ventana de producción.
  2. La ventana de 1° (original) o 0,1° (J6) impide cualquier movimiento útil.
  3. Necesita arrancarse con PP to Routine **en cada movimiento**.
  4. La versión original usaba `v5`, cuya orientación es de 500°/s: la muñeca podía girar rápido. La versión J6 lo corrigió con `vLabJ6`.
- **No hay que cargarla de nuevo.** La v2 la reemplaza, conserva `pcTarget` y `MostrarObjetivo`, y no toca `Module1`.

## 2. Qué hay nuevo en el repositorio

| Archivo | Qué es |
|---|---|
| [`rapid/rws_mover/LabJointRws.mod`](../../ros2_ws/src/irb120_control/rapid/rws_mover/LabJointRws.mod) | Módulo v2: `ServidorPC` (bucle de órdenes) y `MostrarObjetivo` |
| [`irb120_control/rws_mover.py`](../../ros2_ws/src/irb120_control/irb120_control/rws_mover.py) | Cliente: `estado`, `instalar`, `interactivo`, `mover`, `terminar` |
| [`test/test_rws_mover.py`](../../ros2_ws/src/irb120_control/test/test_rws_mover.py) | 16 pruebas con un IRC5 simulado que replica `Validar()` del RAPID |
| [`iniciar.sh`](../../ros2_ws/iniciar.sh) | Nueva entrada `rws_mover`. Las herramientas `rws_*` ya no necesitan ROS: basta Python 3 con `requests` |

### Protocolo PC ↔ robot

```text
PC:    escribe pcTarget (6 ángulos absolutos, grados) → lo lee de vuelta → pcSeq := pcSeq + 1
Robot: ve pcSeq ≠ rbSeq → valida → rbCodigo := 1 → MoveAbsJ (vPc, fine, tool0) → rbCodigo := 2 → rbSeq := pcSeq
PC:    espera rbSeq = pcSeq y lee rbCodigo
```

| `rbCodigo` | Significado |
|---:|---|
| 0 | Listo, esperando |
| 1 | Moviendo |
| 2 | Llegada |
| −1 | Objetivo vacío o no válido |
| −2 | Fuera de límites (margen de 2° respecto a los nominales) |
| −3 | Algún eje cambia más de 10° en una sola orden |
| −4 | Modo no permitido (AUTO con `permitirAuto := FALSE`) |

**Doble protección.** La PC valida límites y paso antes de escribir, y el robot vuelve a validar con su propia lectura `CJointT()`. La velocidad es fija en el RAPID (`vPc := [20,5,20,5]`: 20 mm/s de TCP y 5°/s de orientación). La PC no puede subirla.

## 3. Antes de ir

En la PC Linux, desde la carpeta del repositorio:

```bash
git pull origin proyectoHito3y4
```

```bash
cd 2-2026/IMT342/equipo/proyecto/ros2_ws && python3 -m unittest discover -s src/irb120_control/test -p 'test_rws_*.py'
```

Debe terminar en `OK` (37 pruebas). Comprobar también:

- **Cable** en el puerto **X2 Service** del IRC5 e IP de la PC en **192.168.125.x** (por DHCP del controlador).
- **Usuario y contraseña RWS.** Hasta ahora se usó `Default User`.
- **Coordinación con el operador o responsable.** La sesión necesita dos personas: el operador sostiene el FlexPendant con el habilitador presionado y tú escribes las órdenes en la PC.
- **Postura de partida y zona libre.** Revisarlas en la celda. Los límites del software no detectan colisiones.

## 4. Secuencia en el laboratorio

Todas las órdenes de la PC se ejecutan desde `proyecto/ros2_ws/`.

### Paso 1 · Conexión (solo lectura)

```bash
./iniciar.sh enlace --ping
```

```bash
./iniciar.sh rws_mover estado
```

`estado` muestra el modo, los motores, RAPID, la versión del módulo y los ángulos, más una lista **FALTA:** con lo que impide mover. En este punto es normal ver `módulo J6_revisado` y varias líneas FALTA.

### Paso 2 · Instalar el módulo v2 (una sola vez)

**FlexPendant / controlador:**

1. Llave de modo en **AUTO**. Si aparece el diálogo de cambio de modo, pulsar **OK**.
2. **No** encender motores. La cabecera debe mostrar `Motors Off` y `Stopped`.

**PC:**

```bash
./iniciar.sh rws_mover instalar
```

El comando respalda `LabJointRws` y `Module1` en `proyecto/salidas/control_articular/rws_mover/respaldo_modulo_*`, sustituye solo el texto de `LabJointRws` y verifica la lectura de vuelta. Es el mismo mecanismo que ya funcionó el 10/11. Si `pcTarget` del día anterior siguiera pendiente, se niega; en ese caso, ejecutar antes `./iniciar.sh rws_j6 limpiar` (AUTO, motores apagados).

**FlexPendant, para comprobar que compila:**

3. **Menú ABB → Editor de programas → Depurar → Comprobar programa.** Debe mostrar «sin errores». Si aparece un error, **fotografiarlo** (línea y mensaje) y no seguir.
4. El puntero puede haberse restablecido a `main`. **No pulsar Start.**

Si se repite `./iniciar.sh rws_mover estado`, debe decir `módulo servidor_v2`.

### Paso 3 · Pasar a manual reducido y apuntar a `ServidorPC`

**FlexPendant / controlador:**

1. Llave de modo en **Manual** (símbolo de la mano). La cabecera debe decir **Manual**, no «Manual 100%». En manual es **normal** ver `Guard Stop` mientras no se presiona el habilitador.
2. **Menú ABB → Editor de programas → Depurar → PP a rutina** («PP to Routine»).
3. En la lista, elegir el módulo **LabJointRws** y la rutina **ServidorPC**, y pulsar **OK**. La flecha del puntero debe quedar en la **primera línea de `ServidorPC`**.
   - Si `Depurar` sigue gris: la cabecera **no** está en manual. Repetir el paso 1 y comprobarlo con `./iniciar.sh rws_mover estado` (debe decir `Modo: MANR`).
4. Primera vez: **Quickset** (botón de la esquina inferior derecha) → **Velocidad → 25 %**. Se puede subir a 50 o 100 % cuando el comportamiento esté comprobado.

### Paso 4 · Conceder RMMP (robot todavía quieto)

**PC:**

```bash
./iniciar.sh rws_mover interactivo
```

Pide la contraseña, muestra el estado y solicita RMMP. **En el FlexPendant aparece un diálogo de solicitud de acceso remoto:** el operador pulsa **Conceder** o **Permitir**. La PC confirma con `RMMP concedido`. **Dejar esta terminal abierta**: mantiene el permiso vivo. Si se cierra, se vuelve a pedir.

### Paso 5 · Arrancar `ServidorPC`

**FlexPendant:**

1. Presionar el **habilitador** hasta la posición media y mantenerlo. La cabecera debe pasar a `Motors On`.
2. Pulsar **Start** (▶).
3. Aparece **«¿Aceptar objetivos enviados por la PC?»**. Pulsar **Iniciar** sin soltar el habilitador. Hay 30 s para responder; si no, la rutina termina sin mover.
4. La ventana de producción muestra **«Servidor PC activo. Esperando objetivos.»**

> Si con RMMP concedido el FlexPendant no deja arrancar, hacer el orden inverso: cerrar la terminal de la PC (Ctrl+C), arrancar primero `ServidorPC` (paso 5) y después abrir `interactivo` y aceptar RMMP.

### Paso 6 · Mover desde la PC

En el prompt `irb120 (paso 5.0°)>`:

```text
estado                 # debe terminar sin líneas FALTA
j6 +5                  # primera prueba: 5° de la muñeca, fácil de ver y de bajo riesgo
j6 -5
j1 +10                 # se envía como dos órdenes de 5°
j3= 20                 # valor absoluto de un eje
abs 0 -10 20 0 30 0    # seis ángulos absolutos (grados)
paso 10                # hasta 10° por orden (límite del RAPID)
fin                    # termina ServidorPC en el robot
salir
```

Mientras se mueve, la PC imprime los seis ejes, lo que falta para llegar y el estado del robot. Termina con `LLEGADA confirmada`. Si el robot rechaza una orden, se muestra su código (tabla de la sección 2).

También hay un modo de una sola orden, útil para scripts:

```bash
./iniciar.sh rws_mover mover j6 +5
```

Este modo pide RMMP en cada ejecución. Para la sesión conviene `interactivo`.

**Para detener:** soltar el habilitador (o apretarlo a fondo), pulsar **Stop** o la **parada de emergencia**. **Ctrl+C en la PC no detiene el robot.** Tras soltar el habilitador, RAPID queda detenido. Para reanudar: habilitador y **Start**; la orden en curso continúa y el bucle sigue esperando. La PC avisa con «RAPID se detuvo» y espera hasta 120 s.

### Paso 7 · Cierre

1. En la PC: `fin` y luego `salir`.
2. FlexPendant: soltar el habilitador. Si se va a usar el programa normal, **Depurar → PP a Main**.
3. Copiar `proyecto/salidas/control_articular/rws_mover/*.jsonl` a `docs/conexion_abb/evidencias/` como evidencia de la sesión. Contienen cada escritura, orden, resultado y postura final.

## 5. Problemas y qué hacer

| Mensaje | Causa probable | Acción |
|---|---|---|
| `HTTP 401` | Usuario o contraseña | Revisar las credenciales RWS |
| `FALTA: módulo J6_revisado` / `original_v5` | Falta instalar la v2 | Paso 2 |
| `FALTA: modo AUTO` | Llave en AUTO | Paso 3.1 |
| `FALTA: motores motoroff` | Habilitador no presionado | Mantenerlo en la posición media |
| `FALTA: RAPID detenido` | `ServidorPC` no está corriendo | Paso 5 (puntero en `ServidorPC`, Start) |
| `FALTA: ServidorPC no está activo` | Corre otra rutina (por ejemplo `main`) o no se pulsó «Iniciar» | Pasos 3.2–3.3 y 5 |
| `RMMP no concedido` / `Se perdió RMMP` | El diálogo se rechazó, caducó o la terminal se cerró | Repetir; el operador acepta en el FlexPendant |
| `POST ...: HTTP 403` | Escritura sin RMMP, o el usuario no tiene permiso de modificar datos | Comprobar RMMP; si persiste, revisar los permisos UAS de `Default User` con el responsable |
| Código −3 | El paso supera 10° | Usar `paso 5` (la PC ya divide los recorridos) |
| Código −2 | Destino fuera de límites con 2° de margen | Elegir otro destino |
| `Sin respuesta del robot` | RAPID detenido mucho tiempo, o rutina distinta | Mirar el FlexPendant y la ventana de producción; ejecutar `estado`. No enviar más órdenes |
| Error de RAPID o del movimiento en el FlexPendant | Por ejemplo, colisión, límite o configuración | Fotografiar **Registro de eventos** (código y hora) y detenerse |

## 6. Plan B: AUTO (solo con autorización del responsable)

Si el manual reducido no es práctico (por ejemplo, porque RMMP no se puede conceder), el módulo puede aceptar AUTO, donde las escrituras no necesitan RMMP. **Requiere la celda cerrada y la autorización explícita del responsable**: en AUTO el robot se mueve sin habilitador.

1. En manual: **Editor de programas → LabJointRws**, cambiar `CONST bool permitirAuto := FALSE;` por `TRUE;` y ejecutar **Comprobar programa**. `rws_mover` reconoce esa variante como `servidor_v2_auto`.
2. En manual: **PP a rutina → ServidorPC**.
3. Llave en **AUTO**, aceptar el diálogo, pulsar el botón **Motors On** del controlador y luego **Start** en el FlexPendant. Pulsar **Iniciar**.
4. En la PC: `./iniciar.sh rws_mover interactivo`.

La velocidad sigue limitada por `vPc` en el RAPID. Al terminar, volver a poner `permitirAuto := FALSE`.

## 7. Siguiente paso: RViz

Con la ruta de órdenes comprobada, el siguiente paso es enviar desde ROS 2 o RViz los mismos objetivos que hoy se escriben en el prompt. Se haría con una orden por objetivo confirmado, no con un flujo continuo; para seguimiento continuo sigue haciendo falta EGM ([plan](../hitos_3_4/PLAN_CONTROL_EGM_IK_VISION.md)). Mientras tanto, el gemelo de solo lectura (`./iniciar.sh comunicacion ...`) puede correr en paralelo en otra terminal para ver el robot real en RViz.

## Fuentes

- RMMP obligatorio para modificar variables PERS en modo manual, con sondeo periódico: [abb_robot_client, `request_rmmp` y `poll_rmmp`](https://github.com/rpiRobotics/abb_robot_client/blob/master/src/abb_robot_client/rws.py).
- [RWS: escribir variable RAPID](https://developercenter.robotstudio.com/api/rwsApi/rapid_symbol_data_set_page.html) · [modos de operación](https://developercenter.robotstudio.com/api/rwsApi/panel_opmode_get_page.html).
- [Manual IRC5/FlexPendant: PP to Routine y modo manual](https://bpb-us-e1.wpmucdn.com/wp.txstate.edu/dist/3/3147/files/2020/12/ABB-Robot-Operation-Manual.pdf) (apartados 3.2.5 y 5.8.5).
- [Referencia RAPID: `MoveAbsJ`, `TPReadFK`, `speeddata`](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf).
