"""整理《死者的顿足舞》：以骰娘「阿道夫」的 log（txt）为正文来源。

用法：python3 build.py <导出解压目录> <记录文件夹>
骰娘 log 完整记录了两次开团；QQ 的 HTML 导出缺了约一成消息，只用来取图片。
"""
import re, json, sys, os, glob
from collections import Counter, defaultdict

SRC, OUT = sys.argv[1], sys.argv[2]
KP, BOT = '菠萝大王🍍', '阿道夫'
PCS = ('克洛德', '文森特', '蒂诺丝', '尤金', '朱利安', '西奥多')

# ---------------------------------------------------------------- 读骰娘 log
txt = open([p for p in glob.glob(SRC + '/resources/files/*') if p.endswith('.txt')][0], encoding='utf-8-sig').read()
H = re.compile(r'^(.+?)\((\d+)\) (\d\d:\d\d:\d\d)\s*$')
rows, cur = [], None
for line in txt.replace('\r', '').split('\n'):
    m = H.match(line)
    if m:
        cur = dict(name=m.group(1), qq=m.group(2), t=m.group(3), lines=[]); rows.append(cur)
    elif cur is not None:
        cur['lines'].append(line)
sess, prev = '第一夜', None
for r in rows:
    r['raw'] = '\n'.join(r.pop('lines')).strip()
    if prev and r['t'] < prev:          # 时间回绕：第二次开团
        sess = '第二夜'
    r['sess'], prev = sess, r['t']
    if r['name'].startswith('菠萝大王'):
        r['name'] = KP

# 人工审阅后删去的场外闲聊（序号）：没加括号的吐槽、催骰、问规则、打错重发
MANUAL_DROP = {9, 203, 217, 220, 423, 460, 514, 516, 580, 629,
               668, 1037, 1046, 1138}
KEEP_NOTE = set()        # 人工审阅后保留为场外批注（序号）
# 图片（按 GUID 前 8 位）：已确认是场外截图 / 表情的删去；其余原图缺失，先按上下文标注
IMG_DROP = {'07B7EBA6': '场外截图（问 AI 1920 年代有没有监控）', 'ADEB1E19': '场外表情（群主语录）'}
IMG_CAP = {'A0A6583F': '捡到的名片', '486EC5AF': '早晨的场景图', '149A8590': '玛妮的照片',
           '931A7E41': '侦查所见', 'A6D75847': '车库', '0EB8A323': 'AI 生成的场景图', 'A19FB4DB': 'AI 生成的场景图',
           '17FA4FA2': 'AI 生成的场景图'}
FIXES = {'轰——n': '轰——', '，sc0/1d3。': '。', '克罗德': '克洛德', '帝诺斯': '蒂诺丝',
         '运进纽约的。（': '运进纽约的。”（', '黑樱桃利口酒。': '黑樱桃利口酒。”',
         '“小伙汁，抽烟吗　': '“小伙汁，抽烟吗？”', '我还要写报告。“': '我还要写报告。”',
         '（点根烟）”不过': '”（点根烟）不过', '凯歌 (Veuve': '凯歌（Veuve', 'Clicquot)': 'Clicquot）',
         '哈莱姆 (The Harlem)': '哈莱姆（The Harlem）'}


def punct(t):
    """引号方向按出现顺序交替；省略号统一为 ……；去掉标点前后多余的空格。"""
    out, k = [], 0
    for ch in t:
        if ch == '"':
            out.append('“' if k % 2 == 0 else '”'); k += 1
        else:
            out.append(ch)
    t = ''.join(out)
    t = re.sub(r'\.{2,}|。{3,}|…(?!…)', '……', t)
    t = re.sub(r'……+', '……', t)
    t = re.sub(r'\s+([。，、；：！？」』”）】])', r'\1', t)
    t = re.sub(r'([「『“（【])\s+', r'\1', t)
    return t


