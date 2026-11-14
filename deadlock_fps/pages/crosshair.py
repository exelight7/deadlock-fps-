"""Crosshair: design one (a live preview you can edit), keep it, share it, and put it into the game after a review.

The engines are `deadlock_fps.crosshair` (the model, the game files, the codes) and `crosshair_catalog` (the 50 ready designs). This page draws them.
Editing only changes the preview; nothing is written to the game until "Review and apply", which shows the exact lines and saves a backup first.
The preview is event-driven (no timers): it paints again only when something changes.
"""
import difflib
import html
import json
import re
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, QSize, QStandardPaths, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImageReader, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QColorDialog, QDialog, QDoubleSpinBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QListView, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget, QAbstractSpinBox)

from .. import kv
from ..core import atomic, ensure_closed
from ..crosshair import NUMBERS, PIXELS, PRESETS, Crosshair, CrosshairStore, export_design, import_design, read_code, share_code
from ..crosshair_catalog import entries, shape
from ..i18n import tr
from ..shell import theme
from ..shell.components import (ActionBar, Badge, Banner, Button, Card, Dialog, EmptyState, Menu, SearchField, SegmentedControl, Select, Slider, Switch,
                                TextField, confirm, mark, text_label)

LABELS = {'width': tr('Width'), 'length': tr('Length'), 'gap': tr('Gap offset'), 'opacity': tr('Opacity'),
          'border': tr('Thickness'), 'border_gap': tr('Spacing'), 'border_opacity': tr('Opacity'),
          'dot': tr('Size'), 'dot_opacity': tr('Opacity'), 'dot_border': tr('Thickness'),
          'dot_border_gap': tr('Spacing'), 'dot_border_opacity': tr('Opacity')}
PALETTE = ('#ffffff', '#aaff78', '#73e8ff', '#ffe083', '#ffa0c9', '#bb9bff', '#ff926c', '#ff6565')
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
ARABIC = re.compile('[؀-ۿ]')


def friendly_error(error):
    text = str(error)
    if ARABIC.search(text):
        if tr('أغلق') in text:
            return tr('Close Deadlock before applying or restoring your crosshair.')
        if 'KV3' in text:
            return tr('The hero settings file is not supported or is damaged. Re-save your crosshair inside Deadlock, close the game, and try again.')
        return tr('Check the Deadlock folder and Steam account in Overview, then read the game settings again.')
    return text


