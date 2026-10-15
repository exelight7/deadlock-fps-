"""Event-driven native Qt crosshair designer; no render loop, web view or game overlay."""
from pathlib import Path
from dataclasses import replace
import json,difflib,html
from PySide6.QtCore import Qt,QRect,QRectF,QSize,QStandardPaths
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen,QPixmap,QLinearGradient,QImageReader,QIcon,QFont,QRadialGradient
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFrame,QLabel,QPushButton,QComboBox,QScrollArea,QSplitter,QSlider,QDoubleSpinBox,QCheckBox,QColorDialog,QInputDialog,QFileDialog,QMessageBox,QDialog,QPlainTextEdit,QDialogButtonBox,QApplication,QMenu,QLineEdit,QListWidget,QListWidgetItem,QListView,QAbstractItemView,QStyledItemDelegate,QStyle,QTabWidget,QAbstractSpinBox)
from .crosshair import Crosshair,CrosshairStore,PRESETS,NUMBERS,PIXELS,export_design,import_design,share_code,read_code
from .core import atomic,ensure_closed
from .crosshair_catalog import entries,shape
from .crosshair_style import STYLE as CROSSHAIR_STYLE
from . import kv

LABELS={'width':'Width','length':'Length','gap':'Gap offset','opacity':'Opacity',
 'border':'Thickness','border_gap':'Spacing','border_opacity':'Opacity',
 'dot':'Size','dot_opacity':'Opacity','dot_border':'Thickness',
 'dot_border_gap':'Spacing','dot_border_opacity':'Opacity'}
PALETTE=('#ffffff','#aaff78','#73e8ff','#ffe083','#ffa0c9','#bb9bff','#ff926c','#ff6565')

def friendly_error(error):
    text=str(error)
    if any('\u0600'<=c<='\u06ff' for c in text):
        if 'أغلق' in text:return 'Close Deadlock before applying or restoring your crosshair.'
        if 'KV3' in text:return 'The hero settings file is not supported or is damaged. Re-save your crosshair inside Deadlock, close the game, and try again.'
        return 'Check the Deadlock folder and Steam account in Overview, then read the game settings again.'
    return text

def note(text,name='subtitle'):
    label=QLabel(text);label.setWordWrap(True);label.setObjectName(name);return label

def panel(title):
    frame=QFrame();frame.setObjectName('card');layout=QVBoxLayout(frame);layout.setContentsMargins(16,12,16,12);layout.setSpacing(8)
    layout.addWidget(note(title,'cardtitle'));return frame,layout

