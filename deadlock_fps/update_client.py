"""Cancellable Qt networking; no polling, worker threads or executable replacement."""
import json
from urllib.parse import urlsplit
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from .updates import LATEST_URL, MAX_METADATA, MAX_CHECKSUMS, checksum_for, Download


def allowed_redirect(url,phase):
    u=urlsplit(url)
    hosts={'api.github.com'} if phase=='check' else {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','github-releases.githubusercontent.com'}
    return u.scheme=='https' and u.hostname in hosts and not u.username and not u.password and u.port in (None,443)


class UpdateClient(QObject):
    busyChanged=Signal(bool)
    phaseChanged=Signal(str)
    found=Signal(object,bool)
    progress=Signal(int,int)
    downloaded=Signal(object)
    failed=Signal(str)
    cancelled=Signal()

    def __init__(self,store,parent=None,manager=None):
        super().__init__(parent);self.store=store;self.manager=manager or QNetworkAccessManager(self)
        self._reply=None;self.phase='';self.buffer=bytearray();self.writer=None;self.release=None;self.asset=None;self.folder=None;self.downloaded_hash=''

    @property
    def busy(self):return bool(self.phase)

    def check(self):
        if self.busy:return
        try:self.store.mark_attempt()
        except OSError as e:self.failed.emit('تعذر حفظ وقت الفحص: '+str(e));return
        self.phase='check';self.busyChanged.emit(True);self.phaseChanged.emit(self.phase)
        self._get(LATEST_URL)

    def download(self,release,folder):
        if self.busy:return
        asset=release.package();manifest=release.asset('SHA256SUMS.txt')
        if not asset or not manifest:self.failed.emit('لا تتوفر حزمة متوافقة مع نظامك وملف تحقق لهذا الإصدار.');return
        self.release=release;self.asset=asset;self.folder=folder;self.downloaded_hash='';self.phase='checksum'
        self.busyChanged.emit(True);self.phaseChanged.emit(self.phase);self._get(manifest.url)

    def _get(self,url):
        if not self.busy:return
        self.buffer=bytearray()
        try:
            request=QNetworkRequest(QUrl(url));request.setRawHeader(b'User-Agent',b'DeadlockToolbox-UpdateCenter')
            request.setRawHeader(b'Accept',b'application/vnd.github+json' if self.phase=='check' else b'application/octet-stream')
            request.setAttribute(QNetworkRequest.RedirectPolicyAttribute,QNetworkRequest.UserVerifiedRedirectPolicy)
            request.setMaximumRedirectsAllowed(5)
            request.setTransferTimeout(15000 if self.phase=='check' else 30000)
            if self.phase=='check':
                request.setRawHeader(b'X-GitHub-Api-Version',b'2022-11-28')
                if self.store.etag:request.setRawHeader(b'If-None-Match',self.store.etag.encode('utf-8'))
            reply=self.manager.get(request);self._reply=reply;reply.setReadBufferSize(256*1024)
            reply.readyRead.connect(lambda:self._read(reply))
            reply.redirected.connect(lambda target:self._redirect(reply,target))
            reply.finished.connect(lambda:self._finished(reply))
        except Exception as e:self._fail(str(e))

    def _redirect(self,reply,target):
        if self._reply is not reply:return
        try:allowed=allowed_redirect(target.toString(),self.phase)
        except ValueError:allowed=False
        if allowed:reply.redirectAllowed.emit()
        else:self._fail('أوقف التنزيل: وجهة التحويل خارج خوادم GitHub المعتمدة.')

    def _read(self,reply):
        if self._reply is not reply:return
        status=reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status and 300<=int(status)<400:return
        try:
            while reply.bytesAvailable():
                chunk=bytes(reply.read(64*1024))
                if not chunk:break
                if self.phase=='download':
                    self.writer.write(chunk);self.progress.emit(self.writer.received,self.asset.size)
                    if self._reply is not reply:return
                else:
                    limit=MAX_METADATA if self.phase=='check' else MAX_CHECKSUMS
                    if len(self.buffer)+len(chunk)>limit:raise ValueError('استجابة الخادم أكبر من المسموح.')
                    self.buffer.extend(chunk)
        except Exception as e:self._fail(str(e))

    def _finished(self,reply):
        if self._reply is not reply:return
        self._read(reply)
        if self._reply is not reply:return
        status=reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        self._reply=None
        try:
            if status==304 and self.phase=='check' and reply.error()==QNetworkReply.NoError:
                release=self.store.unchanged();self._idle();self.found.emit(release,False);return
            if status!=200 or reply.error()!=QNetworkReply.NoError:
                if status==403 or status==429:raise ValueError('وصل GitHub لحد الطلبات. انتظر قليلًا ثم أعد الفحص.')
                if status==404:raise ValueError('لا يوجد إصدار عام متاح في المستودع حاليًا.')
                raise ValueError('تعذر الاتصال بـ GitHub. تحقق من الإنترنت ثم أعد المحاولة. '+reply.errorString())
            if self.phase=='check':
                data=json.loads(bytes(self.buffer).decode('utf-8'));etag=bytes(reply.rawHeader('ETag')).decode('utf-8')
                release=self.store.record(data,etag);self._idle();self.found.emit(release,False)
            elif self.phase=='checksum':
                expected=checksum_for(bytes(self.buffer),self.asset,self.release.asset('SHA256SUMS.txt'))
                self.writer=Download(self.folder,self.release,self.asset,expected);self.phase='download';self.phaseChanged.emit(self.phase)
                if self.phase=='download':
                    self.progress.emit(0,self.asset.size)
                    if self.phase=='download':self._get(self.asset.url)
            elif self.phase=='download':
                expected=self.writer.expected;path=self.writer.commit();self.downloaded_hash=expected;self.writer=None;self._idle();self.downloaded.emit(path)
        except Exception as e:self._fail(str(e))
        finally:reply.deleteLater()

    def _idle(self):
        self.phase='';self.buffer=bytearray();self.busyChanged.emit(False)

    def _stop(self):
        reply=self._reply;self._reply=None
        self.phase='';self.buffer=bytearray()
        if reply:reply.abort();reply.deleteLater()
        if self.writer:
            self.writer.abort();self.writer=None
        self.busyChanged.emit(False)

    def _fail(self,message):
        self._stop();self.failed.emit(message)

    def cancel(self):
        if not self.busy:return
        self._stop();self.cancelled.emit()