class CrosshairPreview(QWidget):
    """The picture. Always left to right; 1× is the reference size for the chosen game height."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 85)
        self.setLayoutDirection(Qt.LeftToRight)
        self.design = PRESETS['صليب صغير']
        self.zoom = 1
        self.spread = 8.
        self.resolution_height = 1080
        self.mode = 'dark'
        self.image = QPixmap()
        self.background = QPixmap()
        self.paint_count = 0
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.set_design(self.design)

    def set_design(self, design):
        self.design = design
        self.shapes = []
        d = design.normalized()
        # The setting is an offset from the native base gap, not the inner edge. Base 8 + optional weapon spread matches the modern editor's observable
        # geometry and the user's -8.6 / length 16 reference (inner gap ~7.4). Spread is a manual preview assumption, never written to game settings.
        self.inner_gap = 8 + d.gap + (0 if d.static else self.spread)
        if d.width > 0 and d.length > 0:
            gap = self.inner_gap
            rects = [QRectF(-d.width / 2, -gap - d.length, d.width, d.length), QRectF(-d.width / 2, gap, d.width, d.length),
                     QRectF(-gap - d.length, -d.width / 2, d.length, d.width), QRectF(gap, -d.width / 2, d.length, d.width)]
            for rect in rects:
                outline = QPainterPath()
                outline.setFillRule(Qt.OddEvenFill)
                if d.border > 0:
                    expansion = d.border + d.border_gap
                    outline.addRect(rect.adjusted(-expansion, -expansion, expansion, expansion))
                    outline.addRect(rect.adjusted(-d.border_gap, -d.border_gap, d.border_gap, d.border_gap))
                fill = QPainterPath()
                fill.addRect(rect)
                self.shapes.append((outline, fill, 'line'))
        if d.dot > 0:
            outline = QPainterPath()
            outline.setFillRule(Qt.OddEvenFill)
            r = d.dot / 2
            if d.dot_border > 0:
                outer = r + d.dot_border_gap + d.dot_border
                inner = r + d.dot_border_gap
                outline.addEllipse(QRectF(-outer, -outer, 2 * outer, 2 * outer))
                outline.addEllipse(QRectF(-inner, -inner, 2 * inner, 2 * inner))
            fill = QPainterPath()
            fill.addEllipse(QRectF(-r, -r, 2 * r, 2 * r))
            self.shapes.append((outline, fill, 'dot'))
        self.update()

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.update()

    def set_spread(self, value):
        self.spread = float(value)
        self.set_design(self.design)

    def set_resolution_height(self, value):
        self.resolution_height = int(value)
        self.update()

    def set_background(self, mode, image=None):
        self.mode = mode
        if image is not None:
            self.image = image
        self.background = QPixmap()
        self.update()

    def resizeEvent(self, event):
        self.background = QPixmap()
        super().resizeEvent(event)

    def make_background(self):
        self.background = QPixmap(self.size())
        p = QPainter(self.background)
        if self.mode == 'image' and not self.image.isNull():
            scaled = self.image.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap((self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled)
        else:
            light = self.mode == 'light'
            p.fillRect(self.rect(), QColor('#cdc7b6') if light else theme.color('color.bg.raised'))
            p.setPen(QPen(QColor(0, 0, 0, 22) if light else QColor(255, 255, 255, 10), 1))
            for x in range(self.width() // 2 % 32, self.width(), 32):
                p.drawLine(x, 0, x, self.height())
            for y in range(self.height() // 2 % 32, self.height(), 32):
                p.drawLine(0, y, self.width(), y)
            p.setPen(QPen(QColor('#7d6a43') if light else theme.color('color.border.default'), 1))
            for x, y, dx, dy in [(10, 10, 1, 1), (self.width() - 11, 10, -1, 1), (10, self.height() - 11, 1, -1), (self.width() - 11, self.height() - 11, -1, -1)]:
                p.drawLine(x, y, x + 14 * dx, y)
                p.drawLine(x, y, x, y + 14 * dy)
        p.end()

    def paintEvent(self, event):
        self.paint_count += 1
        if self.background.isNull():
            self.make_background()
        p = QPainter(self)
        p.drawPixmap(0, 0, self.background)
        p.translate(self.width() / 2, self.height() / 2)
        scale = self.zoom * self.resolution_height / 1080 / self.devicePixelRatioF()
        p.scale(scale, scale)
        p.setPen(Qt.NoPen)
        for outline, _, kind in self.shapes:
            p.setRenderHint(QPainter.Antialiasing, kind == 'dot')
            opacity = self.design.dot_border_opacity if kind == 'dot' else self.design.border_opacity
            if opacity and not outline.isEmpty():
                color = QColor(self.design.outline)
                color.setAlphaF(opacity)
                p.setBrush(color)
                p.drawPath(outline)
        for _, fill, kind in self.shapes:
            p.setRenderHint(QPainter.Antialiasing, kind == 'dot')
            opacity = self.design.dot_opacity if kind == 'dot' else self.design.opacity
            if opacity:
                color = QColor(self.design.color)
                color.setAlphaF(opacity)
                p.setBrush(color)
                p.drawPath(fill)
        p.end()


class GalleryTileDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(198, 174)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        rect = option.rect.adjusted(5, 5, -5, -5)
        painter.setPen(QPen(theme.color('color.accent.fill') if selected else theme.color('color.border.default'), 2 if selected else 1))
        painter.setBrush(theme.color('color.accent.tint') if selected else theme.color('color.bg.hover') if hovered else theme.color('color.bg.surface'))
        painter.drawRoundedRect(QRectF(rect), 8, 8)
        index.data(Qt.DecorationRole).paint(painter, QRect(rect.center().x() - 90, rect.top() + 9, 180, 88))
        name, tag = index.data(Qt.DisplayRole).split('\n', 1)
        font = QFont(option.font)
        font.setBold(selected)
        painter.setFont(font)
        painter.setPen(theme.color('color.accent.text') if selected else theme.color('color.text.primary'))
        painter.drawText(QRect(rect.left() + 10, rect.top() + 103, rect.width() - 20, 27), Qt.AlignCenter, painter.fontMetrics().elidedText(name, Qt.ElideRight, rect.width() - 20))
        font.setBold(False)
        if font.pixelSize() > 0:
            font.setPixelSize(max(10, font.pixelSize() - 3))
        else:
            font.setPointSizeF(max(7.5, font.pointSizeF() - 1.5))
        font.setLetterSpacing(QFont.AbsoluteSpacing, 0 if ARABIC.search(tag) else 1.5)
        painter.setFont(font)
        painter.setPen(theme.color('color.text.muted'))
        painter.drawText(QRect(rect.left() + 8, rect.top() + 133, rect.width() - 16, 24), Qt.AlignCenter, tag)
        painter.restore()


class CrosshairGallery(QDialog):
    """Offline gallery of the ready designs, built on demand with cached native previews."""

    def __init__(self, profiles=None, parent=None):
        super().__init__(parent)
        mark(self, 'Dialog', variant='review')
        t = theme.current()
        self.setWindowTitle(tr('PRO Crosshairs'))
        self.resize(1000, 820)
        self.setMinimumSize(780, 650)
        self.catalog = entries(profiles)
        self.chosen = None
        self.apply_requested = False
        self.icons = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(t.px('space.6'), t.px('space.5'), t.px('space.6'), t.px('space.5'))
        layout.setSpacing(t.px('space.3'))
        layout.addWidget(text_label(tr('PRO Crosshairs'), 'DialogTitle'))
        layout.addWidget(text_label(tr('50 crosshairs. Player setups and original Studio picks. Choose your starting point.'), 'CardText'))
        row = QHBoxLayout()
        row.setSpacing(t.px('space.3'))
        self.search_field = SearchField(tr('Search a player or crosshair...'))
        self.search = self.search_field.edit
        row.addWidget(self.search_field, 1)
        self.filter = Select()
        for title, key in [(tr('All designs'), 'all'), (tr('Player setups'), 'players'), (tr('Studio picks'), 'builtin'), (tr('Saved'), 'saved')]:
            self.filter.addItem(title, key)
        self.filter.setMinimumWidth(150)
        row.addWidget(self.filter)
        self.shape_filter = Select()
        for title, shown in [('Any shape', tr('Any shape')), ('Cross', tr('Cross')), ('Dot', tr('Dot')), ('Ring', tr('Ring')), ('Hybrid', tr('Hybrid'))]:
            self.shape_filter.addItem(shown, title)
        self.shape_filter.setMinimumWidth(130)
        row.addWidget(self.shape_filter)
        layout.addLayout(row)
        body = QHBoxLayout()
        body.setSpacing(t.px('space.4'))
        self.tiles = QListWidget()
        self.tiles.setViewMode(QListView.IconMode)
        self.tiles.setResizeMode(QListView.Adjust)
        self.tiles.setMovement(QListView.Static)
        self.tiles.setSelectionMode(QListWidget.SingleSelection)
        self.tiles.setSpacing(2)
        self.tiles.setItemDelegate(GalleryTileDelegate(self.tiles))
        self.tiles.setFrameShape(QFrame.NoFrame)
        body.addWidget(self.tiles, 1)
        self.no_match = EmptyState('search', tr('No matching crosshairs'), tr('Try a different name or filter.'))
        self.no_match.hide()
        body.addWidget(self.no_match, 1)
        details = Card(tr('Selected crosshair'))
        details.setFixedWidth(250)
        self.detail_heading = details.title
        self.name = text_label('', 'RowTitle')
        details.body.addWidget(self.name)
        self.preview = CrosshairPreview()
        self.preview.set_zoom(2)
        self.preview.setFixedHeight(170)
        details.body.addWidget(self.preview)
        self.preview_caption = text_label(tr('2× preview · simulated spread: 8'), 'Muted')
        details.body.addWidget(self.preview_caption)
        self.motion = Badge('', 'neutral')
        details.body.addWidget(self.motion, 0, Qt.AlignLeading)
        self.detail = text_label('', 'CardText')
        details.body.addWidget(self.detail)
        self.source = text_label('', 'Muted', plain=False)
        self.source.setOpenExternalLinks(True)
        details.body.addWidget(self.source)
        details.body.addStretch(1)
        body.addWidget(details)
        layout.addLayout(body, 1)
        self.empty = text_label('', 'Muted')
        layout.addWidget(self.empty)
        buttons = QHBoxLayout()
        cancel = Button(tr('Cancel'), 'secondary')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        self.apply_button = Button(tr('Apply to Game'), 'secondary')
        self.apply_button.clicked.connect(lambda: self.finish(True))
        buttons.addWidget(self.apply_button)
        self.edit_button = Button(tr('Use && Edit'), 'primary')
        self.edit_button.clicked.connect(lambda: self.finish(False))
        buttons.addWidget(self.edit_button)
        layout.addLayout(buttons)
        self.search.textChanged.connect(self.populate)
        self.filter.currentIndexChanged.connect(self.populate)
        self.shape_filter.currentIndexChanged.connect(self.populate)
        self.tiles.currentItemChanged.connect(self.select)
        self.tiles.itemDoubleClicked.connect(lambda _item: self.finish(False))
        self.populate()

    def thumbnail(self, entry):
        if entry.key not in self.icons:
            widget = CrosshairPreview()
            widget.resize(180, 88)
            widget.set_design(entry.design)
            bounds = QRectF()
            for outline, fill, _ in widget.shapes:
                bounds = bounds.united(outline.boundingRect()).united(fill.boundingRect())
            extent = max(abs(bounds.left()), abs(bounds.right()), abs(bounds.top()), abs(bounds.bottom()), 1)
            widget.set_zoom(min(2, 72 / (2 * extent)))
            pixmap = QPixmap(widget.size())
            widget.render(pixmap)
            self.icons[entry.key] = QIcon(pixmap)
        return self.icons[entry.key]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, 'preview_caption'):
            return
        compact = self.height() < 740
        self.preview.setFixedHeight(110 if compact else 170)
        self.preview_caption.setVisible(not compact)
        self.detail_heading.setVisible(not compact)
        self.fit_preview()

    def fit_preview(self):
        bounds = QRectF()
        for outline, fill, _ in self.preview.shapes:
            bounds = bounds.united(outline.boundingRect()).united(fill.boundingRect())
        extent = max(abs(bounds.left()), abs(bounds.right()), abs(bounds.top()), abs(bounds.bottom()), 1)
        zoom = min(2, (self.preview.height() - 16) / (2 * extent))
        self.preview.set_zoom(zoom)
        self.preview_caption.setText(tr('{0:g}× preview · simulated spread: 8').format(zoom))

    def populate(self, *_):
        selected = self.chosen.key if self.chosen else None
        self.tiles.clear()
        query = self.search.text().strip().casefold()
        group = self.filter.currentData()
        category = self.shape_filter.currentData()
        count = 0
        selected_row = 0
        for entry in self.catalog:
            if group not in ('all', entry.group) or category not in ('Any shape', shape(entry.design)) or query not in entry.name.casefold():
                continue
            tag = (tr('PLAYER · ') + entry.published) if entry.group == 'players' else (tr('SAVED') if entry.group == 'saved' else tr('STUDIO · ') + tr(shape(entry.design)).upper())
            item = QListWidgetItem(self.thumbnail(entry), entry.name + '\n' + tag)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, entry.key)
            item.setToolTip(entry.detail)
            self.tiles.addItem(item)
            if entry.key == selected:
                selected_row = count
            count += 1
        self.empty.setText(tr('{0} crosshairs · Select a card to preview. Double-click to edit.').format(count) if count else tr('No matching crosshairs. Try a different name or filter.'))
        self.no_match.setVisible(not count)
        self.tiles.setVisible(bool(count))
        if count:
            self.tiles.setCurrentRow(selected_row)
        else:
            self.select(None)

    def select(self, item, *_):
        self.chosen = next((e for e in self.catalog if item and e.key == item.data(Qt.UserRole)), None)
        self.edit_button.setEnabled(self.chosen is not None)
        self.apply_button.setEnabled(self.chosen is not None)
        if not self.chosen:
            self.name.setText(tr('No selection'))
            self.detail.clear()
            self.source.clear()
            self.motion.setText('')
            self.motion.hide()
            self.preview.setVisible(False)
            return
        entry = self.chosen
        self.preview.setVisible(True)
        self.preview.set_design(entry.design)
        self.fit_preview()
        self.name.setText(entry.name)
        self.detail.setText(tr('Only width, length and gap were published. Other values are defaults.') if entry.key in ('dew', 'crayon')
                            else tr('Player-attributed settings published in Deadlock Labs.') if entry.group == 'players' else entry.detail)
        link = theme.color('color.text.link').name()
        self.source.setText(tr('<a style="color:{2}" href="{0}">View source ↗</a><br>{1}').format(html.escape(entry.source, quote=True), entry.published, link) if entry.source else '')
        self.motion.setText(tr(shape(entry.design)) + ' / ' + (tr('Static') if entry.design.static else tr('Dynamic')))
        self.motion.show()

    def finish(self, apply_requested):
        if self.chosen:
            self.apply_requested = apply_requested
            self.accept()


def swatch_style(color, selected=False):
    return 'QPushButton { background: %s; border: %s; border-radius: 12px; min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; padding: 0; }' % (
        color, '2px solid ' + theme.color('color.border.focus').name() if selected else '1px solid ' + theme.color('color.border.control').name())


class CrosshairPage(QWidget):
    def __init__(self, context, parent=None, library=None):
        super().__init__(parent)
        mark(self, 'CrosshairPage')
        self.context = context
        self.loading = False
        self.loaded = False
        self.model = PRESETS['صليب صغير']
        self.current_model = None
        self.controls = {}
        self.loaded_context = None
        self.library = Path(library) if library else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'crosshairs/profiles.json'
        self.profiles = {}
        self.load_profiles()
        t = theme.current()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(t.px('space.3'))
        self.notice_box = QVBoxLayout()
        root.addLayout(self.notice_box)

        # One row: where to get a design, which one is loaded, how to keep it.
        row = QHBoxLayout()
        row.setSpacing(t.px('space.3'))
        self.gallery_button = Button(tr('PRO Crosshairs'), 'secondary', icon='crosshair')
        self.gallery_button.clicked.connect(self.open_gallery)
        row.addWidget(self.gallery_button)
        self.design_name = Badge(tr('Custom'), 'neutral')
        row.addWidget(self.design_name)
        row.addStretch(1)
        self.save_button = Button(tr('Save'), 'secondary', icon='download')
        self.save_button.clicked.connect(self.save_profile)
        row.addWidget(self.save_button)
        self.share_button = Button(tr('Share'), 'secondary', icon='ext')
        menu = Menu(self.share_button)
        for title, fn in [('Copy Toolbox code', self.copy_code), ('Paste Toolbox code', self.paste_code), ('Export JSON', self.export_file), ('Import JSON', self.import_file)]:
            menu.add(tr(title), fn)
        menu.add(tr('Delete saved design'), self.delete_profile, danger=True)
        self.share_button.setMenu(menu)
        row.addWidget(self.share_button)
        root.addLayout(row)

        columns = QHBoxLayout()
        columns.setSpacing(t.px('space.4'))
        root.addLayout(columns, 1)

        # Live preview and everything that only affects the preview.
        preview_card = Card(tr('Live preview'))
        preview_card.setMinimumWidth(250)
        self.preview = CrosshairPreview()
        self.preview.setToolTip(tr('Native base gap + your gap offset + simulated weapon spread. Preview does not read live weapon state.'))
        preview_card.body.addWidget(self.preview, 1)
        row = QHBoxLayout()
        row.setSpacing(t.px('space.2'))
        self.background = Select()
        self.background.addItems([tr('Dark studio'), tr('Light studio'), tr('Custom image...')])
        self.background.currentIndexChanged.connect(self.change_background)
        row.addWidget(self.background, 1)
        self.zoom = SegmentedControl([('1', '1×'), ('2', '2×'), ('4', '4×')])
        self.zoom.setToolTip(tr('1x is the reference size for the selected game height. Higher zoom is for editing only.'))
        self.zoom.changed.connect(self.change_preview_scale)
        row.addWidget(self.zoom)
        preview_card.body.addLayout(row)
        self.preview_info = text_label('', 'Muted')
        preview_card.body.addWidget(self.preview_info)
        row = QHBoxLayout()
        row.setSpacing(t.px('space.2'))
        self.fix_static = Button(tr('Make Static'), 'ghost', 'sm')
        self.fix_static.setToolTip(tr('Use static lines, disable movement collapse and themed hero reticles. Review before applying.'))
        self.fix_static.clicked.connect(self.make_static)
        row.addWidget(self.fix_static)
        self.calibration_button = Button(tr('Preview Settings'), 'ghost', 'sm')
        self.calibration_button.clicked.connect(self.toggle_calibration)
        row.addWidget(self.calibration_button)
        row.addStretch(1)
        preview_card.body.addLayout(row)
        self.calibration = QWidget(self)
        cal = QVBoxLayout(self.calibration)
        cal.setContentsMargins(0, 0, 0, 0)
        cal.setSpacing(t.px('space.3'))
        row = QHBoxLayout()
        row.addWidget(text_label(tr('Game height'), 'CardText'), 1)
        self.resolution = Select()
        for height in [720, 900, 1080, 1440, 2160]:
            self.resolution.addItem(str(height), height)
        self.resolution.setCurrentIndex(2)
        self.resolution.setToolTip(tr('Preview scaling only. Your game resolution is never changed.'))
        self.resolution.currentIndexChanged.connect(self.change_preview_scale)
        row.addWidget(self.resolution)
        cal.addLayout(row)
        self.spread_row = QWidget()
        sl = QHBoxLayout(self.spread_row)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(text_label(tr('Spread'), 'CardText'))
        self.spread_slider = Slider(0, 640, 80)
        self.spread_slider.setLayoutDirection(Qt.LeftToRight)
        sl.addWidget(self.spread_slider, 1)
        self.spread_value = self.number_field(0, 64, 1, 1)
        self.spread_value.setValue(8)
        sl.addWidget(self.spread_value)
        self.spread_slider.valueChanged.connect(lambda v: self.spread_value.setValue(v / 10))
        self.spread_value.valueChanged.connect(lambda v: self.spread_slider.setValue(round(v * 10)))
        self.spread_value.valueChanged.connect(self.change_preview_spread)
        cal.addWidget(self.spread_row)
        cal.addWidget(text_label(tr('Preview only. Weapon spread and movement can change the result in game.'), 'Muted'))
        self.calibration.hide()
        columns.addWidget(preview_card, 2)

        # The design itself, in three sections.
        design_card = Card()
        design_card.setMinimumWidth(320)
        self.tabs = SegmentedControl([('shape', tr('Shape')), ('outline', tr('Outline')), ('behavior', tr('Behavior'))])
        design_card.body.addWidget(self.tabs)
        self.pages = QStackedWidget()
        self.sections = []
        panes = []
        for _name in ('shape', 'outline', 'behavior'):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            container = QWidget()
            column = QVBoxLayout(container)
            column.setContentsMargins(0, 0, 10, 0)
            column.setSpacing(t.px('space.4'))
            scroll.setWidget(container)
            self.pages.addWidget(scroll)
            panes.append(column)
        self.tabs.changed.connect(lambda key: self.pages.setCurrentIndex(('shape', 'outline', 'behavior').index(key)))
        design_card.body.addWidget(self.pages, 1)
        columns.addWidget(design_card, 3)
        # shape
        column = panes[0]
        column.addWidget(text_label(tr('Color'), 'RowTitle'))
        self.color_field = self.color_row(column, 'color', tr('Fill color'))
        palette = QHBoxLayout()
        palette.setSpacing(6)
        self.swatches = []
        for color in PALETTE:
            button = mark(QPushButton(), 'Swatch')
            button.setFixedSize(24, 24)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(color.upper())
            button.setAccessibleName(color.upper())
            button.setStyleSheet(swatch_style(color))
            button.clicked.connect(lambda _=False, v=color: self.pick_palette(v))
            palette.addWidget(button)
            self.swatches.append(button)
        palette.addStretch(1)
        column.addLayout(palette)
        for title, keys in [(tr('Lines'), ('width', 'length', 'gap', 'opacity')), (tr('Center dot'), ('dot', 'dot_opacity'))]:
            column.addWidget(text_label(title, 'RowTitle'))
            for key in keys:
                self.add_control(column, key)
        column.addStretch(1)
        # outline
        column = panes[1]
        column.addWidget(text_label(tr('Outline color'), 'RowTitle'))
        self.outline_field = self.color_row(column, 'outline', tr('Outline color'))
        for title, keys in [(tr('Line outline'), ('border', 'border_gap', 'border_opacity')), (tr('Dot outline'), ('dot_border', 'dot_border_gap', 'dot_border_opacity'))]:
            column.addWidget(text_label(title, 'RowTitle'))
            for key in keys:
                self.add_control(column, key)
        column.addStretch(1)
        # behaviour
        column = panes[2]
        column.addWidget(text_label(tr('Motion & hero reticles'), 'RowTitle'))
        self.static = Switch(tr('Static lines'))
        self.collapse = Switch(tr('Collapse gap while resting'))
        self.themed = Switch(tr('Use themed hero reticles'))
        self.all_heroes = Switch(tr('Apply to all heroes'))
        for box in (self.static, self.collapse, self.themed):
            box.toggled.connect(self.edited)
            column.addWidget(box)
        column.addWidget(text_label(tr('Static lines keep the gap fixed. Dynamic lines respond to your weapon. Themed reticles may replace your custom design.'), 'Muted'))
        column.addWidget(text_label(tr('Application scope'), 'RowTitle'))
        column.addWidget(self.all_heroes)
        column.addWidget(text_label(tr('Update existing hero-specific crosshairs too. Sensitivity, bindings and other settings stay untouched.'), 'Muted'))
        column.addStretch(1)

        # Read, restore, apply.
        self.actions_panel = ActionBar()
        self.status = self.actions_panel.summary
        self.status.setText(tr('Preview ready. Review and apply when you are finished.'))
        self.reload_button = Button(tr('Read from Game'), 'secondary', icon='refresh')
        self.reload_button.clicked.connect(self.reload_current)
        self.restore_button = Button(tr('Restore Last'), 'ghost', icon='history')
        self.restore_button.clicked.connect(lambda: self.review(True))
        self.apply_button = Button(tr('Review && Apply'), 'primary', icon='check')
        self.apply_button.clicked.connect(lambda: self.review(False))
        for button in (self.reload_button, self.restore_button, self.apply_button):
            self.actions_panel.add(button)
        root.addWidget(self.actions_panel)
        self.zoom.set_value('2')
        self.preview.set_zoom(2)
        self.set_model(self.model)

    # ---- small parts ---------------------------------------------------------------------

    @staticmethod
    def number_field(lo, hi, decimals, step):
        spin = QDoubleSpinBox()
        spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        spin.setRange(lo, hi)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setFixedWidth(64)
        spin.setLayoutDirection(Qt.LeftToRight)
        spin.setAlignment(Qt.AlignRight)
        return spin

    def color_row(self, layout, key, title):
        """A colour: a button that shows it and opens the colour dialog, and a code field (#RRGGBB) that applies when you leave it."""
        row = QHBoxLayout()
        row.setSpacing(theme.current().px('space.3'))
        row.addWidget(text_label(title, 'CardText'), 1)
        button = Button('', 'secondary', 'sm')
        button.clicked.connect(lambda: self.choose_color(key))
        field = TextField(placeholder='#ffffff')
        field.edit.setMaxLength(7)
        field.edit.setFixedWidth(92)
        field.edit.setLayoutDirection(Qt.LeftToRight)
        field.edit.editingFinished.connect(lambda: self.type_color(key))
        row.addWidget(button)
        row.addWidget(field)
        layout.addLayout(row)
        setattr(self, 'color_button' if key == 'color' else 'outline_button', button)
        return field

    def add_control(self, layout, key):
        _, lo, hi = NUMBERS[key]
        percent = key.endswith('opacity')
        pixel = key in PIXELS
        factor = 100 if percent else 1 if pixel else 10
        row = QHBoxLayout()
        row.setSpacing(theme.current().px('space.3'))
        title = text_label(LABELS[key] + (' %' if percent else ''), 'CardText')
        row.addWidget(title, 1)
        spin = self.number_field(lo * 100 if percent else lo, hi * 100 if percent else hi, 0 if percent or pixel else 1, 1 if percent or pixel else .1)
        row.addWidget(spin)
        layout.addLayout(row)
        slider = Slider(round(lo * factor), round(hi * factor), round(lo * factor))
        slider.setLayoutDirection(Qt.LeftToRight)
        slider.setAccessibleName(LABELS[key])
        layout.addWidget(slider)
        if key == 'gap':
            tooltip = tr('Native offset, not the final inner distance: base gap 8 + offset + weapon spread for dynamic lines.')
            for widget in (title, spin, slider):
                widget.setToolTip(tooltip)
        slider.valueChanged.connect(lambda v, s=spin, p=percent, f=factor: s.setValue(v if p else v / f))
        spin.valueChanged.connect(lambda v, s=slider, p=percent, f=factor: s.setValue(round(v if p else v * f)))
        spin.valueChanged.connect(self.edited)
        self.controls[key] = (slider, spin)

    def say(self, title, text='', variant='info'):
        """One notice above the page (an empty title clears it)."""
        while self.notice_box.count():
            old = self.notice_box.takeAt(0).widget()
            if old is not None:
                old.hide()
                old.setParent(None)
                old.deleteLater()
        if title:
            self.notice = Banner(title, text, variant)
            self.notice_box.addWidget(self.notice)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.loaded or self.loaded_context != self.context():
            self.reload_current()

    def toggle_calibration(self, *_):
        dialog = Dialog(tr('Preview Settings'), '', 'review', tr('Done'), tr('Cancel'), False, self)
        dialog.cancel_button.hide()
        dialog.body.addWidget(self.calibration)
        self.calibration.show()
        dialog.exec()
        self.calibration.hide()
        self.calibration.setParent(self)
        dialog.deleteLater()

    # ---- the model -----------------------------------------------------------------------

    def set_model(self, model, custom=False):
        self.loading = True
        model = model.normalized()
        self.model = model
        for key, (slider, spin) in self.controls.items():
            spin.setValue(getattr(model, key) * (100 if key.endswith('opacity') else 1))
        for key in ('static', 'collapse', 'themed'):
            getattr(self, key).setChecked(getattr(model, key))
        if custom:
            self.design_name.setText(tr('Custom'))
        self.loading = False
        self.update_colors()
        self.preview.set_design(self.model)
        self.update_preview_info()

    def edited(self, *_):
        if self.loading:
            return
        data = {k: s.value() / (100 if k.endswith('opacity') else 1) for k, (_, s) in self.controls.items()}
        data.update({k: getattr(self, k).isChecked() for k in ('static', 'collapse', 'themed')})
        self.model = replace(self.model, **data).validate()
        self.design_name.setText(tr('Custom'))
        self.preview.set_design(self.model)
        self.update_preview_info()
        self.status.setText(tr('Preview updated. Review & Apply to save it in Deadlock.'))

    def change_preview_scale(self, *_):
        if not hasattr(self, 'resolution'):
            return
        self.preview.set_zoom(int(self.zoom.value()))
        self.preview.set_resolution_height(self.resolution.currentData())
        self.update_preview_info()

    def change_preview_spread(self, value):
        self.preview.set_spread(value)
        self.update_preview_info()

    def update_preview_info(self):
        if not hasattr(self, 'fix_static'):
            return
        self.spread_row.setVisible(not self.model.static)
        self.fix_static.setVisible(not self.model.static or self.model.themed or self.model.collapse)
        text = tr('Themed hero reticle enabled') if self.model.themed else (tr('Static') if self.model.static else tr('Dynamic / simulated spread')) + tr('  ·  gap {0:.1f}').format(self.preview.inner_gap)
        if self.model.collapse:
            text += tr(' / movement collapse enabled')
        self.preview_info.setText(text)
        self.preview_info.setToolTip(text)

    def make_static(self):
        self.set_model(replace(self.model, static=True, collapse=False, themed=False), True)
        self.status.setText(tr('Static design ready. Adjust the gap, then Review & Apply.'))

    def open_gallery(self):
        gallery = CrosshairGallery(self.profiles, self)
        result = gallery.exec()
        entry = gallery.chosen
        apply_requested = gallery.apply_requested
        gallery.deleteLater()
        if result != QDialog.Accepted or not entry:
            return
        self.set_model(entry.design, True)
        self.design_name.setText(entry.name)
        self.status.setText(entry.name + tr(' loaded. Customize it or apply it to Deadlock.'))
        if apply_requested:
            self.review()

    # ---- colours -------------------------------------------------------------------------

    def update_colors(self):
        for key, button, field in (('color', self.color_button, self.color_field), ('outline', self.outline_button, self.outline_field)):
            color = getattr(self.model, key)
            pix = QPixmap(18, 18)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(theme.color('color.border.control'), 1))
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(.5, .5, 17, 17), 3, 3)
            p.end()
            button.setIcon(QIcon(pix))
            button.setText('')
            button.setAccessibleName(tr('Choose ') + key)
            field.setText(color.lower())
            field.set_error('')
        for swatch, color in zip(self.swatches, PALETTE):
            swatch.setStyleSheet(swatch_style(color, color.lower() == self.model.color.lower()))

    def type_color(self, key):
        field = self.color_field if key == 'color' else self.outline_field
        text = field.text().strip()
        if not text.startswith('#'):
            text = '#' + text
        if text.lower() == getattr(self.model, key).lower():
            return
        if not HEX.match(text):
            field.set_error(tr('Use a colour like #73e8ff.'))
            return
        self.set_model(replace(self.model, **{key: text.lower()}), True)
        self.status.setText(tr('Color updated in preview. Review & Apply to save.'))

    def pick_palette(self, color):
        self.set_model(replace(self.model, color=color), True)
        self.status.setText(tr('Color updated in preview. Review & Apply to save.'))

    def choose_color(self, key):
        color = QColorDialog.getColor(QColor(getattr(self.model, key)), self, tr('Choose ') + ('fill' if key == 'color' else 'outline') + ' color')
        if color.isValid():
            self.set_model(replace(self.model, **{key: color.name()}), True)
            self.status.setText(tr('Color updated in preview. Review & Apply to save.'))

    def change_background(self, index):
        if index < 2:
            self.preview.set_background('dark' if index == 0 else 'light')
            return
        path, _ = QFileDialog.getOpenFileName(self, tr('Choose a preview background'), '', 'Images (*.png *.jpg *.jpeg *.webp)')
        if not path:
            self.background.setCurrentIndex(0)
            return
        reader = QImageReader(path)
        size = reader.size()
        if size.isValid() and max(size.width(), size.height()) > 1600:
            reader.setScaledSize(size.scaled(QSize(1600, 1000), Qt.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            self.error(ValueError(tr('Could not open this image.')))
            self.background.setCurrentIndex(0)
            return
        self.preview.set_background('image', QPixmap.fromImage(image))

    # ---- saved designs, codes, files -----------------------------------------------------

    def load_profiles(self):
        try:
            if self.library.exists():
                if self.library.stat().st_size > 1024 * 1024:
                    raise ValueError(tr('The saved design library is too large.'))
                data = json.loads(self.library.read_text(encoding='utf-8'))
                self.profiles = {k: import_design(v) for k, v in data.items() if isinstance(k, str) and 0 < len(k) <= 60}
        except Exception:
            self.profiles = {}

    def write_profiles(self):
        atomic(self.library, json.dumps({k: export_design(v) for k, v in self.profiles.items()}, ensure_ascii=False, indent=2).encode())

    def save_profile(self):
        name, ok = QInputDialog.getText(self, tr('Save Crosshair'), tr('Design name:'))
        if not ok:
            return
        name = name.strip()
        if not name or len(name) > 60:
            self.error(ValueError(tr('Use a name between 1 and 60 characters.')))
            return
        try:
            if name in self.profiles and not confirm(self, tr('Replace design'), tr('A saved design has this name. Replace it?'), tr('Replace')):
                return
            if name not in self.profiles and len(self.profiles) >= 100:
                raise ValueError(tr('You can save up to 100 designs.'))
            self.profiles[name] = self.model
            self.write_profiles()
            self.design_name.setText(name)
            self.status.setText(tr('Saved on this device: ') + name)
        except Exception as error:
            self.error(error)

    def delete_profile(self):
        if not self.profiles:
            self.status.setText(tr('No saved designs yet.'))
            return
        name, ok = QInputDialog.getItem(self, tr('Delete Saved Crosshair'), tr('Choose a design:'), sorted(self.profiles), editable=False)
        if ok:
            try:
                self.profiles.pop(name)
                self.write_profiles()
                self.status.setText(tr('Saved design removed: ') + name)
            except Exception as error:
                self.error(error)

    def copy_code(self):
        QApplication.clipboard().setText(share_code(self.model))
        self.status.setText(tr('Toolbox code copied. Paste it in Crosshair Designer on another device.'))

    def paste_code(self):
        code, ok = QInputDialog.getMultiLineText(self, tr('Import Toolbox Code'), tr('Paste a DLTB1. code:'), QApplication.clipboard().text()[:4096])
        if ok:
            try:
                self.set_model(read_code(code), True)
                self.status.setText(tr('Imported into preview. Review & Apply to save in game.'))
            except Exception as error:
                self.error(error)

    def export_file(self):
        name, _ = QFileDialog.getSaveFileName(self, tr('Export Crosshair'), 'deadlock-crosshair.json', 'JSON (*.json)')
        if name:
            try:
                atomic(Path(name), json.dumps(export_design(self.model), indent=2).encode())
                self.status.setText(tr('Crosshair exported.'))
            except Exception as error:
                self.error(error)

    def import_file(self):
        name, _ = QFileDialog.getOpenFileName(self, tr('Import Crosshair'), '', 'JSON (*.json)')
        if name:
            try:
                path = Path(name)
                if path.stat().st_size > 8192:
                    raise ValueError(tr('This design file is too large.'))
                self.set_model(import_design(json.loads(path.read_text(encoding='utf-8-sig'))), True)
                self.status.setText(tr('Imported into preview. Review & Apply to save in game.'))
            except Exception as error:
                self.error(error)

    # ---- the game ------------------------------------------------------------------------

    def store(self):
        root, video = self.context()
        return CrosshairStore(root, video)

    def reload_current(self):
        self.loaded = True
        self.loaded_context = self.context()
        self.say('')
        try:
            store = self.store()
            design, paths = store.current()
            self.current_model = design
            self.set_model(design, True)
            self.design_name.setText(tr('In-game'))
            if store.video:
                try:
                    fields = kv.section(store.video.read_text(encoding='utf-8'), ['video.cfg']).children
                    height = int(next(n.value for n in fields if n.key == 'setting.defaultresheight'))
                    if 240 <= height <= 8640:
                        index = self.resolution.findData(height)
                        if index < 0:
                            self.resolution.addItem(str(height), height)
                            index = self.resolution.count() - 1
                        self.resolution.setCurrentIndex(index)
                except (ValueError, StopIteration, OSError):
                    pass
            self.apply_button.setEnabled(True)
            self.restore_button.setEnabled(store.can_restore())
            self.status.setText(tr('Loaded from Deadlock / {0} save locations. Editing only changes the preview.').format(len(paths)))
        except Exception as error:
            self.apply_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            message = friendly_error(error)
            self.status.setText(tr(' You can still design, save and share.').strip())
            self.say(tr('No crosshair was read from the game yet'), message + tr(' You can still design, save and share.'), 'warning')

    def review(self, restoring=False):
        self.say('')
        try:
            ensure_closed()
            store = self.store()
            plan = store.restore_plan() if restoring else store.plan(self.model, self.all_heroes.isChecked())
            if not plan.changes:
                self.status.setText(store.apply(plan))
                self.restore_button.setEnabled(store.can_restore())
                return
            dialog = Dialog(tr('Restore Crosshair') if restoring else tr('Apply Crosshair'), tr('{0} files will change, with a backup. Close Deadlock before applying.').format(len(plan.changes)),
                            'review', tr('Restore && Back Up') if restoring else tr('Apply && Back Up'), tr('Cancel'), False, self)
            dialog.setMinimumWidth(theme.current().px('size.dialog.md') + 200)
            output = QPlainTextEdit()
            output.setReadOnly(True)
            output.setLayoutDirection(Qt.LeftToRight)
            output.setMinimumHeight(320)
            output.setPlainText('\n\n'.join(str(c.path) + '\n' + ''.join(difflib.unified_diff(c.before.decode('utf-8').splitlines(True), c.after.decode('utf-8').splitlines(True),
                                                                                           fromfile='current', tofile='restored' if restoring else 'crosshair')) for c in plan.changes))
            dialog.body.addWidget(output)
            if dialog.exec() != QDialog.Accepted:
                return
            if self.context() != self.loaded_context:
                raise ValueError(tr('The game folder or account changed. Read the game settings and try again.'))
            message = store.apply(plan)
            self.reload_current()
            self.status.setText(message)
        except Exception as error:
            self.error(error)

    def error(self, error):
        message = friendly_error(error)
        self.status.setText(message)
        self.say(tr('Nothing was changed'), message, 'danger')
