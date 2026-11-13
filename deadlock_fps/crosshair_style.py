"""Stylesheet for the English, left-to-right Crosshair workspace: the shared Toolbox sheet with a Latin-first font order."""
from .design import build_style

STYLE = build_style(latin=True) + '''
QLabel#cardtitle {font-size:15px;}
QListWidget#tiles {background:%s;padding:6px;}
''' % __import__('deadlock_fps.theme', fromlist=['SUNKEN']).SUNKEN
