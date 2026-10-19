#!/usr/bin/env python3
"""aggregate_benchmarks.py — 对标账号聚合分析工具（账号诊断 skill 配套）

把平台搜索结果（JSON）按作者聚合，输出高互动作者排行榜，
用于快速锁定 2-3 个对标账号。平台无关：抖音/B站/小红书等
任何返回 {"articles": [...]} 结构的搜索结果都可用。

输入 JSON 格式（缺失字段自动按 0 处理）：
{
  "articles": [
    {"author": "作者名", "title": "标题",
     "like_count": 0, "collect_count": 0, "comment_count": 0,
     "share_count": 0, "play_count": 0, "danmaku_count": 0}
  ]
}

用法：
  python aggregate_benchmarks.py result1.json [result2.json ...] [--top 25] [--out out.txt]

自动兼容 UTF-8 / UTF-8-BOM / UTF-16 编码（PowerShell 重定向产物）。
输出列：作者 | 上榜条数 | 总赞 | 均赞 | 藏赞比 | 评赞比 | 转发 | 弹幕 | 代表作
排序：总赞降序。判读提示：藏赞比>1=收藏驱动(干货型)，评赞比高=互动驱动。
"""
import argparse
import collections
import json
import sys

FIELDS = ("like_count", "collect_count", "comment_count",
          "share_count", "play_count", "danmaku_count")


def load_json(path):
    """按 utf-8-sig / utf-16 / utf-8 依次尝试解码。"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"无法解码: {path}")


def extract_articles(data):
    """兼容 articles / works / videos 三种常见键名。"""
    if isinstance(data, dict):
        for key in ("articles", "works", "videos"):
            if isinstance(data.get(key), list):
                return data[key]
    if isinstance(data, list):
        return data
    return []


def main():
    ap = argparse.ArgumentParser(description="搜索结果按作者聚合，锁定对标账号")
    ap.add_argument("files", nargs="+", help="一个或多个搜索结果 JSON 文件")
    ap.add_argument("--top", type=int, default=25, help="输出前 N 名作者（默认25）")
    ap.add_argument("--out", default=None, help="结果输出到文件（默认打印到 stdout）")
    args = ap.parse_args()

    agg = collections.defaultdict(
        lambda: {"n": 0, "like": 0, "collect": 0, "comment": 0,
                 "share": 0, "play": 0, "danmaku": 0, "top_title": ""})

    total_articles = 0
    for path in args.files:
        try:
            data = load_json(path)
        except Exception as e:
            print(f"[跳过] {path}: {e}", file=sys.stderr)
            continue
        for a in extract_articles(data):
            if not isinstance(a, dict) or not a.get("author"):
                continue
            total_articles += 1
            v = agg[a["author"]]
            v["n"] += 1
            for f in FIELDS:
                v[f.split("_")[0] if f != "like_count" else "like"] += \
                    a.get(f, 0) or 0
            if not v["top_title"] and a.get("title"):
                t = str(a["title"]).replace("\n", " ")
                v["top_title"] = t[:36]

    rows = sorted(agg.items(), key=lambda kv: -kv[1]["like"])[: args.top]

    lines = [f"输入文件 {len(args.files)} 个，共解析作品 {total_articles} 条，"
             f"作者 {len(agg)} 位，输出 Top {len(rows)}", ""]
    header = (f"{'作者':<20}\t条数\t总赞\t均赞\t藏赞比\t评赞比\t转发\t弹幕\t代表作")
    lines.append(header)
    lines.append("-" * 100)
    for name, v in rows:
        avg_like = v["like"] // max(v["n"], 1)
        col_ratio = v["collect"] / v["like"] if v["like"] else 0
        com_ratio = v["comment"] / v["like"] if v["like"] else 0
        lines.append(
            f"{name[:20]:<20}\t{v['n']}\t{v['like']}\t{avg_like}\t"
            f"{col_ratio:.2f}\t{com_ratio:.2f}\t{v['share']}\t{v['danmaku']}\t"
            f"{v['top_title']}")

    lines.append("")
    lines.append("判读提示：藏赞比>1 = 收藏驱动（实用干货型对标）；"
                 "评赞比显著偏高 = 互动驱动（评论区运营型对标）；"
                 "上榜条数多 = 产能纪律型对标。建议三类各选一个。")

    output = "\n".join(lines)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"OK -> {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
