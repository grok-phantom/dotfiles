# 功能总览

本页说明仓库自有配置和工具的完整范围；源码中的选项、锁文件和忽略规则是最终依据。

`.chezmoiroot` 把 `home/` 映射到用户 home；`scripts/`、`docs/`、`tests/` 和
`locks/` 留在 source 仓库。`private_` 控制目标权限，不表示文件内容不会公开；
秘密只在本机 data、环境或密码管理器中保存。

## 功能与入口

| 功能 | 当前提供的行为 | 主要源码 / 使用说明 |
| --- | --- | --- |
| 配置更新 | status → fetch → plan → apply → verify；计划绑定提交、渲染结果和目标状态；只允许向前更新 | [scripts/dotfiles](../scripts/dotfiles)、[README](../README.md#更新入口) |
| 软件维护 | Homebrew / apt 清单安装、升级、检查；独立的 Miniforge 安装器与校验 | [scripts/software](../scripts/software)、[软件清单](../home/.chezmoidata/packages.yaml) |
| 外部资源 | 固定 commit 和 SHA-256 的插件、主题、字体；显式选择 externals 才下载 | [外部声明](../home/.chezmoiexternal.toml.tmpl)、[依赖锁](../locks/README.md) |
| Shell | Zsh、共享命令历史、命令提示、vi 模式、目录跳转、可选历史搜索、代理函数 | [Zsh 入口](../home/dot_zshrc.tmpl)、[shell 模块](../home/private_dot_config/zsh/conf.d)、[命令速查](commands.md#shell-日常操作) |
| Git | 全局身份、个人目录邮箱、可选 SSH 签名、本机 include、自动跟踪与 prune | [Git 配置](../home/private_dot_config/git)、[多 Mac 迁移](multi-mac.md#1password) |
| Vim | amix/Pathogen、Gruvbox、补全、搜索、标签、诊断、格式化与远程复制 | [Vim 入口](../home/dot_vimrc)、[自有配置](../home/private_dot_config/vim/my_configs.vim.tmpl) |
| Tmux / Yazi | 锁定的 Tmux 配置；Yazi 的 ranger 风格按键和退出后切换目录 | [Tmux 链接](../home/symlink_dot_tmux.conf)、[Yazi 按键](../home/private_dot_config/yazi/keymap.toml) |
| 桌面终端 | iTerm2 Dynamic Profile、Ghostty、MesloLGS NF 字体、远程终端支持 | [终端说明](terminals.md) |
| Python 工具配置 | pip/uv 的默认镜像、Conda 的 conda-forge/strict 配置与关闭 base 自动激活 | [pip](../home/private_dot_config/pip/pip.conf)、[uv](../home/private_dot_config/uv/uv.toml)、[Conda](../home/dot_condarc) |
| Workspace | 统一代码布局、外置盘符号链接与卷校验、目录检查、仓库清单与克隆 | [workspace](../home/bin/executable_workspace.tmpl)、[使用说明](workspace.md) |
| SSH | 可选托管、主机分类、1Password agent、公钥、连接复用、转发 agent、临时主机到期管理 | [SSH 模板](../home/private_dot_ssh/private_config.tmpl)、[sshtmp](../home/bin/executable_sshtmp)、[迁移说明](multi-mac.md#ssh-配置) |
| 远程开发 | 远程 tmux、截图/剪贴板图片上传、Raycast 入口、SSH 内签名 | [远程开发说明](multi-mac.md#远程开发主机) |
| Claude / Codex | Claude 代理、无人值守 Git、Roost 状态接入；按目标合并已有应用设置 | [Claude 模板](../home/private_dot_claude/modify_private_settings.json)、[Codex hooks](../home/dot_codex/modify_private_hooks.json)、[notify 迁移](../home/dot_codex/modify_private_config.toml) |
| nori | 从密码管理器合并共享策略与本机配置，渲染订阅；定时健康检查与 Bark 通知 | [共享模板](../home/.chezmoitemplates/nori.yaml.tmpl)、[nori-watch](../home/bin/executable_nori-watch)、[使用说明](multi-mac.md#nori-定时检查) |
| macOS 偏好 | Karabiner 指定键盘映射；独立手动系统偏好脚本 | [Karabiner](../home/private_dot_config/private_karabiner/private_karabiner.json)、[macOS 脚本](../scripts/manual/macos-defaults.sh) |
| 开发小工具 | JSON 格式化、TCP 监听检查、HTTP 文件服务、直连/代理比较 | [命令速查](commands.md#开发小工具) |
| 验证与维护 | 本地隔离测试、缓存集成、运行时检查、终端检查、CI、秘密扫描、Dependabot | [测试说明](testing.md)、[分支维护](branches.md) |

## 平台与 profile

配置入口支持 macOS / Linux 的 arm64/aarch64/x86_64，具体组合由入口检查。
CLI 默认 full，直接 chezmoi 使用本机 `data.profile`，未设置也回落到 full。

| 范围 | core | full |
| --- | --- | --- |
| Git、基础 Zsh、Readline vi 模式、pip/uv、`~/bin` 工具 | 管理 | 管理 |
| OMZ、Powerlevel10k、Vim、Tmux、Yazi、Conda 配置和初始化 | 跳过 | 管理；程序需另外安装 |
| 锁定插件与字体 | 跳过 | 还需选择 `--component externals`；ephemeral 跳过字体 |
| iTerm2、Ghostty、Karabiner、LaunchAgents | 跳过 | 仅 macOS |
| SSH、Claude、Codex、nori 配置 | 由各自本机开关决定 | 由各自本机开关决定 |
| `scripts/software` | 拒绝执行 | 显式 plan / install / upgrade / apply / verify |

工具文件被管理不等于能在所有平台运行：截图、剪贴板和 Raycast 流程依赖 macOS；
nori-watch 需已有 nori；Roost 需应用仓库安装的 `~/bin/roost`。
从 full 切换到 core 只忽略可选目标，保留既有文件与软件。所有开关见[配置参考](configuration.md)。

## Shell、编辑器与终端

Zsh 登录时探测 Homebrew；交互启动时发现 `~/bin`、Go/Cargo/本地工具路径并去重。
两个 profile 都启用 `SHARE_HISTORY`。存在 zoxide、atuin 时才初始化，atuin 在
zsh-vi-mode 的延迟初始化后绑定按键。VS Code / iTerm2 的 shell integration
按当前终端和本机文件是否存在加载。

full 使用 OMZ + Powerlevel10k，关闭 OMZ 自动更新。启用 Git、eza、extract、
vi 模式、语法高亮、自动建议、command-not-found、aliases、history、tmux 插件；
Docker/rsync 按渲染时工具是否存在加入，Linux 加 systemd。Conda 优先加载
`conda.sh`，缺失时回退到 hook；`DOTFILES_CONDA_INIT=hook` 可显式选择 hook。

Vim 的自有设置在 `~/.config/vim/my_configs.vim`，加载 amix 后再加载 Pathogen
和 Gruvbox。外部锁包含 ALE、Gruvbox、jedi-vim 及 Jedi/Parso/递归类型依赖、
webapi-vim、SuperTab、vim-oscyank、fzf.vim、Tagbar。Python 的 flake8/black、
C/C++ 的 clang-tidy/clang-format 由项目环境提供；Tagbar 依赖 Ctags，Jedi 依赖
带 Python 支持的 Vim。快捷键见[命令速查](commands.md#编辑器与文件管理)。

Tmux 使用锁定的 `gpakosz/.tmux`，`~/.tmux.conf` 是托管链接，
`~/.tmux.conf.local` 也由仓库托管：先加载上游模板，再追加本地覆盖
（例如用 Claude Code 的标题给窗口命名）。cmux 新建的 `cmux-new-*` 会话在 shell
第一次进入目录时改名为该目录名，侧边栏显示项目名。Yazi 的 smart-enter 同样来自锁定归档。
外部目录有 `exact` 管理，额外文件可能被删除；自有配置放在外部目录之外。

macOS full 管理 iTerm2 的 `wizplus` Dynamic Profile 和 Ghostty 配置，不自动切换
默认终端。Ghostty 支持 OSC 52 写剪贴板、长命令完成通知、Shift+Enter 换行，
并显式启用 SSH 环境/terminfo 集成。快捷键、效果检查和回退见[终端说明](terminals.md)。

## Git、SSH 与远程开发

Git 提供 `main` 默认分支、pull rebase、push 自动建立 upstream、fetch prune、
UTF-8 路径显示、公共 ignore 和 `~/.config/git/local.conf` 本机扩展。
`personal_email` 通过 `includeIf` 为个人代码目录选择邮箱；可在 macOS 选择
1Password SSH 签名，SSH 会话改走转发 agent。

`ssh_managed` 开启后按 personal/work/temp/local 分类 include 主机配置，默认关闭
agent 转发并启用连接复用。转发应在特定主机块中按需设置；`.zprofile` 在 SSH
登录时维护稳定的 agent socket 链接供长寿命 tmux 会话使用。临时主机由 `sshtmp`
管理，单独使用 `known_hosts.temp`；清单中的到期项在后续命令运行时清理。

`rt` 连接或创建远程 tmux 会话，可用于运行 Claude Code 或 Codex。
在 cmux 里重跑 `rt` 时，若本机 cmux 与该主机的镜像连接已断（窗口冻结），会先分离旧镜像
（远端会话保留）再重新镜像，不必手动关掉冻结的窗口。
`clip-to-remote` / `shot-to-remote` 上传图片并
复制远端路径，上传时清理远端缓存中超过 7 天的文件。主机名保存在本机配置中。
`sync-remote`（`-r` 反向）用 rsync 在本机和远端 `~` 下同一位置之间推送或拉回，默认跳过 `.git`
和 `.gitignore` 忽略的文件，只增不删、不覆盖接收端更新的文件（macOS 自带的 openrsync 删除时不认 `.gitignore`）。
`rtunnel` 按需打开反向隧道，让远端登回本机，默认 2 小时后自动关闭。
这几个命令都可作为 Raycast Script Commands 使用，具体依赖见[远程开发说明](multi-mac.md#远程开发主机)。
`automation_git_global` 让无人值守的远程主机上所有 git 都不等 1Password 批准。

## 代理、AI 工具与 nori

代理地址来自同一份 `proxy.json.tmpl`，供 shell 函数、Claude Code、GUI
LaunchAgent 和 nori-watch 使用。三种入口分别作用于当前 shell、Claude 子进程、
GUI 登录会话；改变 shell 环境不会同步清理另两处。模板的 NO_PROXY 包含 loopback
和 Apple 服务域名；应用是否采用环境变量，需在应用内验证。

Claude 的 `settings.json` 采用 modify template，合并代理 env、automation_git
和 Roost hooks，保留不相关设置。`automation_git` 让 Claude 启动的 Git 使用
GitHub HTTPS + gh 凭据，并指定本机签名钥；不创建密钥、不完成 gh 登录。
`cct` 则为临时 Claude 会话创建 `~/workspace/scratch/<name>`。

Roost 集成分别在 Claude 的 settings.json 和 Codex 的 hooks.json 中添加生命周期
hooks，并从 Codex notify 中移除旧的 Roost 包装，让 Computer Use 继续使用 notify。
未设置 `roost_hooks` 时忽略 Codex 目录。关闭时需要显式设为 false 并 apply；
Claude 目标若已被其他开关共同关闭而
忽略，需先恢复该目标的管理才能清理，详见[配置参考](configuration.md#关闭功能时的行为)。

nori 配置由 1Password 中的共享策略深度合并 `nori_machine_json`，本机字段覆盖
共享字段；订阅和 Bark URL 分别渲染到私有目标。目录名由 `nori_config_dir` 选择。
仓库只提供配置和检查，不安装或重启 nori 服务。

nori-watch 检查状态、维护/恢复标志、刷新结果和刷新年龄；加 `--proxy` 才做
代理连通性探测，LaunchAgent 会传入这一参数。直连也不可达时跳过代理故障判断，
但仍报告 nori 自身状态问题。定时器间隔 30 分钟，新问题和全部恢复会通知；
比较问题时忽略不断增长的刷新小时数，同时保存最新文本用于恢复通知。

## macOS、软件和验证边界

Karabiner 只为配置中匹配的键盘把右 Option 映射为右 Command；不重映射 Caps Lock。
系统偏好脚本提供 `--check` 预览、`--apply` 应用、`--restore` 恢复：
设置 Safari 搜索、触控板轻点、关闭三指轻点查询、
自动切换浅色/深色、Dock 图标大小 31、固定 Spaces 顺序、取消平铺窗口间距、
按键重复、Finder 列表视图/路径栏/状态栏/扩展名和菜单栏项目，并重启相关桌面进程。
应用和恢复都会先保存托管键的原值，再写入并回读；只恢复托管键，其他设置不受影响。
无差异时不写入或重启，失败会保留备份并返回非零。需要已有 Python 3.9+，
命令与备份位置见[操作说明](commands.md#nori验证与手动系统偏好)。
它不由配置更新或软件安装入口执行；菜单栏使用 macOS 26 的键名，
不同 macOS 版本对这些 defaults 键的支持需要实际验收。

软件清单覆盖开发 CLI、编辑器/终端、文档媒体工具和 macOS 桌面应用。
完整包名以 [packages.yaml](../home/.chezmoidata/packages.yaml) 为准；被列入清单
不代表该应用的用户设置由仓库托管，例如 VS Code 配置与 Settings Sync 仍由用户管理。
Homebrew/apt 的安装与升级分开，版本不锁定；Miniforge 安装器固定版本和哈希，
只管理 base 安装，不负责项目环境升级。
Claude Code 不在清单中，用官方安装命令（`curl -fsSL https://claude.ai/install.sh | bash`）
安装到 `~/.local/bin` 并自行更新。

`scripts/test all` 运行 unit + static；cached-externals、runtime、终端检查、
VM 验收是其他独立范围。CI 在 Linux/macOS 运行离线套件，另有 Gitleaks 秘密扫描
和每月 GitHub Actions Dependabot 更新；详情见[测试说明](testing.md)。
