# PLC S7-1200 ↔ PC ↔ IRB 120 · fuentes SCL para TIA Portal

> **Estado: pendiente de compilar en TIA Portal.** No hay compilador TIA en el entorno de desarrollo; la sintaxis se revisó a mano
> (ver «Puntos a verificar»). Contrato de telegramas: `../docs/PLC_S7_1200.md`.

## Archivos

| Archivo | Contenido |
|---|---|
| `UDT_IRB120_Orden.udt` | PLC → PC, 36 B (núcleo 4 B) |
| `UDT_IRB120_Estado.udt` | PC → PLC, 68 B (núcleo 4 B) |
| `FB_IRB120_PC.scl` | Enlace: TCON + TSEND + TRCV + TDISCON, perro guardián, órdenes por bits |
| `OB1_ejemplo.scl` | `FB_Celda_Ejemplo` (secuencia pieza → trayectoria 1 → 2), su DB de instancia y `Main` (OB1) |

## Decisión: acceso estándar (no optimizado)

Los telegramas son UDT dentro de los `STAT` de `FB_IRB120_PC` (`{ S7_Optimized_Access := 'FALSE' }`), pasados directo a
`TSEND`/`TRCV`. El orden de bytes es el nativo de S7 (big-endian) y todos los campos caen en offsets pares sin relleno
(36 B y 68 B), sin `Serialize`/`Deserialize` (dependen del firmware). Consecuencia: el FB que lo use como multiinstancia
(`FB_Celda_Ejemplo`) y los DB de instancia también deben ser no optimizados; `Main` puede quedar optimizado.

## Telegramas (contrato v2, `../docs/PLC_S7_1200.md`)

Formato `Completo = TRUE`: PLC → PC 36 B, PC → PLC 68 B. Formato núcleo (`Completo = FALSE`): solo los 4 primeros bytes
(`LEN` 4 en `TSEND` y `TRCV`). Debe coincidir con `plc.formato` de `celda.yaml`; no cambiarlo con la conexión abierta.

PLC → PC (`UDT_IRB120_Orden`)

| Byte | Tipo | Campo |
|---|---|---|
| 0 | Word | `mando` (núcleo) |
| 2 | UInt | `valor` (núcleo): trayectoria 1…99, o velocidad % en «fijar velocidad» |
| 4 | UInt | `velocidad_pct` (ext.) |
| 6 | UInt | `repeticiones` (ext.) |
| 8, 10 | UInt | reservados = 0 |
| 12 | Real×6 | `pose` X,Y,Z [mm], roll,pitch,yaw [°] (ext.) |

Bits de `mando`

| Bit | Máscara | Nombre |
|---|---|---|
| 0 | `16#0001` | `habilitar` (nivel) |
| 1 | `16#0002` | `ejecutar` (trayectoria `valor`) |
| 2 | `16#0004` | `pausar` |
| 3 | `16#0008` | `reanudar` |
| 4 | `16#0010` | `cancelar` |
| 5 | `16#0020` | `reposo` |
| 6 | `16#0040` | `acusar` |
| 7 | `16#0080` | `velocidad` |
| 8 | `16#0100` | `punto` (solo completo) |
| 15 | `16#8000` | `vida` (alterna en cada envío) |

PC → PLC (`UDT_IRB120_Estado`)

| Byte | Tipo | Campo |
|---|---|---|
| 0 | Word | `estado` (núcleo) |
| 2 | UInt | `valor` (núcleo): código si `rechazada`/`error`; si no, tramo actual |
| 4 | UInt | `fase`: 0 lista · 1 ejecutando · 2 pausada · 3 terminada · 4 cancelada · 5 error (ext.) |
| 6, 8, 10 | UInt | `tramo`, `tramos`, `vuelta` (ext.) |
| 12 | UInt | `velocidad_pct` (ext.) |
| 14 | UInt | `codigo` (ext.) |
| 16, 18 | UInt | reservados |
| 20 | Real×6 | `q` J1…J6 [°] (ext.) |
| 44 | Real×6 | `pose` TCP medido (ext.) |

Bits de `estado`

