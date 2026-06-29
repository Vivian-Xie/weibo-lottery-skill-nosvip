# 获取微博 Cookie（默认走自动化，手动作兜底）

抽奖流程需要一份**已登录微博账号的 cookie**（核心字段 `SUB`、`SUBP`、`ALF`），用于请求微博的 AJAX 接口。

> ⚠️ 不可自动化的边界：登录这一步（扫码 / 账密 / 验证码）**必须用户本人完成**。
> 任何工具都无法替用户登录——能自动登录就等于能盗号。所谓「自动获取 cookie」，
> 自动化的只是「登录后把 cookie 取出来」这一步，不是登录本身。

**默认策略：在有图形界面的桌面环境，直接走方式 A（浏览器自动化自动取），不要默认让用户手动粘贴。**
只有当无图形界面 / playwright 装不上 / RPA 失败时，才回退到方式 B / C。

---

## 方式 A：浏览器自动化「自动取 cookie」（⭐ 默认首选）

适用：**桌面 / 有图形界面**的环境。省掉用户手动复制粘贴，体验最好。

### 实现优先级（agent 决策）

这一步的本质是：**弹出 / 接管一个浏览器 → 打开 weibo.com → 等用户登录 → 读出 cookie**。
agent 应**优先复用自己已具备的浏览器自动化能力，而不是从零硬写**：

- ✅ 能直接**控制用户本机已打开的浏览器**（桌面自动化 / 浏览器扩展 / CDP 连到日常浏览器）→ 优先用，用户可能已登录，体验最佳。
- ✅ 已接入某个**浏览器自动化技能 / 工具**（clawbrowser、Playwright MCP、browser-use、Selenium 等）→ 调用它打开 weibo.com、等登录、读 cookie。
- ✅ 都没有 → **直接安装本包默认依赖 playwright**，用附带的现成脚本（见下）。这是默认兜底，不要因为"嫌装依赖"就跳过去用手动。

### 默认实现：本包附带的 Playwright 脚本

```bash
# 1) 安装（默认依赖，桌面环境直接装）
pip install playwright && python -m playwright install chromium

# 2) 弹窗登录 → 自动写 cookie
python scripts/optional/get_cookie_rpa.py --out ./cookie.txt --timeout 300
```

- 弹出可见浏览器、打开微博、轮询检测登录态、登录后自动写 cookie。
- 成功后 stdout 打印 `COOKIE_OK`，cookie 写入 `--out`。
- 用持久化 profile，下次通常免登录。
- ⚠️ 只 `pip install playwright` 不够，**必须** `python -m playwright install chromium` 装内核，否则弹窗失败。
- 超时未登录退出码 2 → 回退到方式 B / C。

> 设计原则：核心流程（爬取 + 抽奖）**完全不依赖**特定浏览器自动化技术，cookie 怎么来都行。
> 但在桌面环境，**默认就该走自动化**，把手动当兜底。

---

## 方式 B：用户直接粘贴 cookie（回退·最通用）

适用：无图形界面、或用户已自行拿到 cookie。任何 agent、任何环境都行。

请用户：
1. 浏览器登录 https://weibo.com
2. 按方式 C 的步骤复制 Cookie 整行
3. 把这一整行粘贴到对话里

agent 拿到后写入 `cookie.txt`（单行）即可。

---

## 方式 C：手动 F12 获取（回退·给用户的图文步骤）

适用：方式 A 不可用、用户愿意自己操作。无需任何额外依赖。

把下面的步骤完整发给用户（不要省略）：

1. 用电脑浏览器（Chrome / Edge 均可）打开并**登录** https://weibo.com
2. 按 **F12** 打开开发者工具（Mac 上是 `Cmd+Option+I`）
3. 切到 **Network（网络）** 标签
4. 按 **F5 / Cmd+R** 刷新页面
5. 在请求列表里点任意一条发往 `weibo.com` 的请求（如 `config`、`unread` 之类）
6. 在右侧找到 **Request Headers（请求标头）** → 找到 **Cookie:** 这一行
7. **完整复制 Cookie 冒号后面的整行内容**（很长，从 `SCF=...` 一直到结尾，务必复制全）
8. 把复制的内容粘贴回对话

校验：粘贴的内容必须同时包含 `SUB=`、`SUBP=`、`ALF=` 三个字段，否则无效。
