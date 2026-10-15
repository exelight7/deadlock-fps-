import hashlib,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QObject,Signal,QUrl,Qt
from PySide6.QtNetwork import QNetworkRequest,QNetworkReply
from PySide6.QtWidgets import QApplication
from deadlock_fps.updates import Version,parse_release,platform_key,checksum_for,Download,UpdateStore,REPO_URL
from deadlock_fps.update_client import UpdateClient,allowed_redirect

PAYLOAD=b'portable package bytes';HASH=hashlib.sha256(PAYLOAD).hexdigest()
MANIFEST=(HASH+'  DeadlockToolbox-linux-x64.zip\n'+HASH+'  DeadlockToolbox-windows-x64.zip\n').encode()
def release_data(tag='v2.2.2'):
    assets=[]
    for name,data in [('DeadlockToolbox-linux-x64.zip',PAYLOAD),('DeadlockToolbox-windows-x64.zip',PAYLOAD),('SHA256SUMS.txt',MANIFEST)]:
        assets.append(dict(name=name,state='uploaded',size=len(data),digest='sha256:'+hashlib.sha256(data).hexdigest(),browser_download_url=REPO_URL+'/releases/download/'+tag+'/'+name))
    return dict(tag_name=tag,name='Toolbox إصدار جديد',body='Release notes\nخطوات التحديث',published_at='2026-10-15T12:00:00Z',draft=False,prerelease=False,html_url=REPO_URL+'/releases/tag/'+tag,assets=assets)


class Models(unittest.TestCase):
    def test_semver_orders_patch_numeric_prereleases_and_stable_correctly(self):
        values=['1.0.0-alpha','1.0.0-alpha.1','1.0.0-alpha.beta','1.0.0-beta','1.0.0-beta.2','1.0.0-beta.11','1.0.0-rc.1','1.0.0','1.0.1','1.0.10','2.0.0']
        self.assertEqual(sorted(map(Version.parse,reversed(values))),list(map(Version.parse,values)))
        self.assertEqual(Version.parse('v1.0.0+build.1'),Version.parse('1.0.0'))
        for bad in ['1.0','01.2.3','1.2.3-pre.01','../../1.2.3',None]:
            with self.assertRaises(ValueError):Version.parse(bad)
    def test_only_matching_x64_package_is_selected(self):
        release=parse_release(release_data())
        self.assertEqual(release.package('Windows','AMD64').name,'DeadlockToolbox-windows-x64.zip')
        self.assertEqual(release.package('Linux','x86_64').name,'DeadlockToolbox-linux-x64.zip')
        for system,machine in [('Linux','aarch64'),('Windows','ARM64'),('Darwin','x86_64')]:self.assertIsNone(release.package(system,machine))
    def test_untrusted_duplicate_incomplete_or_injected_release_is_rejected(self):
        for field,value in [('html_url','https://evil.test/release'),('draft',True),('prerelease',True),('tag_name','../../outside')]:
            d=release_data();d[field]=value
            with self.assertRaises(ValueError):parse_release(d)
        for field,value in [('browser_download_url','https://github.com/other/repo/package.zip'),('state','new'),('size',True),('size',99999999999),('digest','sha256:bad')]:
            d=release_data();d['assets'][0][field]=value
            with self.assertRaises(ValueError):parse_release(d)
        d=release_data();d['assets'].append(d['assets'][0])
        with self.assertRaises(ValueError):parse_release(d)
    def test_checksums_need_manifest_size_digest_and_consistent_asset_digest(self):
        release=parse_release(release_data());asset=release.assets[0];manifest=release.asset('SHA256SUMS.txt')
        self.assertEqual(checksum_for(MANIFEST,asset,manifest),HASH)
        for data in [MANIFEST[:-1],MANIFEST.replace(b'portable',b'altered'),MANIFEST.replace(HASH.encode(),b'0'*64)]:
            if data==MANIFEST:continue
            with self.assertRaises(ValueError):checksum_for(data,asset,manifest)
        from dataclasses import replace
        for raw in [MANIFEST+MANIFEST, b'0'*64+b'  absent.zip\n']:
            with self.assertRaises(ValueError):checksum_for(raw,asset,replace(manifest,size=len(raw),digest=''))
        with self.assertRaises(ValueError):checksum_for(MANIFEST,replace(asset,digest='0'*64),manifest)
    def test_redirects_reject_credentials_http_and_foreign_hosts(self):
        self.assertTrue(allowed_redirect('https://release-assets.githubusercontent.com/a?sig=1','download'))
        self.assertTrue(allowed_redirect('https://api.github.com/repos/x','check'))
        for value in ['http://github.com/a','https://github.com.evil.test/a','https://user@github.com/a','https://github.com:8080/a']:
            self.assertFalse(allowed_redirect(value,'download'))
        self.assertFalse(allowed_redirect('https://github.com/a','check'))


