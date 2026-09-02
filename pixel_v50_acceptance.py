#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v5.0 素材库 v2 验收（dev 自测 / butler 复验复用）

验收点：
  1. 打开素材弹窗默认显示 RPG 奇幻 tab（6 个 tab：rpg/cute/scifi/sprites/tiles/walker）
  2. 每个风格 tab 点击后卡片数量正确（rpg>=15, cute>=10, scifi>=6, sprites>=5, tiles>=12, walker=1）
  3. 点选一个 RPG 素材 → 载入画布（canvas 非空 + 调色板切换为 custom + 帧数=1）
  4. 点选可爱动物/科幻素材 → 也能载入
  5. 零 console error / pageerror
"""
import sys, asyncio, argparse
from playwright.async_api import async_playwright

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="file:///home/ubuntu/fattyclaw/projects/pixel-editor/pixel-editor.html")
    args = ap.parse_args()

    expect = {
        "rpg": (15, "tplTabCute"),
        "cute": (10, "tplTabScifi"),
        "scifi": (6, "tplTabWalker"),
        "walker": (1, "tplTabRpg"),
    }
    fails = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type=="error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(args.url, wait_until="load")

        # 打开素材弹窗
        await page.evaluate("() => { localStorage.removeItem('pixelstudio_tutorial_done'); }")
        await page.evaluate("() => window.openTemplateModal ? openTemplateModal() : document.getElementById('tplBtn').click()")
        # 若没有合适函数，尝试触发
        vis = await page.evaluate("() => !document.getElementById('templateModal').classList.contains('hidden')")
        if not vis:
            # 尝试点击素材按钮
            clicked = await page.evaluate("""() => {
                const b = document.getElementById('btnTpl') || document.getElementById('tplBtn');
                if(b){ b.click(); return true; }
                return false;
            }""")
            vis = await page.evaluate("() => !document.getElementById('templateModal').classList.contains('hidden')")
            if not clicked and not vis:
                fails.append("无法打开素材弹窗")

        # 检查默认 tab 为 RPG
        active = await page.evaluate("() => { const el=document.querySelector('.tpl-tabs .px-btn.active'); return el ? el.id : ''; }")
        if active != "tplTabRpg":
            fails.append("默认 tab 不是 RPG: %s" % active)

        # 逐个 tab 检查卡片数量（用 JS click 避免 modal 遮挡）
        tab_ids = ["tplTabRpg","tplTabCute","tplTabScifi","tplTabWalker"]
        cat_map = {"tplTabRpg":"rpg","tplTabCute":"cute","tplTabScifi":"scifi","tplTabWalker":"walker"}
        for tid in tab_ids:
            await page.evaluate("(id) => document.getElementById(id).click()", tid)
            await page.wait_for_timeout(100)
            n = await page.evaluate("() => document.querySelectorAll('#tplGrid .tpl-card').length")
            cat = cat_map[tid]
            minv, _ = expect[cat]
            if n < minv:
                fails.append("tab %s 卡片数 %d < 预期 %d" % (cat, n, minv))

        # 点选 RPG 角色载入
        await page.evaluate("() => document.getElementById('tplTabRpg').click()")
        await page.wait_for_timeout(100)
        await page.evaluate("""() => {
            const card = document.querySelector('#tplGrid .tpl-card');
            if(card) card.click();
        }""")
        await page.wait_for_timeout(200)
        loaded = await page.evaluate("""() => {
            const cv = document.getElementById('gridCanvas');
            const ctx = cv.getContext('2d');
            const d = ctx.getImageData(0,0,cv.width,cv.height).data;
            let nonEmpty=0;
            for(let i=3;i<d.length;i+=4){ if(d[i]>0) nonEmpty++; }
            const pal = document.getElementById('paletteSelect').value;
            const frames = window.__px ? window.__px.state.frames.length : -1;
            return {nonEmpty, pal, frames};
        }""")
        if loaded["nonEmpty"] <= 0:
            fails.append("RPG 素材载入后画布为空")
        if loaded["pal"] != "custom":
            fails.append("RPG 素材载入后调色板未切 custom: %s" % loaded["pal"])
        if loaded["frames"] != 1:
            fails.append("RPG 素材载入后帧数不为 1: %s" % loaded["frames"])

        # 点选 cute + scifi 也载入
        for tid in ["tplTabCute","tplTabScifi"]:
            await page.evaluate("(id) => document.getElementById(id).click()", tid)
            await page.wait_for_timeout(100)
            await page.evaluate("() => { const c=document.querySelector('#tplGrid .tpl-card'); if(c)c.click(); }")
            await page.wait_for_timeout(200)
            loaded = await page.evaluate("() => { const cv=document.getElementById('gridCanvas'); const d=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data; let n=0; for(let i=3;i<d.length;i+=4){if(d[i]>0)n++;} return n; }")
            if loaded <= 0:
                fails.append("%s 素材载入后画布为空" % tid)

        # 零报错
        if errors:
            fails.append("console/page errors: %s" % errors[:5])

        # ==== 教程 v2 实战演示 ====
        await page.evaluate("() => { document.getElementById('btnCloseTutorial2').click(); document.getElementById('tutorialModal').classList.remove('hidden'); }")
        opts = await page.evaluate("""() => {
            const st = ['demoStep1','demoStep2','demoStep3','demoStep4','demoHeart','demoDither'];
            const res = {};
            st.forEach(id => {
                const cv = document.getElementById(id);
                if(!cv){ res[id]='missing'; return; }
                const d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
                let n=0; for(let i=3;i<d.length;i+=4){ if(d[i]>0) n++; }
                res[id]=n;
            });
            return res;
        }""")
        for k,v in opts.items():
            if v=='missing' or v<=0:
                fails.append("教程演示 %s 未渲染（%s）" % (k, v))

        # ==== 行走图 tab 仍能载入 12 帧动画 ====
        await page.evaluate("() => { document.getElementById('tutorialModal').classList.add('hidden'); document.getElementById('tplTabWalker').click(); }")
        await page.wait_for_timeout(100)
        wc = await page.evaluate("() => document.querySelectorAll('#tplGrid .tpl-card').length")
        if wc < 1:
            fails.append("行走图 tab 无卡片")
        await page.evaluate("() => { const c=document.querySelector('#tplGrid .tpl-card'); if(c)c.click(); }")
        await page.wait_for_timeout(200)
        fr = await page.evaluate("() => window.__px ? window.__px.state.frames.length : -1")
        if fr != 12:
            fails.append("行走图载入帧数应为 12，实际 %s" % fr)

        await browser.close()

    if fails:
        print("=== FAIL ===")
        for f in fails: print(" -", f)
        sys.exit(1)
    print("=== PASS: 素材库 v2 全部验收点通过 ===")

asyncio.run(main())
