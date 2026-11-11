# De la demo RViz al ABB físico

Estado 04/11/2026: lectura RWS/FK y demo verificadas. El usuario dispone de FlexPendant, sin RobotStudio instalado ni experiencia previa con RAPID. La opción EGM está registrada en el ABB, pero todavía no se ha probado una sesión EGM física. Esta guía prepara esa sesión; no es un acta GO.

## Qué hace cada parte

| Parte | Función en nuestra prueba |
|---|---|
| RViz | Elegir un eje y previsualizar un objetivo; ARMAR y EJECUTAR son acciones separadas |
| Python | Validar objetivo, generar LSPB lento y comparar referencia con medición |
| EGM — Externally Guided Motion | Intercambiar posiciones articulares entre PC y controlador mediante UDP/Protobuf |
| RAPID | Programa que ejecuta el ABB y habilita/prepara la sesión EGM |
| Controlador ABB | Ejecutar su control interno y mover los motores siguiendo la referencia aceptada |
| RobotStudio | Herramienta de ingeniería para editar/verificar RAPID, configurar y respaldar el controlador |

La ruta será **RViz → supervisor/LSPB Python → EGM → controlador ABB → brazo**, con ángulos medidos de regreso. Se transmiten seis posiciones; solo cambia el eje seleccionado y los otros cinco conservan su referencia. EGM no calcula nuestra IK ni reemplaza el control interno del ABB. Después podremos sustituir el objetivo manual por la salida de visión + IK, manteniendo esta misma ruta validada.

RWS, usado para la lectura y la FK, funciona por HTTP. Haber leído bien mediante RWS no configura el receptor de órdenes EGM. EGM usa otro canal: primero el ABB envía un paquete a la IP/puerto UDP configurados para la PC. Muchas actualizaciones por segundo permiten una rampa suave; no implican una velocidad mecánica alta. La plantilla propone 8 ms (125 Hz); debe verificarse en el controlador.

## No hace falta instalar RAPID en Ubuntu

RAPID es el lenguaje del controlador ABB. Podemos redactar un módulo `.mod` en esta PC, pero el ABB debe comprobarlo/cargarlo antes de ejecutarlo. RobotStudio facilita editarlo, simularlo y revisar la configuración.

Hay dos vías:

1. **Recomendada: una PC Windows con RobotStudio Freemium.** ABB incluye editor RAPID, editor de configuración y backup/restore en Freemium. No necesitamos comprar Premium para esas funciones. ROS, RViz y Python permanecen en Ubuntu; Windows se usa para la puesta en marcha. Las notas de RobotStudio 2026.1 archivadas en el proyecto indican Windows 11 o posterior. El controlador virtual debe corresponder al sistema real **RobotWare 6.12.01.00** y sus opciones, usando el respaldo; instalar una versión reciente de RobotStudio no requiere actualizar RobotWare del brazo.
2. **FlexPendant:** permite cargar módulos y editar parámetros del sistema con permisos adecuados. Es una alternativa a estudiar con el responsable del laboratorio. No prueba por sí sola que la plantilla EGM esté validada ni que los parámetros necesarios sean editables en nuestra sesión. El manual EGM de ABB describe el procedimiento de configuración UDPUC con RobotStudio; por eso es la vía recomendada para el primer montaje.

La universidad también puede solicitar la licencia educativa de ABB, disponible sin coste para instituciones que cumplan sus condiciones. Esa solicitud no es necesaria para empezar con las funciones Freemium citadas.

## Lo siguiente que haremos en el controlador

