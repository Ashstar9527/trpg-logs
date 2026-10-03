"""整理《擦枪走火》：QQ 机器人框架导出的 txt -> 整理版.md + 删改记录。"""
import re, json, os, sys
from collections import Counter, defaultdict


def punct(t):
    """引号方向按出现顺序交替；省略号统一为 ……；去掉标点前后多余的空格。"""
    out, k = [], 0
    for ch in t:
        if ch in '“”"':
            out.append('“' if k % 2 == 0 else '”'); k += 1
        else:
            out.append(ch)
    t = ''.join(out)
    t = re.sub(r'\.{2,}|。{3,}|…(?!…)', '……', t)
    t = re.sub(r'……+', '……', t)
    t = re.sub(r'\s+([。，、；：！？」』”）】])', r'\1', t)
    t = re.sub(r'([「『“（【])\s+', r'\1', t)
    return t

S = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
msgs = json.load(open(sys.argv[2] if len(sys.argv) > 2 else f'{S}/msgs.json', encoding='utf-8'))

KP, PC, BOT = 'qwi', '艾迪安·多雷', '芯傅'
RESULT = r'(大成功|极难成功|困难成功|大失败|成功|失败)'
PAREN = re.compile(r'^\s*[（(].*[）)]\s*$', re.S)
TAIL = re.compile(r'\s*[（(][^（）()]{0,40}[）)]\s*$')
CQ_DROP = re.compile(r'\[CQ:(?:reply|at|face)[^\]]*\]|\[CQ:image,file=file:[^\]]*\]')
CQ_IMG = re.compile(r'\[CQ:image,file=https[^\]]*\]')
CQ_FILE = re.compile(r'\[CQ:file,[^\]]*?\bfile=([^,\]]+)[^\]]*\]')
FILE_CAP = {'雕像.jpg': '路边的岩石雕塑', '地图.jpg': '公路与木屋', '伊森.png': '伊森·威廉姆斯', '杨.png': '史密斯·杨', '新闻.jpg': '书桌上的报纸'}
# 团里展示过的图，取自模组 PDF（模组《擦枪走火》，作者 逆光の白羊）
FILE_SRC = {'雕像.jpg': 'assets/statue.jpg', '地图.jpg': 'assets/road-map.jpg', '伊森.png': 'assets/ethan.jpg', '杨.png': 'assets/smith-yang.jpg'}
FILE_DOC = {'新闻.jpg': ('Arizona Morning News', '亚利桑那历史博物馆发生离奇案件！\n\n一具珍贵的木乃伊于昨夜神秘消失。监控显示，凌晨 3 点，木乃伊展室警报骤响，但抵达现场的安保仅见空置的展示柜。警方已介入，初步判断为高技术盗窃。此事件令全球震惊，博物馆承诺加强安保，呼吁公众协助提供线索。案件调查中，敬请关注后续报道！')}
AFTER_TEXT = {'（你现在在④客厅）': ('fig', ('伊森的屋子：①卧室　②厨房　③书房　④客厅', 'assets/cabin-plan.jpg', ''))}
FIXES = {'披上大衣l拿好车钥匙': '披上大衣，拿好车钥匙'}
KEEP_TAIL = ('（你现在在',)                      # 指向地图的位置说明，保留

# 人工审阅后要删的（序号见 caqiang_review 输出）
MANUAL_DROP = set()
# 人工审阅后保留的场外批注（序号）
KEEP_NOTE = set()


def dice(t):
    t = CQ_DROP.sub('', t).replace('~', '')
    m = re.search(r'<([^>]+)>[\s\S]*?["“]?([\u4e00-\u9fffA-Za-z]+)["”]检定结果为:\s*D100=(\d+)/(\d+)', t)
    if m:
        res = re.search(RESULT, t[m.end():])
        return f'{m.group(1)}　{m.group(2)}　{m.group(3)}/{m.group(4)}' + (f'　{res.group(1)}' if res else '')
    m = re.search(r'<([^>]+)>的理智检定:\s*\n?d100=(\d+)/(\d+)', t)
    if m:
        res = re.search(RESULT, t[m.end():])
        ch = re.search(r'理智变化:\s*(\d+)\s*➯\s*(\d+)\s*\(扣除([^=]+)=(\d+)点\)', t)
        s = f'{m.group(1)}　理智检定　{m.group(2)}/{m.group(3)}' + (f'　{res.group(1)}' if res else '')
        if ch and ch.group(1) != ch.group(2):
            s += f'　SAN {ch.group(1)}→{ch.group(2)}（{ch.group(3)}={ch.group(4)}）'
        return s
    m = re.search(r'<([^>]+)>[^\n]*?(?:掷出了|掷骰[:：]?|结果是)\s*(\S*\d*[dD]\d+\S*?=\s*\d+)', t)
    if m:
        return f'{m.group(1)}　{m.group(2)}'
    return None


