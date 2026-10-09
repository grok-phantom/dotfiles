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

## SSH 分层方案（尚未自动安装）

机器的 company 角色与 SSH 主机组分别选择，不根据主机名称或本机角色推断归属。
后续约定由本机显式选择 `personal`、`work` 主机组，并允许个别主机覆盖；同一台机器
可以同时选择经批准的两组，也可以不选。真实分组清单、地址、用户名和保险库引用只留
本机或获准的 1Password 资料中，公开仓库仅记录字段约定。当前不增加生效中的 SSH
模板/Include，不移除现有连接，不改变 agent；后续先确认归属、允许设备及提示策略。

建议保留 `~/.ssh/config` 为本机入口：先放精确主机配置，再放 `Host *` 默认项。
可由用户审查后 Include 本机 `config.d/personal.conf`、获准的
`config.d/work.conf`，以及工具自己维护的 Include。OpenSSH 多数选项采用首个匹配值，
不要把会遮蔽主机例外的全局值放在最前面。

- 公开仓库只保存这份流程与占位说明，不托管真实主机清单或 SSH 文件。
- 个人清单单独记录 alias、用途、HostName、User、Port、公钥指纹、凭据来源和允许设备。
- 公司清单留在批准的设备/凭据系统；个人 Mac 不自动引入 work Include。
- 私钥不放 Git、不进迁移包。公钥分发与 authorized_keys 修改单独授权。
- 每设备密钥配合 Keychain，或经批准使用密码管理器 agent；切换之前先逐主机核实
  IdentityFile/IdentityAgent/IdentitiesOnly，不全局扩大 agent forwarding。
- 不关闭主机校验、不移除口令以减少提示；known_hosts 应由已核实的主机指纹建立。

按别名先静态运行 `ssh -G <alias>`，核对 hostname/user/port/proxyjump/identityfile。
输出仍是别名本身通常意味着映射缺失；`ssh -G` 成功不是网络、凭据或登录成功。
如存在 `Match exec`，静态解析也可执行本机命令，需先审查配置。
跳板账号与管理账号分别命名：仅允许转发的账号不能用于 shell/SFTP。
新设备只迁移该设备获准的主机组配置，分别核实密钥来源与主机信任后再测试连接。

### 可选的 1Password 后端

chezmoi 支持通过 `onepasswordRead`、`onepassword` 等模板函数读取 1Password，
因此敏感主机配置也可以保存在获准的 vault 中，按本机权限渲染。本仓库当前不调用
这些函数，也不要求安装 `op`；本机 Include 结构可以在后续单独迁移时保留。

建议分开处理两类数据：主机地址、用户名等配置由可选模板读取，SSH 私钥由
1Password SSH agent 提供签名。不要为了实现模板化而把私钥渲染到磁盘。真实 vault、
item、field 引用及后端选择留在本机数据中；公开模板只引用泛化的数据字段。
公司与个人凭据分别授权，未启用后端的机器继续使用现有本地配置和认证方式。

后续模板只读取显式选中的主机组，个别覆盖优先；普通 config/status/plan 不调用
秘密 provider。先用无真实地址的 fixture 验证角色变更不影响 SSH 选择、两组合并、
重复 alias 冲突及覆盖规则，再接入获准资料。认证资料读取和 agent 接入另行确认。

启用前需要另行审查：本机 `op` 与账户访问、准确字段映射、渲染文件权限、diff 和
计划日志中的秘密处理、agent 提供的密钥范围，以及锁定/解锁时的授权体验。
CLI 读取与 SSH agent 签名是两个授权流程；不能把接入模板等同于免验证登录。
本机 Keychain 与现有 agent 设置不会因选择 full 或同步仓库而改变。

参考：[chezmoi 的 1Password 集成](https://www.chezmoi.io/user-guide/password-managers/1password/)、
[1Password SSH agent 配置](https://developer.1password.com/docs/ssh/agent/config/)。

## 容器与代理迁移

容器、Compose、订阅转换、LaunchAgent 和代理服务属于本机 infra。先查明当前消费链、
数据卷和启动来源，再安排停用。替代订阅工具只有通过真实订阅等价性、代理原生重载
和回退验收后才能代替现用实例。不要把“测试通过”当成生产链路验收。
移除实例前保存可恢复定义、精确镜像和持久数据备份，并验证备份可读、恢复步骤明确；
保留数据与镜像，不运行 prune。权限不足时停止该操作并报告。
