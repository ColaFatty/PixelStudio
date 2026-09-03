# PixelStudio · 像素画编辑器

单文件 HTML 像素画编辑器，零依赖零 CDN，双击即用，Win / Mac / Linux 浏览器或 Tauri 桌面壳均可运行。

## ✨ 功能总览

### 画图核心
- 🖌️ **画笔**（2 种笔刷形状 square/circle，1-16px 可调）/ 橡皮 / 填充 / 取色 / 直线
- 🔲 **形状工具**：矩形 / 椭圆，空心 / 填充
- ✂️ **选区工具**：框选 / 拖动移动 / Ctrl+C 复制 / Ctrl+V 粘贴 / 水平垂直镜像翻转 / 旋转 90°，全部可撤销
- ↩️ **撤销重做** + 自动保存草稿（刷新不丢）
- 🆕 **新画布**：一键新建/清空画布（16/32/48/64/自定义尺寸），清空所有帧和撤销历史 + 恢复默认调色板
- 🎨 **调色板**：PICO-8（16 色）/ GameBoy（4 色）/ Sweetie-16 / Endesga-32，支持自定义（顶栏 ➕ 一键把当前色加入我的调色板）
- 🪞 **对称绘制**：水平 / 垂直 / 双向镜像
- 🖼️ **图片导入转像素画**：任意图片 → 高质量降采样（平滑插值）→ 自动取色（32色，适合照片/人物）或调色板映射 + 可选抖动，默认关抖动 → 照片导入干净无噪点
- 📖 **内置教程**：17 节新手教程 + 「从零画一个角色」实战演示（分步动画），按 F1 随时查看
- 🧩 **素材模板库**：不会画也能立刻出作品——**多风格专业素材库**（Kenney CC0 免费商用）：🏰 RPG 奇幻 / 🐾 可爱动物 / 🚀 科幻战机 / 🚶 角色行走图（4方向×3帧=12帧动画），点一下自动载入画布并配上专属调色板，行走图载入即可直接播放、导出 GIF

### 动画与导出
- 🎬 **动画帧**：多帧编辑 + 播放预览 + 洋葱皮
- 🧵 **Sprite sheet 导出**：多帧按网格排成雪碧图（列数/间距/缩放/背景可选），实时预览 + 下载 PNG
- 🔤 **字符画导出**：按亮度映射 ASCII（经典/色块/二值/紧凑字符集），预览 + 复制剪贴板 + 下载 txt
- 💾 **PNG 导出**（1x-8x 放大）/ **GIF 导出**（动画）

## 🚀 快速开始

**方式一：浏览器直接玩**
双击 `pixel-editor.html`，浏览器打开即可，完全离线。

**方式二：Tauri 桌面壳（安装包）**
```
cd tauri
cp ../pixel-editor.html dist/index.html
npm install -g @tauri-apps/cli
npm run build
```
产物：Linux `.deb/.AppImage`（服务器直接编）、Windows `.msi/.exe`（Windows 机器编）、macOS `.app/.dmg`（Mac 机器编）。
详见 [tauri/BUILDING.md](tauri/BUILDING.md)。

## 📦 交付包（dist/）

| 版本 | 内容 |
|------|------|
| v5.1 | 🔴 Tauri 同步修复（v4.3/v5.0 漏同步，桌面壳此前是旧前端）+ 播放帧率与 GIF 导出帧间隔联动 + 草稿保存失败 toast 提示 + 科幻素材 8→12（机器人/飞碟/舱门/能量核心）+ 自定义尺寸模态框替代 prompt() + 发版规则成文 |
| v5.0 | 教程 v2（实战教学 + 核心技法 + v4 新功能教学）+ 素材库 v2（多风格 Kenney CC0 专业素材：RPG奇幻/可爱动物/科幻战机）|
| v4.3 | 照片导入优化：默认自动取色 32 色 + 关抖动（无雪花噪点），抖动变开关可选 |
| v4.2 | 行走图模板 frames[0] 空白 bug 修复 + 统一模板载入保护 |
| v4.1 | 新画布按钮 + 修复顶栏加色按钮（🆕）/ + 当前全部功能 |
| v4.0 | 素材模板库（精灵/RPG tile/行走图）+ 当前全部功能 |
| v3.3 | 图片转像素算法升级（平滑降采样 + Floyd–Steinberg 抖动 + PNN 量化）|
| v3.2 | 全部功能 + Sprite sheet / 字符画 / Tauri 壳 |
| v3.1 | 参考层 / Sweetie-16+Endesga-32 调色板 / 笔刷增强 |
| v3.0 | 选区 + 形状工具 |

## 🗂️ 文件清单

- `pixel-editor.html` — 主程序（单文件，~195KB）
- `dist/` — 各版本交付包（zip + README + 使用方法）
- `tauri/` — Tauri 桌面壳工程（含打包指南）
- `pixel_v5*_acceptance.py` — 各版本 playwright 验收脚本（`python3 pixel_v51_acceptance.py`）

## 🔴 发版规则（必读，v5.0 前的血泪教训）

**每次修改 `pixel-editor.html` 后，必须同步以下三处，缺一就是发版事故**（v4.3/v5.0 曾漏同步 Tauri，桌面壳用户用着 v4.2 旧版）：

1. `tauri/dist/index.html` ← 拷贝主文件（Tauri 壳读这里）：
   ```bash
   cp pixel-editor.html tauri/dist/index.html
   ```
2. `dist/PixelStudio-vX.Y.zip` ← 重新打交付包
3. `app/frontend/assets/pixel-editor/`（8003 线上）← 拷贝主文件

**根治方案**：把同步写进发版 checklist，验收脚本 `pixel_v51_acceptance.py` 已内置 tauri md5 一致性检查，跑过全绿才算发版完成。

## 🔧 技术亮点

- 纯前端零依赖零 CDN，完全离线可用
- GIF 编码使用 omggif（成熟编码器，Piskel 同款）内联
- 对称 / 选区 / 形状 / 动画帧全量撤销栈支持