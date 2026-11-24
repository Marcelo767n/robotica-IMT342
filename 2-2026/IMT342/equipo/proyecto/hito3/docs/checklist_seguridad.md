# Protocolo y checklist de seguridad para pruebas en hardware

Basado en `w12_s01_checklist_seguridad.tex`. Preparado el 24/11/2026. Esta plantilla **no certifica ni sustituye** las normas oficiales de ABB ni el reglamento del laboratorio; prohibido puentear resguardos o improvisar secuencias de arranque.

> **Estado inicial de toda sesión: NO-GO para movimiento físico.** Ninguna prueba con movimiento procede hasta que el operador autorizado y el responsable del laboratorio completen la verificación y declaren expresamente `GO`. Ante cualquier campo crítico pendiente, duda sobre marcos/objetivos o falta de supervisión formal, la decisión es `NO-GO`.

## 1. Niveles de prueba y evidencia (oficial)

| Nivel de prueba | Ejemplo | Lo que demuestra | Lo que NO demuestra |
|---|---|---|---|
| Simulación offline | FK/MoveIt/RViz sin controlador | Coherencia de software/modelo bajo supuestos | Estado real del robot ni seguridad física |
| Conectividad sin movimiento | Respuesta del controlador bajo interfaz autorizada | Presencia de comunicación determinada | Control de trayectoria ni autorización de movimiento |
| Estado observado | `joint_states` originados en ABB | Adquisición de datos y trazabilidad de lectura | Aceptación de comando de movimiento |
| Movimiento supervisado | Objetivo ejecutado y medido en zona protegida | Evidencia física acotada del Gate 3 | Seguridad certificada o validez en cualquier condición |

## 2. Puertas de seguridad previas a Gate 3 · lo que consta hoy

Leyenda de la columna «Consta en la documentación»: **sí** (dato en archivo), **parcial**, **no consta**. «Estado» sigue la plantilla oficial; ninguna puerta se marca cumplida aquí porque la autoridad que debe confirmarla no ha firmado.

| # | Condición crítica | Cómo se verifica | Autoridad que confirma | Consta en la documentación | Estado | Evidencia / fecha |
|---|---|---|---|---|---|---|
| 1 | Identidad / controlador / manual correcto | Inspección e inventario | Responsable técnico | Parcial: robot, serie y sistema `120-101516`, RW 6.12.01.00 confirmados (RWS, fotos). Placa del controlador y manual local: no. | Pendiente | `gate0_ficha.md` ítems 1–3, 12 |
| 2 | Autorización de acceso al robot | Registro institucional | Laboratorio | No consta registro escrito. | Pendiente | |
| 3 | Operador habilitado y supervisor presente | Asignación formal | Laboratorio | Parcial: la bitácora menciona operador y responsable; sin nombres ni asignación formal. | Pendiente | `docs/bitacora/2026-11-16_primer_movimiento_real.md` |
| 4 | Modo operativo permitido | Protocolo / manual concreto | Operador autorizado | Parcial: manual reducido el 16/11; AUTO sin habilitador desde el 17/11. **No consta que el laboratorio haya autorizado trabajar en AUTO sin habilitador.** | Pendiente | `MOVER_DESDE_PC.md`; `CONTEXTO_Y_OBJETIVOS.md` §2 |
| 5 | Zona de exclusión y despeje físico | Inspección situacional | Operador autorizado | Solo como recomendación en la guía («revisar la celda»). Los límites del software no detectan colisiones. | Pendiente | `MOVER_DESDE_PC.md` §3 |
| 6 | E-stop y parada normal verificadas | Procedimiento institucional | Operador autorizado | La guía describe cómo parar (habilitador, Stop, paro de emergencia); **no consta** verificación del E-stop antes de cada sesión. | Pendiente | `COMO_FUNCIONA.md` §8 |
| 7 | Trayectoria y objetivos inspeccionados | Validación offline y revisión | Operador / Docente | Parcial: la PC verifica IK→FK, ida y vuelta y modelo vs controlador antes de enviar (bloquea si falla); sin revisión humana registrada. | Pendiente | `CONTEXTO_Y_OBJETIVOS.md` §5 |
| 8 | Límites, velocidad reducida, tool/TCP y base | Modelo / doc. / revisión | Operador autorizado | Parcial: límites articulares en RAPID con margen de 2°; v2 a 20 mm/s y 5°/s; v4 hasta 75 % (17/11) y 65 % (18/11) de 250 mm/s y 60°/s en AUTO; TCP 0,150 m **no medido**. Si 75 % cuenta como «velocidad reducida» en el laboratorio no está definido. | Pendiente | `LabJointRws.mod`; `gate3_ordenes.csv` |
| 9 | Riesgo de pieza/gripper minimizado | Configuración y evaluación local | Operador autorizado | La foto general muestra brida sin herramienta; sin registro por sesión de que no hubiera pieza. | Pendiente | `docs/conexion_abb/README.md` (tabla de fotos) |
| 10 | Registro de estado y mecanismos de cancelación/aborto | Protocolo aprobado | Operador autorizado | Sí, técnico: registro `jsonl` por orden; «Cancelar» solo evita las órdenes siguientes. Ctrl+C en la PC **no** detiene el robot. Protocolo aprobado: no consta. | Pendiente | `rws_mover/*.jsonl`; `COMO_FUNCIONA.md` §8 |
| 11 | Condiciones para abortar y recuperar | Procedimiento aprobado | Laboratorio | Parcial: respaldo del programa del robot y restauración documentados; criterios de aborto no firmados. | Pendiente | `RESPALDO_Y_RESTAURACION.md` |

