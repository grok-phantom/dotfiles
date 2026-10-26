# 多 Mac 迁移与本机边界

默认 `full` 选择完整用户环境；它不意味着复制整台 Mac。`company`、`ephemeral`、
`sudo`、`homebrew` 与 Git 身份仍是各设备自己的数据。不要复制另一台机器的 chezmoi
配置、SSH 目录、Keychain、浏览器资料、代理订阅或公司账户到新机。

## 迁移顺序

1. 在旧机记录 `git status --short`、`git log -5 --oneline`，保存未提交改动和未推送
   提交。不要用重新克隆覆盖唯一 source；若提交未在远端，可单独备份受审查的仓库，
   不打包整个 home。先检查仓库历史是否含秘密。
2. 新机独立安装 Git、Python 3.9+、chezmoi 与 Homebrew（macOS 软件入口的前置条件）。核实仓库来源与提交后，执行
   `chezmoi init --source /path/to/repo`，不加 `--apply`。回答本机角色、权限与身份，
   profile 默认 full；保留已有 core 选择时需明确检查。测试工具需要 Python 3.11+。
3. 备份本机 chezmoi 配置和将要覆盖的目标，备份保存在仓库外、限制权限。先运行
   `./scripts/test all --report-dir /tmp/dotfiles-migration-tests`（目录须不存在）。
4. 执行 `./scripts/dotfiles status` 和
   `./scripts/dotfiles plan --plan /tmp/dotfiles-migration-plan.json`。
   默认只预览 full 自有配置，不下载插件、不安装软件、不改系统偏好。
   若检测到目标本地改动，手工检查并协调；不要为了通过检查清空目标。
5. 软件另行 `./scripts/software packages plan`，审查后显式 install。macOS 清单来自
   `home/.chezmoidata/packages.yaml`，运行时生成 Brewfile；没有独立的常驻 Brewfile。
   既有 cask 列表保留为 desktop 组；company/personal 组初始为空，选择方法见下文。
   Miniforge 同样有独立 plan。系统偏好脚本只能在另行审查后手动执行。
6. 软件基线准备好后，为 full 外部插件和配置重新计划：
   `./scripts/dotfiles plan --component externals --plan /tmp/dotfiles-externals-plan.json`。
   此步骤可下载锁定资源；exact 目录可能删除额外文件，必须阅读目标清单与本地 diff。
   审查后以相同参数 `apply --plan ... --yes`，最后 `verify --component externals`。
7. 执行 `./scripts/test runtime --cache /path/to/reviewed-cache`，再核对终端、Git 身份和代理端口；外部资源、软件与本机服务分别验收。
   没有一键整机 bootstrap 或完整 doctor；测试只证明其记录的平台和选中范围。

默认更改不安装任何东西。CLI 固定默认 full，直接 chezmoi 则尊重本机显式 profile。
回退默认值应恢复本次修改的 source 文件；已应用目标需单独使用备份恢复。
未提交的 source 改动会让更新 CLI 拒绝执行，先审查提交再生成实际 apply 计划。

## 软件选择与本机参数

默认 full 的编辑基线包含 Vim、其 Python 运行时、fzf 和 Universal Ctags；
Debian 系用 vim-nox 提供 Python 能力。Python/C++ 的 flake8、black、clang-format、
clang-tidy 由项目环境提供，打开 Vim 前进入对应环境；`:ALEInfo` 可检查可用性。
本仓库不会为所有项目全局安装这些语言工具。

macOS 默认选 `desktop` 加本机角色组（company 或 personal）。desktop 使用当前托管
cask 列表；两个角色组初始为空。tldr、Discord、qBittorrent 已从软件声明和生成计划
移除，shell 不再加载 tldr 插件；现有安装保留，不执行卸载或 cleanup。可在本机 chezmoi
`[data]` 显式设置 `package_cask_groups = ["desktop", "personal"]`，覆盖角色默认，
并用 `package_cask_exclude = ["example-app"]` 排除个别条目；`package_cask_groups = []` 表示不选择任何
cask（`package_cask_exclude = []` 则不排除条目）。这些选择只影响以后计划/安装/升级，永远不执行卸载。company 标志不是公司批准清单。

