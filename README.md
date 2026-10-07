![界面截图](https://ps.ssl.qhimg.com/t02466fc46fd900a552.jpg)

想把一个 WordPress 主题整个汉化，却发现没有工具能一次性把所有待翻译文本导出来，只能一条条复制——于是有了这个小玩意。

一次导出、一次翻译、一次回填，几千条文本也不用手动复制粘贴。翻译完建议再用 Poedit 校对一遍。

## 用法

**图形界面**：下载 Releases 里的 exe，双击即用。四步：选文件 → 导出 → 翻译 → 回填。

**命令行**：

```bash
python -m potext stats  theme_zh.po                      # 看看翻译进度
python -m potext extract theme_zh.po -o todo.txt         # 导出所有待翻译文本
python -m potext apply   theme_zh.po todo.txt -o done.po --lang zh_CN   # 回填生成新 PO
python -m potext apply   theme_zh.po todo.txt            # 只校验不写出（干跑）
```

## 翻译文档的规则

`todo.txt` 一行对应一条待翻译内容，**翻译时只能改文字，不能增删行**。

- 原文里的换行写成 `\n` 留在同一行内，所以一条记录永远只占一行；
- 复数条目按目标语言的复数形态数展开成多行（中文 1 行、俄语 3 行、阿拉伯语 6 行），
  第 1 行是单数原文，其余是复数原文；形态数由 `--lang` 或 PO 头部的 `Plural-Forms` 决定，
  可用 `python -m potext langs` 查看内置语言；
- 译文留空表示跳过，保留 PO 里原有的翻译；
- 行数对不上时程序会明确报错并指出断在哪一条，不会静默错位。

## 它是怎么保证不弄坏你的文件的

- 自研 PO 读写，零第三方依赖；注释、引用、`fuzzy` 标记、obsolete 条目、重复 msgid、
  条目顺序与 `msgctxt` 全部原样保留，写出结果通过 `msgfmt -c` 校验；
- 默认只导出未翻译的条目，已完成的翻译不会被覆盖（要全部重译用 `--all`）；
- 译文丢失 `%s`、`{name}`、`%1$d` 这类占位符时会被检出并报告，
  需要时用 `--repair-placeholders` 自动补回；
- 输入无论是 UTF-8 / UTF-8-BOM / latin-1，输出统一 UTF-8 并同步头部 charset 声明。

## 从源码运行

需要 Python 3.10 以上，不需要安装任何依赖。

```bash
python main.py              # 启动图形界面
python -m potext --help     # 命令行
python build_exe.py         # 打包成 exe
python -m unittest discover -s tests -t .   # 跑测试
```

## 关于杀软报毒

PyInstaller 打的包经常被误报，我也没办法。代码是开源的，不信我打包的就自己 `python build_exe.py` 打一个。
