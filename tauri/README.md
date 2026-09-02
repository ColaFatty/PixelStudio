# PixelStudio Tauri 桌面壳

给单文件 HTML 像素画编辑器套一个轻量桌面壳，Win / Mac / Linux 双击即用。

> 独立工程目录，不内联进 pixel-editor.html。
> 完整打包指南见 [BUILDING.md](BUILDING.md)

## 快速开始

```bash
cp ../pixel-editor.html dist/index.html   # 同步前端（每次改完 html 都要）
npm install -g @tauri-apps/cli
npm run dev                                # 开发预览
npm run build                              # 发布构建（出安装包）
```

## 平台产物

| 平台 | 构建位置 | 产物 |
|------|---------|------|
| Linux | 本服务器 | .deb / .AppImage / .rpm |
| Windows | Windows 机器（推荐） | .msi / .exe |
| macOS | Mac 机器（必须） | .app / .dmg |

**原则：Win/Mac 包都在对应系统上构建最稳，Linux 包在服务器直接出。**

## 结构

- `dist/index.html` — 前端（来自 pixel-editor.html 的复制品）
- `src-tauri/` — Rust 壳：配置（tauri.conf.json）、图标、主进程