events, removed, imgs = [], [], []
for i, x in enumerate(msgs):
    name, t, date = x['name'], x['text'], x['date']

    def drop(why):
        removed.append((date, why, name, t))

    if name == BOT:
        d = dice(t)
        if d:
            events.append((date, 'dice', d))
        else:
            drop('骰娘：非检定回复')
        continue
    t0 = t
    t = CQ_DROP.sub('', t).strip()
    if re.match(r'^[.。]\s*[a-zA-Z]', t):
        drop('玩家输入指令'); continue
    if re.fullmatch(r'[—\-]+\s*拉线\s*[—\-]+', t):
        drop('结束标记'); continue
    if PAREN.match(t):
        if i in KEEP_NOTE:
            events.append((date, 'note', (name, punct(t.strip('（）() ')))))
        else:
            drop('OOC（括号）')
        continue
    if i in MANUAL_DROP:
        drop('人工审阅：场外闲聊 / 提示'); continue
    files = CQ_FILE.findall(t); t = CQ_FILE.sub('', t)
    n_img = len(CQ_IMG.findall(t)); t = CQ_IMG.sub('', t).strip()
    for a, b in FIXES.items():
        t = t.replace(a, b)
    t = re.sub(r'(?<!\*)\*([^*\n]{1,20})\*(?!\*)', r'**\1**', t)      # KP 用 *……* 表示强调
    stripped = TAIL.sub('', t)
    if stripped != t and len(stripped) >= 8 and not any(k in t[len(stripped):] for k in KEEP_TAIL):
        t = stripped                                  # 旁白末尾的「（。ra侦查）」之类
    if t:
        events.append((date, 'say', (name, punct(t), i)))
    for f in files:
        if f in FILE_DOC:
            events.append((date, 'doc', FILE_DOC[f]))
        else:
            events.append((date, 'fig', (FILE_CAP.get(f, f.rsplit('.', 1)[0]), FILE_SRC.get(f), f)))
    for k, ev in AFTER_TEXT.items():
        if k in t:
            events.append((date,) + ev)
    for k in range(n_img):
        imgs.append((i, name, date))
        events.append((date, 'img', (i, k)))         # 暂存：等原图来了再判断是线索还是表情

json.dump(dict(events=events, imgs=imgs), open(f'{S}/events.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('事件', Counter(e[1] for e in events))
print('删去', len(removed), Counter(w for _, w, _, _ in removed).most_common())
print('图片链接（待配图）', len(imgs), Counter(n for _, n, _ in imgs))
json.dump(removed, open(f'{S}/removed.json', 'w', encoding='utf-8'), ensure_ascii=False)


# ---------------------------------------------------------------- 输出
CHAPTERS = {'2026-09-29': ('第一章 · 暴雨', '九月二十九日'), '2026-10-01': ('第二章 · 肉汤', '十月一日'),
            '2026-10-02': ('第三章 · 来客', '十月二日')}
os.makedirs(OUT, exist_ok=True)
md = ['# 擦枪走火', '',
      '守秘人：qwi　|　调查员：艾迪安·多雷　|　舞台：美国，1981 年 9 月 28 日，暴风雨之夜', '',
      '**体例**：正文为戏内叙事与对白；`反引号` 为检定记录；`::: 文件` 为戏内出现的文件。', '',
      '**来源**：QQ 机器人框架导出的 txt（含图片与文件的引用），骰娘「芯傅」的 log 导出作对照。', '',
      '**模组**：《擦枪走火》，作者 逆光の白羊。文中插图为团中展示过的模组图，取自模组 PDF。', '']
cur = sp = None
for date, kind, p in events:
    if date != cur:
        title, cn = CHAPTERS[date]
        md += ['', '---', '', f'## {title}　{cn}', '']
        cur, sp = date, None
    if kind == 'say':
        name, text, _ = p
        if name != sp:
            md.append(f'**{"守秘人" if name == KP else name}**' if False else f'**{name}**')
            sp = name
        md += [text, '']
        continue
    if kind == 'img':
        continue                                   # 图片链接已失效，等原图
    sp = None
    if kind == 'dice':
        md += [f'`{p}`', '']
    elif kind == 'doc':
        md += [f'::: 文件　{p[0]}', p[1], ':::', '']
    elif kind == 'fig':
        cap, src, f = p
        md += [f'![{cap}]({src})' if src else f'〔图：{cap}　原图待补（{f}）〕', '']
open(f'{OUT}/整理版.md', 'w', encoding='utf-8').write(re.sub(r'\n{3,}', '\n\n', '\n'.join(md)).strip() + '\n')

by = defaultdict(list)
for date, why, name, t in removed:
    by[why].append((date, name, t))
log = ['# 删改记录', '', '下列内容未进入整理版，按原因分组。', '', '| 原因 | 条数 |', '|---|---|'] + \
      [f'| {w} | {len(v)} |' for w, v in sorted(by.items(), key=lambda kv: -len(kv[1]))]
for w, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    log += ['', f'## {w}（{len(v)}）', ''] + [f'- {d[5:]} {n}：{(t or "").replace(chr(10), " / ")[:150]}' for d, n, t in v]
open(f'{OUT}/_删改记录.md', 'w', encoding='utf-8').write('\n'.join(log) + '\n')
print('已写出', OUT)
