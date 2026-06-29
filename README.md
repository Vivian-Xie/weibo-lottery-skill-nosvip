# weibo-lottery · 微博转发/评论抽奖 Skill

一个自包含、可跨 agent 移植的 **微博转发 / 评论抽奖** 技能包：给一条微博链接，自动爬取全部转发者或评论者 → 按用户去重 → 加密级随机抽 N 人 → 输出 CSV / Excel 中奖名单。支持「话题过滤」（只让转发文案含指定话题的人参与）。

> 本项目的微博数据接口与解析逻辑改写自开源项目
> **[nghuyong/WeiboSpider](https://github.com/nghuyong/WeiboSpider)**（MIT License）。
> 在此致谢原作者。详见 [LICENSE](./LICENSE) 的 Third-Party Attribution 一节。

## 特性

- 🎯 **转发 / 评论双模式**：`repostTimeline` 与 `buildComments` 接口，自动翻页爬全。
- 🏷️ **话题过滤**：只保留转发文案同时包含指定话题（如 `#cp99#` ）的有效参与者。
- 🔁 **按用户去重**：同一人多次转发/评论只算一次，保证一人一票。
- 🎲 **公平抽奖**：`random.SystemRandom` 随机，可抽多人。
- 📊 **CSV / Excel 输出**：中奖名单 + 完整参与名单。
- 🔌 **cookie 获取能力**：默认引导用户粘贴 / F12；浏览器自动化为可选模块。

## 目录结构

```
weibo-lottery-skill/
├── SKILL.md                       # 技能说明（agent 读取的主文件，含完整流程与维护手册）
├── README.md                      # 本文件（GitHub 首页）
├── LICENSE                        # MIT + 上游 cite
├── requirements.txt               # 必需依赖（playwright 为可选，见下）
├── scripts/
│   ├── crawl.py                   # 统一爬取（转发/评论，自动识别 mid，自包含）
│   ├── lottery.py                 # 去重 + 话题过滤 + 随机抽 N 人 + CSV/Excel 输出
│   └── optional/
│       └── get_cookie_rpa.py      # 【可选】Playwright 弹窗登录自动取 cookie（仅桌面场景）
└── references/
    ├── get_cookie.md              # cookie 获取总指引（三种方式，能力中立）
    └── get_cookie_manual.md       # 纯手动 F12 图文步骤（降级备份）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt   # python-dateutil + openpyxl（playwright 可选，已注释说明）
```

### 2. 准备 cookie

需要一份**已登录微博账号**的 cookie（含 `SUB`/`SUBP`/`ALF`）。最通用的方式是让用户登录 weibo.com 后复制整行 Cookie 粘贴，写入 `cookie.txt`。详细三种方式见 [`references/get_cookie.md`](./references/get_cookie.md)。

> ⚠️ 登录必须用户本人完成，工具只能在登录后取出 cookie——任何工具都无法替用户登录。

### 3. 爬取参与者

```bash
python scripts/crawl.py --type repost --mid R1GxtvZX3 --cookie cookie.txt --out ./output
# 评论：--type comment
```

### 4. 去重 + 抽奖

```bash
python scripts/lottery.py \
    --jsonl ./output/repost_xxxxxx.jsonl \
    --n 1 --label "转发抽一位·大月卡" \
    --format xlsx \
    --winners-out ./output/中奖名单.xlsx \
    --pool-out ./output/有效参与名单.xlsx

# 话题过滤：追加 --tags "#cp99#" "#xxx值得#"
```

## 作为 Agent Skill 使用

把整个 `weibo-lottery-skill/` 目录放入你的 agent 技能目录即可。`SKILL.md` 顶部的 YAML frontmatter（`name` / `description`）用于技能发现；正文是 agent 执行时遵循的完整流程.

## 关于浏览器自动化（cookie 自动获取）

cookie 自动获取被设计为**可选、能力中立**：

- 若 agent 自身具备「控制本机浏览器」的能力（接管用户日常浏览器 / clawbrowser / Playwright MCP / browser-use / Selenium 等），应**优先复用**它来自动取 cookie，而不是从零硬写。
- 无浏览器控制能力的环境直接人工在浏览器中打开www.weibo.com F12(检查） → Network → 刷新 → 复制 Cookie 整行。

## 维护

微博接口偶尔会变（字段改名、风控调整）。`SKILL.md` 的「维护 / 同步上游」一节提供了修复流程：运行时不依赖上游仓库，出问题时再对照上游 `common.py` 的解析逻辑手动同步。

## 合规与免责声明

- 本工具仅用于**对自己发布的微博**做转发/评论抽奖等合法、正当用途。
- 请遵守微博平台的用户协议与 robots 规则，控制请求频率，**不要用于大规模数据采集、商业爬取或侵犯他人隐私**。
- 抽奖涉及的用户公开信息（昵称、主页、IP 属地）请妥善保管，公示中奖名单时注意保护隐私。
- 使用本工具产生的任何后果由使用者自行承担，作者不承担责任。

## License

[MIT](./LICENSE) © 2026 VivianX。上游 [nghuyong/WeiboSpider](https://github.com/nghuyong/WeiboSpider)（MIT）已在 LICENSE 中署名致谢。
