"""Performance knowledge and the Every-setting page: coverage of every setting, the skip mechanism through the
real Studio, the window itself, and its place in the main window."""
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from deadlock_fps import kv
from deadlock_fps.core import Studio, ASSETS
from deadlock_fps.perf import explain, ignored_names, ENTRIES, CATEGORIES, PROTECTED, STATUS_LABELS, STATUS_TEXT
from deadlock_fps.perf import knowledge
from deadlock_fps.perf.facts import FACTS, CONVAR_BUILD
from deadlock_fps.pages.performance import AllSettingsPage, ApplyReview
from deadlock_fps.shell.components import Badge
from deadlock_fps.settings import Settings, values, MAX_LEVEL, PRESETS


def every_setting():
    """The stem of every setting any slider position can write, by where it goes."""
    convars, video, scene = set(), set(), set()
    for level in range(MAX_LEVEL + 1):
        for aspect in (None, 2.0):
            for cpu in (True, False):
                s = Settings.at_level(level, aspect_ratio=aspect)
                s.cpu = cpu
                v, c, sc = values(s)
                convars.update(c)
                video.update(k.removeprefix('setting.') for k in v)
                scene.update(sc)
    return convars, video, scene


class Coverage(unittest.TestCase):
    def test_every_setting_the_recipe_can_write_is_explained_and_nothing_else_is(self):
        convars, video, scene = every_setting()
        written = convars | video | scene
        self.assertEqual(written - set(ENTRIES), set(), 'a setting was added to the recipe without an explanation: write one in knowledge.py and regenerate facts.py')
        self.assertEqual(set(ENTRIES) - written, set(), 'an explanation exists for a setting the recipe no longer writes')
        self.assertEqual(set(FACTS), set(ENTRIES))

    def test_entries_are_complete(self):
        for name, entry in ENTRIES.items():
            self.assertTrue(entry.effect.strip(), name)
            self.assertIn(entry.category, CATEGORIES, name)
            self.assertIn(entry.status, STATUS_LABELS, name)
            self.assertIn(entry.status, STATUS_TEXT, name)
            if entry.status == 'active':
                self.assertTrue(entry.default or name in ('fps_max_ui',), '%s is active but has no Valve default' % name)

    def test_the_facts_that_were_checked_by_hand(self):
        """Read from Valve's data for build %d on 2026-11-14 (see scripts/dev/perf_facts.py). Update with the facts when the game changes.""" % CONVAR_BUILD
        expected = {'r_shadows': 'blocked', 'r_enable_volume_fog': 'blocked', 'lb_enable_dynamic_lights': 'blocked', 'fog_enableskybox': 'removed',
                    'panorama_max_fps': 'removed', 'mat_vsync': 'removed', 'r_particle_shadows': 'removed', 'fog_enable': 'cheat', 'snd_occlusion_rays': 'cheat',
                    'HairShading': 'unverified', 'useadvanced': 'unverified', 'VolumetricFog': 'active', 'r_grass_quality': 'active', 'r_ssao': 'active',
                    'CSMCascadeResolution': 'active'}
        for name, status in expected.items():
            self.assertEqual(ENTRIES[name].status, status, name)
        self.assertEqual(ENTRIES['fog_enableskybox'].since, 6728)
        self.assertEqual(ENTRIES['panorama_max_fps'].since, 6711)
        self.assertEqual(ENTRIES['r_shadows'].default, 'true')

    def test_settings_that_change_what_you_can_see_are_marked(self):
        for name in ('fog_enable', 'r_enable_volume_fog', 'VolumetricFog', 'r_grass_quality', 'sc_clutter_enable', 'r_drawropes', 'r_aspectratio', 'r_size_cull_threshold'):
            self.assertTrue(ENTRIES[name].sight, name)
        for name in ('r_shadows', 'r_ssao', 'violence_hblood', 'fps_max'):
            self.assertFalse(ENTRIES[name].sight, name)

    def test_the_protected_settings_have_their_own_controls(self):
        self.assertEqual(PROTECTED, frozenset({'fps_max', 'fps_max_ui', 'r_aspectratio'}))
        for name in PROTECTED:
            self.assertTrue(ENTRIES[name].protected)
        self.assertFalse(any(n in PROTECTED for n in ignored_names(Settings.at_level(80))))


