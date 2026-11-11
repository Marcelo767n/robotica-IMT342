"""Arranque fuente: RViz nativo + lectura/EGM + supervisor. No inicia RAPID/motores."""
import argparse
import fcntl
from datetime import datetime, timezone
import getpass
import ipaddress
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np
import yaml
from irb120_conexion.rutas import PROJECT
from irb120_conexion.modelo.preparar import prepare
from irb120_control.supervisor import Policy,Supervisor,Rejected


def prepare_models(folder):
    folder=prepare(folder)
    params=yaml.safe_load((folder/'robot_state_publisher.yaml').read_text())
    original=params['/**']['ros__parameters']['robot_description']
    for name,prefix in [('medido','medido/'),('objetivo','objetivo/')]:
        urdf=original
        if name=='objetivo':
            root=ET.fromstring(urdf)
            for color in root.findall('.//material/color'):color.set('rgba','1 0.5 0.05 0.45')
            urdf=ET.tostring(root,encoding='unicode')
        values={'/**':{'ros__parameters':{'robot_description':urdf,'frame_prefix':prefix,'publish_frequency':30.0}}}
        (folder/(name+'.yaml')).write_text(yaml.safe_dump(values))
    config=yaml.safe_load((folder/'gemelo.rviz').read_text())
    displays=config['Visualization Manager']['Displays']
    model=next(d for d in displays if d.get('Class')=='rviz_default_plugins/RobotModel')
    config['Visualization Manager']['Displays']=[displays[0]]
    import copy
    for name,alpha in [('medido',1.0),('objetivo',.45)]:
        d=copy.deepcopy(model);d['Name']='MEDIDO · '+name if name=='medido' else 'VISTA PREVIA · objetivo naranja'
        d['Description Topic']['Value']=f'/irb120/control/{name}/robot_description'
        # El URDF conserva nombres locales; RSP publica cada árbol con frame_prefix.
        d['TF Prefix']=name
        d['Alpha']=alpha;config['Visualization Manager']['Displays'].append(d)
    config['Visualization Manager']['Displays'] += [
        {'Class':'rviz_default_plugins/InteractiveMarkers','Name':'CONTROL J1–J6 · clic derecho',
         'Enabled':True,'Interactive Markers Namespace':'/irb120/control/articulacion'},
        {'Class':'rviz_default_plugins/Marker','Name':'Estado de la prueba','Enabled':True,
         'Topic':{'Value':'/irb120/control/texto','Depth':10,'History Policy':'Keep Last',
                  'Reliability Policy':'Reliable','Durability Policy':'Volatile'}}]
    config['Visualization Manager']['Views']['Current'].update(Distance=2.0,Pitch=.4,Yaw=.75)
    config['Window Geometry'].update(Height=900,Width=1400)
    (folder/'control.rviz').write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False))
    return folder


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modo',choices=('demo','vista','egm_lectura','robot'),required=True)
    parser.add_argument('--host',default='192.168.125.1')
    parser.add_argument('--user',default='Default User')
    parser.add_argument('--ignore-joint-state',action='store_true')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--bind-ip',help='IP actual de la PC para recepción EGM de solo lectura')
    parser.add_argument('--egm-port',type=int,help='Puerto UDPUC verificado para recepción EGM de solo lectura')
    parser.add_argument('--habilitar-envio',action='store_true',help='Requerido además del GO para modo robot; no arma automáticamente')
    parser.add_argument('--comprobar',action='store_true',help='Solo validar ficha/dependencias; no abrir UDP ni RViz')
    parser.add_argument('--no-rviz',action='store_true')
    parser.add_argument('--recorrido-demo-deg',type=int,choices=(1,5,10),
                        help='Recorrido máximo por ensayo SOLO en demo; mantiene 0.5°/s y 0.5°/s²')
    parser.add_argument('--duration',type=float,default=0,help=argparse.SUPPRESS)
    parser.add_argument('--log-dir',type=Path,default=PROJECT/'salidas/control_articular')
    args=parser.parse_args(argv)
    if args.recorrido_demo_deg is not None and args.modo!='demo':
        parser.error('--recorrido-demo-deg solo se admite en control_demo; no modifica la ficha física.')
    from irb120_control.rviz_control import model_joints
    model_joints()  # no se inicia si modelo/URDF discrepan
    config=None
    if args.modo=='robot':
        if not args.config:parser.error('Modo robot requiere --config con ficha revisada y GO de laboratorio.')
        try:
            policy,config=Policy.physical(args.config)
            network=config['network']
            for key in ('bind_ip','controller_ip'):ipaddress.IPv4Address(network[key])
            if network['controller_ip']=='127.0.0.1' or network['bind_ip']=='0.0.0.0':
                raise Rejected('Modo robot requiere IP de PC/interfaz concreta y controlador físico.')
            if not 1024<=int(network['port'])<=65535:raise Rejected('Declarar puerto EGM verificado.')
            timeout=float(network['comm_timeout_s'])
            if not .02<=timeout<=.2:raise Rejected('Declarar CommTimeout verificado entre 0.02 y 0.2 s para este ensayo.')
        except (Rejected,ValueError,TypeError,KeyError,OSError) as exc:
            parser.error(str(exc))
        if not args.habilitar_envio and not args.comprobar:
            parser.error('Agregar --habilitar-envio solo para el ensayo físico con GO. El arranque permanece desarmado.')
    else:
        policy=Policy.demo(step=args.recorrido_demo_deg or 1)
        if args.modo=='egm_lectura':
            if args.bind_ip is None or args.egm_port is None:parser.error('EGM lectura requiere --bind-ip y --egm-port verificados.')
            try:
                ipaddress.IPv4Address(args.bind_ip);ipaddress.IPv4Address(args.host)
                if args.bind_ip=='0.0.0.0' or not 1024<=args.egm_port<=65535:raise ValueError('Interfaz/puerto inválidos')
            except ValueError as exc:parser.error(str(exc))
    if args.comprobar:
        from irb120_control.protocolo import google
        print('Modelo/URDF y protocolo correctos. Protobuf:',google.protobuf.__version__)
        if config:print('Ficha válida; no se abrió ningún socket EGM.')
        return 0
    import rclpy
    from irb120_control.rviz_control import RvizControl
    lock=threading.RLock();engine=Supervisor(policy,can_send=args.modo in ('demo','robot'))
    runtime=None;sim=None;reader=None;reader_stop=threading.Event();children=[];node=None
    args.log_dir.mkdir(parents=True,exist_ok=True)
    instance_lock=(PROJECT/'salidas/control_articular/instancia.lock')
    instance_lock.parent.mkdir(parents=True,exist_ok=True)
    instance_file=instance_lock.open('a')
    try:fcntl.flock(instance_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        instance_file.close();parser.error('Ya hay una sesión de control abierta. Cerrar esa sesión antes de iniciar otra.')
    log_path=args.log_dir/('control_'+args.modo+'_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%fZ')+'.jsonl')
    password=getpass.getpass('Contraseña UAS (lectura para vista previa): ') if args.modo=='vista' else None
    rclpy.init(args=[])
    try:
        if args.modo!='vista':
            from irb120_control.protocolo import EGMTransport
            from irb120_control.runtime import Runtime
            if args.modo=='demo':
                from irb120_control.simulador import SimulatedController
                transport=EGMTransport('127.0.0.1',0,'127.0.0.1')
                sim=SimulatedController(transport.address);sim.start()
            elif args.modo=='egm_lectura':
                transport=EGMTransport(args.bind_ip,args.egm_port,args.host)
            else:
                transport=EGMTransport(network['bind_ip'],int(network['port']),network['controller_ip'])
            runtime=Runtime(engine,transport,lock,log_path);runtime.start()
        else:
            from irb120_conexion.nodos.lectura_articular.puente_rws import fetch_joints_deg,build_base_url
            import requests
            from requests.auth import HTTPDigestAuth
            base=build_base_url(args.host)
            def read_rws():
                with requests.Session() as session:
                    session.trust_env=False;session.auth=HTTPDigestAuth(args.user,password)
                    while not reader_stop.is_set():
                        try:
                            q=fetch_joints_deg(session,base,timeout=.8,ignore_joint_state=args.ignore_joint_state)
                            with lock:
                                if engine.q is None:
                                    engine.policy=Policy.demo(q,margin=0.);engine.policy.state_timeout=1.
                                engine.ingest(q,time.monotonic(),healthy=False)
                                engine.cycle(time.monotonic())
                        except Exception as exc:
                            with lock:engine.fault('Lectura RWS: '+str(exc))
                        reader_stop.wait(.2)
            reader=threading.Thread(target=read_rws,daemon=True);reader.start()
        node=RvizControl(engine,lock,runtime,args.modo)
        with tempfile.TemporaryDirectory(prefix='irb120_control_') as directory:
            folder=prepare_models(directory)
            for name in ('medido','objetivo'):
                command=['/opt/ros/jazzy/lib/robot_state_publisher/robot_state_publisher','--ros-args','--params-file',str(folder/(name+'.yaml')),
                    '-r',f'__node:=irb120_rsp_{name}','-r',f'joint_states:=/irb120/control/{name}/joint_states',
                    '-r',f'/robot_description:=/irb120/control/{name}/robot_description',
                    '-r','/tf:=/irb120/control/tf','-r','/tf_static:=/irb120/control/tf_static']
                children.append(subprocess.Popen(command))
            if not args.no_rviz:
                children.append(subprocess.Popen(['rviz2','-d',str(folder/'control.rviz'),'--ros-args',
                    '-r','/tf:=/irb120/control/tf','-r','/tf_static:=/irb120/control/tf_static']))
            print(f'\nMODO {args.modo.upper()} · control J1–J6 desde RViz · inicio DESARMADO\n'
                  'Elegir herramienta Interact → clic derecho sobre el aro → seleccionar eje.\n'
                  'Girar/ajustar = vista previa. ARMAR y EJECUTAR son órdenes separadas.\n'
                  f'Recorrido máximo por prueba: {policy.step:g}°; velocidad: {policy.speed:g}°/s; '
                  f'aceleración: {policy.acceleration:g}°/s².\n'
                  f'Registro: {log_path if runtime else "solo lectura/vista previa"}\n'
                  'Para otro eje: esperar MANTENIENDO → seleccionar/sincronizar → ARMAR → EJECUTAR.\n'
                  'DESARMAR cierra el envío al finalizar la sesión.\n',flush=True)
            started=time.monotonic()
            while rclpy.ok():
                rclpy.spin_once(node,timeout_sec=.02)
                if any(c.poll() is not None for c in children):break
                if args.duration and time.monotonic()-started>=args.duration:break
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):
        pass
    except (OSError,RuntimeError,ValueError) as exc:
        print('No se pudo iniciar control:',exc,flush=True);return 2
    finally:
        # Ignorar interrupciones repetidas únicamente durante el cierre normal.
        signal.signal(signal.SIGINT,signal.SIG_IGN);signal.signal(signal.SIGTERM,signal.SIG_IGN)
        if runtime:runtime.close()
        reader_stop.set()
        if reader:reader.join(timeout=1.5)
        if sim:sim.close()
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        if node:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        instance_file.close()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
