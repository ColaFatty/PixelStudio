# PixelStudio · 像素画编辑器

单文件 HTML 像素画编辑器，零依赖零 CDN，双击即用，Win / Mac / Linux 浏览器或 Tauri 桌面壳均可运行。

## ✨ 功能总览

### 画图核心
- 🖌️ **画笔**（2 种笔刷形状 square/circle，1-16px 可调）/ 橡皮 / 填充 / 取色 / 直线
- 🔲 **形状工具**：矩形 / 椭圆，空心 / 填充
- ✂️ **选区工具**：框选 / 拖动移动 / Ctrl+C 复制 / Ctrl+V 粘贴 / 水平垂直镜像翻转 / 旋转 90°，全部可撤销
- ↩️ **撤销重做** + 自动保存草稿（刷新不丢）
- 🎨 **调色板**：PICO-8（16 色）/ GameBoy（4 色）/ Sweetie-16 / Endesga-32，支持自定义
- 🪞 **对称绘制**：水平 / 垂直 / 双向镜像
- 🖼️ **图片导入转像素画**：任意图片 → 高质量降采样（平滑插值）→ 调色板映射或 PNN 色彩量化，**Floyd–Steinberg 误差扩散抖动**让色板色点阵混出中间渐变，告别「压到几色糊成一片」
- 📖 **内置教程**：13 节新手教程，按 F1 随时查看
- 🧩 **素材模板库**：不会画也能立刻出作品——宝可梦风格精灵×6 / RPG tile 集×16 / 角色行走图×1（4方向×3帧=12帧动画），点一下自动载入画布并配上专属调色板，行走图载入即可直接播放、导出 GIF

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
| v4.0 | 素材模板库（精灵/RPG tile/行走图）+ 当前全部功能 |
| v3.3 | 图片转像素算法升级（平滑降采样 + Floyd–Steinberg 抖动 + PNN 量化）|
| v3.2 | 全部功能 + Sprite sheet / 字符画 / Tauri 壳 |
| v3.1 | 参考层 / Sweetie-16+Endesga-32 调色板 / 笔刷增强 |
| v3.0 | 选区 + 形状工具 |

## 🗂️ 文件清单

- `pixel-editor.html` — 主程序（单文件，~132KB）
- `dist/` — 各版本交付包（zip + README + 使用方法）
- `tauri/` — Tauri 桌面壳工程（含打包指南）

## 🔧 技术亮点

- 纯前端零依赖零 CDN，完全离线可用
- GIF 编码使用 omggif（成熟编码器，Piskel 同款）内联
- 对称 / 选区 / 形状 / 动画帧全量撤销栈支持