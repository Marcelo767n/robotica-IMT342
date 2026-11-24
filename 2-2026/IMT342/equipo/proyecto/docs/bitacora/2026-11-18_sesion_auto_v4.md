# Sesión del 18/11/2026: AUTO con el módulo RAPID v4

Entrada reconstruida el 24/11/2026 a partir de los registros `rws_mover/*.jsonl` y de `docs/CONTEXTO_Y_OBJETIVOS.md`; no se escribió durante la sesión. Lo que no consta en esos registros se marca como tal. Tabla orden por orden: [`hito3/docs/gate3_ordenes.csv`](../../hito3/docs/gate3_ordenes.csv) (sesión S18). Horas locales = UTC−4.

```text
ID: BIT-2026-11-18-01
fecha/hora: 2026-11-18, arranque 18:48 (sin órdenes) y órdenes 19:18–19:48 hora local (UTC−4)
equipo y responsables: Dayana Andrade, Mirko Ayala, Marcelo Navarro (README del proyecto); responsable de prueba, operador y responsable del laboratorio: por completar por el equipo
hipotesis: con el módulo v4 en modo AUTO (sin habilitador) el IRC5 ejecuta órdenes articulares de hasta 45° a velocidades distintas elegidas desde la PC (pcVelPct), con llegada confirmada y sin las pausas intermedias de la v2
objetivo de la prueba: comprobar el control desde RViz en AUTO y el efecto de pcVelPct en la duración y el error de llegada
software/hardware y versiones: IRB 120-3/0.6 serie 120-101516; IRC5 (RobotWare 6.12.01.00); LabJointRws v4 reinstalado a las 19:17 (hash del candidato 8cbed6780275…, respaldo respaldo_modulo_20261118_231720_409043Z); PC Linux, ROS 2 Jazzy, panel «IRB 120» de RViz, ./brazo.sh sesion
modo: movimiento (AUTO). Autorización GO: no consta en archivo
condiciones / frames / parametros: AUTO sin habilitador; paso máximo 45° por orden y margen de 2° a los límites en el RAPID; AccSet 50, 50; vMax = 250 mm/s y 60°/s; pcVelPct escrito entre 12 y 75 %; objetivos en grados absolutos, jointtarget, orden J1…J6
prueba ejecutada: panel envía 59 órdenes (seq 1–59), una a la vez; cada una escribe pcTarget (HTTP 204), lo relee y sube pcSeq
resultado observable: 58 órdenes con rbCodigo = 2 (llegada); la orden 59 no tiene resultado en el registro. Error máximo 0,0689° (orden 14, Δmáx 37,5°, a 50 %); mediana 0,0081°
evidencia (log, commit, foto permitida, archivo): hito3/docs/gate3_ordenes.csv; salidas/control_articular/rws_mover/panel_20261118_231627_256948Z.jsonl (sha256 19e4a6a84de7fe30…) y panel_20261118_224817_877322Z.jsonl (solo arranque); no hay foto ni video
estado funcional: partially_verified
limitaciones / hipotesis descartadas: ver abajo
proxima accion y responsable: ver backlog.md (por asignar)
revision docente/laboratorio requerida: sí: autorización de AUTO sin habilitador y GO firmado
```

## Hipótesis → prueba → resultado → interpretación → acción

**Hipótesis.** La v4 permite mover en AUTO a velocidad variable sin pausas dentro de cada orden.

**Prueba.** Dos arranques del servidor: a las 18:48 (`start_server`: mastership, `set-pp-routine`, `execution start`, liberación; sin órdenes) y a las 19:17 (los mismos pasos), tras reinstalar el módulo. Después, 59 órdenes desde el panel.

**Resultado observado.**

| Velocidad (`pcVelPct`) | Órdenes | Qué se ve en el registro |
|---|---:|---|
| 17 % | 3 (seq 1–3) | Movimientos de ~26,8° en 2,7–3,0 s |
| 50 % | 48 (seq 4–15, 20–55) | Movimientos de ~27° en 1,1–1,4 s |
| 12 % | 4 (seq 16–19) | Movimientos de 37,5° en 9,1–9,7 s |
| 65 % | 4 (seq 56–59) | Movimientos de ~38,5° en 1,6 s; seq 59 sin resultado |

Se escribió además `pcVelPct` = 22, 30, 35 y 75 % sin que se enviara una orden con esos valores. Las duraciones medidas son de extremo a extremo (escritura, ejecución, lectura); no son velocidad articular.

- La orden 59 (J1 de −77,05° a −115,57°, Δmáx 38,6°) quedó escrita y `pcSeq` subido a las 19:48:11; el registro termina ahí. No se sabe si el robot llegó, fue detenido o el programa se cerró.
- Todas las demás órdenes llegaron con error ≤ 0,07° (una sola por encima de 0,05°).

**Interpretación.** La cadena PC → RWS → RAPID → estado funcionó en AUTO con velocidad variable: es S3 técnico (orden, código de resultado, estado leído). El efecto de la velocidad es coherente (a 12 % tarda varias veces más que a 50 %), pero no se midió la velocidad real. No se puede decir nada sobre la orden 59, ni se documenta la autorización de AUTO sin habilitador ni el GO.

**Acción.** (1) Averiguar por qué no hay resultado de la orden 59 (revisar `brazo.sh eventos` y la sesión del panel). (2) Registrar `opmode` y `ctrlstate` con cada orden. (3) Pedir al responsable que firme el GO o decida sobre AUTO sin habilitador (`hito3/docs/checklist_seguridad.md`). (4) Copiar los `jsonl` a una carpeta versionada.

## Limitaciones

- El registro no guarda el modo ni el estado de motores durante la sesión; el AUTO sale de `CONTEXTO_Y_OBJETIVOS.md` y de las instalaciones (`opmode: AUTO` al instalar).
- Quién estaba en el FlexPendant y quién autorizó: no consta.
- Sin medición externa del movimiento (video, marcador).
- Esta sesión no prueba EGM, control continuo ni movimiento lineal.
