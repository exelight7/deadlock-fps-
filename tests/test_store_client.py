"""GameBanana client: request shape, strict normalisation of untrusted JSON, and error mapping."""
import json
import unittest
from urllib.parse import urlsplit, parse_qs

from deadlock_fps.repos.errors import RepoError, RATE_LIMITED, NOT_FOUND, NETWORK
from deadlock_fps.repos.transport import Response
from deadlock_fps.store import GameBananaClient, BAD_RESPONSE
from deadlock_fps.store.gamebanana import (clean, to_int, safe_url, plain_text, parse_submission, parse_profile, parse_file,
                                           PAGE_SIZE, GAME_ID)
from store_fixtures import (PagedGameBanana, record, image, file_entry, profile_document, index_document, ok, status, IMAGES)


class RequestShape(unittest.TestCase):
    def setUp(self):
        self.server = PagedGameBanana([record(i) for i in range(1, 4)])
        self.client = GameBananaClient(self.server)

    def test_index_request_uses_the_deadlock_filter_and_the_largest_page(self):
        page = self.client.index_page(2)
        url = self.server.calls[0]
        query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        self.assertEqual(url.split('?')[0], 'https://gamebanana.com/apiv11/Mod/Index')
        self.assertEqual(query, {'_nPerpage': str(PAGE_SIZE), '_aFilters[Generic_Game]': str(GAME_ID), '_nPage': '2', '_sSort': 'Generic_Oldest'})
        self.assertIn('%5BGeneric_Game%5D', url, 'brackets must be percent-encoded')
        self.assertEqual(page.submissions, ())          # page 2 of 3 records is empty

    def test_sort_follows_the_mode(self):
        self.client.index_page(1)
        self.client.index_page(1, newest=True)
        self.assertEqual(self.server.index_requests(), [('Generic_Oldest', 1), ('Generic_LatestModified', 1)])

    def test_page_must_be_in_range(self):
        for bad in (0, -1, 251):
            with self.assertRaises(ValueError):
                self.client.index_page(bad)

    def test_requests_identify_the_client_and_ask_for_json(self):
        seen = {}

        class Spy(PagedGameBanana):
            def get(self, url, *, max_bytes, headers=None, timeout=15.0):
                seen.update(headers or {})
                return super().get(url, max_bytes=max_bytes, headers=headers, timeout=timeout)

        GameBananaClient(Spy([record(1)]), user_agent='Tester').index_page(1)
        self.assertEqual(seen, {'Accept': 'application/json', 'User-Agent': 'Tester'})

    def test_categories_root_and_child(self):
        self.server.categories = [{'_idRow': 33295, '_sName': 'Skins', '_nItemCount': 4110, '_nCategoryCount': 40, '_bIsObsolete': False},
                                  {'_idRow': 0, '_sName': 'Broken'}, 'junk']
        found = self.client.categories()
        self.assertEqual([(c.id, c.name, c.items, c.children) for c in found], [(33295, 'Skins', 4110, 40)])
        self.client.categories(parent=33295)
        root, child = [{k: v[0] for k, v in parse_qs(urlsplit(u).query).items()} for u in self.server.calls]
        self.assertEqual(root['_idGameRow'], str(GAME_ID))
        self.assertEqual(child['_idCategoryRow'], '33295')
        self.assertNotIn('_idGameRow', child)

    def test_profile_request_and_identity_check(self):
        self.server.profiles[711387] = profile_document(711387)
        self.assertEqual(self.client.profile(711387).submission.id, 711387)
        self.assertTrue(self.server.calls[-1].endswith('/Mod/711387/ProfilePage'))
        self.server.profiles[5] = profile_document(6)             # the server answers with another mod
        with self.assertRaises(RepoError) as caught:
            self.client.profile(5)
        self.assertEqual(caught.exception.code, BAD_RESPONSE)
        for bad in (0, -3, 'x', None):
            with self.assertRaises(ValueError):
                self.client.profile(bad)