class Explaining(unittest.TestCase):
    def test_a_higher_level_only_adds_settings(self):
        previous = set()
        for level in (0, 50, 60, 80, 90, 110, 125, 150, 175, 200):
            names = {i.name for i in explain(Settings.at_level(level)).items}
            self.assertTrue(previous <= names, 'level %d dropped %s' % (level, sorted(previous - names)))
            previous = names

    def test_the_report_adds_up(self):
        for level in (0, 25, 80, 200):
            report = explain(Settings.at_level(level))
            self.assertEqual(report.written, len(report.items))
            self.assertEqual(report.confirmed + report.ignored + report.uncertain, report.written)
            self.assertEqual(report.left_out, 0)
            self.assertGreater(report.confirmed, 0)

    def test_the_report_matches_what_values_writes(self):
        s = Settings.at_level(80)
        video, convars, scene = values(s)
        stems = set(convars) | set(scene) | {k.removeprefix('setting.') for k in video}
        self.assertEqual({i.name for i in explain(s).items}, stems)

    def test_where_each_setting_goes(self):
        where = {i.name: i.where for i in explain(Settings.at_level(80)).items}
        self.assertEqual((where['fps_max'], where['VolumetricFog'], where['mat_vsync'], where['r_shadows']), ('both', 'gameinfo.gi', 'video.txt', 'gameinfo.gi'))

    def test_items_come_grouped_by_category_in_a_stable_order(self):
        items = explain(Settings.at_level(80)).items
        order = list(CATEGORIES)
        positions = [order.index(i.entry.category) for i in items]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(items, explain(Settings.at_level(80)).items)

    def test_leaving_settings_out_is_reflected_and_does_not_change_the_list(self):
        full = explain(Settings.at_level(80))
        cut = explain(Settings.at_level(80, skip=('r_shadows', 'VolumetricFog')))
        self.assertEqual([i.name for i in cut.items], [i.name for i in full.items], 'the window still lists what was left out, so it can be put back')
        self.assertEqual({i.name for i in cut.items if i.skipped}, {'r_shadows', 'VolumetricFog'})
        self.assertEqual((cut.written, cut.left_out), (full.written - 2, 2))

    def test_ignored_names_are_the_removed_and_blocked_ones(self):
        names = ignored_names(Settings.at_level(80))
        self.assertIn('r_shadows', names)
        self.assertIn('fog_enableskybox', names)
        self.assertNotIn('fog_enable', names, 'cheat-only is uncertain, not known to be ignored')
        self.assertNotIn('HairShading', names)
        self.assertTrue(all(ENTRIES[n].status in ('removed', 'blocked') for n in names))

    def test_a_setting_without_an_explanation_is_shown_honestly_not_fatally(self):
        trimmed = {k: v for k, v in ENTRIES.items() if k != 'r_shadows'}
        with patch.dict(knowledge.ENTRIES, trimmed, clear=True), patch('deadlock_fps.perf.explain.ENTRIES', trimmed):
            item = next(i for i in explain(Settings.at_level(80)).items if i.name == 'r_shadows')
        self.assertEqual(item.entry.status, 'unverified')
        self.assertIn('no explanation', item.entry.effect)


