#!/usr/bin/env bash
# Compatibilidad: el arranque común vive en el paquete irb120_conexion.
set -eo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$here/../ros2_ws/iniciar.sh" comunicacion "$@"
