"""Rebuild encrypted data.json for each parent page from an exported ledger DB.
usage: python3 build_data.py <db_dir> <repo_dir>
<db_dir> holds students/*.json and sessions/*.json (ArtifactData out_dir export).
Only students whose doc has pub.path and pub.key are built. Keys never leave the DB export.
A page is rewritten only when its decrypted content (ignoring generatedAt) changed."""
import json, glob, os, re, sys, base64, datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEEP = ['date','no','kind','hwRate','hwMemo','pretest','tests','progress','hw','note']
EXAM = ['title','official','raw','std','pct','cut','grade','read','lit','sel','wrong']

def clean(note):
    out = []
    for line in str(note or '').split('\n'):
        if re.search(r'상품권|공약', line): break
        out.append(line)
    return '\n'.join(out).strip()

def load(path):
    x = json.load(open(path))
    return x.get('data', x) if isinstance(x.get('data'), dict) and 'sid' not in x else x

def key_of(k): return base64.urlsafe_b64decode(k + '=' * (-len(k) % 4))

def main(db, repo):
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date().isoformat()
    sessions = [load(f) for f in glob.glob(os.path.join(db, 'sessions', '*.json'))]
    changed = []
    for f in glob.glob(os.path.join(db, 'students', '*.json')):
        sid = os.path.splitext(os.path.basename(f))[0]
        st = load(f); pub = st.get('pub') or {}
        if not (pub.get('path') and pub.get('key')): continue
        S = []
        for x in sessions:
            if x.get('sid') != sid or x.get('kind') in ('absent', 'event'): continue
            r = {k: x.get(k) for k in KEEP}; r['note'] = clean(r['note'])
            e = x.get('exam'); r['exam'] = {k: e.get(k) for k in EXAM} if e else None
            S.append(r)
        S.sort(key=lambda r: (r.get('date') or '', r.get('no') if isinstance(r.get('no'), (int, float)) else -1))
        body = {"teacher": "김용준", "student": {"display": pub.get('display') or st.get('name'), "elective": st.get('elective'), "unit": st.get('unit') or '차시'}, "sessions": S}
        key = key_of(pub['key']); out = os.path.join(repo, pub['path'], 'data.json')
        try:
            E = json.load(open(out))
            old = json.loads(AESGCM(key).decrypt(base64.b64decode(E['iv']), base64.b64decode(E['ct']), None))
            old.pop('generatedAt', None)
            old['sessions'].sort(key=lambda r: (r.get('date') or '', r.get('no') if isinstance(r.get('no'), (int, float)) else -1))
            if json.dumps(old, sort_keys=True, ensure_ascii=False) == json.dumps(body, sort_keys=True, ensure_ascii=False): continue
        except Exception: pass
        D = {"generatedAt": today, **body}
        iv = os.urandom(12); ct = AESGCM(key).encrypt(iv, json.dumps(D, ensure_ascii=False).encode(), None)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"v": 1, "id": pub['path'], "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}, open(out, 'w'))
        changed.append(pub['path'])
    print("updated:", ", ".join(changed) if changed else "none")

if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
