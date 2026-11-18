#!/usr/bin/env bash
# Entrada única para los nodos físicos, sin depender de colcon/ros2 launch.
set -eo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
py="${ROS_PY312:-$HOME/ros_py312/bin/python}"
mode="${1:-ayuda}"
case "$mode" in
  comunicacion) module="irb120_conexion.arranque.comunicacion" ;;
  validar_fk) module="irb120_conexion.arranque.validacion_fk" ;;
  enlace) module="irb120_conexion.diagnostico.enlace" ;;
  rws_j6) module="irb120_control.rws_j6" ;;
  rws_mover) module="irb120_control.rws_mover" ;;
  respaldar) module="irb120_control.respaldo" ;;
  control_demo|control_vista|control_egm_lectura|control_robot) module="irb120_control.arranque" ;;
  panel) module="irb120_control.panel.arranque" ;;
  *)
    echo 'Uso: ./iniciar.sh {enlace|comunicacion|validar_fk|rws_j6|rws_mover|panel|control_demo|control_vista|control_egm_lectura|control_robot} [opciones]'
    echo 'Lectura: ./iniciar.sh comunicacion --host 192.168.125.1 --user "Default User" --ignore-joint-state'
    echo 'Sin robot: ./iniciar.sh control_demo'
    echo 'Mover desde la PC: ./iniciar.sh rws_mover estado | instalar [--auto] | interactivo | mover j6 +5 | terminar'
    echo 'Panel de ángulos + RViz: ./iniciar.sh panel   (sin robot: ./iniciar.sh panel --simulado)'
    exit 2 ;;
esac
shift
if [[ "$mode" == rws_* || "$mode" == respaldar ]]; then
  # Las herramientas RWS solo necesitan Python 3 y requests; no dependen de ROS.
  [[ -x "$py" ]] || py=python3
  export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
  exec "$py" -m "$module" "$@"
fi
if [[ ! -x "$py" || ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "Falta el entorno Python 3.12 ($py) o ROS 2 Jazzy."
  exit 2
fi
source /opt/ros/jazzy/setup.bash
if [[ "$mode" == panel ]]; then
  # Panel C++ de RViz (./brazo.sh compilar). Los tópicos de órdenes se quedan en esta PC:
  # nadie en la red Wi-Fi puede publicar en /irb120/panel/orden.
  [[ -f "$here/install/setup.bash" ]] && source "$here/install/setup.bash"
  export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
  # Dominios ROS separados: un panel simulado nunca comparte tópicos con el del robot real.
  if [[ " $* " == *" --simulado "* ]]; then export ROS_DOMAIN_ID=121; else export ROS_DOMAIN_ID=120; fi
fi
set -u
export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
if [[ "$mode" == control_* || "$mode" == panel ]]; then
  mkdir -p "$here/../salidas/control_articular/ros_logs"
  export ROS_LOG_DIR="$here/../salidas/control_articular/ros_logs"
fi
if [[ "$mode" == control_* ]]; then
  exec "$py" -m "$module" --modo "${mode#control_}" "$@"
fi
exec "$py" -m "$module" "$@"
