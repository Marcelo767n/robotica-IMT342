#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_dir="${project_dir}/ros2_ws"

if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

if ! command -v colcon >/dev/null 2>&1; then
  echo "Falta colcon. Instala: sudo apt install python3-colcon-common-extensions"
  exit 2
fi

cd "${workspace_dir}"
colcon build --symlink-install --packages-select irb120_hito1
# shellcheck disable=SC1091
source "${workspace_dir}/install/setup.bash"
colcon test --packages-select irb120_hito1 --event-handlers console_direct+
colcon test-result --verbose
ros2 run irb120_hito1 verify_model
