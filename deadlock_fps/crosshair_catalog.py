"""Offline, attributed snapshots; no network requests while browsing the gallery."""
from dataclasses import dataclass
from .crosshair import Crosshair,PRESETS

@dataclass(frozen=True)
class CatalogEntry:
    key:str
    name:str
    design:Crosshair
    group:str
    source:str=''
    published:str=''
    detail:str=''

# Numerical settings published in the linked catalog, checked 2026-10-15.
# Attribution is to that catalog, not independent verification of a player's
# current settings. Dew/crayon expose only three values; label defaults clearly.
def player(key,name,date,design,partial=False):
    return CatalogEntry(key,name,design.validate(),'players',
        f'https://deadlocklabs.gg/crosshairs/pro/{key}/',date,
        'Published in Deadlock Labs. Only gap, width and length are attributed to the player; other values are defaults.' if partial else
        'Published in Deadlock Labs. Settings are attributed to the player and may change over time.')

PLAYERS=(
    player('hydration','Hydration','2026-03',Crosshair(width=2,length=8,gap=2,opacity=1,border=1,border_opacity=1,dot=4,dot_opacity=1,dot_border=0,dot_border_opacity=1,color='#00ff00')),
    player('dimov','Dimov','2026-04',Crosshair(width=3,length=7,gap=1,opacity=1,border=0,dot_opacity=0,dot_border_opacity=0,static=True)),
    player('vegas','Vegas','2026-02',Crosshair(width=2,length=5,gap=-9,opacity=1,border=0,border_opacity=1,dot=1,dot_opacity=.7,dot_border=2,dot_border_opacity=.7,static=True,color='#00ff79')),
    player('lefaa','Lefaa','2025-02',Crosshair(width=4,length=2,gap=-2,opacity=1,border=1,dot_opacity=0,dot_border_opacity=1,static=True)),
    player('sharyk','Sharyk','2024-10',Crosshair(width=2,length=4,gap=-3,opacity=1,border=0,dot_opacity=0,dot_border_opacity=0,color='#31ffff')),
    player('dew','Dew','2026-06',Crosshair(width=2,length=4,gap=-1,static=True),True),
    player('crayon','crayon','2025-06',Crosshair(width=1,length=24,gap=-4),True),
    player('shroud','shroud','2024-09',Crosshair(width=2,length=6,gap=-2,opacity=1,border=0,dot_border_opacity=.9,color='#00ffff')),
    player('mikaels','MikaelS','2025-03',Crosshair(width=3,length=5,gap=1,opacity=1,border=1,dot_opacity=0,dot_border_opacity=0,color='#00ff00')),
)

BASE_NAMES={'صليب صغير':'Small Cross','نقطة خضراء':'Green Dot','صليب سماوي':'Cyan Hybrid','دائرة':'Green Ring','صليب كلاسيكي':'Classic Cross'}

def studio(key,name,**values):
    model=Crosshair(width=2,length=6,gap=-6,opacity=1,border=1,border_opacity=.85,dot=0,dot_opacity=0,dot_border_opacity=0,static=True)
    from dataclasses import replace
    return CatalogEntry('studio:'+key,name,replace(model,**values).validate(),'builtin',detail='Original Toolbox design. Fully editable; not attributed to a player.')

