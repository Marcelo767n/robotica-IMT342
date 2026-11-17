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
