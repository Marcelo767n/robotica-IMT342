# Contexto actual y próximos objetivos · IRB 120 desde RViz

Actualizado el **20/11/2026**. Resume dónde está el proyecto para retomarlo en otra sesión (o con otra persona) y fija los objetivos siguientes. Rama: `proyectoHito3y4`.

## 1. Estado en una frase

El ABB IRB 120 real se controla desde la PC Linux **dentro de RViz**: se escriben ángulos o se arrastra una pose, la cinemática inversa de Pieper del Hito 2 calcula los ángulos, se verifican con la FK propia y con el propio controlador, y solo entonces se envían por RWS a un servidor RAPID (`LabJointRws`, v4 en el robot y v5 lista para instalar) que los ejecuta con `MoveAbsJ` (y, en la v5, también `MoveL`). El gemelo digital sigue al robot en tiempo real.

## 2. Qué funciona (comprobado con el robot real)

| Fecha | Resultado |
|---|---|
| 16/11 | Primer movimiento desde la PC: 24 órdenes en J6, J1, J4, J3 y J2, error ≤ 0,016° por orden ([bitácora](bitacora/2026-11-16_primer_movimiento_real.md)) |
| 17/11 | Control desde RViz; verificación modelo vs controlador ABB 0,00007 mm; modo AUTO sin habilitador; movimiento a posición 0 con error 0,0046° |
| 18/11 | Sesión en AUTO con la v4: 59 órdenes, 58 con llegada confirmada (1 sin resultado), error máx. 0,069°, velocidad cambiada entre 17 % y 75 % |
| 19/11 | 5 órdenes, todas con llegada, error máx. 0,054°, velocidad 50 % |

## 3. Cómo se usa

```bash
brazo sesion        # desde cualquier carpeta (atajo en ~/.local/bin/brazo)
```

Una contraseña. La terminal guía: llave en **AUTO** (confirmar) → si hace falta, **Stop + Motors Off** y reinstala el módulo → **Motors On** → la PC pone el puntero en `ServidorPC` y arranca → **Ventana del operador → «Iniciar»** (2 min, con reintentos). Después abre RViz + panel «IRB 120» + ventana de análisis del Hito 2. Otros comandos: `brazo eventos` (registro del controlador), `brazo estado`, `brazo respaldar`, `brazo simulado --analisis`, `brazo pruebas`, `brazo ayuda`.

Guía completa del laboratorio: [MOVER_DESDE_PC.md](conexion_abb/MOVER_DESDE_PC.md) · cómo funciona por dentro: [COMO_FUNCIONA.md](conexion_abb/COMO_FUNCIONA.md) · respaldo del programa del robot: [RESPALDO_Y_RESTAURACION.md](conexion_abb/RESPALDO_Y_RESTAURACION.md).

## 4. Arquitectura actual

```text
RViz: panel «IRB 120» (C++) + control 3D ──JSON /irb120/panel/orden|estado──► nodo irb120_panel_rws (Python)
                                                                               │  validación, IK Pieper,
Ventana de análisis (tkinter + matplotlib) ◄── HTTP 127.0.0.1:8770/estado ─────┤  verificación, tramos ≤ 40°
                                                                               │
                                              RWS 1.0 (HTTP 80, Digest) ───────► IRC5 · LabJointRws v4 · ServidorPC
                                                                               │  MoveAbsJ a pcVelPct % de 250 mm/s
gemelo digital (blanco) ◄── JointState ◄── lectura de ejes cada 0,3 s ◄────────┘
```

| Pieza | Dónde |
|---|---|
| Script único | `ros2_ws/brazo.sh` (+ `iniciar.sh`) |
| Nodo y lógica del panel | `ros2_ws/src/irb120_control/irb120_control/panel/` (estado, verificación, sesión, puente ROS, controles 3D…) |
| Cliente RWS | `ros2_ws/src/irb120_control/irb120_control/rws_mover.py`, `rws_j6.py` |
| Programa RAPID | `ros2_ws/src/irb120_control/rapid/rws_mover/LabJointRws.mod` (v4, ≤ 4900 caracteres) |
| Panel de RViz (C++/Qt) | `ros2_ws/src/irb120_rviz_panel/` |
| Ventana de análisis | `ros2_ws/src/irb120_control/irb120_control/analisis/` |
| Matemática del Hito 2 | `hito2/irb120/` (DH, Pieper, Jacobiano, LSPB, dinámica) |

## 5. Verificación antes de enviar (pedido del ingeniero)

1. **IK → FK**: T = FK(q_IK) frente a la T pedida, ≤ 0,001 mm / 0,001°.
2. **Ida y vuelta**: IK(FK(q_IK)) frente a q_IK, eje por eje, ≤ 0,001°.
3. **Modelo vs controlador**: FK propia de `tool0` frente a la pose que informa el ABB, ≤ 0,5 mm / 0,1° con el robot quieto.
4. **Robot real**: ángulos medidos frente a los de la IK, eje por eje, en ° y en % del recorrido, más dx/dy/dz en mm.