# Original shapes, not invented pro-player setups. Every entry has distinct
# native settings; colors, outlines and geometry offer different starting points.
STUDIO=(
    studio('needle','Needle',width=1,length=7,gap=-6,color='#f1f5f0'),
    studio('lime-lock','Lime Lock',length=4,gap=-7,color='#b4ff76'),
    studio('ice-cross','Ice Cross',width=1,length=9,gap=-5,color='#79e8ff'),
    studio('compact','Compact',length=3,gap=-7,color='#ffffff',border=0),
    studio('precision','Precision',length=5,gap=-8,color='#87ff9a'),
    studio('amber','Amber Sight',length=7,gap=-4,color='#ffd36c'),
    studio('orchid','Orchid',width=1,length=8,gap=-6,color='#e7a0ff'),
    studio('rose','Rose Cross',width=3,length=5,gap=-5,color='#ff82b4'),
    studio('longshot','Longshot',width=1,length=15,gap=-3,color='#ffffff'),
    studio('wide-angle','Wide Angle',length=6,gap=3,color='#7cffe7'),
    studio('bold','Bold',width=4,length=8,gap=-4,color='#dcff70'),
    studio('ghost','Ghost',width=1,length=6,gap=-5,opacity=.6,border=0,color='#ffffff'),
    studio('signal','Signal',width=3,length=9,gap=-2,color='#ffb26b',border=2),
    studio('mini-plus','Mini Plus',width=2,length=4,gap=-8,border=0,color='#73eeff'),
    studio('split','Split',width=1,length=4,gap=-1,color='#ffdf7c'),
    studio('deep-green','Deep Green',width=3,length=6,gap=-5,color='#33ff88',border=2),
    studio('pinpoint','Pinpoint',width=0,length=0,dot=2,dot_opacity=1,dot_border=1,dot_border_opacity=1,color='#ffffff'),
    studio('mint-dot','Mint Dot',width=0,length=0,dot=3,dot_opacity=1,dot_border=1,dot_border_opacity=.8,color='#84ffba'),
    studio('cyan-dot','Cyan Dot',width=0,length=0,dot=4,dot_opacity=1,dot_border=0,color='#64eaff'),
    studio('sun-dot','Sun Dot',width=0,length=0,dot=5,dot_opacity=1,dot_border=1,dot_border_opacity=1,color='#ffe06f'),
    studio('rose-dot','Rose Dot',width=0,length=0,dot=4,dot_opacity=.9,dot_border=1,dot_border_opacity=1,color='#ff87b5'),
    studio('bold-dot','Bold Dot',width=0,length=0,dot=6,dot_opacity=1,dot_border=2,dot_border_opacity=1,color='#b7ff70'),
    studio('white-dot','White Dot',width=0,length=0,dot=4,dot_opacity=1,dot_border=2,dot_border_opacity=.8,color='#ffffff'),
    studio('violet-dot','Violet Dot',width=0,length=0,dot=3,dot_opacity=1,dot_border=1,dot_border_opacity=1,color='#c9a0ff'),
    studio('halo','Halo',width=0,length=0,dot=8,dot_opacity=0,dot_border=1,dot_border_opacity=1,outline='#ffffff'),
    studio('mint-ring','Mint Ring',width=0,length=0,dot=10,dot_opacity=0,dot_border=1,dot_border_opacity=1,outline='#87ffc0'),
    studio('cyan-ring','Cyan Ring',width=0,length=0,dot=8,dot_opacity=0,dot_border=2,dot_border_opacity=1,outline='#75eaff'),
    studio('amber-ring','Amber Ring',width=0,length=0,dot=12,dot_opacity=0,dot_border=1,dot_border_opacity=1,outline='#ffd577'),
    studio('small-ring','Small Ring',width=0,length=0,dot=5,dot_opacity=0,dot_border=1,dot_border_opacity=1,outline='#ffffff'),
    studio('bold-ring','Bold Ring',width=0,length=0,dot=8,dot_opacity=0,dot_border=3,dot_border_opacity=1,outline='#b4ff73'),
    studio('rose-ring','Rose Ring',width=0,length=0,dot=9,dot_opacity=0,dot_border=1,dot_border_opacity=1,outline='#ffa1cc'),
    studio('ghost-ring','Ghost Ring',width=0,length=0,dot=14,dot_opacity=0,dot_border=1,dot_border_opacity=.65,outline='#ffffff'),
    studio('anchor','Anchor',length=5,gap=-4,dot=2,dot_opacity=1,dot_border=1,dot_border_opacity=.9,color='#a4ff8c'),
    studio('ice-focus','Ice Focus',width=1,length=8,gap=-3,dot=3,dot_opacity=1,dot_border=1,dot_border_opacity=1,color='#77eaff'),
    studio('center-lock','Center Lock',width=3,length=4,gap=-5,dot=4,dot_opacity=1,dot_border=1,dot_border_opacity=1,color='#ffffff'),
    studio('gold-focus','Gold Focus',length=7,gap=-2,dot=2,dot_opacity=1,dot_border=0,color='#ffe28d'),
)

def shape(design):
    if design.width and design.length and design.opacity:return 'Hybrid' if design.dot and design.dot_opacity else 'Cross'
    return 'Ring' if design.dot and not design.dot_opacity and design.dot_border and design.dot_border_opacity else 'Dot'

def entries(profiles=None):
    return list(PLAYERS)+[
        CatalogEntry('builtin:'+name,BASE_NAMES[name],model,'builtin',detail='Original Toolbox preset. Customize every setting.')
        for name,model in PRESETS.items()
    ]+list(STUDIO)+[
        CatalogEntry('saved:'+name,name,model,'saved',detail='Saved on your device.')
        for name,model in sorted((profiles or {}).items())
    ]