重新 init 会保留已有身份/profile、代理地址/端口、hostname、显式关闭的 Homebrew
以及上述软件选择；ephemeral/sudo 守卫仍可禁止 Homebrew。先备份本机配置再初始化。
PATH 在 shell 启动时检查用户工具目录并去重，后装工具不再要求重新 apply。

Conda 默认直接加载本机 `conda.sh`，只初始化命令，保持仓库关闭 base 自动激活的行为。
脚本缺失时回退到 `conda shell.zsh hook`。需要自定义 hook/自动激活语义时，可在本机
启动环境设置 `DOTFILES_CONDA_INIT=hook`；不会改 Conda 安装或已有环境。

## SSH 配置

按机器选择启用：本机 chezmoi data 设 `ssh_managed = true` 后，`~/.ssh/config` 由本仓库生成；未设置的机器完全不碰 `~/.ssh`。生成的配置只有 Include 和默认项，主机按类别放在 `~/.ssh/config.d/`：

| 文件 | 类别 | 来源 |
| --- | --- | --- |
| `personal.conf` | 自己的机器和服务器 | 设了 `ssh_personal_fleet` 时由本机 infra 仓库的 `fleet.json` 生成；否则设了 `ssh_personal_document` 时从 1Password 文档渲染（可选 `ssh_personal_vault`）；都没设则本机手写，chezmoi 不动 |
| `work.conf` | 公司主机 | 只在获准的机器上本机手写，永远不进 Git、不进个人 1Password |
| `temp.conf` | 临时主机 | `sshtmp` 维护，每条带到期日 |
| `*.local.conf` | 本机其他 | 本机手写 |

主机在家（局域网）和在外走不同路线时，在它的 `Host` 块前加一个反向条件块，例如
`Match host NAME !exec "~/bin/ssh-lan-reachable 192.0.2.10 22"` 后面写跳板（`ProxyJump`）：连得上局域网地址就直连，否则走跳板，
`ssh NAME` 在哪都一样用。`ssh-lan-reachable` 绑定物理网卡探测，不会被 Surge 增强模式骗过；同网段才探测，不在家时立刻返回。
Transmit 等不认 `ProxyJump`/`Match` 的 SFTP 客户端另给固定路线的别名。

OpenSSH 取第一个匹配的值，所以类别文件都在 `Host *` 默认项之前；某台主机需要例外（如 `ForwardAgent yes`、旧的 `ssh-rsa`）就写在它自己的块里。不存在的文件会被跳过。

`Host *` 默认项：保活、`ControlMaster auto`（套接字在 `~/.ssh/controlmasters/`）、`ForwardAgent no`；macOS 上设 `ssh_1password_agent = true` 再加 1Password SSH agent 的 `IdentityAgent`。

临时主机：

```sh
sshtmp add lab root@192.0.2.5:2222 --days 3 [--jump bastion] [--identity ~/.ssh/key]
sshtmp list            # 顺带清掉已过期的
sshtmp extend lab --days 7
sshtmp rm lab
sshtmp prune
```

临时主机的主机密钥写到 `~/.ssh/known_hosts.temp`（`accept-new`），不和长期主机的已核实指纹混在一起。

### 1Password

