#!/usr/bin/env bash
# brazo.sh · todos los comandos para mover el ABB IRB 120 desde la PC (RWS + LabJointRws v5).
# Uso: ./brazo.sh <comando> [opciones]     ·     ./brazo.sh ayuda
# Cada comando que habla con el robot pide la contraseña RWS de "Default User"; no se guarda.
set -eo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
host="${ROBOT_HOST:-192.168.125.1}"
cmd="${1:-ayuda}"
[[ $# -gt 0 ]] && shift
run() { exec "$here/iniciar.sh" "$@"; }

ayuda() {
  cat <<EOF
brazo.sh · IRB 120 desde la PC        (robot: $host · cambiar con ROBOT_HOST=...)

  PREPARAR
    ./brazo.sh enlace          cable, IP de la PC, ping y puerto RWS (no pide contraseña)
    ./brazo.sh estado          modo, motores, RAPID, módulo y ángulos; dice qué FALTA
    ./brazo.sh eventos         estado + puntero de programa + últimos mensajes del FlexPendant (solo lectura)
    ./brazo.sh respaldar       copia los módulos RAPID del robot a rapid/respaldo_controlador/ (solo lectura)
    ./brazo.sh limpiar         vacía un objetivo pendiente     (llave AUTO, motores OFF)
    ./brazo.sh instalar        instala LabJointRws v5 (manual) (llave AUTO, motores OFF)
    ./brazo.sh instalar-auto   v5 que acepta modo AUTO         (llave AUTO, motores OFF, con autorización)

  TODO EN UNO (jueves)
    ./brazo.sh sesion          una contraseña: comprueba el enlace, guía AUTO (llave, módulo, Motors On,
                               arranque, «Iniciar») y abre RViz + panel + Estudio de trayectorias
    ./brazo.sh sesion --simulado  la misma sesión SIN robot (prueba): RViz + panel + Estudio, robot ficticio
    ./brazo.sh sesion --v4     lo mismo con el módulo de RESPALDO v4 (ya probado: solo articular, órdenes de ≤40°,
                               sin MoveL). Si la v5 no carga o no arranca en el robot, usar este.
                               También vale: ./brazo.sh panel --modulo v4
    ./brazo.sh estudio         solo el Estudio (CustomTkinter): trayectorias A→B→C→A, reglas, gráficas,
                               matemática en LaTeX. --demo sin panel · --puerto 8771 con el simulado
    ./brazo.sh analisis        la ventana de análisis anterior (tkinter, solo lectura)
    ./brazo.sh punto X Y Z R P Y  añade un punto al buzón del panel por el tópico de visión (mm, °, TCP;
                               --simulado para el panel simulado)

  CELDA CON PLC S7-1200 (nodos ROS 2 independientes; ver docs/PLC_S7_1200.md)
    ./brazo.sh plc             nodo irb120_plc_s7 (telegrama TCP, puerto 2000) + nodo irb120_celda (traductor)
                               junto al panel ya abierto (sesion/panel). --simulado con ./brazo.sh simulado
    ./brazo.sh nodos           grafo ROS 2 en vivo: nodos, tópicos, quién publica/escucha (--simulado, --png F)
    ./brazo.sh demo            TODO sin robot: RViz + panel simulado + Estudio (--plc: + celda PLC)
    ./brazo.sh plc-simulador   PLC simulado en esta PC (sin hardware): habilitar on · ejecutar 1 40 · pausar…

  MOVER (todo en RViz: panel «IRB 120» + control 3D de la pose)
    ./brazo.sh panel           robot real: ángulos, pose con cinemática inversa, Enviar al robot
    ./brazo.sh arrancar        solo AUTO: pone el puntero en ServidorPC y arranca RAPID (luego «Iniciar» en el FlexPendant)
    ./brazo.sh simulado        lo mismo sin robot, para practicar     (añadir --web para la página local)
    ./brazo.sh terminal        prompt de órdenes: j6 +5 · j3= 20 · abs 0 0 0 0 30 0 · estado · fin
    ./brazo.sh mover j6 +5     una sola orden y sale

  CERRAR
    ./brazo.sh terminar        termina ServidorPC en el robot (pcFin=1)

  OTROS
    ./brazo.sh compilar        compila el panel «IRB 120» de RViz (una vez, o tras cambiarlo)
    ./brazo.sh pruebas         pruebas offline (sin robot ni red)
    ./brazo.sh ayuda           esta ayuda y los pasos del FlexPendant

FLEXPENDANT · MANUAL (motores ON mientras se sostiene el habilitador)
  1. Llave en Manual (reducido). Editor de programas → Depurar → Comprobar programa.
  2. Depurar → PP a rutina → LabJointRws / ServidorPC. NUNCA Start con el puntero en main.
  3. Quickset → Velocidad 25 %.
  4. En la PC: ./brazo.sh panel (o terminal). En el FlexPendant pulsar «Conceder» (acceso remoto).
  5. Habilitador a media posición → Start → «Iniciar» antes de 30 s.

FLEXPENDANT · AUTO (motores ON fijos; solo con autorización y nadie al alcance del brazo)
  1. Llave AUTO, motores OFF: ./brazo.sh instalar-auto
  2. Llave Manual: Comprobar programa y PP a rutina → ServidorPC.
  3. Llave AUTO, confirmar el diálogo y botón Motors On del controlador.
     En AUTO el controlador lleva el puntero a main: en la PC ./brazo.sh arrancar (pone el puntero en
     ServidorPC, lo comprueba y arranca) y en el FlexPendant pulsar «Iniciar».
  4. En la PC: ./brazo.sh panel. Al terminar: llave AUTO, motores OFF, ./brazo.sh instalar.

PARAR EL ROBOT: soltar el habilitador, Stop, Motors Off o paro de emergencia.
Ctrl+C en la PC NO detiene el robot.
EOF
}

case "$cmd" in
  ayuda|help|-h|--help) ayuda ;;
  enlace)
    echo "== IP de la PC en la red del robot (192.168.125.x)"
    ip -br addr | grep -E '192\.168\.125\.' || echo "   NINGUNA: conectar el cable al puerto X2 Service y esperar el DHCP."
    echo "== Ping a $host"
    if ping -c 3 -W 1 "$host"; then echo "   OK"; else echo "   SIN RESPUESTA"; exit 2; fi
    echo "== Puerto RWS (HTTP 80)"
    if timeout 3 bash -c ": </dev/tcp/$host/80" 2>/dev/null; then echo "   ABIERTO: siguiente paso ./brazo.sh estado"
    else echo "   CERRADO"; exit 2; fi ;;
  estado)   run rws_mover estado --host "$host" "$@" ;;
  limpiar)  run rws_j6 limpiar --host "$host" "$@" ;;
  respaldar) run respaldar --host "$host" "$@" ;;
  instalar) run rws_mover instalar --host "$host" "$@" ;;
  instalar-auto)
    echo "Instala la variante que deja mover el robot en AUTO, SIN habilitador."
    echo "Solo con autorización del responsable y nadie dentro del alcance del brazo."
    read -r -p 'Escribir AUTO para continuar: ' answer
    [[ "$answer" == AUTO ]] || { echo "Cancelado."; exit 1; }
    run rws_mover instalar --auto --host "$host" "$@" ;;
  panel)    run panel --host "$host" "$@" ;;
  sesion)
    # --simulado: la misma sesión (RViz + panel + Estudio) con un robot ficticio, sin cable ni FlexPendant.
    for a in "$@"; do
      if [[ "$a" == --simulado ]]; then
        args=(); for b in "$@"; do [[ "$b" == --simulado || "$b" == --v4 ]] || args+=("$b"); done
        echo "SESIÓN DE PRUEBA SIN ROBOT: robot simulado, mismas ventanas que la sesión real."
        run panel --simulado --analisis "${args[@]}"
      fi
    done
    "$here/brazo.sh" enlace || { echo; echo 'Sin enlace con el robot: revisar cable y adaptador USB (conectarlo directo a la PC).'; exit 2; }
    run panel --auto --analisis --host "$host" "$@" ;;
  estudio)
    export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
    exec /usr/bin/python3 -m irb120_control.estudio "$@" ;;
  analisis)
    export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
    [[ "${IRB120_CON_XIM:-}" == 1 ]] || export XMODIFIERS=@im=none   # Tk + ibus (XIM) es muy lento; ver estudio/__init__.py
    exec /usr/bin/python3 -m irb120_control.analisis "$@" ;;
  simulado) run panel --simulado "$@" ;;
  punto)
    # Punto para la trayectoria por el tópico de visión: ./brazo.sh punto X Y Z ROLL PITCH YAW [--simulado]
    dominio=120; args=()
    for a in "$@"; do [[ "$a" == --simulado ]] && dominio=121 || args+=("$a"); done
    [[ ${#args[@]} -eq 6 ]] || { echo 'Uso: ./brazo.sh punto X Y Z ROLL PITCH YAW [--simulado]   (mm y grados, TCP en base_link)'; exit 2; }
    source /opt/ros/jazzy/setup.bash
    export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST ROS_DOMAIN_ID=$dominio
    export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
    exec "${ROS_PY312:-$HOME/ros_py312/bin/python}" -m irb120_control.vision.publicar_punto -- "${args[@]}" ;;
  plc)
    # Dos procesos independientes: irb120_plc_s7 (transporte) e irb120_celda (traductor). Ctrl+C cierra ambos.
    dominio=120; args=()
    for a in "$@"; do [[ "$a" == --simulado ]] && dominio=121 || args+=("$a"); done
    source /opt/ros/jazzy/setup.bash
    export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST ROS_DOMAIN_ID=$dominio
    export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
    py="${ROS_PY312:-$HOME/ros_py312/bin/python}"
    "$py" -m irb120_control.celda.nodo_celda &
    celda=$!
    trap 'kill $celda 2>/dev/null; wait $celda 2>/dev/null' EXIT INT TERM
    "$py" -m irb120_control.plc.nodo_plc "${args[@]}" ;;
  nodos)
    # Grafo ROS 2 en vivo (nodos, tópicos, quién publica y escucha). --simulado para el panel simulado.
    dominio=120; args=()
    for a in "$@"; do [[ "$a" == --simulado ]] && dominio=121 || args+=("$a"); done
    source /opt/ros/jazzy/setup.bash
    export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST ROS_DOMAIN_ID=$dominio
    export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
    exec "${ROS_PY312:-$HOME/ros_py312/bin/python}" -m irb120_control.grafo_ros "${args[@]}" ;;
  demo)
    # Todo sin robot: RViz + panel simulado + Estudio. Con --plc, además la celda PLC simulada en segundo plano.
    args=(); conplc=0
    for a in "$@"; do [[ "$a" == --plc ]] && conplc=1 || args+=("$a"); done
    if [[ $conplc == 1 ]]; then
      log="$here/../salidas/demo"; mkdir -p "$log"
      "$here/brazo.sh" plc --simulado > "$log/plc_nodos.log" 2>&1 &
      plc=$!
      trap 'kill $plc 2>/dev/null; wait $plc 2>/dev/null' EXIT INT TERM
      echo "Celda PLC simulada en segundo plano (registro: salidas/demo/plc_nodos.log)."
      echo "En OTRA terminal: ./brazo.sh plc-simulador   (habilitar on · ejecutar 1 30 · pausar · reanudar)"
    fi
    echo "Para ver los nodos conectados: ./brazo.sh nodos --simulado --png salidas/grafo_ros.png"
    "$here/brazo.sh" simulado --analisis "${args[@]}" ;;
  plc-simulador)
    export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
    exec /usr/bin/python3 -m irb120_control.plc.simulador "$@" ;;
  terminal) run rws_mover interactivo --host "$host" "$@" ;;
  arrancar) run rws_mover arrancar --host "$host" "$@" ;;
  eventos)  run rws_mover eventos --host "$host" "$@" ;;
  mover)
    [[ $# -gt 0 ]] || { echo 'Uso: ./brazo.sh mover j6 +5   |   mover j3= 20   |   mover abs J1 J2 J3 J4 J5 J6'; exit 2; }
    run rws_mover mover "$@" --host "$host" ;;
  terminar) run rws_mover terminar --host "$host" "$@" ;;
  compilar)
    source /opt/ros/jazzy/setup.bash
    cd "$here"
    exec colcon build --packages-select irb120_rviz_panel "$@" ;;
  pruebas)
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
    py="${ROS_PY312:-$HOME/ros_py312/bin/python}"; [[ -x "$py" ]] || py=python3
    cd "$here"
    "$py" -m unittest discover -s src/irb120_control/test -p 'test_r[we]*.py' \
      && "$py" -m unittest discover -s src/irb120_control/test -p 'test_panel*.py' \
      && "$py" -m unittest discover -s src/irb120_control/test -p 'test_sesion.py' \
      && "$py" -m unittest discover -s src/irb120_control/test -p 'test_trayectorias.py' \
      && /usr/bin/python3 -m unittest discover -s src/irb120_control/test -p 'test_analisis.py' \
      && /usr/bin/python3 -m unittest discover -s src/irb120_control/test -p 'test_estudio*.py' \
      && "$py" -m unittest discover -s src/irb120_control/test -p 'test_plc.py' \
      && "$py" -m unittest discover -s src/irb120_control/test -p 'test_celda.py' ;;
  *) echo "Comando desconocido: $cmd"; echo; ayuda; exit 2 ;;
esac