def clean(t):
    """去掉回复引用、@QQ号、表情码、转义；图片另外取出。"""
    imgs = re.findall(r'\[mirai:image:\{([^}]+)\}\.\w+,[^\]]*?isEmoji=(\w+)', t)
    t = re.sub(r'\[mirai:quote:\[mirai:source:[\s\S]*?at \d+\],\s*content=<[^>]*>\]', '', t)
    t = re.sub(r'\[mirai:[^\]]*\]', '', t)
    t = t.replace('\\#', '#').replace('\\', '')
    t = re.sub(r'^\s*(?:\d{6,}\s*)+', '', t)            # 开头的 @QQ号
    t = re.sub(r'(?<!\d)\d{9,10}(?!\d)\s?', '', t)        # 句中的 @QQ号
    return t.strip(), [g for g, emo in imgs if emo == 'false']


RES = r'(大成功|极难成功|困难成功|大失败|成功|失败)'


def dice(t):
    m = re.search(r'([^\s/]+?)进行的(\S+?)鉴定结果:\s*1d100=(\d+)/(\d+)\s*' + RES, t)
    if m:
        return f'{m.group(1)}　{m.group(2)}　{m.group(3)}/{m.group(4)}　{m.group(5)}'
    m = re.search(r'([^\s/。]+?)\s*的SanCheck[\s\S]*?:\s*(\d+)/(\d+)\s*(\S+?)。[\s\S]*?san=(\d+)-(\S+?)=(\d+)', t, re.I)
    if m:
        roll, goal = int(m.group(2)), int(m.group(3))
        ok = '大成功' if roll == 1 else '大失败' if roll == 100 or (roll >= 96 and goal < 50) else '成功' if roll <= goal else '失败'
        s = f'{m.group(1)}　理智检定　{m.group(2)}/{m.group(3)}　{ok}'
        if m.group(5) != m.group(7):
            s += f'　SAN {m.group(5)}→{m.group(7)}'
        return s
    return None


PAREN = re.compile(r'^\s*[（(][\s\S]*[）)]\s*$')
TAIL = re.compile(r'\s*[（(][^（）()]{0,50}[）)]\s*$')
events, removed, img_slots = [], [], []
for i, r in enumerate(rows):
    name = r['name']
    t, imgs = clean(r['raw'])
    r['clean'] = t

    def drop(why):
        removed.append((r['sess'], why, name, t or r['raw'][:60]))

    if name == BOT:
        if '暗骰' in t:
            drop('KP 暗骰'); continue
        d = dice(t)
        if d and not d.startswith(KP):
            events.append((r['sess'], 'dice', d))
        else:
            drop('骰娘：非检定回复' if not d else 'KP 玩笑骰')
        continue
    if re.match(r'^[.。]\s*\S', t):
        drop('指令'); continue
    if i in KEEP_NOTE and PAREN.match(t):
        events.append((r['sess'], 'note', (name, t.strip('（）() ')))); continue
    if PAREN.match(t):
        drop('OOC（括号）'); continue
    if i in MANUAL_DROP:
        drop('人工审阅：场外闲聊'); continue
    t = re.sub(r'^[#＃]\s*', '', t)                    # 戏内发言前的 # 标记
    t = re.sub(r'([”"」])\s*[#＃]\s*', r'\1', t)       # 「“台词”#动作」里的 #
    t = re.sub(r'\s*[#＃]\s*', '　', t)
    for a, b in FIXES.items():
        t = t.replace(a, b)
    t = punct(t)
    s2 = TAIL.sub('', t)
    if s2 != t and len(s2) >= 8:
        t = s2                                         # 句末夹带的括号吐槽
    if t:
        events.append((r['sess'], 'say', (name, t, i)))
    for g in imgs:
        if g[:8] in IMG_DROP:
            drop('图片：' + IMG_DROP[g[:8]]); continue
        img_slots.append((i, name, r['sess'], r['t'], g))
        events.append((r['sess'], 'img', (g, name, r['t'])))
    if not t and not imgs:
        drop('仅表情 / 空消息')