- **私钥**：放在 1Password，由 SSH agent 签名，不渲染到磁盘。把它的公钥写进本机 data `ssh_personal_pubkey`，chezmoi 生成 `~/.ssh/personal-1password.pub`；个人主机写 `IdentityFile ~/.ssh/personal-1password.pub`，开了 agent 后默认 `IdentitiesOnly yes`，只出示主机指定的那把钥。1Password → Settings → Developer → Use the SSH agent；导入或新建密钥后，删除磁盘上的旧私钥，并把对应公钥更新到各服务器的 `authorized_keys`。公司密钥不放个人 vault。
- **个人主机清单**：主机统一写在私有 infra 仓库的 `fleet.json`。有这个仓库的机器设 `ssh_personal_fleet = "/绝对路径/infra"`，直接生成，不经 1Password；没有的机器（例如只装了 1Password 的新 Mac）用下面的 1Password 文档，由 infra 的 `scripts/fleet ssh --publish` 更新，不要手改。
- **1Password 文档（备用来源）**：在 1Password 建一个 Document（例如名为 `SSH hosts`），内容就是 `personal.conf`。本机设 `ssh_personal_document = "SSH hosts"`，需要 `op` 命令行（`1password-cli`，已在软件清单）并在 1Password 设置里打开 Integrate with 1Password CLI。只有渲染 `personal.conf` 时才读 1Password，`status`/`plan` 也会触发一次读取授权。
- **提交签名**：再设 `personal_git_signing = true`（需要 `personal_email` 和 `ssh_personal_pubkey`），个人目录下的提交和 tag 由 1Password 签名（`op-ssh-sign`），并生成 `~/.config/git/allowed_signers` 供本地验证。把同一把公钥作为 Signing key 加到 GitHub，提交会显示 Verified。
- **无人值守的 git（`automation_git`）**：1Password 每次连 GitHub、每次签名都要人点批准，锁屏后直接失败，Claude Code 自动跑的 git 就会卡住。在需要的机器上设 `automation_git = true`，chezmoi 往 `~/.claude/settings.json` 的 `env` 写一组 `GIT_CONFIG_*`，只影响 Claude Code 启动的 git，你自己终端里的 git 不变：
  - GitHub 改走 HTTPS，凭据用 `gh auth git-credential`（`gh auth login` 已登录的 token；建议用只授权个人仓库的 fine-grained PAT）；
  - 签名改用本机磁盘上的 `~/.ssh/automation-signing`（`ssh-keygen` 直接签，不经 agent）。这把钥只放这台机器、不放 1Password，丢了只吊销它：
    ```bash
    ssh-keygen -t ed25519 -N '' -C "$(hostname -s)-automation" -f ~/.ssh/automation-signing
    ```
    把公钥加到 GitHub → Settings → SSH and GPG keys → **Signing key**（不要加成 Authentication key），并写进本机 data `automation_signing_pubkey`，`allowed_signers` 会多一行用于本地验证。
  - 关掉开关再 apply，只删除这组由它写入的 `GIT_CONFIG_*`；重启 Claude Code 后生效。连服务器的 SSH 仍走 1Password，写主机的操作照旧要人批准。
  - 无人值守的远程开发主机再设 `automation_git_global = true`：同样的设置写进 `~/.config/git/config` 末尾，终端、Codex 等所有 git 都不再等 1Password（否则 SSH 会话里的 push 和签名每次都要在你面前的 Mac 上批准，人不在就卡住）。代价是这台机器上任何进程都能用 gh 令牌推送、用本机钥签名，所以 gh 令牌要限定到个人仓库。
- 主机清单很少变，改完 1Password 里的文档后再 `chezmoi apply ~/.ssh/config.d/personal.conf` 即可。

切换前后用 `ssh -G <alias>` 逐个核对 hostname/user/port/proxyjump/identityfile；`ssh -G` 成功不代表能登录。

