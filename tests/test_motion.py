import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import unittest
from PySide6.QtCore import Qt,QEvent,QPointF,qInstallMessageHandler
from PySide6.QtGui import QColor,QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from deadlock_fps.shell.motion import Intro,PageTransition,alpha,tween
from deadlock_fps.settings import PRESETS
from deadlock_fps.ui import Window


class Motion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def run_for(self,ms):
        end=time.monotonic()+ms/1000
        while time.monotonic()<end:self.app.processEvents();time.sleep(.002)
    def window(self):
        w=Window();w.guard_timer.stop();w.servers.activate=lambda:None;self.addCleanup(w.close);return w

    def test_hidden_widgets_skip_animation_and_land_on_final_state(self):
        w=self.window()
        for address,slot,page in (('servers','servers','servers'),('performance','graphics','performance'),('settings.update','settings','settings')):
            w.navigate(address);self.assertEqual(w.current_slot,slot);self.assertFalse(w.transition.isVisible())
            self.assertTrue(w.nav[page].isChecked());self.assertEqual(sum(b.isChecked() for b in w.nav.values()),1)
        w.load_preset('ultra');self.assertEqual(w.level.value(),PRESETS['ultra'].level)
        self.assertEqual(w.level_page.presets.value(),'ultra')
        w.level.setValue(57);self.assertIsNone(w.level_page.presets.value())

    def test_page_changes_immediately_while_the_overlay_animates_and_ignores_the_mouse(self):
        messages=[];previous=qInstallMessageHandler(lambda kind,context,text:messages.append(text))
        try:
            w=self.window();w.resize(1200,820);w.show();self.run_for(60)
            w.navigate('performance');self.assertEqual(w.current_slot,'graphics');self.assertTrue(w.transition.isVisible())
            self.assertTrue(w.transition.testAttribute(Qt.WA_TransparentForMouseEvents))
            # A second click mid-transition and a resize must not leave the overlay behind.
            w.navigate('servers');self.assertEqual(w.current_slot,'servers');self.run_for(40);w.resize(1000,700);self.run_for(40)
            self.assertFalse(w.transition.isVisible())
            QTest.mouseClick(w.nav['mods'],Qt.LeftButton);self.assertEqual(w.current_address,'mods.browse');self.assertEqual(w.current_slot,'store');self.assertTrue(w.nav['mods'].isChecked())
            self.run_for(1300)
            self.assertFalse(w.transition.isVisible());self.assertIsNone(w.transition.before)
            w.navigate('mods.browse');self.assertFalse(w.transition.isVisible(),'same page must not animate')
        finally:qInstallMessageHandler(previous)
        self.assertEqual([m for m in messages if 'propagateSizeHints' not in m],[])

    def test_update_badge_keeps_the_text_contract(self):
        w=self.window();w.updates.updateAvailable.emit(True);self.assertEqual(w.nav['settings'].text(),'الإعدادات •');self.assertTrue(w.nav['settings'].badged)
        w.navigate('settings.update');self.assertNotIn('•',w.page_title.text());self.assertEqual(w.settings_view.nav['update'].text(),'App update •')
        w.updates.updateAvailable.emit(False);self.assertEqual(w.nav['settings'].text(),'الإعدادات');self.assertFalse(w.nav['settings'].badged)
        self.assertEqual(w.settings_view.nav['update'].text(),'App update');self.assertTrue(w.settings_view.nav['update'].isChecked())

    def test_the_launch_reveal_leaves_nothing_behind(self):
        w=self.window();w.resize(900,600);w.show()
        reveal=Intro(w.centralWidget(),QPixmap(8,8),'Deadlock Toolbox','VERSION 1');reveal.grab()
        self.assertTrue(reveal.testAttribute(Qt.WA_TransparentForMouseEvents));self.run_for(1300)
        with self.assertRaises(RuntimeError):reveal.isVisible()           # it deleted itself when it finished

    def test_small_helpers(self):
        self.assertAlmostEqual(alpha(QColor('#ffffff'),2).alphaF(),1.);self.assertAlmostEqual(alpha(QColor('#ffffff'),-1).alphaF(),0.)
        seen=[];host=QPushButton();animation=tween(host,30,seen.append);animation.start();self.run_for(120);self.assertTrue(seen);self.assertAlmostEqual(seen[-1],1.)


if __name__=='__main__':unittest.main()