json.dump(dict(rows=rows, events=events, imgs=img_slots, removed=removed),
          open(os.path.join(OUT, '_build', 'state.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('骰娘 log', len(rows), '| 事件', Counter(e[1] for e in events))
print('删去', len(removed), Counter(w for _, w, _, _ in removed).most_common())


# ---------------------------------------------------------------- 输出
import shutil
# 曲目：每夜按场景切成几首「曲子」，标题用故事里真正奏响的曲名或场景（锚点 = 该段落开头）
TRACKS = [
    ('斯默的天堂！', '斯默的天堂', "Smalls' Paradise"),
    ('穿过门卫，踩着金丝', '博士爵士乐', 'Doctor Jazz'),
    ('这很稀奇了，通常小号都是三键的', '死者的顿足舞', 'Dead Man Stomp'),
    ('在你们离开之时，斯默的天堂', '乔伊，乔伊', 'Joe, Joe'),
    ('而随着第一缕清晨阳光的降临', '晨报', 'Morning Edition'),
    ('非常好，真是救星，不久之后', '西 131 街', 'West 131st Street'),
    ('在莫甘与杜佩非裔家庭殡仪馆中', '与汝同行', 'Just a Closer Walk with Thee'),
    ('而就在这一片骚乱，惊慌，惨叫', '灰色帕卡德', 'The Grey Packard'),
    ('话又说回来，你们深一脚浅一脚', '上流社会', 'High Society'),
    ('他能去哪里——为什么能跑这么快', '为玛妮而奏', "Marnie's Song"),
]
CHAPTERS = {'第一夜': '第一夜　2026 年 1 月 21 日', '第二夜': '第二夜　2026 年 1 月 28 日'}
md = ['# 死者的顿足舞', '',
      f'守秘人：{KP}　|　调查员：{"、".join(PCS)}　|　舞台：1920 年代，纽约哈莱姆', '',
      '**体例**：正文为戏内叙事与对白；`反引号` 为检定记录；〔图〕为当时贴出的图片。', '',
      '**来源**：骰娘「阿道夫」的 log（txt，两夜完整）；QQ 群聊 HTML 导出仅用于取图。', '']
cur = sp = None
for sess, kind, p in events:
    if sess != cur:
        md += ['', '---', '', f'## {CHAPTERS[sess]}', '']
        cur, sp = sess, None
    if kind == 'say':
        name, text, _ = p
        tr = next((t for t in TRACKS if text.startswith(t[0])), None)
        if tr:
            k = TRACKS.index(tr) + 1
            md += [f'### {k:02d}　{tr[1]}　{tr[2]}', '']
            sp = None
        if name != sp:
            md.append(f'**{name}**'); sp = name
        md += [text, '']
        continue
    sp = None
    if kind == 'dice':
        md += [f'`{p}`', '']
    elif kind == 'note':
        md += [f'> 〔场外〕{p[0]}：{p[1]}', '']
    elif kind == 'img':
        g, name, t = p
        md += [f'〔图：{IMG_CAP.get(g[:8], "未知")}　{name} {t} 贴出　原图待补（{g[:8]}）〕', '']
open(os.path.join(OUT, '整理版.md'), 'w', encoding='utf-8').write(re.sub(r'\n{3,}', '\n\n', '\n'.join(md)).strip() + '\n')

by = defaultdict(list)
for sess, why, name, t in removed:
    by[why].append((sess, name, t))
log = ['# 删改记录', '', '下列内容未进入整理版，按原因分组。', '', '| 原因 | 条数 |', '|---|---|'] + \
      [f'| {w} | {len(v)} |' for w, v in sorted(by.items(), key=lambda kv: -len(kv[1]))]
for w, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    log += ['', f'## {w}（{len(v)}）', ''] + [f'- {s} {n}：{(t or "").replace(chr(10), " / ")[:150]}' for s, n, t in v]
open(os.path.join(OUT, '_删改记录.md'), 'w', encoding='utf-8').write('\n'.join(log) + '\n')

raw = [p for p in glob.glob(SRC + '/resources/files/*') if p.endswith('.txt')][0]
shutil.copy(raw, os.path.join(OUT, '原始log.txt'))
print('已写出', OUT)
