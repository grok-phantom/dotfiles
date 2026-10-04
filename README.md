# dotfiles

个人用户环境的 chezmoi source tree。`.chezmoiroot` 指向 `home/`。
机器服务、Docker 权限、防火墙、系统级代理等属于独立 infra；应用部署属于应用仓库。
这里不做服务器管理，也不自动修改登录 shell、用户组或持久权限。

## 更新入口

需要 Python 3.9+、Git、chezmoi（本次验证版本 v2.73.0）。默认只检查：

```sh
cd ~/.local/share/chezmoi
./scripts/dotfiles
./scripts/dotfiles fetch
git diff --stat HEAD..FETCH_HEAD
git diff HEAD..FETCH_HEAD
./scripts/dotfiles plan --ref FETCH_HEAD --plan /tmp/dotfiles-plan.json
# 阅读变更后，使用同样的 profile/component/config/target/state 参数：
./scripts/dotfiles apply --plan /tmp/dotfiles-plan.json --yes
./scripts/dotfiles verify
```

计划文件必须放在仓库外，权限为 0600，已有文件不会覆盖。使用新的文件名生成新计划。
`plan --diff` 可显示渲染后的完整 diff，可能包含本机私有配置，请只在本机查看。
默认只显示目标路径；计划只保存提交、选项和哈希，不保存渲染后的配置内容。

| 阶段 | 实际行为 |
| --- | --- |
| `status`（默认） | 检查平台、Git source 状态和选中目标的 chezmoi 状态，不升级软件 |
| `fetch` | 检查后只 `git fetch` 指定 remote/branch，更新 Git 元数据，不 merge、不 apply |
| `plan` | 将指定提交导出到临时 source，渲染并预览；检查权限，绑定 source/target/config/平台/渲染结果 |
| `apply --yes` | 重做检查，拒绝过期计划，只允许 fast-forward，再使用这次验证保留的提交快照 apply 和 verify |
| `verify` | 从当前 HEAD 的提交快照检查选中目标；不是安装器或整机测试 |

source 有 staged、unstaged 或 untracked 改动会停止；没有 autostash、rebase、reset 或 clean。
目标有上次 apply 后的本地修改也会停止。先手工检查 `chezmoi status`、`chezmoi diff`，
用 `chezmoi merge` / `chezmoi add` 等保存需要的更改，再提交和重新规划；不要为了通过检查丢弃改动。
分支分叉、回退提交或 detached HEAD 不由入口自动处理。

配置入口的 status、plan、apply 和 verify 都只读取已提交的 source 快照。
Git 忽略且未提交的文件不参与渲染或写入，现有的对应用户目标也不会因此被接管。
匹配 ignore 规则但已明确提交的文件仍属于计划。普通未跟踪、staged、unstaged 改动继续使入口停止。
apply 在重新核验计划后保留同一临时快照直到写入和验证完成，并检查 source HEAD 未发生意外变化；
成功或失败后都会清理临时导出。直接运行 chezmoi 的 source 规则不受此入口约束。

配置更新不执行 `.chezmoiscripts`，也不调用包管理器安装/升级。
fetch 禁止交互认证，SSH 连接等待上限 15 秒，整体等待上限 120 秒；需要事先配置可用的凭据/agent。
`--config PATH` 默认指向 `$XDG_CONFIG_HOME/chezmoi/chezmoi.toml`（未设置时为 `~/.config/chezmoi/chezmoi.toml`）；
非 TOML、非标准路径必须显式指定。隔离验证可同时设置 `--repo`、`--target`、`--state`、`--cache`。
读取本地配置及执行模板仍需信任所选 source：模板中的 `output` 等函数本来就能执行命令，
本入口不是运行不可信 dotfiles 的沙箱。不要在另一个更新进程或编辑器同时修改目标时 apply。

## Profile 和组件

| 选择 | 范围 |
| --- | --- |
| `core`（CLI 和新初始化默认） | Git、基础 Zsh 配置、开发小工具、pip/uv 配置；不管理 OMZ/Vim/Tmux/Yazi/字体/桌面配置，不初始化 Conda |
| `full` | 保留原来的软件与完整用户环境选择；配置里启用 OMZ、Vim、Tmux、Yazi、终端和 Conda 初始化 |
| `--component config`（默认） | 所选 profile 的仓库自有文件；不下载/更新外部资源，不运行安装脚本 |
| `--profile full --component externals` | 完整配置及锁定的外部资源一起预览/应用；首次预览可能下载到 chezmoi cache 并校验 SHA-256 |

