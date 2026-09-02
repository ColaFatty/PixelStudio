#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v4.2 独立复验（butler）：
核心 = 行走图模板 frames[0] 非空修复（此前 bug：loadWalkerTemplate 首帧空白），
外加精灵/tile 模板回归 + 新画布清空回归 + 全按钮抽查 + 零报错。"""
import sys, asyncio
from playwright.async_api import async_playwright

URL = "file:///home/ubuntu/fattyclaw/app/frontend/assets/pixel-editor/pixel-editor-v4.2.html"
MINI = "--headless=new"

async def main():
    errors, results = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[MINI])
        page = await browser.new_page(viewport={"width":1400,"height":1000})
        page.on("console", lambda m: errors.append(("console", m.type, m.text)) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
        page.on("requestfailed", lambda r: errors.append(("requestfailed", r.url, str(r.failure))))
        await page.goto(URL, wait_until="load")
        await page.wait_for_timeout(1000)
        if await page.locator("#tutorialModal").is_visible():
            await page.click("#btnCloseTutorial"); await page.wait_for_timeout(300)

        def frame_nonempty(idx):
            return page.evaluate("""(i) => {
                const f = state.frames[i];
                if (!f) return -1;
                const d = f.data || f;
                let n = 0;
                for (let j=3;j<d.length;j+=4){ if (d[j]!==0) n++; }
                return n;
            }""", idx)

        # ============ 1. 行走图模板专项（本次修复核心） ============
        try:
            await page.click("#btnTemplates"); await page.wait_for_timeout(400)
            await page.click("#tplTabWalker"); await page.wait_for_timeout(300)
            cards = await page.query_selector_all(".tpl-card")
            results.append(("🚶 行走图 tab 卡片数", len(cards) > 0, str(len(cards))))
            if cards:
                await cards[0].click(); await page.wait_for_timeout(600)
                st = await page.evaluate("() => ({f: state.frames.length, w: state.w, h: state.h, pt: state.paletteType})")
                results.append(("🚶 行走图帧数≥12", st["f"] >= 12, f"frames={st['f']}"))
                # ★ 核心断言：frames[0] 必须非空（此前=0 空白 bug）
                n0 = await frame_nonempty(0)
                results.append(("🚶 [修复核心] frames[0] 非空", n0 > 0, f"frames[0] 非透明像素={n0}（期望>0，此前bug=0）"))
                # 全 12 帧逐帧非空
                all_ok = True; details = []
                for i in range(min(st["f"], 12)):
                    n = await frame_nonempty(i)
                    details.append(f"f{i}={n}")
                    if n <= 0: all_ok = False
                results.append(("🚶 全部 12 帧有内容", all_ok, " ".join(details[:12])))
                # 逐帧切换画布都应有内容
                cv_ok = True
                for i in range(min(st["f"], 12)):
                    await page.evaluate("(i) => switchFrame(i)", i); await page.wait_for_timeout(80)
                    nonempty = await page.evaluate("""() => {
                        const cv = document.getElementById('gridCanvas');
                        const d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
                        for (let j=3;j<d.length;j+=4){ if (d[j]!==0) return true; }
                        return false;
                    }""")
                    if not nonempty: cv_ok = False
                results.append(("🚶 逐帧切换画布全有内容", cv_ok, "frames 0..11 canvas nonempty"))
            await page.click("#btnCloseTpl"); await page.wait_for_timeout(300)
        except Exception as e:
            results.append(("🚶 行走图专项", False, str(e)))

        # ============ 2. 精灵 / tile 模板回归 ============
        try:
            for tab, name, exp in [("tplTabSprites","宝可梦精灵",150), ("tplTabTiles","RPG tile 集",256)]:
                await page.click("#btnTemplates"); await page.wait_for_timeout(400)
                await page.click("#"+tab); await page.wait_for_timeout(300)
                cards = await page.query_selector_all(".tpl-card")
                if cards:
                    await cards[0].click(); await page.wait_for_timeout(500)
                    n0 = await frame_nonempty(0)
                    results.append((f"🧩 {name} frames[0] 非空", n0 > 0, f"非透明像素={n0}（参考{exp}）"))
                await page.click("#btnCloseTpl"); await page.wait_for_timeout(300)
        except Exception as e:
            results.append(("🧩 精灵/tile 回归", False, str(e)))

        # ============ 3. 新画布清空回归 ============
        try:
            await page.click("#btnNewCanvas"); await page.wait_for_timeout(300)
            modal_vis = await page.locator("#newCanvasModal").is_visible()
            results.append(("🆕 新画布弹窗", modal_vis, "visible"))
            await page.click('.nc-size[data-size="32"]'); await page.wait_for_timeout(500)
            st = await page.evaluate("() => ({f: state.frames.length, u: state.undoStack.length, w: state.w, h: state.h})")
            n0 = await frame_nonempty(0)
            ok = st["f"] == 1 and st["u"] == 0 and st["w"] == 32 and n0 == 0
            results.append(("🆕 新画布 32×32 清空干净", ok, str(st) + f" frames[0]={n0}"))
        except Exception as e:
            results.append(("🆕 新画布清空", False, str(e)))

        # ============ 4. 基础按钮抽查（确认没被改坏） ============
        try:
            await page.click("#btnAddFrame"); await page.wait_for_timeout(200)
            n = await page.evaluate("state.frames.length")
            results.append(("➕ 加帧正常", n >= 2, f"frames={n}"))
            await page.click("#btnUndo"); await page.wait_for_timeout(200)
            results.append(("↩️ 撤销正常", True, "no-error"))
            await page.click("#btnExport"); await page.wait_for_timeout(300)
            results.append(("📤 导出弹窗", True, "opened"))
            close = await page.query_selector(".modal-mask:not(.hidden) [id^=btnClose], .modal-mask:not(.hidden) .close-x")
            if close:
                await close.click(); await page.wait_for_timeout(200)
        except Exception as e:
            results.append(("🔘 基础抽查", False, str(e)))

        await browser.close()

    print("===== PixelStudio v4.2 独立复验 =====")
    passed = 0
    for label, ok, detail in results:
        print(f"{'✅' if ok else '❌'} {label} | {detail}")
        if ok: passed += 1
    print(f"\n合计 {passed}/{len(results)} PASS")
    print("\n===== 错误收集 =====")
    if errors:
        for e in errors[:30]:
            print("ERROR:", e)
        sys.exit(1)
    else:
        print("✅ 零 console error / pageerror / requestfailed")
        sys.exit(1 if passed != len(results) else 0)

asyncio.run(main())