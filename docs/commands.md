# 命令速查

仓库入口从 source 根目录运行；`~/bin` 命令要先应用对应配置，再通过 PATH 使用。
开关与平台条件见[本机配置参考](configuration.md)，首次部署见[多 Mac 迁移](multi-mac.md)。

## 配置更新

需要 Python 3.9+、Git 和 chezmoi。所有阶段使用已提交的 source；普通未跟踪、
staged 或 unstaged 改动会阻止执行。先保存本地更改，再生成计划。

| 命令 | 行为 |
| --- | --- |
| `./scripts/dotfiles` / `status` | 检查 source、平台和目标漂移 |
| `./scripts/dotfiles fetch` | 从 origin/main fetch，不合并、不应用 |
| `./scripts/dotfiles plan --ref FETCH_HEAD --plan /tmp/dotfiles-plan-01.json` | 为候选提交生成计划；已有计划文件不会覆盖 |
| `./scripts/dotfiles apply --plan /tmp/dotfiles-plan-01.json --yes` | 核验计划、fast-forward、从已验证快照 apply 后 verify |
| `./scripts/dotfiles verify` | 检查当前提交的选中目标 |

| 参数 | 默认 / 用途 |
| --- | --- |
| `--profile core\|full` | full；选择配置范围 |
| `--component config\|externals` | config；externals 包含 full 配置和锁定外部资源 |
| `--remote` / `--branch` | origin / main；选择 fetch 来源 |
| `--ref` | HEAD；plan 的候选提交，不是 apply 时重新取分支头 |
| `--repo` / `--target` | 当前脚本所在仓库 / 当前用户 home |
| `--config` | `$XDG_CONFIG_HOME/chezmoi/chezmoi.toml`，XDG 未设置时在 `~/.config/` |
| `--state` / `--cache` | 可选的隔离 chezmoi 状态文件与缓存目录 |
| `--diff` | plan 显示完整渲染 diff，可能含本机私有值 |
| `--diagnostic-dir` | 仓库外尚不存在的私有诊断目录 |