CLI 的 profile 默认固定为 core；要保持完整环境，每次使用 `--profile full`。
直接使用 chezmoi 时由本机 `data.profile` 决定，未设置也为 core。
从 full 切回 core 会忽略对应目标，不卸载已有工具、不删除之前已生成的文件。
这只是两个固定 profile，没有任意组合的组件框架，也没有多设备清单或主机调度。

外部资源更新示例：

```sh
./scripts/dotfiles plan --profile full --component externals --plan /tmp/externals-plan.json
./scripts/dotfiles apply --profile full --component externals --plan /tmp/externals-plan.json --yes
./scripts/dotfiles verify --profile full --component externals
```

此组件包括外部目录的 `exact` 管理：归档之外的额外文件可能被删除，必须检查计划。
自有 Vim 配置与 Zsh completion 移到 `~/.config/vim/`、`~/.config/zsh/completions/`，
不再与 exact 外部目录重叠，因此 config-only 不会清除外部内容。
Jedi 的 Jedi/Parso 子模块也分别固定到父项目所引用的 commit；Yazi smart-enter 由锁定归档提供。
Vim 的 `.vimrc` 和 Tmux 的 `.tmux.conf` 现在是可 diff 的目标；不再运行上游安装器或 `ln -sf`。
`~/.tmux.conf.local` 保持用户自管。full 配置建议先应用 externals，避免缺少插件或产生临时悬空链接。

## 软件安装和升级：单独执行

软件命令也默认只 plan，要求 clean source 和 `--profile full`，从原 `packages.yaml` 读取同一份清单。
它不更新 dotfiles Git 分支，也不会接着应用配置。
包管理器操作针对当前主机，不是 `--target` 下的沙箱；软件入口对 package 组件拒绝其他 target。

```sh
./scripts/software packages --profile full
./scripts/software packages install --profile full --yes
./scripts/software packages upgrade --profile full --yes
./scripts/software packages verify --profile full
# Debian / Ubuntu / Pop!_OS / Raspbian：显式选择 apt
./scripts/software packages plan --profile full --manager apt
./scripts/software packages install --profile full --manager apt --yes
./scripts/software packages upgrade --profile full --manager apt --yes
```

Homebrew 必须预先安装且本机 `data.homebrew=true`；本仓库不再执行 `install/HEAD/install.sh`。
install 使用 `bundle --no-upgrade` 并关闭自动 update/cleanup；upgrade 才显式执行 `brew update`
和 `bundle --upgrade`。`--no-upgrade` 不保证依赖绝不升级：为安装缺失包，Homebrew 仍可能调整依赖。
包清单不是版本锁，也不能保证重建完全相同的系统；Brew plan 只列清单与操作类型。
apt plan 使用当前本地索引做安装模拟，执行阶段才更新索引；需要本机 `data.sudo=true` 和可用的
非交互 `sudo -n`。apt 升级仅针对清单中的已安装包，不执行全系统 upgrade/full-upgrade。
操作非事务性：失败时停止后续步骤，但不声称撤销已经安装的包。

```sh
./scripts/software miniforge --profile full
./scripts/software miniforge apply --profile full --yes
# 更新已有安装前先导出环境并备份；显式允许对 base 运行锁定安装器 -u：
./scripts/software miniforge apply --profile full --yes --update-existing
./scripts/software miniforge verify --profile full
```

Miniforge 固定为 `locks/miniforge.json` 的版本，下载后必须通过锁定 SHA-256 才执行。
覆盖 macOS arm64/x86_64、Linux aarch64/x86_64；其他平台立即拒绝。
仅管理 `$HOME/opt/miniforge3`（或显式 `--target` 下的同路径）。成功后记录安装器哈希，重复运行不重装；
没有标记的旧安装需要 `--update-existing`。verify 检查标记和 conda 可运行，
不声称验证 base 中每个包。已有环境及 conda 环境内的包升级由用户另外规划；不执行 `conda init`。

## 首次使用、身份和迁移

先备份已有目标和本机 chezmoi 配置。可用 `chezmoi init --source PATH` 生成本机数据（不加 `--apply`），
阅读其提示和生成内容，再使用上述 plan。新用户的 Git 姓名/邮箱默认空，由本人输入；
company flag 不再代表某个固定身份。已有 `data.email` 保留，姓名需显式设置 `data.git_name`。
如原来依赖仓库硬编码姓名，迁移时先在本机补充姓名，避免中断 Git 提交。

