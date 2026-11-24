# Evidencia de movimiento físico (Gate 3) · sesiones del 16 al 19/11/2026

Extraída de los registros crudos `salidas/control_articular/rws_mover/*.jsonl` (carpeta del repositorio principal, **no versionada**: `.gitignore` excluye `/salidas/control_articular/`). Tabla completa por orden: [`gate3_ordenes.csv`](gate3_ordenes.csv) (265 filas). Criterio de clasificación: tabla S0–S3 de `w14_s02_criterios_unificados_validacion_hito3.tex`.

Convenciones del CSV: ángulos en **grados**, orden J1…J6, separados por `;`; `q_partida` es la lectura del controlador justo antes de la orden (`from_deg`), `q_objetivo` lo que escribió la PC (`target_deg`), `q_llegada` la lectura al terminar (`joints_deg`), `error_max_deg` el mayor error entre objetivo y llegada que calculó la PC. Código de resultado: 2 = llegada confirmada (0 listo, 1 moviendo, −1 vacío, −2 límites, −3 paso excesivo, −4 modo no permitido, −5 tipo no válido). Las horas del registro están en UTC; la hora local se obtiene con UTC−4 (Bolivia; consistente con el informe del 04/11, `-04:00`). Las fechas de sesión usan la hora local (por eso los archivos `…20261118_00…` pertenecen al 17/11).

## 1. Resumen por sesión

| Sesión | Fecha local | Archivos | Módulo RAPID | Órdenes | Con llegada (código 2) | Sin resultado | Error máx. | Error mediano |
|---|---|---|---|---:|---:|---:|---:|---:|
| S16 | 16/11 (21:23–21:28) | `interactivo_20261117_012222_264923Z.jsonl` | v2 | 24 | 24 | 0 | 0,0159° | 0,0015° |
| S17 | 17/11 (21:01–22:53) | `panel_20261118_005925…`, `panel_20261118_015959…`, `panel_20261118_024913…` | v2 (inferida), v3, v4 | 177 | 177 | 0 | 0,1862° | 0,0068° |
| S18 | 18/11 (19:18–19:48) | `panel_20261118_231627_256948Z.jsonl` (+ `panel_20261118_224817…`, solo arranque) | v4 | 59 | 58 | 1 (seq 59) | 0,0689° | 0,0081° |
| S19 | 19/11 (17:27–17:29) | `panel_20261119_212627_484523Z.jsonl` | v4 (inferida) | 5 | 5 | 0 | 0,0537° | 0,0103° |
| Total | | | | 265 | 264 | 1 | 0,1862° | |

Detalle de S17 por archivo:

| Archivo | Módulo | seq | Órdenes | Llegadas | Error máx. | Orden mayor (|Δq| máx.) |
|---|---|---|---:|---:|---:|---:|
| `panel_20261118_005925_255493Z.jsonl` | v2 (inferida: solo v2 la dejaba en manual; ver abajo) | 43–140 | 98 | 98 | 0,1862° (seq 46) | 4,9° |
| `panel_20261118_015959_387886Z.jsonl` | v3 | 1–54 | 54 | 54 | 0,0982° | 39,5° |
| `panel_20261118_024913_526986Z.jsonl` | v4 | 1–25 | 25 | 25 | 0,0696° | 35,4° |

Observaciones que no se deben ocultar:

