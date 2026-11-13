"""Row painting for the server table: every cell is drawn here, so the look does not depend on the platform style."""
from .i18n import tr
from PySide6.QtCore import Qt, QRect, QRectF, QEvent
from PySide6.QtGui import QColor, QPen, QPainter, QPainterPath, QFont, QFontMetrics, QIcon
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle, QTableWidgetItem
from . import theme as T

SELECTED_BACKGROUND = T.BRASS_SHADE
CHECK_FILL = T.BRASS_BRIGHT


def row_is_checked(index):
    # Qt item APIs return int, while a Python setData call may retain the enum.
    value = index.siblingAtColumn(0).data(Qt.CheckStateRole)
    return value == Qt.Checked or value == Qt.Checked.value


def cell_font(size=12, bold=False):
    font = QFont()
    font.setFamilies(list(T.BODY))
    font.setPixelSize(size)
    font.setWeight(QFont.DemiBold if bold else QFont.Normal)
    return font


class ServerRowDelegate(QStyledItemDelegate):
    def row_option(self, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        return opt

    def draw_cell(self, painter, opt, index):
        """Background and row rules. Selected rows take the brass shade edge to edge."""
        checked = row_is_checked(index)
        painter.save()
        if checked:
            fill = SELECTED_BACKGROUND
        else:
            fill = T.SUNKEN if opt.features & QStyleOptionViewItem.Alternate else T.SURFACE
        painter.fillRect(opt.rect, QColor(fill))
        painter.setPen(QColor(T.BRASS_DEEP if checked else T.LINE))
        painter.drawLine(opt.rect.bottomLeft(), opt.rect.bottomRight())
        if checked:
            painter.drawLine(opt.rect.topLeft(), opt.rect.topRight())
        painter.restore()

    def paint(self, painter, option, index):
        opt = self.row_option(option, index)
        self.draw_cell(painter, opt, index)
        text = str(index.data(Qt.DisplayRole) or '')
        if not text:
            return
        painter.save()
        if not opt.state & QStyle.State_Enabled:
            painter.setOpacity(.5)
        brush = index.data(Qt.ForegroundRole)
        painter.setPen(brush.color() if brush is not None else QColor(T.TEXT_SOFT))
        painter.setFont(cell_font(13 if index.column() == 3 else 12, index.column() == 3))
        area = opt.rect.adjusted(8, 0, -8, 0)
        metrics = painter.fontMetrics()
        painter.drawText(area, int(Qt.AlignCenter | Qt.TextSingleLine), metrics.elidedText(text, Qt.ElideRight, area.width()))
        painter.restore()


class SelectionDelegate(ServerRowDelegate):
    def paint(self, painter, option, index):
        opt = self.row_option(option, index)
        self.draw_cell(painter, opt, index)
        checked = row_is_checked(index)
        box = QRectF(option.rect.center().x() - 11, option.rect.center().y() - 14, 22, 22)
        painter.save()
        if not opt.state & QStyle.State_Enabled:
            painter.setOpacity(.5)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(CHECK_FILL if checked else T.LINE_STRONG), 1.5))
        painter.setBrush(QColor(CHECK_FILL if checked else T.SUNKEN))
        painter.drawRoundedRect(box, 2, 2)
        if checked:
            mark = QPainterPath()
            mark.moveTo(box.left() + 5, box.top() + 11)
            mark.lineTo(box.left() + 9, box.top() + 15)
            mark.lineTo(box.left() + 17, box.top() + 6)
            painter.setPen(QPen(QColor(T.ON_BRASS), 2.6, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(mark)
            # Brass bar on the leading edge of the row.
            leading = option.rect.right() - 2 if option.direction == Qt.RightToLeft else option.rect.left()
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.fillRect(QRect(leading, option.rect.top(), 3, option.rect.height()), QColor(CHECK_FILL))
            painter.setFont(cell_font(10))
            painter.setPen(QColor(T.BRASS_BRIGHT))
            painter.drawText(option.rect.adjusted(0, 37, 0, 0), Qt.AlignCenter, tr('محدد'))
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if not index.flags() & Qt.ItemIsEnabled:
            return False
        toggle = (event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton) or (event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Space, Qt.Key_Select))
        if toggle:
            # CheckStateRole is an integer role. Avoid storing a Python enum in QVariant.
            return model.setData(index, Qt.Unchecked.value if row_is_checked(index) else Qt.Checked.value, Qt.CheckStateRole)
        return False


class PingItem(QTableWidgetItem):
    def __lt__(self, other):
        a = self.data(Qt.UserRole)
        b = other.data(Qt.UserRole)
        return (float('inf') if a is None else float(a)) < (float('inf') if b is None else float(b))


class RegionDelegate(ServerRowDelegate):
    """Flag on the leading edge, then the place name over its country line. Mirrors with the layout direction."""
    def paint(self, painter, option, index):
        opt = self.row_option(option, index)
        icon = QIcon(opt.icon)
        text = str(index.data(Qt.DisplayRole) or '').split('\n', 1)
        self.draw_cell(painter, opt, index)
        painter.save()
        if not opt.state & QStyle.State_Enabled:
            painter.setOpacity(.5)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setLayoutDirection(Qt.LeftToRight)
        rect = option.rect
        painter.setClipRect(rect)
        rtl = option.direction == Qt.RightToLeft
        flag = QRect(rect.right() - 46 if rtl else rect.left() + 14, rect.center().y() - 12, 32, 24)
        icon.paint(painter, flag)
        painter.setPen(QColor(T.LINE_STRONG))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(flag.adjusted(-1, -1, 0, 0))
        width = max(0, rect.width() - 72)
        middle = rect.center().y()
        for value, size, bold, color, baseline in [(text[0], 13, True, T.TEXT, middle - 3), (text[1] if len(text) > 1 else '', 11, False, T.TEXT_MUTED, middle + 16)]:
            font = cell_font(size, bold)
            painter.setFont(font)
            painter.setPen(QColor(color))
            metrics = QFontMetrics(font)
            value = metrics.elidedText(value.replace('⁦', '').replace('⁩', ''), Qt.ElideRight, width)
            x = flag.left() - 12 - metrics.horizontalAdvance(value) if rtl else flag.right() + 12
            painter.drawText(x, baseline, value)
        painter.restore()
