# 20/11/2026: trayectorias A→B→C→A, RAPID v5, Estudio y celda PLC (trabajo offline)

Sesión de trabajo sin robot. Todo lo de esta entrada es **simulación o software**; nada se probó en el IRC5 ni con un PLC real. Fuentes: `docs/CONTEXTO_Y_OBJETIVOS.md` (§8–10), `docs/ARQUITECTURA_TRAYECTORIAS.md`, `docs/PLC_S7_1200.md`, `docs/conexion_abb/MOVER_DESDE_PC.md` (Novedades v5), commit `6e82c45` («Decisiones del 20/11…»).

```text
ID: BIT-2026-11-20-01
fecha/hora: 2026-11-20 (trabajo en gabinete; hora no registrada)
equipo y responsables: Dayana Andrade, Mirko Ayala, Marcelo Navarro (README del proyecto); responsable de cada pieza: por asignar
hipotesis: se puede planificar y verificar con las reglas del Hito 2 (más estrictas) una trayectoria A→B→C→A eligiendo por tramo articular o lineal, ejecutarla con una sola orden RAPID por tramo y comandarla desde un PLC S7-1200 sin romper la verificación de la PC
objetivo de la prueba: implementar planificador, módulo RAPID v5, ejecución en el panel, Estudio CustomTkinter y celda PLC, y probarlos contra el robot y el PLC simulados
software/hardware y versiones: PC Linux, ROS 2 Jazzy, Python; RAPID LabJointRws v5 (4667 caracteres, sin compilar en IRC5); TIA Portal: bloque SCL escrito, no compilado; PLC S7-1200: ninguno conectado
modo: simulacion
condiciones / frames / parametros: TCP en base_link, tool0 → TCP 0,150 m (convención); tolerancias en trayectorias/reglas.py (σ_min bloquea < 0,02, κ > 500, margen a límites < 10°, velocidad > 85 %, aceleración, par, z del TCP < 30 mm, salto de rama > 5°); paso máximo del RAPID v5 360° (355° en la PC); paradas `fine` en cada punto
prueba ejecutada: pruebas offline y panel simulado; PLC simulado contra el panel simulado; comprobación con ROS del punto externo (alcanzable entra al buzón, inalcanzable se rechaza con motivo)
resultado observable: ver «Resultado»
evidencia (log, commit, foto permitida, archivo): commit 6e82c45; docs/ARQUITECTURA_TRAYECTORIAS.md; docs/PLC_S7_1200.md; plc_s7_1200/ (FB_IRB120_PC.scl, OB1_ejemplo.scl, UDT_*.udt); ros2_ws/src/irb120_control/irb120_control/{trayectorias,estudio,plc,celda}/. No hay log de hardware.
estado funcional: not verified (en hardware). Software: partially_verified en simulación
limitaciones / hipotesis descartadas: ver abajo
proxima accion y responsable: ver backlog.md (por asignar)
revision docente/laboratorio requerida: sí: tolerancias propias, v5 antes de instalarla en el IRC5
```

## Decisiones tomadas el 20/11 (según el contexto del proyecto)

| Tema | Decisión |
|---|---|
| Tipo de movimiento entre puntos | Lo elige el programa por cálculo, tramo a tramo, y explica por qué |
| Paradas | El robot se detiene (`fine`) en cada punto de paso y se verifica la llegada |
| Fluidez dentro de un tramo | Sin paradas intermedias: una orden RAPID por tramo |
| Definición de puntos | Capturando la postura actual o arrastrando el control 3D en RViz |
| Interfaz CustomTkinter | Solo análisis y trayectorias; para mover se sigue usando el panel de RViz |
| Matemática | LaTeX completo con respaldo a mathtext |
| Visión | Solo el cimiento: tópico `/irb120/trayectoria/punto_externo` y `POST /api/punto_externo` |
| Tolerancias | Más estrictas que el Hito 2 (decisión del equipo; **no aprobadas por el docente**) |

## Hipótesis → prueba → resultado → interpretación → acción

**Prueba.** Ejecución de la planificación para 4 puntos (~1,5 s), del panel con el robot simulado, del nodo del PLC contra un PLC simulado y del envío de un punto externo por ROS.

**Resultado.** Funciona en simulación. El módulo v5 (`pcTipo` 0 = `MoveAbsJ`, 1 = `MoveL` con `ConfL \Off`, código de rechazo −5, `maxPasoDeg` 360) mide 4667 caracteres, por debajo del tope de 4900 que corta RWS. Los resultados numéricos de las pruebas automáticas no se vuelven a ejecutar en esta entrada.

**Interpretación.** Es S0: demuestra coherencia del software bajo supuestos, no comportamiento del robot. Lo no verificado, explícito:

- **El RAPID v5 no se ha compilado ni ejecutado en el IRC5.** La sintaxis de `MoveL` y `ConfL \Off` podría fallar en *Comprobar programa*.
- La orientación y la configuración tras un `MoveL` pueden cambiar; la PC se detiene si el robot termina a más de 5° de lo previsto, pero no se ha visto ocurrir.
- La duración que muestra el Estudio es del modelo LSPB del Hito 2; el IRC5 usa su propio perfil con `pcVelPct`, así que la real será distinta.
- **El bloque SCL del PLC no se ha compilado en TIA Portal** y no hay PLC físico en la prueba; el telegrama (núcleo de 2 palabras, parte extendida de 36 y 68 bytes) es un contrato, no un hecho medido.
- Pausar y cancelar actúan al terminar el tramo en curso; para parar ya hay que usar habilitador, Stop o paro de emergencia.
- La visión es solo una entrada de puntos; no hay cámara ni calibración.

**Acción (próxima sesión de laboratorio).** Primera sesión con v5: `./brazo.sh sesion` encontrará la v4 y pedirá Stop + Motors Off para instalar la v5; en el FlexPendant, *Comprobar programa* sobre `LabJointRws`; primero un tramo articular corto a 10–20 %; luego un tramo lineal corto desde el Estudio; medir la duración real con el registro. Antes de todo eso, GO firmado (`hito3/docs/checklist_seguridad.md`). Ver `backlog.md`.
