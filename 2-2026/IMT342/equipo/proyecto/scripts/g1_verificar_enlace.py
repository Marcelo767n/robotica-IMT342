#!/usr/bin/env python3
"""G1-A: comprueba el enlace Ethernet directo PC <-> controlador ABB.

Sin --ping solo LEE el estado local de la PC (no envia ningun paquete). Con --ping envia
3 paquetes ICMP al host indicado. No usa RWS, no inicia RAPID, motores ni EGM.
Resultado: una lista de comprobaciones PASS / FAIL / AVISO, cada una con la accion a tomar.
Codigo de salida: 0 si todo pasa, 2 si algo falla.
"""

import argparse
import ipaddress
import json
from pathlib import Path
import subprocess
import sys

ABB_SERVICE_NETWORK = ipaddress.ip_network("192.168.125.0/24")
DEFAULT_HOST = "192.168.125.1"


def find_ethernet_interfaces(base=Path("/sys/class/net")):
    """Interfaces fisicas cableadas: tienen dispositivo, no son inalambricas ni loopback."""
    names = []
    if base.exists():
        for item in sorted(base.iterdir()):
            if item.name == "lo" or (item / "wireless").exists() or not (item / "device").exists():
                continue
            names.append(item.name)
    return names


def read_link(name, base=Path("/sys/class/net")):
    """operstate y carrier de la interfaz; None si el sistema no los puede leer."""
    out = {}
    for field in ("operstate", "carrier"):
        try:
            out[field] = (base / name / field).read_text().strip()
        except OSError:
            out[field] = None
    return out


def run_ip(*args):
    try:
        proc = subprocess.run(["ip", "-j", *args], capture_output=True, text=True, timeout=5)
        return json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def ipv4_addresses(addr_json):
    """Direcciones IPv4 (como interface) de la salida de `ip -j addr show dev X`."""
    found = []
    for entry in addr_json or []:
        for info in entry.get("addr_info", []):
            if info.get("family") == "inet":
                found.append(ipaddress.ip_interface(f"{info['local']}/{info['prefixlen']}"))
    return found


def evaluate(iface, link, addresses, route, default_routes, host=DEFAULT_HOST):
    """Pura y sin E/S. Devuelve [(id, estado, mensaje, accion)] con estado PASS/FAIL/AVISO.

    route: dict de `ip -j route get HOST` (o None si no hay ruta); default_routes: lista de dicts.
    """
    results = []
    if iface is None:
        results.append(("adaptador", "FAIL", "No hay interfaz Ethernet fisica.",
                        "Conecta el adaptador USB-Ethernet y revisa con: lsusb ; ip -br link"))
        return results
    results.append(("adaptador", "PASS", f"Interfaz Ethernet: {iface}.", ""))

    if link.get("carrier") != "1":
        results.append(("cable", "FAIL", f"{iface} sin enlace fisico (carrier={link.get('carrier')}, "
                        f"operstate={link.get('operstate')}).",
                        "Revisa que el cable este en el puerto indicado por el operador (X2 Service), "
                        "que el otro extremo este firme en el adaptador y que el controlador este encendido."))
        return results
    results.append(("cable", "PASS", f"Enlace fisico activo en {iface}.", ""))

    in_net = [a for a in addresses if a.ip in ABB_SERVICE_NETWORK]
    if any(str(a.ip) == host for a in addresses):
        results.append(("ip", "FAIL", f"La PC tiene la misma IP que el controlador ({host}).",
                        "Cambia la IP de la PC a 192.168.125.2/24 para evitar un conflicto."))
        return results
    if not in_net:
        got = ", ".join(str(a) for a in addresses) or "ninguna"
        results.append(("ip", "FAIL", f"{iface} no tiene IP en 192.168.125.0/24 (tiene: {got}).",
                        "Espera 15 s al DHCP; si no llega, activa el perfil estatico 192.168.125.2/24 "
                        "(sin gateway) de la guia."))
        return results
    results.append(("ip", "PASS", f"IP de la PC en la red de servicio: {in_net[0]}.", ""))

    if route is None:
        results.append(("ruta", "FAIL", f"No hay ruta hacia {host}.",
                        "Comprueba la IP y la mascara de la interfaz."))
    elif route.get("dev") != iface:
        results.append(("ruta", "FAIL", f"La ruta hacia {host} sale por {route.get('dev')}, no por {iface}.",
                        "DETENTE: no consultes RWS por otra interfaz. Revisa perfiles de red y rutas."))
    else:
        results.append(("ruta", "PASS", f"La ruta hacia {host} sale por {iface}.", ""))

    hijacked = [r for r in default_routes if r.get("dev") == iface]
    if hijacked:
        results.append(("internet", "AVISO", f"{iface} es la ruta predeterminada: el trafico de internet "
                        "saldria por el robot.", "Usa el perfil con never-default de la guia."))
    return results


def ping(host, iface):
    proc = subprocess.run(["ping", "-c", "3", "-W", "1", "-I", iface, host],
                          capture_output=True, text=True, timeout=15)
    return proc.returncode == 0, proc.stdout.strip().splitlines()[-2:]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iface", help="Interfaz Ethernet; por defecto la unica fisica detectada")
    parser.add_argument("--host", default=DEFAULT_HOST, help="IPv4 del controlador (defecto 192.168.125.1)")
    parser.add_argument("--ping", action="store_true", help="Enviar 3 ICMP al controlador (requiere enlace e IP)")
    args = parser.parse_args(argv)
    try:
        host = ipaddress.IPv4Address(args.host)
    except ipaddress.AddressValueError:
        parser.error("--host debe ser una IPv4 concreta.")
    if host.is_multicast or host.is_unspecified or str(host) == "255.255.255.255":
        parser.error("No se permiten direcciones multicast, broadcast ni inespecificas.")

    candidates = find_ethernet_interfaces()
    iface = args.iface or (candidates[0] if len(candidates) == 1 else None)
    if args.iface is None and len(candidates) > 1:
        print(f"Hay varias interfaces Ethernet ({', '.join(candidates)}); indica una con --iface.")
        return 2
    link = read_link(iface) if iface else {}
    addresses = ipv4_addresses(run_ip("addr", "show", "dev", iface)) if iface else []
    route_json = run_ip("route", "get", str(host)) if iface else None
    route = route_json[0] if route_json else None
    defaults = run_ip("route", "show", "default") or []
    results = evaluate(iface, link, addresses, route, defaults, str(host))

    if args.ping and all(state != "FAIL" for _, state, _, _ in results):
        ok, tail = ping(str(host), iface)
        results.append(("ping", "PASS" if ok else "FAIL", " | ".join(tail) or "sin respuesta",
                        "" if ok else "El enlace existe pero el controlador no responde a ICMP; "
                        "ICMP puede estar filtrado. Continua con la lectura RWS solo si la IP es la confirmada."))
    for check, state, message, action in results:
        print(f"[{state:5}] {check:9} {message}")
        if action:
            print(f"        -> {action}")
    return 0 if all(state != "FAIL" for _, state, _, _ in results) else 2


if __name__ == "__main__":
    sys.exit(main())
