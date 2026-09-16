import unittest,tempfile,shutil,json,threading,time,urllib.request,urllib.error
from pathlib import Path
from datetime import date,timedelta
from study_widget_core import StudyModel,ROOT
from study_sync import SharedProgress,merge,empty,latest
from study_server import StudyServer

class StudyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        shutil.copy2(ROOT/'study_schedule.json',self.root/'study_schedule.json')
        self.model=StudyModel(self.root,today=date(2026,9,16));self.first=date(2026,9,16)
    def tearDown(self):self.temp.cleanup()
    def finish(self,day):
        p=self.model.plan(day);self.model.record(p,{t.id for t in p.tasks})
    def test_manual_unlock_same_day_and_restart(self):
        nextday=self.first+timedelta(days=1)
        self.assertTrue(self.model.is_locked(nextday))
        with self.assertRaises(ValueError):self.model.unlock_next(self.first)
        self.finish(self.first);self.assertTrue(self.model.is_locked(nextday))
        self.model.unlock_next(self.first);self.assertFalse(self.model.is_locked(nextday))
        model=StudyModel(self.root,today=self.first);self.assertFalse(model.is_locked(nextday))
        self.finish(nextday);self.assertEqual(self.model.calendar_status(nextday,self.first),'complete')
    def test_no_date_auto_unlock_or_skip(self):
        self.assertTrue(self.model.is_locked(self.first+timedelta(days=1),date(2030,1,1)))
        with self.assertRaises(ValueError):self.finish(self.first+timedelta(days=3))
    def test_revoke_prior_check_relocks_without_losing_next_progress(self):
        self.finish(self.first);day=self.model.unlock_next(self.first)
        self.model.mark_task(day,'read',True);self.model.mark_task(self.first,'read',False)
        self.assertTrue(self.model.is_locked(day));self.assertIn('read',self.model.done(self.model.plan(day)))
        self.model.mark_task(self.first,'read',True);self.assertFalse(self.model.is_locked(day))
    def test_interview_date_does_not_replace_curriculum(self):
        self.model.update_settings({'interview_date':'2026-09-17'})
        self.assertEqual([t.id for t in self.model.plan(date(2026,9,17)).tasks],['recall','read','exercise','oral','note'])
    def test_49_stages_unlocked_in_order(self):
        day=self.first
        for _ in range(49):
            self.assertFalse(self.model.is_locked(day));self.finish(day);day=self.model.unlock_next(day)
        self.assertEqual(self.model.current_stage(),day)
    def test_legacy_note_and_checks_preserved(self):
        self.finish(self.first);p=self.model.plan(self.first);self.model.record(p,self.model.done(p),'한글 메모 <script> &')
        shared=SharedProgress(self.model);doc=shared.capture()
        self.assertEqual(latest(doc['notes'][self.first.isoformat()]),'한글 메모 <script> &')
        self.assertTrue(doc['fields']['done:2026-09-16:read']['value'])
    def test_merge_independent_check_uncheck_and_note_revisions(self):
        a=empty();b=empty();a['fields']['done:2026-09-16:read']={'value':True,'stamp':'1000000000000-a'}
        b['fields']['done:2026-09-16:read']={'value':False,'stamp':'1000000000001-b'}
        b['fields']['done:2026-09-16:oral']={'value':True,'stamp':'1000000000001-b'}
        a['notes']['2026-09-16']={'1000000000000-a':'PC 메모'};b['notes']['2026-09-16']={'1000000000001-b':'휴대폰 메모'}
        c=merge(a,b);self.assertEqual(c,merge(b,a));self.assertFalse(c['fields']['done:2026-09-16:read']['value']);self.assertEqual(len(c['notes']['2026-09-16']),2)
    def test_remote_application_and_clock_skew(self):
        shared=SharedProgress(self.model);remote=empty();remote['notes']['2026-09-16']={'9000000000000-remote':'먼저 쓴 메모'}
        shared.apply(remote);p=self.model.plan(self.first);self.model.record(p,set(),'나중 수정')
        result=shared.capture();self.assertEqual(latest(result['notes']['2026-09-16']),'나중 수정')
    def test_http_assets_state_and_private_file_block(self):
        web=self.root/'web';web.mkdir();(web/'index.html').write_text('<html>test</html>')
        server=StudyServer(self.model,auto_sync=False);stop=threading.Event()
        def drain():
            while not stop.is_set():server.drain();time.sleep(.005)
        thread=threading.Thread(target=drain);thread.start();base=f'http://127.0.0.1:{server.http.server_port}'
        try:
            self.assertEqual(urllib.request.urlopen(base+'/').status,200)
            state=json.load(urllib.request.urlopen(base+'/api/state'));self.assertEqual(state['version'],3)
            for path in ['/study_widget_state.json','/progress/state.json','/assets/../../study_widget_state.json']:
                with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(base+path)
                self.assertEqual(cm.exception.code,404)
            req=urllib.request.Request(base+'/api/state',headers={'Origin':'https://untrusted.example'})
            with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(req)
            self.assertEqual(cm.exception.code,403)
            self.assertTrue(server.url(self.first,'oral').endswith('?day=2026-09-16#oral'))
        finally:stop.set();thread.join();server.close();server.http.server_close()

if __name__=='__main__':unittest.main(verbosity=2)
