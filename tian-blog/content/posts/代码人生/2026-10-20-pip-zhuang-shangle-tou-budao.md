---
title: pip 装成功了，import 却说没有这个模块：一台机器上藏着两个 Python
date: 2026-10-20
tags: [python, pip, 虚拟环境, PATH, 解释器, 代码人生]
collection: 代码人生
author: 老田
---

# pip 装成功了，import 却说没有这个模块：一台机器上藏着两个 Python

装包这件事，我原以为是最不需要动脑子的环节。`pip install requests`，出几个进度条，最后一行 `Successfully installed`，然后 `import requests` 就能用。直到有一次，这两句话在同一台机器上互相打脸。

那是给一个定时脚本换个抓取库，装完包，跑脚本，报错：

```
ModuleNotFoundError: No module named 'requests'
```

我不信邪，再装一遍。pip 的回答很客气：

```
Requirement already satisfied: requests in /usr/lib/python3/dist-packages (2.31.0)
```

它明确告诉我：包在 `/usr/lib/python3/dist-packages` 里，好好的。可脚本就是不认。到这一步，如果只是删了重装、或者加个 `--force-reinstall`，那大概能折腾一晚上，最后得出的结论是"这机器有鬼"。

真正的答案不神秘，只是有点反直觉：**pip 和 python 是两个独立的程序，它们之间没有任何血缘关系**。你敲的 `pip`，和你敲的 `python3`，只是恰好都躺在 PATH 里，谁都可以是别人家的孩子。

## 一个"命令名"，背后可能是好几个程序

Linux 里敲命令时，shell 做的是同一件事：从左到右翻 PATH 里的目录，找到第一个同名文件，执行它。PATH 像一张按顺序排的名单，谁的目录在前面，谁就是这次的赢家。

问题就在这儿。同一台机器上，Python 往往不止一个：系统自带的 `/usr/bin/python3`，编译安装的 `/usr/local/bin/python3.11`，某个工具自己塞进 PATH 的 venv 里的 `python3`，再加上 Homebrew、conda、pyenv 各占一块地盘。它们每一个都自带一整套标准库、一整套第三方包目录，彼此互不通气。

我在自己的服务器上做了个实验，两个命令的输出值得并排看：

```
$ which -a python3
/home/ubuntu/.hermes/venv/bin/python3
/usr/bin/python3

$ python3 -V
Python 3.11.15

$ pip -V
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)
```

`python3` 是 3.11，`pip` 却挂在一个 3.12 身上。它们不是"同一个 Python 的两个入口"，而是两个不同 Python 各自带的工具。pip 把包装进了 3.12 的库目录，我跑的脚本是 3.11 在执行，3.11 翻遍自己的目录找不到这个包，于是很诚实地报错。

换个比喻：**解释器是房子，包是房子里的家具**。`pip install` 是往某一栋房子里搬沙发。你搬沙发的时候没看门牌号，回家开门的却是另一栋房子。房子都没错，沙发也没丢，只是不在同一个屋里。

## 为什么脚本更容易踩这个坑

在终端里手动敲命令，至少 PATH 还是你熟悉的那一套。脚本一进去，变量全变了。

第一层是 shebang。文件开头那行 `#!/usr/bin/env python3` 和 `#!/usr/bin/python3` 长得几乎一样，行为差得很远：`env python3` 会去走 PATH，也就是说"谁排前面用谁"；而写死 `/usr/bin/python3` 就永远用系统那个，你辛辛苦苦装进 venv 的包，一个都用不上。反过来，写死路径的脚本在别人的机器上大概率直接启动失败。

第二层是 `sudo`。很多人习惯了"报错就加 sudo"，但 sudo 会重置 PATH，把当前用户的环境变量丢掉一大半。于是 `sudo python3 xxx.py` 用的是 root 的、系统的那只 Python，和你在自己 shell 里测通的完全是两个环境。于是出现经典的"我自己跑没问题，一放定时任务就不行"——cron 的环境比 sudo 还干净，连 `/usr/local/bin` 都不一定在 PATH 里。

第三层是 PEP 668。近两年的发行版会在系统 Python 上加一个 `EXTERNALLY-MANAGED` 标记，直接拒绝往系统目录装包，报一行提示：

```
error: externally-managed-environment
```

这不是发行版在刁难人，是它终于认了这件事：系统 Python 是操作系统自己用的，`apt` 依赖它的具体版本，你手动往上装包，早晚会和系统包管理器打架。所以它干脆把门锁上，请你另找屋子住。

## 三行命令定位，比猜快

遇到"装了却用不了"，不用重新装，也不用怀疑人生，先问三个问题：**正在执行的是谁，它从哪儿找包，pip 又是谁家的**。

```bash
which -a python3                  # 有几个 python3，谁排在最前面
python3 -c "import sys; print(sys.executable); print(sys.path)"
python3 -m pip -V                 # 这个解释器名下的 pip 装到哪儿
```

第一行列出所有候选，让你知道牌堆里有几张牌。第二行是核心：`sys.executable` 是当前解释器的绝对路径，`sys.path` 是它找包时挨个翻的目录清单——包在不在这个清单里，一眼就能看出来。第三行是最好用的习惯：**永远用 `python3 -m pip` 而不是裸 `pip`**。`-m` 的意思是"用这个解释器去跑它自己的 pip 模块"，解释器和 pip 被强制绑成一对，从根上断掉张冠李戴的可能。

这一条改掉，等于把事故概率砍掉一大半。它不解决版本冲突，但至少保证"我在哪个 Python 里装包，就在哪个 Python 里用包"。

## 真正该改的是习惯

装包这件事，最好从一开始就别往系统目录里塞。做法朴素得没什么技术含量：

项目目录下 `python3 -m venv .venv`，然后 `.venv/bin/python` 干活、`.venv/bin/pip` 装包，脚本的 shebang 写成 `#!/path/to/project/.venv/bin/python`，或者运行时显式用 `.venv/bin/python script.py`。定时任务里写绝对路径，不依赖 PATH。整套流程唯一的要求是：**别再敲那个没有门牌号的 `pip`**。

我后来想，这类问题的讨厌之处不在于它难，而在于它不报"你搞错了"，它报的是"没找到"。一个信息量极低的错误，配上一个看起来无比成功的安装日志，人就会开始往玄学方向想：是不是缓存、是不是权限、是不是这库有什么毛病。

其实底层逻辑一直很干净：**Python 不是一个程序，是"解释器 + 它那一屋子包"的一对组合**。同名不代表同物，装成功不等于装对人。把这句话记住，往后遇到 `ModuleNotFoundError`，第一反应就不会是重装，而是先抬头看一眼门牌号。

*个人观点，请多包涵。*