class SkipSetting(unittest.TestCase):
    def test_a_default_settings_object_writes_exactly_what_it_always_did(self):
        s = Settings.at_level(80)
        self.assertEqual(s.skip, ())
        self.assertEqual(values(s), values(replace(s, skip=())))

    def test_a_skipped_name_is_removed_from_every_place_it_would_be_written(self):
        video, convars, scene = values(Settings.at_level(80, skip=('r_citadel_shadow_quality', 'VolumetricFog', 'mat_vsync', 'r_grass_quality')))
        self.assertNotIn('r_citadel_shadow_quality', convars)
        self.assertNotIn('setting.r_citadel_shadow_quality', video, 'the video.txt twin goes too')
        self.assertNotIn('VolumetricFog', scene)
        self.assertNotIn('setting.mat_vsync', video)
        self.assertNotIn('r_grass_quality', convars)
        full = values(Settings.at_level(80))
        self.assertEqual((len(full[0]) - len(video), len(full[1]) - len(convars), len(full[2]) - len(scene)), (2, 2, 1))

    def test_other_settings_keep_their_values(self):
        full, cut = values(Settings.at_level(80)), values(Settings.at_level(80, skip=('r_shadows',)))
        self.assertEqual({k: v for k, v in full[1].items() if k != 'r_shadows'}, cut[1])
        self.assertEqual((full[0], full[2]), (cut[0], cut[2]))

    def test_validation(self):
        Settings.at_level(80, skip=('r_shadows', 'VolumetricFog')).validate()
        Settings.at_level(80, skip=['r_shadows']).validate()                    # a list is fine: JSON gives lists
        for bad in (('fps_max',), ('r_aspectratio',), ('fps_max_ui',), (5,), ('',), ('a b',), ('x' * 81,), ('r_shadows;rm',), ['a'] * 201, 'r_shadows', None, (None,)):
            with self.assertRaises(ValueError, msg=repr(bad)):
                Settings.at_level(80, skip=bad).validate()

    def test_it_survives_a_json_round_trip_and_old_profiles_still_load(self):
        s = Settings.at_level(80, skip=('r_shadows', 'VolumetricFog'), preset='custom')
        back = Settings.from_dict(json.loads(json.dumps(s.to_dict())))
        self.assertEqual((back.skip, values(back)), (s.skip, values(s)), 'what is written is the same after a save and a load')
        older = s.to_dict()
        del older['skip']
        self.assertEqual(Settings.from_dict(older).skip, ())
        self.assertEqual(Settings.from_dict(PRESETS['performance'].to_dict()), PRESETS['performance'])


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'Deadlock'
        self.gi = self.root / 'game/citadel/gameinfo.gi'
        self.gi.parent.mkdir(parents=True)
        self.gi.write_bytes((ASSETS / 'reference/gameinfo.gi').read_bytes())
        self.video = self.root / 'game/citadel/cfg/video.txt'
        self.video.parent.mkdir()
        self.video.write_bytes((ASSETS / 'reference/video.txt').read_bytes())
        self.original_gi, self.original_video = self.gi.read_bytes(), self.video.read_bytes()
        self.studio = Studio(self.root, self.video)
        patcher = patch('deadlock_fps.core.ensure_closed')
        patcher.start()
        self.addCleanup(patcher.stop)

    def apply(self, s):
        self.studio.apply(self.studio.plan(s), s)

    @staticmethod
    def section(text, name):
        node = kv.section(text, ['GameInfo', name])
        return {c.key: c.value for c in node.children} if node else {}


