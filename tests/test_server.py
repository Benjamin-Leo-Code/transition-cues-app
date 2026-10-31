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

    def setup_pin(self):
        status, _, cookie = self.request('/api/setup', {'pin': '1234'})
        self.assertEqual(status, 200)
        self.cookie = cookie.split(';')[0]

    def add(self, kind='places', name='Park'):
        status, item, _ = self.request('/api/items', {'kind': kind, 'name': name, 'image': PNG})
        self.assertEqual(status, 201)
        return item

    def test_first_launch_and_single_setup(self):
        self.assertTrue(self.request('/api/state')[1]['setupRequired'])
        self.assertEqual(self.request('/api/setup', {'pin': 'abc'})[0], 400)
        self.setup_pin()
        self.assertEqual(self.request('/api/setup', {'pin': '9999'})[0], 403)
        public = self.request('/api/state')[1]
        self.assertNotIn('pin', public)
        self.assertFalse(public['setupRequired'])
        persisted = json.loads((Path(self.directory.name) / 'library.json').read_text())
        self.assertNotIn('1234', json.dumps(persisted['pin']))
        self.assertEqual(persisted['version'], 1)

    def test_upload_read_delete_and_persistence(self):
        self.setup_pin()
        item = self.add()
        self.add('transport', 'Bus')
        fresh_store = Store(self.directory.name)
        self.assertEqual(fresh_store.public()['places'][0]['name'], 'Park')
        self.assertEqual(self.request(item['image'])[0], 200)
        self.assertEqual(self.request('/api/delete', {'kind': 'places', 'id': item['id']})[0], 200)
        self.assertEqual(self.request('/api/state')[1]['places'], [])
        # Active locked displays must still be able to load their old photo.
        self.assertEqual(self.request(item['image'])[0], 200)

    def test_auth_and_cross_origin(self):
        self.setup_pin()
        self.assertEqual(self.request('/api/items', {'kind':'places','name':'Home','image':PNG}, cookie='')[0], 403)
        self.assertEqual(self.request('/api/settings', {'returnUrl':''}, origin='http://evil.example')[0], 403)
        self.assertEqual(self.request('/api/unlock', {'pin':'wrong'}, cookie='')[0], 403)
        status, _, cookie = self.request('/api/unlock', {'pin':'1234'}, cookie='')
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)

    def test_pin_change_revokes_sessions(self):
        self.setup_pin()
        old_cookie = self.cookie
        status, _, cookie = self.request('/api/pin', {'currentPin':'1234','pin':'5678'})
        self.assertEqual(status, 200)
        self.assertEqual(self.request('/api/settings', {'returnUrl':''}, cookie=old_cookie)[0], 403)
        self.cookie = cookie.split(';')[0]
        self.assertEqual(self.request('/api/unlock', {'pin':'1234'})[0], 403)
        self.assertEqual(self.request('/api/unlock', {'pin':'5678'})[0], 200)

    def test_upload_validation_and_path_traversal(self):
        self.setup_pin()
        for image in ('invalid', base64.b64encode(b'<svg onload="alert(1)"/>').decode()):
            self.assertEqual(self.request('/api/items', {'kind':'places','name':'Bad','image':image})[0], 400)
        self.assertEqual(self.request('/images/../../server.py')[0], 404)
        self.assertEqual(self.request('/%2e%2e/server.py')[0], 404)
        self.assertEqual(self.request('/api/settings', {'returnUrl':'javascript:alert(1)'})[0], 400)
        self.assertEqual(self.request('/api/settings', {'returnUrl':'http://homeassistant.local:8123/lovelace/0'})[0], 200)

    def test_brute_force_is_limited(self):
        self.setup_pin()
        for _ in range(5):
            self.assertEqual(self.request('/api/unlock', {'pin':'0000'})[0], 403)
        status, error, _ = self.request('/api/unlock', {'pin':'1234'})
        self.assertEqual(status, 403)
        self.assertIn('Wait one minute', error['error'])

    def test_concurrent_uploads_do_not_lose_records(self):
        self.setup_pin()
        with ThreadPoolExecutor(max_workers=4) as executor:
            items = list(executor.map(lambda i: self.add(name=f'Place {i}'), range(8)))
        self.assertEqual(len({x['id'] for x in items}), 8)
        self.assertEqual(len(Store(self.directory.name).public()['places']), 8)

    def test_bring_items_storage_auth_and_removal(self):
        self.setup_pin()
        self.assertEqual(self.request('/api/items', {'kind':'items', 'name':'Drink', 'image':PNG}, cookie='')[0], 403)
        # The library may contain more than four; the cap applies to each journey.
        items = [self.add('items', name) for name in ['Drink', 'Headphones', 'Coat', 'Toy', 'Bag']]
        self.assertEqual(len(Store(self.directory.name).public()['items']), 5)
        self.assertEqual(self.request('/api/delete', {'kind':'items', 'id':items[0]['id']}, cookie='')[0], 403)
        self.assertEqual(self.request('/api/delete', {'kind':'items', 'id':items[0]['id']})[0], 200)
        self.assertEqual(len(self.request('/api/state')[1]['items']), 4)
        self.assertEqual(self.request(items[0]['image'])[0], 200)

    def test_older_library_keeps_photos_settings_and_pin(self):
        self.setup_pin()
        place = self.add()
        path = Path(self.directory.name) / 'library.json'
        legacy = json.loads(path.read_text())
        legacy.pop('items')
        legacy['returnUrl'] = 'http://homeassistant.local:8123/'
        path.write_text(json.dumps(legacy))
        upgraded = Store(self.directory.name)
        self.assertEqual(upgraded.public()['items'], [])
        self.assertEqual(upgraded.public()['places'], [place])
        self.assertEqual(upgraded.public()['returnUrl'], legacy['returnUrl'])
        upgraded.verify('1234', 'test')
        upgraded.save()
        self.assertEqual(Store(self.directory.name).public()['items'], [])

    def test_people_migration_storage_and_crop(self):
        self.setup_pin()
        person = self.add('people', 'Person A')
        self.assertEqual(Store(self.directory.name).public()['people'], [person])
        status, uploaded, _ = self.request('/api/items', {'kind':'people','name':'Person B','image':PNG,'original':PNG})
        self.assertEqual(status, 201)
        self.assertNotEqual(uploaded['image'], uploaded['originalImage'])
        self.assertEqual(self.request(uploaded['originalImage'])[0], 200)
        old_image = person['image']
        body = {'kind':'people', 'id':person['id'], 'sourceImage':old_image, 'image':PNG}
        self.assertEqual(self.request('/api/crop', body, cookie='')[0], 403)
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

    def test_older_library_without_people_and_crop_original(self):
        self.setup_pin()
        item = self.add()
        path = Path(self.directory.name) / 'library.json'
        legacy = json.loads(path.read_text())
        legacy.pop('people')
        legacy['places'][0].pop('originalImage')
        path.write_text(json.dumps(legacy))
        upgraded = Store(self.directory.name)
        self.assertEqual(upgraded.public()['people'], [])
        upgraded.verify('1234', 'migration')
        self.server.store = upgraded
        self.cookie = self.request('/api/unlock', {'pin':'1234'})[2].split(';')[0]
        status, result, _ = self.request('/api/crop', {'kind':'places','id':item['id'], 'sourceImage':item['image'],'image':PNG})
        self.assertEqual(status, 200)
        self.assertEqual(result['originalImage'], item['image'])


if __name__ == '__main__':
    unittest.main()
