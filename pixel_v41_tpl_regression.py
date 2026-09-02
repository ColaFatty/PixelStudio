#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v4.1 素材模板回归验证：3 tab 逐个卡片载入 + 画布非空 + 调色板切换"""
import sys, asyncio
from playwright.async_api import async_playwright

URL = "file:///home/ubuntu/fattyclaw/app/frontend/assets/pixel-editor/pixel-editor-v4.1.html"
MINI = "--headless=new"

async def main():
    errors, results = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[MINI])
        page = await browser.new_page(viewport={"width":1400,"height":1000})
        page.on("console", lambda m: errors.append(("console", m.type, m.text)) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
        await page.goto(URL, wait_until="load")
        await page.wait_for_timeout(800)
        if await page.locator("#tutorialModal").is_visible():
            await page.click("#btnCloseTutorial"); await page.wait_for_timeout(300)

        await page.click("#btnTemplates"); await page.wait_for_timeout(400)

        for tab, name in [("tplTabSprites","宝可梦精灵"), ("tplTabTiles","RPG tile 集"), ("tplTabWalker","角色行走图")]:
            await page.click("#"+tab); await page.wait_for_timeout(300)
            cards = await page.query_selector_all(".tpl-card")
            results.append((f"🧩 {name} 卡片数", len(cards) > 0, str(len(cards))))
            # 每个 tab 点第一个卡片验证载入
            if cards:
                await cards[0].click(); await page.wait_for_timeout(400)
                st = await page.evaluate("() => ({f: state.frames.length, w: state.w, h: state.h, pt: state.paletteType, customLen: (state.customPalette||[]).length})")
                ok = st["f"] >= 1 and st["w"] > 1 and st["h"] > 1 and st["pt"] == "custom" and st["customLen"] > 0
                # 画布有非透明像素
                nonempty = await page.evaluate("""() => {
                    const cv = document.getElementById('gridCanvas');
                    const d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
                    for (let i=3;i<d.length;i+=4){ if (d[i]!==0) return true; }
                    return false;
                }""")
                results.append((f"🧩 {name} 首个载入", ok and nonempty, str(st) + f" nonempty={nonempty}"))
                # 若已载多帧行走图则说明动画帧生成正常
                if tab == "tplTabWalker":
                    results.append(("🧩 行走图帧数≥12", st["f"] >= 12, f"frames={st['f']}"))
        await browser.close()

    print("===== PixelStudio v4.1 素材模板回归 =====")
    passed = 0
    for label, ok, detail in results:
        print(f"{'✅' if ok else '❌'} {label} | {detail}")
        if ok: passed += 1
    print(f"\n合计 {passed}/{len(results)} PASS")
    print("===== 错误收集 =====")
    if errors:
        for e in errors[:20]:
            print("ERROR:", e)
        sys.exit(1)
    else:
        print("✅ 零 console error / pageerror")
        sys.exit(1 if passed != len(results) else 0)

asyncio.run(main())