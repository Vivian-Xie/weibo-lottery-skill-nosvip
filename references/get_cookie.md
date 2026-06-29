# 获取微博 Cookie（三种方式，按通用性排序）

抽奖流程需要一份**已登录微博账号的 cookie**（核心字段 `SUB`、`SUBP`、`ALF`），用于请求微博的 AJAX 接口。

> ⚠️ 不可自动化的边界：登录这一步（扫码 / 账密 / 验证码）**必须用户本人完成**。
> 任何工具都无法替用户登录——能自动登录就等于能盗号。所谓「自动获取 cookie」，
> 自动化的只是「登录后把 cookie 取出来」这一步，不是登录本身。

agent 应**按下面的顺序**选择方式，优先用最通用、对用户最省事的：

---

## 方式 A：用户直接粘贴 cookie（最通用，默认首选）

适用：任何 agent、任何环境（无图形界面也行）。

请用户：
1. 浏览器登录 https://weibo.com
2. 按方式 B 的步骤复制 Cookie 整行
3. 把这一整行粘贴到对话里

agent 拿到后写入 `cookie.txt`（单行）即可。**这是所有 agent 的最小公约数，永远可用。**

---

## 方式 B：手动 F12 获取（无需任何额外依赖，给用户的图文步骤）

适用：用户愿意自己操作，环境无浏览器自动化能力。

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

---

## 方式 C：浏览器自动化「自动取 cookie」（可选，桌面场景加分项）

适用：**当前 agent 已具备「控制本机浏览器」的能力时**，可省掉用户手动复制粘贴。

### 给 agent 的决策指引（重要）

这一步的本质是：**弹出 / 接管一个浏览器 → 打开 weibo.com → 等用户登录 → 读出 cookie**。
实现这个能力的方式有很多，agent 应**优先复用自己已经具备的浏览器自动化能力，而不是自己从零硬写**：

- ✅ 如果你（agent）能直接**控制用户本机已打开的浏览器**（如通过桌面自动化 / 浏览器扩展 / CDP 连接到用户日常浏览器），**优先用这个**——用户可能已经登录过，体验最好。
- ✅ 如果你接入了某个**浏览器自动化技能 / 工具**（如 clawbrowser、Playwright MCP、browser-use、Selenium 等），调用它打开 weibo.com、等登录、读 cookie 即可。
- ✅ 都没有、但本机能装 Playwright 时，可使用本包附带的参考脚本 `scripts/optional/get_cookie_rpa.py`（见下）。
- ❌ 没有任何浏览器控制能力、或运行在无图形界面的服务器/容器里 → **不要勉强**，直接回退到方式 A / B。

要让 agent 读出的 cookie 满足：单行字符串、用 `; ` 连接、**至少包含 `SUB`、`SUBP`、`ALF`**，写入 `cookie.txt`。

### 附带的 Playwright 参考实现（仅桌面 + 已装 playwright 时）

本包在 `scripts/optional/get_cookie_rpa.py` 提供了一个基于 Playwright 的现成实现，
它会弹出可见浏览器、打开微博、轮询检测登录态、自动写 cookie。**这是可选项，不是必需依赖。**

```bash
# 仅在确认本机有图形界面、且已 pip install playwright + playwright install chromium 时使用
python scripts/optional/get_cookie_rpa.py --out ./cookie.txt --timeout 300
```

- 成功后 stdout 打印 `COOKIE_OK`，cookie 写入 `--out`。
- 用持久化 profile，下次通常免登录。
- 超时未登录退出码 2 → 回退到方式 A / B。

> 设计原则：本 skill 的核心流程（爬取 + 抽奖）**完全不依赖**这个脚本，也不依赖任何特定浏览器自动化技术。
> cookie 怎么来都行，只要拿到一份有效的单行 cookie 即可。