1. **Inventario y respaldo.** Con el responsable, guardar el programa y la configuración actuales; revisar tareas, herramienta/carga, opciones y permisos. En FlexPendant se pueden localizar, sin cambiar nada, **Program Editor**, **Backup and Restore** y **Control Panel → Configuration**. Nuestra lectura con `Default User` no demuestra permisos para escribir programas o parámetros.
2. **Revisar la plantilla en el sistema correspondiente.** El archivo [IRB120_EGM_Prueba.mod](../../ros2_ws/src/irb120_control/rapid/IRB120_EGM_Prueba.mod) sigue pendiente de compilación y revisión del handshake en RW6.12. Su indicador de revisión permanece `FALSE`. No sustituir el programa existente ni activar esa plantilla sin resolverlo. Debe revisarse también la condición ABB de inicio/fin en un punto `fine` y la primera maniobra después de un reinicio.
3. **Configurar el destino EGM.** En el controlador, revisar **Communication → Transmission Protocol → UDPUC**: nombre del dispositivo, IP actual de la PC, puerto UDP y ruta/interfaz autorizadas. Luego revisar el perfil **Motion → External Motion Interface Data**. Los nombres, puerto y demás valores se registran desde la configuración real; no se adivinan. El reinicio que requiera un cambio se coordina con el responsable.
4. **Recepción sin consignas.** Iniciar desde el controlador la fase de streaming revisada. En Ubuntu, ejecutar `control_egm_lectura` con esa IP/puerto. Verificar los seis ángulos contra FlexPendant, cadencia y estados del ABB. Este modo no transmite posiciones de comando.
5. **Mantenimiento sin desplazamiento.** Tras revisar límites, postura, herramienta, recorrido y comportamiento de parada, completar la ficha real y el GO del laboratorio. Iniciar `control_robot`, recibir estado y ARMAR con primera referencia igual a la postura medida. Verificar el paso a Guidance y el seguimiento sin solicitar otro ángulo.
6. **Primer desplazamiento de un eje: 1°.** Verificar sentido, cinco ejes fijos, seguimiento y cancelación. Registrar resultado. El código físico actual mantiene ese máximo inicial.
7. **Ampliación posterior: 5°, luego 10°.** Revisar cada recorrido completo y ampliar coherentemente la ventana PC y el límite de desviación ABB. La plantilla contiene `MaxPosDeviation:=2`: no admite planificar 10° cambiando solamente un menú. Tampoco basta con encadenar movimientos pequeños para eludir la ventana de sesión. Esta ampliación física todavía no está implementada ni ensayada.

Los límites angulares no detectan colisiones ni garantizan recorrido libre. La velocidad/aceleración de referencia se comprueban en Python; el seguimiento físico y el comportamiento de parada deben medirse en el ABB.

## Comandos que corresponden a cada fase

Desde `proyecto/ros2_ws`, una sesión cada vez:

```bash
# Red/RWS ya conocidos; no inicia motores ni RAPID.
./iniciar.sh enlace --ping
./iniciar.sh control_vista --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

Solo cuando UDPUC esté configurado y el ABB esté enviando streaming, sustituir los dos marcadores por los valores comprobados:

```bash
./iniciar.sh control_egm_lectura --host 192.168.125.1 --bind-ip IP_PC_VERIFICADA --egm-port PUERTO_VERIFICADO
```

Después de completar la ficha real y revisar la sesión:

```bash
./iniciar.sh control_robot --config ../salidas/control_articular/sesion_robot.yaml --comprobar
./iniciar.sh control_robot --config ../salidas/control_articular/sesion_robot.yaml --habilitar-envio
```

El segundo comando no carga RAPID ni enciende motores. Espera feedback y comienza desarmado. La ficha de ejemplo incompleta se rechaza: todavía faltan datos del controlador y del ensayo.

## Recorrido mayor disponible ahora en la demo

Elegir un comando:

```bash
./iniciar.sh control_demo --recorrido-demo-deg 5
./iniciar.sh control_demo --recorrido-demo-deg 10
```

En el menú **Ajustar objetivo**, usar ±5°/±10° según el modo, revisar y después ARMAR/EJECUTAR. La referencia conserva **0.5°/s** y **0.5°/s²**. Nuestro LSPB tarda aproximadamente **11 s para 5°** y **21 s para 10°**, más asentamiento. Estos recorridos ampliados son exclusivamente simulados; el parámetro se rechaza en modos conectados al ABB.

Fuentes: [ABB, manual EGM RW6, capítulos 1–3 y referencia RAPID](https://library.e.abb.com/public/f63dc4031d194a58be058eb657441180/3HAC073319%20AM%20Externally%20Guided%20Motion%20RW6-en.pdf), [ABB, especificación RobotStudio, Freemium/Premium](https://library.e.abb.com/public/194220a64e8b4b8983d176cd852845e4/3HAC026932-001_en_AN_Product%20Specification%2C%20RobotStudio.pdf), [descargas ABB](https://www.abb.com/global/en/areas/robotics/downloads), [licencia educativa ABB](https://www.abb.com/global/en/areas/robotics/products/software/robotstudio-suite/robotstudio-license), [manual ABB IRC5 con FlexPendant, copia universitaria](https://bpb-us-e1.wpmucdn.com/wp.txstate.edu/dist/3/3147/files/2020/12/ABB-Robot-Operation-Manual.pdf). La revisión F de EGM describe RW6.14 y la copia del manual FlexPendant RW6.08: sus instrucciones deben contrastarse con el RW6.12 real; no constituyen una compilación o prueba en nuestro sistema.