| Bit | Máscara | Nombre | Salida del FB |
|---|---|---|---|
| 0 | `16#0001` | `enlace` (nodo del brazo) | `EnlaceBrazo` |
| 1 | `16#0002` | `listo` | `RobotListo` |
| 2 | `16#0004` | `moviendo` | `Moviendo` |
| 3 | `16#0008` | `terminado` | `Terminado` |
| 4 | `16#0010` | `error` | `ErrorCelda` |
| 5 | `16#0020` | `pausada` | `Pausada` |
| 6 | `16#0040` | `motores_on` | `MotoresOn` |
| 7 | `16#0080` | `servidor_activo` | `ServidorActivo` |
| 8 | `16#0100` | `auto` | `ModoAuto` |
| 9 | `16#0200` | `simulado` | `Simulado` |
| 10 | `16#0400` | `aceptada` (saludo) | `OrdenAceptada` (retenida) |
| 11 | `16#0800` | `rechazada` (saludo; código en `valor`) | `OrdenRechazada`, `CodigoRechazo` |
| 12 | `16#1000` | `habilitar_recibido` | `HabilitarRecibido` |
| 15 | `16#8000` | `vida` | perro guardián |

Códigos de rechazo (contrato §3.3): 1 orden no válida · 2 sin habilitar · 3 sin enlace con el brazo · 4 robot no listo ·
5 trayectoria inexistente · 6 plan no apto · 7 brazo rechazó/no respondió · 8 ocupado · 9 enlace PLC perdido.
Locales del FB: `1` parámetro inválido (no se envía), `100` sin saludo en `TimeoutOrden` (5 s) o enlace perdido en vuelo.

### Saludo de una orden (4 pasos)

1. El programa da un flanco en la entrada del FB (p. ej. `Ejecutar` con `Trayectoria := 1`, `Habilitar` = 1). El FB pone a 1 **solo** el bit de esa orden y `valor` = 1: `mando = 16#0003` (habilitar + ejecutar), más el bit 15 que alterna.
2. El FB **mantiene** el bit hasta que la PC responde `aceptada` (bit 10) o `rechazada` (bit 11, código en `valor`), o hasta 5 s (rechazo local, código 100).
3. Al recibir la respuesta el FB **baja** el bit de orden (`mando = 16#0001`) y activa `OrdenAceptada` u `OrdenRechazada` (retenidas hasta el siguiente flanco).
4. La PC baja `aceptada`/`rechazada`; hasta verlo el FB no acepta otra orden. Una orden a la vez; las demás esperan (prioridad cancelar > pausar > reposo > reanudar > acusar > velocidad > punto > ejecutar). Sin `Parada` aparte: usar `Pausar`.

## Pasos en TIA Portal

1. Crear proyecto → agregar la CPU S7-1200 real (misma referencia y **firmware** que el equipo físico).
2. Propiedades de la CPU → PROFINET → dirección IP fija, p. ej. `192.168.125.10/255.255.255.0`. Anotar el *HW identifier* de la interfaz (normalmente 64) para `InterfaceId`.
3. No hace falta activar PUT/GET: se usa Open User Communication (TCON/TSEND/TRCV).
4. Árbol del proyecto → **Fuentes externas** → agregar los archivos, en este orden: `UDT_IRB120_Orden.udt`, `UDT_IRB120_Estado.udt`, `FB_IRB120_PC.scl`, `OB1_ejemplo.scl`. Clic derecho en cada uno → **Generar bloques desde fuente**.
5. Comprobar que `FB_IRB120_PC`, `FB_Celda_Ejemplo` y `DB_Celda_IRB120` tienen *Acceso optimizado al bloque* **desactivado** (propiedades → Atributos). Si falló el DB de instancia al importar, crearlo a mano como DB de instancia de `FB_Celda_Ejemplo`.
6. Si se usa el ejemplo, ajustar IP de la PC (`IpPC`), `InterfaceId`, y direcciones `%I`/`%Q` en `Main`. El OB1 ya llama al FB.
7. Compilar (hardware y software), cargar en la CPU. PC y PLC en la misma subred (la PC por ejemplo `192.168.125.100`).
8. En línea: observar `"DB_Celda_IRB120".plc.EnlacePC`, `ComEstado` (2 = conectado), `ComStatusUltimo`.

## Interfaz del FB (resumen)

