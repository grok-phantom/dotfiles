# Ubuntu 24.04 x86_64 部署

先用 core 验证 Git、Zsh 和 SSH，再按需要启用 full。
目标是 Ubuntu 24.04 的 64 位 x86 主机；不是 32 位 x86。
本仓库配置用户环境，不安装系统服务，不修改登录 shell、网络或 Docker 权限。

## 部署范围

| 选择 | 内容 | 需要另外准备 |
| --- | --- | --- |
| core | Git、基础 Zsh、用户命令、pip/uv 配置、仓库内 skills | Git、Python、Zsh、chezmoi；SSH 身份由本机管理 |
| full + apt | 再增加 Vim/Tmux/OMZ 等配置与 Debian 系基础软件清单 | 锁定外部资源；更高版本的 fzf；Yazi、agent 工具等未在 apt 清单内的软件 |
| full + Homebrew | 增加可选 CLI 软件，包括新版 fzf、Yazi、Herdr、Memex | 已安装且当前用户可写的 Homebrew；上游所需系统编译工具 |

Ubuntu 24.04 的 apt fzf 为 0.44.x，仓库锁定的 fzf.vim 需要 fzf >= 0.54.0。
因此 apt 安装成功不等于 full 编辑器运行时通过。可使用已准备的 Homebrew 安装新版 fzf，
再核对 `command -v fzf` 和 `fzf --version`。不为解决这个差异自动添加 PPA 或执行在线安装脚本。

Linux 不管理 macOS 的 iTerm2、Ghostty、cmux、Karabiner、LaunchAgents、截图/剪贴板上传和 1Password 本地签名助手。
`mba` 支持交互终端中的 SSH/tmux；无 TTY 的桌面启动只支持 macOS。
Herdr 可单独启用，终端通知、剪贴板和按键仍需按实际终端验收。

## 准备与初始化

在普通用户下工作，不以 root 运行配置或软件入口。
先通过系统管理员或已审查的安装方式准备 Git、Python 3.11+、Zsh、curl、OpenSSH client 和 chezmoi。
Ubuntu 24.04 的 Python 3.12 可运行本仓库测试；chezmoi 安装来源需单独核对。
这些步骤不能由尚未具备依赖的仓库入口代为完成。

```sh
uname -m
cat /etc/os-release
python3 --version
git --version
zsh --version
chezmoi --version
```

将受信任的仓库克隆到 `~/.local/share/chezmoi`，进入仓库后初始化：

```sh
chezmoi init --source "$PWD"
```

不加 `--apply`。选择 core，并在本机配置的 `[data]` 中确认以下值；保留初始化生成的其他数据：

```toml
profile = "core"
homebrew = false
herdr_enabled = false
cmux_enabled = false
claude_proxy = false
```

`company`、Git 身份、`sudo` 和 SSH 选择按这台机器实际情况填写，不复制 Mac 的配置文件。
`osid` 应由初始化得到 `linux-ubuntu`。代理默认关闭；Linux 代理端口默认 7890，
只有确实有本机代理或 SSH 转发时才启用。不要照搬 Mac 的代理端口和私有主机清单。

## core 预览与应用

先保存已有 `.zshrc`、Git 配置等目标及 chezmoi 配置/状态的备份。
以下命令均在干净的已提交仓库中执行：

```sh
./scripts/check-linux --profile core
./scripts/test all
./scripts/dotfiles plan --profile core --diff --plan /tmp/dotfiles-core-01.json
./scripts/dotfiles apply --profile core --plan /tmp/dotfiles-core-01.json --yes
./scripts/dotfiles verify --profile core
zsh -l
```

计划文件名每次换新。diff 可能包含本机私有数据，只在本机查看。
更新 CLI 默认 full，即使 data.profile 是 core，也必须在每个阶段显式传 `--profile core`。
`zsh -l` 用来试运行；仓库不会执行 chsh。SSH 远端命令要使用实际登录 shell，
若账户默认仍是 Bash，显式使用 `zsh -lc 'command'` 才能加载这里的 Zsh 配置。

检查 Git 身份、`~/bin` PATH、命令历史、SSH 认证和代理访问。
`ssh_managed` 默认关闭。需要仓库管理 SSH 时，先设置本机开关与主机文件，再单独预览。
本仓库不安装 sshd、不开放端口、不修改 authorized_keys。

## 软件与 full

apt 使用 Ubuntu 软件源中的包。部分条目在 universe；先由管理员确认源和索引可用。
`--apt` 只用当前本地索引模拟依赖，不刷新索引、不安装：

```sh
./scripts/check-linux --profile core --apt
./scripts/software packages plan --manager apt
```

审查后可显式安装：

```sh
./scripts/software packages install --manager apt --yes --interactive
./scripts/software packages verify --manager apt
```

安装要求本机 data.sudo=true。`--interactive` 在当前终端询问 sudo 密码；
不传时要求非交互 `sudo -n` 可通过。无需为正常终端安装设置永久免密 sudo。
软件入口只接受 full，默认也是 full；它不改变上面的 core 配置选择。
APT 清单不安装 chezmoi、Homebrew、Claude、Codex、Herdr、Memex、Yazi 或 Rust 工具链。
`bat` 的命令可能为 batcat，fd 为 fdfind，Shell 已做别名适配。

如使用已经准备好的 Homebrew，在本机 data 设置 `homebrew=true`。
拥有 sudo 不是使用已安装 Homebrew 的必要条件；当前用户仍需对其安装目录有写权限。
ephemeral 主机初始化仍强制关闭 Homebrew。仓库不会安装 Homebrew 本身。

```sh
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
./scripts/software packages plan
# 审查清单后才执行：
./scripts/software packages install --yes
```

Linux Homebrew 清单包含基础 CLI，仍需操作系统提供 SSH、编译环境和系统库。
Miniforge 可选，不是使用 Zsh 或系统 Python 的前置条件。

决定使用 full 时，把本机 data.profile 改为 full，先检查程序依赖，再规划外部资源：

```sh
./scripts/check-linux --profile full
./scripts/dotfiles plan --profile full --component externals --diff --plan /tmp/dotfiles-full-01.json
./scripts/dotfiles apply --profile full --component externals --plan /tmp/dotfiles-full-01.json --yes
./scripts/dotfiles verify --profile full --component externals
```

externals 会下载并校验锁定资源，exact 目录可能清理额外文件，必须审查 diff。
Herdr 需要时设 `herdr_enabled=true`，按[终端说明](terminals.md#herdr)安装插件和集成。
Navigator 需要 Cargo，Auto Title/Plus 需要 Go；不能仅凭 Homebrew 软件清单已安装就认为所有插件可用。
无桌面 SSH 会话不保证系统剪贴板、copypath 或桌面通知可用。

## 验收边界

`check-linux` 只检查指定系统、命令前置条件和可选 apt 依赖模拟，不代替整机验收。
CI 在 Ubuntu 24.04 x86_64 上运行离线测试及 apt 模拟；不安装整份软件清单，不测试真实 SSH 或桌面。
本机的 shell、Vim、Tmux、代理、agent 登录和远程会话需在目标机器逐项确认。
有已下载的锁定缓存时，可运行 `./scripts/test runtime --cache /path/to/cache`，
它仍使用临时 HOME，与真实用户环境验收分开。

切回 core 或关闭 Herdr 不删除已生成的文件，也不卸载软件。恢复方式见
[配置参考](configuration.md#关闭功能时的行为)和[终端说明](terminals.md#herdr)。
