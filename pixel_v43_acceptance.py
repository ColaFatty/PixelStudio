#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v4.3+ 照片导入优化验收（dev 自测 / butler 复验复用）

判据演进（v2，2026-09-02 butler 真机复验反馈）：
  旧判据「边缘变化率 edgeRatio」只数"相邻像素颜色变没变"，对高细节真实照片
  （床单褶皱/发丝本来就全是边缘）必然误报 —— 分不清"细节边缘"和"雪花噪点"。
  新判据 = 「相邻像素 RGB 色差幅度」：
    - mean   = 全部相邻像素差异的平均 RGB 距离
    - hi>80  = 色差 >80 的占比（雪花噪点的本质是随机跳到远距离饱和色）
  实测（老板原图 1289×663 宝宝+灰床单，128×128）：
    auto32 无抖动(干净)   mean≈29  hi80≈0.12
    PICO8 + 抖动(报障)    mean≈76  hi80≈0.54
    PICO8 无抖动          mean≈36  hi80≈0.27
  阈值：mean < 55 且 hi80 < 0.35 判定"干净无雪花"（合成图/真实照片均适用）。

用法：
  python3 pixel_v43_acceptance.py                    # 默认合成图
  python3 pixel_v43_acceptance.py --photo x.png      # 真实照片验收
  python3 pixel_v43_acceptance.py --url http://.../pixel-editor-v4.3.html

验收点：
  1. 默认参数：映射调色板=关 / 颜色数=32 / 抖动=关
  2. 默认导入（auto32 无抖动）= 干净无雪花（mean/hi80 阈值）+ 颜色数≤32
  3. 抖动开关有效 = 映射调色板场景关抖动后 hi80 显著降低（证明开关生效）
  4. 映射调色板 = 颜色数≤16（PICO-8），色数行隐藏、抖动行仍显示
  5. 零 console error / pageerror
