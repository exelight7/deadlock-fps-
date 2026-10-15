"""High-contrast, clickable checkmarks for the server table."""
from PySide6.QtCore import Qt,QRectF,QEvent
from PySide6.QtGui import QColor,QPen,QPainter,QPainterPath,QBrush,QFont
from PySide6.QtWidgets import QStyledItemDelegate,QStyleOptionViewItem,QStyle,QApplication,QTableWidgetItem

SELECTED_BACKGROUND = '#3b3427'

def row_is_checked(index):
    # Qt item APIs return int, while a Python setData call may retain the enum.
    value=index.siblingAtColumn(0).data(Qt.CheckStateRole)
    return value==Qt.Checked or value==Qt.Checked.value

class ServerRowDelegate(QStyledItemDelegate):
    def row_option(self,option,index):
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index)
        if row_is_checked(index):
            opt.backgroundBrush=QBrush(QColor(SELECTED_BACKGROUND))
            opt.features &= ~QStyleOptionViewItem.Alternate
            opt.state &= ~QStyle.State_HasFocus
        return opt
    def draw_cell(self,painter,opt,index):
        style=opt.widget.style() if opt.widget else QApplication.style()
        painter.save();style.drawControl(QStyle.CE_ItemViewItem,opt,painter,opt.widget)
        if row_is_checked(index):
            painter.setPen(QColor('#6b5739'));painter.drawLine(opt.rect.topLeft(),opt.rect.topRight());painter.drawLine(opt.rect.bottomLeft(),opt.rect.bottomRight())
        painter.restore()
    def paint(self,painter,option,index):
        self.draw_cell(painter,self.row_option(option,index),index)

class SelectionDelegate(ServerRowDelegate):
    def paint(self,painter,option,index):
        opt=self.row_option(option,index)
        opt.features &= ~QStyleOptionViewItem.HasCheckIndicator;opt.text=''
        self.draw_cell(painter,opt,index)
        checked=row_is_checked(index)
        box=QRectF(option.rect.center().x()-11,option.rect.center().y()-14,22,22)
        painter.save();painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor('#e7c08a' if checked else '#858c8a'),1.5));painter.setBrush(QColor('#e7c08a' if checked else '#141719'));painter.drawRoundedRect(box,5,5)
        if checked:
            mark=QPainterPath();mark.moveTo(box.left()+5,box.top()+11);mark.lineTo(box.left()+9,box.top()+15);mark.lineTo(box.left()+17,box.top()+6)
            painter.setPen(QPen(QColor('#251f16'),2.7,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));painter.drawPath(mark)
            painter.setPen(Qt.NoPen);painter.setBrush(QColor('#e7c08a'));painter.drawRect(QRectF(option.rect.right()-3,option.rect.top(),3,option.rect.height()))
            font=QFont('Noto Sans Arabic');font.setPixelSize(9);painter.setFont(font);painter.setPen(QColor('#f2d6a6'))
            painter.drawText(option.rect.adjusted(0,38,0,0),Qt.AlignCenter,'محدد')
        painter.restore()
    def editorEvent(self,event,model,option,index):
        if not index.flags() & Qt.ItemIsEnabled:return False
        toggle=(event.type()==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton) or (event.type()==QEvent.KeyPress and event.key() in (Qt.Key_Space,Qt.Key_Select))
        if toggle:
            # CheckStateRole is an integer role. Avoid storing a Python enum in QVariant.
            return model.setData(index,Qt.Unchecked.value if row_is_checked(index) else Qt.Checked.value,Qt.CheckStateRole)
        return False

class PingItem(QTableWidgetItem):
    def __lt__(self,other):
        a=self.data(Qt.UserRole);b=other.data(Qt.UserRole)
        return (float('inf') if a is None else float(a))<(float('inf') if b is None else float(b))

class RegionDelegate(ServerRowDelegate):
    """Keep the flag and both name lines legible on Qt/Windows and Qt/Linux."""
    def paint(self,painter,option,index):
        from PySide6.QtGui import QFont,QFontMetrics,QIcon
        from PySide6.QtCore import QRect
        opt=self.row_option(option,index)
        icon=QIcon(opt.icon);text=str(index.data(Qt.DisplayRole) or '').split('\n',1)
        opt.features &= ~QStyleOptionViewItem.HasDecoration;opt.icon=QIcon();opt.text=''
        self.draw_cell(painter,opt,index)
        painter.save();painter.setRenderHint(QPainter.Antialiasing);painter.setLayoutDirection(Qt.LeftToRight)
        rect=option.rect;painter.setClipRect(rect)
        flag=QRect(rect.right()-44,rect.center().y()-12,32,24);icon.paint(painter,flag)
        width=max(0,rect.width()-66);right=flag.left()-10
        for value,size,bold,color,baseline in [(text[0],13,True,'#ede9e0',25),(text[1] if len(text)>1 else '',11,False,'#a8b2b5',47)]:
            font=QFont('Noto Sans Arabic');font.setPixelSize(size);font.setBold(bold);painter.setFont(font);painter.setPen(QColor(color))
            metrics=QFontMetrics(font);value=value.replace('\u2066','').replace('\u2069','');value=metrics.elidedText(value,Qt.ElideRight,width)
            painter.drawText(right-metrics.horizontalAdvance(value),rect.top()+baseline,value)
        painter.restore()
