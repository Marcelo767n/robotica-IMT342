# Guía G1 para el día de laboratorio: lectura del ABB sin movimiento

Preparada el 29 de octubre de 2026 a partir del [traspaso de ChatGPT](TRASPASO_CLAUDE_2026-10-22.md) (tarea P0). Cubre solo **G1: enlace Ethernet y lectura RWS de solo lectura**. No mueve el robot, no inicia RAPID, motores ni EGM.

## Qué se comprobó antes de escribirla

| Hecho | Estado |
|---|---|
| Adaptador USB-Ethernet | Detectado: `enx00e04c36006d` (Realtek RTL8152, 10/100). Sin cable enchufado |
| Wi-Fi y Docker | `172.22.24.0/21` y `172.17.0.0/16`: no chocan con la red del robot `192.168.125.0/24` |
| Perfil NetworkManager existente | `Conexión cableada 1`: atado al adaptador, DHCP, con autoconexión y **sin** `never-default`. Por eso esta guía usa perfiles propios |
| `requests` y Python | Python 3.14.4 y `requests` 2.32.5 del sistema; no hace falta entorno virtual |
| Pruebas offline | 18 pasan (8 del lector RWS y 10 de la verificación de enlace) |
| Enlace con el robot | **No probado.** Ningún paquete se ha enviado al controlador |

## Reglas del día

1. **Con el operador del laboratorio presente.** Él confirma el puerto antes de enchufar.
2. Solo el puerto etiquetado **X2 Service 10/100**. No uses LAN/WAN ni la red institucional.
3. No desconectes cables del gabinete ni del FlexPendant, ni toques joystick o botón de habilitación.
4. No cambies opciones, calibración ni programas. No hagas ni restaures respaldos.
5. Mantén el Wi-Fi como está. Si algo falla, **detente y anota**; no improvises comandos.
6. Usuario y contraseña UAS: los da el operador. ABB usa en sus ejemplos un usuario predeterminado de fábrica ([`fuentes/rws_intro.html`](fuentes/rws_intro.html), sección Authentication), pero el laboratorio pudo haberlo cambiado. No pruebes contraseñas al azar. **Nunca los escribas en archivos.**

## Antes de ir (en casa, 5 minutos)

Desde la carpeta `proyecto/`:

```bash
python3 -m unittest discover -s scripts/tests -t scripts/tests
python3 scripts/g1_verificar_enlace.py
```

Con Python 3.14 hace falta `-t scripts/tests`. Sin cable, la segunda debe dar `PASS adaptador` y `FAIL cable`. Crea los dos perfiles de red (no se activan solos y no ponen ruta predeterminada):

```bash
nmcli connection add type ethernet ifname enx00e04c36006d con-name abb-g1-dhcp connection.autoconnect no ipv4.method auto ipv4.never-default yes ipv6.method disabled
nmcli connection add type ethernet ifname enx00e04c36006d con-name abb-g1 connection.autoconnect no ipv4.method manual ipv4.addresses 192.168.125.2/24 ipv4.never-default yes ipv6.method disabled
```

La sintaxis se validó con `nmcli --offline`, sin tocar tu configuración. Si el nombre del adaptador cambia, míralo con `ip -br link`. Lleva el cable, el adaptador y esta guía impresa o abierta en otro dispositivo.

## En el laboratorio