class ErrorMapping(unittest.TestCase):
    def client_answering(self, response):
        server = PagedGameBanana()
        server.hook = lambda url, query: response
        return GameBananaClient(server)

    def code_of(self, response, call=lambda c: c.index_page(1)):
        with self.assertRaises(RepoError) as caught:
            call(self.client_answering(response))
        return caught.exception

    def test_rate_limit_carries_retry_after(self):
        error = self.code_of(status(429, retry_after='120'))
        self.assertEqual(error.code, RATE_LIMITED)
        self.assertIn('120', error.message)

    def test_not_found_and_server_errors(self):
        self.assertEqual(self.code_of(status(404), lambda c: c.profile(5)).code, NOT_FOUND)
        self.assertEqual(self.code_of(status(503)).code, NETWORK)

    def test_unusable_bodies(self):
        for body in (b'<html>', b'', b'\xff\xfe', b'[]', b'{"_aRecords": 5}', b'{"_aMetadata": {}}'):
            self.assertEqual(self.code_of(Response(200, body, {}, '')).code, BAD_RESPONSE, body)

    def test_a_bad_record_does_not_sink_its_page(self):
        good = record(1)
        page = self.client_answering(ok(index_document([good, 'junk', {'_idRow': 'x'}, record(3, model='Sound')]))).index_page(1)
        self.assertEqual([s.id for s in page.submissions], [1])
        self.assertEqual((page.raw_count, page.skipped), (4, 3))


class Cleaning(unittest.TestCase):
    def test_clean_bounds_and_strips(self):
        self.assertEqual(clean('  a\x00b‮  c\n d  '), 'ab c d')
        self.assertEqual(clean('x' * 500, 10), 'x' * 10)
        for not_text in (None, 5, b'x', ['x']):
            self.assertEqual(clean(not_text), '')

    def test_clean_keeps_arabic_and_direction_marks(self):
        self.assertEqual(clean('سكن ‏رائع'), 'سكن ‏رائع')

    def test_to_int(self):
        self.assertEqual([to_int(v) for v in (5, '12', 3.0, 3.5, True, -1, '²', '١٢', None, 2 ** 60)], [5, 12, 3, 0, 0, 0, 0, 0, 0, 0])

    def test_safe_url_only_accepts_gamebanana_https(self):
        good = ['https://images.gamebanana.com/a.jpg', 'https://gamebanana.com/x', 'https://files.gamebanana.com/y']
        for url in good:
            self.assertEqual(safe_url(url), url)
        for url in ('http://images.gamebanana.com/a.jpg', 'https://gamebanana.com.evil.net/a.jpg', 'https://evilgamebanana.com/a.jpg',
                    'https://127.0.0.1/a.jpg', 'https://user:pw@gamebanana.com/a', 'https://images.gamebanana.com:8443/a', 'javascript:alert(1)', '', None, 5):
            self.assertEqual(safe_url(url), '', url)

    def test_plain_text_drops_markup_and_scripts(self):
        html = '<p>One &amp; two</p><script>alert(1)</script><style>p{}</style><br>Three<ul><li>a</li><li>b</li></ul>'
        self.assertEqual(plain_text(html), 'One & two\n\nThree\n\na\n\nb')
        self.assertEqual(plain_text('<b>unclosed <i>tags'), 'unclosed tags')
        self.assertEqual(plain_text(None), '')
        self.assertLessEqual(len(plain_text('x' * 100000)), 20000)