El envío se bloquea si la pose no es alcanzable, sale de los límites (con 2° de margen) o falla 1, 2 o 3.

## 6. Lecciones aprendidas con el robot real

| Problema | Causa | Solución |
|---|---|---|
| El robot se quedaba antes del objetivo | El ABB devuelve 6 cifras (101.664) y la PC comparaba con más decimales | Escribir con 3 decimales; replanificar cada tramo |
| Pausas cada 5–10° | Órdenes cortas con `fine` | v3/v4: hasta 45° por orden, `AccSet 50` |
| Al pasar a AUTO el puntero va a `main` | Comportamiento del IRC5; `main` es de otro grupo | La PC pone el PP por RWS (`set-pp-routine`) y lo verifica |
| Módulo cortado | RWS corta `set-module-text` a 5000 caracteres | Módulo ≤ 4900; el instalador lo controla |
| «Iniciar» no aparecía | `TPReadFK` esperaba solo 30 s en la Ventana del operador | 120 s y reintentos automáticos |
| Pérdida de enlace | Hub USB | Adaptador USB-Ethernet directo a la laptop |
| Otros grupos usan el robot | `Module1` vacío, `MainModule`, `IMT342_*` | Respaldo con `brazo respaldar`; la sesión reinstala nuestro módulo si cambió |

## 7. Nuevos objetivos

### 7.1 Interfaz gráfica nueva con CustomTkinter
- Sustituir la ventana de análisis actual (tkinter/ttk) por una interfaz **CustomTkinter** más clara: tema oscuro/claro, pestañas, tarjetas con indicadores verde/rojo.
- Leer el estado del panel como hoy (HTTP local) y **además** poder dar órdenes (objetivos, trayectorias), con la misma validación y confirmación que el panel de RViz.
- Mantener RViz para el gemelo digital y el control 3D.

### 7.2 Trayectorias definidas por el usuario (A → B → C → … → A)
- Editor de **puntos de paso** en la interfaz: añadir, editar, reordenar y borrar puntos; cada punto como pose cartesiana (X, Y, Z, roll, pitch, yaw), como ángulos, o **capturado** de la postura actual del robot.
- Secuencias con nombre, guardadas en archivos (JSON) para repetirlas; opción de cerrar el ciclo y de repetir N veces.
- **Vista previa** completa antes de mover: el robot naranja recorre la trayectoria en RViz y las gráficas muestran q(t), q̇(t), q̈(t) por tramo.
- Ejecución en el robot tramo a tramo con la verificación de la sección 5 en cada punto, con pausa, reanudar y cancelar.

### 7.3 Reglas de seguridad de la trayectoria (Hito 2)
Antes de permitir la ejecución, comprobar a lo largo de **toda** la trayectoria (no solo en los puntos):
- Alcanzabilidad y **rama de IK consistente** entre puntos (sin saltos de configuración brazo/codo/muñeca).
- **Singularidades**: σ_min(J) ≥ 0,01 (criterio del Hito 2) y número de condición acotado; marcar el instante y el tramo que se acercan.
- **Límites articulares** con margen, y velocidades/aceleraciones dentro de los límites de la LSPB.
- Par articular (dinámica completa y 1R) dentro de valores razonables.
- Si una regla falla: decir en qué tramo y por qué, y proponer una alternativa (otra rama, punto intermedio).

### 7.4 Presentación matemática "como LaTeX"
- Mostrar con notación matemática renderizada (matplotlib *mathtext* o LaTeX): tabla DH, cada matriz ⁱ⁻¹Aᵢ, ⁰T₆ y T del TCP, el Jacobiano J(q) 6×6 con det, σ y número de condición, las ecuaciones de la LSPB por tramo, y τ = M(q)q̈ + C(q,q̇)q̇ + G(q).
- Que se vean con los valores numéricos actuales y se actualicen con la pose/trayectoria seleccionada.
- Pensado para proyectar en la defensa: tipografía grande y explicación breve de cada bloque.

## 8. Decisiones del 20/11/2026

| Tema | Decisión |
|---|---|
| Tipo de movimiento entre puntos | **Lo elige el programa según los cálculos**: para cada tramo evalúa recta cartesiana y movimiento articular (alcanzabilidad en todo el tramo, rama de IK consistente, σ_min(J), límites, duración LSPB, par) y propone el mejor, explicando por qué. |
| Paradas | El robot **se detiene en cada punto de paso** (`fine`), donde se verifica la llegada (mm y %). |
| Fluidez dentro de un tramo | **Sin paradas intermedias**: eliminar los cortes cada 40° que hoy dividen un tramo largo en varias órdenes con parada (requiere ampliar el RAPID a una sola orden por tramo o encolar subpuntos con zona y `fine` solo al final). |
| Cómo se definen los puntos | **Capturando la postura actual** del robot y **arrastrando el control 3D en RViz** («Añadir a la trayectoria»). |
| Interfaz CustomTkinter | **Solo análisis y trayectorias** (diseñar, verificar, ver la matemática). Para mover se sigue usando el panel de RViz; la trayectoria verificada se envía al panel. |
| Visión artificial | Dejar el **cimiento**: una entrada de puntos externa (p. ej. un tópico ROS con poses en `base_link`) para que un nodo de visión publique coordenadas que aparezcan como puntos de trayectoria, con la misma verificación. |

