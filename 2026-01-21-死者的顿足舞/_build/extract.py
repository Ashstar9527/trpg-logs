"""从 QQChatExporter 的 HTML 导出抽取开团时段内的消息。

用法：python3 extract.py <导出解压目录> rows.json
开团时段以骰娘 log（resources/files/【死者的顿足舞】.txt）的两段为准。
"""
import re, json, sys, glob, html as H, datetime

SRC = sys.argv[1]
TZ_CN = datetime.timezone(datetime.timedelta(hours=8))
# 骰娘 log 的两段（北京时间）
SESSIONS = [
    ('第一夜', datetime.datetime(2026, 1, 21, 20, 2, 0, tzinfo=TZ_CN), datetime.datetime(2026, 1, 21, 22, 23, 50, tzinfo=TZ_CN)),
    ('第二夜', datetime.datetime(2026, 1, 28, 9, 0, 0, tzinfo=TZ_CN), datetime.datetime(2026, 1, 28, 11, 37, 55, tzinfo=TZ_CN)),
]
NAME = {'莫伊拉': '西奥多'}           # 莫伊拉的调查员是西奥多（骰娘 log 用角色名）
STATUS = re.compile(r'\s+(hp\d+/\d+\s+san\d+/\d+\s+dex\d+)\s*$', re.I)


def load():
    s = open(glob.glob(SRC + '/*.html')[0], encoding='utf-8').read()
    dec, out = json.JSONDecoder(), []
    for m in re.finditer(r'__QCE_CHUNK__\(\{id:"(c\d+)",messages:', s):
        a, _ = dec.raw_decode(s[m.end():]); out += a
    return out


def body(h, fb):
    h = re.sub(r'<div class="reply-content".*?</div>\s*</div>', '', h, flags=re.S)
    parts = re.findall(r'<span class="text-content">(.*?)</span>', h, re.S)
    if not parts:
        return re.sub(r'\[图片:[^\]]*\]|\[语音[^\]]*\]', '', fb or '').strip()
    t = re.sub(r'<br\s*/?>', '\n', ''.join(parts))
    return H.unescape(re.sub(r'<[^>]+>', '', t)).strip()


rows = []
for x in load():
    when = datetime.datetime.fromtimestamp(x['ts'] / 1000, TZ_CN)
    sess = next((s for s, a, b in SESSIONS if a <= when <= b), None)
    if not sess:
        continue
    h = x.get('html') or ''
    name, st = x['name'], ''
    m = STATUS.search(name)
    if m:
        st, name = m.group(1), name[:m.start()].strip()
    name = NAME.get(name, name)
    rows.append(dict(sess=sess, ts=x['ts'], cn=when.strftime('%m-%d %H:%M:%S'), name=name, status=st,
                     text=body(h, x.get('text')), imgs=re.findall(r'resources/images/([^"\\ ]+)', h),
                     voice='[语音' in (x.get('text') or ''), sys=x['name'] == '系统消息'))
rows.sort(key=lambda r: r['ts'])
json.dump(rows, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
from collections import Counter
print(len(rows), Counter(r['sess'] for r in rows), Counter(r['name'] for r in rows).most_common(12))