- Entradas: `Conectar`, `Completo`, `IpPC`, `PuertoPC`, `InterfaceId`, `ConnID`, `TimeoutOrden`, `ReintentoConexion`, `Habilitar` (nivel, bit 0); órdenes por **flanco** `Ejecutar` (`Trayectoria`; en completo también `VelocidadPct`, `Repeticiones`), `Pausar`, `Reanudar`, `Cancelar`, `Reposo`, `FijarVelocidad` (`VelocidadPct`), `AnadirPunto` (`Pose`, solo completo), `AcusarError`.
- Salidas: `EnlacePC`, `AlarmaEnlace`, `OrdenPendiente`, `OrdenAceptada`, `OrdenRechazada`, `CodigoRechazo`, los bits de estado de la tabla anterior, extendido (`Fase`, `Tramo`, `Tramos`, `Vuelta`, `VelocidadVigente`, `Codigo`, `Q`, `PoseTCP`; en núcleo solo `Tramo` = `valor` y `Codigo`), `EstadoWord` y `MandoWord` (verlas en hex en la tabla de observación) y diagnóstico `ComBusy`, `ComError`, `ComStatus`, `ComStatusUltimo`, `ComEstado` (2 = conectado).
- Perro guardián: si el bit 15 de `estado` no cambia en 1 s → `EnlacePC = FALSE`, booleanos de estado a FALSE, se descartan órdenes retenidas. A los 5 s sin vida se reconecta; si la conexión falla: `TDISCON` y reintento cada 3 s.

## Probar sin robot ni PLC (nombres que integrará el equipo)

En la PC, dos terminales (carpeta `ros2_ws`):

```
./brazo.sh simulado          # brazo simulado (nodo irb120_panel_rws sin robot)
./brazo.sh plc --simulado    # nodos irb120_plc_s7 + irb120_celda, servidor TCP :2000
```

Sin PLC físico, con el simulador de PLC de la PC (habla el mismo telegrama que este FB):

```
./brazo.sh plc-simulador     # cliente TCP que hace de PLC contra la PC
```

Con PLC real: poner la IP de la PC en `IpPC`; abrir el puerto 2000 TCP en el firewall de la PC. Primera prueba sin movimiento: `Conectar` y mirar `EnlacePC`, `MandoWord` y `EstadoWord` (hex); luego `FijarVelocidad` y `Ejecutar` en simulado.

## Puntos a verificar al compilar

- Tipo `CONN_OUC` para `ConnID` y `HW_ANY := 64` como valor por defecto de entrada (si TIA lo rechaza, usar `Word` / constante en la llamada).
- Campos de `TCON_IP_v4` (`InterfaceId, ID, ConnectionType, ActiveEstablished, RemoteAddress.ADDR[1..4], RemotePort, LocalPort`) según firmware.
- Parámetro `LEN`: `UInt` en S7-1200 (en S7-1500 es `UDInt`); aquí es variable (36/68 o 4/4). `TRCV` con `ADHOC := FALSE`. Verificar que `LEN` no constante se acepte en el firmware.
- Asignaciones por bit `#tx.mando.%X15 := ...` y `UINT_TO_WORD`.
- Instancias `TON_TIME`, `R_TRIG`, `TCON`, `TSEND`, `TRCV`, `TDISCON` como multiinstancia dentro de FB no optimizado.
- Literales `16#0001` con `Word`, acceso por bit `.%X3` sobre `estado`, y constante de array `[192,168,125,100]` en el valor por defecto y en la llamada.
- Orden de importación (UDT → FB → ejemplo) y que el DB de instancia generado desde fuente sea no optimizado.
- Que `DONE`/`BUSY` de `TCON`/`TDISCON` se comporten como se supone al reconectar (la máquina de estados lee los resultados del ciclo anterior).

## Seguridad

- **El PLC y este enlace no sustituyen el paro de emergencia, el habilitador ni el Stop del IRC5.** `Pausar`/`Habilitar` por TCP solo pausa en el siguiente punto de paso y depende de la PC, la red y el software: no tiene categoría de seguridad (EN ISO 13849 / IEC 62061) y no debe usarse como función de seguridad.
- Cablear el paro de emergencia y las protecciones de la celda por el circuito de seguridad del IRC5 (y, si se requiere, un relé/PLC de seguridad aparte).
- La parada física del ejemplo usa contacto NC (`ParadaOK`): cable roto = parada.
- Probar siempre primero en simulado y con velocidad baja.