class SubmissionParsing(unittest.TestCase):
    def test_a_normal_listing(self):
        s = parse_submission(record(42, 'Pink Doorman', category='Skins', sub='Doorman', author='Mira', tags=['pink', {'_sValue': 'vfx'}, 'pink']))
        self.assertEqual((s.id, s.name, s.category, s.subcategory, s.author), (42, 'Pink Doorman', 'Skins', 'Doorman', 'Mira'))
        self.assertEqual(s.tags, ('pink', 'vfx'))
        self.assertEqual(s.url, 'https://gamebanana.com/mods/42')
        self.assertTrue(s.has_files and not s.nsfw and not s.obsolete)
        self.assertEqual(s.thumbnail, IMAGES + '/220-90_2a0.jpg')
        self.assertEqual(s.images, (IMAGES + '/530-90_2a0.jpg',))

    def test_unusable_records_are_dropped(self):
        for bad in (None, 'x', [], {}, record(0), record(-4), record(True), {**record(5), '_idRow': 'abc'}, {**record(5), '_sName': ''},
                    {**record(5), '_sName': '\x00‮'}, {**record(5), '_sName': None}, record(5, model='Sound')):
            self.assertIsNone(parse_submission(bad), bad)

    def test_names_are_cleaned(self):
        s = parse_submission(record(1, name='Evil‮txt.exe\x00  '))
        self.assertEqual(s.name, 'Eviltxt.exe')
        self.assertEqual(len(parse_submission(record(1, name='n' * 999)).name), 200)

    def test_visibility_decides_nsfw(self):
        self.assertEqual([parse_submission(record(1, visibility=v)).nsfw for v in ('show', 'warn', 'hide', None, 5)],
                         [False, True, True, False, False])

    def test_flags(self):
        self.assertTrue(parse_submission(record(1, obsolete=True)).obsolete)
        self.assertFalse(parse_submission(record(1, files=False)).has_files)
        document = record(1)
        del document['_bHasFiles']
        self.assertTrue(parse_submission(document).has_files)

    def test_modified_falls_back_to_added(self):
        document = record(1, added=500)
        document['_tsDateModified'] = 'later'
        self.assertEqual(parse_submission(document).modified, 500)

    def test_images_must_be_https_gamebanana_with_a_plain_file_name(self):
        def doc(*entries):
            d = record(1)
            d['_aPreviewMedia'] = {'_aImages': list(entries)}
            return parse_submission(d)

        good = image(1)
        cases = [
            {**good, '_sBaseUrl': 'http://images.gamebanana.com/img'},
            {**good, '_sBaseUrl': 'https://images.gamebanana.com.evil.net/img'},
            {**good, '_sFile': '../../x.jpg', '_sFile530': None, '_sFile220': None},
            {**good, '_sFile': 'payload.exe', '_sFile530': None, '_sFile220': None},
            {**good, '_sBaseUrl': 5}, 'junk', None,
        ]
        self.assertEqual(doc(*cases).images, ())
        self.assertEqual(doc(*cases, good).images, (IMAGES + '/530-90_10.jpg',))

    def test_image_and_tag_counts_are_capped(self):
        s = parse_submission(record(1, images=30, tags=['t%d' % i for i in range(60)]))
        self.assertEqual((len(s.images), len(s.tags)), (12, 12))

    def test_a_missing_preview_is_fine(self):
        d = record(1)
        d['_aPreviewMedia'] = None
        s = parse_submission(d)
        self.assertEqual((s.thumbnail, s.images), ('', ()))


class ProfileParsing(unittest.TestCase):
    def test_files_use_the_canonical_download_url_and_a_valid_md5(self):
        profile = parse_profile(profile_document())
        f = profile.files[0]
        self.assertEqual((f.id, f.name, f.size, f.md5, f.av_clean), (1801337, 'pak52_dir_ab12.zip', 7493240, '03f6e9f9e25675d14521c84e010a33c2', True))
        self.assertEqual(f.url, 'https://gamebanana.com/dl/1801337', 'the url comes from the id, never from the response')

    def test_md5_is_validated_and_lowercased(self):
        self.assertEqual(parse_file(file_entry(md5='A' * 32)).md5, 'a' * 32)
        for bad in ('abc', 'g' * 32, 'a' * 33, None, 5):
            self.assertEqual(parse_file(file_entry(md5=bad)).md5, '')

    def test_file_names_cannot_carry_paths(self):
        self.assertEqual(parse_file(file_entry(name='..\\..\\evil/x.vpk')).name, '.._.._evil_x.vpk')

    def test_antivirus_verdict(self):
        self.assertEqual([parse_file(file_entry(av=v)).av_clean for v in ('clean', 'Clean', 'infected', '', None)], [True, True, False, None, None])

    def test_bad_files_are_skipped(self):
        profile = parse_profile(profile_document(files=[file_entry(ident=0), 'junk', file_entry(ident=7)]))
        self.assertEqual([f.id for f in profile.files], [7])
        self.assertEqual(parse_profile(profile_document(files={'not': 'a list'})).files, ())

    def test_has_files_follows_the_file_list(self):
        self.assertTrue(parse_profile(profile_document()).submission.has_files)
        self.assertFalse(parse_profile(profile_document(files=[])).submission.has_files)

    def test_counts_text_and_license(self):
        profile = parse_profile(profile_document())
        self.assertEqual((profile.submission.likes, profile.submission.views, profile.submission.downloads), (3, 988, 468))
        self.assertEqual(profile.text, 'Gives a pink retexture')
        self.assertEqual(profile.license, 'CC BY-NC-ND 4.0')
        self.assertEqual(parse_profile(profile_document(license_html='All rights reserved')).license, '')
        self.assertEqual(parse_profile(profile_document(license_html=None)).license, '')

    def test_a_profile_without_a_usable_mod_is_an_error(self):
        with self.assertRaises(RepoError):
            parse_profile({'_idRow': 0})


if __name__ == '__main__':
    unittest.main()
