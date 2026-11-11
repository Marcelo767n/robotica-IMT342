# Gate 2 · FK propia frente a la pose del controlador ABB

El 03/11 el usuario reportó exitosa la prueba física de comunicación y seguimiento del gemelo en RViz. La siguiente etapa compara la matemática propia contra `robtarget` del ABB. No debe confundirse el anterior error de transmisión RWS/ROS/TF con este error de modelo.

## Arranque

Desde `proyecto/`, con el enlace y acceso de laboratorio establecidos:

```bash
bash ros2_ws/iniciar.sh validar_fk --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

La contraseña se pide una vez. Se abren RViz, el panel de comunicación [8765](http://127.0.0.1:8765/) y el panel FK [8766](http://127.0.0.1:8766/). Ctrl+C en la terminal detiene todos los procesos. Los comandos antiguos de comunicación siguen funcionando.

## Qué compara

1. Lee los seis ejes ABB `q_antes`, en grados.
2. Consulta por GET `robtarget?tool=tool0&wobj=wobj0&coordinate=Base&json=1`.
3. Lee otra vez los seis ejes, `q_después`.
4. El nodo FK convierte `q_antes` a radianes y llama a la **función propia existente** `irb120_hito1.kinematics.dh.forward_kinematics`.
5. Compara esa pose con la respuesta ABB, expresando ambas en metros y matrices de rotación. Muestra posición en mm y RPY en grados; RPY es solo presentación.

La orientación ABB usa `q1,q2,q3,q4 = w,x,y,z`. Se normaliza dentro de una tolerancia estrecha y se rechazan valores no finitos, cuaterniones nulos o incorrectos. `q` y `−q` representan la misma orientación.

La referencia viene del **controlador**, no del TF de nuestro modelo. El contexto fijo es Base/tool0/wobj0. Se adopta la correspondencia entre `base_link` propio y Base ABB, cuya concordancia se observó en la primera postura del 29/10; se debe confirmar en más posturas. No se incluye el TCP supuesto de la pinza de 150 mm, pues todavía no está medido.

Fuentes: [GET robtarget de ABB](https://developercenter.robotstudio.com/api/rwsApi/ms_mechunit_robtarget_page.html) y [protocolo de comparación del docente](<../../archivos que hay que presentar/actualizacion_semana_12/w12_s01_protocolo_validacion.tex>).

## Cálculo que ejecuta el código en cada muestra

La implementación está en [comparacion.py](../../ros2_ws/src/irb120_conexion/irb120_conexion/nodos/validacion_fk/comparacion.py). Su cálculo central es:

```python
q_rad = np.deg2rad(sample["q_before_deg"])    # seis ángulos leídos de jointtarget
T_python = dh.forward_kinematics(q_rad)      # función DH propia del proyecto
T_abb = abb_transform(sample["controller_pose"])  # robtarget recibido, mm/cuaternión → matriz
error_posicion_mm = dh.position_error_m(T_abb, T_python) * 1000
error_orientacion_rad = dh.rotation_error_rad(T_abb, T_python)
```

Cada segundo la terminal muestra los seis ángulos ABB, su conversión a radianes, XYZ/RPY calculados, XYZ/RPY recibidos, diferencia XYZ y errores. El cálculo se sigue ejecutando a 5 Hz; `--print-every` regula solamente la impresión. El panel también muestra los ángulos de entrada en ambas unidades y permite desplegar las dos matrices completas. RPY se muestra para lectura; el error angular se calcula con matrices.

Si la sesión estaba abierta al actualizar el programa, detener con Ctrl+C una vez y volver a ejecutar el comando de arranque de arriba para cargar estos cambios. La contraseña se vuelve a solicitar en la terminal.

## Errores y criterio estricto

- `e_p = ||p_Python − p_ABB||₂`, mostrado en mm.
- `e_R = ángulo(R_ABBᵀ · R_Python)`, calculado con la función geodésica existente basada en `atan2`, mostrado en rad y grados.
- Límite inicial de posición: **10⁻⁶ m = 0.001 mm**.
- Límite inicial angular: **10⁻⁶ rad ≈ 0.0000573°**.

El usuario pidió el criterio más pequeño y no indicó un valor oficial. Por eso se conserva el criterio numérico estricto utilizado en el proyecto, identificado como **propuesto**, no como requisito físico del docente. Puede resultar más estricto que la concordancia alcanzable entre modelo nominal y controlador. El programa informa ese resultado sin ampliar el umbral automáticamente. Una concordancia con el controlador tampoco constituye medición externa de exactitud mecánica.

Ejemplo para declarar otro criterio explícito en una sesión:

```bash
bash ros2_ws/iniciar.sh validar_fk --host 192.168.125.1 --user "Default User" \
  --ignore-joint-state --position-tol-mm 0.1 --orientation-tol-rad 0.0001745329252