| # | Acción | Qué esperar | Si falla |
|---|---|---|---|
| 1 | El operador confirma el puerto **X2 Service**. Conecta adaptador ↔ X2 | Luz de enlace en el adaptador | Revisa el puerto con el operador |
| 2 | `python3 scripts/g1_verificar_enlace.py` | `PASS adaptador`, `PASS cable` | Ver tabla de fallos |
| 3 | `nmcli connection up abb-g1-dhcp` y espera 15 s | Se activa la conexión | Siguiente fila |
| 4 | Si no llegó IP: `nmcli connection down abb-g1-dhcp` y `nmcli connection up abb-g1` | IP `192.168.125.2/24` | Pide al operador la pantalla de red del FlexPendant |
| 5 | `python3 scripts/g1_verificar_enlace.py --ping` | `PASS ip`, `PASS ruta`, `PASS ping` | **Si la ruta sale por otra interfaz, no sigas** |
| 6 | `python3 scripts/abb_lectura_rws.py --output docs/conexion_abb/evidencias/g1_inventario_pc_AAAA-MM-DD.json` | JSON con Ethernet presente | Es solo local |
| 7 | `python3 scripts/abb_lectura_rws.py --host 192.168.125.1 --user USUARIO --output docs/conexion_abb/evidencias/g1_rws_AAAA-MM-DD.json` | Pide la contraseña sin mostrarla; termina con código 0 y `"state": "rws_joint_snapshot_observed"` | Ver tabla de fallos |
| 8 | **Dos personas**: una lee `rax_1_to_6` del JSON; la otra, los ejes del FlexPendant (el operador indica dónde verlos) | Diferencia por eje menor que la tolerancia | Repite con el robot detenido; si persiste, anota ambas lecturas |
| 9 | Fotografía el campo de ejes del FlexPendant junto a la hora | Evidencia del contraste | — |
| 10 | Desconecta. `nmcli connection down abb-g1` y `nmcli connection delete abb-g1 abb-g1-dhcp` | Perfiles eliminados | — |

Reemplaza `USUARIO` por el dado por el operador y `AAAA-MM-DD` por la fecha. **Tolerancia propuesta para el paso 8: 0,1° por eje**, con el robot detenido. Es una propuesta del equipo: confírmala con el docente **antes** del ensayo y anótala. La lectura queda registrada en grados (convención `jointtarget` de RAPID).

## Qué hacer ante cada fallo

| Síntoma | Qué significa | Acción |
|---|---|---|
| `FAIL adaptador` | El sistema no ve el adaptador | Reenchufa; `lsusb` debe listar Realtek RTL8152 |
| `FAIL cable` | Sin enlace físico | Cable firme en ambos extremos, puerto correcto, controlador encendido |
| `FAIL ip` tras 15 s | No hubo DHCP | Perfil estático `abb-g1` (paso 4) |
| `FAIL ip` por misma IP del controlador | Conflicto de direcciones | Usa `192.168.125.2/24`, nunca `.1` |
| `FAIL ruta` | El tráfico saldría por otra interfaz | Detente; revisa `ip route` y los perfiles |
| `AVISO internet` | El adaptador quedó como ruta predeterminada | Usa los perfiles con `never-default` |
| `FAIL ping` con IP y ruta correctas | ICMP filtrado o IP distinta | Verifica la IP en el FlexPendant; la lectura RWS puede seguir si la IP está confirmada |
| `connection_or_service_not_verified` | Timeout: RWS no responde | IP, puerto 80, servicio; no demuestra falta de licencia |
| `http_reachable_authentication_or_permission_pending` | HTTP 401 o 403 | Usuario, contraseña o permiso UAS: pídelos al operador |
| `rws_identity_not_verified` | Responde HTTP pero no parece RWS | Puerto o equipo equivocado |
| `rws_system_observed` sin lectura de ejes | No se confirmó `ROB_1` o el `jointtarget` | Revisa `resources` en el JSON y repite con `--mechunit` |

Código de salida 2 significa que la prueba no alcanzó el estado final; no es un daño al robot.

## Qué registrar (bitácora)

Hora, comando, resultado, interpretación, siguiente acción. Guarda los dos JSON y la foto. Los JSON no contienen contraseñas, pero el inventario local incluye direcciones MAC e IP de tu PC: revisa antes de subirlo a un repositorio público.

## Qué se considera logrado

- **G1-A:** la ruta hacia `192.168.125.1` sale por Ethernet (`PASS ruta`).
- **G1-B:** respuesta RWS del ABB físico `120-101516`, unidad `ROB_1`, seis valores finitos y coincidencia con el FlexPendant bajo la tolerancia acordada.

Con eso **no** se demuestra que EGM funcione ni que el driver sirva. Siguen: G2 (FK/IK/J contra la lectura real), puente de estado ROS 2 y, solo con el GO del operador y el docente, G3. Ver [`README.md`](README.md).
