# Ubuntu 24.04 / 26.04 x86_64 部署

先用 core 验证 Git、Zsh 和 SSH，再按需要启用 full。
目标是 Ubuntu 24.04 / 26.04 的 64 位 x86 主机；不是 32 位 x86。
本仓库配置用户环境，不安装系统服务，不修改登录 shell、网络或 Docker 权限。

## 部署范围

| 选择 | 内容 | 需要另外准备 |
| --- | --- | --- |
| core | Git、基础 Zsh、用户命令、pip/uv 配置、仓库内 skills | Git、Python、Zsh、chezmoi；SSH 身份由本机管理 |
| full + apt | 再增加 Vim/Tmux/OMZ 等配置与 Debian 系基础软件清单 | 锁定外部资源；24.04 另需新版 fzf；Yazi、agent 工具等未在 apt 清单内的软件 |
| full + Homebrew | 增加可选 CLI 软件，包括新版 fzf、Yazi | 已安装且当前用户可写的 Homebrew；上游所需系统编译工具 |

Ubuntu 24.04 的 apt fzf 为 0.44.x，仓库锁定的 fzf.vim 需要 fzf >= 0.54.0。
Ubuntu 26.04 的 apt fzf 0.67.x 已满足此版本要求；Yazi 仍不在本仓库 apt 清单中。
因此 apt 安装成功不等于 full 编辑器运行时通过。可使用已准备的 Homebrew 安装新版 fzf，
再核对 `command -v fzf` 和 `fzf --version`。不为解决这个差异自动添加 PPA 或执行在线安装脚本。
Ubuntu 的 fzf Vim 集成位于 `/usr/share/doc/fzf/examples/plugin/fzf.vim`，配置会在文件存在时加载。
精简镜像可能通过 dpkg 排除整个文档目录；此时只补新版 fzf 可执行文件仍不够。
需在安装 fzf 包前保留该目录，容器流程已处理。缺少 eza 时不启用其 OMZ 插件。

core/full 区分配置深度，不区分服务器和桌面角色。无桌面的服务器也可以使用 full。
服务器最低安装可选 core；需要补全、主题和编辑器插件时，再准备 full 的依赖。
Linux 桌面沿用相同终端配置，桌面环境、终端模拟器、输入法、剪贴板和 GUI 软件需另外安装验收。
不把 macOS cask 清单套用到 Linux，也不新增角色 profile。

Linux 不管理 macOS 的 iTerm2、Ghostty、Karabiner、LaunchAgents 和 1Password 本地签名助手。
终端通知、剪贴板和按键仍需按实际终端验收。

## 按使用场景选择

系统版本、使用期限、配置深度和桌面能力分别选择，不引入新的角色 profile。

| 使用场景 | 配置与软件选择 | 登录 shell |
| --- | --- | --- |
| 临时排障、借用机器 | `core`，`ephemeral=true`，使用已有工具 | 保留原 shell，按需运行 `zsh -l` |
| 临时开发 VM / 容器 | 需要完整编辑器时选 `full`，`ephemeral=true`；依赖装在隔离环境 | 容器可创建 Zsh 用户，宿主保持原设置 |
| 常用服务器 / 开发机 | `ephemeral=false`；`core` 起步或直接准备 `full`；apt 系统基线 + 可选 Homebrew CLI | 验证后可单独切换到系统 Zsh |
| 常用桌面 / 笔记本 | 与常用服务器共用终端配置，按操作系统另外安装 GUI 与终端集成 | 按使用习惯单独选择 |

`ephemeral=true` 会在初始化时关闭 Homebrew，不会自动减少 full 的插件，
也不是退出后清理 HOME 的开关。24.04 临时 full 环境仍需要满足新版 fzf 等运行依赖。
`sudo` 只描述安装权限；SSH、agent 等按本机需求分别开启，不由“常用”自动推导。

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

常用机器若决定更改登录 shell，先试运行 `/bin/zsh -lic 'exit'`，确认没有启动错误，
并确认 `/bin/zsh` 已在 `/etc/shells` 中，再由用户单独执行：

```sh
chsh -s /bin/zsh
getent passwd "$(id -un)" | cut -d: -f1,7
```

保留当前 SSH 会话，另开新连接确认登录正常后再关闭旧会话。
建议登录入口使用 apt 管理的 `/bin/zsh`；登录后仍可通过 PATH 使用 Homebrew CLI，
不必让账户登录依赖某个 Cellar 版本路径。此步骤不由 chezmoi apply 或软件安装入口自动执行。

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
APT 清单不安装 chezmoi、Homebrew、Claude、Codex、Yazi 或 Rust 工具链。
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

apt 与 Homebrew 分别管理 `/usr` 和 `/home/linuxbrew/.linuxbrew`，不应互相覆盖文件。
本仓库 `.zprofile` 加载 `brew shellenv`，登录终端中的同名命令优先使用 brew；
现有 apt 清单保留系统基线，不为去重卸载系统 Python、Git 或库。
安装后用 `type -a git python3 vim tmux fzf` 核对解析顺序；需要系统版本时用 `/usr/bin/...`。
服务使用显式程序路径，不能假定 systemd 会读取交互 shell 的 PATH。
不要全局设置 `LD_LIBRARY_PATH` 把两套库混在一起，也不要把 brew 文件链接进 `/usr/bin`。
Vim 的 Python 支持和 fzf runtime 必须随所选工具实际验证，不能只看命令是否存在。

Miniforge 可选，不是使用 Zsh 或系统 Python 的前置条件。

决定使用 full 时，把本机 data.profile 改为 full，先检查程序依赖，再规划外部资源：

```sh
./scripts/check-linux --profile full
./scripts/dotfiles plan --profile full --component externals --diff --plan /tmp/dotfiles-full-01.json
./scripts/dotfiles apply --profile full --component externals --plan /tmp/dotfiles-full-01.json --yes
./scripts/dotfiles verify --profile full --component externals
```

externals 会下载并校验锁定资源，exact 目录可能清理额外文件，必须审查 diff。
无桌面 SSH 会话不保证系统剪贴板、copypath 或桌面通知可用。

## 验收边界

从空 Ubuntu 镜像安装和运行的可重复流程见 [Docker 安装验证](linux-docker.md)。
该流程会实际安装 apt 软件并执行终端工具，与只读预检和模板测试分开。

`check-linux` 只检查指定系统、命令前置条件和可选 apt 依赖模拟，不代替整机验收。
CI 在 Ubuntu 24.04 x86_64 上运行离线测试及 apt 模拟；不安装整份软件清单，不测试真实 SSH 或桌面。
本机的 shell、Vim、Tmux、代理、agent 登录和远程会话需在目标机器逐项确认。
有已下载的锁定缓存时，可运行 `./scripts/test runtime --cache /path/to/cache`，
它仍使用临时 HOME，与真实用户环境验收分开。

切回 core 不删除已生成的文件，也不卸载软件。恢复方式见
[配置参考](configuration.md#关闭功能时的行为)。
