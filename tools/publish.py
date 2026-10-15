"""Nightly parent-page publish (ciphertext only).
usage: python3 tools/publish.py <outbox_dir> <repo_dir> <out_json>

<outbox_dir>/pubout/*.json is an ArtifactData export of the ledger's `pubout` collection.
The ledger page encrypts each student's parent-page data in the browser and stores only
{path, h, dataAt, enc:{v, sv, id, iv, ct}} there, so this script never sees keys or plain records.

Writes <repo_dir>/<path>/data.json when the stored HMAC `h` differs from the committed one,
then writes <out_json>: the settings/pubstate document the ledger reads."""
import json, glob, os, re, sys, datetime

B64 = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')
PATH = re.compile(r'^[a-z0-9]{4,40}$')
HEX = re.compile(r'^[0-9a-f]{64}$')


def load(p):
    x = json.load(open(p))
    return x['data'] if isinstance(x.get('data'), dict) and 'enc' not in x else x


def valid(d):
    e = d.get('enc') if isinstance(d, dict) else None
    return (isinstance(e, dict) and isinstance(d.get('path'), str) and PATH.match(d['path'])
            and isinstance(d.get('h'), str) and HEX.match(d['h'])
            and e.get('v') == 1 and isinstance(e.get('sv'), int) and e.get('id') == d['path']
            and isinstance(e.get('iv'), str) and B64.match(e['iv'])
            and isinstance(e.get('ct'), str) and B64.match(e['ct']))


def main(db, repo, out):
    now = datetime.datetime.now(datetime.timezone.utc)
    state = {'at': now.isoformat(), 'atKst': (now + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M'), 'students': {}}
    changed, skipped = [], []
    for f in sorted(glob.glob(os.path.join(db, 'pubout', '*.json'))):
        sid = os.path.splitext(os.path.basename(f))[0]
        d = load(f)
        if not valid(d):
            skipped.append(sid); continue
        e = d['enc']; target = os.path.join(repo, d['path'], 'data.json')
        try:
            cur = json.load(open(target))
        except Exception:
            cur = {}
        if cur.get('h') != d['h']:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            json.dump({'v': 1, 'sv': e['sv'], 'id': d['path'], 'iv': e['iv'], 'ct': e['ct'], 'h': d['h']}, open(target, 'w'))
            changed.append(d['path'])
        if isinstance(d.get('dataAt'), (int, float)):
            state['students'][sid] = {'dataAt': d['dataAt']}
    json.dump(state, open(out, 'w'), ensure_ascii=False)
    print('updated:', ', '.join(changed) if changed else 'none')
    if skipped: print('skipped (invalid outbox doc):', ', '.join(skipped))


if __name__ == '__main__':
    main(*sys.argv[1:4])
