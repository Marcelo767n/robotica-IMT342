# Sesión del 16/11/2026: primer movimiento real desde la PC

Primera vez que el ABB IRB 120 se movió con órdenes enviadas desde la PC Linux, por RWS y el módulo RAPID `LabJointRws` v2. Antecedente: el intento del 10/11 no consiguió movimiento ([avance](AVANCE_2026-11-10.md), [cierre](../conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md)).

## Resultado

| Dato | Valor |
|---|---|
| Órdenes enviadas | 24 |
| Órdenes con llegada confirmada (`rbCodigo = 2`) | 24 |
| Ejes movidos, en orden | J6, J1, J4, J3 y J2 |
| Error máximo por orden | ≤ 0,016° |
| J5 | `HTTP 403` tras detener RAPID; corregido en el código, falta repetirlo en el robot |
| Registro | `salidas/control_articular/rws_mover/interactivo_20261117_012222_264923Z.jsonl` |

Ejemplo (orden 1): J6 de 3,565° a 8,565°, llegada confirmada con error de 0,004° en unos 4,4 s.

## Qué se hizo

1. Se instaló el módulo `LabJointRws` v2 en el controlador por RWS (`./brazo.sh instalar`, llave en AUTO y motores apagados).
2. Con la llave en manual reducido, se apuntó el puntero a `ServidorPC` y el operador concedió RMMP en el FlexPendant.
3. Se arrancó `ServidorPC` con el habilitador y se enviaron las órdenes desde la PC, una a la vez.

## Problemas encontrados y corregidos

| Síntoma | Causa | Corrección |
|---|---|---|
| `estado` decía `módulo no_verificado`; `limpiar` e `instalar` se negaban | El controlador devuelve el módulo con el valor actual de cada PERS, y la huella del módulo cambiaba | La huella restituye el valor inicial de las PERS antes del hash; sigue detectando cambios de código |
| Un `j6 +5` salió como dos órdenes de 2,5° | La lectura dio 5,000004° y el redondeo hacia arriba partía la orden | Tolerancia de 0,05° en la comprobación de paso, sin superar los 10° del RAPID |
| `HTTP 403` al escribir el objetivo de J5, tras detener y reanudar RAPID | El sondeo seguía en `GRANTED`, pero el controlador ya no aceptaba el permiso | Ante un 403 se descarta el permiso y el siguiente envío vuelve a pedir RMMP |

## Pendiente tras la sesión

- Repetir J5 en el robot.
- Probar el modo AUTO y el panel de RViz con el robot real (hasta entonces solo con robot simulado).

## Continuación del 17/11/2026 (sin robot)

| Cambio | Detalle |
|---|---|
| Control desde RViz | Panel C++ «IRB 120» ([`irb120_rviz_panel`](../../ros2_ws/src/irb120_rviz_panel/README.md)) y control 3D con marcador arrastrable y cinemática inversa |
| Código modularizado | El panel Python quedó en `ros2_ws/src/irb120_control/irb120_control/panel/` |
| Comandos unificados | [`ros2_ws/brazo.sh`](../../ros2_ws/brazo.sh): `estado`, `instalar`, `panel`, `simulado`, `terminal`, `mover`, `terminar`, `compilar`, `pruebas` |

Seguridad: soltar el habilitador, Stop o el paro de emergencia detienen el robot. Ctrl+C en la PC no lo detiene.

## Sesión del 17/11/2026 (tarde): verificación, modo AUTO y v3

Se probó el control desde RViz con el robot real. La verificación pedida por el ingeniero (modelo propio frente al controlador ABB, `robtarget` en `tool0`) dio **0,00007 mm** y **0,000007°** de diferencia.

### Problemas y correcciones

1. **El robot se quedaba antes del objetivo.** Causa: con ejes de más de 100° el ABB devuelve el objetivo con 6 cifras (p. ej. 101.664) y la PC lo comparaba con más decimales. La lectura de vuelta no coincidía y la orden no se enviaba (4 veces en el registro). Corrección: objetivos con 3 decimales, lectura de vuelta con 0,002° de tolerancia, cada tramo replanificado desde la postura real y orden de corrección final si faltan más de 0,02°.
2. **Pausas cada 5-10°.** Corrección: módulo `LabJointRws` v3 (hasta 45° por orden; la PC usa 40°; AccSet 50, 50).
3. **Al pasar la llave a AUTO, el puntero iba a `main`.** El controlador lleva el puntero a `main` (de `MainModule`, de otro grupo) y el FlexPendant no permite «PP a rutina». Corrección: `./brazo.sh arrancar` pone el PP en LabJointRws/ServidorPC por RWS (set-pp-routine), lo lee de vuelta y solo entonces arranca RAPID; el operador confirma con «Iniciar».
4. **El adaptador USB-Ethernet se desconectó con el hub USB.** Se resolvió conectándolo directo a la laptop.

### Resultado en AUTO (sin habilitador)

De [7,02; 10,22; −33,33; 48,94; −1,48; 103,57]° a la posición 0 en 3 órdenes (J6 recorría 103,6°), ~10,5 s cada una, código 2 (llegada) y error final 0,0046°. El usuario lo describió como fluido.

### Copia del programa del robot (`./brazo.sh respaldar`)

`Module1` está vacío y aparecieron `MainModule`, `IMT342_DestinoDirecto` e `IMT342_EgmEnlace` (de otro grupo). La versión anterior de Module1 está en `ros2_ws/src/irb120_control/rapid/respaldo_controlador/2026-11-16/`.
