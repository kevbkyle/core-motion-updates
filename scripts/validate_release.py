#!/usr/bin/env python3
"""Validate a Core Motion in-app update archive and write its release feed."""
import argparse, hashlib, json, re, sys, zipfile
from pathlib import Path
ALLOWED = {'static/index.html','static/app.js','server.py','furnace_bridge.py','updater_api.py','launcher.py','core_motion_version.json'}
def verify(path):
    if not path.is_file() or path.suffix.lower() != '.zip' or path.stat().st_size > 32*1024*1024:
        raise ValueError('Expected update ZIP <=32 MB')
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names)>30 or 'coremotion-package.json' not in names: raise ValueError('Invalid ZIP entries')
        m=json.loads(z.read('coremotion-package.json'))
        if m.get('schema')!='coremotion-package-v1': raise ValueError('Wrong update format')
        for field in ('version','min_version'):
            if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?',str(m.get(field,''))): raise ValueError('Invalid '+field)
        paths=set()
        for f in m.get('files',[]):
            name=f['path']
            if name not in ALLOWED or name in paths: raise ValueError('Unsafe or duplicate path: '+name)
            paths.add(name)
            if z.getinfo(name).file_size>4*1024*1024: raise ValueError('Oversized file')
            if hashlib.sha256(z.read(name)).hexdigest()!=f['sha256'].lower(): raise ValueError('Checksum mismatch '+name)
        if set(names)!=paths|{'coremotion-package.json'} or not {'static/app.js','static/index.html'}<=paths:
            raise ValueError('Missing/extra files, or missing complete main interface')
        return m
p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--feed-output',type=Path);p.add_argument('--package-url');a=p.parse_args()
try:
    m=verify(a.package)
    feed={'schema':'coremotion-feed-v1','version':m['version'],'notes':str(m.get('notes','Core Motion update'))[:1800], 'package_url':a.package_url or '', 'sha256':hashlib.sha256(a.package.read_bytes()).hexdigest()}
    if a.feed_output:
        if not a.package_url or not a.package_url.startswith('https://github.com/kevbkyle/core-motion-updates/releases/download/'):
            raise ValueError('Use your official GitHub release URL')
        a.feed_output.write_text(json.dumps(feed,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(feed))
except (OSError,ValueError,KeyError,zipfile.BadZipFile) as e:
    print('Release validation failed:',e,file=sys.stderr);sys.exit(1)