参考：[chezmoi 的 1Password 集成](https://www.chezmoi.io/user-guide/password-managers/1password/)、[1Password SSH agent 配置](https://developer.1password.com/docs/ssh/agent/config/)。

## 远程开发主机

常用的远程开发主机名写在本机 `~/.config/clip-to-remote/host`（第一行，不进 Git），下面几个命令共用。它们都带 Raycast 头，在 Raycast → Settings → Extensions → Script Commands 里 Add Directories 选 `~/bin`，再给各自绑全局快捷键：

- `rt [session]`（Remote tmux）：`ssh -t` 后直接 `tmux new-session -A -s <session>`（默认 `main`），断线或 detach 后会话仍在远端。远端缺 Ghostty terminfo 时回退到 `xterm-256color`。从 Raycast 运行时，装了 cmux 就把会话镜像进 cmux（不填会话名则镜像远端全部会话，每个会话是侧边栏一行），否则在 Ghostty 新开标签页执行 `rt`；`RT_APP=ghostty` 强制用 Ghostty。cmux 里可以直接粘贴图片到远端，不需要 `clip-to-remote`。
- `shot-to-remote`（Screenshot to Remote）：框选截图 → 上传到远端 `~/.cache/clip/` → 远端路径进剪贴板；Ghostty 在前台时直接把路径输入到当前终端，正在远端跑的 Claude Code / Codex 输入框里就有了。
- `clip-to-remote`（Clip Image to Remote）：同上，但上传剪贴板里已有的图片，或命令行给出的文件；`-s` 等同 `shot-to-remote`。
- `rtunnel`（Reverse SSH Tunnel）：反方向，让远端能 `ssh -p 2222 127.0.0.1` 登回你面前这台 Mac（本机要开远程登录），例如让远端的 agent 在这台 Mac 上同步配置或测试。Raycast 里选 Toggle 开关；终端里 `rtunnel` 看状态，`rtunnel on 4` 开 4 小时，`rtunnel off` 关。默认 2 小时后自动关闭，开和关都会弹系统通知。端口只监听在远端的 127.0.0.1，但远端上任何进程都能用它，所以只在需要时打开；端口用 `RTUNNEL_PORT` 改。

用 Codex 远程开发时，在本机执行 `rt codex`，进入远端会话后再执行 `codex`。
远端需已安装 Codex；`rt` 使用登录 shell 查找工具，会话名本身不会自动启动程序。
再次执行 `rt codex` 可接回同一会话。

Ghostty 里 Shift+Enter 发送 Esc+Return：Claude Code 把它当换行，隔着 SSH 和 tmux 也一样；zsh 里是在命令行中插入换行。Codex 也可用 Ctrl+J。

### Tailscale

Mac 之间（以及家里主机）走 Tailscale，SSH 别名直接指向对方的 Tailscale 地址，不再需要跳板、在家/在外条件块或 Transmit 专用路线。主机清单仍在 infra 的 `fleet.json`。

- 有人用的 Mac：`tailscale-app`（软件清单里的 cask，带菜单栏界面）。首次打开时允许网络扩展，登录后在菜单里取消 Use Tailscale DNS（DNS 交给 Surge）。
- 无人值守的主机：不装 cask（本机 data `package_cask_exclude = ["tailscale-app"]`），改用命令行版，免去屏幕上的确认：
  ```sh
  brew install tailscale
  sudo brew services start tailscale
  sudo tailscale up --hostname=<名字> --accept-dns=false   # 打印的链接在另一台机器上打开授权
  ```
  然后在管理后台对这台机器 Disable key expiry，否则约半年后掉线且无法在本机重新登录。
- 和 Surge 增强模式共存：基础配置的 `[Rule]` 里让 `tailscale.com` 走代理、Tailscale 进程（`tailscaled`、`io.tailscale.ipn.macsys.network-extension`）和 `100.64.0.0/10` 直连。**不要**加 `tun-excluded-routes = 100.64.0.0/10`：它会让这段地址经物理网关发出，并挡住 Tailscale 自己的路由，结果 `tailscale ping` 通而 SSH 超时。核对：`netstat -rn -f inet | grep '^100\.64'` 应指向某个 `utun`，不是 `en0`。
- 中继：国内到官方中继延迟高，私有 infra 在自己的服务器上跑了中继（`derper`），登记在管理后台的 `derpMap`。`tailscale ping <主机>` 显示 `via DERP(…)` 为中继、`via <IP>:<端口>` 为直连；中继速度受那台服务器的出口带宽限制。

### 远端不弹窗

远端合盖时，任何需要在它屏幕上点的确认都等于卡死。约定：在 SSH 会话里（`SSH_CONNECTION` 非空）需要签名的操作都走转发过来的 agent，1Password 在你面前这台 Mac 上确认：

- `ssh`（含 `git push` 到 GitHub）：`~/.ssh/config` 的 `Match` 块在 SSH 会话中一律用 `SSH_AUTH_SOCK`；没有可用的转发 agent 时直接失败，不回落到远端的 1Password。
- tmux 会话比 SSH 连接活得久，旧 pane 里的 `SSH_AUTH_SOCK` 会失效。`~/.zprofile` 在每次 SSH 登录时把 `~/.ssh/agent-forwarded.sock` 指向当前的转发 socket，并让后续进程都用这个固定路径。改动之前已经开着的 tmux 会话要重开一次（`tmux kill-server`，或新建会话）才会用上。
- 提交签名：`gpg.ssh.program` 是 `~/bin/git-ssh-sign`，本机用 `op-ssh-sign`，SSH 会话里改用 `ssh-keygen` 经转发 agent 签名。
- 远端 Claude Code 自己跑的 git 用 `automation_git`（见上文），完全不需要确认；远端也设上它。

仍会在远端弹窗的：远端执行 `op` / 需要 1Password 的 `chezmoi apply`（1Password CLI 走远端的桌面 App），以及 macOS 钥匙串访问确认（例如 Claude Code 升级后首次读取登录凭据）。这些在远端本机处理一次即可，或在远端选“始终允许”。

这几个命令每次都是新的 `ssh` 进程，主机块里关掉 `ControlMaster` 时每次都要走一遍 1Password 确认（有 ProxyJump 时是两次）；让该主机沿用默认的 `ControlMaster auto` 后，8 小时内的后续连接复用同一条连接，不再询问。

## nori 定时检查

`~/bin/nori-watch` 的 LaunchAgent 每 30 分钟检查本机的 nori 部署，问题有变化时推 Bark（新问题，以及全部恢复后的一条 all clear）。检查项：`nori status` 能否读出、代理和定时刷新是否开着、是否需要维护或恢复、上次刷新是否报错、是否超过 60 小时没有刷新成功，以及经本机代理（`proxy_host:proxy_http_port`）访问 `cp.cloudflare.com/generate_204`（走兜底规则的默认代理组，不经过 AI_Services）；失败会隔 10 秒、30 秒各重试一次，三次都失败才算问题，单个节点偶发 503 不报警。直连也不可达时跳过代理故障判断；nori 本身的状态问题仍会报告。Bark 请求直接发出，不经过被检查的代理。

按机器开启：data 设 `nori_watch = true`，并用 `nori_config_dir` 指明部署读取的目录（`nori` 或 `nori-mba`）。macOS full 会管理 LaunchAgent `local.dotfiles.nori-watch`，首次需要手动加载：`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.dotfiles.nori-watch.plist`，之后登录时自动加载。nori 配置从 1Password 渲染的机器（设了 `nori_machine_json`），Bark 地址同样从 `Personal/infra secrets` 的 `bark_url` 渲染到 `~/.config/nori-watch/bark.url`；其他机器手工放这个文件（0600）。`nori-watch --config <nori.yaml> --print` 只检查 nori 状态、不推送；要同时验证代理，加 `--proxy <本机代理 URL>`，LaunchAgent 已带此参数。日志在 `~/Library/Logs/nori-watch.log`，记录发现的问题及通知失败。

同一刷新故障仅小时数增长时不会重复通知；状态仍保存最新年龄用于恢复提醒。
共享策略渲染、所有开关及
关闭后的清理行为见[本机配置参考](configuration.md#nori-配置与定时检查)。

## 容器与代理迁移

容器、Compose、订阅转换、LaunchAgent 和代理服务属于本机 infra。先查明当前消费链、
数据卷和启动来源，再安排停用。替代订阅工具只有通过真实订阅等价性、代理原生重载
和回退验收后才能代替现用实例。不要把“测试通过”当成生产链路验收。
移除实例前保存可恢复定义、精确镜像和持久数据备份，并验证备份可读、恢复步骤明确；
保留数据与镜像，不运行 prune。权限不足时停止该操作并报告。
