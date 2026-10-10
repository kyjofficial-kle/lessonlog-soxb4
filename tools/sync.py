"""Nightly parent-page sync.
usage: python3 tools/sync.py <db_dir> <repo_dir> <out_json>
Rebuilds every parent page's data.json from an ArtifactData export (via build_data.py),
then writes <out_json>: the settings/pubstate document the ledger reads to show
which students still have changes that are not on their parent page."""
import json, glob, os, sys, datetime, subprocess
db, repo, out = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
res = subprocess.run([sys.executable, os.path.join(here, 'build_data.py'), db, repo], capture_output=True, text=True)
print(res.stdout.strip() or '(no output)'); 
if res.returncode: print(res.stderr); sys.exit(1)
load = lambda p: json.load(open(p))
sess = [load(f) for f in glob.glob(os.path.join(db, 'sessions', '*.json'))]
now = datetime.datetime.now(datetime.timezone.utc)
state = {'at': now.isoformat(), 'atKst': (now + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M'), 'students': {}}
for f in glob.glob(os.path.join(db, 'students', '*.json')):
    sid = os.path.splitext(os.path.basename(f))[0]; st = load(f)
    if not (st.get('pub') or {}).get('path'): continue
    ts = [st.get('updatedAt') or 0] + [x.get('updatedAt') or 0 for x in sess if x.get('sid') == sid]
    state['students'][sid] = {'dataAt': max(t for t in ts if isinstance(t, (int, float)))}
json.dump(state, open(out, 'w'), ensure_ascii=False)
print('pubstate', json.dumps(state, ensure_ascii=False))