## 9. Preguntas abiertas → respuestas del 20/11/2026

| Pregunta | Respuesta | Cómo quedó |
|---|---|---|
| Tolerancias | Más estrictas que el Hito 2 | σ_min bloquea < 0,02 (aviso < 0,04), κ > 500, margen a límites < 10°, más velocidad, aceleración, par, altura del TCP y salto de rama. Tabla en [ARQUITECTURA_TRAYECTORIAS.md](ARQUITECTURA_TRAYECTORIAS.md); valores en `trayectorias/reglas.py` (`TOLERANCIAS`). |
| Matemática | Libre elección: lo que se vea mejor | LaTeX completo (matplotlib `usetex`, TeX ya instalado), con respaldo automático a *mathtext* si TeX falla (`IRB120_SIN_TEX=1` lo fuerza). |
| Visión | Aún no se sabe qué cámara ni dónde | Cimiento genérico: tópico `/irb120/trayectoria/punto_externo` (`PoseStamped`, TCP en `base_link`) y `POST /api/punto_externo` → buzón del panel → Estudio. La calibración cámara → base se decide cuando se elija montaje (fija: mano-ojo una vez; en la pinza: FK(q)·T_tool0_cam). |

## 10. Implementado el 20/11/2026 (probado offline y con el panel simulado; falta el robot real)

| Pieza | Dónde | Estado |
|---|---|---|
| Planificador y reglas A→B→C→A | `irb120_control/trayectorias/` | Evalúa articular y lineal en cada tramo, elige y explica; muestrea todo el tramo (σ_min, κ, límites, q̇, q̈, τ, z, rama). ~1,5 s para 4 puntos. |
| RAPID v5 «una orden por tramo» | `rapid/rws_mover/LabJointRws.mod` (4667 caracteres) | `pcTipo` 0 = `MoveAbsJ`, 1 = `MoveL` (`ConfL \Off`); `fine` solo al final; sin cortes de 40°. **Sin probar en el IRC5.** |
| Ejecución en el panel | `panel/trayectoria.py`, `panel/buzon.py` | Re-planifica con la postura real, exige las mismas órdenes, verifica cada punto (sección 5), pausa/reanuda en los puntos de paso, N vueltas. |
| Estudio CustomTkinter | `irb120_control/estudio/` · `brazo estudio` | Estado, Trayectoria (editor, capturar, buzón, JSON), Reglas, Gráficas (q, q̇, q̈, τ, σ, κ), Matemática (DH, A_i, T, J, LSPB, τ en LaTeX). |
| Biblioteca de trayectorias | Estudio → pestaña Trayectoria | Cualquier número de puntos, abiertas o cerradas, editables (insertar, duplicar, reordenar); guardar como `NN_nombre.json` con Nº PLC; papelera en vez de borrar. |
| Celda PLC S7-1200 | `plc/` (nodo `irb120_plc_s7`), `celda/` (nodo `irb120_celda`), `plc_s7_1200/` (TIA Portal) · `brazo plc`, `brazo plc-simulador` | Telegrama de 2 palabras (mando/estado + valor) con parte extendida opcional; contrato en [PLC_S7_1200.md](PLC_S7_1200.md). Probado con el PLC simulado contra el panel simulado; el FB SCL **no se ha compilado** en TIA Portal. |
| Puntos desde RViz y visión | menú del control 3D «Añadir a la trayectoria» · `brazo punto X Y Z R P Y` | Comprobado con ROS: el punto alcanzable entra al buzón; el inalcanzable se rechaza con el motivo. |

### Primera sesión con el robot real después de este cambio
1. `brazo sesion`: encontrará la v4 y pedirá **Stop + Motors Off una vez** para instalar la v5; luego Motors On e «Iniciar» como siempre.
2. En el FlexPendant, *Comprobar programa* sobre `LabJointRws` (la sintaxis de la v5 no se pudo compilar sin el controlador).
3. Primero un tramo **articular** corto a velocidad baja (10–20 %) desde el panel; después un tramo **lineal** corto desde el Estudio. Tras un lineal, si el robot acaba a más de 5° de lo previsto, la PC se detiene y no corrige a ciegas.
4. Pausar y cancelar actúan al terminar el tramo en curso: para parar YA, habilitador, Stop o paro de emergencia.
5. La duración que muestra el Estudio es la del modelo LSPB del Hito 2; el IRC5 usa su propio perfil con `pcVelPct`, así que la duración real será distinta (se puede medir con el registro).
