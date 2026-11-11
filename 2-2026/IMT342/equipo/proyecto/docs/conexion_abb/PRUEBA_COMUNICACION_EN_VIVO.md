# Prueba en vivo: FlexPendant → ABB → ROS 2 → RViz

Preparada el 30/10/2026. El operador mueve el brazo con el FlexPendant; la PC lee sus seis ejes por RWS, actualiza el gemelo y muestra los ángulos lado a lado. El software solo consulta el ABB mediante GET; no inicia RAPID, motores ni EGM.

## Ejecutar hoy

**Actualización del 03/11 — HTTP 400 al consultar ejes:** el ensayo del usuario devolvió `-1073414145`, `icode:-804` con la consulta normal y HTTP 200 con `ignore=1`. Para repetir esa lectura de forma explícita, usar:

```bash
bash scripts/prueba_comunicacion.sh --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

`--ignore-joint-state` añade únicamente el parámetro GET `ignore=1` a `jointtarget`; no cambia el controlador, no enciende motores ni arranca programas. No se activa automáticamente ante un error. El panel indica su uso y el CSV lo registra en la columna `ignore_joint_state`. ABB documenta este parámetro para obtener `jointtarget`, pero HTTP 200 por sí solo no certifica validez física ni actualización de las medidas: comparar con FlexPendant en la prueba. [Referencia ABB](https://developercenter.robotstudio.com/api/rwsApi/ms_mechunit_jointtarget_page.html).

La captura adjunta del fallo mostraba `AUTO / motoroff`. En la comprobación posterior, `MANR / motoron`, tanto la consulta normal como la de `ignore=1` respondieron 200; se observaron cambios de J3 entre consultas. Esto sugiere dependencia del estado, pero no identifica por sí solo el significado del código interno `-804`. No cambiar modo, motores ni configuración para intentar resolver un error de lectura.

El 03/11 se verificó **RWS real → ROS → TF**, sin abrir RViz: 30 publicaciones y 28 muestras sincronizadas, con diferencia máxima de `7.11e-15°`. Durante ese ensayo corto el brazo estaba quieto. [Evidencia](evidencias/verificacion_rws_ros_tf_2026-11-03.json). La confirmación visual del gemelo siguiendo el brazo físico sigue pendiente.

Si solo se quiere diagnosticar sin abrir el gemelo:

```bash
python3 scripts/abb_lectura_rws.py --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

Los errores muestran ahora el código y mensaje entregados por ABB, además del HTTP 400. Reiniciar los procesos que estuvieran ejecutándose para que carguen estos cambios.

Desde `proyecto/`, con el acceso y la operación acordados con el laboratorio y el cable en X2 Service:

```bash
python3 scripts/g1_verificar_enlace.py --ping
./scripts/prueba_comunicacion.sh --host 192.168.125.1 --user "Default User"
```

Si la verificación muestra fallo de enlace/IP/ruta, resolverlo antes de arrancar la prueba. Usar la cuenta UAS autorizada si es distinta de la empleada el 29/10. La contraseña se solicita en la terminal y no se guarda.

