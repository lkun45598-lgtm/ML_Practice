"""matplotlib 中文显示设置：尝试常见中文字体，找不到则回退并提示。"""
import matplotlib
import matplotlib.font_manager as fm


def set_chinese_font():
    """设置 matplotlib 支持中文，返回所用字体名（找不到返回 None）。"""
    candidates = ["WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "Noto Sans CJK SC",
                  "Source Han Sans SC", "SimHei", "Microsoft YaHei", "Droid Sans Fallback"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.sans-serif"] = [name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name
    matplotlib.rcParams["axes.unicode_minus"] = False
    print("[警告] 未找到中文字体，图中中文可能显示为方块。")
    return None
