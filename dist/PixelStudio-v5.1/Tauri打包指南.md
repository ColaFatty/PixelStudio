# PixelStudio Tauri 桌面壳 — 打包构建指南

> 关联项目：PixelStudio 像素画编辑器（单文件 HTML 应用）
> Tauri 版本：2.x ｜ 目标平台：Windows / macOS / Linux

## 一、Tauri 是什么

Tauri 是一个**轻量桌面壳框架**：用系统自带的 WebView（Windows 用 WebView2、macOS 用 WKWebView、Linux 用 WebKitGTK）渲染前端页面，外面包一层 Rust 二进制。相比 Electron：

- 安装包体积小（Tauri 通常 <10MB，Electron 通常 >80MB）
- 内存占用低
- 启动快
- 前端代码完全复用（PixelStudio 的 HTML 直接搬进来）

PixelStudio 是**纯单文件 HTML**（零依赖零 CDN），套 Tauri 壳非常合适：`dist/index.html` 就是整个前端。

## 二、工程结构

```
projects/pixel-editor/tauri/
├── package.json              # npm 脚本（开发/构建入口）
├── dist/
│   └── index.html            # ★ 前端资源（从 pixel-editor.html 复制）
└── src-tauri/
    ├── Cargo.toml            # Rust 依赖
    ├── build.rs              # Tauri 构建脚本
    ├── tauri.conf.json       # ★ 主配置（窗口/打包/图标）
    ├── capabilities/
    │   └── default.json      # 权限配置
    ├── icons/                # 应用图标（32/128/icns/ico）
    └── src/
        └── main.rs           # Rust 入口（启动窗口）
```

## 三、开发预览（本机跑）

```bash
cd projects/pixel-editor/tauri

# 1. 安装 Rust（https://rustup.rs）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. 安装 Tauri CLI（推荐用 npm 版，比 cargo 快）
npm install -g @tauri-apps/cli

# 3. 安装系统依赖（Linux 需要；Windows/macOS 不需要）
#   Ubuntu/Debian:
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev patchelf libssl-dev
#   Fedora:
sudo dnf install webkit2gtk4.1-devel gtk3-devel libappindicator-gtk3-devel librsvg2-devel patchelf openssl-devel

# 4. 同步前端（每次改了 pixel-editor.html 都要跑）
cp ../pixel-editor.html dist/index.html

# 5. 开发模式（热更新窗口）
npm run dev
```

## 四、发布构建

### 🔴 发版必检（先同步前端再打包）

**每次修改主文件 `pixel-editor.html` 后，打包前必须重新同步**（Tauri 壳读的是 `dist/index.html`，不是主文件）：

```bash
cp ../pixel-editor.html dist/index.html
# 验证一致：两条 md5 必须相同
md5sum ../pixel-editor.html dist/index.html
```

⚠️ v4.3/v5.0 两次大更新都漏了这步，桌面壳用户一直用着 v4.2 旧前端（v5.1 修复）。此规则已写进项目 README「发版规则」节，验收脚本 pixel_v51_acceptance.py 会自动检查 md5 一致性。

### Linux（Ubuntu x64）

```bash
cd projects/pixel-editor/tauri
cp ../pixel-editor.html dist/index.html
npm run build        # 等价于 tauri build
# 产物：src-tauri/target/release/bundle/
#   deb/  → PixelStudio_3.2.0_amd64.deb
#   appimage/ → PixelStudio_3.2.0_amd64.AppImage（免安装，双击直接跑）
#   rpm/  → PixelStudio-3.2.0-1.x86_64.rpm
```

在**服务器（Linux）**上能直接产出的就是这几个格式。

### 🔴 Windows（推荐在 Windows 机器上打包）

**原则：Windows 的安装包最好在 Windows 上直接构建**，这是官方支持最稳的路径。

```powershell
# 在 Windows 机器上（安装 Rust + WebView2 运行时 + Visual Studio Build Tools）
cd projects\pixel-editor\tauri
Copy-Item ..\pixel-editor.html dist\index.html
npm install -g @tauri-apps/cli
npm run build
# 产物：src-tauri\target\release\bundle\
#   msi/  → PixelStudio_3.2.0_x64.msi（WiX 安装器）
#   nsis/ → PixelStudio_3.2.0_x64-setup.exe（NSIS 安装器）
#   （如果配置了 targets:"all" 且装了 NSIS，会出 .exe）
```

> 需要先安装：
> 1. Rust：https://rustup.rs
> 2. WebView2 Runtime：Win10/11 一般自带，Win7/8 需手动装
> 3. Visual Studio Build Tools（勾选「使用 C++ 的桌面开发」）— cargo 编译 Rust 需要 MSVC 链接器

**Linux 上交叉编译 Windows 包（实验性，不推荐）：**
Tauri 官方文档说明 Linux 交叉编译 Windows 包**可行但在非 Windows 主机上构建 NSIS 安装器属于实验性**，需要 cargo-xwin 或 zig 工具链 + 大量系统 lib 配置，容易踩坑。PixelStudio 建议**直接在 Windows 机器上打包**，一条命令搞定，省心。

### 🍎 macOS（必须在 Mac 上构建）

**macOS 的 .app / .dmg 只能在 Mac 上构建**（Apple 签名 + 平台限制，任何其他 OS 都无法产出能用的 mac 包）。

```bash
# 在 Mac 上（M 系列或 Intel 都行）
cd projects/pixel-editor/tauri
cp ../pixel-editor.html dist/index.html
npm install -g @tauri-apps/cli
npm run build
# 产物：src-tauri/target/release/bundle/
#   macos/  → PixelStudio.app
#   dmg/    → PixelStudio_3.2.0_aarch64.dmg（或 x86_64，取决于机器架构）
```

> 需要先装：Rust、Xcode Command Line Tools（`xcode-select --install`）。
> M 系列 Mac 编出的是 arm64 包，Intel Mac 编出 x86_64 包。要同时支持两种架构需在对应架构机器上各编一次（或用 GitHub Actions CI）。

## 五、Tauri 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `WebKitGTK not found` | Linux 缺系统依赖 | `sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev` |
| 编译很慢 | Rust 首次编译全部依赖 | 正常现象，第一次 10-20min，之后增量快 |
| 图标报错 | 缺 icns/ico 文件 | 用 `npx tauri icon path/to/icon.png` 一键生成全平台图标 |
| 窗口白屏 | frontendDist 路径不对 | 确认 dist/index.html 存在且 `tauri.conf.json` 的 `build.frontendDist` 指向它 |

## 六、图标更新

```bash
# 准备一张 ≥1024x1024 的 PNG
npx tauri icon icon-source.png
# 自动生成 32x32.png / 128x128.png / icon.icns / icon.ico 等全套
```

## 七、更新版本号

改 3 处保持一致：
1. `package.json` 的 `"version"`
2. `src-tauri/Cargo.toml` 的 `[package] version`
3. `src-tauri/tauri.conf.json` 的 `version` 和 `productName`

---

*文档生成：2026-09-02 PixelStudio P2 dev*