## 3. Qué consta de cada sesión con movimiento (16–19/11)

Fechas en hora local (UTC−4). «Quién en el FlexPendant»: la documentación solo dice «el operador» o «el responsable», sin nombre.

| Dato | S16 · 16/11 | S17 · 17/11 | S18 · 18/11 | S19 · 19/11 |
|---|---|---|---|---|
| Hora de órdenes (registro) | 21:23–21:28 | 21:01–22:53 | 19:18–19:48 (arranque previo 18:48) | 17:27–17:29 |
| Órdenes / llegadas | 24 / 24 | 177 / 177 | 59 / 58 | 5 / 5 |
| Módulo RAPID | v2 | v2 (inferida), v3, v4 | v4 | v4 (inferida) |
| Modo de operación | Manual reducido (bitácora) | Primera tanda manual (inferido por v2); luego AUTO (bitácora) | AUTO (CONTEXTO §2) | No consta en la documentación (el flujo `sesion` lo pone en AUTO; el registro no guarda `opmode`) |
| Habilitador | Sostenido por el operador en manual (bitácora, guía) | Manual: sí; AUTO: **sin habilitador** | AUTO sin habilitador | No consta |
| Velocidad | 20 mm/s y 5°/s (fija en v2) | v2/v3 igual; v4 50 % y 75 % | Órdenes con 12, 17, 50 y 65 % (se escribieron también 22, 30, 35 y 75 %) | 50 % |
| Quién en el FlexPendant | «el operador» concedió RMMP; nombre no consta | «Iniciar» y paso a AUTO en el FlexPendant; nombre no consta | Ídem | No consta |
| Paso máx. por orden | 10° | 10° / 45° | 45° | 45° |
| Sesión autorizada por | Participación del responsable según la bitácora; **firma: no consta** | No consta | No consta | No consta |
| Incidentes registrados | 2 escrituras de J5 con HTTP 403 (sin movimiento); correcciones en bitácora | Enlace USB-Ethernet cortado por el hub USB; el puntero iba a `main` al pasar a AUTO (corregido con `set-pp-routine`) | 1 orden sin resultado (seq 59) | Ninguno en el registro |
| Fuente | `bitacora/2026-11-16…`, `interactivo_*.jsonl` | `bitacora/2026-11-16…` (continuación), `panel_20261118_00*…024913*` | `CONTEXTO_Y_OBJETIVOS.md`, `panel_20261118_231627*` | `CONTEXTO_Y_OBJETIVOS.md`, `panel_20261119_212627*` |

Nota: la causa «Iniciar» sin aparecer (espera de 30 s en `TPReadFK`, ampliada a 120 s) consta en `CONTEXTO_Y_OBJETIVOS.md` §6 sin fecha de sesión; no se asigna a ninguna columna.

Hallazgo: de las cuatro sesiones, **ninguna tiene el registro de decisión GO/NO-GO firmado** en el repositorio, y desde el 17/11 se trabaja en AUTO sin habilitador, cuya aceptación por el laboratorio no está documentada. El equipo debe pedir al responsable que lo confirme o lo prohíba antes de la próxima sesión.

