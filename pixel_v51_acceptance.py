#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PixelStudio v5.1 验收（dev 自测 / butler 复验复用）

验收点（对应本批 6 项改动）：
  P0  tauri/dist/index.html 与主文件 md5 一致（脚本外部检查，见 main 尾部）
  P1.1 播放帧率联动：改 exportGifDelay → 播放 tick 间隔跟着变（setTimeout spy 实测）
  P1.2 localStorage 满时 saveDraft → toast 显示（实测填爆 storage 触发）
  P2.1 科幻素材 12 个：逐个点卡片载入画布成功（canvas 非空）
  P2.2 自定义尺寸模态框：①newCanvas→custom 走弹窗，确定后清空画布到 WxH ②取消不清空
       ③sizePreset→custom resize 到 WxH
  6.  「循坏」错字已修
  附加：零 console error / pageerror
"""
import sys, asyncio, argparse, subprocess, hashlib
from playwright.async_api import async_playwright

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="file:///home/ubuntu/fattyclaw/projects/pixel-editor/pixel-editor.html")
    ap.add_argument("--skip-md5", action="store_true", help="跳过 tauri md5 检查（8003 副本无 tauri 目录）")
    args = ap.parse_args()

    fails = []
    def check(name, ok, detail=""):
        print(("✅" if ok else "❌"), name, detail)
        if not ok: fails.append(name)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(args.url, wait_until="load")
        await page.wait_for_timeout(600)

        # ---------- P1.1 帧率联动：setTimeout spy ----------
        await page.evaluate("""() => {
            window.__spans = [];
            const origST = window.setTimeout;
            window.setTimeout = function(fn, ms, ...rest){
                window.__spans.push(ms);
                return origST(fn, ms, ...rest);
            };
        }""")
        # 需要多帧才能播放：手动造 4 帧
        await page.evaluate("""() => {
            const st = window.__px.state;
            while(st.frames.length < 4){
                st.frames.push(st.frames[0]);
            }
        }""")
        # 档位=120（默认）播放
        await page.evaluate("() => { window.__spans.length = 0; togglePlay(); }")
        await page.wait_for_timeout(700)
        await page.evaluate("() => stopPlay()")
        spans120 = await page.evaluate("() => window.__spans.filter(m => m >= 100 && m <= 200)")
        check("P1.1 默认120ms档 tick=120", all(abs(s-120) < 5 for s in spans120) and len(spans120) >= 2, f"spans={spans120[:5]}")
        # 切到 80ms 档再播放
        await page.evaluate("""() => {
            document.getElementById('exportGifDelay').value = '80';
            window.__spans.length = 0;
            togglePlay();
        }""")
        await page.wait_for_timeout(700)
        await page.evaluate("() => stopPlay()")
        spans80 = await page.evaluate("() => window.__spans.filter(m => m >= 60 && m <= 110)")
        check("P1.1 切80ms档 tick=80（联动生效）", all(abs(s-80) < 5 for s in spans80) and len(spans80) >= 2, f"spans={spans80[:5]}")

        # ---------- P1.2 localStorage 爆仓 toast ----------
        await page.evaluate("""() => {
            // 填爆 localStorage：把全部剩余空间吃光（含 saveDraft 需要的零头）
            let i = 0;
            try { for(;;){ localStorage.setItem('px_fill_'+i++, 'x'.repeat(100000)); } } catch(e){}
            try { for(;;){ localStorage.setItem('px_fill_'+i++, 'x'.repeat(1000)); } } catch(e){}
            try { for(;;){ localStorage.setItem('px_fill_'+i++, 'y'); } } catch(e){}
            try { localStorage.setItem('px_last_bit', 'z'); } catch(e){ window.__totally_full = true; }
        }""")
        filled = await page.evaluate("() => !!window.__totally_full")
        if not filled:
            # 极端情况：仍有残空间（存储配额极大）→ 直接 mock setItem 抛 QuotaExceeded，验证 catch→toast 链路
            await page.evaluate("""() => {
                const orig = localStorage.setItem.bind(localStorage);
                localStorage.setItem = function(k, v){ if(k === 'pixelstudio_draft_v2'){ const e = new Error('quota'); e.name = 'QuotaExceededError'; throw e; } return orig(k, v); };
            }""")
        await page.evaluate("() => saveDraft()")
        await page.wait_for_timeout(400)
        toast = await page.evaluate("""() => {
            const t = document.getElementById('pxToast');
            return t ? {exists: true, text: t.textContent, visible: t.style.opacity === '1'} : {exists: false};
        }""")
        check("P1.2 爆仓 toast 出现且可见", toast["exists"] and toast["visible"] and "保存失败" in toast["text"], str(toast))
        await page.evaluate("() => { Object.keys(localStorage).filter(k=>k.startsWith('px_fill_')).forEach(k=>localStorage.removeItem(k)); }")

        # ---------- P2.1 科幻素材 12 个逐个载入 ----------
        await page.evaluate("() => { document.getElementById('tutorialModal').classList.add('hidden'); }")
        # 直接调 renderTplGrid 避免依赖具体按钮 id
        await page.evaluate("() => { renderTplGrid('scifi'); }")
        names = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('#tplGrid .tpl-card')).map(c => c.querySelector('.tpl-name').textContent);
        }""")
        check("P2.1 科幻 tab 有 12 个素材", len(names) == 12, f"实际{len(names)}: {names}")
        load_ok = []
        for nm in names:
            r = await page.evaluate("""(nm) => {
                const cards = Array.from(document.querySelectorAll('#tplGrid .tpl-card'));
                const card = cards.find(c => c.querySelector('.tpl-name').textContent === nm);
                if(!card) return 'nocard';
                card.click();
                const st = window.__px.state;
                const nonEmpty = st.frames.length === 1 && Array.prototype.some.call(st.frames[0].data, v => v !== 0);
                return nonEmpty ? 'ok' : 'empty';
            }""", nm)
            load_ok.append((nm, r))
        bad = [x for x in load_ok if x[1] != "ok"]
        check("P2.1 科幻素材逐个载入画布成功", not bad, f"失败: {bad}" if bad else "12/12")

        # ---------- P2.2 自定义尺寸模态框（新画布来源）----------
        # 先画点东西
        await page.evaluate("""() => {
            const st = window.__px.state;
            st.frames = [window.__px ? null : null].filter(Boolean);
        }""")
        await page.evaluate("""() => {
            // 造一个 32x32 有一笔的内容
            doNewCanvas(32);
            const st = window.__px.state;
            // 在 frames[0] 打个色点
            const d = st.frames[0]; d.data[0] = 255; d.data[1] = 0; d.data[2] = 0; d.data[3] = 255;
        }""")
        before_wh = await page.evaluate("() => { const s = window.__px.state; return [s.w, s.h, s.frames.length]; }")
        # newCanvas → custom：打开弹窗，取消
        await page.evaluate("() => doNewCanvas('custom')")
        vis1 = await page.evaluate("() => !document.getElementById('customSizeModal').classList.contains('hidden')")
        check("P2.2 newCanvas→custom 打开弹窗", vis1)
        await page.evaluate("() => document.getElementById('btnCancelCustomSize').click()")
        after_cancel = await page.evaluate("() => { const s = window.__px.state; return [s.w, s.h, s.frames.length]; }")
        check("P2.2 取消不清空画布", before_wh == after_cancel, f"{before_wh}→{after_cancel}")
        # 再开，填 48x48，确定 → 画布清空成 48x48 且 1 帧
        await page.evaluate("() => doNewCanvas('custom')")
        await page.evaluate("""() => {
            document.getElementById('ncw').value = '48';
            document.getElementById('nch').value = '48';
            document.getElementById('btnApplyCustomSize').click();
        }""")
        await page.wait_for_timeout(200)
        st = await page.evaluate("() => { const s = window.__px.state; return [s.w, s.h, s.frames.length, s.undoStack.length]; }")
        check("P2.2 确定→48x48 新画布+清历史", st == [48, 48, 1, 0], str(st))
        # 非法值 300 → 提示且不应用
        await page.evaluate("""() => {
            doNewCanvas('custom');
            document.getElementById('ncw').value = '300';
            document.getElementById('nch').value = '48';
            document.getElementById('btnApplyCustomSize').click();
        }""")
        warn = await page.evaluate("() => document.getElementById('customSizeWarn').textContent")
        still = await page.evaluate("() => { const s = window.__px.state; return s.w; }")
        check("P2.2 非法值 300 被拦下", "1-256" in warn and still == 48, f"warn={warn!r} w={still}")
        await page.evaluate("() => document.getElementById('btnCancelCustomSize').click()")

        # ---------- P2.2 sizePreset→custom resize ----------
        await page.evaluate("""() => {
            const sel = document.getElementById('sizePreset');
            sel.value = 'custom';
            sel.dispatchEvent(new Event('change'));
        }""")
        vis2 = await page.evaluate("() => !document.getElementById('customSizeModal').classList.contains('hidden')")
        check("P2.2 sizePreset→custom 打开弹窗", vis2)
        await page.evaluate("""() => {
            document.getElementById('ncw').value = '64';
            document.getElementById('nch').value = '32';
            document.getElementById('btnApplyCustomSize').click();
        }""")
        await page.wait_for_timeout(200)
        wh = await page.evaluate("() => { const s = window.__px.state; return [s.w, s.h]; }")
        check("P2.2 resize→64x32（非正方形）", wh == [64, 32], str(wh))

        # ---------- 6. 错字 ----------
        typo = await page.evaluate("() => document.body.innerHTML.includes('循坏')")
        check("6. 「循坏」错字已修", not typo)

        # ---------- console 干净 ----------
        check("零 console error / pageerror", not errors, f"errors={errors[:3]}" if errors else "")

        await browser.close()

    # ---------- P0 tauri md5 ----------
    if not args.skip_md5:
        try:
            r = subprocess.run(
                ["md5sum", "/home/ubuntu/fattyclaw/projects/pixel-editor/pixel-editor.html",
                 "/home/ubuntu/fattyclaw/projects/pixel-editor/tauri/dist/index.html"],
                capture_output=True, text=True, timeout=10)
            lines = r.stdout.strip().split("\n")
            m1, m2 = lines[0].split()[0], lines[1].split()[0]
            check("P0 tauri/dist/index.html == 主文件", m1 == m2, f"{m1[:8]} vs {m2[:8]}")
        except Exception as e:
            check("P0 tauri md5", False, str(e))

    print()
    if fails:
        print(f"❌ {len(fails)} 项失败: {fails}")
        sys.exit(1)
    print("🎉 全部通过")

asyncio.run(main())