class Files(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);self.release=parse_release(release_data());self.asset=self.release.assets[0]
    def tearDown(self):self.temp.cleanup()
    def test_atomic_download_preserves_existing_until_verified(self):
        target=self.folder/self.release.tag/self.asset.name;target.parent.mkdir();target.write_bytes(b'old')
        writer=Download(self.folder,self.release,self.asset,HASH);writer.write(PAYLOAD[:5]);self.assertEqual(target.read_bytes(),b'old');writer.write(PAYLOAD[5:])
        self.assertEqual(writer.commit(),target);self.assertEqual(target.read_bytes(),PAYLOAD);self.assertFalse(writer.part.exists())
    def test_cancel_short_corrupt_and_oversize_downloads_do_not_leave_partial_files(self):
        for payload,action in [(PAYLOAD[:2],'commit'),(b'x'*len(PAYLOAD),'commit'),(PAYLOAD,'abort'),(PAYLOAD+b'extra','write')]:
            writer=Download(self.folder,self.release,self.asset,HASH)
            if action=='write':
                with self.assertRaises(ValueError):writer.write(payload)
                writer.abort()
            else:
                writer.write(payload)
                if action=='commit':
                    with self.assertRaises(ValueError):writer.commit()
                else:writer.abort()
            self.assertFalse(writer.target.exists());self.assertFalse(writer.part.exists())
    def test_cache_utf8_etag_preferences_and_daily_limit(self):
        store=UpdateStore(self.folder);self.assertTrue(store.due());store.mark_attempt();self.assertFalse(store.due());store.record(release_data(),'"etag"')
        again=UpdateStore(self.folder);self.assertEqual(again.release.title,'Toolbox إصدار جديد');self.assertEqual(again.etag,'"etag"');self.assertFalse(again.due())
        self.assertTrue(again.due(time.time()+86401));again.auto_check=False;again.save_preferences();self.assertFalse(UpdateStore(self.folder).auto_check)
        self.assertFalse(again.due(time.time()+999999))
    def test_bad_cache_cannot_make_an_update_available(self):
        self.folder.joinpath('latest.json').write_text('{bad',encoding='utf-8');store=UpdateStore(self.folder);self.assertIsNone(store.release);self.assertTrue(store.due());self.assertTrue(store.warning)
        with self.assertRaises(ValueError):store.unchanged()


class Reply(QObject):
    readyRead=Signal();redirected=Signal(QUrl);redirectAllowed=Signal();finished=Signal()
    def __init__(self):
        super().__init__();self.data=bytearray();self.status=200;self.code=QNetworkReply.NoError;self.aborted=False;self.redirect_allowed=False
        self.redirectAllowed.connect(lambda:setattr(self,'redirect_allowed',True))
    def attribute(self,key):return self.status
    def error(self):return self.code
    def errorString(self):return 'test error'
    def rawHeader(self,key):
        if not isinstance(key,str):raise TypeError('Qt rawHeader expects str')
        return b'"test-etag"'
    def setReadBufferSize(self,size):pass
    def bytesAvailable(self):return len(self.data)
    def read(self,count):chunk=bytes(self.data[:count]);del self.data[:count];return chunk
    def abort(self):self.aborted=True;self.finished.emit()
    def feed(self,data=b'',status=200,error=QNetworkReply.NoError,finish=True):
        self.status=status;self.code=error;self.data.extend(data);self.readyRead.emit()
        if finish:self.finished.emit()

