---
name: weibo-lottery
description: 微博转发/评论抽奖全流程。当用户给出一条微博链接，要求对其转发或评论做抽奖（爬取参与者、去重、随机抽 N 人、可按话题过滤、输出 CSV/Excel 名单）时使用。关键词：微博抽奖、转发抽奖、评论抽奖、weibo lottery、抽一个人、转发去重、话题过滤抽奖、爬转发、爬评论。基于开源项目 nghuyong/WeiboSpider 的解析逻辑改写。
license: MIT
---

# 微博转发/评论抽奖

对一条微博的**转发者**或**评论者**做公平抽奖：明确需求 → 获取 cookie → 爬取全部参与者 → 按用户去重 → 加密级随机抽 N 人 → 输出表格名单（CSV / Excel）。可选「话题过滤」，只让转发文案含指定话题的人参与。

> 数据接口与解析逻辑参考开源项目 [nghuyong/WeiboSpider](https://github.com/nghuyong/WeiboSpider)（MIT）。本 skill 是面向「抽奖」场景的自包含改写，运行时不依赖该仓库。详见 LICENSE。

## 何时使用

用户给出微博链接并要求：抽奖 / 抽一个（几个）人 / 转发抽奖 / 评论抽奖 / 带话题 `#xxx#` 的才算有效 / 输出中奖名单。

## 前置依赖

```bash
pip install python-dateutil openpyxl playwright
python -m playwright install chromium      # 安装浏览器内核，自动取 cookie 必需
```

- `python-dateutil`：解析微博时间。**必需**。
- `openpyxl`：输出 Excel（只用 CSV 可不装）。
- `playwright`：**默认依赖**。本 skill 默认用浏览器自动化自动获取 cookie（见第 1 步），桌面环境请直接安装。
  - ⚠️ **务必同时执行 `python -m playwright install chromium`**——只 `pip install playwright` 没装内核，弹窗会失败。
  - 仅当运行在**无图形界面**的服务器 / 容器 / CI 时，才可跳过 playwright，改用手动粘贴 cookie。

建议用隔离 venv 运行，之后用该 venv 的 python 跑脚本。

---

## 完整流程（6 步）

### 第 0 步：⭐ 先和用户对齐需求（务必先问，再动手）

在做任何爬取前，**必须先确认以下 4 件事**（用户没说全就主动问），这样最后才能做出用户想要的表格：

1. **抽哪个区**：转发区，还是评论区？（也可能两个都要，各抽各的）
   - 链接带 `#repost` 通常=转发；带 `#comment`=评论。但仍要跟用户确认。
2. **抽什么内容/奖项**：抽几人、每个奖项叫什么（如「大月卡」「648」「小月卡」）。
   - 例：「转发抽一位·648」「评论抽一位·小月卡」。
3. **是否话题过滤**：是否要求转发文案必须含某些话题（如 `#刃恒99#` `#千冶刃值得#`）才算有效参与。
4. **最终表格形式**：输出 CSV 还是 Excel；表格里要哪些列（默认：奖项 / 昵称 / 用户ID / IP属地 / 主页）。

把这些落成一句明确的执行计划复述给用户，再继续。

### 第 1 步：获取 Cookie（⭐ 默认走浏览器自动化，自动安装 playwright）

抽奖需要一份**已登录微博账号**的 cookie（核心字段 `SUB`/`SUBP`/`ALF`）。
**登录必须用户本人完成**（平台安全机制，无法自动化）；自动化的只是「登录后取出 cookie」。

**默认方式 = 浏览器自动化自动取 cookie**。除非运行在无图形界面环境，否则 agent 应直接走这条路径，**不要**先问用户要手动粘贴的 cookie。完整说明见 `references/get_cookie.md`。

#### 默认：浏览器自动化自动取（弹窗登录 → 自动写 cookie）

1. **先确保浏览器能力就绪**（默认就做，不要跳过）：
   - 若 agent 已接入现成的浏览器自动化能力（接管用户日常浏览器 / clawbrowser / Playwright MCP / browser-use / Selenium 等），**优先复用它**，不要从零硬写。
   - 否则**直接安装本包默认依赖 playwright** 并用附带脚本：
     ```bash
     pip install playwright && python -m playwright install chromium
     ```
2. **提示用户准备登录**：告诉用户"接下来会弹出一个浏览器窗口，请在里面登录微博（扫码/账密），登录后我会自动取走 cookie"，等用户回复"继续"再弹窗。
3. **运行自动取 cookie 脚本**：
   ```bash
   python scripts/optional/get_cookie_rpa.py --out ./cookie.txt --timeout 300
   ```
   - 成功 stdout 打印 `COOKIE_OK`，cookie 已写入 `--out`；用持久化 profile，下次通常免登录。
   - 超时未登录退出码 2 → 才回退到手动方式。

#### 回退：手动获取（仅当无图形界面 / playwright 装不上 / RPA 失败）

把 `references/get_cookie.md` 里的 F12 图文步骤完整发给用户，让其复制 Cookie 整行粘贴；agent 写入 `cookie.txt`（单行）。无任何依赖，但需用户手动操作。

> 💡 给 agent 的提醒：核心流程对 cookie 来源完全解耦——无论自动还是手动，最终拿到一份**单行、含 SUB/SUBP/ALF 的有效 cookie** 写入 `cookie.txt` 即可。但**默认应主动走自动化，把手动当兜底**。

**验证 cookie 有效性**（强烈建议先验证再爬）：

```bash
python -c "
import urllib.request, json
mid='<数字mid；base62短码先转，见关键坑>'
cookie=open('cookie.txt').read().strip()
url=f'https://weibo.com/ajax/statuses/repostTimeline?id={mid}&page=1&count=10'
req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Cookie':cookie,'Referer':'https://weibo.com/','X-Requested-With':'XMLHttpRequest'})
d=json.loads(urllib.request.urlopen(req,timeout=20).read())
print('total=',d.get('total_number'),'thispage=',len(d.get('data',[])))
"
```
`total` 有值且 `thispage>0` 即有效。

### 第 2 步：爬取全部参与者

```bash
python scripts/crawl.py \
    --type repost \
    --mid R1GxtvZX3 \
    --cookie /path/to/cookie.txt \
    --out /path/to/output
```
- `--type repost`（转发）或 `comment`（评论）。`--mid` 直接传链接里的原样字符串（base62 或纯数字，自动识别）。
- 长任务用后台运行（转发上万条会跑几分钟），等自然结束（脚本会打印 `RESULT_FILE=<jsonl路径>`）。
- 输出 `output/repost_<时间戳>.jsonl` / `comment_<时间戳>.jsonl`，每行含 `content`（文案，话题过滤用）、`user._id`、`ip_location`、`created_at`。
- 接口有损耗：实际爬到条数通常略少于接口报告的 `total_number`（差额是已删除/无权限条目），正常。

### 第 3 步：去重 + 抽奖 + 输出名单

```bash
python scripts/lottery.py \
    --jsonl /path/to/output/repost_xxx.jsonl \
    --n 1 \
    --label "转发抽一位·大月卡" \
    --tags "#刃恒99#" "#千冶刃值得#" \
    --exclude-uid 5634207347 \
    --format xlsx \
    --winners-out /path/to/output/中奖名单.xlsx \
    --pool-out /path/to/output/有效参与名单.xlsx
```
- `--n` 抽几人；`--label` 奖项名；`--tags` 可选话题过滤（**同时**含所有话题才有效）；`--format csv|xlsx`。
- **话题是「完整精确匹配」，绝不模糊/子串**：脚本会把文案里 `#...#` 解析成完整话题 token 再精确比对。要求 `#cp#` 时，`#cp99#`、`#cphh#` **一律不命中**。tag 写成 `#cp#` / `#cp` / `cp` 都等价。
- `--exclude-uid` 可选，从参与池**剔除指定用户ID**（可多个，空格分隔），常用于**去掉博主本人**、小号或工作人员。博主 UID 即微博链接里 `weibo.com/<UID>/...` 的那段数字。统计行会显示「剔除指定UID N 条」。注意：博主通常不会转发自己的微博，剔除转发池时人数常不变属正常；评论池则可能命中。
- 去重按 `user._id`：一人多次只算一次，保证一人一票。

### 第 4 步：展示结果

展示中奖名单（与参与名单）文件，并在回复里用表格列出中奖者（昵称/UID/IP属地/主页）和抽奖池数据（原始数/有效数/去重人数）。

---

## 常见追加需求

- **转发+评论各抽一人**：分别爬 repost 和 comment、各自抽 1 人，再合并成一张表给用户。
- **重抽 / 改人数**：名单不用重爬，直接重跑第 3 步（改 `--n`）。
- **覆盖原文件**：用户说"修改原来那个文档/废弃刚才的"，把 `--winners-out` 指向同一文件名即可覆盖，并在备注注明"重新开奖，原中奖者作废"。

## 关键坑（务必注意）

1. **先问需求再动手**：第 0 步的 4 个问题（转发/评论、奖项人数、话题过滤、表格形式）没确认清楚就别爬。
2. **cookie 默认走浏览器自动化**：桌面环境默认安装 playwright（含 `playwright install chromium`）并用 RPA 弹窗自动取 cookie，不要默认让用户手动粘贴；仅无图形界面时才回退手动 F12。
3. **纯数字 mid 不要再做 base62 转换**——crawl.py 内部 `resolve_mid()` 自动判断（纯数字原样、短码才转）。早期曾因二次解码爬空。
4. **cookie 必须含 SUB/SUBP/ALF**，否则接口返回空或被重定向到登录页。
5. **转发 vs 评论别搞混**：repostTimeline=转发；buildComments=评论。
6. **重复转发打榜型微博**：接口报上万条转发，去重后独立用户可能只有几百（同一批人反复刷）。去重对公平至关重要，向用户说明真实参与人数=去重后人数。
7. **IP 属地清洗**：原始字段可能带"发布于 "前缀，crawl.py 已清洗。

---

## 维护 / 同步上游（接口变更时怎么修）

本 skill 的爬取脚本是**自包含**的——已把上游 `nghuyong/WeiboSpider` 的解析逻辑内联进 `scripts/crawl.py`，**运行时不依赖、也不要 git pull 那个仓库**。原因：真正会变的是微博自家的接口和风控（仓库说了不算），而仓库基于老版 Scrapy、在新 Python 上跑不起来，运行时拉取只会引入兼容性问题。但上游仓库要留作「维护字典」：**平时不依赖它，坏了时查阅它**。

### 触发信号（什么时候说明接口可能变了）

- 爬取脚本秒退、`total_number` 为 None 或 0，但 cookie 刚取且有效。
- 爬到的条数为 0，或解析后 `user._id` / `nick_name` / `content` 大面积为空。
- 接口返回 HTTP 4xx/302（被重定向到登录页）或 JSON 里 `ok != 1`。
- 话题过滤后有效数异常（如文案字段名变了，导致全部被过滤掉）。

### 诊断三步

1. **先排除 cookie**：重取新 cookie，再跑第 1 步末尾的「验证 cookie 有效性」探针。能返回 `total` 就不是接口问题，是 cookie 过期。
2. **裸调接口看原始 JSON**：直接 `urllib` 请求一次，把返回的顶层 key 和第一条 item 的 key 打印出来，和脚本里假设的字段名比对：
   ```bash
   python -c "
   import urllib.request, json
   mid='<数字mid>'; cookie=open('cookie.txt').read().strip()
   url=f'https://weibo.com/ajax/statuses/repostTimeline?id={mid}&page=1&count=5'
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Cookie':cookie,'Referer':'https://weibo.com/','X-Requested-With':'XMLHttpRequest'})
   d=json.loads(urllib.request.urlopen(req,timeout=20).read())
   print('top keys:', list(d.keys()))
   if d.get('data'): print('item keys:', list(d['data'][0].keys()))
   "
   ```
3. **对照上游解析逻辑**：打开上游最新的 `weibospider/spiders/common.py`，定位 `parse_tweet_info`（转发/微博解析）、`url_to_mid`（base62 解码）、评论解析处，看上游把字段读到哪、有没有改名/换路径。

### 字段映射表（脚本 ↔ 接口）

`scripts/crawl.py` 当前依赖这些接口字段，接口改了对照改这里：

| skill 内字段 | 接口端点 | 接口原字段 | 说明 |
|---|---|---|---|
| 转发列表 | `ajax/statuses/repostTimeline` | `data[]` | 每页转发数组 |
| 评论列表 | `ajax/statuses/buildComments` | `data[]` | 每页评论数组，翻页靠 `max_id` |
| 总数 | 两者 | `total_number` | 用于估算页数/进度 |
| 文案（话题过滤） | 转发 item | `text_raw` → `content` | 话题过滤读 `content` |
| 用户ID | item | `user.id` / `user.idstr` → `user._id` | 去重主键 |
| 昵称 | item | `user.screen_name` → `user.nick_name` | |
| IP属地 | item | `source` / `region_name` → `ip_location` | 需去「发布于 」前缀 |
| 发布时间 | item | `created_at` | |

### 修复流程

1. 在 `scripts/crawl.py` 里改对应的字段读取或接口 URL。
2. 用「诊断第 2 步」的探针确认新字段能拿到值。
3. 跑一次小量真实抓取（一页）验证清洗、去重正常。
4. **改完务必更新上面的字段映射表**，并记一行「YYYY-MM-DD 微博把 X 改成 Y，已同步」。

### 变更日志

- 2026-06-29：skill 初版字段映射如上表（基于当时的 repostTimeline / buildComments 接口）。
