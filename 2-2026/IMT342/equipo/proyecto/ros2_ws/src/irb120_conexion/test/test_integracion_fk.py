"""Procesos ROS reales + ABB simulado: acierto, error y movimiento detectables."""
import csv
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from irb120_conexion.rutas import PROJECT
sys.path.insert(0, str(PROJECT / "scripts/tests"))
sys.path.insert(0, str(PROJECT / "hito2"))
import test_rws_simulado_loopback as sim
from irb120.rosi_model import rosi_forward_kinematics
from irb120.transforms import matrix_to_quaternion
from irb120_conexion.arranque import comunicacion as launch


@unittest.skipUnless(os.environ.get("IRB120_RUN_ROS_TEST") == "1", "Ensayo opcional ROS/loopback")
class IntegratedFkTests(unittest.TestCase):
    def test_reports_independent_pose_error_and_never_accepts_motion(self):
        q = [30,-20,15,40,-35,60]
        T = rosi_forward_kinematics([v*3.141592653589793/180 for v in q])
        x,y,z,w = matrix_to_quaternion(T[:3,:3])
        pose = dict(zip(("x","y","z","q1","q2","q3","q4"), (T[:3,3]*1000).tolist()+[w,x,y,z]))
        class Controller(sim.FakeRws):
            def do_GET(self):
                self.server.log.append((self.command,self.path))
                if not self._digest_ok():
                    self.send_response(401)
                    self.send_header("WWW-Authenticate",f'Digest realm="{sim.REALM}", qop="auth", nonce="{sim.NONCE}"')
                    self.send_header("Content-Length","0");self.end_headers();return
                path=urlsplit(self.path).path
                if path.endswith("robtarget"):
                    self.server.pose_count+=1
                    self.server.after=True
                    v=dict(pose)
                    if 6 <= self.server.pose_count <= 10:v["x"]+=.02
                    return self._send(200,sim.json_body(sim.record("ms-robtargets","ROB_1",**v)),"application/json")
                if path.endswith("jointtarget"):
                    values=q[:]
                    if self.server.after and 11 <= self.server.pose_count <=15:values[0]+=.1
                    self.server.after=False
                    return self._send(200,sim.json_body(sim.record("ms-jointtarget","ROB_1",**{f"rax_{i+1}":v for i,v in enumerate(values)})),"application/json")
                self._send(404,"","text/plain")
        server=ThreadingHTTPServer(("127.0.0.1",0),Controller)
        server.log=[];server.pose_count=0;server.after=False
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        ports=[]
        sockets=[]
        for _ in range(2):
            s=socket.socket();s.bind(("127.0.0.1",0));sockets.append(s);ports.append(s.getsockname()[1])
        for s in sockets:s.close()
        with tempfile.TemporaryDirectory() as tmp,patch.object(launch.getpass,"getpass",return_value=sim.PASSWORD):
            result=launch.main(["--host","127.0.0.1","--port",str(server.server_address[1]),"--user",sim.USER,
                                "--validate-fk","--rate","5","--max-messages","25","--no-rviz","--no-browser",
                                "--http-port",str(ports[0]),"--fk-http-port",str(ports[1]),
                                "--log-dir",tmp,"--print-every","0"])
            self.assertEqual(result,0)
            files=list(Path(tmp).glob('*_fk.csv'));self.assertEqual(len(files),1)
            with files[0].open() as f:rows=list(csv.DictReader(f))
            states={row["status"] for row in rows}
            self.assertTrue({"DENTRO","FUERA","NO_EVALUABLE"} <= states,states)
            for row in rows:
                if row["status"]=="NO_EVALUABLE":self.assertEqual(row["accepted"],"")
                if row["status"]=="FUERA":self.assertAlmostEqual(float(row["position_error_mm"]),.02,places=8)
            details=list(Path(tmp).glob('*_fk.jsonl'))
            self.assertTrue(details)
            self.assertNotIn(sim.PASSWORD,details[0].read_text())
        self.assertTrue(all(method=="GET" for method,_ in server.log))
        poses=[parse_qs(urlsplit(path).query) for _,path in server.log if '/robtarget' in path]
        self.assertTrue(all(v=={"json":["1"],"tool":["tool0"],"wobj":["wobj0"],"coordinate":["Base"]} for v in poses))
        print('Ensayo FK integrado:',len(rows),'muestras;',sorted(states),flush=True)


if __name__=="__main__":unittest.main()
