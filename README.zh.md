<div align="center">

**面向 Ubuntu 的专业 SSH 连接管理器 — 图形界面 + 命令行，共享同一引擎。**

`sss prod` · `sss prod nginx` · `sss prod --exec "uptime"`

[English](README.md) · [فارسی](README.fa.md) · [العربية](README.ar.md) · **简体中文** · [Русский](README.ru.md) · [Español](README.es.md) · [Français](README.fr.md)

</div>

SSH Desk 是一个真实可安装的产品（绝非原型演示），用于管理你的所有 SSH 服务器：密码**只**存储在 GNOME Keyring（Secret Service）中，SSH 引擎就是系统自带的 **OpenSSH**，内置终端是**真实的 PTY**（vim/nano、颜色、Ctrl+C、窗口缩放 — 一切都真正可用）。

- 🖥️ **桌面 GUI**（PySide6）：深色/浅色主题，波斯语/英语（完整 RTL），真实终端多标签，SFTP 文件管理器，隧道，密钥，历史记录
- ⌨️ **命令行**（Typer）：**无需** GUI 即可工作；命令名可配置（`sss`、`cnc`、`sshgo`…）；bash/zsh 自动补全（含服务器别名补全）
- 🔐 **安全优先**：强制主机密钥校验并显示指纹对话框；机密绝不进入数据库/日志/命令行参数；不使用 sshpass，也不使用 `StrictHostKeyChecking=no`
- 🌐 **抗网络中断**：PyPI 多镜像回退链（官方 → ArvanCloud 伊朗 → TUNA → Aliyun → Tencent），并支持 `install.sh --offline` 完全离线安装

📄 **[完整用户指南（PDF，中文）](docs/SSH-Desk-User-Guide-zh.pdf)** — 14 页图文指南，涵盖离线安装、完整 CLI 参考、终端、SFTP、隧道与安全模型。另有 7 种语言版本：[English](docs/SSH-Desk-User-Guide-en.pdf) · [فارسی](docs/SSH-Desk-User-Guide-fa.pdf) · [العربية](docs/SSH-Desk-User-Guide-ar.pdf) · [Русский](docs/SSH-Desk-User-Guide-ru.pdf) · [Español](docs/SSH-Desk-User-Guide-es.pdf) · [Français](docs/SSH-Desk-User-Guide-fr.pdf)

---

## 快速开始

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
bash scripts/install.sh
```

然后：

```bash
ssh-desk          # 图形界面
sss add           # 添加第一台服务器
sss prod          # 连接（在你自己的终端里进入交互式 shell）
```

DEB 包与手动安装见 [docs/INSTALLATION.md](docs/INSTALLATION.md)。
弱网/断网环境：先 `bash scripts/download_wheels.sh --mirror-name ir`，再 `bash scripts/install.sh --offline`。

## 30 秒上手命令行

```bash
sss                      # 概览 + 提示
sss list                 # 服务器列表
sss add                  # 交互式向导（也可用 --alias/--host/...）
sss info prod            # 完整详情
sss test prod            # 连接性测试
sss prod                 # 进入默认路径的交互式 shell
sss prod nginx           # 连接到已保存的路径
sss prod /etc/nginx      # 连接到任意绝对路径
sss prod --exec "uptime" # 执行单条命令（不保存任何内容）
sss prod --user ubuntu --port 2222   # 仅本次生效的覆盖参数
sss history              # 连接历史
sss current              # 活动会话 + 运行中的隧道
sss tunnel db            # 启动命名隧道（独立于终端存活）
sss config cli-name cnc  # 在操作系统层面重命名命令
sss --help               # 完整参考
```

## 功能一览

| 领域 | 实际可用能力 |
| --- | --- |
| 服务器 | 增删改查，别名唯一，分组，标签，收藏，复制，搜索/排序/过滤 |
| 认证 | 密码（Keyring），私钥（口令存于 Keyring），SSH agent，交互式 |
| 路径 | 默认路径 + 命名保存路径（`sss prod nginx`），安全引号转义 |
| 终端 | 真实 PTY（OpenSSH），多标签，颜色，vim/nano，窗口缩放，复制/粘贴 |
| 文件 | 双窗格 SFTP 管理器：上传/下载/mkdir/重命名/chmod/编辑/删除，服务器↔服务器互传 |
| 密钥 | 生成 Ed25519/RSA/ECDSA（OpenSSH 格式），导入，指纹，导出公钥，`ssh-copy-id` 指引 |
| 隧道 | 本地 / 远程 / 动态 SOCKS，启停，独立守护进程，状态跟踪 |
| 跳板 | 经由任意已注册服务器的 `ssh -W` ProxyCommand（支持嵌套链） |
| 命令库 | 按服务器或全局保存命令，危险命令需确认 |
| 历史 | 连接/断开，时长，状态，错误（不记录终端内容与密码） |
| 导入/导出 | `~/.ssh/config` 导入（预览 + 去重），TOML 备份/恢复（密码为可选项目） |

## 安全模型（简版）

1. 密码/口令**只**存在于 Secret Service（GNOME Keyring）；数据库仅保存无机密含义的引用。
2. OpenSSH 通过加固的 **askpass 助手**获取机密 — 绝不经参数、绝不经环境变量、绝不使用 sshpass。
3. 强制主机密钥校验（`StrictHostKeyChecking=yes`）：未知主机 → 指纹对话框；密钥变更 → 硬性告警。
4. 数据库/配置文件权限为 `0600`/`0700`；日志自动脱敏；无 root 守护进程。

完整说明：[docs/SECURITY.md](docs/SECURITY.md)。

## 开发

```bash
pip install -e .[dev]
pytest          # 54 tests
ruff check .    # clean
```

架构与内部细节：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## 系统要求

- Ubuntu 22.04 / 24.04+（或任何 Debian 系发行版）
- Python 3.10+（推荐 3.12），`openssh-client`
- GNOME Keyring（`sudo apt install gnome-keyring`），用于存储密码

## 许可证

MIT — 见 [LICENSE](LICENSE)。
