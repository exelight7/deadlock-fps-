"""Prepare, review and commit mod-only changes without requiring a video account."""
from dataclasses import dataclass
from .core import Studio,ensure_closed
from .settings import Settings
from .mod_inspector import inspect_mods
from .mods import ImportCancelled

@dataclass
class PreparedMods:
    root:object
    settings:Settings
    plan:dict
    before:dict
    state:bytes|None
    report:object

def raw(path):return path.read_bytes() if path.exists() else None

def prepare_mods(root,library,selected,cancel=None):
    ensure_closed();studio=Studio(root);settings=Settings.from_dict(studio.state().get('settings',{}));settings.mods=tuple(selected);settings.validate()
    report=inspect_mods(library,studio.root,selected,cancel)
    if report is None or cancel and cancel.is_set():raise ImportCancelled('أُلغي الفحص قبل التركيب؛ لم تتغير ملفات اللعبة.')
    if report.errors:raise ValueError('\n'.join(f.title+': '+f.detail for f in report.errors))
    plan=studio.plan_mods(settings.mods,library.cache)
    if cancel and cancel.is_set():raise ImportCancelled('أُلغي الفحص قبل التركيب؛ لم تتغير ملفات اللعبة.')
    return PreparedMods(studio.root,settings,plan,{p:raw(p) for p in plan},raw(studio.manifest),report)

def commit_mods(prepared,library):
    fresh=prepare_mods(prepared.root,library,prepared.settings.mods)
    if fresh.plan!=prepared.plan or fresh.before!=prepared.before or fresh.state!=prepared.state:raise ValueError('تغيّرت الملفات بعد الفحص؛ اضغط التركيب مرة أخرى لمراجعة النسخة الحالية.')
    result=Studio(prepared.root).apply(prepared.plan,prepared.settings,mod_only=True)
    return result
