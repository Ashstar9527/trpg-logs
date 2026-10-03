"""把 QQ 机器人框架导出的 txt 拆成消息列表：python3 parse.py 原始log.txt msgs.json"""
import re, json, sys
txt = open(sys.argv[1], encoding='utf-8').read().replace('\r', '')
H = re.compile(r'^(.+?)\((\d+)\) (\d{4}/\d\d/\d\d) (\d\d:\d\d:\d\d)$')
msgs, cur = [], None
for line in txt.split('\n'):
    m = H.match(line)
    if m:
        cur = dict(name=m.group(1), qq=m.group(2), date=m.group(3).replace('/', '-'), time=m.group(4), lines=[])
        msgs.append(cur)
    elif cur is not None:
        cur['lines'].append(line)
for x in msgs:
    x['text'] = '\n'.join(x.pop('lines')).strip()
json.dump(msgs, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
print(len(msgs), 'messages')