class ThroughTheStudio(Fixture):
    """The reference gameinfo.gi and video.txt were themselves written by this recipe, so they already hold the level-80 values.
    Level 0 writes the opposite (high quality), which makes "left at the file's own value" visible."""
    LEFT_OUT = ('r_shadows', 'r_particle_max_detail_level', 'VolumetricFog', 'r_citadel_shadow_quality')

    def written(self, settings):
        text = self.studio.plan(settings)[self.gi].decode('utf-8-sig')
        return self.section(text, 'ConVars'), self.section(text, 'SceneSystem')

    def video_values(self, settings):
        node = kv.section(self.studio.plan(settings)[self.video].decode('utf-8-sig'), ['video.cfg'])
        return {c.key: c.value for c in node.children}

    def test_a_setting_left_out_keeps_the_files_own_value_and_the_rest_take_the_levels(self):
        original_convars = self.section(self.original_gi.decode('utf-8-sig'), 'ConVars')
        original_scene = self.section(self.original_gi.decode('utf-8-sig'), 'SceneSystem')
        full_convars, full_scene = self.written(Settings.at_level(0))
        cut_convars, cut_scene = self.written(Settings.at_level(0, skip=self.LEFT_OUT))
        for name in ('r_shadows', 'r_particle_max_detail_level', 'r_citadel_shadow_quality'):
            self.assertNotEqual(full_convars[name], original_convars[name], 'the test needs a level that changes %s' % name)
            self.assertEqual(cut_convars[name], original_convars[name], '%s was left out, so the file keeps its own value' % name)
        self.assertEqual((full_scene['VolumetricFog'], original_scene['VolumetricFog'], cut_scene['VolumetricFog']), ('1', '0', '0'))
        self.assertEqual({k: v for k, v in full_convars.items() if k not in self.LEFT_OUT}, {k: v for k, v in cut_convars.items() if k not in self.LEFT_OUT})
        self.assertEqual({k: v for k, v in full_scene.items() if k != 'VolumetricFog'}, {k: v for k, v in cut_scene.items() if k != 'VolumetricFog'})

    def test_the_video_file_gets_the_same_treatment(self):
        full = self.video_values(Settings.at_level(0))
        cut = self.video_values(Settings.at_level(0, skip=('r_citadel_shadow_quality',)))
        self.assertEqual((full['setting.r_citadel_shadow_quality'], cut['setting.r_citadel_shadow_quality']), ('1', '0'))
        self.assertEqual(full['setting.r_post_bloom'], cut['setting.r_post_bloom'])

    def test_changing_the_choice_later_moves_the_setting_back_and_restore_still_works(self):
        full, cut = Settings.at_level(0), Settings.at_level(0, skip=self.LEFT_OUT)
        self.apply(full)
        self.assertEqual(self.section(self.gi.read_text(encoding='utf-8-sig'), 'ConVars')['r_shadows'], '1')
        self.apply(cut)
        self.assertEqual(self.section(self.gi.read_text(encoding='utf-8-sig'), 'ConVars')['r_shadows'], '0', "applying a smaller choice returns the setting to the file's own value")
        self.assertFalse(self.studio.plan(cut), 'and the same choice again changes nothing')
        self.apply(full)
        self.assertEqual(self.section(self.gi.read_text(encoding='utf-8-sig'), 'ConVars')['r_shadows'], '1', 'putting it back works too')
        self.studio.restore()
        self.assertEqual((self.gi.read_bytes(), self.video.read_bytes()), (self.original_gi, self.original_video))

    def test_what_the_studio_remembers_as_its_own_excludes_what_was_left_out(self):
        self.apply(Settings.at_level(0, skip=self.LEFT_OUT))
        entry = self.studio.state()['files'][str(self.gi)]
        owned = {tuple(scope): keys for scope, keys in entry['owned']}
        self.assertNotIn('r_shadows', owned[('GameInfo', 'ConVars')])
        self.assertNotIn('VolumetricFog', owned[('GameInfo', 'SceneSystem')])
        self.assertIn('r_citadel_ssao_quality', owned[('GameInfo', 'ConVars')])
        self.assertEqual(self.studio.state()['settings']['skip'], list(self.LEFT_OUT))


class TheEverySettingPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def page(self, **kwargs):
        s = Settings.at_level(80, **kwargs)
        page = AllSettingsPage(lambda: s)
        page.reload()
        self.addCleanup(page.deleteLater)
        return page

    def row(self, page, name):
        return next(r for r in range(page.table.rowCount()) if page.table.item(r, 1).text() == name)

    def status(self, page, name):
        return page.table.cellWidget(self.row(page, name), 4).findChild(Badge)

    def test_one_row_per_setting_with_its_facts(self):
        page = self.page()
        report = explain(Settings.at_level(80))
        self.assertEqual(page.table.rowCount(), len(report.items))
        row = self.row(page, 'r_shadows')
        self.assertEqual(self.status(page, 'r_shadows').text(), 'Blocked')
        self.assertIn('should ignore', self.status(page, 'r_shadows').toolTip())
        self.assertEqual((page.table.item(row, 2).text().replace('‎', ''), page.table.item(row, 3).text().replace('‎', '')), ('true', '0'), "Valve's value, then what is written")
        effects = ' '.join(l.text() for l in page.table.cellWidget(row, 1).findChildren(QLabel))
        self.assertIn('Master switch for shadows', effects)
        grass = ' '.join(l.text() for l in page.table.cellWidget(self.row(page, 'r_grass_quality'), 1).findChildren(QLabel))
        self.assertIn('can change what you see', grass)
        self.assertIn('build 6728', self.status(page, 'fog_enableskybox').text())
        self.assertEqual(page.tile_written.value.text(), str(report.written))
        self.assertIn('{}'.format(report.written), page.summary_text)

    def test_everything_is_written_until_the_user_chooses_otherwise(self):
        page = self.page()
        self.assertEqual(page.skip(), ())
        self.assertTrue(all(b.isChecked() for b in page.boxes))

    def test_unticking_a_row_leaves_it_out_and_updates_the_tiles(self):
        page = self.page()
        seen = []
        page.skipChanged.connect(seen.append)
        before = page.tile_written.value.text()
        page.boxes[self.row(page, 'r_ssao')].setChecked(False)
        self.assertEqual(page.skip(), ('r_ssao',))
        self.assertEqual(seen[-1], ('r_ssao',))
        self.assertNotEqual(page.tile_written.value.text(), before)
        self.assertIn('1 left out', page.summary_text)
        page.boxes[self.row(page, 'r_ssao')].setChecked(True)
        self.assertEqual(page.skip(), ())

    def test_leave_out_the_ignored_ones_and_write_everything(self):
        page = self.page()
        page.leave_out_ignored()
        self.assertEqual(set(page.skip()), set(ignored_names(Settings.at_level(80))))
        report = explain(replace(Settings.at_level(80), skip=page.skip()))
        self.assertEqual(report.ignored, 0)
        self.assertEqual(page.tile_ignored.value.text(), '0')
        page.write_everything()
        self.assertEqual(page.skip(), ())

    def test_settings_with_their_own_controls_cannot_be_unticked(self):
        page = self.page(aspect_ratio=2.0)          # r_aspectratio is only written when a view width is chosen
        for name in PROTECTED:
            box = page.boxes[self.row(page, name)]
            self.assertFalse(box.isEnabled(), name)
            self.assertTrue(box.isChecked())
        page.leave_out_ignored()
        self.assertFalse(any(n in PROTECTED for n in page.skip()))

    def test_even_a_forced_untick_of_a_protected_row_is_never_returned(self):
        """The control is disabled (above); this isolates the second line of defence, in case code ever unticks the row."""
        page = self.page(aspect_ratio=2.0)
        for name in PROTECTED:
            page.boxes[self.row(page, name)].setChecked(False)
        self.assertEqual(page.skip(), ())
        with self.assertRaises(ValueError):                         # and the settings themselves refuse them as well
            Settings.at_level(80, skip=tuple(PROTECTED)).validate()

    def test_an_earlier_choice_is_shown_ticked_off(self):
        page = self.page(skip=('r_shadows', 'VolumetricFog'))
        self.assertEqual(page.skip(), ('VolumetricFog', 'r_shadows'))
        self.assertIn('2 left out', page.summary_text)

    def test_filters_and_the_empty_state(self):
        page = self.page()
        page.category.setCurrentIndex(page.category.findData('shadows'))
        shown = [page.table.item(r, 1).text() for r in range(page.table.rowCount()) if not page.table.isRowHidden(r)]
        self.assertIn('r_shadows', shown)
        self.assertNotIn('r_grass_quality', shown)
        page.category.setCurrentIndex(0)
        page.only_ignored.setChecked(True)
        shown = {page.table.item(r, 1).text() for r in range(page.table.rowCount()) if not page.table.isRowHidden(r)}
        self.assertEqual(shown, set(ignored_names(Settings.at_level(80))))
        page.clear_filter()
        self.assertFalse(any(page.table.isRowHidden(r) for r in range(page.table.rowCount())))
        page.category.setCurrentIndex(page.category.findData('shadows'))
        page.only_ignored.setChecked(True)
        if not any(not page.table.isRowHidden(r) for r in range(page.table.rowCount())):
            self.assertFalse(page.empty.isHidden())

    def test_texts_from_the_table_are_plain(self):
        page = self.page()
        labels = [l for r in range(page.table.rowCount()) for l in page.table.cellWidget(r, 1).findChildren(QLabel)]
        self.assertTrue(labels and all(l.textFormat() == Qt.PlainText for l in labels))

    def test_it_states_what_it_is_based_on(self):
        page = self.page()
        self.assertIn('build %d' % CONVAR_BUILD, page.intro.text())


class InsideTheMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patches = [patch('deadlock_fps.ui.QStandardPaths.writableLocation', return_value=folder.name),
                   patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=folder.name),
                   patch('deadlock_fps.game_link.detect_games', return_value=[]), patch('deadlock_fps.mods.ModLibrary.discover', return_value=[])]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        from deadlock_fps.ui import Window
        w = Window()
        self.addCleanup(lambda: (w.close(), w.deleteLater()))
        w.guard_timer.stop()
        w.detect_timer.stop()
        w.servers.activate = lambda: None
        return w

    def test_nothing_is_left_out_by_default(self):
        w = self.window()
        self.assertEqual((w.skip, w.settings().skip), ((), ()))
        self.assertTrue(w.level_page.details.text())

    def test_the_choice_made_on_the_second_tab_travels_with_the_settings_and_shows_on_the_link(self):
        w = self.window()
        w.level.setValue(80)
        w.navigate('performance.all')
        self.assertEqual(w.current_slot, 'perf_all')
        row = next(r for r in range(w.all_page.table.rowCount()) if w.all_page.table.item(r, 1).text() == 'r_shadows')
        w.all_page.boxes[row].setChecked(False)
        self.assertEqual(w.settings().skip, ('r_shadows',))
        self.assertIn('1', w.level_page.details.text())
        self.assertNotIn('r_shadows', values(Settings.at_level(80, skip=w.settings().skip))[1])

    def test_moving_the_level_clears_a_choice_made_for_another_level(self):
        w = self.window()
        w.load_settings(Settings.at_level(60, skip=('r_ssao',)))
        self.assertEqual(w.skip, ('r_ssao',))
        w.level.setValue(70)
        self.assertEqual(w.settings().skip, ())

    def test_loading_settings_or_a_preset_replaces_the_choice(self):
        w = self.window()
        w.load_settings(Settings.at_level(60, skip=('r_ssao',)))
        self.assertEqual(w.skip, ('r_ssao',))
        w.load_preset('performance')
        self.assertEqual(w.skip, (), 'a preset is a whole recipe: it starts with nothing left out')
        self.assertEqual(w.level_page.details.text(), 'What does this level change?')

    def test_the_second_tab_lists_the_current_level(self):
        w = self.window()
        w.level.setValue(80)
        w.navigate('performance.all')
        self.assertEqual(w.all_page.table.rowCount(), len(explain(Settings.at_level(80, aspect_ratio=1.78)).items))

    def test_without_a_game_the_review_button_is_off_and_the_banner_says_why(self):
        w = self.window()
        w.show()
        self.assertFalse(w.level_page.review_button.isEnabled())
        self.assertFalse(w.level_page.game_notice.isHidden())

    def test_the_view_width_and_frame_limit_are_part_of_the_settings(self):
        w = self.window()
        w.aspect.setValue(250)
        w.level_page.fps.setValue(144)
        s = w.settings()
        self.assertEqual((s.aspect_ratio, s.fps), (2.5, 144))
        self.assertEqual(w.level_page.fps_value.text(), '144 FPS')
        w.level_page.fps.setValue(0)
        self.assertEqual(w.level_page.fps_value.text(), 'No limit')


