"""Vista RViz del panel: configuración y procesos robot_state_publisher (×2) y rviz2."""
import os
from pathlib import Path
import subprocess

import yaml

RSP = '/opt/ros/jazzy/lib/robot_state_publisher/robot_state_publisher'
TF_REMAP = ['-r', '/tf:=/irb120/control/tf', '-r', '/tf_static:=/irb120/control/tf_static']
PANEL_PACKAGE = 'irb120_rviz_panel'
PANEL_CLASS = 'irb120_rviz_panel/PanelIRB120'


def panel_disponible():
    """¿Está compilado e indexado el panel C++ (./brazo.sh compilar + source install/setup.bash)?"""
    for prefix in filter(None, os.environ.get('AMENT_PREFIX_PATH', '').split(':')):
        if Path(prefix, 'share/ament_index/resource_index/packages', PANEL_PACKAGE).exists():
            return True
    return False


def preparar(folder, con_panel=True):
    """Dos modelos (medido sólido, objetivo naranja), controles 3D, texto de estado y panel IRB 120."""
    from irb120_control.arranque import prepare_models
    folder = prepare_models(folder)
    gemelo_blanco(folder / 'medido.yaml')
    config = yaml.safe_load((folder / 'control.rviz').read_text())
    manager = config['Visualization Manager']
    names = {'rviz_default_plugins/InteractiveMarkers': 'CONTROL 3D · arrastrar la pose / clic derecho = menú',
             'rviz_default_plugins/Marker': 'Estado del panel'}
    for display in manager['Displays']:
        if display.get('TF Prefix') == 'medido':
            display['Name'] = 'ROBOT · postura medida'
        elif display.get('TF Prefix') == 'objetivo':
            display['Name'] = 'OBJETIVO · naranja'
        elif display.get('Class') in names:
            display['Name'] = names[display['Class']]
    if con_panel:
        # Todo el lateral para el panel IRB 120. «Displays» y «Views» se reabren desde el menú Panels;
        # la cámara se mueve con el ratón.
        config['Panels'] = [{'Class': PANEL_CLASS, 'Name': 'IRB 120'}]
        config['Window Geometry'].update(Width=1700, Height=1000)
    (folder / 'panel.rviz').write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    return folder


def gemelo_blanco(params):
    """El gemelo medido en blanco grisáceo (como el IRB 120 real); el objetivo sigue naranja translúcido."""
    import xml.etree.ElementTree as ET
    values = yaml.safe_load(params.read_text())
    ros = values['/**']['ros__parameters']
    root = ET.fromstring(ros['robot_description'])
    for color in root.findall('.//material/color'):
        color.set('rgba', '0.86 0.86 0.84 1')
    ros['robot_description'] = ET.tostring(root, encoding='unicode')
    params.write_text(yaml.safe_dump(values))


def lanzar(folder, rviz=True):
    """Arranca los procesos auxiliares; devuelve la lista para cerrarlos con detener()."""
    children = []
    for name in ('medido', 'objetivo'):
        children.append(subprocess.Popen(
            [RSP, '--ros-args', '--params-file', str(folder / (name + '.yaml')), '-r', f'__node:=irb120_rsp_{name}',
             '-r', f'joint_states:=/irb120/control/{name}/joint_states',
             '-r', f'/robot_description:=/irb120/control/{name}/robot_description', *TF_REMAP]))
    if rviz:
        children.append(subprocess.Popen(['rviz2', '-d', str(folder / 'panel.rviz'), '--ros-args', *TF_REMAP]))
    return children


def detener(children):
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
