#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v4.0 按钮逐个验证：真机 file:// 加载 + 逐个点击每种按钮 + 抓 console/pageerror"""
import sys, asyncio
from playwright.async_api import async_playwright

URL = "file:///home/ubuntu/fattyclaw/app/frontend/assets/pixel-editor/pixel-editor-v4.0.html"
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
        # 关闭教程
        if await page.locator("#tutorialModal").is_visible():
            await page.click("#btnCloseTutorial"); await page.wait_for_timeout(300)

        # ---- 工具栏按钮：打开各弹窗并关闭 ----
        top_buttons = [
            ("btnOpenTutorial", "打开教程弹窗"),
            ("btnUndo", "撤销"), ("btnRedo", "重做"),
            ("btnImport", "触发文件选择"), ("btnTemplates", "打开素材模板弹窗"),
            ("btnExport", "打开导出弹窗"), ("btnExportGIF", "打开 GIF 导出弹窗"),
            ("btnExportSprite", "打开 Sprite sheet 弹窗"), ("btnExportAscii", "打开字符画弹窗"),
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

        # ---- 侧栏工具按钮 ----
        for t in ["pen","eraser","fill","picker","line","select","rect","ellipse"]:
            try:
                await page.click(f'[data-tool="{t}"]'); await page.wait_for_timeout(120)
                cur = await page.evaluate("state.tool")
                results.append((f"🛠️ 工具 {t}", cur == t, f"state.tool={cur}"))
            except Exception as e:
                results.append((f"🛠️ 工具 {t}", False, str(e)))

        # ---- 画一笔，供选区/帧测试用 ----
        cv = page.locator("#gridCanvas"); box = await cv.bounding_box()
        cx, cy = box["x"]+box["width"]*0.5, box["y"]+box["height"]*0.5
        await page.mouse.move(cx, cy); await page.mouse.down()
        await page.mouse.move(cx+30, cy); await page.mouse.up()
        await page.wait_for_timeout(200)
        await page.click('[data-tool="pen"]'); await page.wait_for_timeout(100)

        # ---- 动画/帧操作 ----
        for bid, desc in [("btnAddFrame","新增帧"),("btnDupFrame","复制当前帧"),("btnPlay","播放/暂停")]:
            try:
                await page.click("#"+bid); await page.wait_for_timeout(250)
                n = await page.evaluate("state.frames.length")
                results.append((f"🎞️ {bid} ({desc})", n >= 2, f"frames={n}"))
            except Exception as e:
                results.append((f"🎞️ {bid} ({desc})", False, str(e)))

        # ---- 选区操作（先切选区工具并框选）----
        try:
            await page.click('[data-tool="select"]'); await page.wait_for_timeout(120)
            await page.mouse.move(cx, cy); await page.mouse.down()
            await page.mouse.move(cx+20, cy+20); await page.mouse.up()
            await page.wait_for_timeout(250)
            for bid, desc in [("btnSelFlipH","水平翻转"),("btnSelFlipV","垂直翻转"),
                              ("btnSelRotate","旋转90°"),("btnSelCopy","复制"),
                              ("btnSelPaste","粘贴"),("btnSelClear","取消选区")]:
                try:
                    await page.click("#"+bid); await page.wait_for_timeout(200)
                    results.append((f"✂️ {bid} ({desc})", True, "no-error"))
                except Exception as e:
                    results.append((f"✂️ {bid} ({desc})", False, str(e)))
        except Exception as e:
            results.append(("✂️ 选区准备", False, str(e)))

        # ---- 调色板按钮 ----
        try:
            await page.click("#btnAddColor"); await page.wait_for_timeout(250)
            pal = await page.evaluate("() => ({ pt: state.paletteType, customLen: (state.customPalette||[]).length })")
            results.append(("🎨 btnAddColor", True, str(pal)))
            bl = await page.evaluate("(state.customPalette||[]).length")
            await page.click("#btnDelColor"); await page.wait_for_timeout(250)
            al = await page.evaluate("(state.customPalette||[]).length")
            results.append(("🎨 btnDelColor", al <= bl, f"custom {bl}->{al}"))
        except Exception as e:
            results.append(("🎨 btnAddColor/btnDelColor", False, str(e)))

        # ---- 尺寸预设（模拟重开画布 / 缩放）----
        try:
            await page.select_option("#sizePreset", "32"); await page.wait_for_timeout(400)
            sz = await page.evaluate("() => ({w: state.w, h: state.h})")
            results.append(("📐 sizePreset→32", sz["w"]==32 and sz["h"]==32, str(sz)))
        except Exception as e:
            results.append(("📐 sizePreset→32", False, str(e)))

        # ---- 参考层按钮 ----
        try:
            await page.click("#btnRefRemove"); await page.wait_for_timeout(200)
            results.append(("🖼️ btnRefRemove", True, "no-error"))
        except Exception as e:
            results.append(("🖼️ btnRefRemove", False, str(e)))

        await browser.close()

    print("===== 按钮逐个验证结果 =====")
    for label, ok, detail in results:
        print(f"{'✅' if ok else '❌'} {label} | {detail}")
    print("\n===== 错误收集 =====")
    if errors:
        for e in errors[:30]:
            print("ERROR:", e)
        sys.exit(1)
    else:
        print("✅ 零 console error / pageerror / requestfailed")
        sys.exit(0)

asyncio.run(main())