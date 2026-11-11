import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import io
import unittest
from unittest.mock import patch

sys.path[:0]=[str(Path(__file__).resolve().parents[1]),
               str(Path(__file__).resolve().parents[3]/'src/irb120_conexion')]
from irb120_control.rws_j6 import (Client, Refused, EMPTY, SYMBOL, MODULE_PATH,
    MAIN_MODULE_PATH, MASTERSHIP, ORIGINAL_MODULE_SHA256, J6_MODULE_SHA256,
    make_j6_target, parse_target, literal, source_fingerprint, diagnose_inspection, main)

SOURCE=(Path(__file__).resolve().parents[4]/'docs/conexion_abb/evidencias/LabJointRws_original_2026-11-10.mod').read_bytes().decode()
J6_SOURCE=(Path(__file__).resolve().parents[1]/'rapid/rws_j6/LabJointRws.mod').read_bytes().decode()


class Response:
    def __init__(self, rows=None, status=200, content=None):
        self.status_code=status
        self.text=json.dumps({'_embedded':{'_state':rows or []}})
        self.content=self.text.encode() if content is None else content


class Session:
    def __init__(self):
        self.ctrl='motoroff';self.mode='AUTO';self.execution='stopped'
        self.robot='120-101516';self.source=SOURCE
        self.current=[[-4.28397,-12.4929,.697668,-.640559,3.30636,1.73935],[9e9]*6]
        self.target=copy.deepcopy(EMPTY);self.calls=[];self.post_status=204
        self.readback_error=0.;self.drift=0.;self.joint_reads=0
        self.joint_sequence=[]
        self.main_source='MODULE Module1\nPROC main()\nENDPROC\nENDMODULE\n'
        self.edit_status=200;self.mastership_status=204;self.ignore_edit=False

    def __enter__(self):return self

    def __exit__(self,*args):return False

    def get(self,url,**kw):
        self.calls.append(('GET',url,kw))
        assert kw['allow_redirects'] is False
        path=url.replace('http://127.0.0.1','')
        if path=='/rw/system':return Response([{'_type':'sys-system-li','name':self.robot,'rwversionname':'6.12.01.00'}])
        if path=='/rw/panel/ctrlstate':return Response([{'_type':'pnl-ctrlstate','ctrlstate':self.ctrl}])
        if path=='/rw/panel/opmode':return Response([{'_type':'pnl-opmode','opmode':self.mode}])
        if path=='/rw/rapid/execution':return Response([{'_type':'rap-execution','ctrlexecstate':self.execution}])
        if path==MODULE_PATH:return Response([{'_type':'rap-module-text','module-text':self.source}])
        if path==MAIN_MODULE_PATH:return Response([{'_type':'rap-module-text','module-text':self.main_source}])
        if path==SYMBOL:
            target=copy.deepcopy(self.target)
            if target!=EMPTY:target[0][0]+=self.readback_error
            return Response([{'_type':'rap-data','value':literal(target)}])
        if path=='/rw/rapid/tasks/T_ROB1/motion':
            self.joint_reads+=1
            values=copy.deepcopy(self.current)
            if self.joint_sequence:values[0]=self.joint_sequence.pop(0)
            if self.joint_reads==2:values[0][5]+=self.drift
            row={'_type':'rapid-jointtarget'}
            row.update({f'j{i+1}':str(v) for i,v in enumerate(values[0])})
            row.update({f'ej{i+1}':str(v) for i,v in enumerate(values[1])})
            return Response([row])
        if path=='/rw/rapid/modules':return Response([{'_type':'rap-module-info-li','name':name} for name in ('LabJointRws','Module1')])
        raise AssertionError('GET inesperado: '+path)

    def post(self,url,**kw):
        self.calls.append(('POST',url,kw))
        if url=='http://127.0.0.1'+MASTERSHIP:
            assert kw['params']['action'] in ('request','release') and kw['data']=={}
            assert kw['headers']['Content-Type']=='application/x-www-form-urlencoded'
            return Response(status=self.mastership_status)
        if url=='http://127.0.0.1'+MODULE_PATH:
            assert kw['params']=={'task':'T_ROB1','action':'set-module-text'}
            assert set(kw['data'])=={'text'}
            if self.edit_status==200 and not self.ignore_edit:self.source=kw['data']['text']
            return Response(status=self.edit_status)
        assert url=='http://127.0.0.1'+SYMBOL
        assert kw['params']=={'action':'set'} and kw['allow_redirects'] is False
        assert set(kw['data'])=={'value'}
        if self.post_status==204:self.target=parse_target(kw['data']['value'],allow_empty=True)
        return Response(status=self.post_status)


