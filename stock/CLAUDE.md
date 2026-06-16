# CLAUDE.md - 股票日记网站 / 缠论看板

## 项目定位

这是老板的股票日记网站与缠论策略研究看板子项目。请只把当前目录 `stock/` 当作工作范围，除非明确要求，不要扫描整个 `/root/.openclaw/workspace`。

## 关键文件

- `server.py`：Python `http.server` 后端、REST API、静态路由。
- `index.html` / `app.js` / `style.css`：股票日记主页面。
- `chan.html`：缠论策略研究看板，当前展示 V21/V22/V23 研究状态。
- `chan_execution_600585_backup.html`：600585.SH V22 轻量执行图。
- `stock_diary.db`：SQLite 数据库，默认不要修改、不要格式化、不要删除。

## 当前路由

- `/stock`、`/stock/` → `index.html`
- `/chan`、`/chan/` → `chan.html`
- `/chan/execution/600585` → `chan_execution_600585_backup.html`

公网常用入口：

- `http://159.75.242.239/stock/`
- `http://159.75.242.239/chan`
- `http://159.75.242.239/chan/execution/600585`

## 修改纪律

1. 默认只修改任务要求涉及的文件。
2. 不要改 `stock_diary.db`、`stock.tar`、`__pycache__/`、`venv/`。
3. 不要全文件重写 `server.py`，避免换行符/格式化造成巨大 diff。
4. 不要删除文件；如需替换，先说明理由并等待确认。
5. UI 文案保持中文、短句、老板能快速看懂。
6. 投资内容必须标注这是研究/回测，不构成投资建议；不要夸大收益。

## 验收命令

在 `stock/` 目录内修改后至少运行：

```bash
python3 -m py_compile server.py
```

如果改了 `/chan` 或路由，在仓库根目录或服务运行时验证：

```bash
curl -fsS http://127.0.0.1/chan | grep '缠论策略研究看板'
curl -fsS http://127.0.0.1/chan | grep 'v22_hold5_60pct_amt50m_exbottom5'
curl -fsS http://127.0.0.1/chan/execution/600585 | grep '<title>600585.SH V22执行图</title>'
```

如果本地 80 端口服务未运行，先不要擅自重启全局服务；报告需要启动/重启。

## 推荐 Claude Code 工作方式

- 从 `stock/` 目录启动 Claude Code，不要从 workspace 根目录启动。
- 大改前先 `/plan`，列出将改哪些文件。
- 完成后展示：
  - `git diff --stat`
  - 关键 diff
  - 验收命令输出
- 长会话用 `/compact`，换任务用 `/clear`。
