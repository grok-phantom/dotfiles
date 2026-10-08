# 多 Mac 迁移与本机边界

默认 `full` 选择完整用户环境；它不意味着复制整台 Mac。`company`、`ephemeral`、
`sudo`、`homebrew` 与 Git 身份仍是各设备自己的数据。不要复制另一台机器的 chezmoi
配置、SSH 目录、Keychain、浏览器资料、代理订阅或公司账户到新机。

## 迁移顺序

1. 在旧机记录 `git status --short`、`git log -5 --oneline`，保存未提交改动和未推送
   提交。不要用重新克隆覆盖唯一 source；若提交未在远端，可单独备份受审查的仓库，
   不打包整个 home。先检查仓库历史是否含秘密。
2. 新机独立安装 Git、Python 3.9+ 和 chezmoi。核实仓库来源与提交后，执行
   `chezmoi init --source /path/to/repo`，不加 `--apply`。回答本机角色、权限与身份，
   profile 默认 full；保留已有 core 选择时需明确检查。测试工具需要 Python 3.11+。
3. 备份本机 chezmoi 配置和将要覆盖的目标，备份保存在仓库外、限制权限。先运行
   `./scripts/test all --report-dir /tmp/dotfiles-migration-tests`（目录须不存在）。
4. 执行 `./scripts/dotfiles status` 和
   `./scripts/dotfiles plan --plan /tmp/dotfiles-migration-plan.json`。
   默认只预览 full 自有配置，不下载插件、不安装软件、不改系统偏好。
   若检测到目标本地改动，手工检查并协调；不要为了通过检查清空目标。
5. full 使用的外部插件需单独计划：
   `./scripts/dotfiles plan --component externals --plan /tmp/dotfiles-externals-plan.json`。
   此步骤可下载锁定资源；exact 目录可能删除额外文件，必须阅读目标清单与本地 diff。
   审查后以相同参数 `apply --plan ... --yes`，最后 `verify --component externals`。
6. 软件另行 `./scripts/software packages plan`。macOS 清单来自
   `home/.chezmoidata/packages.yaml`，运行时生成 Brewfile；没有独立的常驻 Brewfile。
   full 的通用 cask 列表不是公司批准的软件清单，先评审再显式 install/upgrade。
   Miniforge 同样有独立 plan。系统偏好脚本只能在另行审查后手动执行。
7. 核对登录 shell、终端、Git 身份和代理端口；外部资源、软件与本机服务分别验收。
   没有一键整机 bootstrap 或完整 doctor；测试只证明其记录的平台和选中范围。

默认更改不安装任何东西。CLI 固定默认 full，直接 chezmoi 则尊重本机显式 profile。
回退默认值应恢复本次修改的 source 文件；已应用目标需单独使用备份恢复。
未提交的 source 改动会让更新 CLI 拒绝执行，先审查提交再生成实际 apply 计划。

## SSH 分层方案（尚未自动安装）

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
新设备只迁移批准的个人主机配置，分别核实密钥来源与主机信任后再测试连接。

## 容器与代理迁移

容器、Compose、订阅转换、LaunchAgent 和代理服务属于本机 infra。先查明当前消费链、
数据卷和启动来源，再安排停用。替代订阅工具只有通过真实订阅等价性、代理原生重载
和回退验收后才能代替现用实例。不要把“测试通过”当成生产链路验收。
移除实例前保存可恢复定义、精确镜像和持久数据备份，并验证备份可读、恢复步骤明确；
保留数据与镜像，不运行 prune。权限不足时停止该操作并报告。
