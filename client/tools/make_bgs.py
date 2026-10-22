#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gomoku 五子棋的菜单与对局底图 —— 程序化背景素材生成器。

用法（在仓根下）：
    python client/tools/make_bgs.py

产出 `client/assets/*.png`，尺寸与被替换的素材完全一致，可直接覆盖。

为什么是程序化：
    这批底图原先随 zan-lang 早期游戏模板一同迁出，未记录来源与授权。
    公开发分发等于把第三方素材权利一并公开，所以改为本地程序化生成——
    产出物没有外部素材来源，也不依赖任何 AI 出图服务。

构图口径（与 runtime 配套）：
    背景是「氛围底图」，运行时按 cover 居中裁剪，棋盘/牌桌/标题叠在上层，
    因此底图中心必须可安全裁剪，不能有主体元素压中心。
    材质一律走方向性纹理（毡面绒毛 / 竹编经纬 / 宣纸纤维 / 木纹年轮），
    刻意避开「纯色 + 随机噪点」那种一眼假的观感。

依赖：pip install pillow numpy
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序化背景材质引擎（纯 numpy + PIL，无外部素材、无 AI 出图）。

这一段是**引擎本体**，会被内嵌进各游戏仓的 `client/tools/make_bgs.py`，
保证每个仓的素材都能被独立复现。

设计口径：
  * 背景图是**氛围底图**——棋盘/牌桌/标题都叠在上层，所以底图必须
    「中心可安全裁剪」（runtime 用 cover 居中裁剪），主体信息不能压中心。
  * 材质要有**方向性**（纤维走向 / 年轮 / 编织经纬 / 宣纸纹理），
    刻意避开「纯色 + 随机噪点」那种一眼假的观感。
  * 输出走索引色 PNG + Floyd–Steinberg 抖动，压体积的同时避免渐变色带。