```

Ese ejemplo usa 0.1 mm y 0.01°; no sustituye el criterio estricto predeterminado.

## Qué hacer con el brazo

El operador lleva el robot a una postura con el FlexPendant y lo deja quieto durante unos segundos. Observar y guardar varias posturas distintas, incluyendo cambios en las seis articulaciones y especialmente J3, J5 y J6. No se generan consignas físicas desde este código.

El panel muestra:

| Estado | Significado |
|---|---|
| DENTRO | Muestra comparable y ambos errores dentro de los límites de la sesión |
| FUERA | Muestra comparable y alguno de los errores supera su límite |
| NO EVALUABLE | Movimiento detectable o ventana de adquisición demasiado larga; errores visibles solo como diagnóstico |
| MARCO INVALIDO | La muestra no declara Base/tool0/wobj0; no se calcula el error |
| LECTURA INVALIDA | Falló RWS o llegó una respuesta incompleta/no válida |
| SIN DATOS | El panel conserva valores antiguos tras más de 1.5 s sin muestras |

RWS no entrega ángulos y pose en una transacción atómica. Se evita evaluar cuando `q_antes` y `q_después` difieren más de 0.01°, cuando su variación de FK supera cualquiera de las tolerancias de comparación, o cuando la adquisición dura más de 500 ms. Es una comprobación de consistencia temporal, no una garantía de simultaneidad; movimientos que salgan y vuelvan entre ambas lecturas podrían pasar inadvertidos. **La validación se hace con el robot quieto**, no utilizando las diferencias durante movimiento como errores de geometría.

## Evidencia y estructura

Los registros de cada sesión están en `salidas/prueba_comunicacion/`:

- `comunicacion_…Z.csv`: comparación de los ángulos RWS/ROS/TF.
- `comunicacion_…Z_fk.csv`: ángulos, poses, errores, tolerancias, aceptación e intervalos de adquisición.
- `comunicacion_…Z_fk.jsonl`: muestra completa, matrices, referencia ABB y ruta/SHA256 del código matemático utilizado.

Se registran también muestras descartadas; no se reemplazan datos ausentes por cero ni se evalúan como aprobados. La contraseña no se guarda. Las fechas con sufijo `Z` están en UTC.

La nueva organización está en [ros2_ws/README.md](../../ros2_ws/README.md), con implementación por nodos en `ros2_ws/src/irb120_conexion/irb120_conexion/nodos/`.

## Verificación de software del 03/11

Pasaron diez pruebas nuevas de comparación/adquisición, frente a geometría ROS-Industrial independiente. La prueba integrada de procesos ROS y HTTP Digest simulado registró 25 muestras e identificó correctamente `DENTRO`, `FUERA` (desplazamiento artificial de 0.02 mm) y `NO_EVALUABLE` (ángulos cambiantes). La batería anterior conserva 61 pruebas aprobadas y una integrada opcional omitida en su ejecución normal.

Durante la preparación del 03/11, la consulta nueva de `robtarget` terminó en timeout. Ese era el estado de aquella fecha; el éxito físico del gemelo anterior fue reportado por el usuario.

## Ensayo físico del 04/11

El proceso del usuario entregó lecturas reales de ángulos y pose desde `192.168.125.1`. Se congelaron y recalcularon **1365 muestras**: **1177 DENTRO, 25 FUERA y 163 NO_EVALUABLE**. Las últimas **100 muestras estacionarias (19.80 s)** pasaron todas el criterio estricto, con error de posición **0.0000745114 mm** y orientación **0.0000117848°**. No se modificaron modelo ni tolerancias.

La variación fue principalmente en J1–J3; falta ampliar posturas de J4–J6. Los 25 resultados FUERA se conservan, sin atribuir automáticamente su causa a movimiento o redondeo. Esto verifica concordancia numérica con ABB en el alcance ensayado, sin cerrar una validación global ni medir exactitud mecánica externa. Abrir el [informe con datos y gráfico](evidencias/fk_real_2026-11-04_224412Z_informe.md).

Tras hacer visible el cálculo en terminal/panel, se recibieron otras **cinco muestras ROS nuevas** del puente conectado al ABB (secuencias 3550–3554). El código actualizado introdujo sus ángulos en la FK propia y comparó la pose con ABB: las cinco pasaron, con error **0.000019242212 mm** y **0.000006733372°** en esa postura. Se guardaron [los cinco cálculos completos](evidencias/fk_codigo_2026-11-04_225130Z_muestras.jsonl) y [la captura del panel con datos reales](evidencias/fk_codigo_2026-11-04_225130Z_panel.jpg).

La prueba adicional verifica que cambiar los ángulos de entrada, manteniendo fija la pose ABB, cambia la pose propia y provoca el error esperado. Pasaron las once pruebas unitarias FK y la integrada ROS con 25 muestras simuladas (pose concordante, pose incorrecta y movimiento).
