#!/usr/bin/env bash
# brazo.sh · todos los comandos para mover el ABB IRB 120 desde la PC (RWS + LabJointRws v2).
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
    ./brazo.sh limpiar         vacía un objetivo pendiente     (llave AUTO, motores OFF)
    ./brazo.sh instalar        instala LabJointRws v2 (manual) (llave AUTO, motores OFF)
    ./brazo.sh instalar-auto   v2 que acepta modo AUTO         (llave AUTO, motores OFF, con autorización)

  MOVER (todo en RViz: panel «IRB 120» + control 3D de la pose)
    ./brazo.sh panel           robot real: ángulos, pose con cinemática inversa, Enviar al robot
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
  3. Llave AUTO, confirmar el diálogo, botón Motors On del controlador, Start, «Iniciar».
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
  instalar) run rws_mover instalar --host "$host" "$@" ;;
  instalar-auto)
    echo "Instala la variante que deja mover el robot en AUTO, SIN habilitador."
    echo "Solo con autorización del responsable y nadie dentro del alcance del brazo."
    read -r -p 'Escribir AUTO para continuar: ' answer
    [[ "$answer" == AUTO ]] || { echo "Cancelado."; exit 1; }
    run rws_mover instalar --auto --host "$host" "$@" ;;
  panel)    run panel --host "$host" "$@" ;;
  simulado) run panel --simulado "$@" ;;
  terminal) run rws_mover interactivo --host "$host" "$@" ;;
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
    exec "$py" -m unittest discover -s src/irb120_control/test -p 'test_[rp][wa]*.py' ;;
  *) echo "Comando desconocido: $cmd"; echo; ayuda; exit 2 ;;
esac