plan/apply 保持相同的 profile、component、repo、target、config 和 state 参数，
目标或配置变化后重新 plan。实际写入步骤、外部 exact 目录和回退方法见
[README](../README.md#升级锁与回退)。不会执行 `.chezmoiscripts`。

## 软件维护

软件入口只接受 full，默认动作是 plan，要求 clean source。
package 操作针对真实主机，`--target` 不是包管理器沙箱。

| 命令 | 行为 |
| --- | --- |
| `./scripts/software packages plan` | 列出 Homebrew 清单和动作，不锁定包版本 |
| `./scripts/software packages install --yes` | 安装缺失包，不主动升级已安装清单项；依赖仍可能变化 |
| `./scripts/software packages upgrade --yes` | 更新 Homebrew 索引并升级清单项 |
| `./scripts/software packages verify` | 检查所选包是否安装 |
| `./scripts/software packages plan --manager apt` | 支持的 Debian 系统用当前本地索引模拟安装 |
| `./scripts/software packages install --manager apt --yes` | 需要本机 sudo 开关和 `sudo -n`；upgrade 同理 |
| `./scripts/software miniforge plan` | 显示固定版本和安装/更新状态 |
| `./scripts/software miniforge apply --yes` | 下载、核验 SHA-256 后安装；已有匹配标记时跳过重装 |
| `./scripts/software miniforge apply --yes --update-existing` | 明确允许更新已有 base；先自行备份环境 |
| `./scripts/software miniforge verify` | 检查安装器标记和 conda 可执行程序 |

`--manager` 默认 brew；需要终端密码交互的 Homebrew cask 可加 `--interactive`。
软件入口也支持 `--repo`、`--target`、`--config`、`--profile` 和 `--diagnostic-dir`；
软件诊断可能包含安装器原始输出。不会安装 Homebrew 本身、卸载未选包、运行 cleanup
或执行全系统 apt upgrade。软件选择见[配置参考](configuration.md#基础数据与软件选择)。

## Shell 日常操作

| 命令 / 设置 | 行为与依赖 |
| --- | --- |
| `cat` | 有 bat 时用 bat，否则尝试 batcat；原始行为用 `command cat` |
| `ls` / `ll` | 有 eza 时映射到 eza / `eza -lah` |
| `fd` | 检测到 fdfind 时为其建立别名 |
| `z` | zoxide 存在时启用的目录跳转 |
| Ctrl+R / ↑ | atuin 存在时由其初始化历史搜索；完整按键受 atuin/vi 模式影响 |
| `y` / `yy` / `r` / `ranger` | 启动 Yazi，退出时让当前 shell 切换到所选目录 |
| `cct [name] [claude args...]` | 在 `~/workspace/scratch/<name>` 启动 Claude；省略名称用时间戳，名称不可含 `/` 或以 `.` 开头 |
| `SHARE_HISTORY` | 两个 profile 都开启，让 shell 会话共享历史 |

例如 `cct notes --resume` 在固定的 scratch 目录继续 Claude 会话。
Conda、OMZ 和 Powerlevel10k 只在 full 初始化；其余工具按是否已安装初始化。

## 代理与 SSH 隧道

| 命令 | 作用域 |
| --- | --- |
| `proxyon` / `proxyoff` | 设置 / 清除当前 shell 大小写 HTTP(S)、ALL_PROXY、NO_PROXY 变量 |
| `withproxy command ...` | 仅此命令使用配置的代理和 NO_PROXY |
| `noproxy command ...` | 仅此命令移除 HTTP(S)/ALL_PROXY 变量；保留 NO_PROXY |
| `sshproxy [ssh options] user@host [command]` | SSH 连接，同时把本机代理反向转发到远端 |
| `sshproxy-tunnel [ssh options] user@host` | 同上，但 `ssh -N` 只保持隧道 |
| `proxyon-ssh` | 在远端 shell 中使用已转发的 loopback 端口；不负责建立隧道 |
| `proxy-check [url]` | 用 curl 比较直连和代理访问，默认访问 GitHub API，退出码取代理检查结果 |

`SSH_PROXY_REMOTE_HTTP_PORT` / `SSH_PROXY_REMOTE_SOCKS_PORT` 默认 7890 / 7891，
建立隧道和远端启用时应保持一致。`proxyon-ssh` 不写 NO_PROXY。
Zsh 中的 brew/chezmoi 包装默认直连，`DOTFILES_PROXY_MODE=on` 切到代理；
Python 更新入口使用进程环境，不经过这些 shell 函数。

## 开发小工具

| 命令 | 行为 |
| --- | --- |
| `jsonfmt [file ...]` | 从文件或 stdin 格式化 JSON 到 stdout；优先 jq，回退到 Python，不原地覆盖文件 |
| `port-listen port [port ...]` | 查询 TCP LISTEN 进程；使用 lsof，缺失时回退 ss |
| `serve-here [port] [directory]` | Python HTTP 文件服务，默认当前目录、8000 端口、127.0.0.1；也可只传目录 |

`SERVE_HERE_BIND` 可改变监听地址；服务会暴露指定目录中的文件。
`PROXY_CHECK_PROXY` / `PROXY_CHECK_TIMEOUT` 分别覆盖 proxy-check 的代理和超时
（默认 8 秒）。以上四个小工具都支持 `--help`。

## Workspace 与临时 SSH 主机

| 命令 | 行为 |
| --- | --- |
| `workspace init` | 创建代码目录骨架，保留已有内容 |
| `workspace doctor` | 检查目录布局、缺少 origin、没有远端引用覆盖的提交；提示未提交更改 |
| `workspace list` | 输出仓库相对路径和 origin，TAB 分隔 |
| `workspace clone [file]` | 从本机清单克隆缺失仓库；默认读 `~/.config/workspace/repos.tsv` |
| `sshtmp add lab user@192.0.2.5:2222 --days 3` | 添加或替换临时主机；另支持 `--jump`、`--identity` |
| `sshtmp list` | 显示临时主机，并写回清理后的清单 |
| `sshtmp extend lab --days 7` | 从今天起续期；add/extend 默认 7 天 |
| `sshtmp rm lab` / `sshtmp prune` | 删除指定临时主机 / 到期主机 |

`sshtmp` 专管 `~/.ssh/config.d/temp.conf`，不要混入手写主机块；
`SSHTMP_FILE` 可改变文件位置。`ssh_managed=true` 时主配置会 include 此文件，
否则需要自行 include。workspace 目录与外置盘规则见[专页](workspace.md)。

## 远程开发

| 命令 | 行为与前提 |
| --- | --- |
| `rt [-H host] [session]` | SSH 登录 shell 中连接/创建 tmux 会话，默认 main；无 TTY 时通过 macOS AppleScript 打开 Ghostty 标签页 |
| `clip-to-remote [-H host] [-s] [image ...]` | macOS 剪贴板图片或文件上传；`-s` 先框选截图 |
| `shot-to-remote` | 调用 `clip-to-remote -s`，使用已配置的默认主机 |
| `git-ssh-sign` | Git 自动调用的签名适配器：本机用 1Password signer，SSH 会话用 ssh-keygen |

运行 Codex 时，先用 `rt codex` 连接名为 `codex` 的远程会话，再在远端运行 `codex`。
`rt` 只管理 SSH/tmux 连接，会话名不会自动启动同名程序；远端需已安装 Codex。

主机优先级：`-H` → `RT_HOST` / `CLIP_REMOTE_HOST` →
`~/.config/clip-to-remote/host` 第一行。截图工具需要 macOS 截屏/自动化权限与可用
SSH；上传会更新剪贴板，并在符合条件时把路径输入前台 Ghostty。
文件扩展名仅接受字母和数字；没有扩展名时使用 `.png`。
目录创建、写入或远端清理失败时返回错误，保留原剪贴板，不输入上传路径。
远端 `~/.cache/clip` 超过 7 天的文件在上传时清理。设置步骤见[远程开发说明](multi-mac.md#远程开发主机)。

## 编辑器与文件管理

| 程序 | 自有配置提供的操作 |
| --- | --- |
| Vim | F6 调用 ALEFix；F8 切换 Tagbar；`<leader>c` / `<leader>cc` 通过 OSCYank 复制选区/整行 |
| Yazi | `h` 上级，`l` smart-enter，`gg` / `G` 首尾，Ctrl+D/U 半页，`yy` 复制、`dd` 剪切、`p` 粘贴，`r` 重命名 |
| Yazi | `v` 选择，`.` 隐藏文件，`/` 搜索，`:` shell，`t` 新标签，`gt` / `gT` 切换标签 |
| Ghostty | Shift+Enter 发送 Esc+Return；其余 Cmd 快捷键见[终端说明](terminals.md) |

这些按键基于安装好的 full 外部资源；语言工具还需对应项目环境。

## nori、验证与手动系统偏好

`nori-watch --config /path/to/nori.yaml --print` 只打印 nori 状态问题，不发送 Bark
也不写状态文件。要同时探测代理，加 `--proxy http://127.0.0.1:6152`，端口应与本机
配置一致。去掉 `--print` 会按变化发送通知并记录状态。选项还包括 `--max-age-hours`
（默认 60）、`--name`、`--probe-url`、`--direct-url`。退出码 0 为正常、1 为发现问题、
2 为通知发送失败；默认本机依赖路径见[配置参考](configuration.md#运行时环境变量与本机文件)。

| 命令 | 验证范围 |
| --- | --- |
| `./scripts/test all` / `make test` | unit + static |
| `./scripts/test unit` / `./scripts/test static` | 单独选中套件 |
| `./scripts/test cached-externals --cache /path/to/cache` | 已下载锁定资源的校验与临时目标应用 |
| `./scripts/test runtime --cache /path/to/cache` | 在上述基础上检查 Zsh/Vim/Tmux |
| `./scripts/verify-terminals` | iTerm2 JSON；macOS 上检查已安装 Ghostty 的配置、字体、主题和搜索能力 |
| `bash -n scripts/manual/macos-defaults.sh` | 只做脚本语法检查 |
| `bash scripts/manual/macos-defaults.sh --apply` | 实际修改 macOS 偏好并重启相关桌面进程，需先阅读脚本 |

测试入口支持 `--report-dir`（新目录）和 `PYTHON`（已有 Python 3.11+）。
测试、缓存集成、GUI 和 VM 验收的区别见[测试说明](testing.md)。