class RwsJ6Tests(unittest.TestCase):
    def client(self):
        self.session=Session()
        return Client(self.session,'http://127.0.0.1')

    def test_inspection_only_get_and_actual_module_hash(self):
        client=self.client();report=client.inspect()
        self.assertEqual(hashlib.sha256(SOURCE.encode()).hexdigest(),ORIGINAL_MODULE_SHA256)
        self.assertTrue(all(r['ok'] for r in report['resources'].values()))
        self.assertTrue(all(call[0]=='GET' for call in self.session.calls))
        self.assertEqual(report['resources']['module']['records'][0]['module-text'],SOURCE)

    def test_quoted_temporary_file_read_and_untrusted_paths_refused(self):
        client=self.client()
        rows=[{'file-path':'%22/hd0a/TEMPpusres.123%22'}]
        with patch.object(self.session,'get',return_value=Response(content=SOURCE.encode())) as get:
            client.resolve_module_text(rows)
            self.assertEqual(rows[0]['module-text'],SOURCE)
            self.assertEqual(get.call_args.args[0],'http://127.0.0.1/fileservice/hd0a/TEMPpusres.123')
        for path in ('https://example.com/file','/hd0a/TEMP/../../other','/hd0a/other.mod'):
            with self.subTest(path=path),self.assertRaises(Refused):
                client.resolve_module_text([{'file-path':path}])

    def test_reception_same_angles_readback_and_clear(self):
        client=self.client()
        with patch('irb120_control.rws_j6.time.sleep'):
            report=client.reception_test()
        self.assertTrue(report['passed']);self.assertFalse(report['motion_command_sent'])
        self.assertEqual(report['initial_joints_deg'],report['target_joints_deg'])
        self.assertEqual(self.session.target,EMPTY)
        posts=[c for c in self.session.calls if c[0]=='POST']
        self.assertEqual(len(posts),2)
        self.assertEqual(parse_target(posts[0][2]['data']['value']),self.session.current)

    def test_wrong_readback_is_failure_but_target_is_cleared(self):
        client=self.client();self.session.readback_error=.02
        with patch('irb120_control.rws_j6.time.sleep'):
            report=client.reception_test()
        self.assertFalse(report['passed']);self.assertTrue(report['cleared'])
        self.assertFalse(report['readback_verified'])

    def test_running_motors_guardstop_bad_mode_pending_and_changed_module_block_writes(self):
        cases=(('ctrl','motoron'),('ctrl','guardstop'),('execution','running'),('mode','MANF'),
               ('mode','UNDEF'),('robot','other'),('source',SOURCE+'\n! edit'),('target',[[0.]*6,[9e9]*6]))
        for field,value in cases:
            with self.subTest(field=field,value=str(value)[:20]):
                client=self.client();setattr(self.session,field,value)
                with self.assertRaises(Refused),patch('irb120_control.rws_j6.time.sleep'):
                    client.reception_test()
                self.assertFalse(any(c[0]=='POST' for c in self.session.calls))

    def test_motion_during_read_and_permission_refusal_not_retried(self):
        client=self.client();self.session.drift=.01
        with self.assertRaises(Refused),patch('irb120_control.rws_j6.time.sleep'):
            client.reception_test()
        self.assertFalse(any(c[0]=='POST' for c in self.session.calls))
        for code in (302,400,403,500):
            client=self.client();self.session.post_status=code
            with self.assertRaises(Refused),patch('irb120_control.rws_j6.time.sleep'):
                client.reception_test()
            self.assertEqual(len([c for c in self.session.calls if c[0]=='POST']),1)

    def test_j6_plan_keeps_other_five_axes_and_multiturn(self):
        client=self.client();current=self.session.current
        for delta in (-.1,.1,0.):
            result=make_j6_target(current,delta)
            self.assertEqual(result[0][:5],current[0][:5])
            self.assertAlmostEqual(result[0][5],current[0][5]+delta)
            self.assertEqual(result[1],current[1])
        current[0][5]=370.
        self.assertAlmostEqual(make_j6_target(current,.1)[0][5],370.1)
        self.assertEqual(current[0][5],370.)
        for delta in (1.,5.,10.,float('nan'),float('inf')):
            with self.assertRaises(Refused):make_j6_target(current,delta)
        current[0][5]=398.
        with self.assertRaises(Refused):make_j6_target(current,.1)

    def test_missing_nonfinite_sentinel_robot_axes_or_external_axes_are_refused(self):
        for text in ('[]','[[1,2],[9E9]]','[[true,0,0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]]',
                     '[[NaN,0,0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]]',literal(EMPTY)):
            with self.assertRaises(Refused):parse_target(text)
        self.assertEqual(parse_target(literal(EMPTY),allow_empty=True),EMPTY)
        client=self.client();self.session.current[1][0]=0.
        with self.assertRaises(Refused):make_j6_target(self.session.current,.1)

    def test_original_v5_module_blocks_every_nonzero_preparation(self):
        client=self.client()
        with self.assertRaisesRegex(Refused,'v5'):client.prepare_j6(.1)
        self.assertFalse(any(c[0]=='POST' for c in self.session.calls))

    def test_candidate_exact_hash_and_prepare_only_joint_six(self):
        self.assertEqual(source_fingerprint(J6_SOURCE),J6_MODULE_SHA256)
        self.assertEqual(source_fingerprint(J6_SOURCE.replace('\n','\r\n')),J6_MODULE_SHA256)
        for delta in (-.1,.1):
            client=self.client();self.session.source=J6_SOURCE
            with patch('irb120_control.rws_j6.time.sleep'):report=client.prepare_j6(delta)
            self.assertTrue(report['passed']);self.assertTrue(report['target_pending'])
            self.assertFalse(report['motion_command_sent'])
            self.assertEqual(report['target_joints_deg'][:5],self.session.current[0][:5])
            self.assertAlmostEqual(report['target_joints_deg'][5],self.session.current[0][5]+delta)
            self.assertEqual(len([c for c in self.session.calls if c[0]=='POST']),1)
            with self.assertRaises(Refused):client.prepare_j6(delta)

    def test_post_timeout_records_unknown_and_never_retries(self):
        import requests
        client=self.client()
        with patch.object(self.session,'post',side_effect=requests.Timeout('simulado')) as post:
            with self.assertRaises(requests.Timeout),patch('irb120_control.rws_j6.time.sleep'):
                client.reception_test()
            self.assertEqual(post.call_count,1)
        self.assertEqual(client.write_events[-1]['result'],'pending_or_unknown')

    def test_observation_detects_arrival_and_unselected_joint_movement(self):
        for drift in (0.,.1):
            client=self.client();self.session.source=J6_SOURCE
            with patch('irb120_control.rws_j6.time.sleep'):plan=client.prepare_j6(.1)
            destination=copy.deepcopy(plan['target_joints_deg']);destination[0]+=drift
            self.session.joint_sequence=[destination]*4
            import tempfile
            with tempfile.TemporaryDirectory() as tmp,patch('irb120_control.rws_j6.time.sleep'):
                report=client.observe(plan,5,Path(tmp)/'samples.jsonl')
            self.assertEqual(report['passed'],drift==0.)
            self.assertFalse(report['motion_command_sent'])
            self.assertEqual(len([c for c in self.session.calls if c[0]=='POST']),1)
            if drift:self.assertIn('ALERTA',report['reason'])

    def test_transfer_backs_up_then_edits_only_reviewed_module_and_is_idempotent(self):
        client=self.client();original_main=self.session.main_source
        original_post=self.session.post
        with tempfile.TemporaryDirectory() as tmp,patch('irb120_control.rws_j6.time.sleep'):
            def checked_post(url,**kw):
                backups=list(Path(tmp).glob('respaldo_modulo_*'))
                self.assertEqual(len(backups),1)
                self.assertEqual((backups[0]/'LabJointRws.mod').read_text(),SOURCE)
                self.assertEqual((backups[0]/'Module1.mod').read_text(),original_main)
                journal=json.loads((backups[0]/'transferencia.json').read_text())
                self.assertEqual(journal['write_events'][-1]['result'],'pending_or_unknown')
                return original_post(url,**kw)
            with patch.object(self.session,'post',side_effect=checked_post):
                report=client.update_module(Path(tmp))
            self.assertTrue(report['passed']);self.assertTrue(report['program_verification_required'])
            self.assertTrue(report['program_pointer_may_reset'])
            self.assertEqual(self.session.main_source,original_main)
            posts=[c for c in self.session.calls if c[0]=='POST']
            self.assertEqual([c[2]['params']['action'] for c in posts],['request','set-module-text','release'])
            again=client.update_module(Path(tmp))
            self.assertTrue(again['already_installed'])
            self.assertEqual(len([c for c in self.session.calls if c[0]=='POST']),3)

    def test_transfer_blocks_unsafe_state_modified_source_and_pending_target(self):
        for field,value in (('ctrl','motoron'),('execution','running'),('mode','MANR'),
                            ('source',SOURCE+'\n!change'),('target',[[0.]*6,[9e9]*6])):
            client=self.client();setattr(self.session,field,value)
            with tempfile.TemporaryDirectory() as tmp,self.assertRaises(Refused):
                client.update_module(Path(tmp))
            self.assertFalse(any(c[0]=='POST' for c in self.session.calls))

    def test_transfer_failures_no_retry_release_and_unknown_edit_persisted(self):
        import requests
        for failure in ('403','timeout','bad_readback','mastership_denied'):
            client=self.client();original_post=self.session.post
            def post(url,**kw):
                if url.endswith(MODULE_PATH) and failure=='timeout':
                    self.session.calls.append(('POST',url,kw))
                    raise requests.Timeout('simulado')
                return original_post(url,**kw)
            if failure=='403':self.session.edit_status=403
            if failure=='bad_readback':self.session.ignore_edit=True
            if failure=='mastership_denied':self.session.mastership_status=403
            with tempfile.TemporaryDirectory() as tmp,patch('irb120_control.rws_j6.time.sleep'):
                with patch.object(self.session,'post',side_effect=post),self.assertRaises((Refused,requests.Timeout)):
                    client.update_module(Path(tmp))
                journal=json.loads(next(Path(tmp).glob('*/transferencia.json')).read_text())
                self.assertFalse(journal['passed'])
                actions=[c[2]['params']['action'] for c in self.session.calls if c[0]=='POST']
                if failure=='mastership_denied':self.assertEqual(actions,['request'])
                else:self.assertEqual(actions,['request','set-module-text','release'])
                if failure=='timeout':self.assertEqual(journal['write_events'][1]['result'],'pending_or_unknown')

    def test_actual_rw612_release_already_not_held_is_distinguished_from_other_403(self):
        for already_released in (True,False):
            client=self.client();original_post=self.session.post
            def post(url,**kw):
                if kw['params']['action']=='release':
                    self.session.calls.append(('POST',url,kw))
                    response=Response(status=403)
                    message=('rws_resource_mastership.cpp[563] The resource is not held by caller '
                             'code:-1073445880 icode:-1' if already_released else 'Permission denied')
                    response.text=json.dumps({'_embedded':{'status':{'code':-1073445880,'msg':message},'_state':[]}})
                    return response
                return original_post(url,**kw)
            with tempfile.TemporaryDirectory() as tmp,patch('irb120_control.rws_j6.time.sleep'),patch.object(self.session,'post',side_effect=post):
                if already_released:
                    report=client.update_module(Path(tmp))
                    self.assertTrue(report['passed'])
                    self.assertEqual(report['mastership_release'],'already_not_held_by_this_session')
                else:
                    with self.assertRaises(Refused):client.update_module(Path(tmp))

    def test_read_only_diagnosis_distinguishes_auto_from_manual_without_authorizing_motion(self):
        client=self.client();self.session.source=J6_SOURCE
        for mode in ('AUTO','MANR','MANF','AUTO_CH','UNDEF'):
            self.session.mode=mode
            report=diagnose_inspection(client.inspect())
            self.assertEqual(report['local_navigation_prerequisites_observed'],mode=='MANR')
            self.assertFalse(report['motion_authorized_by_diagnostic'])
            self.assertFalse(report['local_execution_verified'])
            self.assertFalse(report['motion_command_sent'])
            if mode=='AUTO':self.assertTrue(any('MODO_AUTO:' in s for s in report['issues']))
        self.assertTrue(all(c[0]=='GET' for c in self.session.calls))

    def test_diagnosis_reports_guard_stop_pending_target_and_original_module_independently(self):
        for field,value,issue in (('ctrl','guardstop','ESTADO_CONTROLADOR:'),
                                  ('execution','running','RAPID_NO_DETENIDO:'),
                                  ('target',[[0.]*6,[9e9]*6],'OBJETIVO_PENDIENTE:'),
                                  ('source',SOURCE,'MODULO_NO_J6_REVISADO:'),
                                  ('robot','other','IDENTIDAD_NO_VERIFICADA:')):
            client=self.client();self.session.source=J6_SOURCE;self.session.mode='MANR'
            setattr(self.session,field,value)
            report=diagnose_inspection(client.inspect())
            self.assertFalse(report['local_navigation_prerequisites_observed'])
            self.assertTrue(any(issue in s for s in report['issues']),report['issues'])
            self.assertTrue(all(c[0]=='GET' for c in self.session.calls))

    def test_missing_readings_never_become_empty_target_or_manual_ready(self):
        client=self.client();self.session.source=J6_SOURCE;self.session.mode='MANR'
        inspection=client.inspect()
        inspection['resources']['target']={'ok':False,'error':'HTTP 403'}
        inspection['resources']['mode']={'ok':True,'records':[]}
        report=diagnose_inspection(inspection)
        self.assertIsNone(report['target_pending']);self.assertIsNone(report['mode'])
        self.assertFalse(report['local_navigation_prerequisites_observed'])

    def test_historical_real_inspection_diagnosis_offline_cli_does_not_request_password_or_network(self):
        import requests
        path=Path(__file__).resolve().parents[4]/'docs/conexion_abb/evidencias/rws_j6_inspection_2026-11-10.json'
        with patch('irb120_control.rws_j6.getpass.getpass') as password,patch.object(requests,'Session') as session,patch('sys.stdout',new_callable=io.StringIO) as output:
            result=main(['diagnosticar','--informe',str(path)])
        self.assertEqual(result,2)
        self.assertIn('ARCHIVO HISTORICO, NO ES ESTADO ACTUAL',output.getvalue())
        self.assertIn('MODO_AUTO:',output.getvalue())
        password.assert_not_called();session.assert_not_called()

    def test_live_diagnostic_cli_saves_readings_and_never_posts_even_with_pending_target(self):
        import requests
        self.client();self.session.source=J6_SOURCE
        self.session.target=copy.deepcopy(self.session.current)
        with tempfile.TemporaryDirectory() as tmp,patch('irb120_control.rws_j6.getpass.getpass',return_value='test-only'),patch.object(requests,'Session',return_value=self.session),patch('sys.stdout',new_callable=io.StringIO) as output:
            result=main(['diagnosticar','--host','127.0.0.1','--log-dir',tmp])
            report=json.loads(next(Path(tmp).glob('diagnostico_*.json')).read_text())
            inspection=json.loads(next(Path(tmp).glob('inspeccion_*.json')).read_text())
        self.assertEqual(result,2)
        self.assertTrue(report['target_pending']);self.assertFalse(report['historical_report'])
        self.assertFalse(report['motion_authorized_by_diagnostic'])
        self.assertIn('OBJETIVO_PENDIENTE:',output.getvalue())
        self.assertTrue(all(c[0]=='GET' for c in self.session.calls))
        self.assertEqual(self.session.target,self.session.current)
        self.assertNotIn('test-only',json.dumps(report)+json.dumps(inspection)+output.getvalue())


if __name__=='__main__':unittest.main()
