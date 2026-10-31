#!/usr/bin/env python3
"""Local, dependency-free Transition Cues server. Python 3.11+."""
import base64
import json
from pathlib import Path
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent
MAX_BODY = 7 * 1024 * 1024


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.images = self.directory / 'images'
        self.images.mkdir(exist_ok=True)
        self.path = self.directory / 'library.json'
        self.lock = threading.RLock()
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            'version': 1, 'places': [], 'transport': [], 'items': [], 'people': [], 'returnUrl': ''}
        # Existing libraries predate the optional bring-along category.
        self.data.setdefault('items', [])
        self.data.setdefault('people', [])
        if 'pin' in self.data:
            self.data.pop('pin')
            self.save()

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, indent=2))
        temporary.chmod(0o600)
        temporary.replace(self.path)

    def public(self):
        return {k: self.data[k] for k in ('places', 'transport', 'items', 'people', 'returnUrl')}

    def write_image(self, encoded):
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise ValueError('Please choose a JPEG, PNG or WebP image.')
        extension = None
        if raw.startswith(b'\xff\xd8\xff'):
            extension = '.jpg'
        elif raw.startswith(b'\x89PNG\r\n\x1a\n'):
            extension = '.png'
        elif raw.startswith(b'RIFF') and raw[8:12] == b'WEBP':
            extension = '.webp'
        if not extension or len(raw) > 5 * 1024 * 1024:
            raise ValueError('Use a JPEG, PNG or WebP image smaller than 5 MB.')
        filename = secrets.token_hex(12) + extension
        (self.images / filename).write_bytes(raw)
        return '/images/' + filename



class Handler(BaseHTTPRequestHandler):
    server_version = 'TransitionCues/1'

    def reply(self, status, body, mime='application/json'):
        if mime == 'application/json':
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob: data:; script-src 'self'; style-src 'self'; manifest-src 'self'; object-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == '/api/state':
            with self.server.store.lock:
                self.reply(200, self.server.store.public())
            return
        if path.startswith('/api/'):
            self.reply(404, {'error': 'Not found.'})
            return
        if path.startswith('/images/'):
            directory = self.server.store.images
            name = path.removeprefix('/images/')
        else:
            directory = self.server.web
            name = 'index.html' if path in ('/', '/manage', '/settings') else path.lstrip('/')
        target = (directory / name).resolve()
        if not target.is_relative_to(directory.resolve()) or not target.is_file():
            self.reply(404, {'error': 'Not found.'})
            return
        mime = {'.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript',
                '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml'}.get(target.suffix)
        if not mime:
            self.reply(404, {'error': 'Not found.'})
            return
        self.reply(200, target.read_bytes(), mime)

    def do_POST(self):
        # Only same-origin browser requests with a JSON content type are accepted.
        origin = self.headers.get('Origin')
        if (origin and urlsplit(origin).netloc != self.headers.get('Host')) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.reply(403, {'error': 'Please open this page directly.'})
            return
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            self.reply(415, {'error': 'JSON required.'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_BODY:
                raise ValueError('Upload too large. Choose an image smaller than 5 MB.')
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError('Invalid request.')
            with self.server.store.lock:
                self.mutate(urlsplit(self.path).path, body)
        except (ValueError, KeyError, TypeError) as exc:
            self.reply(400, {'error': str(exc) or 'Invalid request.'})
        except PermissionError as exc:
            self.reply(403, {'error': str(exc)})
        except OSError:
            self.reply(500, {'error': 'Could not save. Check data folder permissions and disk space.'})

    def mutate(self, path, body):
        store = self.server.store
        if path == '/api/items':
            kind = body.get('kind')
            name = body.get('name', '')
            if kind not in ('places', 'transport', 'items', 'people') or not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
                raise ValueError('Choose a category and a name of 1 to 60 characters.')
            item_id = secrets.token_hex(12)
            image = store.write_image(body.get('image', ''))
            original = store.write_image(body['original']) if 'original' in body else image
            item = {'id': item_id, 'name': name.strip(), 'image': image, 'originalImage': original}
            store.data[kind].append(item)
            store.save()
            self.reply(201, item)
        elif path == '/api/crop':
            kind = body.get('kind')
            if kind not in ('places', 'transport', 'items', 'people'):
                raise ValueError('Unknown category.')
            item = next((x for x in store.data[kind] if x['id'] == body.get('id')), None)
            if not item:
                raise ValueError('This picture was removed. Refresh the library.')
            if body.get('sourceImage') != item['image']:
                raise ValueError('This picture changed on another device. Refresh the library before cropping again.')
            original = item.get('originalImage', item['image'])
            image = store.write_image(body.get('image', ''))
            item.update(image=image, originalImage=original)
            store.save()
            # Existing locked journeys keep their old immutable image URLs.
            self.reply(200, item)
        elif path in ('/api/rename', '/api/transfer'):
            kind = body.get('kind')
            if kind not in ('places', 'transport', 'items', 'people'):
                raise ValueError('Unknown category.')
            item = next((x for x in store.data[kind] if x['id'] == body.get('id')), None)
            if not item:
                raise ValueError('This picture was removed or moved. Refresh the library.')
            if path == '/api/rename':
                name = body.get('name', '')
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
                    raise ValueError('Choose a name of 1 to 60 characters.')
                if body.get('sourceName') != item['name']:
                    raise ValueError('This name changed on another device. Refresh the library.')
                item['name'] = name.strip()
            else:
                target = body.get('targetKind')
                if target not in ('places', 'transport', 'items', 'people') or target == kind:
                    raise ValueError('Choose a different category.')
                store.data[kind].remove(item)
                store.data[target].append(item)
            store.save()
            # Names, categories and immutable image URLs in saved journeys are unchanged.
            self.reply(200, item)
        elif path == '/api/delete':
            kind = body.get('kind')
            if kind not in ('places', 'transport', 'items', 'people'):
                raise ValueError('Unknown category.')
            item = next((x for x in store.data[kind] if x['id'] == body.get('id')), None)
            if not item:
                raise ValueError('This picture was already removed. Refresh the page.')
            store.data[kind].remove(item)
            store.save()
            # Keep old images for active displays on other devices; documented backup/cleanup policy.
            self.reply(200, {'ok': True})
        elif path == '/api/settings':
            url = body.get('returnUrl', '')
            if not isinstance(url, str) or len(url) > 2000 or (url and (urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).netloc)):
                raise ValueError('Enter a full http:// or https:// return address.')
            store.data['returnUrl'] = url
            store.save()
            self.reply(200, {'ok': True})
        else:
            self.reply(404, {'error': 'Not found.'})


def make_server(host, port, data, web=ROOT / 'transition-cues-web'):
    server = ThreadingHTTPServer((host, port), Handler)
    server.store = Store(data)
    server.web = Path(web)
    return server


if __name__ == '__main__':
    server = make_server('0.0.0.0', 8099, Path('/data/transition-cues-data'))
    print(f'Transition Cues is listening on port {server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
