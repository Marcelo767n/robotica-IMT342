"""El reloj del ciclo debe leerse después de adquirir el estado compartido."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class RuntimeTests(unittest.TestCase):
    def test_heartbeat_updated_while_waiting_for_lock_does_not_fault(self):
        from irb120_control.runtime import Runtime
        from irb120_control.supervisor import Policy, Supervisor
        q = [0., -20., 20., 0., 30., 0.]
        engine = Supervisor(Policy.demo())
        for stamp in (99.4, 99.7, 100.):
            engine.ingest(q, stamp)
        engine.heartbeat(100.)
        engine.arm(100.)
        clock = [100.]

        class CallbackLock:
            def __enter__(self):
                # Reproduce un callback ROS que terminó mientras el hilo EGM
                # esperaba el lock. El heartbeat es posterior al receive.
                clock[0] += .001
                engine.heartbeat(clock[0])

            def __exit__(self, *args):
                pass

        class Transport:
            commands = []
            first = True

            def receive(self, timeout):
                if self.first:
                    self.first = False
                else:
                    runtime.closing.set()
                    clock[0] += .01
                return SimpleNamespace(q=np.array(q), received_at=clock[0], healthy=True, guidance=True, sequence=0)

            def send(self, command):
                self.commands.append(command.copy())

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            transport = Transport()
            runtime = Runtime(engine, transport, CallbackLock(), Path(directory) / 'runtime.jsonl')
            try:
                with patch('irb120_control.runtime.time.monotonic', side_effect=lambda: clock[0]):
                    runtime.run()
                self.assertGreaterEqual(len(transport.commands), 1)
                self.assertEqual(engine.state, 'MANTENIENDO', engine.reason)
                for command in transport.commands:
                    self.assertEqual(command.tolist(), q)
            finally:
                runtime.log.close()


if __name__ == '__main__':
    unittest.main()