Se abren **RViz** y un **panel en el navegador**. Si el navegador no se abre automáticamente, entrar a [http://127.0.0.1:8765/](http://127.0.0.1:8765/). La lectura solicitada es de **10 Hz**, aproximadamente una consulta cada 100 ms; la frecuencia efectiva se muestra en pantalla. Es sondeo RWS, no un enlace de tiempo real estricto.

El arranque usa `/opt/ros/jazzy` y `~/ros_py312/bin/python`, sin `colcon`, `ros2 launch`, Qt para Python ni instalaciones nuevas. Los archivos temporales del modelo se generan en `/tmp` y se eliminan al finalizar. `ROS_PY312` permite indicar otro intérprete compatible.

## Qué muestra el panel

| Columna | Origen |
|---|---|
| Robot RWS (°) | Los seis valores originales de `jointtarget`, antes de convertir a radianes |
| ROS recibido (°) | Suscripción independiente a `sensor_msgs/JointState`, convertido de vuelta a grados para verlo |
| Gemelo TF (°) | Ángulos recuperados de las transformadas relativas que usa RViz, quitando los `origin` y considerando los `axis` del URDF |
| Δ ROS − RWS | Diferencia de conversión/transporte |
| Δ TF − ROS | Diferencia entre el estado recibido y la orientación articular del gemelo |

Se comparan **marcas de tiempo iguales**, evitando restar una postura vieja del gemelo y una lectura nueva mientras el brazo se mueve. El panel puede mostrar una muestra completa ligeramente anterior, hasta 0.35 s respecto a la última lectura. Si ROS o TF dejan de llegar, pasa a mostrar el RWS nuevo con las columnas faltantes vacías.

TF describe orientaciones equivalentes cada 360°. Para J6 se muestra la vuelta equivalente más próxima al valor ROS; el número de vueltas completo procede del `JointState`, no puede inferirse únicamente de TF.

Las tarjetas muestran frecuencia recibida, cantidad de muestras y tiempo desde el último dato de cada etapa. `COMUNICACIÓN CORRECTA` exige las tres etapas recientes, una muestra comparable y diferencias menores de **0.01°**. Este umbral comprueba la cadena de conversión y visualización; no mide exactitud física ni retardo del robot.

## Ensayo en el laboratorio

1. Con el robot quieto, comprobar que las seis filas tienen datos. Comparar **Robot RWS** con los seis ejes del FlexPendant. Para este contraste físico se conserva la propuesta previa de **0.1° por eje**, pendiente de acuerdo con el docente.
2. El operador mueve una articulación por vez con el FlexPendant. Comprobar que cambia el mismo eje en el panel y que RViz reproduce el sentido y la postura. Repetir para J1–J6.
3. Detener el movimiento y capturar el panel, el gemelo y el FlexPendant para documentar el contraste.
4. Observar frecuencia y antigüedad durante el ensayo. Ante pérdida de lectura, el panel debe avisar y conservar los últimos números, sin sustituirlos por cero.
5. Terminar con **Ctrl+C en la terminal**. Eso detiene puente, monitor y RViz. Cerrar RViz también termina la sesión; cerrar solo la pestaña del navegador no la detiene.

Si hay un fallo RWS, el mensaje aparece en el panel. Tras **1 s** sin datos se marca `SIN DATOS`. RViz puede conservar la última postura; debe interpretarse junto al indicador de antigüedad del panel. La recuperación de lectura es automática. No hace falta provocar una desconexión física para completar la comprobación inicial.

## Evidencia y opciones

Cada sesión guarda un CSV en `salidas/prueba_comunicacion/`, excluido de Git. La terminal imprime su ruta. Las marcas del nombre de archivo terminan en `Z` y corresponden a UTC. Cada fila contiene una muestra común de RWS/ROS/TF, sus ángulos, diferencias, secuencia, sello ROS y duración de la consulta HTTP. La contraseña no se registra. El CSV contiene muestras comparables; los intervalos sin recepción se ven como huecos temporales, no como filas de ceros.

```bash
# Menor frecuencia si se desea evaluar a 5 Hz:
./scripts/prueba_comunicacion.sh --host 192.168.125.1 --user "Default User" --rate 5

# Otra carpeta de registros y otro puerto para el panel:
./scripts/prueba_comunicacion.sh --host 192.168.125.1 --user "Default User" \
  --log-dir ~/lecturas_abb/pruebas --http-port 8766
```

No ejecutar simultáneamente otro puente contra el mismo tema. Este arranque utiliza `joint_states`, TF, TF estáticos y descripción del robot bajo `/irb120/real/`, para aislar el gemelo del panel de simulación del Hito 1.

| Problema | Acción |
|---|---|
| HTTP 401/403 | Revisar la cuenta UAS autorizada; detener y reiniciar con las credenciales correctas |
| Timeout / error de conexión | Comprobar cable, IP y ruta mediante `g1_verificar_enlace.py` |
| RWS llega pero ROS/TF no | Revisar la terminal; no confundir la última postura visible con datos nuevos |
| Puerto del panel ocupado | Reiniciar usando `--http-port 8766` |
| Falta Python 3.12 o un módulo | Utilizar el arranque `.sh` y el entorno `~/ros_py312` de esta PC |
| El panel está en blanco o desconectado | Abrir la dirección impresa en la terminal y comprobar que el proceso sigue activo |

## Archivos y verificación antes del laboratorio

- `scripts/prueba_comunicacion.sh` / `.py`: arranque, contraseña, procesos, registros y cierre conjunto.
- `scripts/abb_rws_joint_bridge.py`: lectura GET, conversión y publicación; añade telemetría de la lectura original y errores para el panel.
- `scripts/monitor_comunicacion.py` / `.html`: recepción independiente, comparación TF, estado de comunicación y pantalla local.
- `scripts/tests/test_monitor_comunicacion.py`: doce pruebas de sincronización, geometría TF, diferencias reales, antigüedad, recuperación y memoria acotada.
- `scripts/tests/test_comunicacion_integrada.py`: ensayo opcional con procesos ROS reales, HTTP Digest simulado, ejes variables y una interrupción HTTP 503.

```bash
python3 -m unittest discover -s scripts/tests -t scripts/tests

# Ensayo integrado opcional, solo en loopback; no abre RViz ni necesita el ABB:
source /opt/ros/jazzy/setup.bash
ROS_DOMAIN_ID=143 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST IRB120_RUN_ROS_TEST=1 \
  ~/ros_py312/bin/python -m unittest discover -s scripts/tests -t scripts/tests \
  -p test_comunicacion_integrada.py -v
```

La primera ejecución integrada del 30/10 produjo **63 muestras comparadas**, con error máximo **5.68e-14°**, y verificó pérdida de lectura y recuperación. Además, RViz abrió con OpenGL 4.6 y el panel se comprobó visualmente recibiendo RWS/ROS/TF a 10 Hz desde un controlador simulado. **La prueba con el ABB físico de hoy queda por ejecutar en el laboratorio.**
