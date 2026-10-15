"""Server Picker capabilities integrated into the Toolbox Qt interface."""
from pathlib import Path
import time
from PySide6.QtCore import Qt,QObject,Signal,QRunnable,QThreadPool,QStandardPaths,QTimer,QSize,QEvent
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QLineEdit,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMessageBox,QComboBox,QInputDialog,QMenu,QFrame)
from .servers import ServerStore,ping_regions,PingResult
from .server_delegate import SelectionDelegate,PingItem,RegionDelegate,ServerRowDelegate
from .region_info import region_info,flag_icon
from PySide6.QtGui import QColor
from .firewall import apply_elevated
from .core import ensure_closed

class JobSignals(QObject):
    result=Signal(object)
    failure=Signal(str)
    done=Signal()
    progress=Signal(object)
class Job(QRunnable):
    def __init__(self,fn,progress=False):super().__init__();self.fn=fn;self.with_progress=progress;self.signals=JobSignals()
    def run(self):
        try:self.signals.result.emit(self.fn(self.signals.progress.emit) if self.with_progress else self.fn())
        except Exception as e:self.signals.failure.emit(str(e))
        finally:self.signals.done.emit()

class ServerPage(QWidget):
    def __init__(self,parent=None,store=None):
        super().__init__(parent);self.busy=False;self.regions=[];self.measurements={};self._job=None;self.buttons=[];self.last_measure=0;self.pending=set();self.measure_total=0;self.selection_locked=False
        folder=Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))/'servers'
        self.store=store or ServerStore(folder)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,10,0);layout.setSpacing(12)
        text=QLabel('اضغط أي مكان في سطر المنطقة لتحديدها. التحديد لا يغيّر الحظر حتى تختار إجراءً بالأسفل.');text.setWordWrap(True);text.setObjectName('subtitle');layout.addWidget(text)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('ابحث بالعربي أو الإنجليزي: دبي، الإمارات، Frankfurt…');self.search.textChanged.connect(self.filter_rows);row.addWidget(self.search,1)
        self.add_button(row,'تحديث القائمة',self.refresh)
        self.ping_button=self.add_button(row,'قياس البنق',self.measure);self.ping_button.setToolTip('يقيس المناطق المحددة، أو كل المناطق الظاهرة إذا لم تحدد شيئًا.');layout.addLayout(row)
        row=QHBoxLayout()
        self.select_visible_button=self.add_button(row,'تحديد الظاهر',self.select_visible)
        clear_selection_button=self.add_button(row,'مسح التحديد',self.clear_selection)
        self.view_filter=QComboBox();self.view_filter.addItems(['كل المناطق','الحظر المحفوظ','المحددة فقط']);row.addWidget(self.view_filter,1);layout.addLayout(row)
        row=QHBoxLayout();self.selection_note=QLabel();self.selection_note.setWordWrap(True);self.selection_note.setObjectName('selectionNotice');row.addWidget(self.selection_note,1)
        sort_button=self.add_button(row,'الأقل بنقًا',self.sort_ping)
        saved=self.add_button(row,'اختياراتي ▾',lambda:None);self.saved_menu=QMenu(saved);saved.setMenu(self.saved_menu)
        help_button=self.add_button(row,'شرح',self.explain);layout.addLayout(row)
        self.selection_buttons=[self.select_visible_button,clear_selection_button,sort_button,saved,help_button]
        self.presets=QComboBox(self);self.presets.hide()
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['تحديد','المنطقة / الدولة','العدد','البنق (ms)','فقد الردود','حالة القياس','الحظر المحفوظ'])
        self.table.setItemDelegate(ServerRowDelegate(self.table));self.table.setItemDelegateForColumn(1,RegionDelegate(self.table));self.table.setIconSize(QSize(32,24));self.table.setItemDelegateForColumn(0,SelectionDelegate(self.table));self.table.itemChanged.connect(self.selection_changed)
        self.table.cellClicked.connect(self.toggle_row);self.table.installEventFilter(self);self.table.viewport().installEventFilter(self)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(40)
        for col,width in [(0,65),(2,50),(3,85),(4,85),(5,135),(6,115)]:
            self.table.horizontalHeader().setSectionResizeMode(col,QHeaderView.Fixed);self.table.setColumnWidth(col,width)
        self.table.verticalHeader().setVisible(False);self.table.verticalHeader().setDefaultSectionSize(62);self.table.setMinimumHeight(260);self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False);layout.addWidget(self.table,1)
        self.view_filter.currentIndexChanged.connect(self.filter_rows)
        self.actions_panel=QFrame();self.actions_panel.setObjectName('actionbar');actions=QVBoxLayout(self.actions_panel);actions.setContentsMargins(14,10,14,10);actions.setSpacing(8)
        self.status=QLabel('جاهز • اختر المناطق، ثم اختر إجراءً.');self.status.setWordWrap(True);self.status.setObjectName('subtitle');actions.addWidget(self.status)
        row=QHBoxLayout();self.block_button=self.add_button(row,'حظر المحدد',self.block_selected)
        self.unblock_button=self.add_button(row,'فك حظر المحدد',lambda:self.apply_action('unblock'));self.unblock_button.setObjectName('positive')
        self.only_button=self.add_button(row,'اسمح بالمحدد فقط',lambda:self.apply_action('only'));self.only_button.setToolTip('يسمح بالمحدد ويحظر بقية المناطق. راجع التأكيد قبل التطبيق.')
        self.clear_block_button=self.add_button(row,'فك كل الحظر',lambda:self.apply_action('clear'));self.clear_block_button.setObjectName('positive');self.clear_block_button.setToolTip('يزيل حظر Toolbox كله، حتى إذا لم تحدد مناطق.')
        actions.addLayout(row);layout.addWidget(self.actions_panel)
        self.status.setToolTip('حالة الحظر تمثل الاختيار المحفوظ، وليست فحصًا حيًا لجدار الحماية. Toolbox لا يحذف قواعد البرامج الأخرى.')
        self.reload_presets()
        try:self.set_catalog(self.store.load_catalog())
        except Exception as e:self.status.setText(str(e))
    def explain(self):
        QMessageBox.information(self,'البنق واختيار السيرفرات',
            'البنق قياس ICMP إلى خوادم Steam الوسيطة، وليس بنق المباراة الفعلي.\n\n'
            'لا رد: قد تكون ردود ICMP محجوبة؛ لا يعني أن سيرفر اللعبة متوقف. تعذر القياس: راجع توضيح الخطأ بالمرور على الخانة.\n\n'
            'العلامة ✓ تحدد المنطقة للعملية فقط. لإجراء تغيير، اختر الحظر أو السماح بالأزرار أسفل القائمة وراجع التأكيد.\n\n'
            'آخر اختيار محفوظ لا يمثل فحصًا لجدار الحماية. على Linux أعد تطبيق الحظر بعد إعادة التشغيل. الحظر قد يؤثر على ألعاب Steam الأخرى.\n\n'
            'إذا استعملت ServerPickerX سابقًا، فك قواعده من البرنامج الأصلي؛ Toolbox يعدل قواعده الخاصة فقط.')
    def add_button(self,row,text,fn):
        button=QPushButton(text);button.clicked.connect(fn);row.addWidget(button);self.buttons.append(button);return button
    def selected_codes(self):
        return {self.table.item(row,0).data(Qt.UserRole) for row in range(self.table.rowCount()) if self.table.item(row,0).checkState()==Qt.Checked}
    def showEvent(self,event):
        super().showEvent(event);QTimer.singleShot(300,self.activate)
    def activate(self):
        if self.isVisible() and not self.busy and time.monotonic()-self.last_measure>60:self.measure()
    def set_catalog(self,result):
        selected=self.selected_codes();before={r.code:r.relays for r in self.regions};regions,revision=result;self.regions=sorted(regions,key=lambda r:(0 if r.code=='dxb' else 1 if r.code=='dfjr' else 2,r.name.casefold()))
        for r in self.regions:
            if before.get(r.code)!=r.relays:self.measurements.pop(r.code,None)
        self.render(selected)
        self.status.setText(f'{len(self.regions)} منطقة اتصال • سيبدأ البنق تلقائيًا عند فتح الصفحة، أو اضغط إعادة القياس.')
    def selection_changed(self,item=None):
        if item is not None and item.column()!=0:return
        self.filter_rows()
    def update_selection_note(self):
        count=len(self.selected_codes());visible=sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        hidden=sum(self.table.isRowHidden(row) and self.table.item(row,0).checkState()==Qt.Checked for row in range(self.table.rowCount()))
        self.selection_note.setText((f'✓ تم تحديد {count} مناطق' if count else 'لم تحدد أي منطقة')+f' • الظاهر: {visible}'+(f' • {hidden} محدد خارج البحث' if hidden else ''))
        self.selection_note.setProperty('hasSelection',bool(count));self.selection_note.style().unpolish(self.selection_note);self.selection_note.style().polish(self.selection_note)
        self.table.viewport().update()
        if hasattr(self,'block_button'):
            for button in (self.block_button,self.unblock_button,self.only_button):button.setEnabled(bool(count) and not self.busy)
    def toggle_row(self,row,col):
        if col==0 or self.selection_locked:return
        item=self.table.item(row,0);item.setCheckState(Qt.Unchecked if item.checkState()==Qt.Checked else Qt.Checked)
    def eventFilter(self,watched,event):
        if watched is self.table.viewport() and event.type()==QEvent.Resize:
            compact=self.table.viewport().width()<820
            if compact!=getattr(self,'_compact',None):
                self._compact=compact
                for col in (2,4,5):self.table.setColumnHidden(col,compact)
        if watched is self.table and event.type()==QEvent.KeyPress and event.key()==Qt.Key_Space and self.table.currentColumn()!=0 and self.table.currentRow()>=0:
            self.toggle_row(self.table.currentRow(),self.table.currentColumn());return True
        return super().eventFilter(watched,event)
    def clear_selection(self):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):self.table.item(row,0).setCheckState(Qt.Unchecked)
        self.table.blockSignals(False);self.filter_rows()
    def select_visible(self):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):self.table.item(row,0).setCheckState(Qt.Checked)
        self.table.blockSignals(False);self.filter_rows()
    def sort_ping(self):self.ping_sorted=True;self.table.sortItems(3,Qt.AscendingOrder)
    def render(self,selected=None):
        selected=selected or set();blocked=set(self.store.state().get('blocked',[]));self.table.blockSignals(True);self.table.setRowCount(len(self.regions))
        for row,region in enumerate(self.regions):
            check=QTableWidgetItem();check.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable|Qt.ItemIsSelectable);check.setData(Qt.UserRole,region.code);check.setCheckState(Qt.Checked if region.code in selected else Qt.Unchecked)
            check.setToolTip('محدد للعملية فقط، وليس حظرًا. اضغط مرة لتبديل التحديد.');self.table.setItem(row,0,check)
            for col,text in [(1,region.name+'  ['+region.code+']'),(2,str(len(region.relays))),(6,'حظر محفوظ' if region.code in blocked else 'غير محظور')]:
                item=QTableWidgetItem(text)
                if col==1:
                    info=region_info(region);item.setText(info.text(region));item.setIcon(flag_icon(info.country));item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                    item.setData(Qt.UserRole,info.search(region));item.setToolTip(region.name+' ['+region.code+']\n'+info.country_name+'\n'+'\n'.join(f'{r.ip}:{r.first}–{r.last}' for r in region.relays))
                elif col==6:
                    item.setForeground(QColor('#e8b49b' if region.code in blocked else '#9dd7b2'));item.setTextAlignment(Qt.AlignCenter);item.setToolTip('الاختيار المحفوظ؛ لا يمثل فحصًا حيًا لجدار الحماية.')
                else:item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row,col,item)
            self.render_measurement(row,region.code)
        self.table.blockSignals(False)
        if getattr(self,'ping_sorted',False):self.table.sortItems(3,Qt.AscendingOrder)
        self.filter_rows()
    def render_measurement(self,row,code):
        result=self.measurements.get(code)
        if code in self.pending:ping,loss,state,detail,color='جارٍ القياس…','—','يقيس الآن','انتظر وصول الردود.','#d6b17c';numeric=None
        elif result is None:ping,loss,state,detail,color='لم يُقَس','—','بانتظار القياس','لم يبدأ القياس لهذه المنطقة بعد.','#94a2b2';numeric=None
        elif result.status=='ok':
            ping=f'{result.latency:.1f}';loss=f'{result.loss}%';state='وصل رد';detail=result.detail+'\nفقد الردود: '+str(result.loss)+'%\nالعنوان: '+result.address;numeric=result.latency
            color='#9dd7b2' if result.latency<=60 else ('#f4cb79' if result.latency<=120 else '#f39b92')
        else:
            ping='لا رد' if result.status=='no_reply' else ('انتهت المهلة' if result.status=='timeout' else 'تعذر القياس')
            loss='لا رد' if result.status=='no_reply' else 'غير متاح';state='ردود محجوبة أو غير متاحة' if result.status=='no_reply' else 'راجع التوضيح'
            detail=result.detail+('\nالعنوان: '+result.address if result.address else '');color='#b4bdc7';numeric=None
        for col,text in [(3,ping),(4,loss),(5,state)]:
            item=PingItem(text) if col==3 else QTableWidgetItem(text)
            if col==3:item.setData(Qt.UserRole,numeric);item.setForeground(QColor(color))
            item.setToolTip(detail);item.setTextAlignment(Qt.AlignCenter);self.table.setItem(row,col,item)
    def filter_rows(self,*_):
        if not hasattr(self,'table'):return
        text=self.search.text().strip().casefold();mode=self.view_filter.currentIndex();blocked=set(self.store.state().get('blocked',[]))
        for row in range(self.table.rowCount()):
            item=self.table.item(row,1)
            if item is None:continue
            code=self.table.item(row,0).data(Qt.UserRole)
            visible=text in (item.data(Qt.UserRole) or item.text().casefold()) and (mode!=1 or code in blocked) and (mode!=2 or self.table.item(row,0).checkState()==Qt.Checked)
            self.table.setRowHidden(row,not visible)
        self.update_selection_note()
    def start(self,fn,success,message,progress=False):
        if self.busy:return
        self.busy=True;self.selection_locked=not progress;self.status.setText(message);self.table.setEnabled(progress);self.search.setEnabled(progress);self.view_filter.setEnabled(progress)
        for button in self.buttons:button.setEnabled(False)
        if progress:
            for button in self.selection_buttons:button.setEnabled(True)
        self._job=Job(fn,progress);self._job.signals.progress.connect(self.ping_progress);self._job.signals.result.connect(success);self._job.signals.failure.connect(self.failed);self._job.signals.done.connect(self.finished)
        QThreadPool.globalInstance().start(self._job)
    def finished(self):
        self.busy=False
        for button in self.buttons:button.setEnabled(True)
        self._job=None;self.selection_locked=False;self.table.setEnabled(True);self.search.setEnabled(True);self.view_filter.setEnabled(True);self.update_selection_note()
    def failed(self,message):
        for code in list(self.pending):self.measurements[code]=PingResult(None,None,'error',message)
        self.pending.clear();self.render(self.selected_codes());self.status.setText('تعذر إكمال العملية: '+message[:2000])
    def refresh(self):self.start(self.store.refresh,self.set_catalog,'أجلب أحدث مناطق الاتصال من Steam…')
    def measure(self):
        if self.busy:return
        selected=self.selected_codes();visible={self.table.item(row,0).data(Qt.UserRole) for row in range(self.table.rowCount()) if not self.table.isRowHidden(row)}
        regions=[r for r in self.regions if r.code in (selected or visible)]
        if not regions:self.status.setText('لا توجد مناطق ظاهرة للقياس.');return
        self.pending={r.code for r in regions};self.measure_total=len(regions);self.render(self.selected_codes())
        self.start(lambda emit:ping_regions(regions,lambda code,result:emit((code,result))),self.measured,f'أقيس البنق • 0/{self.measure_total} • النتائج ستظهر فور وصولها.',progress=True)
    def ping_progress(self,payload):
        code,result=payload;self.measurements[code]=result;self.pending.discard(code)
        for row in range(self.table.rowCount()):
            if self.table.item(row,0).data(Qt.UserRole)==code:self.render_measurement(row,code);break
        if getattr(self,'ping_sorted',False):self.table.sortItems(3,Qt.AscendingOrder)
        self.status.setText(f'أقيس البنق • اكتمل {self.measure_total-len(self.pending)}/{self.measure_total} • هذا اتصال وسيط وليس بنق المباراة.')
    def measured(self,result):
        self.pending.clear();self.last_measure=time.monotonic();selected=self.selected_codes();self.measurements.update(result);self.render(selected)
        ok=sum(r.status=='ok' for r in result.values());errors=sum(r.status=='error' for r in result.values())
        self.status.setText(f'اكتمل القياس: {ok}/{len(result)} مناطق ردّت'+(f' • {errors} أخطاء أداة القياس' if errors else '')+' • لا رد يعني أن ICMP لم يستجب، وليس أن سيرفر اللعبة متوقف. هذا ليس بنق المباراة.')
    def reload_presets(self):
        self.presets.clear();self.presets.addItems(sorted(self.store.state().get('presets',{})))
        self.saved_menu.clear();self.saved_menu.addAction('حفظ التحديد الحالي',self.save_preset)
        for index in range(self.presets.count()):
            name=self.presets.itemText(index);action=self.saved_menu.addAction('تحميل: '+name);action.triggered.connect(lambda _,n=name:self.choose_preset(n))
        self.saved_menu.addSeparator();self.saved_menu.addAction('حذف اختيار محفوظ…',self.choose_delete_preset)
    def choose_preset(self,name):
        self.presets.setCurrentText(name);self.view_filter.setCurrentIndex(0);self.load_preset()
    def choose_delete_preset(self):
        names=[self.presets.itemText(i) for i in range(self.presets.count())]
        if not names:self.status.setText('لا توجد اختيارات محفوظة لحذفها.');return
        name,ok=QInputDialog.getItem(self,'حذف اختيار محفوظ','اختر الاسم:',names,editable=False)
        if ok:self.presets.setCurrentText(name);self.delete_preset()
    def save_preset(self):
        codes=self.selected_codes()
        if not codes:self.status.setText('حدد مناطق قبل الحفظ.');return
        name,ok=QInputDialog.getText(self,'حفظ اختيار السيرفرات','اسم الاختيار:')
        if ok:
            try:self.store.save_preset(name,codes);self.reload_presets();self.status.setText('حُفظ الاختيار؛ لم يتغير الحظر.')
            except Exception as e:self.failed(str(e))
    def load_preset(self):
        codes=set(self.store.state().get('presets',{}).get(self.presets.currentText(),[]));self.search.clear();self.render(codes);self.status.setText('تم تحميل الاختيار. اختر إجراء الحظر لتطبيقه.')
    def delete_preset(self):self.store.delete_preset(self.presets.currentText());self.reload_presets()
    def block_selected(self):self.apply_action('block')
    def apply_action(self,action):
        if self.busy:return
        try:
            ensure_closed();selected=self.selected_codes()
            if action in {'block','unblock','only'} and not selected:raise ValueError('حدد منطقة واحدة على الأقل.')
            plan,blocked=self.store.plan(self.regions,selected,action);plan['reset']=action=='clear'
            selected_names=[region_info(r).city+' ['+r.code+']' for r in self.regions if r.code in selected]
            if action=='clear':description='إزالة كل قواعد الحظر التي أنشأها Toolbox. لا تحتاج تحديد مناطق، ولا تُحذف قواعد البرامج الأخرى.'
            elif action=='unblock':description='فك الحظر المحفوظ عن:\n'+'\n'.join(selected_names)
            elif action=='only':description='السماح بالمناطق المحددة فقط:\n'+'\n'.join(selected_names)+'\n\nسيُحظر باقي المناطق في القائمة.'
            else:description='حظر المناطق المحددة:\n'+'\n'.join(selected_names)
            description+='\n\nإجمالي المناطق المحظورة بعد العملية: '+str(len(blocked))
            description+=f'\n\nعدد قواعد UDP: {len(plan["new"])}.\nستظهر نافذة صلاحية المدير. قد تتأثر ألعاب Steam أخرى بنفس الخوادم الوسيطة.'
            if QMessageBox.question(self,'مراجعة اختيار السيرفرات',description)!=QMessageBox.Yes:return
            def apply():
                ensure_closed();apply_elevated(plan);self.store.record(blocked,plan['new']);return blocked
            self.last_action=action
            self.start(apply,self.applied,'أطبّق القواعد • أكمل نافذة صلاحية المدير إن ظهرت…')
        except Exception as e:self.failed(str(e))
    def applied(self,result):
        self.render(self.selected_codes());self.status.setText(('تم فك كل حظر Toolbox.' if getattr(self,'last_action','')=='clear' else 'تم فك حظر المناطق المحددة.' if getattr(self,'last_action','')=='unblock' else 'تم تطبيق الاختيار.')+f' • الحظر المحفوظ الآن: {len(result)} مناطق.')
