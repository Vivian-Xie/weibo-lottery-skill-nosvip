#!/usr/bin/env python
# encoding: utf-8
"""
微博转发 / 评论 通用爬取脚本（自包含，不依赖原 WeiboSpider 项目）。

Part of the weibo-lottery skill. MIT License. Copyright (c) 2026 vivian.
数据接口与解析逻辑改写自 https://github.com/nghuyong/WeiboSpider （MIT），在此致谢。

特性:
- 支持两种 mid 输入：base62 短码（如 R1GxtvZX3）或纯数字 mid（如 5304035628291835），自动识别。
- 支持爬转发(repost) 或 评论(comment)。
- 翻页爬到接口连续空页为止，结果实时追加写入 jsonl（中途不丢）。
- 每条记录含 content 字段（转发/评论文案），可用于话题过滤。

用法:
    python crawl.py --type repost  --mid R1GxtvZX3        --cookie cookie.txt --out ./output
    python crawl.py --type repost  --mid 5304035628291835 --cookie cookie.txt --out ./output
    python crawl.py --type comment --mid R1GxtvZX3        --cookie cookie.txt --out ./output

输出: <out>/repost_<时间戳>.jsonl 或 <out>/comment_<时间戳>.jsonl
脚本最后一行打印: RESULT_FILE=<绝对路径>  （供调用方解析）
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.request

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base62_decode(string):
    string = str(string)
    num = 0
    for idx, char in enumerate(string):
        power = len(string) - (idx + 1)
        num += ALPHABET.index(char) * (len(ALPHABET) ** power)
    return num


def reverse_cut_to_length(content, cut_num=4, fill_num=7):
    content = str(content)
    cut_list = [content[i - cut_num if i >= cut_num else 0:i]
                for i in range(len(content), 0, -cut_num)]
    cut_list.reverse()
    result = []
    for i, item in enumerate(cut_list):
        s = str(base62_decode(item))
        if i > 0 and len(s) < fill_num:
            s = (fill_num - len(s)) * "0" + s
        result.append(s)
    return "".join(result)


def resolve_mid(raw):
    """纯数字 -> 原样；base62 短码 -> 转数字 mid。"""
    raw = str(raw).strip()
    if raw.isdigit():
        return raw
    return str(int(reverse_cut_to_length(raw)))


def parse_time(s):
    try:
        import dateutil.parser
        return dateutil.parser.parse(s).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return s


def parse_user(data):
    return {
        "_id": str(data.get("id", "")),
        "nick_name": data.get("screen_name", ""),
        "verified": data.get("verified", False),
        "followers_count": data.get("followers_count"),
        "location": data.get("location"),
    }


def parse_repost(data):
    content = (data.get("text_raw") or "").replace("\u200b", "")
    return {
        "_id": str(data.get("mid", "")),
        "created_at": parse_time(data.get("created_at", "")),
        "ip_location": (data.get("region_name") or "").replace("发布于 ", "").replace("发布于", "").strip(),
        "content": content,
        "user": parse_user(data.get("user", {}) or {}),
    }


def parse_comment(data):
    content = (data.get("text_raw") or data.get("text") or "")
    content = re.sub(r"<[^>]+>", "", content).replace("\u200b", "")
    return {
        "_id": str(data.get("id", "")),
        "created_at": parse_time(data.get("created_at", "")),
        "ip_location": (data.get("source") or "").replace("来自", "").strip(),
        "content": content,
        "user": parse_user(data.get("user", {}) or {}),
    }


def fetch(url, cookie, retry=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": cookie,
        "Referer": "https://weibo.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
    }
    last_err = None
    for _ in range(retry):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as e:  # noqa
            last_err = e
            time.sleep(3)
    raise last_err


def crawl_repost(mid, cookie, fout):
    total_written, page, empty = 0, 1, 0
    while True:
        url = (f"https://weibo.com/ajax/statuses/repostTimeline?"
               f"id={mid}&page={page}&moduleID=feed&count=20")
        try:
            data = fetch(url, cookie)
        except Exception as e:  # noqa
            print(f"[第{page}页] 请求失败，停止: {e}")
            break
        items = data.get("data", []) or []
        if page == 1 and data.get("total_number") is not None:
            print(f"[信息] 接口报告总转发数: {data.get('total_number')}")
        if not items:
            empty += 1
            if empty >= 3:
                print(f"[第{page}页] 连续空页，结束")
                break
            page += 1
            time.sleep(1)
            continue
        empty = 0
        for it in items:
            try:
                rec = parse_repost(it)
            except Exception:  # noqa
                continue
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total_written += 1
        fout.flush()
        if page % 5 == 0 or page == 1:
            print(f"[进度] 转发 {page} 页，累计 {total_written} 条")
        page += 1
        time.sleep(0.6)
    return total_written


def crawl_comment(mid, cookie, fout):
    total_written, max_id, page, empty = 0, 0, 0, 0
    while True:
        page += 1
        if max_id == 0:
            url = (f"https://weibo.com/ajax/statuses/buildComments?"
                   f"is_reload=1&id={mid}&is_show_bulletin=2&is_mix=0&count=20")
        else:
            url = (f"https://weibo.com/ajax/statuses/buildComments?"
                   f"is_reload=1&id={mid}&is_show_bulletin=2&is_mix=0&max_id={max_id}&count=20")
        try:
            data = fetch(url, cookie)
        except Exception as e:  # noqa
            print(f"[第{page}页] 请求失败，停止: {e}")
            break
        items = data.get("data", []) or []
        if page == 1 and data.get("total_number") is not None:
            print(f"[信息] 接口报告总评论数: {data.get('total_number')}")
        if not items:
            empty += 1
            if empty >= 2:
                print(f"[第{page}页] 无更多评论，结束")
                break
            time.sleep(1)
            continue
        empty = 0
        for it in items:
            try:
                rec = parse_comment(it)
            except Exception:  # noqa
                continue
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total_written += 1
        fout.flush()
        if page % 5 == 0 or page == 1:
            print(f"[进度] 评论 {page} 页，累计 {total_written} 条")
        max_id = data.get("max_id", 0)
        if not max_id:
            print(f"[第{page}页] max_id 为空，结束")
            break
        time.sleep(0.6)
    return total_written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=["repost", "comment"], required=True)
    ap.add_argument("--mid", required=True, help="base62 短码或纯数字 mid")
    ap.add_argument("--cookie", required=True, help="cookie.txt 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    args = ap.parse_args()

    with open(args.cookie, "rt", encoding="utf-8") as f:
        cookie = f.read().strip()
    mid = resolve_mid(args.mid)
    os.makedirs(args.out, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    out_path = os.path.abspath(os.path.join(args.out, f"{args.type}_{ts}.jsonl"))

    print(f"[开始] type={args.type} mid={mid}")
    with open(out_path, "wt", encoding="utf-8") as fout:
        if args.type == "repost":
            n = crawl_repost(mid, cookie, fout)
        else:
            n = crawl_comment(mid, cookie, fout)
    print(f"[完成] 共写入 {n} 条  ->  {out_path}")
    print(f"RESULT_FILE={out_path}")


if __name__ == "__main__":
    main()
