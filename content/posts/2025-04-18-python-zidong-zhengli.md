---
title: 用 Python 写了个自动整理文件的脚本，节省了我每周2小时
date: 2025-04-18
slug: python-zidong-zhengliwenjian
tags: [Python, 工具, 效率]
collection: 代码人生
excerpt: 我的下载文件夹乱成了一锅粥。于是我花了两小时写了个脚本，以后每次点一下就全整理好了。代码分享。
author: 老田
---

## 问题

我的 Downloads 文件夹有 1,600+ 个文件。

图片、PDF、安装包、压缩包、代码文件——全混在一起。找一个三个月前下的 PDF，至少要五分钟。

我忍了很久，直到某天我花了半小时没找到一个文件，才决定动手解决它。

---

## 解决方案

用 Python 写一个脚本，按文件类型自动分类整理。

运行一次，把文件移到对应的子文件夹里。

---

## 代码

```python
import os
import shutil
from pathlib import Path

# 类型映射
TYPE_MAP = {
    "图片":  [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".heic"],
    "文档":  [".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".pptx"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "安装包": [".exe", ".dmg", ".pkg", ".msi", ".deb"],
    "代码":  [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml"],
    "视频":  [".mp4", ".mov", ".avi", ".mkv"],
    "音频":  [".mp3", ".wav", ".flac", ".m4a"],
}

def get_category(suffix: str) -> str:
    for cat, exts in TYPE_MAP.items():
        if suffix.lower() in exts:
            return cat
    return "其他"

def organize(folder: str):
    base = Path(folder)
    moved = 0
    for f in base.iterdir():
        if f.is_file():
            cat = get_category(f.suffix)
            dest_dir = base / cat
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / f.name
            # 避免覆盖同名文件
            if dest.exists():
                dest = dest_dir / f"{f.stem}_copy{f.suffix}"
            shutil.move(str(f), dest)
            moved += 1
    print(f"✅ 整理完成，移动了 {moved} 个文件")

if __name__ == "__main__":
    target = input("输入要整理的文件夹路径：").strip() or str(Path.home() / "Downloads")
    organize(target)
```

---

## 使用方法

1. 把上面的代码保存为 `organize.py`
2. 命令行运行：`python organize.py`
3. 输入你的 Downloads 路径（或直接回车使用默认路径）
4. 完成

---

## 效果

我运行了一次，1,600 个文件，大概 3 秒整理完毕。

现在我的 Downloads 里面是这样的：
```
Downloads/
  图片/     (423 个文件)
  文档/     (318 个文件)
  压缩包/   (201 个文件)
  安装包/   (87 个文件)
  代码/     (156 个文件)
  视频/     (43 个文件)
  其他/     (378 个文件)
```

清晰多了。

---

## 进阶：定时自动运行

如果你想每天自动运行，可以：

- **Windows**：用任务计划程序
- **Mac/Linux**：用 crontab

```bash
# 每天凌晨2点自动整理
0 2 * * * python /path/to/organize.py
```

---

代码挺简单，但解决了一个真实的问题。这就够了。
