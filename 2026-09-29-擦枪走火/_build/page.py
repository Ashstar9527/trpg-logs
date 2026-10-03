"""整理版.md -> index.html（FBI 证人陈述档案风格）。用法：python3 page.py .."""
import re, html, os, sys

DIR = sys.argv[1] if len(sys.argv) > 1 else '..'
md = open(os.path.join(DIR, '整理版.md'), encoding='utf-8').read()
PC, KP = '艾迪安·多雷', 'qwi'
CN = '一二三四五六七八九十'
MONTH = {'九月': 9, '十月': 10}


def esc(t):
    return html.escape(t, quote=False)


def inline(t):
    return re.sub(r'\*\*(.+?)\*\*', r'<em class="kp-em">\1</em>', esc(t))


def P(ps):
    return ''.join(f'<p>{inline(p)}</p>' for p in ps)


def cn_day(s):
    if len(s) == 1:
        return CN.index(s) + 1
    if s[0] == '十':
        return 10 + (CN.index(s[1]) + 1 if len(s) > 1 else 0)
    return (CN.index(s[0]) + 1) * 10 + (CN.index(s[2]) + 1 if len(s) > 2 else 0)


# ---------------------------------------------------------------- 解析
body = md.split('\n---\n', 1)[1]
parts = []
for chunk in re.split(r'\n(?=## )', body.strip()):
    L = chunk.split('\n')
    title = L[0][3:].strip()
    m = re.search(r'　([九十]月)([一二三四五六七八九十]+)日$', title)
    date = f'2026.{MONTH[m.group(1)]:02d}.{cn_day(m.group(2)):02d}' if m else ''
    name = re.sub(r'　[九十]月.*$', '', title)
    ev, sp, buf, i = [], None, [], 0

    def flush():
        global buf
        if sp and buf:
            ev.append(('say', sp, list(buf)))
        buf.clear()

    while i < len(L):
        s = L[i].strip(); i += 1
        if not s:
            continue
        if mm := re.fullmatch(r'\*\*(.+?)\*\*', s):
            flush(); sp = mm.group(1); continue
        if s.startswith('`') and s.endswith('`'):
            flush(); sp = None; ev.append(('dice', s[1:-1])); continue
        if mm := re.match(r'::: 文件　(.+)', s):
            flush(); sp = None
            txt = []
            while L[i].strip() != ':::':
                txt.append(L[i]); i += 1
            i += 1
            ev.append(('doc', mm.group(1), [p for p in '\n'.join(txt).split('\n') if p.strip()])); continue
        if mm := re.fullmatch(r'!\[(.+?)\]\((.+?)\)', s):
            flush(); sp = None; ev.append(('fig', mm.group(1), mm.group(2))); continue
        buf.append(s)
    flush()
    parts.append(dict(name=name, date=date, ev=ev))

# ---------------------------------------------------------------- 渲染
EXHIBIT = iter('ABCDEFGHIJ')
RES = re.compile(r'(大成功|极难成功|困难成功|大失败|成功|失败)$')


def r_dice(d):
    bits = [b for b in d.split('　') if b]
    m = RES.search(d)
    res = m.group(1) if m else ''
    body = '　'.join(bits[1:])
    if res:
        body = body[:-len(res)].rstrip('　 ')
    kind = {'大成功': 'crit', '大失败': 'fumble', '失败': 'fail'}.get(res, 'ok' if res else '')
    return (f'<div class="chk {kind}"><span class="chk-tag">检定</span><span class="chk-body">{esc(body)}</span>'
            + (f'<span class="chk-res">{res}</span>' if res else '') + '</div>')


def r_fig(cap, src):
    x = next(EXHIBIT)
    bare = ' bare' if any(k in src for k in ('ethan', 'smith-yang')) else ''   # 立绘自带拍立得相框
    return (f'<figure class="exhibit{bare}"><div class="clip" aria-hidden="true"></div>'
            f'<a href="{src}" target="_blank" rel="noopener"><img src="{src}" alt="{esc(cap)}" loading="lazy" decoding="async"></a>'
            f'<figcaption><span class="ex-no">证物 {x}</span>{esc(cap)}</figcaption></figure>')


def r_doc(title, ps):
    head, rest = ps[0], ps[1:]
    return (f'<figure class="clipping" aria-label="剪报：{esc(title)}"><div class="np-mast">{esc(title)}</div>'
            f'<div class="np-head">{esc(head)}</div><div class="np-body">{P(rest)}</div>'
            '<figcaption>书房书桌上的报纸</figcaption></figure>')


def r_say(name, ps):
    if name == PC:
        return f'<div class="wit"><div class="wit-name">证人　艾迪安·多雷</div>{P(ps)}</div>'
    return f'<div class="narr">{P(ps)}</div>'


sheets, toc = [], []
for n, part in enumerate(parts, 1):
    num, _, sub = part['name'].partition(' · ')
    out = []
    for e in part['ev']:
        if e[0] == 'say':
            out.append(r_say(e[1], e[2]))
        elif e[0] == 'dice':
            out.append(r_dice(e[1]))
        elif e[0] == 'fig':
            out.append(r_fig(e[1], e[2]))
        elif e[0] == 'doc':
            out.append(r_doc(e[1], e[2]))
    pid = f'part{n}'
    toc.append(f'<li><a href="#{pid}"><span>第 {n} 部分</span>{esc(sub)}</a></li>')
    sheets.append(
        f'<section class="sheet" id="{pid}" aria-labelledby="{pid}-h">'
        f'<header class="sheet-head"><div class="form">FD-302　证人陈述　续页 {n}/3</div>'
        f'<div class="sheet-date">记录日期　{part["date"]}</div></header>'
        f'<h2 id="{pid}-h"><span class="h-no">陈述 · 第 {n} 部分</span>{esc(sub)}</h2>'
        f'<div class="statement">{"".join(out)}</div>'
        f'<div class="page-no" aria-hidden="true">— {n + 2} —</div></section>')

tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html'), encoding='utf-8').read()
page = tpl.replace('{{SHEETS}}', '\n'.join(sheets)).replace('{{TOC}}', ''.join(toc))
open(os.path.join(DIR, 'index.html'), 'w', encoding='utf-8').write(page)
print('index.html', len(page), 'chars |', len(parts), 'parts')
