"""Intercambio EGM en hilo separado de los callbacks ROS/RViz, con watchdog.

Python/Linux ordinario no garantiza tiempo real. Los atrasos abortan el envío;
el comportamiento físico sin paquetes debe estar verificado en el controlador.
"""
import json
import threading
import time
from datetime import datetime, timezone
import numpy as np
from irb120_control.supervisor import Policy


class Runtime:
    def __init__(self, engine, transport, lock, log_path):
        self.engine,self.transport,self.lock=engine,transport,lock
        self.closing=threading.Event()
        self.thread=threading.Thread(target=self.run,daemon=True)
        self.log=log_path.open('x',encoding='utf-8')
        self.sent=0;self.received=0;self.last_logged=0

    def record(self, kind, **fields):
        # Se llama bajo el mismo RLock que protege el supervisor.
        self.log.write(json.dumps({'time_utc':datetime.now(timezone.utc).isoformat(),'kind':kind,
                        'state':self.engine.state,**fields},ensure_ascii=False,allow_nan=False)+'\n')
        self.log.flush()

    def start(self):
        self.thread.start()

    def run(self):
        last_state=None;hold_since=None;closing_started=None
        try:
            while True:
                feedback=self.transport.receive(.01)
                with self.lock:
                    # Un callback ROS puede actualizar el heartbeat mientras esperamos
                    # el lock. Comparar con un instante anterior produce una falsa
                    # señal de reloj invertido/heartbeat ausente.
                    now=time.monotonic()
                    e=self.engine
                    if feedback is not None:
                        if not e.can_send and e.q is None:
                            e.policy=Policy.demo(feedback.q,margin=0.)
                        e.ingest(feedback.q,feedback.received_at,feedback.healthy,feedback.guidance)
                        self.received+=1
                    if self.closing.is_set():
                        e.heartbeat(now)  # cierre solicitado: permitir completar el frenado normal
                        if closing_started is None:
                            closing_started=now;e.cancel(now)
                        if e.state not in e.ACTIVE or now-closing_started>3:
                            break
                    ref=e.cycle(now)
                    if ref is not None and feedback is not None:
                        self.transport.send(ref);self.sent+=1
                    if e.state!=last_state:
                        self.record('state',reason=e.reason)
                        print(f'[CONTROL] {e.state}: {e.reason}',flush=True)
                        last_state=e.state
                    if feedback is not None and now-self.last_logged>=.1:
                        self.last_logged=now
                        self.record('sample',sequence=feedback.sequence,q_deg=feedback.q.tolist(),
                            target_deg=None if e.target is None else e.target.tolist(),
                            reference_deg=None if ref is None else ref.tolist(),
                            following_error_deg=None if ref is None else (ref-feedback.q).tolist(),sent_packets=self.sent)
                    if self.closing.is_set() and e.state=='MANTENIENDO':
                        if np.max(np.abs(e.q-e.reference))<=e.policy.start_drift:
                            if hold_since is None:hold_since=now
                            if now-hold_since>=.3:break
        except Exception as exc:
            with self.lock:
                self.engine.fault(f'Fallo del transporte: {type(exc).__name__}: {exc}')
                self.record('fault',reason=self.engine.reason)
            print(self.engine.reason,flush=True)
        finally:
            self.transport.close()

    def close(self):
        self.closing.set();self.thread.join(timeout=3.5)
        # Si el hilo de transporte quedó bloqueado, cerrar socket y documentar el fallo.
        if self.thread.is_alive():
            self.transport.close();self.thread.join(timeout=.5)
        self.log.close()
