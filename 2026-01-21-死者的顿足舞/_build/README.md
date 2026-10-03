# 整理流程

```
python3 build.py <QQ 导出解压目录> ..   # 读骰娘 log txt，写出 ../整理版.md、../_删改记录.md、../原始log.txt
python3 cards.py                       # 读六张人物卡，写出 cards.json
python3 page.py ..                     # 整理版.md + cards.json + template.html -> ../index.html
```

缺失的图片：把原图存成 `../assets/<GUID 前 8 位小写>.<扩展名>`（GUID 见整理版里的〔图〕占位），再跑一次 page.py 即可出现在页面上。
