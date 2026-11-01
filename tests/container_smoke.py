"""Check the built add-on with an isolated /data volume; never deploys to HA."""
import argparse
import json
import os
import subprocess
import uuid


def run(image):
    name = 'transition-cues-check-' + uuid.uuid4().hex[:12]
    volume = name + '-data'
    environment = os.environ.copy()
    for key in ['DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH']:
        environment.pop(key, None)

    def docker(*args, source=None, check=True):
        result = subprocess.run(['docker', '--host=unix:///var/run/docker.sock', *args], input=source,
                                text=True, capture_output=True, env=environment, check=check)
        return result.stdout.strip()

    def start():
        docker('run', '-d', '--name', name, '--network', 'none', '--mount',
               f'type=volume,src={volume},dst=/data', image)

    probe = '''import json,time,urllib.request,urllib.error
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def request(path,body=None,cookie=''):
 data=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request('http://127.0.0.1:8099'+path,data=data,headers={'Content-Type':'application/json','Cookie':cookie})
 return opener.open(req)
for attempt in range(40):
 try:
  state=json.load(request('/api/state'))
  break
 except OSError:
  time.sleep(.25)
else:
 raise RuntimeError('Add-on did not start')
'''
    try:
        docker('volume', 'create', volume)
        start()
        first = probe + '''assert 'setupRequired' not in state
cookie=''
photo='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII='
for kind,name in [('places','Home'),('items','Drink'),('people','Person A')]:
 record=json.load(request('/api/items',{'kind':kind,'name':name,'image':photo},cookie))
 if kind=='people':
  json.load(request('/api/crop',{'kind':kind,'id':record['id'],'sourceImage':record['image'],'image':photo},cookie))
assert Path('/data/transition-cues-data/library.json').is_file()
assert len(list(Path('/data/transition-cues-data/images').iterdir()))==4
try:
 request('/data/transition-cues-data/library.json')
 raise AssertionError('Private data exposed')
except urllib.error.HTTPError as error:
 assert error.code==404
print('Initial setup and uploads saved in private /data')
'''
        print(docker('exec', '-i', name, 'python', '-', source=first))
        docker('stop', '-t', '2', name)
        docker('rm', name)
        start()  # A replacement container must use the same private data volume.
        second = probe + '''assert 'setupRequired' not in state
assert state['places'][0]['name']=='Home'
assert state['items'][0]['name']=='Drink'
assert state['people'][0]['name']=='Person A'
assert state['people'][0]['originalImage']!=state['people'][0]['image']
assert request(state['items'][0]['image']).status==200
assert request('/').status==200
assert request('/app.js').status==200
print('PASS: replacement container preserves library and images in /data')
'''
        print(docker('exec', '-i', name, 'python', '-', source=second))
    except subprocess.CalledProcessError as error:
        raise RuntimeError(error.stderr or error.stdout) from error
    finally:
        docker('rm', '-f', name, check=False)
        docker('volume', 'rm', volume, check=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='transition-cues-ha-check:1.0.19')
    run(parser.parse_args().image)
