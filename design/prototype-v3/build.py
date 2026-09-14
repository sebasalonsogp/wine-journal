"""Build the connected design prototype; no application framework or backend."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
VIZ = Path('C:/Users/Sebas/.codex/visualizations/2026/09/14/01a09d4f-02c9-7851-a2c7-5ff22969fde9')
LUCIDE = Path('C:/Users/Sebas/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/lucide')
baseline = HERE / 'baseline-v2.html'
if not baseline.exists():
    baseline.write_bytes((VIZ / 'wine-journal-second-walkthrough.html').read_bytes())
source = baseline.read_text(encoding='utf-8').replace('wine-journal-v2', 'wine-journal-v3')
parts = re.split(r'^// @(replace \w+|extra)\s*$', (HERE / 'refinements.js').read_text(encoding='utf-8'), flags=re.M)
blocks = dict(zip(parts[1::2], parts[2::2]))
for key, value in blocks.items():
    if not key.startswith('replace '):
        continue
    name = key.split()[1]
    pattern = rf'  function {name}\(.*?(?=\n  (?:function |let |const |root\.addEventListener)|\Z)'
    source, count = re.subn(pattern, lambda _: value.strip('\n')+'\n', source, count=1, flags=re.S)
    assert count == 1, name

insertion = source.index("  root.addEventListener('click'")
source = source[:insertion] + blocks['extra'] + '\n' + source[insertion:]
old_files = "if(el.dataset.files){const picked=Array.from(el.files||[]).map(f=>({name:f.name,type:f.type.startsWith('video/')?'video':'photo'}));if(el.dataset.files==='entry')draft.media=draft.media.concat(picked);else{const o=occasion(selectedOccasion);o.media=o.media.concat(picked);}render();}"
assert old_files in source
source = source.replace(old_files, 'if(el.dataset.files)loadMemories(el);')
source = source.replace("ratings[selectedWine].push({value:v,date:TODAY});", "ratings[selectedWine].push({value:v,date:TODAY,time:new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})});")
source = source.replace("function submitPreview(form){if(form&&form.reportValidity())", "function submitPreview(form){if(!mediaBusy&&form&&form.reportValidity())")
source = source.replace("function clearCapture(){draft=null;", "function clearCapture(){mediaError='';draft=null;")
source = source.replace("function startEntry(id,oId=''){selectedWine=id;", "function startEntry(id,oId=''){mediaError='';selectedWine=id;")
source = source.replace("else if(a==='edit-entry'){draft=", "else if(a==='edit-entry'){mediaError='';draft=")
source = source.replace('The photo does not identify the wine automatically.', 'This cover photo stays with your personal wine record.')
source = source.replace('</style>', '\n'+(HERE / 'refinements.css').read_text(encoding='utf-8')+'\n</style>', 1)

assert len(source.encode('utf-8')) < 1_000_000
assert '<!doctype' not in source.lower()
assert source.count("let browseTab=") == 1
assert source.count('const copy=') == 1
assert source.count("function winePage(") == 1
assert '\ufffd' not in source
inline = VIZ / 'wine-journal-connected-walkthrough.html'
inline.write_text(source, encoding='utf-8')
(HERE / 'fragment.html').write_text(source, encoding='utf-8')
(HERE / 'script-check.js').write_text(source.split('<script>', 1)[1].split('</script>', 1)[0], encoding='utf-8')
icons = (LUCIDE / 'dist/umd/lucide.min.js').read_text(encoding='utf-8')
assert '</script' not in icons.lower()
head = (HERE / 'standalone-head.html').read_text(encoding='utf-8')
(HERE / 'walkthrough.html').write_text(head+'\n<script>\n'+icons+'\n</script>\n'+source+'\n</body>\n</html>\n', encoding='utf-8')
(HERE / 'THIRD-PARTY-NOTICES.txt').write_text('Lucide 1.8.0 — https://lucide.dev\n\n'+(LUCIDE / 'LICENSE').read_text(encoding='utf-8'), encoding='utf-8')
print(f'Created inline and standalone walkthroughs. Fragment: {len(source.encode()):,} bytes.')
