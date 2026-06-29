#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博 Cookie 自动获取 RPA 脚本（基于 Playwright）—— 可选模块

Part of the weibo-lottery skill. MIT License. Copyright (c) 2026 vivian.
注意：本脚本是【可选】的。核心爬取+抽奖流程不依赖它。
仅当 agent 无其他浏览器自动化能力、且本机有图形界面并已装 playwright 时使用。

作用：弹出一个可见浏览器窗口 → 打开 weibo.com → 等待用户登录（扫码/账密）
     → 登录成功后自动读取浏览器 cookie → 写入 cookie.txt（单行，weibo 接口可直接用）。

用户只需在弹出的窗口里登录一次（这一步平台安全机制要求本人操作，无法自动化），
其余「找请求、复制 Cookie 整行」的繁琐步骤全部由脚本代劳。

用法:
    python get_cookie_rpa.py --out /path/to/cookie.txt [--timeout 300] [--reuse-profile]

参数:
    --out            cookie 输出文件路径（必填）
    --timeout        等待登录的最长秒数，默认 300（5 分钟）
    --reuse-profile  尝试复用一个持久化 profile（下次免登录）。默认开启持久化目录。
    --profile-dir    持久化 profile 目录，默认在 cookie 输出同级的 .wb_browser_profile
    --keep-open      读到 cookie 后不自动关闭浏览器（调试用）

退出码: 0 成功；非 0 失败。成功时 stdout 打印 COOKIE_OK 与字段校验结果。
"""
import argparse
import os
import sys
import time

REQUIRED_FIELDS = ["SUB", "SUBP", "ALF"]  # 微博鉴权核心字段，缺失则 cookie 无效


def cookies_to_header(cookies):
    """把 Playwright 的 cookie 列表拼成单行 Cookie 头字符串。"""
    parts = []
    seen = set()
    for c in cookies:
        name = c.get("name")
        val = c.get("value", "")
        if not name or name in seen:
            continue
        seen.add(name)
        parts.append(f"{name}={val}")
    return "; ".join(parts)


def has_required(cookie_str):
    return all((f + "=") in cookie_str for f in REQUIRED_FIELDS)


def is_logged_in(cookie_str):
    """判定是否已登录：核心字段齐全且 SUB 有实际值。"""
    if not has_required(cookie_str):
        return False
    # SUB 值要足够长才算真正登录态（未登录时可能有占位）
    for kv in cookie_str.split("; "):
        if kv.startswith("SUB="):
            return len(kv) > 20
    return False


def main():
    ap = argparse.ArgumentParser(description="微博 Cookie 自动获取 RPA")
    ap.add_argument("--out", required=True, help="cookie 输出文件路径")
    ap.add_argument("--timeout", type=int, default=300, help="等待登录最长秒数")
    ap.add_argument("--profile-dir", default="", help="持久化 profile 目录")
    ap.add_argument("--keep-open", action="store_true", help="读到cookie后不关闭浏览器")
    args = ap.parse_args()

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    profile_dir = args.profile_dir or os.path.join(
        os.path.dirname(out_path), ".wb_browser_profile"
    )
    os.makedirs(profile_dir, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: 未安装 playwright。请先 pip install playwright 并 "
              "python -m playwright install chromium", file=sys.stderr)
        return 3

    print("[RPA] 正在启动浏览器窗口…（请稍候）", flush=True)
    with sync_playwright() as p:
        # 持久化 context：复用 profile，下次可能免登录
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,  # 必须可见，让用户登录
            viewport={"width": 1200, "height": 820},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        print("[RPA] 打开 weibo.com，请在弹出的窗口中登录（扫码或账密）…", flush=True)
        try:
            page.goto("https://weibo.com/", timeout=60000)
        except Exception as e:
            print(f"[RPA] 打开页面异常（可忽略，继续等待登录）: {e}", flush=True)

        deadline = time.time() + args.timeout
        cookie_str = ""
        last_report = 0
        while time.time() < deadline:
            try:
                cookies = context.cookies()
                cookie_str = cookies_to_header(cookies)
            except Exception:
                cookie_str = ""
            if is_logged_in(cookie_str):
                print("[RPA] 检测到登录成功！正在读取 cookie…", flush=True)
                break
            remain = int(deadline - time.time())
            if remain // 15 != last_report // 15:
                print(f"[RPA] 等待登录中…（剩余 {remain}s）请在浏览器窗口完成登录",
                      flush=True)
                last_report = remain
            time.sleep(2)

        if not is_logged_in(cookie_str):
            print("ERROR: 超时未检测到登录态（缺少 SUB/SUBP/ALF）。"
                  "请确认已在窗口中完成微博登录。", file=sys.stderr)
            if not args.keep_open:
                context.close()
            return 2

        # 写入 cookie 文件
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cookie_str)

        present = [f for f in REQUIRED_FIELDS if (f + "=") in cookie_str]
        print(f"COOKIE_OK 已写入: {out_path}", flush=True)
        print(f"[校验] 核心字段: {', '.join(present)} "
              f"({len(present)}/{len(REQUIRED_FIELDS)})", flush=True)
        print(f"[长度] cookie 字符数: {len(cookie_str)}", flush=True)

        if not args.keep_open:
            print("[RPA] cookie 已获取，3 秒后关闭浏览器…", flush=True)
            time.sleep(3)
            context.close()
        else:
            print("[RPA] --keep-open 已开启，浏览器保持打开。", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