class ApplyThroughTheWindow(Fixture):
    """The whole path a user takes on Performance: review, apply, see the toast, undo. A throwaway game folder; nothing else is touched."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        data = tempfile.TemporaryDirectory()
        self.addCleanup(data.cleanup)
        for target, value in (('deadlock_fps.ui.QStandardPaths.writableLocation', data.name), ('PySide6.QtCore.QStandardPaths.writableLocation', data.name)):
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, value in (('deadlock_fps.game_link.detect_games', []), ('deadlock_fps.mods.ModLibrary.discover', []), ('deadlock_fps.game_link.video_files', [self.video]),
                              ('deadlock_fps.core.video_files', [self.video])):
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        from deadlock_fps.ui import Window
        w = Window()
        self.addCleanup(lambda: (w.close(), w.deleteLater()))
        w.guard_timer.stop()
        w.detect_timer.stop()
        w.servers.activate = lambda: None
        w.path.setText(str(self.root))
        w.refresh_accounts()
        w.set_game_linked(True)
        return w

    def test_review_then_apply_writes_and_the_toast_undo_puts_the_originals_back(self):
        from deadlock_fps.shell.components import Toast
        w = self.window()
        self.assertTrue(w.level_page.review_button.isEnabled(), 'a linked game turns the review button on')
        w.load_settings(Settings.at_level(0))                    # the reference files hold level 80, so level 0 changes them
        shown = []
        with patch('deadlock_fps.pages.performance.ApplyReview.exec', lambda dialog: shown.append(dialog) or 1):
            w.level_page.review_button.click()
        self.assertEqual(len(shown), 1)
        self.assertGreaterEqual(shown[0].table.rowCount(), 1)
        self.assertNotEqual(self.gi.read_bytes(), self.original_gi, 'accepting the review wrote the file')
        toasts = w.centralWidget().findChildren(Toast)
        self.assertTrue(toasts, 'the user is told it was applied')
        w.undo_apply()
        self.assertEqual((self.gi.read_bytes(), self.video.read_bytes()), (self.original_gi, self.original_video), 'undo restores the originals')

    def test_cancelling_the_review_writes_nothing(self):
        w = self.window()
        w.load_settings(Settings.at_level(0))
        with patch('deadlock_fps.pages.performance.ApplyReview.exec', lambda dialog: 0):
            w.level_page.review_button.click()
        self.assertEqual((self.gi.read_bytes(), self.video.read_bytes()), (self.original_gi, self.original_video))

    def test_a_running_game_stops_the_write_and_says_nothing_was_changed(self):
        w = self.window()
        w.load_settings(Settings.at_level(0))
        with patch('deadlock_fps.pages.performance.ApplyReview.exec', lambda dialog: 1), patch('deadlock_fps.pages.performance.ensure_closed', side_effect=ValueError('Close Deadlock first.')):
            w.level_page.review_button.click()
        self.assertEqual(self.gi.read_bytes(), self.original_gi)
        self.assertFalse(w.level_page.error.isHidden())
        self.assertEqual(w.level_page.error.title.text(), 'Nothing was changed')
        self.assertIn('Close Deadlock', w.level_page.error.text.text())
        self.assertTrue(w.level_page.review_button.isEnabled(), 'the button is usable again')

    def test_already_applied_says_so_instead_of_opening_a_review(self):
        w = self.window()
        w.load_settings(Settings.at_level(0))
        with patch('deadlock_fps.pages.performance.ApplyReview.exec', lambda dialog: 1):
            w.level_page.review_button.click()
        changed = (self.gi.read_bytes(), self.video.read_bytes())
        with patch('deadlock_fps.pages.performance.ApplyReview.exec', side_effect=AssertionError('no review is needed')):
            w.level_page.review_button.click()                # the same choice again: nothing to review
        self.assertTrue(w.level_page.error.isHidden())
        self.assertEqual((self.gi.read_bytes(), self.video.read_bytes()), changed)


class TheReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_review_lists_files_and_what_changes_and_hides_the_lines_until_asked(self):
        with tempfile.TemporaryDirectory() as folder:
            gi = Path(folder) / 'gameinfo.gi'
            gi.write_text('a\nb\n')
            vpk = Path(folder) / 'pak.vpk'
            plan = {gi: b'a\nc\n', vpk: b'1234'}
            review = ApplyReview(plan, Settings.at_level(80))
            self.addCleanup(review.deleteLater)
            self.assertEqual(review.table.rowCount(), 2)
            self.assertIn('2 lines change', review.table.item(0, 1).text())
            self.assertIn('VPK', review.table.item(1, 1).text())
            self.assertTrue(review.diff.isHidden())
            review.every.setChecked(True)
            self.assertFalse(review.diff.isHidden())
            self.assertIn('+c', review.diff.toPlainText())


if __name__ == '__main__':
    unittest.main()
