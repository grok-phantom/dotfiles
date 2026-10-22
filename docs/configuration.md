# 本机配置参考

本机数据通常在 `~/.config/chezmoi/chezmoi.toml` 的 `[data]`，XDG 配置目录可改变
路径。初始化模板是 [home/.chezmoi.toml.tmpl](../home/.chezmoi.toml.tmpl)，
实际管理范围还由 [.chezmoiignore.tmpl](../home/.chezmoiignore.tmpl) 决定。
修改这些值前先备份本机配置；模板、渲染后的 diff 和计划都可能关联私有信息。

## 基础数据与软件选择

| 键 | 默认 / 来源 | 作用 |
| --- | --- | --- |
| `profile` | 初始化默认 full；已有选择保留 | 直接 chezmoi 的 core/full 范围；更新 CLI 的 `--profile` 单独覆盖，默认仍为 full |
| `company` | 首次初始化询问，默认 false | workspace 公司目录与软件角色组，不决定 Git 身份 |
| `ephemeral` | 首次初始化询问，默认 false | 初始化时禁止 Homebrew，默认关闭 Claude 代理；外部字体跳过临时主机 |
| `sudo` | 首次初始化询问，默认 false | 无 sudo 时初始化关闭 Homebrew；apt 写操作要求 true 且 `sudo -n` 可用 |
| `homebrew` | 初始化默认 true，保留显式值，再受 ephemeral/sudo 守卫约束 | 允许软件入口使用已安装 Homebrew，不会安装 Homebrew 本身 |
| `git_name` / `email` | 首次询问，默认空 | 全局 Git 姓名和邮箱；空值不生成对应 user 项 |
| `hostname` | 当前主机名，保留已有值 | 本机模板数据，不应把渲染结果加入公共仓库 |
| `osid` | 初始化按 OS/发行版计算 | apt 判断支持的 Debian/Ubuntu/Pop!_OS/Raspbian 系统 |
| `package_cask_groups` | macOS 默认 desktop 加 company 或 personal | 覆盖 cask 组选择；`[]` 表示不选 cask，当前两个角色附加组为空 |
| `package_cask_exclude` | 默认不排除 | 从选中 cask 中排除包名；不卸载现有软件 |

软件完整清单在 [packages.yaml](../home/.chezmoidata/packages.yaml)。core 的软件入口
会报错，不是另一份精简安装清单。

`update_component` 是外部资源模板的选择值：默认 config，更新 CLI 用 `--component`
覆盖。只有 full + externals 才启用外部资源；`packages` 和 `external_lock`
由仓库 `.chezmoidata/` 提供，不需要复制到每台机器的 data。

## Git、SSH 与 Workspace

| 键 | 默认 / 开启条件 | 作用 |
| --- | --- | --- |
| `personal_email` | 未设置时不启用个人身份 include | 个人目录使用的 Git 邮箱 |
| `personal_git_dir` | `~/workspace/personal/` | Git `includeIf` 匹配的目录，应保留目录结尾 `/` |
| `personal_git_signing` | 默认关闭 | macOS 个人目录提交/tag 的 SSH 签名，需个人邮箱和公钥 |
| `git_hooks_path` | 未设置时不写 | 保留本机管理工具要求的 `core.hooksPath`，不安装 hooks |
| `ssh_managed` | 默认关闭 | 管理 `~/.ssh/config`、分类 include 和连接复用目录 |
| `ssh_1password_agent` | 默认关闭；macOS | 使用 1Password SSH agent；需已启用 SSH 管理和本机 App 的 agent |
| `ssh_personal_document` / `ssh_personal_vault` | document 未设置时忽略 personal.conf；vault 可选 | 从 1Password 文档渲染个人主机清单 |
| `ssh_personal_pubkey` | 默认空 | 渲染公钥文件，供主机选钥及个人 Git 签名使用；不渲染私钥 |
| `workspace_root` | 未设置时忽略 `~/workspace` 目标 | 把 `~/workspace` 管为指向指定目录的符号链接 |
| `workspace_volume_uuid` | 可选 | workspace 命令检查 macOS 外置卷身份，避免写到错误卷 |

私钥、`work.conf`、`temp.conf`、`*.local.conf`、`known_hosts*`、Git 的
`~/.config/git/local.conf` 和 workspace 仓库清单留在本机。迁移与签名准备见
[多 Mac 迁移](multi-mac.md)，卷挂载与克隆见 [Workspace](workspace.md)。

## 代理与 AI 工具

| 键 | 默认 / 开启条件 | 作用 |
| --- | --- | --- |
| `proxy_host` | `127.0.0.1` | shell、Claude、GUI 和检查工具共用的代理地址 |
| `proxy_http_port` | macOS 6152；其他平台 7890 | HTTP / HTTPS 代理端口 |
| `proxy_socks_port` | macOS 6153；其他平台 7890 | SOCKS 代理端口 |
| `claude_proxy` | 非 ephemeral macOS 默认 true，其他默认 false | 合并 Claude 代理 env；macOS full 同时管理 GUI 代理 LaunchAgent |
| `automation_git` | 默认关闭 | Claude 子进程 Git 使用 gh HTTPS 凭据和本机 `~/.ssh/automation-signing` |
| `automation_signing_pubkey` | 默认空 | 与 `personal_email` 一起增加本地 Git allowed signer；不生成私钥 |
| `roost_hooks` | 未设置时忽略 Codex；true 开启，显式 false 用于清理 | Claude/Codex 生命周期 hooks，并清理旧 Codex notify 包装；需已安装 `~/bin/roost` |

