import base64
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import tempfile
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'transition_cues'))
from server import make_server, Store

PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII='


class AppTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.server = make_server('127.0.0.1', 0, self.directory.name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = ''

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, path, body=None, cookie=None, origin=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Content-Type': 'application/json', 'Cookie': self.cookie if cookie is None else cookie}
        if origin:
            headers['Origin'] = origin
        connection.request('GET' if body is None else 'POST', path, body=None if body is None else json.dumps(body), headers=headers)
        response = connection.getresponse()
        raw = response.read()
        result = json.loads(raw) if 'application/json' in response.getheader('Content-Type', '') else raw
        session = response.getheader('Set-Cookie')
        connection.close()
        return response.status, result, session

    def add(self, kind='places', name='Park'):
        status, item, _ = self.request('/api/items', {'kind': kind, 'name': name, 'image': PNG})
        self.assertEqual(status, 201)
        return item

    def test_first_launch_needs_no_setup(self):
        public = self.request('/api/state')[1]
        self.assertNotIn('pin', public)
        self.assertNotIn('setupRequired', public)
        self.add()
        self.assertEqual(Store(self.directory.name).public()['places'][0]['name'], 'Park')

    def test_install_manifest_and_apple_icons_are_served(self):
        import struct
        from urllib.parse import urlsplit
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request('GET', '/manifest.webmanifest')
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader('Content-Type'), 'application/manifest+json')
        manifest = json.loads(response.read())
        connection.close()
        self.assertEqual(self.request(urlsplit(manifest['start_url']).path)[0], 200)
        self.assertEqual(manifest['display'], 'standalone')
        for icon in manifest['icons'] + [{'src':'/apple-touch-icon.png','sizes':'180x180'}]:
            status, content, _ = self.request(icon['src'])
            self.assertEqual(status, 200, icon['src'])
            self.assertTrue(content.startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertEqual(struct.unpack('>II', content[16:24]), tuple(map(int, icon['sizes'].split('x'))))

    def test_upload_read_delete_and_persistence(self):
        item = self.add()
        self.add('transport', 'Bus')
        fresh_store = Store(self.directory.name)
        self.assertEqual(fresh_store.public()['places'][0]['name'], 'Park')
        self.assertEqual(self.request(item['image'])[0], 200)
        self.assertEqual(self.request('/api/delete', {'kind': 'places', 'id': item['id']})[0], 200)
        self.assertEqual(self.request('/api/state')[1]['places'], [])
        # Active locked displays must still be able to load their old photo.
        self.assertEqual(self.request(item['image'])[0], 200)

    def test_lan_editing_and_cross_origin_protection(self):
        self.assertEqual(self.request('/api/items', {'kind':'places','name':'Home','image':PNG}, cookie='')[0], 201)
        self.assertEqual(self.request('/api/settings', {'returnUrl':''}, origin='http://evil.example')[0], 403)

    def test_upload_validation_and_path_traversal(self):
        for image in ('invalid', base64.b64encode(b'<svg onload="alert(1)"/>').decode()):
            self.assertEqual(self.request('/api/items', {'kind':'places','name':'Bad','image':image})[0], 400)
        self.assertEqual(self.request('/images/../../server.py')[0], 404)
        self.assertEqual(self.request('/%2e%2e/server.py')[0], 404)
        self.assertEqual(self.request('/api/settings', {'returnUrl':'javascript:alert(1)'})[0], 400)
        self.assertEqual(self.request('/api/settings', {'returnUrl':'http://homeassistant.local:8123/lovelace/0'})[0], 200)

    def test_obsolete_pin_endpoints_are_removed(self):
        for endpoint in ['setup', 'unlock', 'pin']:
            self.assertEqual(self.request('/api/'+endpoint, {'pin':'1234'})[0], 404)

    def test_concurrent_uploads_do_not_lose_records(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            items = list(executor.map(lambda i: self.add(name=f'Place {i}'), range(8)))
        self.assertEqual(len({x['id'] for x in items}), 8)
        self.assertEqual(len(Store(self.directory.name).public()['places']), 8)

    def test_bring_items_storage_and_removal(self):
        # The library may contain more than four; the cap applies to each journey.
        items = [self.add('items', name) for name in ['Drink', 'Headphones', 'Coat', 'Toy', 'Bag']]
        self.assertEqual(len(Store(self.directory.name).public()['items']), 5)
        self.assertEqual(self.request('/api/delete', {'kind':'items', 'id':items[0]['id']})[0], 200)
        self.assertEqual(len(self.request('/api/state')[1]['items']), 4)
        self.assertEqual(self.request(items[0]['image'])[0], 200)

    def test_older_library_keeps_photos_settings_and_removes_pin(self):
        place = self.add()
        path = Path(self.directory.name) / 'library.json'
        legacy = json.loads(path.read_text())
        legacy['pin'] = {'salt':'old-salt', 'digest':'old-hash'}
        legacy.pop('items')
        legacy['returnUrl'] = 'http://homeassistant.local:8123/'
        path.write_text(json.dumps(legacy))
        upgraded = Store(self.directory.name)
        self.assertEqual(upgraded.public()['items'], [])
        self.assertEqual(upgraded.public()['places'], [place])
        self.assertEqual(upgraded.public()['returnUrl'], legacy['returnUrl'])
        self.assertNotIn('pin', upgraded.data)
        self.assertNotIn('pin', json.loads(path.read_text()))
        upgraded.save()
        self.assertEqual(Store(self.directory.name).public()['items'], [])

    def test_people_migration_storage_and_crop(self):
        person = self.add('people', 'Person A')
        self.assertEqual(Store(self.directory.name).public()['people'], [person])
        status, uploaded, _ = self.request('/api/items', {'kind':'people','name':'Person B','image':PNG,'original':PNG})
        self.assertEqual(status, 201)
        self.assertNotEqual(uploaded['image'], uploaded['originalImage'])
        self.assertEqual(self.request(uploaded['originalImage'])[0], 200)
        old_image = person['image']
        body = {'kind':'people', 'id':person['id'], 'sourceImage':old_image, 'image':PNG}
        self.assertEqual(self.request('/api/crop', body | {'image':'invalid'})[0], 400)
        status, cropped, _ = self.request('/api/crop', body)
        self.assertEqual(status, 200)
        self.assertEqual(cropped['id'], person['id'])
        self.assertEqual(cropped['name'], person['name'])
        self.assertNotEqual(cropped['image'], old_image)
        self.assertEqual(cropped['originalImage'], old_image)
        self.assertEqual(self.request(old_image)[0], 200)
        self.assertEqual(self.request('/api/crop', body)[0], 400)  # Stale edit on another device.
        latest = Store(self.directory.name).public()['people'][0]
        self.assertEqual(latest, cropped)
        second = self.request('/api/crop', body | {'sourceImage':cropped['image']})[1]
        self.assertEqual(second['originalImage'], old_image)
        self.assertEqual(self.request('/api/delete', {'kind':'people','id':person['id']})[0], 200)
        self.assertEqual(self.request('/api/state')[1]['people'], [uploaded])
        self.assertEqual(self.request(second['image'])[0], 200)

    def test_reorder_persists_each_category_and_rejects_stale_or_boundary_moves(self):
        for kind in ['places', 'transport', 'items', 'people']:
            first = self.add(kind, 'First')
            second = self.add(kind, 'Second')
            third = self.add(kind, 'Third')
            body = {'kind':kind, 'id':second['id'], 'direction':'left', 'neighbourId':first['id']}
            self.assertEqual(self.request('/api/reorder', body)[0], 200)
            self.assertEqual(Store(self.directory.name).public()[kind], [second, first, third])
            self.assertEqual(self.request('/api/reorder', body)[0], 400)  # Already at the left edge.
            self.assertEqual(self.request('/api/reorder', body | {'id':first['id'], 'direction':'right'})[0], 400)  # Stale neighbour.
            self.assertEqual(self.request('/api/reorder', body | {'direction':'down'})[0], 400)
            self.assertEqual(self.request('/api/reorder', body | {'kind':'unknown'})[0], 400)
            self.assertEqual(self.request('/api/reorder', body | {'id':'missing'})[0], 400)
            self.assertEqual(self.request('/api/reorder', body | {'direction':'right', 'neighbourId':first['id']})[0], 200)
            self.assertEqual(Store(self.directory.name).public()[kind], [first, second, third])
            self.assertEqual(self.request(first['image'])[0], 200)

    def test_concurrent_reorders_reject_a_conflicting_stale_move(self):
        entries = [self.add(name=name) for name in ['First','Second','Third']]
        def move(direction):
            return self.request('/api/reorder', {'kind':'places','id':entries[1]['id'],'direction':direction,'neighbourId':entries[0 if direction=='left' else 2]['id']})[0]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(move, ['left','right']))
        self.assertEqual(sorted(results), [200, 400])
        self.assertEqual(len(Store(self.directory.name).public()['places']), 3)

    def test_rename_validation_stale_edits_and_persistence(self):
        item = self.add()
        body = {'kind':'places', 'id':item['id'], 'sourceName':'Park', 'name':'  The park  '}
        for name in ['', '   ', 'x'*61, None]:
            self.assertEqual(self.request('/api/rename', body | {'name':name})[0], 400)
        self.assertEqual(self.request('/api/rename', body | {'kind':'unknown'})[0], 400)
        status, renamed, _ = self.request('/api/rename', body)
        self.assertEqual(status, 200)
        self.assertEqual(renamed, item | {'name':'The park'})
        self.assertEqual(Store(self.directory.name).public()['places'], [renamed])
        self.assertEqual(self.request('/api/rename', body | {'name':'Old edit'})[0], 400)
        self.assertEqual(self.request('/api/rename', body | {'id':'missing'})[0], 400)
        self.assertEqual(self.request(item['image'])[0], 200)

    def test_transfer_preserves_identity_and_images_in_every_category(self):
        item = self.add()
        kind = 'places'
        for target in ['transport', 'items', 'people', 'places']:
            body = {'kind':kind, 'id':item['id'], 'targetKind':target}
            for invalid in [kind, 'unknown', None]:
                self.assertEqual(self.request('/api/transfer', body | {'targetKind':invalid})[0], 400)
            status, moved, _ = self.request('/api/transfer', body)
            self.assertEqual(status, 200)
            self.assertEqual(moved, item)
            self.assertEqual(self.request('/api/transfer', body)[0], 400)
            saved = Store(self.directory.name).public()
            self.assertEqual(saved[target], [item])
            self.assertEqual(saved[kind], [])
            self.assertEqual(self.request(item['image'])[0], 200)
            kind = target

    def test_concurrent_transfers_move_a_picture_only_once(self):
        item = self.add()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda target: self.request('/api/transfer', {'kind':'places', 'id':item['id'], 'targetKind':target})[0], ['items','people']))
        self.assertEqual(sorted(results), [200, 400])
        saved = Store(self.directory.name).public()
        self.assertEqual(saved['places'], [])
        self.assertEqual(len(saved['items']) + len(saved['people']), 1)

    def test_older_library_without_people_and_crop_original(self):
        item = self.add()
        path = Path(self.directory.name) / 'library.json'
        legacy = json.loads(path.read_text())
        legacy.pop('people')
        legacy['places'][0].pop('originalImage')
        path.write_text(json.dumps(legacy))
        upgraded = Store(self.directory.name)
        self.assertEqual(upgraded.public()['people'], [])
        self.server.store = upgraded
        status, result, _ = self.request('/api/crop', {'kind':'places','id':item['id'], 'sourceImage':item['image'],'image':PNG})
        self.assertEqual(status, 200)
        self.assertEqual(result['originalImage'], item['image'])


if __name__ == '__main__':
    unittest.main()