class CrosshairPreview(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setMinimumSize(120,85);self.design=PRESETS['صليب صغير'];self.zoom=1;self.spread=8.;self.resolution_height=1080;self.mode='dark';self.image=QPixmap();self.background=QPixmap();self.paint_count=0
        self.setAttribute(Qt.WA_OpaquePaintEvent);self.set_design(self.design)
    def set_design(self,design):
        self.design=design;self.shapes=[];d=design.normalized()
        # The setting is an offset from the native base gap, not the inner edge.
        # Base 8 + optional weapon spread matches the modern editor's observable
        # geometry and the user's -8.6 / length 16 reference (inner gap ~7.4).
        # Spread is a manual preview assumption, never written to game settings.
        self.inner_gap=8+d.gap+(0 if d.static else self.spread)
        if d.width>0 and d.length>0:
            gap=self.inner_gap
            rects=[QRectF(-d.width/2,-gap-d.length,d.width,d.length),QRectF(-d.width/2,gap,d.width,d.length),QRectF(-gap-d.length,-d.width/2,d.length,d.width),QRectF(gap,-d.width/2,d.length,d.width)]
            for rect in rects:
                outline=QPainterPath();outline.setFillRule(Qt.OddEvenFill)
                if d.border>0:
                    expansion=d.border+d.border_gap;outline.addRect(rect.adjusted(-expansion,-expansion,expansion,expansion));outline.addRect(rect.adjusted(-d.border_gap,-d.border_gap,d.border_gap,d.border_gap))
                fill=QPainterPath();fill.addRect(rect);self.shapes.append((outline,fill,'line'))
        if d.dot>0:
            outline=QPainterPath();outline.setFillRule(Qt.OddEvenFill);r=d.dot/2
            if d.dot_border>0:
                outer=r+d.dot_border_gap+d.dot_border;inner=r+d.dot_border_gap
                outline.addEllipse(QRectF(-outer,-outer,2*outer,2*outer));outline.addEllipse(QRectF(-inner,-inner,2*inner,2*inner))
            fill=QPainterPath();fill.addEllipse(QRectF(-r,-r,2*r,2*r));self.shapes.append((outline,fill,'dot'))
        self.update()
    def set_zoom(self,zoom):self.zoom=zoom;self.update()
    def set_spread(self,value):self.spread=float(value);self.set_design(self.design)
    def set_resolution_height(self,value):self.resolution_height=int(value);self.update()
    def set_background(self,mode,image=None):
        self.mode=mode
        if image is not None:self.image=image
        self.background=QPixmap();self.update()
    def resizeEvent(self,event):self.background=QPixmap();super().resizeEvent(event)
    def make_background(self):
        self.background=QPixmap(self.size());p=QPainter(self.background)
        if self.mode=='image' and not self.image.isNull():
            scaled=self.image.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation);p.drawPixmap((self.width()-scaled.width())//2,(self.height()-scaled.height())//2,scaled)
        else:
            gradient=QRadialGradient(self.width()/2,self.height()*.48,max(self.width(),self.height())*.8)
            gradient.setColorAt(0,QColor('#d9d6c8' if self.mode=='light' else '#223d39'));gradient.setColorAt(1,QColor('#aea99b' if self.mode=='light' else '#101a20'));p.fillRect(self.rect(),gradient)
            p.setPen(QPen(QColor('#15000000' if self.mode=='light' else '#0cffffff'),1))
            for x in range(0,self.width(),32):p.drawLine(x,0,x,self.height())
            for y in range(0,self.height(),32):p.drawLine(0,y,self.width(),y)
            p.setPen(QPen(QColor('#557f9387'),1))
            for x,y,dx,dy in [(16,16,1,1),(self.width()-17,16,-1,1),(16,self.height()-17,1,-1),(self.width()-17,self.height()-17,-1,-1)]:p.drawLine(x,y,x+16*dx,y);p.drawLine(x,y,x,y+16*dy)
        p.end()
    def paintEvent(self,event):
        self.paint_count+=1
        if self.background.isNull():self.make_background()
        p=QPainter(self);p.drawPixmap(0,0,self.background);p.translate(self.width()/2,self.height()/2)
        scale=self.zoom*self.resolution_height/1080/self.devicePixelRatioF();p.scale(scale,scale);p.setPen(Qt.NoPen)
        for outline,_,kind in self.shapes:
            p.setRenderHint(QPainter.Antialiasing,kind=='dot')
            opacity=self.design.dot_border_opacity if kind=='dot' else self.design.border_opacity
            if opacity and not outline.isEmpty():color=QColor(self.design.outline);color.setAlphaF(opacity);p.setBrush(color);p.drawPath(outline)
        for _,fill,kind in self.shapes:
            p.setRenderHint(QPainter.Antialiasing,kind=='dot')
            opacity=self.design.dot_opacity if kind=='dot' else self.design.opacity
            if opacity:color=QColor(self.design.color);color.setAlphaF(opacity);p.setBrush(color);p.drawPath(fill)
        p.end()

class GalleryTileDelegate(QStyledItemDelegate):
    def sizeHint(self,option,index):return QSize(198,174)
    def paint(self,painter,option,index):
        painter.save();painter.setRenderHint(QPainter.Antialiasing)
        selected=bool(option.state&QStyle.State_Selected);hovered=bool(option.state&QStyle.State_MouseOver)
        rect=option.rect.adjusted(5,5,-5,-5)
        painter.setPen(QPen(QColor('#e7c18a' if selected else '#6d796e' if hovered else '#344145'),2 if selected else 1))
        painter.setBrush(QColor('#32382e' if selected else '#1c2528'));painter.drawRoundedRect(rect,11,11)
        index.data(Qt.DecorationRole).paint(painter,QRect(rect.center().x()-90,rect.top()+9,180,88))
        name,tag=index.data(Qt.DisplayRole).split('\n',1);font=QFont(option.font);font.setBold(selected);painter.setFont(font);painter.setPen(QColor('#f1ede4'))
        painter.drawText(QRect(rect.left()+10,rect.top()+103,rect.width()-20,27),Qt.AlignCenter,painter.fontMetrics().elidedText(name,Qt.ElideRight,rect.width()-20))
        font.setBold(False)
        if font.pixelSize()>0:font.setPixelSize(max(10,font.pixelSize()-2))
        else:font.setPointSizeF(max(8,font.pointSizeF()-1))
        painter.setFont(font);painter.setPen(QColor('#99aaa2'));painter.drawText(QRect(rect.left()+8,rect.top()+133,rect.width()-16,24),Qt.AlignCenter,tag)
        if selected:
            painter.setBrush(QColor('#e7c18a'));painter.setPen(Qt.NoPen);painter.drawEllipse(QRectF(rect.right()-23,rect.top()+13,12,12))
            painter.setPen(QPen(QColor('#24291f'),1.5));painter.drawLine(rect.right()-20,rect.top()+19,rect.right()-18,rect.top()+21);painter.drawLine(rect.right()-18,rect.top()+21,rect.right()-14,rect.top()+16)
        painter.restore()

class CrosshairGallery(QDialog):
    """Offline gallery, built on demand with cached native previews."""
    def __init__(self,profiles=None,parent=None):
        super().__init__(parent);self.setWindowTitle('PRO Crosshairs');self.setLayoutDirection(Qt.LeftToRight);self.setStyleSheet(CROSSHAIR_STYLE);self.resize(1000,820);self.setMinimumSize(780,650)
        self.catalog=entries(profiles);self.chosen=None;self.apply_requested=False;self.icons={}
        layout=QVBoxLayout(self);layout.setContentsMargins(22,20,22,18);layout.setSpacing(13)
        layout.addWidget(note('THE COLLECTION','workspaceEyebrow'));layout.addWidget(note('PRO Crosshairs','workspaceTitle'))
        layout.addWidget(note('50 crosshairs. Player setups and original Studio picks. Choose your starting point.'))
        row=QHBoxLayout();self.search=QLineEdit();self.search.setClearButtonEnabled(True);self.search.setPlaceholderText('Search a player or crosshair...');row.addWidget(self.search,1)
        self.filter=QComboBox()
        for title,key in [('All designs','all'),('Player setups','players'),('Studio picks','builtin'),('Saved','saved')]:self.filter.addItem(title,key)
        row.addWidget(self.filter);self.shape_filter=QComboBox()
        for title in ['Any shape','Cross','Dot','Ring','Hybrid']:self.shape_filter.addItem(title)
        row.addWidget(self.shape_filter);layout.addLayout(row)
        body=QHBoxLayout();body.setSpacing(14);self.tiles=QListWidget();self.tiles.setViewMode(QListView.IconMode);self.tiles.setResizeMode(QListView.Adjust);self.tiles.setMovement(QListView.Static);self.tiles.setSelectionMode(QAbstractItemView.SingleSelection);self.tiles.setWordWrap(True);self.tiles.setSpacing(4);self.tiles.setIconSize(QSize(180,88));self.tiles.setGridSize(QSize(198,174));self.tiles.setLayoutDirection(Qt.LeftToRight)
        self.tiles.setStyleSheet('QListWidget {background:#131b1e;border:1px solid #303f43;border-radius:13px;padding:7px;}')
        self.tiles.setItemDelegate(GalleryTileDelegate(self.tiles));body.addWidget(self.tiles,1)
        frame,details=panel('SELECTED CROSSHAIR');self.detail_heading=details.itemAt(0).widget();frame.setFixedWidth(250);frame.setMinimumHeight(310);body.addWidget(frame)
        self.name=note('','cardtitle');details.addWidget(self.name)
        self.preview=CrosshairPreview();self.preview.set_zoom(2);self.preview.setFixedHeight(170);details.addWidget(self.preview)
        self.preview_caption=note('2× preview · simulated spread: 8');details.addWidget(self.preview_caption)
        self.motion=note('','previewMode');details.addWidget(self.motion,0,Qt.AlignLeft)
        self.detail=note('');details.addWidget(self.detail);self.source=QLabel();self.source.setWordWrap(True);self.source.setOpenExternalLinks(True);details.addWidget(self.source);details.addStretch()
        layout.addLayout(body,1);self.empty=note('');layout.addWidget(self.empty)
        buttons=QHBoxLayout();cancel=QPushButton('Cancel');cancel.clicked.connect(self.reject);buttons.addWidget(cancel);buttons.addStretch()
        self.edit_button=QPushButton('Use && Edit');self.edit_button.setObjectName('primary');self.edit_button.clicked.connect(lambda:self.finish(False));buttons.addWidget(self.edit_button)
        self.apply_button=QPushButton('Apply to Game');self.apply_button.clicked.connect(lambda:self.finish(True));buttons.addWidget(self.apply_button);layout.addLayout(buttons)
        self.search.textChanged.connect(self.populate);self.filter.currentIndexChanged.connect(self.populate);self.shape_filter.currentIndexChanged.connect(self.populate);self.tiles.currentItemChanged.connect(self.select);self.tiles.itemDoubleClicked.connect(lambda _:self.finish(False));self.populate()
    def thumbnail(self,entry):
        if entry.key not in self.icons:
            widget=CrosshairPreview();widget.resize(180,88);widget.set_design(entry.design);bounds=QRectF()
            for outline,fill,_ in widget.shapes:bounds=bounds.united(outline.boundingRect()).united(fill.boundingRect())
            extent=max(abs(bounds.left()),abs(bounds.right()),abs(bounds.top()),abs(bounds.bottom()),1);widget.set_zoom(min(2,72/(2*extent)))
            pixmap=QPixmap(widget.size());widget.render(pixmap);self.icons[entry.key]=QIcon(pixmap)
        return self.icons[entry.key]
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if not hasattr(self,'preview_caption'):return
        compact=self.height()<740;self.preview.setFixedHeight(110 if compact else 170);self.preview_caption.setVisible(not compact);self.detail_heading.setVisible(not compact);self.fit_preview()
    def fit_preview(self):
        bounds=QRectF()
        for outline,fill,_ in self.preview.shapes:bounds=bounds.united(outline.boundingRect()).united(fill.boundingRect())
        extent=max(abs(bounds.left()),abs(bounds.right()),abs(bounds.top()),abs(bounds.bottom()),1);zoom=min(2,(self.preview.height()-16)/(2*extent))
        self.preview.set_zoom(zoom);self.preview_caption.setText(f'{zoom:g}× preview · simulated spread: 8')
    def populate(self,*_):
        selected=self.chosen.key if self.chosen else None;self.tiles.clear();query=self.search.text().strip().casefold();group=self.filter.currentData();category=self.shape_filter.currentText();count=0;selected_row=0
        for entry in self.catalog:
            if group not in ('all',entry.group) or category not in ('Any shape',shape(entry.design)) or query not in entry.name.casefold():continue
            tag=('PLAYER · '+entry.published) if entry.group=='players' else ('SAVED' if entry.group=='saved' else 'STUDIO · '+shape(entry.design).upper())
            item=QListWidgetItem(self.thumbnail(entry),entry.name+'\n'+tag);item.setTextAlignment(Qt.AlignCenter);item.setData(Qt.UserRole,entry.key);item.setToolTip(entry.detail);self.tiles.addItem(item)
            if entry.key==selected:selected_row=count
            count+=1
        self.empty.setText(f'{count} crosshairs · Select a card to preview. Double-click to edit.' if count else 'No matching crosshairs. Try a different name or filter.')
        if count:self.tiles.setCurrentRow(selected_row)
        else:self.select(None)
    def select(self,item,*_):
        self.chosen=next((e for e in self.catalog if item and e.key==item.data(Qt.UserRole)),None);self.edit_button.setEnabled(self.chosen is not None);self.apply_button.setEnabled(self.chosen is not None)
        if not self.chosen:self.name.setText('No selection');self.detail.clear();self.source.clear();self.motion.clear();self.preview.setVisible(False);return
        entry=self.chosen;self.preview.setVisible(True);self.preview.set_design(entry.design);self.fit_preview();self.name.setText(entry.name)
        self.detail.setText('Only width, length and gap were published. Other values are defaults.' if entry.key in ('dew','crayon') else 'Player-attributed settings published in Deadlock Labs.' if entry.group=='players' else entry.detail);self.detail.setToolTip(entry.detail)
        self.source.setText(f'<a style="color:#dfbd88" href="{html.escape(entry.source,quote=True)}">View source ↗</a><br>{entry.published}' if entry.source else '')
        self.motion.setText(shape(entry.design)+' / '+('Static' if entry.design.static else 'Dynamic'))
    def finish(self,apply_requested):
        if self.chosen:self.apply_requested=apply_requested;self.accept()

class CrosshairPage(QWidget):
    def __init__(self,context,parent=None,library=None):
        super().__init__(parent);self.setLayoutDirection(Qt.LeftToRight);self.setStyleSheet(CROSSHAIR_STYLE)
        self.context=context;self.loading=False;self.loaded=False;self.model=PRESETS['صليب صغير'];self.current_model=None;self.controls={};self.loaded_context=None
        self.library=Path(library) if library else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))/'crosshairs/profiles.json'
        self.profiles={};self.load_profiles();root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(14)
        header=QHBoxLayout();copy=QVBoxLayout();copy.setSpacing(3);copy.addWidget(note('MAKE IT YOURS / 06','workspaceEyebrow'));copy.addWidget(note('Crosshair Designer','workspaceTitle'));header.addLayout(copy,1)
        self.design_name=note('Custom','previewMode');header.addWidget(self.design_name,0,Qt.AlignBottom);root.addLayout(header)
        row=QHBoxLayout();row.setSpacing(9);self.presets=QComboBox();self.presets.setPlaceholderText('Choose a preset');self.presets.setMinimumWidth(150);row.addWidget(self.presets,1);self.rebuild_presets();self.presets.currentIndexChanged.connect(self.choose_preset)
        self.gallery_button=QPushButton('PRO Crosshairs');self.gallery_button.setObjectName('primary');self.gallery_button.clicked.connect(self.open_gallery);row.addWidget(self.gallery_button)
        save=QPushButton('Save');save.clicked.connect(self.save_profile);row.addWidget(save);share=QPushButton('Share');menu=QMenu(share)
        for title,fn in [('Copy Toolbox code',self.copy_code),('Paste Toolbox code',self.paste_code),('Export JSON',self.export_file),('Import JSON',self.import_file),('Delete saved design',self.delete_profile)]:menu.addAction(title,fn)
        share.setMenu(menu);row.addWidget(share);root.addLayout(row)
        self.splitter=QSplitter(Qt.Horizontal);self.splitter.setLayoutDirection(Qt.LeftToRight);self.splitter.setChildrenCollapsible(False);self.splitter.setHandleWidth(12);root.addWidget(self.splitter,1)
        preview_frame,preview_layout=panel('LIVE PREVIEW');self.preview=CrosshairPreview();preview_layout.addWidget(self.preview,1)
        row=QHBoxLayout();self.background=QComboBox();self.background.addItems(['Dark studio','Light studio','Custom image...']);self.background.currentIndexChanged.connect(self.change_background);row.addWidget(self.background,1)
        self.zoom=QComboBox()
        for value in [1,2,4,8]:self.zoom.addItem(f'\u200e{value}×',value)
        self.zoom.setToolTip('1x is the reference size for the selected game height. Higher zoom is for editing only.');self.zoom.currentIndexChanged.connect(self.change_preview_scale);row.addWidget(self.zoom);preview_layout.addLayout(row)
        self.preview_info=note('','previewMode');preview_layout.addWidget(self.preview_info)
        self.fix_static=QPushButton('Make Static');self.fix_static.setObjectName('quiet');self.fix_static.clicked.connect(self.make_static);self.fix_static.setToolTip('Use static lines, disable movement collapse and themed hero reticles. Review before applying.');preview_layout.addWidget(self.fix_static)
        self.calibration_button=QPushButton('Preview Settings');self.calibration_button.setObjectName('quiet');preview_layout.addWidget(self.calibration_button)
        self.calibration=QWidget(self);calibration_layout=QVBoxLayout(self.calibration);calibration_layout.setContentsMargins(0,0,0,0);calibration_layout.setSpacing(8)
        row=QHBoxLayout();row.addWidget(note('Game height'));self.resolution=QComboBox()
        for height in [720,900,1080,1440,2160]:self.resolution.addItem(str(height),height)
        self.resolution.setCurrentIndex(2);self.resolution.setToolTip('Preview scaling only. Your game resolution is never changed.');self.resolution.currentIndexChanged.connect(self.change_preview_scale);row.addWidget(self.resolution);calibration_layout.addLayout(row)
        self.spread_row=QWidget();spread_layout=QHBoxLayout(self.spread_row);spread_layout.setContentsMargins(0,0,0,0);spread_layout.addWidget(note('Spread'));self.spread_slider=QSlider(Qt.Horizontal);self.spread_slider.setRange(0,640);self.spread_slider.setValue(80);spread_layout.addWidget(self.spread_slider,1)
        self.spread_value=QDoubleSpinBox();self.spread_value.setButtonSymbols(QAbstractSpinBox.NoButtons);self.spread_value.setRange(0,64);self.spread_value.setDecimals(1);self.spread_value.setValue(8);self.spread_value.setFixedWidth(56);spread_layout.addWidget(self.spread_value)
        self.spread_slider.valueChanged.connect(lambda v:self.spread_value.setValue(v/10));self.spread_value.valueChanged.connect(lambda v:self.spread_slider.setValue(round(v*10)));self.spread_value.valueChanged.connect(self.change_preview_spread);calibration_layout.addWidget(self.spread_row)
        self.preview_note=note('Preview only. Weapon spread and movement can change the result in game.');calibration_layout.addWidget(self.preview_note);self.calibration.hide();self.calibration_button.clicked.connect(self.toggle_calibration)
        self.preview.setToolTip('Native base gap + your gap offset + simulated weapon spread. Preview does not read live weapon state.');preview_frame.setMinimumWidth(210);self.splitter.addWidget(preview_frame)
        self.tabs=QTabWidget();self.tabs.setDocumentMode(True);self.tabs.tabBar().setExpanding(True);self.tabs.setMinimumWidth(290);self.splitter.addWidget(self.tabs)
        columns=[]
        for name in ['Shape','Outline','Behavior']:
            scroll=QScrollArea();scroll.setWidgetResizable(True);container=QWidget();column=QVBoxLayout(container);column.setContentsMargins(0,0,5,0);column.setSpacing(12);scroll.setWidget(container);self.tabs.addTab(scroll,name);columns.append(column)
        f,c=panel('Color');columns[0].addWidget(f);row=QHBoxLayout();row.addWidget(note('Fill color'));row.addStretch();self.color_button=QPushButton();self.color_button.clicked.connect(lambda:self.choose_color('color'));row.addWidget(self.color_button);c.addLayout(row)
        palette=QHBoxLayout();palette.setSpacing(8)
        for color in PALETTE:
            button=QPushButton();button.setFixedSize(25,25);button.setToolTip(color.upper());button.setStyleSheet(f'background:{color};border:2px solid #3b484a;border-radius:12px;padding:0;');button.clicked.connect(lambda _,v=color:self.pick_palette(v));palette.addWidget(button)
        palette.addStretch();c.addLayout(palette)
        for title,keys in [('Lines',('width','length','gap','opacity')),('Center dot',('dot','dot_opacity'))]:
            f,c=panel(title);columns[0].addWidget(f)
            for key in keys:self.add_control(c,key)
        f,c=panel('Outline color');columns[1].addWidget(f);self.outline_button=QPushButton();self.outline_button.clicked.connect(lambda:self.choose_color('outline'));c.addWidget(self.outline_button,0,Qt.AlignLeft)
        for title,keys in [('Line outline',('border','border_gap','border_opacity')),('Dot outline',('dot_border','dot_border_gap','dot_border_opacity'))]:
            f,c=panel(title);columns[1].addWidget(f)
            for key in keys:self.add_control(c,key)
        f,c=panel('Motion & hero reticles');columns[2].addWidget(f)
        self.static=QCheckBox('Static lines');self.collapse=QCheckBox('Collapse gap while resting');self.themed=QCheckBox('Use themed hero reticles');self.all_heroes=QCheckBox('Apply to all heroes')
        for box in [self.static,self.collapse,self.themed]:box.toggled.connect(self.edited);c.addWidget(box)
        c.addWidget(note('Static lines keep the gap fixed. Dynamic lines respond to your weapon. Themed reticles may replace your custom design.'))
        f,c=panel('Application scope');columns[2].addWidget(f);c.addWidget(self.all_heroes);c.addWidget(note('Update existing hero-specific crosshairs too. Sensitivity, bindings and other settings stay untouched.'))
        for column in columns:column.addStretch()
        self.splitter.setSizes([420,520]);self.actions_panel=QFrame();self.actions_panel.setObjectName('crosshairActions');self.actions_panel.setLayoutDirection(Qt.LeftToRight);self.actions_panel.setStyleSheet(CROSSHAIR_STYLE)
        actions=QVBoxLayout(self.actions_panel);actions.setContentsMargins(16,11,16,11);actions.setSpacing(8);self.status=note('Preview ready. Review and apply when you are finished.');actions.addWidget(self.status)
        row=QHBoxLayout();self.reload_button=QPushButton('Read from Game');self.reload_button.clicked.connect(self.reload_current);row.addWidget(self.reload_button);self.restore_button=QPushButton('Restore Last');self.restore_button.clicked.connect(lambda:self.review(True));row.addWidget(self.restore_button);row.addStretch()
        self.apply_button=QPushButton('Review && Apply');self.apply_button.setObjectName('primary');self.apply_button.clicked.connect(lambda:self.review(False));row.addWidget(self.apply_button);actions.addLayout(row);root.addWidget(self.actions_panel);self.set_model(self.model)
    def showEvent(self,event):
        super().showEvent(event)
        if not self.loaded or self.loaded_context!=self.context():self.reload_current()
    def resizeEvent(self,event):
        desired=Qt.Vertical if self.width()<600 else Qt.Horizontal
        if self.splitter.orientation()!=desired:self.splitter.setOrientation(desired);self.splitter.setSizes([230,max(160,self.height()-230)] if desired==Qt.Vertical else [420,520])
        super().resizeEvent(event)
    def toggle_calibration(self,*_):
        dialog=QDialog(self);dialog.setWindowTitle('Preview Settings');dialog.setLayoutDirection(Qt.LeftToRight);dialog.setStyleSheet(CROSSHAIR_STYLE);dialog.resize(380,260)
        layout=QVBoxLayout(dialog);layout.setContentsMargins(20,20,20,20);layout.addWidget(note('Preview Settings','cardtitle'));layout.addWidget(self.calibration);self.calibration.show()
        close=QPushButton('Done');close.clicked.connect(dialog.accept);layout.addWidget(close,0,Qt.AlignRight);dialog.exec();self.calibration.hide();self.calibration.setParent(self);dialog.deleteLater()
    def add_control(self,layout,key):
        _,lo,hi=NUMBERS[key];percent=key.endswith('opacity');pixel=key in PIXELS;factor=100 if percent else 1 if pixel else 10
        block=QVBoxLayout();block.setSpacing(0);row=QHBoxLayout();title=note(LABELS[key]+(' %' if percent else ''));row.addWidget(title,1)
        spin=QDoubleSpinBox();spin.setButtonSymbols(QAbstractSpinBox.NoButtons);spin.setRange(lo*100 if percent else lo,hi*100 if percent else hi);spin.setDecimals(0 if percent or pixel else 1);spin.setSingleStep(1 if percent or pixel else .1);spin.setFixedWidth(62);row.addWidget(spin);block.addLayout(row)
        slider=QSlider(Qt.Horizontal);slider.setRange(round(lo*factor),round(hi*factor));block.addWidget(slider)
        if key=='gap':
            tooltip='Native offset, not the final inner distance: base gap 8 + offset + weapon spread for dynamic lines.';title.setToolTip(tooltip);spin.setToolTip(tooltip);slider.setToolTip(tooltip)
        slider.valueChanged.connect(lambda v,s=spin,p=percent,f=factor:s.setValue(v if p else v/f));spin.valueChanged.connect(lambda v,s=slider,p=percent,f=factor:s.setValue(round(v if p else v*f)));spin.valueChanged.connect(self.edited);layout.addLayout(block);self.controls[key]=(slider,spin)
    def set_model(self,model,custom=False):
        self.loading=True;model=model.normalized();self.model=model
        for key,(slider,spin) in self.controls.items():spin.setValue(getattr(model,key)*(100 if key.endswith('opacity') else 1))
        for key in ('static','collapse','themed'):getattr(self,key).setChecked(getattr(model,key))
        if custom:self.presets.setCurrentIndex(-1);self.design_name.setText('Custom')
        self.loading=False;self.update_colors();self.preview.set_design(self.model);self.update_preview_info()
    def edited(self,*_):
        if self.loading:return
        data={k:s.value()/(100 if k.endswith('opacity') else 1) for k,(_,s) in self.controls.items()};data.update({k:getattr(self,k).isChecked() for k in ('static','collapse','themed')})
        self.model=replace(self.model,**data).validate();self.presets.blockSignals(True);self.presets.setCurrentIndex(-1);self.presets.blockSignals(False);self.design_name.setText('Custom');self.preview.set_design(self.model);self.update_preview_info();self.status.setText('Preview updated. Review & Apply to save it in Deadlock.')
    def change_preview_scale(self,*_):
        if not hasattr(self,'resolution'):return
        self.preview.set_zoom(self.zoom.currentData());self.preview.set_resolution_height(self.resolution.currentData());self.update_preview_info()
    def change_preview_spread(self,value):self.preview.set_spread(value);self.update_preview_info()
    def update_preview_info(self):
        if not hasattr(self,'fix_static'):return
        self.spread_row.setVisible(not self.model.static);self.fix_static.setVisible(not self.model.static or self.model.themed or self.model.collapse)
        text='Themed hero reticle enabled' if self.model.themed else ('Static' if self.model.static else 'Dynamic / simulated spread')+f'  ·  gap {self.preview.inner_gap:.1f}'
        if self.model.collapse:text+=' / movement collapse enabled'
        self.preview_info.setText(text);self.preview_info.setToolTip(text)
    def make_static(self):
        self.set_model(replace(self.model,static=True,collapse=False,themed=False),True);self.status.setText('Static design ready. Adjust the gap, then Review & Apply.')
    def open_gallery(self):
        gallery=CrosshairGallery(self.profiles,self)
        result=gallery.exec();entry=gallery.chosen;apply_requested=gallery.apply_requested;gallery.deleteLater()
        if result!=QDialog.Accepted or not entry:return
        self.set_model(entry.design,True);self.design_name.setText(entry.name);self.status.setText(entry.name+' loaded. Customize it or apply it to Deadlock.')
        if apply_requested:self.review()
    def update_colors(self):
        for key,button in [('color',self.color_button),('outline',self.outline_button)]:
            color=getattr(self.model,key);pix=QPixmap(18,18);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor('#6f7a75'),1));p.setBrush(QColor(color));p.drawRoundedRect(QRectF(.5,.5,17,17),5,5);p.end();button.setIcon(QIcon(pix));button.setText('\u200e'+color.upper())
    def pick_palette(self,color):self.set_model(replace(self.model,color=color),True);self.status.setText('Color updated in preview. Review & Apply to save.')
    def choose_color(self,key):
        color=QColorDialog.getColor(QColor(getattr(self.model,key)),self,'Choose '+('fill' if key=='color' else 'outline')+' color')
        if color.isValid():self.set_model(replace(self.model,**{key:color.name()}),True);self.status.setText('Color updated in preview. Review & Apply to save.')
    def change_background(self,index):
        if index<2:self.preview.set_background('dark' if index==0 else 'light');return
        path,_=QFileDialog.getOpenFileName(self,'Choose a preview background','','Images (*.png *.jpg *.jpeg *.webp)')
        if not path:self.background.setCurrentIndex(0);return
        reader=QImageReader(path);size=reader.size()
        if size.isValid() and max(size.width(),size.height())>1600:reader.setScaledSize(size.scaled(QSize(1600,1000),Qt.KeepAspectRatio))
        image=reader.read()
        if image.isNull():self.error(ValueError('Could not open this image.'));self.background.setCurrentIndex(0);return
        self.preview.set_background('image',QPixmap.fromImage(image))
    def load_profiles(self):
        try:
            if self.library.exists():
                if self.library.stat().st_size>1024*1024:raise ValueError('The saved design library is too large.')
                data=json.loads(self.library.read_text());self.profiles={k:import_design(v) for k,v in data.items() if isinstance(k,str) and 0<len(k)<=60}
        except Exception:self.profiles={}
    def rebuild_presets(self):
        self.presets.blockSignals(True);self.presets.clear()
        catalog=entries(self.profiles)
        for entry in sorted(catalog,key=lambda e:0 if e.key.startswith('builtin:') else 1 if e.group=='players' else 2 if e.group=='builtin' else 3):
            self.presets.addItem(entry.name+(' / Player' if entry.group=='players' else ' / Saved' if entry.group=='saved' else ''),entry.key)
        self.presets.setCurrentIndex(-1);self.presets.blockSignals(False)
    def choose_preset(self,index):
        if self.loading or index<0:return
        entry=next(e for e in entries(self.profiles) if e.key==self.presets.itemData(index));self.set_model(entry.design);self.design_name.setText(entry.name);self.status.setText(entry.name+' loaded. Customize or apply it to Deadlock.')
    def write_profiles(self):atomic(self.library,json.dumps({k:export_design(v) for k,v in self.profiles.items()},ensure_ascii=False,indent=2).encode())
    def save_profile(self):
        name,ok=QInputDialog.getText(self,'Save Crosshair','Design name:')
        if not ok:return
        name=name.strip()
        if not name or len(name)>60:self.error(ValueError('Use a name between 1 and 60 characters.'));return
        try:
            if name in self.profiles and QMessageBox.question(self,'Replace design','A saved design has this name. Replace it?')!=QMessageBox.Yes:return
            if name not in self.profiles and len(self.profiles)>=100:raise ValueError('You can save up to 100 designs.')
            self.profiles[name]=self.model;self.write_profiles();self.rebuild_presets();self.design_name.setText(name);self.status.setText('Saved on this device: '+name)
        except Exception as e:self.error(e)
    def delete_profile(self):
        if not self.profiles:self.status.setText('No saved designs yet.');return
        name,ok=QInputDialog.getItem(self,'Delete Saved Crosshair','Choose a design:',sorted(self.profiles),editable=False)
        if ok:
            try:self.profiles.pop(name);self.write_profiles();self.rebuild_presets();self.status.setText('Saved design removed: '+name)
            except Exception as e:self.error(e)
    def copy_code(self):QApplication.clipboard().setText(share_code(self.model));self.status.setText('Toolbox code copied. Paste it in Crosshair Designer on another device.')
    def paste_code(self):
        code,ok=QInputDialog.getMultiLineText(self,'Import Toolbox Code','Paste a DLTB1. code:',QApplication.clipboard().text()[:4096])
        if ok:
            try:self.set_model(read_code(code),True);self.status.setText('Imported into preview. Review & Apply to save in game.')
            except Exception as e:self.error(e)
    def export_file(self):
        name,_=QFileDialog.getSaveFileName(self,'Export Crosshair','deadlock-crosshair.json','JSON (*.json)')
        if name:
            try:atomic(Path(name),json.dumps(export_design(self.model),indent=2).encode());self.status.setText('Crosshair exported.')
            except Exception as e:self.error(e)
    def import_file(self):
        name,_=QFileDialog.getOpenFileName(self,'Import Crosshair','','JSON (*.json)')
        if name:
            try:
                path=Path(name)
                if path.stat().st_size>8192:raise ValueError('This design file is too large.')
                self.set_model(import_design(json.loads(path.read_text())),True);self.status.setText('Imported into preview. Review & Apply to save in game.')
            except Exception as e:self.error(e)
    def store(self):
        root,video=self.context();return CrosshairStore(root,video)
    def reload_current(self):
        self.loaded=True;self.loaded_context=self.context()
        try:
            store=self.store();design,paths=store.current();self.current_model=design;self.set_model(design,True);self.design_name.setText('In-game')
            if store.video:
                try:
                    fields=kv.section(store.video.read_text(),['video.cfg']).children;height=int(next(n.value for n in fields if n.key=='setting.defaultresheight'))
                    if 240<=height<=8640:
                        index=self.resolution.findData(height)
                        if index<0:self.resolution.addItem(str(height),height);index=self.resolution.count()-1
                        self.resolution.setCurrentIndex(index)
                except (ValueError,StopIteration,OSError):pass
            self.apply_button.setEnabled(True);self.restore_button.setEnabled(store.can_restore());self.status.setText(f'Loaded from Deadlock / {len(paths)} save locations. Editing only changes the preview.')
        except Exception as e:
            self.apply_button.setEnabled(False);self.restore_button.setEnabled(False);self.status.setText(friendly_error(e)+' You can still design, save and share.')
    def review(self,restoring=False):
        try:
            ensure_closed();store=self.store();plan=store.restore_plan() if restoring else store.plan(self.model,self.all_heroes.isChecked())
            if not plan.changes:self.status.setText(store.apply(plan));self.restore_button.setEnabled(store.can_restore());return
            dialog=QDialog(self);dialog.setWindowTitle('Restore Crosshair' if restoring else 'Apply Crosshair');dialog.setLayoutDirection(Qt.LeftToRight);dialog.setStyleSheet(CROSSHAIR_STYLE);dialog.resize(840,620);layout=QVBoxLayout(dialog)
            layout.addWidget(note(f'{len(plan.changes)} files will change, with a backup. Close Deadlock before applying.','cardtitle'))
            output=QPlainTextEdit();output.setReadOnly(True);output.setPlainText('\n\n'.join(str(c.path)+'\n'+''.join(difflib.unified_diff(c.before.decode('utf-8').splitlines(True),c.after.decode('utf-8').splitlines(True),fromfile='current',tofile='restored' if restoring else 'crosshair')) for c in plan.changes));layout.addWidget(output,1)
            buttons=QDialogButtonBox();buttons.addButton('Restore && Back Up' if restoring else 'Apply && Back Up',QDialogButtonBox.AcceptRole);buttons.addButton('Cancel',QDialogButtonBox.RejectRole);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
            if dialog.exec()!=QDialog.Accepted:return
            if self.context()!=self.loaded_context:raise ValueError('The game folder or account changed. Read the game settings and try again.')
            message=store.apply(plan);self.reload_current();self.status.setText(message)
        except Exception as e:self.error(e)
    def error(self,error):
        message=friendly_error(error);self.status.setText(message);QMessageBox.warning(self,'Crosshair Designer',message)
