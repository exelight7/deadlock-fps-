"""Opt-in HTTPS check/download through the real Update Center, isolated from user data.

Run after publication, e.g.:
python scripts/verify_update_center_live.py --expected v2.4.0 --current 2.3.0 --download
No game files, saved preferences or installed executables are touched.
"""
import argparse,os,sys,hashlib,json
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QEventLoop,QTimer
from PySide6.QtWidgets import QApplication
from deadlock_fps.update_ui import UpdatePage
from deadlock_fps.updates import UpdateStore,Version


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expected',required=True);parser.add_argument('--current',required=True);parser.add_argument('--download',action='store_true');parser.add_argument('--system',choices=['linux','windows']);parser.add_argument('--folder',type=Path,default=Path('build/qa/live-update-center'))
    args=parser.parse_args();app=QApplication([]);folder=args.folder.resolve();folder.mkdir(parents=True,exist_ok=True)
    context=patch('deadlock_fps.updates.platform_key',return_value=args.system) if args.system else nullcontext()
    with context:
        page=UpdatePage(store=UpdateStore(folder/'state'),current=args.current,download_folder=folder/'downloads');errors=[];page.client.failed.connect(errors.append)
        def wait(start,limit):
            loop=QEventLoop();timer=QTimer();timer.setSingleShot(True);timed_out=[]
            timer.timeout.connect(lambda:(timed_out.append(True),loop.quit()));page.client.busyChanged.connect(lambda busy:loop.quit() if not busy else None)
            start()
            if page.client.busy:timer.start(limit);loop.exec()
            timer.stop();assert not timed_out,'Live Update Center timed out';assert not errors,errors
        wait(page.check,60000)
        assert page.fresh and page.release.tag==args.expected,(page.state.text(),page.latest.text(),page.detail.text())
        newer=Version.parse(args.expected)>Version.parse(args.current)
        assert page.state.text()==('تحديث جديد متاح' if newer else 'أنت على آخر إصدار عام'),page.state.text()
        assert page.download_button.isEnabled(),page.detail.text()
        # A second actual HTTP request exercises conditional ETag/304 behavior.
        wait(page.check,60000);assert page.fresh and page.release.tag==args.expected
        result=dict(expected=args.expected,current=args.current,state=page.state.text(),system=args.system or 'native',fresh=page.fresh,download_enabled=page.download_button.isEnabled(),etag_saved=bool(page.store.etag))
        if args.download:
            wait(page.download,600000);assert page.saved_path and page.saved_path.is_file(),page.detail.text();assert page.state.text()=='تم التحقق من التنزيل ✓',page.state.text()
            path=page.saved_path
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            result.update(download=str(path),size=path.stat().st_size,sha256=digest,verified=True)
            assert not list(path.parent.glob('*.part')) and not list(path.parent.glob('.*.part'))
        (folder/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False));page.close();page.client.cancel()

if __name__=='__main__':main()
