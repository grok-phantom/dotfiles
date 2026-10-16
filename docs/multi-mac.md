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
| `personal.conf` | 自己的机器和服务器 | 设了 `ssh_personal_document` 时从 1Password 文档渲染（可选 `ssh_personal_vault`）；否则本机手写，chezmoi 不动 |
| `work.conf` | 公司主机 | 只在获准的机器上本机手写，永远不进 Git、不进个人 1Password |
| `temp.conf` | 临时主机 | `sshtmp` 维护，每条带到期日 |
| `*.local.conf` | 本机其他 | 本机手写 |

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
- **个人主机清单**：在 1Password 建一个 Document（例如名为 `SSH hosts`），内容就是 `personal.conf`。本机设 `ssh_personal_document = "SSH hosts"`，需要 `op` 命令行（`1password-cli`，已在软件清单）并在 1Password 设置里打开 Integrate with 1Password CLI。只有渲染 `personal.conf` 时才读 1Password，`status`/`plan` 也会触发一次读取授权。
- **提交签名**：再设 `personal_git_signing = true`（需要 `personal_email` 和 `ssh_personal_pubkey`），个人目录下的提交和 tag 由 1Password 签名（`op-ssh-sign`），并生成 `~/.config/git/allowed_signers` 供本地验证。把同一把公钥作为 Signing key 加到 GitHub，提交会显示 Verified。
- **无人值守的 git（`automation_git`）**：1Password 每次连 GitHub、每次签名都要人点批准，锁屏后直接失败，Claude Code 自动跑的 git 就会卡住。在需要的机器上设 `automation_git = true`，chezmoi 往 `~/.claude/settings.json` 的 `env` 写一组 `GIT_CONFIG_*`，只影响 Claude Code 启动的 git，你自己终端里的 git 不变：
  - GitHub 改走 HTTPS，凭据用 `gh auth git-credential`（`gh auth login` 已登录的 token；建议用只授权个人仓库的 fine-grained PAT）；
  - 签名改用本机磁盘上的 `~/.ssh/automation-signing`（`ssh-keygen` 直接签，不经 agent）。这把钥只放这台机器、不放 1Password，丢了只吊销它：
    ```bash
    ssh-keygen -t ed25519 -N '' -C "$(hostname -s)-automation" -f ~/.ssh/automation-signing
    ```
    把公钥加到 GitHub → Settings → SSH and GPG keys → **Signing key**（不要加成 Authentication key），并写进本机 data `automation_signing_pubkey`，`allowed_signers` 会多一行用于本地验证。
  - 关掉开关再 apply，只删除这组由它写入的 `GIT_CONFIG_*`；重启 Claude Code 后生效。连服务器的 SSH 仍走 1Password，写主机的操作照旧要人批准。
- 主机清单很少变，改完 1Password 里的文档后再 `chezmoi apply ~/.ssh/config.d/personal.conf` 即可。

切换前后用 `ssh -G <alias>` 逐个核对 hostname/user/port/proxyjump/identityfile；`ssh -G` 成功不代表能登录。

参考：[chezmoi 的 1Password 集成](https://www.chezmoi.io/user-guide/password-managers/1password/)、[1Password SSH agent 配置](https://developer.1password.com/docs/ssh/agent/config/)。

## 容器与代理迁移

容器、Compose、订阅转换、LaunchAgent 和代理服务属于本机 infra。先查明当前消费链、
数据卷和启动来源，再安排停用。替代订阅工具只有通过真实订阅等价性、代理原生重载
和回退验收后才能代替现用实例。不要把“测试通过”当成生产链路验收。
移除实例前保存可恢复定义、精确镜像和持久数据备份，并验证备份可读、恢复步骤明确；
保留数据与镜像，不运行 prune。权限不足时停止该操作并报告。