"""

import math
import os

import numpy as np
from PIL import Image

# --------------------------------------------------------------------------
# 基础噪声
# --------------------------------------------------------------------------


def value_noise(w, h, freq_x, freq_y, seed):
    """随机格点 + 双线性插值的值噪声，返回 [0,1] 的 float32 数组。"""
    rng = np.random.default_rng(seed)
    fx = max(2, int(freq_x))
    fy = max(2, int(freq_y))
    g = rng.random((fy + 1, fx + 1)).astype(np.float32)
    ys = np.linspace(0, fy, h, endpoint=False, dtype=np.float32)
    xs = np.linspace(0, fx, w, endpoint=False, dtype=np.float32)
    y0 = np.floor(ys).astype(np.int32)
    x0 = np.floor(xs).astype(np.int32)
    ty = (ys - y0)[:, None]
    tx = (xs - x0)[None, :]
    # smoothstep 插值权重
    ty = ty * ty * (3.0 - 2.0 * ty)
    tx = tx * tx * (3.0 - 2.0 * tx)
    v00 = g[np.ix_(y0, x0)]
    v01 = g[np.ix_(y0, x0 + 1)]
    v10 = g[np.ix_(y0 + 1, x0)]
    v11 = g[np.ix_(y0 + 1, x0 + 1)]
    top = v00 * (1.0 - tx) + v01 * tx
    bot = v10 * (1.0 - tx) + v11 * tx
    return top * (1.0 - ty) + bot * ty


def fbm(w, h, seed, octaves=5, base=3.0, gain=0.5, lac=2.0, aspect=1.0):
    """分形叠加噪声。aspect 用于把噪声在非正方画布上拉成想要的纤维走向。"""
    total = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    norm = 0.0
    fx, fy = base, max(2.0, base * h / max(1.0, w) / max(0.05, aspect))
    for _ in range(octaves):
        total += amp * value_noise(w, h, fx, fy, seed)
        norm += amp
        amp *= gain
        fx *= lac
        fy *= lac
    return total / max(1e-6, norm)


def ridged(w, h, seed, octaves=4, base=4.0):
    """脊状噪声：山脊/云纹结构，比普通 fbm 更有"笔触感"。"""
    n = fbm(w, h, seed, octaves=octaves, base=base)
    return 1.0 - np.abs(n * 2.0 - 1.0)


def normalize(a):
    lo = float(a.min())
    hi = float(a.max())
    if hi - lo < 1e-6:
        return np.zeros_like(a)
    return (a - lo) / (hi - lo)


def mix(c0, c1, t):
    """两个 RGB 三元组按 t 混合。"""
    t = np.clip(t, 0.0, 1.0)[..., None]
    a = np.array(c0, dtype=np.float32)
    b = np.array(c1, dtype=np.float32)
    return a * (1.0 - t) + b * t


# --------------------------------------------------------------------------
# 光照与构图
# --------------------------------------------------------------------------


def coords(w, h):
    """归一化坐标场，中心为 (0,0)，范围约 [-1,1]。"""
    ys = (np.arange(h, dtype=np.float32) / max(1, h - 1) - 0.5) * 2.0
    xs = (np.arange(w, dtype=np.float32) / max(1, w - 1) - 0.5) * 2.0
    return xs[None, :] * np.ones((h, 1), dtype=np.float32), np.ones((h, 1), dtype=np.float32) * ys[:, None]


def vignette(w, h, strength=0.40, radius=1.18, power=1.45):
    """径向暗角：中心亮、四周沉下去。

    强度刻意压低——暗部梯度太平缓时，索引色量化会把它切成一圈圈
    可见色带（看着像多边形遮罩）。宁可暗角弱，也不要出现阶梯。
    """
    gx, gy = coords(w, h)
    r = np.sqrt(gx * gx + gy * gy) / radius
    v = np.clip(1.0 - strength * np.power(np.clip(r, 0.0, 1.6), power), 0.0, 1.0)
    return v.astype(np.float32)


def key_light(w, h, cx=-0.35, cy=-0.45, radius=1.25, strength=0.26):
    """单向受光场：给材质一个方向性明暗。"""
    gx, gy = coords(w, h)
    d = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2) / radius
    return np.clip(1.0 - strength * np.clip(d, 0.0, 1.0) ** 1.8, 0.0, 1.0).astype(np.float32)


def radial_ring(w, h, r0, r1, softness=0.08, cx=0.0, cy=0.0):
    """金色竞技环的环形带（在归一化坐标下按半径给一个 0..1 的带状权重）。"""
    gx, gy = coords(w, h)
    d = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
    inner = np.clip((d - r0) / max(1e-5, softness), 0.0, 1.0)
    outer = np.clip((r1 - d) / max(1e-5, softness), 0.0, 1.0)
    return (inner * outer).astype(np.float32)


# --------------------------------------------------------------------------
# 材质
# --------------------------------------------------------------------------


def felt_field(w, h, seed, fiber=8.0, depth=0.5):
    """毡面：沿 x 拉长的绒毛（横向短绒）+ 低频染色斑驳 + 一层更细的绒。

    fbm 的 aspect 越大 → 纵向频率越低 → 条带越"横"。
    毡面要的是横向短绒（aspect 大）叠横向斑驳，再加一层细绒打破规律感。
    """
    fuzz = fbm(w, h, seed, octaves=4, base=3.0, aspect=fiber)
    fine = fbm(w, h, seed + 4111, octaves=3, base=9.0, aspect=fiber * 0.6)
    mottle = fbm(w, h, seed + 7717, octaves=3, base=2.4)
    fuzz = np.clip(normalize(fuzz) * 0.72 + normalize(fine) * 0.28, 0.0, 1.0)
    return normalize(fuzz), normalize(mottle)


def weave_field(w, h, seed, cells_x=26, cells_y=18):
    """编织经纬：竹席 / 竹帘用。返回经纬交织后的明暗场。

    经线（竖）宽、纬线（横）扁 → 编织物才是"长条"而不是"方格"。
    """
    ys = np.arange(h, dtype=np.float32)[:, None] / max(1, h - 1) * cells_y
    xs = np.arange(w, dtype=np.float32)[None, :] / max(1, w - 1) * cells_x
    warp = 0.5 + 0.5 * np.cos(2.0 * math.pi * ys)
    weft = 0.5 + 0.5 * np.cos(2.0 * math.pi * xs)
    # 交织：谁在上按格子奇偶交替
    over = ((np.floor(xs).astype(np.int32) + np.floor(ys).astype(np.int32)) % 2).astype(np.float32)
    # 竹节：每条经线中部有一段更亮的实心段
    slat = (np.floor(xs).astype(np.int32) % 3 == 0).astype(np.float32)
    node = np.clip((np.abs(np.cos(2.0 * math.pi * ys)) - 0.72) / 0.28, 0.0, 1.0)
    grain = normalize(fbm(w, h, seed, octaves=3, base=8.0))
    combined = np.where(over > 0.5, warp, weft) * 0.70 + grain * 0.16 + node * slat * 0.14
    return normalize(combined)


def wood_field(w, h, seed, rings=13.0, aspect=4.0):
    """木纹年轮：低频蜿蜒的平行层叠 + 顺纹细纤维。

    年轮用"强扰动的低频正弦"而不是整齐的正弦，条带才会像真的木头。
    """
    gx, gy = coords(w, h)
    warp = fbm(w, h, seed, octaves=5, base=2.2) - 0.5
    # 非线性间距：年轮疏密不均。扰动幅度要克制——太大就把平行年轮扭成涡旋，
    # 看着像火焰/大理石而不像木头。
    phase = gy * rings + warp * 1.7
    band = np.sin(phase * math.pi)
    ring = 0.5 + 0.5 * band
    fiber = normalize(fbm(w, h, seed + 331, octaves=4, base=14.0, aspect=aspect))
    return normalize(ring * 0.62 + fiber * 0.38)


def paper_field(w, h, seed):
    """宣纸：横帘纹 + 竖向长纤维 + 云斑。

    纤维要"看得见"：fbm 的原始分布集中在中间，直接用会糊成一片，
    所以先做一次对比拉伸再交给上层着色。
    """
    lat = normalize(fbm(w, h, seed, octaves=4, base=26.0, aspect=7.0))
    lon = normalize(fbm(w, h, seed + 991, octaves=4, base=30.0, aspect=0.22))
    cloud = normalize(fbm(w, h, seed + 4441, octaves=4, base=2.6))
    raw = normalize(lat) * 0.55 + normalize(lon) * 0.45
    fiber = np.clip((raw - 0.5) * 2.1 + 0.5, 0.0, 1.0)
    return fiber, cloud


def nebula_field(w, h, seed):
    """星云：域扭曲的丝状云 + 星点。返回 (云, 星)。"""
    warp_x = fbm(w, h, seed, octaves=4, base=2.0)
    warp_y = fbm(w, h, seed + 313, octaves=4, base=2.0)
    gx, gy = coords(w, h)
    swirl = np.sin((gx * 2.2 + warp_x * 4.0) * math.pi) * 0.5 + 0.5
    core = normalize(ridged(w, h, seed + 55, octaves=5, base=3.2))
    band = np.clip(core * 0.75 + swirl * 0.25, 0.0, 1.0)
    rng = np.random.default_rng(seed + 9001)
    stars = np.zeros((h, w), dtype=np.float32)
    count = int(w * h / 5200.0)
    ys = rng.integers(0, h, count)
    xs = rng.integers(0, w, count)
    mag = rng.random(count).astype(np.float32) ** 6.0
    stars[ys, xs] = mag
    # 少量大亮星带一点光晕
    big = count // 18
    if big > 0:
        by = rng.integers(0, h, big)
        bx = rng.integers(0, w, big)
        stars[by, bx] = np.maximum(stars[by, bx], 0.9)
    return band, stars


# --------------------------------------------------------------------------
# 出图
# --------------------------------------------------------------------------


def to_image(rgb):
    """float [0,255] 数组 → PIL RGB。"""
    arr = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def save_png(img, path, colors=96, dither=True):
    """索引色 PNG：体积小；抖动用来压掉渐变色带。"""
    if colors and colors > 0:
        q = img.convert("RGB").quantize(
            colors=min(colors, 256),
            method=Image.MEDIANCUT,
            dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE,
        )
    else:
        q = img.convert("RGB")
    q.save(path, optimize=True)
    return os.path.getsize(path)


def to_float(img):
    return np.asarray(img.convert("RGB"), dtype=np.float32)

# --- gomoku：竹席编织 -------------------------------------------------------
# 五子棋。底图走竹编坐垫：经纬交织 + 竹节色阶，暖黄绿调。


def _bamboo(w, h, seed, cells_x=30, cells_y=22):
    comb = weave_field(w, h, seed, cells_x=cells_x, cells_y=cells_y)
    grain = normalize(fbm(w, h, seed + 77, octaves=4, base=6.0))
    t = np.clip(comb * 0.76 + grain * 0.24, 0, 1)
    c_dark = np.array([68, 50, 30], dtype=np.float32)
    c_mid = np.array([128, 100, 56], dtype=np.float32)
    c_light = np.array([192, 166, 106], dtype=np.float32)
    rgb = mix(c_dark, c_mid, t)
    rgb = mix(rgb, c_light, np.clip((t - 0.62) / 0.38, 0, 1) * 0.52)
    lit = key_light(w, h, cx=-0.30, cy=-0.40, strength=0.28)
    rgb *= (0.74 + 0.38 * lit)[..., None]
    rgb *= vignette(w, h, 0.42, 1.18, 1.45)[..., None]
    return to_image(rgb)


def make_menu_bg(w, h, seed=20260106):
    return _bamboo(w, h, seed, cells_x=22, cells_y=30)


def make_menu_bg2(w, h, seed=20260107):
    return _bamboo(w, h, seed, cells_x=12, cells_y=26)


def make_play_bg(w, h, seed=20260108):
    return _bamboo(w, h, seed, cells_x=10, cells_y=24)


# --------------------------------------------------------------------------
# 规格
# --------------------------------------------------------------------------

SPECS = [
    ("menu_bg", 1536, 1024, "make_menu_bg", 20260106),
    ("menu_bg2", 720, 1080, "make_menu_bg2", 20260107),
    ("play_bg", 720, 1080, "make_play_bg", 20260108),]


def main():
    out_dir = os.path.join(ROOT, "client", "assets")
    os.makedirs(out_dir, exist_ok=True)
    for name, w, h, fn, seed in SPECS:
        img = globals()[fn](w, h, seed)
        path = os.path.join(out_dir, name + ".png")
        size = save_png(img, path, colors=200, dither=True)
        print("  %5.1f KB  %s  (%dx%d)" % (size / 1024.0, name + ".png", w, h))
    print("DONE")


if __name__ == "__main__":
    main()