class Manager:
    def __init__(self):self.requests=[];self.replies=[]
    def get(self,request):
        reply=Reply();self.requests.append(request);self.replies.append(reply);return reply


class NetworkFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);self.store=UpdateStore(self.folder/'state');self.manager=Manager();self.client=UpdateClient(self.store,manager=self.manager);self.errors=[];self.done=[];self.found=[]
        self.client.failed.connect(self.errors.append);self.client.downloaded.connect(self.done.append);self.client.found.connect(lambda r,c:self.found.append(r))
    def tearDown(self):self.client.cancel();self.temp.cleanup()


class Network(NetworkFixture):
    def test_metadata_conditional_304_and_bounded_body(self):
        self.client.check();self.manager.replies[-1].feed(json.dumps(release_data()).encode());self.assertEqual(len(self.found),1);self.assertFalse(self.client.busy)
        self.client.check();self.assertEqual(bytes(self.manager.requests[-1].rawHeader('If-None-Match')),b'"test-etag"');self.manager.replies[-1].feed(status=304);self.assertEqual(len(self.found),2)
        self.client.check();reply=self.manager.replies[-1];reply.feed(b'x'*(2*1024*1024+1));self.assertTrue(reply.aborted);self.assertTrue(self.errors);self.assertFalse(self.client.busy)
    def test_download_verifies_manifest_then_streamed_payload(self):
        self.client.download(parse_release(release_data()),self.folder/'downloads');self.assertEqual(len(self.manager.requests),1)
        self.manager.replies[-1].feed(MANIFEST);self.assertEqual(len(self.manager.requests),2)
        self.manager.replies[-1].feed(PAYLOAD[:5],finish=False);self.assertFalse(self.done);self.manager.replies[-1].feed(PAYLOAD[5:]);self.assertEqual(self.done[0].read_bytes(),PAYLOAD);self.assertFalse(self.errors)
    def test_cancel_handles_synchronous_finished_and_cleans_partial(self):
        self.client.download(parse_release(release_data()),self.folder/'downloads');self.manager.replies[-1].feed(MANIFEST);reply=self.manager.replies[-1];reply.feed(PAYLOAD[:2],finish=False);part=self.client.writer.part
        self.client.cancel();self.assertTrue(reply.aborted);self.assertFalse(part.exists());self.assertFalse(self.done);self.assertFalse(self.errors);self.assertFalse(self.client.busy)
    def test_corrupt_manifest_never_requests_package_and_invalid_redirect_aborts(self):
        self.client.download(parse_release(release_data()),self.folder/'downloads');self.manager.replies[-1].feed(b'bad');self.assertEqual(len(self.manager.requests),1);self.assertTrue(self.errors)
        self.client.check();reply=self.manager.replies[-1];reply.redirected.emit(QUrl('https://evil.test/file'));self.assertTrue(reply.aborted);self.assertFalse(reply.redirect_allowed)
    def test_approved_redirect_is_explicitly_allowed_and_download_http_error_cleans_file(self):
        self.client.download(parse_release(release_data()),self.folder/'downloads');reply=self.manager.replies[-1];reply.redirected.emit(QUrl('https://release-assets.githubusercontent.com/manifest?signature=1'));self.assertTrue(reply.redirect_allowed)
        reply.feed(MANIFEST);part=self.client.writer.part;self.manager.replies[-1].feed(status=500);self.assertFalse(part.exists());self.assertTrue(self.errors);self.assertFalse(self.done)
    def test_http_failures_keep_cached_data_without_reporting_fresh_success(self):
        self.store.record(release_data());self.client.check();self.manager.replies[-1].feed(status=403);self.assertTrue(self.errors);self.assertFalse(self.found);self.assertIsNotNone(self.store.release)
    def test_network_error_on_304_never_reports_a_successful_check(self):
        self.store.record(release_data());checked=self.store.checked_at;self.client.check();self.manager.replies[-1].feed(status=304,error=QNetworkReply.RemoteHostClosedError)
        self.assertFalse(self.found);self.assertTrue(self.errors);self.assertEqual(self.store.checked_at,checked)
    def test_cancellation_from_phase_and_progress_signals_cannot_restart_requests(self):
        self.client.phaseChanged.connect(lambda _:self.client.cancel());self.client.check();self.assertFalse(self.manager.requests);self.assertFalse(self.client.busy)
        self.client.phaseChanged.disconnect();self.client.download(parse_release(release_data()),self.folder/'downloads')
        self.client.progress.connect(lambda *_:self.client.cancel());self.manager.replies[-1].feed(MANIFEST)
        self.assertEqual(len(self.manager.requests),1);self.assertFalse(self.client.busy);self.assertFalse(list((self.folder/'downloads').rglob('*.part')))
    def test_cancellation_from_streamed_progress_stops_reading_without_error(self):
        self.client.download(parse_release(release_data()),self.folder/'downloads');self.manager.replies[-1].feed(MANIFEST)
        self.client.progress.connect(lambda *_:self.client.cancel());self.manager.replies[-1].feed(PAYLOAD)
        self.assertFalse(self.client.busy);self.assertFalse(self.done);self.assertFalse(self.errors);self.assertFalse(list((self.folder/'downloads').rglob('*.part')))