## 4. Registro de decisión por sesión (para firma del responsable del laboratorio)

Los campos están **vacíos a propósito**: los debe llenar y firmar el responsable del laboratorio. Una firma posterior no convierte en autorizada una sesión pasada; sirve para dejar constancia de lo que ese responsable declare.

| Sesión | Decisión operativa | Tipo de prueba autorizada (alcance exacto) | Firma e identidad del operador autorizado | Fecha, hora y referencia al protocolo local |
|---|---|---|---|---|
| S16 · 16/11/2026 | ☐ GO ☐ NO-GO | | | |
| S17 · 17/11/2026 | ☐ GO ☐ NO-GO | | | |
| S18 · 18/11/2026 | ☐ GO ☐ NO-GO | | | |
| S19 · 19/11/2026 | ☐ GO ☐ NO-GO | | | |

## 5. Versión para la próxima sesión de laboratorio

Llenar **antes** de encender motores. Fecha de la sesión: por completar. Equipo: por completar. Responsable del laboratorio: por completar. Operador en el FlexPendant: por completar.

**Lo que ya se conoce y no hace falta preguntar** (verificar al llegar con `./brazo.sh estado`): robot IRB 120-3/0.6 serie 120-101516; RobotWare 6.12.01.00; red `192.168.125.1`; módulo en el robot `LabJointRws` v4; la v5 está lista para instalar y **no se ha compilado ni probado en el IRC5**.

| # | Puerta | Cómo se verifica hoy | Autoridad | Estado (☐ OK ☐ NO) | Evidencia / hora |
|---|---|---|---|---|---|
| 1 | Identidad del robot y del controlador coinciden con el manual | `./brazo.sh estado` + placa | Responsable técnico | ☐ ☐ | |
| 2 | Acceso autorizado por el laboratorio | Registro del laboratorio | Laboratorio | ☐ ☐ | |
| 3 | Operador habilitado y supervisor presentes (nombres) | Asignación | Laboratorio | ☐ ☐ | |
| 4 | Modo permitido: ¿manual reducido, AUTO con habilitador, AUTO sin habilitador? | Pregunta expresa al responsable | Operador | ☐ ☐ | |
| 5 | Zona despejada, nadie dentro del alcance | Inspección | Operador | ☐ ☐ | |
| 6 | E-stop y paro normal probados | Procedimiento del laboratorio | Operador | ☐ ☐ | |
| 7 | Trayectoria y objetivos revisados (para la v5: primer tramo **articular** corto) | Estudio/panel; revisión humana | Operador / docente | ☐ ☐ | |
| 8 | Velocidad inicial 10–20 %; tope de velocidad acordado; TCP 0,150 m sin medir | Panel | Operador | ☐ ☐ | |
| 9 | Sin pieza ni herramienta peligrosa en el primer ensayo | Inspección | Operador | ☐ ☐ | |
| 10 | Registro activo y mecanismo de aborto entendido (habilitador, Stop, paro de emergencia; Ctrl+C no detiene) | Briefing | Operador | ☐ ☐ | |
| 11 | Criterios de aborto y recuperación (respaldo del programa hecho) | `./brazo.sh respaldar` | Laboratorio | ☐ ☐ | |
| 12 | `Module1/main` **no** debe arrancarse con Start; el puntero va a `ServidorPC` | `./brazo.sh estado` | Operador | ☐ ☐ | |
| 13 | Otros grupos no están usando el robot (el 17/11 aparecieron módulos de otro grupo) | Coordinación | Laboratorio | ☐ ☐ | |
| 14 | Instalar la v5 requiere Stop + Motors Off una vez: confirmar y *Comprobar programa* en el FlexPendant | Operador | Operador | ☐ ☐ | |

**Registro de decisión de la sesión**

- Decisión operativa: ☐ **GO** ☐ **NO-GO**
- Tipo de prueba autorizada (alcance exacto): ______________________________
- Firma e identidad del operador autorizado: ______________________________
- Firma e identidad del responsable del laboratorio: ______________________________
- Fecha, hora y referencia al protocolo local: ______________________________

**Para que la sesión produzca evidencia útil** (no sustituye las puertas): foto o video fechado del brazo; copiar los `jsonl` a una carpeta versionada; anotar `opmode` y quién está en el FlexPendant en cada tanda; provocar a propósito «detener y reanudar RAPID» para confirmar la corrección del 403 del 16/11.
