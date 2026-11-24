"""Grafo ROS 2 en vivo: nodos, tópicos y quién publica / escucha (sustituto de rqt_graph, que aquí no hay).

    ./brazo.sh nodos [--simulado] [--espera 4] [--png salidas/grafo_ros.png] [--todos]

Descubre el grafo durante unos segundos, imprime cada nodo con sus tópicos y, con --png, dibuja el grafo con
graphviz (`dot`). Por defecto oculta los tópicos internos de ROS (/rosout, /parameter_events, …)."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

INTERNOS = ('/rosout', '/parameter_events', '/robot_description')
SONDA = 'irb120_grafo_sonda'


def descubrir(espera):
    """{nodo: {'pub': [(tópico, tipo)], 'sub': [...]}} tras `espera` s de descubrimiento DDS."""
    import rclpy
    rclpy.init()
    nodo = rclpy.create_node(SONDA)
    try:
        time.sleep(espera)
        grafo = {}
        for nombre, ns in nodo.get_node_names_and_namespaces():
            if nombre == SONDA:
                continue
            completo = (ns.rstrip('/') + '/' + nombre) if ns not in ('', '/') else nombre
            pubs = nodo.get_publisher_names_and_types_by_node(nombre, ns)
            subs = nodo.get_subscriber_names_and_types_by_node(nombre, ns)
            grafo[completo] = {'pub': [(t, ','.join(ty)) for t, ty in pubs],
                               'sub': [(t, ','.join(ty)) for t, ty in subs]}
        return grafo
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


def filtrar(grafo, todos):
    if todos:
        return grafo
    interno = lambda t: t.startswith(INTERNOS) or t.endswith(('/robot_description', '/transition_event'))
    return {n: {k: [x for x in v if not interno(x[0])] for k, v in d.items()} for n, d in grafo.items()}


def texto(grafo):
    lineas = []
    for nodo in sorted(grafo):
        lineas.append(f'● {nodo}')
        for clave, flecha in (('pub', 'publica →'), ('sub', 'escucha ←')):
            for topico, tipo in sorted(grafo[nodo][clave]):
                lineas.append(f'    {flecha} {topico}  [{tipo.split("/")[-1]}]')
    return '\n'.join(lineas)


def dot(grafo):
    """Nodos = cajas, tópicos = elipses; arista nodo→tópico (publica) y tópico→nodo (escucha)."""
    def q(s):
        return '"' + s.replace('"', '\\"') + '"'
    # Identificadores sin ':' (graphviz lo lee como puerto y pierde aristas).
    ids_n = {n: f'N{i}' for i, n in enumerate(sorted(grafo))}
    topicos = sorted({t for d in grafo.values() for k in ('pub', 'sub') for t, _ in d[k]})
    ids_t = {t: f'T{i}' for i, t in enumerate(topicos)}
    out = ['digraph ros {', '  rankdir=LR; splines=curved; nodesep=0.35; ranksep=0.9; bgcolor="white"; fontname="DejaVu Sans";'  # 2.43 falla con splines por defecto,
           '  node [fontname="DejaVu Sans", fontsize=11]; edge [color="#5b6b7f"];']
    for nodo, d in grafo.items():
        etiqueta = 'rviz (escucha TF)' if nodo.startswith('transform_listener_impl') else nodo
        out.append(f'  {ids_n[nodo]} [label={q(etiqueta)}, shape=box, style="rounded,filled", '
                   'fillcolor="#dbeafe", color="#1d4ed8"];')
        for t, _ in d['pub']:
            out.append(f'  {ids_n[nodo]} -> {ids_t[t]};')
        for t, _ in d['sub']:
            out.append(f'  {ids_t[t]} -> {ids_n[nodo]};')
    for t in topicos:
        out.append(f'  {ids_t[t]} [label={q(t)}, shape=ellipse, style=filled, fillcolor="#f1f5f9", '
                   'color="#94a3b8", fontsize=10];')
    out.append('}')
    return '\n'.join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--espera', type=float, default=4., help='segundos de descubrimiento (por defecto 4)')
    p.add_argument('--png', type=Path, help='además, dibuja el grafo en este PNG (necesita graphviz)')
    p.add_argument('--todos', action='store_true', help='incluir tópicos internos de ROS')
    a = p.parse_args(argv)
    grafo = filtrar(descubrir(a.espera), a.todos)
    if not grafo:
        print('No se ve ningún nodo. ¿Está abierto el panel? (real: ROS_DOMAIN_ID=120, simulado: 121)')
        return 2
    print(texto(grafo))
    if a.png:
        if not shutil.which('dot'):
            print('No está graphviz (`dot`): no se dibuja el PNG.')
            return 1
        a.png.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['dot', '-Tpng', '-Gdpi=130', '-o', str(a.png)], input=dot(grafo), text=True, check=True)
        print(f'\nGrafo dibujado en {a.png}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
