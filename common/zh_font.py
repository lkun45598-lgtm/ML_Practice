"""matplotlib 中文显示设置。

优先使用同时包含中文、拉丁字母与数字的单一字体文件，避免“数字显示成方块”的问题
（部分系统的纯 CJK 字体如 Droid Sans Fallback 不含数字/字母，而 matplotlib 的逐字形
回退在此环境并不可靠）。找不到首选字体时退回到按字体名查找。
"""
import os
import matplotlib
import matplotlib.font_manager as fm

# 首选：已知同时覆盖 中文+拉丁+数字 的字体文件（按优先级）
_PREFERRED_FILES = [
    "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf",  # AR PL SungtiL GB 宋体(简)
    "/usr/share/fonts/truetype/arphic-gkai00mp/gkai00mp.ttf",  # AR PL KaitiM GB 楷体(简)
]
# 次选：按字体名查找（部分系统装有这些字体）
_NAME_CANDIDATES = ["WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "Noto Sans CJK SC",
                    "Source Han Sans SC", "SimHei", "Microsoft YaHei"]


def set_chinese_font():
    """设置 matplotlib 中文字体，返回所用字体名（找不到返回 None）。"""
    # 1) 首选字体文件
    for path in _PREFERRED_FILES:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            name = fm.FontProperties(fname=path).get_name()
            matplotlib.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name
    # 2) 退回按字体名
    available = {f.name for f in fm.fontManager.ttflist}
    chosen = next((n for n in _NAME_CANDIDATES if n in available), None)
    matplotlib.rcParams["font.sans-serif"] = ([chosen] if chosen else []) + ["DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    if chosen is None:
        print("[警告] 未找到中文字体，图中中文可能显示为方块。")
    return chosen
