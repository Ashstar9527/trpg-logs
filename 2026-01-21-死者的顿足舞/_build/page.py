"""整理版.md + cards.json -> index.html（1920 年代哈莱姆爵士俱乐部节目单风格）。用法：python3 page.py .."""
import re, html, os, sys, json, glob

DIR = sys.argv[1] if len(sys.argv) > 1 else '..'
HERE = os.path.dirname(os.path.abspath(__file__))
md = open(os.path.join(DIR, '整理版.md'), encoding='utf-8').read()
cards = json.load(open(os.path.join(HERE, 'cards.json'), encoding='utf-8'))
KP = '菠萝大王🍍'
PCS = [c['key'] for c in cards]
SLUG = dict(zip(PCS, ['eugene', 'claude', 'vincent', 'tinos', 'julian', 'theodore']))
PLAYER = {'西奥多': '莫伊拉'}            # 西奥多的卡沿用了尤金的模板，姓名、玩家栏不准
OCC = {'尤金': '联邦探员', '克洛德': '律师', '文森特': '走私者', '蒂诺丝': '赌徒', '朱利安': '酒保', '西奥多': '私家侦探'}


def esc(t):
    return html.escape(str(t), quote=False)


def speech(t):
    """玩家发言：引号内是台词，引号外是动作。"""
    out = re.sub(r'“[^“”]*”', lambda m: f'<span class="q">{m.group(0)}</span>', esc(t))
    return out


# ---------------------------------------------------------------- 解析
sets, cur_set, cur_tr = [], None, None
sp, buf = None, []


def flush():
    global buf
    if sp and buf:
        cur_tr['ev'].append(('say', sp, list(buf)))
    buf = []


for line in md.split('\n'):
    s = line.strip()
    if s.startswith('## '):
        flush(); sp = None
        cur_set = dict(title=s[3:], tracks=[]); sets.append(cur_set); continue
    if s.startswith('### '):
        flush(); sp = None
        no, cn, en = s[4:].split('　', 2)
        cur_tr = dict(no=no, cn=cn, en=en, ev=[]); cur_set['tracks'].append(cur_tr); continue
    if cur_tr is None or not s or s == '---':
        continue
    if m := re.fullmatch(r'\*\*(.+?)\*\*', s):
        flush(); sp = m.group(1); continue
    if s.startswith('`') and s.endswith('`'):
        flush(); sp = None
        if cur_tr['ev'] and cur_tr['ev'][-1][0] == 'dice':
            cur_tr['ev'][-1][1].append(s[1:-1])
        else:
            cur_tr['ev'].append(('dice', [s[1:-1]]))
        continue
    if m := re.fullmatch(r'〔图：(.+?)　(\S+) (\S+) 贴出.*（(\w{8})）〕', s):
        flush(); sp = None
        cur_tr['ev'].append(('img', m.group(1), m.group(2), m.group(4))); continue
    buf.append(s)
flush()

# ---------------------------------------------------------------- 渲染
RES = re.compile(r'(大成功|极难成功|困难成功|大失败|成功|失败)')
KIND = {'大成功': 'crit', '极难成功': 'ok', '困难成功': 'ok', '成功': 'ok', '失败': 'fail', '大失败': 'fumble'}


def r_dice(lines):
    chips = []
    for d in lines:
        b = [x for x in d.split('　') if x]
        who, skill, roll = b[0], b[1], b[2]
        res = b[3] if len(b) > 3 else ''
        extra = '　'.join(b[4:])
        cls = KIND.get(res, '')
        chips.append(f'<li class="roll {cls} pc-{SLUG.get(who, "x")}"><span class="r-who">{esc(who)}</span>'
                     f'<span class="r-skill">{esc(skill)}</span><span class="r-num">{esc(roll)}</span>'
                     f'<span class="r-res">{esc(res)}</span>'
                     + (f'<span class="r-san">{esc(extra)}</span>' if extra else '') + '</li>')
    return f'<ul class="rolls" aria-label="检定">{"".join(chips)}</ul>'


def r_img(cap, who, g):
    hit = glob.glob(os.path.join(DIR, 'assets', g.lower() + '.*'))
    if not hit:
        return ''                                   # 原图缺失：网页上先不占位
    src = 'assets/' + os.path.basename(hit[0])
    note = '　蒂诺丝用 AI 生成' if 'AI' in cap else ''
    return (f'<figure class="photo"><a href="{src}" target="_blank" rel="noopener"><img src="{src}" alt="{esc(cap)}" loading="lazy" decoding="async"></a>'
            f'<figcaption>{esc(cap.replace("AI 生成的", ""))}{note}</figcaption></figure>')