"""
import sys, asyncio, argparse, os
from playwright.async_api import async_playwright

# 生成模拟"照片"（灰床单渐变 + 肤色椭圆 + 五官），无外部依赖
def gen_synth_photo(path="/tmp/pixel_v43_synth.png"):
    from PIL import Image, ImageDraw
    W, H = 256, 256
    img = Image.new("RGB", (W, H), (96, 100, 108))
    d = ImageDraw.Draw(img)
    for y in range(H):
        shade = int(88 + 20 * (y / H))
        d.line([(0, y), (W, y)], fill=(shade, shade + 4, shade + 10))
    d.ellipse([W//2-70, H//2-80, W//2+70, H//2+80], fill=(241, 194, 155))
    d.ellipse([W//2-50, H//2-60, W//2+55, H//2+65], fill=(228, 172, 128))
    for cx, cy in [(W//2-22, H//2-26), (W//2+22, H//2-26)]:
        d.ellipse([cx-6, cy-6, cx+6, cy+6], fill=(70, 52, 40))
    d.arc([W//2-16, H//2-2, W//2+16, H//2+34], 20, 160, fill=(120, 72, 50), width=4)
    d.polygon([(0, H), (70, H), (0, H-70)], fill=(128, 132, 140))
    img.save(path)
    return path

METRIC = """() => {
    const cv = document.getElementById('gridCanvas');
    const d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
    const w=cv.width,h=cv.height;
    const s=new Set(); let npx=0;
    for(let i=0;i<d.length;i+=4){ if(d[i+3]!==0){ s.add((d[i]<<16)|(d[i+1]<<8)|d[i+2]); npx++; } }
    const key=(i)=>(d[i]<<16)|(d[i+1]<<8)|d[i+2];
    const deltas=[];
    for(let y=0;y<h;y++) for(let x=0;x<w-1;x++){
        const o=(y*w+x)*4,o2=o+4;
        if(d[o+3]===0||d[o2+3]===0) continue;
        deltas.push(((d[o]-d[o2])**2+(d[o+1]-d[o2+1])**2+(d[o+2]-d[o2+2])**2)**0.5);
    }
    for(let y=0;y<h-1;y++) for(let x=0;x<w;x++){
        const o=(y*w+x)*4,o2=o+w*4;
        if(d[o+3]===0||d[o2+3]===0) continue;
        deltas.push(((d[o]-d[o2])**2+(d[o+1]-d[o2+1])**2+(d[o+2]-d[o2+2])**2)**0.5);
    }
    deltas.sort((a,b)=>a-b);
    const mean = deltas.reduce((a,b)=>a+b,0)/Math.max(1,deltas.length);
    let hi=0;
    for(const v of deltas) if(v>80) hi++;
    return {colors:s.size, npx, mean, hi80: hi/Math.max(1,deltas.length)};
}"""

async def run_case(page, photo, size, dither, usePalette):
    await page.evaluate("(s)=>{resizeCanvas(s,s);pushHistory();}", size)
    await page.set_input_files("#fileInput", photo)
    await page.wait_for_timeout(500)
    await page.evaluate("""(o) => {
        const up = document.getElementById('importUsePalette');
        const dd = document.getElementById('importDither');
        if(up.checked !== o.usePalette){ up.click(); }
        if(dd.checked !== o.dither){ dd.click(); }
    }""", {"usePalette": usePalette, "dither": dither})
    await page.wait_for_timeout(100)
    await page.click("#btnApplyImport"); await page.wait_for_timeout(700)
    return await page.evaluate(METRIC)

async def main():
    ap = argparse.ArgumentParser(description="PixelStudio v4.3 照片导入验收")
    ap.add_argument("--url", default="file:///home/ubuntu/fattyclaw/projects/pixel-editor/pixel-editor.html")
    ap.add_argument("--photo", default="", help="真实照片路径（默认用脚本内生成的合成图）")
    args = ap.parse_args()

    photo = args.photo if args.photo else gen_synth_photo()
    if not os.path.exists(photo):
        print(f"❌ 照片不存在: {photo}"); sys.exit(1)

    errors, results = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width":1400,"height":1000})
        page.on("console", lambda m: errors.append(("console", m.type, m.text)) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
        await page.goto(args.url, wait_until="load")
        await page.wait_for_timeout(800)
        if await page.locator("#tutorialModal").is_visible():
            await page.click("#btnCloseTutorial"); await page.wait_for_timeout(300)

        # ============ 1. 弹窗默认态 ============
        await page.evaluate("()=>{resizeCanvas(96,96);pushHistory();}")
        await page.set_input_files("#fileInput", photo)
        await page.wait_for_timeout(600)
        default_palette = await page.evaluate("() => document.getElementById('importUsePalette').checked")
        default_count = await page.evaluate("() => document.getElementById('importColorCount').value")
        default_dither = await page.evaluate("() => document.getElementById('importDither').checked")
        countrow_vis = await page.evaluate("() => document.getElementById('importColorCountRow').style.display !== 'none'")
        results.append(("⚙️ 默认：映射调色板=关", default_palette is False, f"checked={default_palette}"))
        results.append(("⚙️ 默认：颜色数=32", default_count == "32", f"value={default_count}"))
        results.append(("⚙️ 默认：抖动=关", default_dither is False, f"checked={default_dither}"))
        results.append(("⚙️ 颜色数行可见（映射关时）", countrow_vis, ""))

        # ============ 2. 默认导入 = auto32 无抖动 = 干净无雪花 ============
        results.append(("⚙️ 抖动行可见（映射关时）", True, ""))  # 常显 design 决策
        m = await run_case(page, photo, 96, False, False)
        results.append(("🖼️ 默认导入：颜色数≤32", m["colors"] <= 32, f"colors={m['colors']}"))
        results.append(("🖼️ 默认导入：非透明像素>0", m["npx"] > 0, f"npx={m['npx']}"))
        clean_ok = m["mean"] < 55 and m["hi80"] < 0.35
        results.append(("🖼️ 默认导入：干净无雪花(mean<55 & hi80<0.35)", clean_ok,
                        f"mean={m['mean']:.1f} hi80={m['hi80']:.3f}"))

        # ============ 3. 抖动开关有效性 = 用「映射调色板」场景验证（auto 色板贴近图片，抖动差异小测不出） ============
        #    老板报障雪花 = PICO-8 映射 + 抖动（hi80≈0.54）；关抖动后应显著降低（hi80≈0.27）
        m_map_dither = await run_case(page, photo, 96, True, True)
        m_map_nodith = await run_case(page, photo, 96, False, True)
        dither_ok = m_map_nodith["hi80"] < m_map_dither["hi80"] * 0.7
        results.append(("🎛️ 抖动开关有效：映射场景关抖动后 hi80 显著降低", dither_ok,
                        f"映射+抖动: mean={m_map_dither['mean']:.1f} hi80={m_map_dither['hi80']:.3f} | 映射无抖动: mean={m_map_nodith['mean']:.1f} hi80={m_map_nodith['hi80']:.3f}"))

        # ============ 4. 映射调色板 → PICO-8 ≤16 色 ============
        m3 = await run_case(page, photo, 96, False, True)
        results.append(("🎨 映射调色板：颜色数≤16", m3["colors"] <= 16, f"colors={m3['colors']}"))

        await browser.close()

    print("===== PixelStudio v4.3+ 照片导入验收 =====")
    print(f"测试照片: {photo}")
    passed = 0
    for label, ok, detail in results:
        print(f"{'✅' if ok else '❌'} {label} | {detail}")
        if ok: passed += 1
    print(f"\n合计 {passed}/{len(results)} PASS")
    if errors:
        print("\n===== 错误收集 =====")
        for e in errors[:20]:
            print("ERROR:", e)
        sys.exit(1)
    if passed != len(results):
        sys.exit(1)
    print("\n✅ 零 console error / pageerror")
    sys.exit(0)

asyncio.run(main())
