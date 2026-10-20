import sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3] / 'hito2'))
from irb120.dh import forward_kinematics_tcp,HOME_Q
from irb120.pieper import analyze_pose,select_solution
from irb120.jacobian import geometric_jacobian
from irb120.lspb import default_limits,plan_lspb
from irb120.dynamics_1r import shoulder_model
out={}
T=forward_kinematics_tcp(HOME_Q)
for name in ['rotacion_escalada','ultima_fila_invalida']:
 bad=T.copy()
 if name=='rotacion_escalada': bad[:3,:2]*=2
 else: bad[3,3]=2
 try:
  r=analyze_pose(bad,HOME_Q)
  out[name]={'alcanzable':r.reachable,'det_R':float(np.linalg.det(bad[:3,:3])),'errores':[{'ep':c.position_error_m,'eR':c.rotation_error_rad,'eF':c.frobenius_error} for c in r.checks if c is not None and c.accepted]}
 except Exception as e:out[name]={'rechazo':str(e)}
q=np.deg2rad([30,-20,15,40,30,60]); J=geometric_jacobian(q); sv=np.linalg.svd(J,compute_uv=False)
out['determinante']={'detJ':float(np.linalg.det(J)),'producto_sigma':float(sv.prod())}
from irb120.transforms import pose_from_xyz_rpy_deg
r=analyze_pose(pose_from_xyz_rpy_deg(.4,.1,.35,0,180,0)); c=select_solution(r,HOME_Q)
qf=np.array(c.q); v,a=default_limits(); tr=plan_lspb(HOME_Q,qf,v,a); model=shoulder_model((HOME_Q+qf)/2)
q,qd,qdd=tr.sample(tr.tf)
out['frontera_final']={'tf':tr.tf,'qdd_tf':qdd.tolist(),'tau_en_tf':float(model.torque(q[1],qdd[1])),'tau_en_reposo_sostenido':float(model.torque(q[1],0)),'qdd_despues_tf':tr.sample(tr.tf+1)[2].tolist()}
out['rama_ejemplo']={'etiqueta':c.wrist,'q5_grados':float(np.rad2deg(c.q[4]))}
print(json.dumps(out,indent=2))