def r_say(name, ps):
    if name == KP:
        out = []
        for p in ps:
            if p.startswith('【END'):
                out.append(f'<p class="end">{esc(p)}</p>')
            else:
                out.append(f'<p>{esc(p)}</p>')
        return f'<div class="narr">{"".join(out)}</div>'
    slug = SLUG.get(name, 'x')
    return (f'<div class="line pc-{slug}"><div class="who">{esc(name)}</div>'
            + ''.join(f'<p>{speech(p)}</p>' for p in ps) + '</div>')


body, toc = [], []
for si, st in enumerate(sets, 1):
    night, date = st['title'].split('　', 1)
    sid = f'set{si}'
    toc.append(f'<li class="toc-set"><a href="#{sid}">{"Set One" if si == 1 else "Set Two"}<span>{esc(night)} · {esc(date)}</span></a></li>')
    parts = []
    for tr in st['tracks']:
        tid = f'track{tr["no"]}'
        toc.append(f'<li><a href="#{tid}"><span class="t-no">{tr["no"]}</span><span class="t-cn">{esc(tr["cn"])}</span>'
                   f'<span class="t-en">{esc(tr["en"])}</span></a></li>')
        out = []
        for e in tr['ev']:
            if e[0] == 'say':
                out.append(r_say(e[1], e[2]))
            elif e[0] == 'dice':
                out.append(r_dice(e[1]))
            elif e[0] == 'img':
                out.append(r_img(*e[1:]))
        parts.append(f'<section class="track" id="{tid}" aria-labelledby="{tid}-h">'
                     f'<h3 id="{tid}-h"><span class="t-no">No. {tr["no"]}</span>{esc(tr["cn"])}<span class="t-en">{esc(tr["en"])}</span></h3>'
                     f'{"".join(out)}</section>')
    body.append(f'<section class="set" id="{sid}" aria-labelledby="{sid}-h">'
                f'<header class="set-head"><div class="set-en">{"Set One" if si == 1 else "Set Two"}</div>'
                f'<h2 id="{sid}-h">{esc(night)}</h2><div class="set-date">{esc(date)}</div></header>'
                f'{"".join(parts)}</section>')
    if si == 1:
        body.append('<div class="interlude" role="separator" aria-label="中场休息"><span>Intermission</span>中场休息 · 一周后</div>')

# ---------------------------------------------------------------- 乐手（调查员）
band = []
for c in cards:
    n = c['key']
    sm = (c['summary'] or '').split('，')
    age = next((x for x in sm if x.endswith('岁')), '')
    sex = sm[1] if len(sm) > 1 else ''
    full = '尤金·兰开斯特' if n == '尤金' else '朱利安·韦斯特' if n == '朱利安' else n
    player = PLAYER.get(n, c['player'])
    bg = c['bg']
    stats = ''.join(f'<div><b>{v}</b><span>{k}</span></div>' for k, v in c['attr'].items())
    der = ''.join(f'<span>{k} <b>{esc(v)}</b></span>' for k, v in c['derived'].items() if v)
    skills = ''.join(f'<span>{esc(k)}<b>{v}</b></span>' for k, v in c['skills'] if v >= 40)
    weap = '；'.join(f'{w["name"].strip()}（{w["skill"]} {w["val"]}，{w["dmg"]}）' for w in c['weapons'])
    kit = ''.join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k, v in bg.items() if k not in ('描述',))
    story = ''.join(f'<p>{esc(p)}</p>' for p in (c['story'] or '').split('\n') if p.strip())
    you = '<span class="you">我的调查员</span>' if n == '尤金' else ''
    band.append(f'''<article class="card pc-{SLUG[n]}" id="pc-{SLUG[n]}" aria-labelledby="pc-{SLUG[n]}-h">
  <div class="card-top"><span class="instr">Featuring</span>{you}</div>
  <h3 id="pc-{SLUG[n]}-h">{esc(full)}</h3>
  <div class="occ">{OCC[n]} · {esc(age)} · {esc(sex)}<span class="pl">玩家 {esc(player)}</span></div>
  <p class="desc">{esc(bg.get("描述", ""))}</p>
  <details>
    <summary>人物卡</summary>
    <div class="stats">{stats}</div>
    <div class="derived">{der}</div>
    <div class="skills">{skills}</div>
    {f'<p class="weap"><b>武器</b>{esc(weap)}</p>' if weap else ''}
    <p class="weap"><b>随身</b>{esc("、".join(c["items"]))}</p>
    <table class="kit">{kit}</table>
    <div class="story">{story}</div>
  </details>
</article>''')

tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
page = tpl.replace('{{BAND}}', '\n'.join(band)).replace('{{SETS}}', '\n'.join(body)).replace('{{TOC}}', ''.join(toc))
open(os.path.join(DIR, 'index.html'), 'w', encoding='utf-8').write(page)
print('index.html', len(page), 'chars |', sum(len(s['tracks']) for s in sets), 'tracks')
