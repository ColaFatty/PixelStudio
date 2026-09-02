#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v4.3 照片导入优化验收（dev 自测）：
1. 默认参数 = 自动取色 32 色 + 关抖动（导入弹窗默认态断言）
2. 默认导入照片 → 无雪花噪点（边缘变化率低）+ 颜色数 ≤ 32
3. 开启抖动 → 边缘变化率显著升高（证明抖动开关生效）
4. 映射调色板 → 颜色数 = 16（PICO-8）
5. 零 console error / pageerror
"""
import sys, asyncio
from playwright.async_api import async_playwright

URL = "file:///home/ubuntu/fattyclaw/projects/pixel-editor/pixel-editor.html"
PHOTO = "/tmp/pixel_test_photo.png"

async def main():
    errors, results = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width":1400,"height":1000})
        page.on("console", lambda m: errors.append(("console", m.type, m.text)) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
        await page.goto(URL, wait_until="load")
        await page.wait_for_timeout(800)
        if await page.locator("#tutorialModal").is_visible():
            await page.click("#btnCloseTutorial"); await page.wait_for_timeout(300)

        # 画布设为 96×96（照片建议分辨率）
        await page.evaluate("() => { resizeCanvas(96,96); pushHistory(); }")
        await page.wait_for_timeout(200)

        # ============ 1. 弹窗默认态 ============
        await page.set_input_files("#fileInput", PHOTO)
        await page.wait_for_timeout(600)
        default_palette = await page.evaluate("() => document.getElementById('importUsePalette').checked")
        default_count = await page.evaluate("() => document.getElementById('importColorCount').value")
        default_dither = await page.evaluate("() => document.getElementById('importDither').checked")
        countrow_vis = await page.evaluate("() => document.getElementById('importColorCountRow').style.display !== 'none'")
        ditherrow_vis = await page.evaluate("() => document.getElementById('importDitherRow').style.display !== 'none'")
        results.append(("⚙️ 默认：映射调色板=关", default_palette is False, f"checked={default_palette}"))
        results.append(("⚙️ 默认：颜色数=32", default_count == "32", f"value={default_count}"))
        results.append(("⚙️ 默认：抖动=关", default_dither is False, f"checked={default_dither}"))
        results.append(("⚙️ 颜色数行可见（映射关时）", countrow_vis, ""))
        results.append(("⚙️ 抖动行可见（映射关时）", ditherrow_vis, ""))

        async def import_photo_and_measure():
            await page.click("#btnApplyImport"); await page.wait_for_timeout(700)
            return await page.evaluate("""() => {
                const cv = document.getElementById('gridCanvas');
                const d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
                const w = cv.width, h = cv.height;
                const s = new Set(); let npx = 0;
                for (let i=0;i<d.length;i+=4){ if(d[i+3]!==0){ s.add((d[i]<<16)|(d[i+1]<<8)|d[i+2]); npx++; } }
                const key = (i) => (d[i]<<16)|(d[i+1]<<8)|d[i+2];
                let diff = 0, total = 0;
                for (let y=0;y<h;y++) for (let x=0;x<w-1;x++){
                    const o=(y*w+x)*4, o2=o+4;
                    if (d[o+3]===0 || d[o2+3]===0) continue;
                    if (key(o)!==key(o2)) diff++;
                    total++;
                }
                return {colors:s.size, npx, edgeRatio: total? diff/total : 0};
            }""")

        # 用默认参数（自动取色32 + 无抖动）导入照片
        m = await import_photo_and_measure()
        results.append(("🖼️ 默认导入（auto32/无抖动）颜色数≤32", m["colors"] <= 32, f"colors={m['colors']}"))
        results.append(("🖼️ 非透明像素>0", m["npx"] > 0, f"npx={m['npx']}"))
        results.append(("🖼️ 边缘变化率低（无雪花）", m["edgeRatio"] < 0.4, f"ratio={m['edgeRatio']:.3f}"))

        # 重新导入 + 开抖动 → 对比边缘变化率（抖动应显著升高）
        await page.evaluate("() => { resizeCanvas(96,96); pushHistory(); }")
        await page.set_input_files("#fileInput", PHOTO)
        await page.wait_for_timeout(500)
        await page.click("label:has(#importDither)")
        await page.wait_for_timeout(100)
        m2 = await import_photo_and_measure()
        results.append(("🎛️ 开抖动：边缘变化率显著高于默认", m2["edgeRatio"] > m["edgeRatio"] * 1.4, f"no-dither={m['edgeRatio']:.3f} vs dither={m2['edgeRatio']:.3f}"))

        # 映射调色板 → 颜色数应为 16（PICO-8）
        await page.evaluate("() => { resizeCanvas(96,96); pushHistory(); }")
        await page.set_input_files("#fileInput", PHOTO)
        await page.wait_for_timeout(500)
        await page.click("label:has(#importUsePalette)")
        await page.wait_for_timeout(100)
        dither_hidden = await page.evaluate("() => document.getElementById('importDitherRow').style.display === ''")
        results.append(("⚙️ 映射勾选后抖动行仍显示", dither_hidden, ""))
        m3 = await import_photo_and_measure()
        results.append(("🎨 映射调色板颜色数≤16", m3["colors"] <= 16, f"colors={m3['colors']}"))

        await browser.close()

    print("===== PixelStudio v4.3 照片导入验收 =====")
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