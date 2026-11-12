import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import unittest
from PySide6.QtCore import Qt,QEvent,QPointF,qInstallMessageHandler
from PySide6.QtGui import QEnterEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from deadlock_fps.motion import Fader,Glow,LevelMeter,NavButton,StatusChip,enliven
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
        for i in (4,1,6):
            w.navigate(i);self.assertEqual(w.stack.currentIndex(),i);self.assertFalse(w.transition.isVisible())
            self.assertIs(w.nav_indicator.target,w.nav[i]);self.assertEqual(w.nav[i].active.level,1.)
        w.load_preset('ultra');self.assertEqual(w.level_meter.shown,PRESETS['ultra'].level)
        self.assertTrue(w.preset_buttons['ultra'].property('active'));self.assertFalse(w.preset_buttons['balanced'].property('active'))
        w.level.setValue(57);self.assertFalse(any(b.property('active') for b in w.preset_buttons.values()))
        meter=LevelMeter(200);meter.set_value(999);self.assertEqual(meter.shown,200)

    def test_page_changes_immediately_while_the_overlay_animates_and_ignores_the_mouse(self):
        messages=[];previous=qInstallMessageHandler(lambda kind,context,text:messages.append(text))
        try:
            w=self.window();w.resize(1200,820);w.show();self.run_for(60)
            w.navigate(1);self.assertEqual(w.stack.currentIndex(),1);self.assertTrue(w.transition.isVisible())
            self.assertTrue(w.transition.testAttribute(Qt.WA_TransparentForMouseEvents))
            # A second click mid-transition and a resize must not leave the overlay behind.
            w.navigate(4);self.assertEqual(w.stack.currentIndex(),4);self.run_for(40);w.resize(1000,700);self.run_for(40)
            self.assertFalse(w.transition.isVisible())
            QTest.mouseClick(w.nav[2],Qt.LeftButton);self.assertEqual(w.stack.currentIndex(),2);self.assertTrue(w.nav[2].isChecked())
            self.run_for(1300)
            self.assertFalse(w.transition.isVisible());self.assertIsNone(w.transition.before)
            self.assertEqual(w.nav_indicator.geometry(),w.nav[2].geometry())
            w.navigate(2);self.assertFalse(w.transition.isVisible(),'same page must not animate')
        finally:qInstallMessageHandler(previous)
        self.assertEqual([m for m in messages if 'propagateSizeHints' not in m],[])

    def test_update_badge_keeps_the_text_contract(self):
        w=self.window();w.updates.updateAvailable.emit(True);self.assertEqual(w.nav[6].text(),'التحديث والتثبيت •');self.assertTrue(w.nav[6].badged)
        w.navigate(6);self.assertNotIn('•',w.heading.text())
        w.updates.updateAvailable.emit(False);self.assertEqual(w.nav[6].text(),'التحديث والتثبيت');self.assertFalse(w.nav[6].badged)
        button=NavButton('Page',w.nav[0].glyph);button.resize(190,42);button.setText('Page •');button.grab();button.setChecked(True);button.grab()

    def test_game_chip_follows_the_connected_text(self):
        chip=StatusChip('ربط اللعبة');self.assertEqual(chip.state.level,0.);self.assertFalse(chip.icon().isNull())
        chip.setText('اللعبة مرتبطة');self.assertEqual(chip.state.level,1.);chip.setText('Game connected');self.assertEqual(chip.state.level,1.)
        chip.setText('Connect game');self.assertEqual(chip.state.level,0.);self.assertEqual(chip.text(),'Connect game')

    def test_glow_is_created_on_hover_and_rests_disabled(self):
        w=self.window();enliven(w)
        glowing=[b for b in w.findChildren(QPushButton) if b.property('glow')]
        self.assertIn(w.apply_button,glowing);self.assertEqual(len(w.apply_button.findChildren(Glow)),1,'enliven must be idempotent')
        self.assertIsNone(w.apply_button.graphicsEffect())
        w.resize(1200,820);w.show();self.run_for(60)
        glow=w.apply_button.findChildren(Glow)[0];center=QPointF(w.apply_button.rect().center())
        self.app.sendEvent(w.apply_button,QEnterEvent(center,center,center));self.run_for(320)
        self.assertTrue(glow.effect.isEnabled());self.assertGreater(glow.effect.blurRadius(),10)
        self.app.sendEvent(w.apply_button,QEvent(QEvent.Leave));self.run_for(320);self.assertFalse(glow.effect.isEnabled())
        w.apply_button.setEnabled(False);self.app.sendEvent(w.apply_button,QEnterEvent(center,center,center));self.run_for(60);self.assertFalse(glow.effect.isEnabled())

    def test_fader_retargets_from_its_current_level(self):
        seen=[];host=QPushButton();fader=Fader(host,60,lambda:seen.append(fader.level))
        fader.to(1,False);self.assertEqual(fader.level,1.);fader.to(0);self.run_for(160);self.assertEqual(fader.level,0.);self.assertGreater(len(seen),2)


if __name__=='__main__':unittest.main()
