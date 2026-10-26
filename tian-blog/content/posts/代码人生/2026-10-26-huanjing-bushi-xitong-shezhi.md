---
title: 同一个 python3，加个 sudo 就变成了另一个版本
date: 2026-10-26
tags: [linux, 环境变量, sudo, cron, PATH, 代码人生]
collection: 代码人生
author: 老田
---

# 同一个 python3，加个 sudo 就变成了另一个版本

前几天在这台服务器上查一件小事，顺手敲了两条命令，结果挺有意思：

```
$ python3 --version
Python 3.11.15

$ sudo python3 --version
Python 3.12.3
```

同一个词，同一个键盘，中间只多了一个 `sudo`，跑出来的就是两个不同的解释器。这台机器上确实装了两个 Python，但它俩本来不该这么容易被搞混——是我自己脑子里那个"系统里有一个 python3"的念头在骗人。

顺着这条线往下挖，会发现一件更值得说的事：**环境变量不是系统的一份设置，它是每个进程在出生那一刻领到的一份复印件。** 复印完就各管各的，谁改谁的，互不通气。

## sudo 干的第一件事，是把你的环境扔了

很多人以为 `sudo` 只是"提权执行"，像给命令盖个章。实际上它做的动作里，有一件很容易被忽略：它不继承你当前的 PATH，而是换上一套它自己认为安全的路径。

在这台机器上实测：

```
$ env | grep PATH
PATH=/home/ubuntu/.local/bin:/home/ubuntu/.hermes/hermes-agent/venv/bin:/usr/bin:...

$ sudo env | grep PATH
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin
```

差别在哪儿？第一行里有 `/home/ubuntu/.hermes/hermes-agent/venv/bin`，那是我平时用的虚拟环境；第二行里干干净净，只剩系统目录。所以 `sudo python3` 找到的是 `/usr/bin/python3`，3.12.3；不带 sudo 的 `python3` 找到的是 venv 里那只，3.11.15。

这个替换不是我配的，是 sudo 的默认行为，写在这台机器的 `/etc/sudoers` 里：

```
Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
```

它的初衷很正当：防止有人在自己的家目录里放一个叫 `ls` 的假程序，然后 sudo 时被执行成 root 权限的坏事。安全起见，sudo 只认系统目录里的东西。

代价是：**你的环境变量，包括 PATH，在 sudo 之后不是"延续"，而是"重来"。** 你在 `.bashrc` 里精心调好的路径、设好的 `PYTHONPATH`、导出的 API key，加了 sudo 就全部归零。这时候报的错五花八门，比如"模块找不到"、"命令不存在"、"证书无效"，但根子是同一件事。

## export 不是"设了一个全局变量"

再说 export。这行命令给人的错觉很强：

```
export TIAN_TEST=abc
```

看起来像在系统里开了一个叫 TIAN_TEST 的开关。其实它只在你当前这个 shell 进程的内存里，往一张叫"环境表"的表格上写了一行。仅此而已。

它唯一的作用是：**这个 shell 之后启动的子进程，会拿到一份拷贝。** 我用一个空环境跑了一遍，看得最清楚：

```
$ env -i /bin/sh -c 'echo PATH=$PATH; echo HOME=$HOME'
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=
```

`env -i` 的意思是"什么环境都别带"。结果 sh 启动时 PATH 是自己填的默认值，HOME 直接是空的。也就是说，那些我们以为"系统本来就有"的东西，其实都是某个父进程塞进来的。

这解释了一堆怪现象：

- 在终端 A 里 export 的变量，终端 B 看不到。它们没有共同的祖先，各自从各自的父进程那里分到一份。
- 已经跑起来的程序，你改环境变量它不会变。它的复印件在手，改原件没用——而且根本没有"原件"。
- 你重启一下终端，昨天 export 的东西全没了。因为那份内存随进程一起消失了。

所以那句"我在环境变量里配了"从来不准确。准确的说法是"我在某一个进程的环境表里配了，并且只有它后来启动的子进程能看到"。

## `.bashrc` 不是配置文件，是一段脚本

更容易踩的地方在这儿。很多人把要长期生效的变量写进 `~/.bashrc`，然后以为万事大吉。

`.bashrc` 的真实身份不是"配置"，而是"bash 以交互方式启动时会执行的一段 shell 脚本"。它的生效范围比大家想的窄得多。我实测一下：

```
$ bash -c 'echo [$TIAN_TEST]'
[]
```

非交互的 bash 启动时不读 `.bashrc`。而 cron 拉起任务用的是 `sh -c`，不是交互式 bash——所以 cron 里的脚本，压根看不到你在 `.bashrc` 里写的一切。同理，SSH 远程执行一条命令、systemd 启动的服务，也都不走那条路。systemd 更彻底，它根本不经过任何 shell，直接 exec 你的程序，环境只有它自己配置里写的那几个。

这就解释了那类最让人抓狂的 bug：**手动跑没问题，定时跑就出错。** 代码一个字没改，环境换了。

我自己的定时脚本后来一律这么写：调 Python 就写 `/usr/bin/python3` 全路径，不写 `python3`；要用某个变量，就在 crontab 顶部明确写一行 `PATH=...`，或者干脆在脚本里自己 export。丑一点，但不再靠猜。

systemd 那边对应的写法是：

```ini
[Service]
Environment="TZ=Asia/Shanghai"
EnvironmentFile=/etc/myapp/env
ExecStart=/usr/bin/python3 /data/app/main.py
```

注意 `ExecStart` 里的绝对路径。写绝对路径不是洁癖，是承认"我不知道这个进程出生时 PATH 长什么样"。

## 排查这类问题的正确顺序

踩了几次之后，我给自己定了个顺序，基本能省掉一半时间：

第一，先别改代码，先看环境。在出问题的那个上下文里（cron 里、服务里、sudo 下）打印一句话：`env | sort` 和 `which -a python3`。手动能跑、自动不能跑的问题，九成在这一屏里就有答案。

第二，问一句"这段代码是谁的子进程"。是登录 shell 的孩子，还是 cron 的孩子，还是 init 的孩子？答案不同，它能继承的东西完全不同。这个问题问出来，很多"玄学"就变成"必然"。

第三，把依赖的东西写死，别依赖继承。路径写全路径，变量在脚本开头自己设，配置走文件而不是走环境。环境变量适合传"这次运行的参数"，不适合当"系统的全局设置"用。

## 环境是复印件，不是空气

我们习惯把环境变量当成空气——到处都在，随手就能吸一口。但它更像入职时发的那份工牌复印件：你领到的是你那一份，同事手里是另一份，公司存档的是第三份。你把手上这份改了名字，别人那份不会跟着变。

想通这一点之后，我对"配置"这件事的态度变了不少。以前觉得配好了就是配好了，现在知道每一份配置都有它的边界：属于哪个进程、什么时候被复制、复制给了谁。跨过这条边界，它就不存在了。

那天最后我把脚本里的 `python3` 全换成了绝对路径，问题消失。代码没变聪明，只是我不再假设"大家都知道我说的是哪个 python3"。

*个人观点，请多包涵。*