class Interface(NetworkFixture):
    def test_release_states_cache_and_persistent_auto_preference(self):
        from deadlock_fps.update_ui import UpdatePage
        page=UpdatePage(store=self.store,current='2.1.0',manager=self.manager,download_folder=self.folder/'downloads')
        page.show_release(parse_release(release_data()),True);self.assertFalse(page.download_button.isEnabled());page.check();self.manager.replies[-1].feed(json.dumps(release_data()).encode());self.assertIn('تحديث جديد',page.state.text());self.assertTrue(page.download_button.isEnabled())
        self.assertTrue(page.progress.isHidden());self.assertTrue(page.progress_text.isHidden())
        page.auto_check.setChecked(False);self.assertFalse(UpdateStore(self.store.folder).auto_check)
        page.check();self.manager.replies[-1].feed(status=404);self.assertFalse(page.download_button.isEnabled());self.assertIn('محفوظة',page.checked.text());page.close()
        preview=UpdatePage(store=self.store,current='2.3.0-preview.1',manager=Manager());preview.show_release(parse_release(release_data()));self.assertIn('أحدث',preview.state.text());self.assertIn('أقدم',preview.download_button.text());preview.close()
    def test_window_page_is_accessible_at_minimum_size_and_stops_network_on_close(self):
        from deadlock_fps.ui import Window
        with patch('deadlock_fps.update_ui.UpdateStore',return_value=self.store):window=Window()
        window.guard_timer.stop();window.servers.activate=lambda:None;window.resize(940,680);window.show();window.navigate(6);self.app.processEvents()
        self.assertEqual(window.stack.currentIndex(),6);self.assertFalse(window.hero.isVisible());self.assertFalse(window.actionbar.isVisible());self.assertTrue(window.updates.download_button.isVisible());self.assertFalse(window.update_startup_timer.isActive())
        for button in window.nav:
            self.assertGreaterEqual(button.y(),0);self.assertLessEqual(button.y()+button.height(),window.height())
        manager=Manager();window.updates.client.manager=manager;window.updates.check();reply=manager.replies[-1];window.close();self.assertTrue(reply.aborted);self.assertFalse(window.updates.client.busy)

if __name__=='__main__':unittest.main()