- **Orden sin resultado.** S18, seq 59 (J1 de −77,05° a −115,57°, Δmáx 38,6°): el registro termina 0,07 s después de subir `pcSeq`; no hay evento `result`. No se puede afirmar ni llegada ni rechazo. Total honesto: 264 de 265 con llegada confirmada.
- **Huecos de numeración.** S17 empieza en seq 43 (seq 25–42 sin registro en los archivos disponibles; no se sabe si hubo órdenes) y S19 en seq 98 (seq 60–97 sin registro). No se rellenan.
- **Escrituras rechazadas.** En S16 hubo 2 escrituras de `pcTarget` con HTTP 403 (J5, 01:31 UTC); no generaron orden. La bitácora del 16/11 lo explica (tras detener y reanudar RAPID) y la corrección está en el código; en las sesiones S17–S19 J5 se movió en 168, 49 y 5 órdenes sin ningún HTTP 403 (el registro no contiene más rechazos). No se repitió expresamente el escenario «detener y reanudar RAPID» que causó el 403.
- **Errores mayores en la primera tanda de S17** (15 órdenes entre 0,05° y 0,19°, con pasos de ~4,8° en ~1,1 s) frente a ≤ 0,07° en el resto: no se ha investigado la causa; no se atribuye a ninguna.
- **Velocidad.** v2 y v3: fija `vPc = [20,5,20,5]` (20 mm/s, 5°/s de orientación) por el código del módulo. v4: porcentaje de `vMax = [250,60,250,60]` escrito en `pcVelPct`: órdenes ejecutadas con S17 50 % (18 órdenes) y 75 % (5; las 2 primeras sin escritura previa de `pcVelPct` en el registro); S18 17 % (3), 50 % (48), 12 % (4) y 65 % (4); S19 50 % (5). En S18 se escribió además 22, 30, 35 y 75 % sin que se ejecutara una orden con ellos. Columna `velocidad` del CSV = último `pcVelPct` escrito antes de cada orden. Aceleración v3/v4: `AccSet 50, 50`. Las velocidades articulares y la aceleración reales **no se midieron**.
- **Módulo por sesión.** S16: v2 instalado el 16/11 (hash leído de vuelta = candidato, `instalar_20261117_004801_057276Z.json`). S17: v3 instalado a las 21:42 locales (`instalar_20261118_014214_009344Z.json`), v4 a las 22:49 (respaldo `…024913…`; un intento previo `…024613…` terminó `interrupted_inspect_before_any_start`, sin comandos de movimiento). S18: v4 reinstalado (`respaldo_modulo_20261118_231720_409043Z`). S19: no hay archivo de instalación; se infiere que siguió la v4 hasta el cambio a v5 del 20/11 (CONTEXTO_Y_OBJETIVOS).

## 2. Clasificación según el criterio S3

Criterio oficial S3: **orden verificable → aceptación → estado → movimiento observado**, con registros. Se evalúa cada eslabón por separado.

| Eslabón | Qué hay | Registro | Falta |
|---|---|---|---|
| 1. Orden verificable | Cada orden tiene `pcTarget` escrito (HTTP 204) y un evento `order` con `seq`, `from_deg`, `target_deg`. La PC solo sube `pcSeq` después de leer de vuelta `pcTarget` (diseño en `MOVER_DESDE_PC.md`; en el registro se ve el orden `write pcTarget` → `order` → `write pcSeq`). | Sí: `*.jsonl` | El registro no guarda el valor leído de vuelta, solo la escritura y la orden. |
| 2. Aceptación | `rbCodigo` final = 2 (llegada) implica que el RAPID validó y ejecutó la orden; los rechazos tendrían código −1…−5 y no aparecen. El código intermedio 1 (moviendo) no queda registrado. | Sí, indirecto: campo `code` | No hay registro del instante de aceptación ni del código 1. |
| 3. Estado | `joints_deg` leído por RWS del controlador al terminar cada orden, más el estado del controlador (`ctrlstate`, `opmode`) en los JSON de instalación. | Sí: `joints_deg` y `instalar_*.json` | `opmode` y `ctrlstate` **durante** cada orden no se guardan en el `jsonl`. |
| 4. Movimiento observado | `q_llegada` ≠ `q_partida` en cada orden, medido por el propio controlador (S1): p. ej. S16 orden 1, J6 de 3,565° a 8,569° en unos 4,4 s. Observación humana: el operador/usuario vio el brazo moverse (bitácora 16/11; «fluido» el 17/11). | Parcial: la medición es del controlador; la observación humana **solo consta en la bitácora**. | No hay video, foto con hora, ni medición externa independiente (p. ej. marcador, cámara). No hay registro firmado de «movimiento observado». |
| Autorización GO | La bitácora dice que operador y responsable participaron; el manifiesto del 10/11 la llama «reportada por el usuario». | **No** consta en archivo ninguna autorización GO firmada, ni nombres, ni alcance, ni lista de puertas de seguridad. | `checklist_seguridad.md` por firmar por el responsable del laboratorio. |

**Clasificación propuesta:**

