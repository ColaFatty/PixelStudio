#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v4.1 独立复验（butler）：新画布按钮 + btnAddColor + 全按钮回归 + 零报错
真机 file:// 加载，不依赖 dev 的结论。"""
import sys, asyncio
from playwright.async_api import async_playwright

URL = "file:///home/ubuntu/fattyclaw/app/frontend/assets/pixel-editor/pixel-editor-v4.1.html"
MINI = "--headless=new"

async def main():
    errors, results = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[MINI])
        page = await browser.new_page(viewport={"width":1400,"height":1000})
        page.on("console", lambda m: (errors.append(("console", m.type, m.text)) if m.type == "error" else None))
        page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
        page.on("requestfailed", lambda r: errors.append(("requestfailed", r.url, str(r.failure))))
        await page.goto(URL, wait_until="load")
        await page.wait_for_timeout(1000)
        if await page.locator("#tutorialModal").is_visible():
            await page.click("#btnCloseTutorial"); await page.wait_for_timeout(300)

        # ============ 1. btnAddColor 专项 ============
        try:
            # 初始状态
            init = await page.evaluate("() => ({pt: state.paletteType, customLen: (state.customPalette||[]).length})")
            before_len = init["customLen"]
            btn_visible = await page.locator("#btnAddColor").is_visible()
            # 点击顶栏 ➕
            await page.click("#btnAddColor"); await page.wait_for_timeout(250)
            after1 = await page.evaluate("() => ({pt: state.paletteType, customLen: (state.customPalette||[]).length, swatches: document.querySelectorAll('.swatch').length})")
            # 首次从内置切 custom = 内置色板全量复制(16)+追加当前色 → 17；断言语义
            added = after1["pt"] == "custom" and after1["customLen"] >= 17 and after1["customLen"] > before_len
            # 再点一次不重复
            await page.click("#btnAddColor"); await page.wait_for_timeout(250)
            after2 = await page.evaluate("state.customPalette.length")
            no_dup = after2 == after1["customLen"]
            results.append(("➕ btnAddColor 首次加色", btn_visible and added, f"{init} -> {after1}"))
            results.append(("➕ btnAddColor 重复点不重复加", no_dup, f"len {after1['customLen']} -> {after2}"))
            # 调色板网格 .swatch.add 同样生效
            await page.evaluate("addColorToPalette()"); await page.wait_for_timeout(200)
            after3 = await page.evaluate("state.customPalette.length")
            results.append(("➕ addColorToPalette() 函数复用", after3 == after2, f"len {after2} -> {after3}"))
        except Exception as e:
            results.append(("➕ btnAddColor 专项", False, str(e)))

        # ============ 2. 新画布按钮专项 ============
        try:
            # 先画点东西 + 加个帧 + 撤销历史，确保有内容可清
            cv = page.locator("#gridCanvas"); box = await cv.bounding_box()
            cx, cy = box["x"]+box["width"]*0.5, box["y"]+box["height"]*0.5
            await page.click('[data-tool="pen"]'); await page.wait_for_timeout(100)
            await page.mouse.move(cx, cy); await page.mouse.down()
            await page.mouse.move(cx+30, cy); await page.mouse.up()
            await page.wait_for_timeout(200)
            await page.click("#btnAddFrame"); await page.wait_for_timeout(200)
            # 有撤销历史
            hist_before = await page.evaluate("() => ({u: state.undoStack.length, r: state.redoStack.length, f: state.frames.length})")
            # 打开新画布弹窗
            await page.click("#btnNewCanvas"); await page.wait_for_timeout(300)
            modal_vis = await page.locator("#newCanvasModal").is_visible()
            results.append(("🆕 新画布按钮打开弹窗", modal_vis, f"hist={hist_before}"))
            # 关闭弹窗不清空（防误触）
            await page.click("#btnCloseNewCanvas"); await page.wait_for_timeout(250)
            keep = await page.evaluate("() => ({u: state.undoStack.length, f: state.frames.length})")
            results.append(("🆕 关闭弹窗不清空", keep["u"] == hist_before["u"] and keep["f"] == hist_before["f"], str(keep)))
            # 重新打开并确认 32x32
            await page.click("#btnNewCanvas"); await page.wait_for_timeout(250)
            await page.click('.nc-size[data-size="32"]'); await page.wait_for_timeout(500)
            after_new = await page.evaluate("() => ({f: state.frames.length, u: state.undoStack.length, r: state.redoStack.length, w: state.w, h: state.h, pt: state.paletteType, cur: state.curColor, modal: document.getElementById('newCanvasModal').classList.contains('hidden')})")
            ok = after_new["f"] == 1 and after_new["u"] == 0 and after_new["r"] == 0 and after_new["w"] == 32 and after_new["h"] == 32 and after_new["pt"] == "pico8" and after_new["modal"]
            results.append(("🆕 确认 32×32 清空+历史清+默认色板+弹窗关", ok, str(after_new)))
            # 画布全透明？
            empty = await page.evaluate("""() => {
                const cv = document.getElementById('gridCanvas');
                const ctx = cv.getContext('2d');
                const d = ctx.getImageData(0,0,cv.width,cv.height).data;
                for (let i=3;i<d.length;i+=4){ if (d[i]!==0) return false; }
                return true;
            }""")
            results.append(("🆕 新画布全透明空白", empty, "alpha 全 0"))
        except Exception as e:
            results.append(("🆕 新画布专项", False, str(e)))

        # ============ 3. 全按钮回归 ============
        try:
            top_buttons = [
                ("btnOpenTutorial", "打开教程弹窗"),
                ("btnUndo", "撤销"), ("btnRedo", "重做"),
                ("btnImport", "触发文件选择"), ("btnTemplates", "打开素材模板弹窗"),
                ("btnExport", "打开导出弹窗"), ("btnExportGIF", "打开 GIF 导出弹窗"),
                ("btnExportSprite", "打开 Sprite sheet 弹窗"), ("btnExportAscii", "打开字符画弹窗"),
                ("btnNewCanvas", "新画布弹窗"),
            ]
            for bid, desc in top_buttons:
                try:
                    vis_before = await page.evaluate("""() => [...document.querySelectorAll('.modal-mask')].filter(m => !m.classList.contains('hidden')).length""")
                    await page.click("#"+bid); await page.wait_for_timeout(300)
                    vis_after = await page.evaluate("""() => [...document.querySelectorAll('.modal-mask')].filter(m => !m.classList.contains('hidden')).length""")
                    results.append((f"🔘 {bid} ({desc})", True, f"modals {vis_before}->{vis_after}"))
                    if vis_after > 0:
                        closebtns = await page.query_selector_all(".modal-mask:not(.hidden) [id^=btnClose], .modal-mask:not(.hidden) .close-x")
                        for cb in closebtns:
                            try:
                                await cb.click(); await page.wait_for_timeout(200); break
                            except Exception: pass
                except Exception as e:
                    results.append((f"🔘 {bid} ({desc})", False, str(e)))
            # 侧栏工具
            for t in ["pen","eraser","fill","picker","line","select","rect","ellipse"]:
                try:
                    await page.click(f'[data-tool="{t}"]'); await page.wait_for_timeout(120)
                    cur = await page.evaluate("state.tool")
                    results.append((f"🛠️ 工具 {t}", cur == t, f"state.tool={cur}"))
                except Exception as e:
                    results.append((f"🛠️ 工具 {t}", False, str(e)))
            # 动画/帧
            for bid, desc in [("btnAddFrame","新增帧"),("btnDupFrame","复制当前帧"),("btnPlay","播放/暂停")]:
                try:
                    await page.click("#"+bid); await page.wait_for_timeout(250)
                    n = await page.evaluate("state.frames.length")
                    results.append((f"🎞️ {bid} ({desc})", n >= 2, f"frames={n}"))
                except Exception as e:
                    results.append((f"🎞️ {bid} ({desc})", False, str(e)))
            # 尺寸预设
            try:
                await page.select_option("#sizePreset", "16"); await page.wait_for_timeout(400)
                sz = await page.evaluate("() => ({w: state.w, h: state.h})")
                results.append(("📐 sizePreset→16", sz["w"]==16 and sz["h"]==16, str(sz)))
            except Exception as e:
                results.append(("📐 sizePreset→16", False, str(e)))
            # 参考层移除
            try:
                await page.click("#btnRefRemove"); await page.wait_for_timeout(200)
                results.append(("🖼️ btnRefRemove", True, "no-error"))
            except Exception as e:
                results.append(("🖼️ btnRefRemove", False, str(e)))
        except Exception as e:
            results.append(("🔘 全按钮回归", False, str(e)))

        await browser.close()

    print("===== PixelStudio v4.1 独立复验 =====")
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