NO_PROXY 列表在 [proxy.json.tmpl](../home/.chezmoitemplates/proxy.json.tmpl) 中共享，
目前不是单独的 data 选项。`claude_proxy` 不控制 shell 的 proxyon/proxyoff。
GUI plist 只设置登录会话环境，首次需加载；修改已加载项后需重新加载并重启目标应用。
不要重复 bootstrap 已加载的 job 来代替重载。

Claude 设置在上述三个功能中至少一个为 true 时参与管理。Codex 只要 data 中
存在 `roost_hooks` 键就参与管理，因此 false 和删除键的含义不同。
Codex hooks 合并到 `~/.codex/hooks.json`；config.toml 模板只迁移旧 notify 包装，
接受单行或多行 TOML 数组（含注释和尾逗号）；无旧包装时原样保留，
需要迁移时只替换 notify 项，不会重写整份 TOML。
登录凭据、会话、记忆、其他 Codex 设置和 Roost 程序本身由各工具维护。

## nori 配置与定时检查

| 键 | 默认 / 开启条件 | 作用 |
| --- | --- | --- |
| `nori_config_dir` | 未设置时不选择部署目录；支持 nori / nori-mba | 对应 `~/.config/<目录>/nori.yaml` 和订阅文件 |
| `nori_machine_json` | 默认空 | JSON 字符串，含本机 deployment/target/storage/runtime 等字段；覆盖共享策略 |
| `nori_watch` | 默认关闭 | 结合非空配置目录，在 macOS full 管理 30 分钟一次的检查 LaunchAgent |

配置目录和 `nori_machine_json` 都有效时才渲染 nori 配置与订阅，渲染需要
1Password CLI 授权。Bark URL 仅在开启检查且本机 nori 配置也从 1Password
渲染时托管；否则由用户在本机放置 `~/.config/nori-watch/bark.url`（0600）。
订阅 URL 和机器字段只写入本机私有目标，不进入公开 source；代理服务由其他部署
流程管理。说明见[定时检查](multi-mac.md#nori-定时检查)。

## 运行时环境变量与本机文件

这些是命令启动时的参数，不需要写入 chezmoi data。

| 变量 / 文件 | 默认 / 用途 |
| --- | --- |
| `DOTFILES_PROXY_MODE` | off；仅影响交互 Zsh 的 brew/chezmoi 包装，on/proxy 启用代理，off/none/direct 直连 |
| `DOTFILES_CONDA_INIT` | source；hook 显式改用 `conda shell.zsh hook` |
| `SSH_PROXY_REMOTE_HTTP_PORT` / `SSH_PROXY_REMOTE_SOCKS_PORT` | 7890 / 7891；sshproxy 隧道与 proxyon-ssh 的远端端口 |
| `PROXY_CHECK_PROXY` / `PROXY_CHECK_TIMEOUT` | 覆盖检查代理 / 默认 8 秒；代理未覆盖时优先使用进程 HTTP(S) 代理变量，再用渲染默认值 |
| `SERVE_HERE_BIND` | 127.0.0.1；HTTP 文件服务监听地址 |
| `WORKSPACE_ROOT` / `WORKSPACE_VOLUME_UUID` / `WORKSPACE_COMPANY` | 覆盖命令的 workspace 根目录、卷校验值和公司目录选择；不改变 chezmoi 符号链接目标 |
| `~/.config/workspace/repos.tsv` | workspace clone 默认清单；使用自定义 XDG_CONFIG_HOME 时随之改变 |
| `RT_HOST` / `CLIP_REMOTE_HOST` | 远程 tmux / 图片上传的主机，低于命令行 `-H` 的优先级 |
| `~/.config/clip-to-remote/host` | 上述变量和 `-H` 均未指定时，取第一行 |
| `SSHTMP_FILE` | 默认 `~/.ssh/config.d/temp.conf`；测试可用 `SSHTMP_TODAY` 固定日期 |
| `NORI_WATCH_NORI` | 默认 `~/.local/bin/nori` |
| `NORI_WATCH_BARK` | 默认 `~/.config/nori-watch/bark.url` |
| `NORI_WATCH_STATE` | 默认 `~/.local/state/nori-watch/state.json` |
| `PYTHON` | 测试入口选择已有 Python 3.11+，不会安装解释器 |

## 关闭功能时的行为

开关通常改变的是管理范围，不是卸载动作。full → core、删除 SSH/nori 的选择值、
关闭定时检查，都不会自动移除旧文件或已加载的 LaunchAgent；需审查具体目标并
单独处理已有 job。禁用 GUI 代理还需清理登录会话里已设置的环境并重启应用。

`claude_proxy=false` 不会自动删除 Claude 已有代理 env。
`automation_git=false` 可清理模板识别为自有的 Git env，前提是 Claude 目标仍在
托管范围内。Roost 同理：显式 false 并 apply 可清理自有条目，但所有 Claude
开关都为 false 时 settings.json 会被忽略，需要另行审查清理原条目。
删除 `roost_hooks` 键会直接忽略 Codex，无法触发其清理。

重新 init 会保留初始化模板中列明的现有开关和参数；新加入的自定义 data 必须
确认模板是否保留。始终检查新配置和目标 diff，再做 apply。