- **S3 técnico, con alcance acotado** para S16, S17, S18 y S19: la cadena orden → aceptación → estado → movimiento está registrada por logs del PC y del controlador, para movimientos articulares (`MoveAbsJ`) de un eje a la vez o combinados, dentro de los límites del RAPID (margen de 2° respecto de los nominales; paso máximo 10° en v2, 45° en v3/v4).
- **Gate 3 formal (S3 «autorizado») no acreditado** hasta que exista la autorización GO por escrito: hoy es lo que impide presentar el movimiento como «ejecución física autorizada» en sentido oficial. No se debe afirmar «S3 completo».
- **«Movimiento observado»** descansa en: lectura del controlador (registrada) y testimonio del equipo (bitácora). Si el docente exige observación independiente, hay que añadirla en la próxima sesión (video fechado).
- **Qué NO acredita** (criterio oficial): seguridad certificada universal, exactitud global de modelos, control continuo/tiempo real (esto es RWS + RAPID con parada `fine` en cada orden), ni movimiento lineal cartesiano (`MoveL`, v5, **sin probar en el IRC5**), ni trayectorias A→B→C→A ni la celda PLC.
- Modo de operación: S16 en manual reducido con habilitador (bitácora del 16/11); S17 primera tanda en manual (**inferido**: el módulo v2 solo admite manual, `permitirAuto := FALSE`, y todas las órdenes dieron código 2, no −4); S17 (v3, v4), S18 y S19 en AUTO sin habilitador, según la bitácora y el contexto del 20/11. Detalle en `checklist_seguridad.md`.

Estado según P5 (plantilla oficial): **parcial** para movimiento autorizado (cálculo/registro trazable, falta autorización documentada y observación independiente).

## 3. Sanitización e integridad

- Se revisaron los `*.jsonl` e `instalar_*.json` con búsqueda de `passw`, `cookie`, `authoriz`, `digest`: sin coincidencias. Los registros solo contienen marcas de tiempo, símbolos PERS, ángulos y códigos. Las contraseñas se piden con `getpass` y no se guardan.
- La carpeta `respaldo_modulo_*` contiene el código RAPID de otro proyecto (`Module1`); no se copia aquí.
- Huellas SHA-256 (primeros 16 caracteres) de los archivos de origen, para poder comprobar que no cambiaron:

| Archivo | SHA-256 (inicio) |
|---|---|
| `interactivo_20261117_012222_264923Z.jsonl` | `34d60404cc9bad0e` |
| `panel_20261118_005925_255493Z.jsonl` | `d752499757b60552` |
| `panel_20261118_015959_387886Z.jsonl` | `de08dca98ed26831` |
| `panel_20261118_024913_526986Z.jsonl` | `5e4236534831bff6` |
| `panel_20261118_224817_877322Z.jsonl` (solo arranque) | `c5ee39b93cbf811c` |
| `panel_20261118_231627_256948Z.jsonl` | `19e4a6a84de7fe30` |
| `panel_20261119_212627_484523Z.jsonl` | `1813e9332fbd4cda` |
| `arrancar_20261118_015526_454013Z.jsonl` (solo arranque) | `e7438056f458d192` |
| `instalar_20261117_004801_057276Z.json` | `466a8792c96e79fa` |
| `instalar_20261118_014214_009344Z.json` | `614b304be86fc40a` |

## 4. Qué debe hacer el equipo para cerrar la brecha

1. **Copiar** los `jsonl` (sanitizados, sin contraseñas) a una carpeta versionada de evidencia, porque `salidas/control_articular/` está ignorada por git.
2. Que el responsable del laboratorio firme `checklist_seguridad.md` para la próxima sesión **antes** de mover; guardar el escaneo.
3. Registrar `opmode` y `ctrlstate` en cada orden y guardar el valor leído de vuelta de `pcTarget` (mejora de registro; hoy no existe).
4. Grabar un video fechado del movimiento (observación independiente) y anotar quién está en el FlexPendant.
5. Probar a propósito «detener y reanudar RAPID» y comprobar que la PC vuelve a pedir RMMP (el 403 del 16/11 solo se observó una vez).

## 5. Ejes que se movieron (más de 1° entre `q_partida` y `q_llegada`)

| Sesión | J1 | J2 | J3 | J4 | J5 | J6 | Órdenes |
|---|---:|---:|---:|---:|---:|---:|---:|
| S16 | 5 | 9 | 3 | 2 | 0 | 5 | 24 |
| S17 | 105 | 126 | 126 | 150 | 168 | 139 | 177 |
| S18 | 55 | 47 | 47 | 39 | 49 | 43 | 58 |
| S19 | 4 | 4 | 4 | 4 | 5 | 4 | 5 |

Cada celda cuenta órdenes con movimiento de ese eje; una orden puede mover varios. S18 cuenta las 58 órdenes con `q_llegada`. En S16 J5 no se movió (coincide con la bitácora: el intento de J5 dio HTTP 403).
