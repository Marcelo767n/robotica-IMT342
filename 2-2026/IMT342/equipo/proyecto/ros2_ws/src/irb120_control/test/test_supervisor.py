import copy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import yaml
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[3]/'src/irb120_conexion')]
from irb120_control.supervisor import Policy,Supervisor,Rejected,JOINT_LIMITS_DEG,vector


def ready(policy=None):
    e=Supervisor(policy or Policy.demo())
    for now in np.arange(0,.641,.008):
        e.heartbeat(float(now));e.ingest([0,-20,20,0,30,0],float(now))
    return e,.64


class SupervisorTests(unittest.TestCase):
    def test_rejects_nonfinite_incomplete_and_invalid_bounds(self):
        for bad in ([0]*5,[0]*7,[0,0,0,0,0,float('nan')],[0,0,0,0,0,float('inf')]):
            with self.assertRaises(Rejected):vector(bad)
        with self.assertRaises(Rejected):Policy(JOINT_LIMITS_DEG,[[0,0]]*6)

    def test_no_reference_on_start_or_preview_and_no_automatic_resume(self):
        e,t=ready();e.preview(.5)
        self.assertIsNone(e.cycle(t));self.assertIsNone(e.reference)
        e.arm(t);e.cycle(t)
        e.cycle(t+.3)
        self.assertEqual(e.state,'FALLO');self.assertIsNone(e.reference)
        e.heartbeat(t+.31);e.ingest([0,-20,20,0,30,0],t+.31)
        self.assertIsNone(e.cycle(t+.31));self.assertEqual(e.state,'FALLO')

    def test_hard_limits_j3_j6_and_single_step(self):
        e,t=ready()
        for axis,angle in [(0,166),(1,-111),(2,71),(3,161),(4,121),(5,401)]:
            e.select(axis)
            with self.assertRaises(Rejected):e.preview(angle)
        e.select(0)
        with self.assertRaises(Rejected):e.preview(1.01)
        e.preview(1.)
        np.testing.assert_equal(e.target[1:],e.anchor[1:])

    def test_five_and_ten_degree_demo_profiles_keep_speed_and_acceleration(self):
        from irb120.lspb import check_trajectory
        for distance in (5.,10.):
            for axis in range(6):
                for sign in (-1,1):
                    with self.subTest(distance=distance,axis=axis,sign=sign):
                        e,t=ready(Policy.demo(step=distance))
                        e.select(axis);e.preview(float(e.target[axis]+sign*distance))
                        e.arm(t);np.testing.assert_array_equal(e.cycle(t),e.q);e.execute(t)
                        self.assertEqual(e.policy.speed,.5)
                        self.assertEqual(e.policy.acceleration,.5)
                        self.assertAlmostEqual(e.trajectory.tf,distance/.5+1,places=6)
                        self.assertTrue(check_trajectory(e.trajectory,np.full(6,.5),np.full(6,.5)).passed)
                        positions,velocities,accelerations=e.trajectory.sample_many(np.linspace(0,e.trajectory.tf,1001))
                        self.assertLessEqual(float(np.abs(velocities).max()),.5+1e-9)
                        self.assertLessEqual(float(np.abs(accelerations).max()),.5+1e-9)
                        for other in set(range(6))-{axis}:
                            np.testing.assert_allclose(positions[:,other],e.start[other],atol=1e-10)
                        endpoint=e.trajectory.qf.copy()
                        for now in np.arange(t+.008,t+e.trajectory.tf+.1,.008):
                            e.heartbeat(float(now));e.ingest(e.reference,float(now));e.cycle(float(now))
                            self.assertNotEqual(e.state,'FALLO',e.reason)
                        self.assertEqual(e.state,'MANTENIENDO',e.reason)
                        np.testing.assert_allclose(e.q,endpoint,atol=1e-9)

    def test_extended_demo_does_not_expand_robot_limits_or_physical_policy(self):
        p=Policy.demo(step=10)
        with self.assertRaises(Rejected):Policy(p.limits,p.window,step=10)
        with self.assertRaises(Rejected):Policy.demo(step=11)
        q=[162,-20,20,0,30,0]
        e=Supervisor(Policy.demo(q,step=10));e.ingest(q,0)
        with self.assertRaises(Rejected):e.preview(172)
        with self.assertRaises(Rejected):e.preview(151)  # más de 10° desde la postura medida
        e.preview(152);self.assertEqual(e.target[0],152)

    def test_demo_range_argument_is_rejected_for_robot_and_read_only_modes(self):
        from irb120_control.arranque import main
        import contextlib
        import io
        for mode in ('robot','vista','egm_lectura'):
            output=io.StringIO()
            with contextlib.redirect_stderr(output),self.assertRaises(SystemExit) as raised:
                main(['--modo',mode,'--recorrido-demo-deg','10','--comprobar'])
            self.assertEqual(raised.exception.code,2)
            self.assertIn('solo se admite en control_demo',output.getvalue())

    def test_j6_is_not_wrapped_modulo_360(self):
        q=[0,-20,20,0,30,370]
        e=Supervisor(Policy.demo(q));e.ingest(q,0);e.preview(370.5) if e.axis==5 else None
        e.select(5);e.preview(370.5)
        self.assertEqual(e.target[5],370.5)
        with self.assertRaises(Rejected):e.preview(10.5)

    def test_stale_moving_unhealthy_and_preview_only_cannot_arm(self):
        e,t=ready();e.can_send=False
        with self.assertRaises(Rejected):e.arm(t)
        e.can_send=True
        with self.assertRaises(Rejected):e.arm(t+.3)
        e,t=ready();e.healthy=False
        with self.assertRaises(Rejected):e.arm(t)
        e,t=ready();e.ingest([.1,-20,20,0,30,0],t)
        with self.assertRaises(Rejected):e.arm(t)

    def test_initial_reference_and_all_six_individual_profiles(self):
        for axis in range(6):
            e,t=ready();e.select(axis);e.preview(float(e.target[axis]+.4));e.arm(t)
            np.testing.assert_array_equal(e.cycle(t),e.q)
            e.execute(t)
            with self.assertRaises(Rejected):e.execute(t)
            references=[];velocities=[]
            for now in np.arange(t+.008,t+3,.008):
                e.heartbeat(float(now));e.ingest(e.reference,float(now))
                q=e.cycle(float(now));self.assertIsNotNone(q,e.reason)
                references.append(q);velocities.append(e.velocity.copy())
                self.assertLessEqual(float(np.max(np.abs(e.velocity))),e.policy.speed+1e-9)
            self.assertEqual(e.state,'MANTENIENDO',e.reason)
            refs=np.array(references)
            for other in set(range(6))-{axis}:np.testing.assert_array_equal(refs[:,other],np.full(len(refs),e.start[other]))
            self.assertLessEqual(float(np.max(np.abs(np.diff(velocities,axis=0)/.008))),e.policy.acceleration+1e-7)
            self.assertAlmostEqual(e.q[axis],e.target[axis],places=9)

    def test_cancel_brakes_instead_of_jumping(self):
        e,t=ready();e.preview(.8);e.arm(t);e.execute(t)
        for now in np.arange(t+.008,t+.6,.008):
            e.heartbeat(float(now));e.ingest(e.reference,float(now));e.cycle(float(now))
        t=float(now);q=e.reference.copy();v=e.velocity.copy();e.cancel(t)
        first=e.cycle(t);np.testing.assert_allclose(first,q)
        self.assertEqual(e.state,'FRENANDO')
        with self.assertRaises(Rejected):e.disarm()
        for now in np.arange(t+.008,t+1.2,.008):
            e.heartbeat(float(now));e.ingest(e.reference,float(now));e.cycle(float(now))
        self.assertEqual(e.state,'MANTENIENDO');self.assertGreater(e.reference[0],q[0])
        self.assertLess(e.reference[0],.8);self.assertEqual(e.velocity[0],0)
        e.disarm();self.assertIsNone(e.cycle(float(now)))

    def test_following_other_joint_and_motor_faults(self):
        for q,healthy in [([.4,-20,20,0,30,0],True),([0,-19.95,20,0,30,0],True),([0,-20,20,0,30,0],False)]:
            e,t=ready();e.preview(.5);e.arm(t)
            e.heartbeat(t+.008);e.ingest(q,t+.008,healthy)
            self.assertIsNone(e.cycle(t+.008));self.assertEqual(e.state,'FALLO')

    def test_stream_can_arm_hold_but_execution_waits_for_guidance(self):
        e,t=ready();e.guidance=False;e.arm(t)
        np.testing.assert_array_equal(e.cycle(t),e.q)
        with self.assertRaises(Rejected):e.execute(t)
        self.assertEqual(e.state,'ARMADO')

    def test_go_and_session_expire(self):
        e,t=ready();e.policy.expires=1
        with self.assertRaises(Rejected):e.arm(t,wall=2)
        e.policy.expires=10;e.arm(t,wall=0)
        self.assertIsNone(e.cycle(t,wall=11));self.assertEqual(e.state,'FALLO')

    def test_singular_home_is_not_an_implicit_start(self):
        q=[0,-20,20,0,0,0];e=Supervisor(Policy.demo(q))
        for t in np.arange(0,.641,.008):e.heartbeat(float(t));e.ingest(q,float(t))
        e.preview(.1)
        with self.assertRaisesRegex(Rejected,'singularidad'):e.arm(.64)
        self.assertIsNone(e.reference)

    def test_measured_overshoot_of_reviewed_window_stops_even_below_following_limit(self):
        e,t=ready();e.policy.window[0]=[-.1,.1];e.preview(.1);e.arm(t);e.execute(t)
        for now in np.arange(t+.008,t+1.5,.008):
            e.heartbeat(float(now));e.ingest(e.reference,float(now));e.cycle(float(now))
        self.assertEqual(e.state,'MANTENIENDO')
        measured=e.q.copy();measured[0]=.11
        self.assertLess(abs(measured[0]-e.reference[0]),e.policy.following)
        e.ingest(measured,float(now)+.008)
        self.assertEqual(e.state,'FALLO');self.assertIsNone(e.reference)

    def test_physical_template_blocks_and_requires_explicit_limits(self):
        template=Path(__file__).resolve().parents[1]/'config/sesion_robot.ejemplo.yaml'
        with self.assertRaises(Rejected):Policy.physical(template)
        data=yaml.safe_load(template.read_text());p=Policy.demo();now=datetime.now(timezone.utc)
        data['verified']={k:True for k in data['verified']}
        data['go']={'decision':'GO','operator':'operador de prueba simulada','laboratory_responsible':'supervisor simulado',
                    'approved_at':(now-timedelta(minutes=1)).isoformat(),'valid_until':(now+timedelta(minutes=10)).isoformat()}
        data['controller_limits_deg']=JOINT_LIMITS_DEG.tolist();data['initial_joints_deg']=[0,-20,20,0,30,0]
        data['approved_joint_window_deg']=p.window.tolist()
        data['test']={k:getattr(p,k) for k in data['test']}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'session.yaml';path.write_text(yaml.safe_dump(data))
            policy,_=Policy.physical(path);self.assertEqual(policy.step,1)
            e=Supervisor(policy);e.ingest([.2,-20,20,0,30,0],0)
            self.assertEqual(e.state,'FALLO');self.assertIsNone(e.reference)
            data['controller_limits_deg']=None;path.write_text(yaml.safe_dump(data))
            with self.assertRaises((Rejected,ValueError,TypeError)):Policy.physical(path)


if __name__=='__main__':unittest.main()