`~/.config/git/local.conf` 是可选的本机 Git include，适合身份、组织 URL rewrite 等；
它不属于本仓库托管范围。不要把凭据、主机专属地址、私钥、token 或渲染后的私有配置提交到公开仓库。
现有 localhost 代理辅助函数保留，但包装函数默认直连；需要时显式设置 `DOTFILES_PROXY_MODE=on`
或调用 `withproxy`。Python 更新入口使用进程环境中的代理变量，不继承交互 Zsh 的函数包装。

macOS 偏好保留在 `scripts/manual/macos-defaults.sh`，阅读脚本后可单独运行：
`bash scripts/manual/macos-defaults.sh --apply`。它会改系统偏好并重启相关桌面进程，
不在任一更新组件中自动调用。dotfiles 更新不要求授予 Full Disk Access。
登录 shell、Docker 组、服务、网络与持久权限由用户/infra 单独评审操作；这里没有自动命令。
Docker 组访问接近 root 权限，不能当成普通 dotfiles 的便利设置。

## 升级锁与回退

外部锁位于 `home/.chezmoidata/external-lock.json`，每项记录上游 repo、完整 commit、URL、SHA-256。
这次归档哈希来自对固定 URL 的实际下载，Miniforge 哈希来自同版本官方 `.sha256` 发布文件。
锁定时间与方法见 [locks/README.md](locks/README.md)。更新时：核对上游变更，选择明确 commit/tag，
下载固定 URL 并独立计算/核对 SHA-256，更新锁，跑测试，在临时 home 预览，最后提交锁变更。
不再用 `master`、`latest` 或定期刷新隐式选版本；不提供无审查的“一键更新全部锁”。
固定归档若被上游重打包导致哈希变化，先停下来核对，不删除校验来绕过失败。

保留每次升级前的 source commit、计划和目标备份。撤销已提交变更优先用 `git revert` 产生新的向前提交，
手工保存 apply 后新增的本地更改，再为 revert 提交重新 plan/apply。
本入口拒绝倒退/分叉提交；若确需旧版测试，用独立 worktree 和临时 target。
chezmoi apply 不是全局事务；中途失败可能留下部分目标变化且 source 已 fast-forward，应检查后重新规划。
包管理器和 Miniforge base 的回退依赖其自身机制/环境备份，不由 Git rollback 自动完成。

## 验证与边界

统一入口为 `./scripts/test all`（或 `make test`），自动选择已有 Python 3.11+；
可用 `PYTHON=/path/to/python3.13` 明确指定。入口隔离 HOME/XDG，并生成绑定提交、
平台和依赖版本的 JSON 报告，不安装软件。单元/mock、缓存集成和 CI 的区别见
[测试说明](docs/testing.md)；[macOS VM 验收计划](docs/macos-vm-acceptance.md) 已准备但尚未执行。
下面保留的是原始底层命令，推荐日常使用上述统一入口。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
# 可选：使用事先下载且与锁一致的归档/字体缓存做完整离线集成验证
PYTHONDONTWRITEBYTECODE=1 python3 tests/check_cached_externals.py --cache /path/to/upstream-cache
bash -n scripts/manual/macos-defaults.sh
git diff --check
```

测试使用临时 Git source、target、chezmoi config/state/cache，以及 mock 网络/包管理器。
真实 chezmoi 负责模板渲染、计划和临时目标应用；没有向真实 home 应用，没有安装工具或修改系统设置。
macOS VM 可作为后续完整安装/系统偏好的隔离验证；Linux apt 和另一种 CPU 的实际运行也需对应环境。
这些尚不是已完成的生产验证，`--dry-run` 也不代表执行测试了全部脚本。

官方行为依据：

- [chezmoi update](https://www.chezmoi.io/reference/commands/update/)：默认 `pull --autostash --rebase`；`--apply=false` 仍拉取，因此本入口不用它。
- [chezmoi status](https://www.chezmoi.io/reference/commands/status/)：第一列是上次写入后目标的变化，第二列是将要应用的变化。
- [Global flags](https://www.chezmoi.io/reference/command-line-flags/global/)：dry-run 保护 destination；`refresh-externals=never` 仍会下载未缓存资源，不是离线保证。
- [External checksums](https://www.chezmoi.io/reference/special-files/chezmoiexternal-format/) 与 [Homebrew bundle](https://docs.brew.sh/Manpage#bundle-subcommand)。
- [Miniforge](https://github.com/conda-forge/miniforge)：固定版本支持范围和现有安装 `-u` 行为。
