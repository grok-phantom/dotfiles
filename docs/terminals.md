# Terminals

macOS `full` manages one iTerm2 Dynamic Profile and a minimal Ghostty config.
`core` and Linux skip both; Linux package installation is unchanged.

## iTerm2

`wizplus` has its own stable GUID. The old exported GUID could collide with a
regular profile, causing iTerm2 to ignore the dynamic profile. Existing regular
profiles and the default profile are never replaced or selected automatically.
Choose **Profiles → wizplus** to try it.

The 46-line JSON explicitly owns MesloLGS NF 11, the existing Gruvbox ANSI palette,
selection/cursor colors, Option-key behavior, terminal type, mouse reporting,
scrollback/bell preferences and application-driven resize behavior. The empty
profile keyboard map is intentional; app-level shortcuts remain local. Other
fields inherit the default profile, including login shell, working directory,
close handling and window size. No global plist, session history, SSH commands or
machine paths are tracked. Keep global preferences local until a concrete portable
setting is needed. Changing the default parent later can change inherited fields.

Dynamic Profiles require `Name` and `Guid`; a regular profile with the same GUID
wins. See [iTerm2 documentation](https://iterm2.com/documentation-dynamic-profiles.html).

## Ghostty

Use `MesloLGS NF`, size 11, and `Gruvbox Dark`, with 8pt horizontal / 6pt
vertical padding. Keep macOS Option-character input (`macos-option-as-alt = false`);
terminal Alt-letter sequences are intentionally not enabled. Clipboard OSC 52 reads
ask first, including requests from SSH; OSC 52 writes (Claude Code, tmux, vim copy)
are allowed without a prompt, and the copy toast is off. Native Cmd+C/V remain
unchanged. Unsafe paste protection stays enabled. Commands running 30s or longer
send a desktop notification when they finish while Ghostty is unfocused. Directory inheritance and running-command
close confirmation use the verified 1.3.1 defaults. No extra shell/TERM setup is needed.
The existing full-profile font provision supplies MesloLGS NF. `config` remains
supported by 1.3.1 and older releases; `config.ghostty` is also supported since
1.2.3. A macOS config under `~/Library/Application Support/com.mitchellh.ghostty/`
loads after XDG config and may override it. Avoid maintaining conflicting copies.

Ghostty 1.4.0 stable was checked with its own CLI. Run `./scripts/verify-terminals`
after upgrades; it validates both source and effective config, font/theme presence,
and native search binding, failing when a required capability disappears.
This does not establish compatibility with every older release or GUI behavior.

Daily macOS shortcuts (Ctrl+Tab / Ctrl+Shift+Tab are unbound to avoid competing
with the app switcher):

| Action | Shortcut |
| --- | --- |
| Tab | Cmd+T; Cmd+Shift+[ / Cmd+Shift+] |
| Split right / down | Cmd+D / Cmd+Shift+D |
| Focus split | Cmd+[ / Cmd+] |
| Search | Cmd+F; Cmd+G / Cmd+Shift+G |
| Copy / paste | Cmd+C / Cmd+V |
| Claude / Codex multiline input | Shift+Enter sends Ctrl+J; in a regular shell this usually accepts the command |
| Fullscreen | Cmd+Enter or Ctrl+Cmd+F |

Automatic zsh integration is enabled; existing zsh/p10k/fzf/zoxide/Yazi/tmux
configuration stays intact. Do not source iTerm2 integration in Ghostty or set
`TERM` globally. Ghostty defaults to `xterm-ghostty`; its bundled terminfo works in
its own environment but may be missing on remote systems. This repository explicitly
sets `shell-integration-features = ssh-env,ssh-terminfo`, enabling Ghostty's SSH
environment and terminfo integration. SSH use may install terminfo on the remote
host; review that behavior for the target. The separate `mba` helper also checks
remote terminfo and falls back to `xterm-256color` if unavailable.
iTerm2's native tmux control-mode UI is not replicated
by Ghostty; normal tmux inside the terminal is a separate workflow.

Window state uses the macOS-dependent `window-save-state = default`; this is not a
promise to restore running shell jobs. Before making Ghostty primary, test Chinese
IME composition/candidates, mixed-width text, paste safety, Yazi previews, tmux,
search in long output, tabs/splits, and quit/relaunch with disposable sessions.
Automated text injection cannot verify IME feel. Keep iTerm2 available meanwhile.

Reload changes with **Cmd+Shift+,**; no restart of active jobs is needed.
To undo only this personalization, restore the previous Ghostty config in both
the source and target, then reload. Keep the private backup outside the repository.

## Herdr

在 Ghostty 中运行 `herdr`，通过 Machines 选择已添加的远端主机。
Herdr 的工作区、标签页和分屏使用 Ctrl+B 前缀；Cmd+T / Cmd+D 仍控制外层 Ghostty。
Ctrl+B 后按小写 q 只脱离客户端，后台会话继续运行。`herdr server stop` 会停止服务端及其中的进程。

full profile 在 macOS 和 Linux 管理 `~/.config/herdr/config.toml` 的共享偏好：
关闭首次引导、Gruvbox 主题、关闭主题自动切换、直接新建标签页、通过终端发送通知。
Agent 侧栏宽度设为 36，第一行显示状态和 pane 名称，第二行显示 workspace 和机器。
不再单独显示 Agent 类型和 tab 编号，给任务名称留出空间。
合并模板保留其他配置键；首次发生差异时会重新格式化 TOML，之后无差异则保留原文。
在 Herdr 设置页修改上述偏好后，下次 apply 会恢复仓库值。
Homebrew 软件清单包含 `herdr`；配置 apply 不会自动安装或升级软件。

### 插件与文件树

在需要使用插件的每台主机执行 `sh scripts/manual/herdr-plugins.sh`。
脚本按 `locks/herdr-plugins.tsv` 固定的提交安装九个插件，已匹配的安装会跳过。
应用配置后，脚本还会注册本仓库的 `dotfiles.quick-actions` 本地插件，
它声明四个工具标签页入口和 Codex 图片粘贴动作，不下载代码或运行常驻后台任务。
升级时先审阅新提交，再更新锁文件；不要直接用批量 update 绕过锁定版本。
`glow`、`git-delta` 和 `bat` 提供 Markdown、差异和代码渲染，均列在 Homebrew 清单中。

下列按键都先按 Ctrl+B 并松开，再按表中第二个键：

| 第二个键 | 操作 |
| --- | --- |
| `f` | 在当前项目旁边打开文件树和预览 |
| `Shift+F` | 在独立标签页打开文件树 |
| `Ctrl+G` | 打开 / 聚焦 / 关闭 lazygit 分屏 |
| `Ctrl+T` | 打开 / 切换 / 关闭 lazygit 标签页 |
| `Shift+Z` | 从 zoxide 常用目录新建工作区、标签页或分屏 |
| `Shift+O` | 给屏幕上的文件路径和链接标号，选择后预览 |
| `Ctrl+P` | Herdr Plus 项目布局，预置 Dotfiles 的 Shell / Git 标签页 |
| `Ctrl+A` | Herdr Plus 弹窗菜单；选中 Claude / Codex 后再新建标签页 |
| `Ctrl+N` | Navigator：统一找工作区、Agent、目录和快捷操作 |
| `Shift+M` | Memex：搜索并恢复历史会话 |
| `Ctrl+R` | Reviewr：查看差异并给 Agent 写逐行批注 |
| `F1` | 中文快捷键速查表；Mac 可能需要 Fn+F1 |
| `?` | Herdr 自带按键帮助，显示当前生效绑定 |

文件树内，方向键展开、折叠和选择，Tab 切换到右侧预览，`f` 找文件，`s` 搜内容，
`.` 显示隐藏文件，`q` 退出。查看器本身只读，`e` 会打开 Vim 编辑选中文件。
Quicklook 的自动 agent 建议保持关闭，只在手动调用时打开预览。
固定版本的提示扫描器会把中文句号及其前面的右括号收入 URL，例如
`https://example.com/docx/abc)。`。安装脚本会运行 `herdr-quicklook-fix.py`，
在扫描器清理英文括号前先去掉中文句末标点。补丁核对版本和文件哈希、备份原文件，
重复执行会跳过；升级 Quicklook 时需重新审阅，不盲目套用。

本机 Ghostty + Herdr Local + Codex 0.166.0 中，已实测 `Ctrl+Option+V`
能直接粘贴剪贴板图片，不需要 Raycast，也不加 Herdr 前缀。普通 `Ctrl+V`
无响应的拦截点尚未定位；这不等于 Codex 无法读取图片，未做全局按键重映射。
共享配置另将 Ghostty 的 `Cmd+V` 设为 `performable:super+v=paste_from_clipboard`：
可粘贴文本时保留原有粘贴路径，没有文本时将按键交给 Herdr。Herdr 的同名直接
绑定调用本地插件：按触发时捕获的 pane ID，将 Codex 的按键转为 `ctrl+alt+v`，
其他程序收到原来的 `super+v`，不模拟 Enter、不提交输入。该图片路径针对 Local，
不增加跨机器剪贴板传输；配置与路由测试通过，本机 Local + Codex 已实测
Cmd+V 图片和普通文字粘贴均正常。其他主机仍需各自重载并验证。
启用时先在 Ghostty 按 `Cmd+Shift+,`，再在 Herdr 按 `Ctrl+B → Shift+R` 重载。
macOS 用 `Ctrl+Cmd+Shift+4` 将选区截图直接复制到剪贴板；
普通 `Cmd+Shift+4` 默认保存文件，两者不是同一个操作。

完整中文速查表同步到 `~/.config/herdr/shortcuts.txt`，也可从快捷操作菜单打开。
先熟悉 Ctrl+N、f、Shift+M、Ctrl+R、Ctrl+A；这些入口都先按 Ctrl+B。
插件内部通常不加前缀，但 Navigator 的收藏键本身也是 Ctrl+B；当前 overlay
仍是普通 pane，需要连续按两次 Ctrl+B，才能把一次 Ctrl+B 传给插件。

按 Herdr 0.9.5 内置键位和 Ghostty 实际绑定核对，十二个前缀入口没有重复或
覆盖内置按键。Shift+N 保留新建工作区，Shift+H 保留交换左侧 pane。
Ctrl+B → Ctrl+R 打开 Reviewr，Ctrl+B → Shift+R 重新加载配置；普通终端中的
Ctrl+R 仍供 Shell 搜索历史。Ghostty 的 Cmd+Shift+P 打开外层命令面板。
Ghostty 保留 Shift+方向键选区绑定；Reviewr 选行用 `v` 后接普通方向键。
以上是配置与输入路由检查，实际按键效果仍需在终端中验证。

Herdr Plus 提供 Claude / Codex 当前目录入口、调用 cct / cxt 的临时任务入口、
chezmoi 差异查看、速查表和 Auto Title 启动入口。菜单使用 popup，Esc 直接收起；
选中 Claude / Codex 后，通过本地插件的 pane 入口在原工作区新建标签页，
继承打开菜单时的目录，并用登录交互式 zsh 启动工具。退出工具后标签页关闭。
差异和速查表留在弹窗中，按 q 收起；Auto Title 执行后直接收起。
当前版本的 quick action 子进程不继承 stdin，弹窗里的查看命令显式接入
`/dev/tty`；工具标签页由 Herdr 分配独立 PTY，不通过菜单转发输入。

Reviewr 使用 Gruvbox，手动打开独立标签页，不自动插入工作区。
Navigator 复用已有工作区，读取 Plus 项目和 zoxide；跨机器仍走 Machines，
不额外配置 Navigator 的 remote handoff。Navigator 需要 Cargo，Auto Title 需要 Go；
安装脚本先检查构建工具，Go 和 Memex 在 Homebrew 软件清单中。

Memex 只用本地索引，关闭 embeddings 和用量统计，恢复会话时使用新标签页。
配置合并保留自定义项；索引、历史和机器连接不进仓库。首次可以执行
`memex index --no-embeddings`；搜索会增量更新，Herdr 启动时也会更新索引。
每台主机检索各自的会话，不配置跨主机聚合，也不启动 Web 服务。

Auto Title 的共享偏好位于 `~/.config/herdr-auto-title/config.env`。
首次运行可能覆盖原有 pane 名称，应先备份本机 `session.json`。
安装到正在运行的服务端后，在快捷操作里选“Auto Title · 启用或刷新”启动，
无需重启服务端；以后随服务端启动。不要为启动插件结束正在运行的任务。

共享快捷键按 action 合并；如果占用了其他自定义命令或显式内置绑定，apply 会报错，
保留原配置。插件下载、注册表和运行状态不纳管，只同步偏好、布局和安装锁文件。

在 Machines 中先选中远端工作区，再按快捷键。远端也要安装这些插件和绑定，
否则本机安装不能代替远端安装。独立 `herdr --remote` 模式需使用
`--remote-keybindings server`；它与 Machines 切换是两种入口。
修改客户端设置后，在 Herdr 中按 Ctrl+B、Shift+R 重新加载配置。

### 应用共享配置

只应用 Herdr 配置并热加载，不重启现有 agent：

```sh
chezmoi diff --recursive ~/.config/herdr ~/.config/herdr-auto-title ~/.memex
chezmoi apply --recursive --exclude scripts ~/.config/herdr ~/.config/herdr-auto-title ~/.memex
herdr config check
herdr server reload-config
```

通知使用 `[ui.toast] delivery = "terminal"`。Ghostty 允许终端应用发送桌面通知；
macOS 仍需允许 Ghostty 通知。配置检查不能证明通知已弹出，需用后台工作区实际验证。

在实际运行 agent 的每台主机上显式安装集成：

```sh
sh scripts/manual/herdr-integrations.sh
```

脚本调用 Herdr 自带的 Claude/Codex 安装器，合并其 hooks，保留其他 hooks。
缺少对应 agent 配置目录时跳过。执行前备份 `.claude/settings.json`、
`.codex/config.toml` 和 `.codex/hooks.json`；自定义配置目录按环境变量替换。
集成记录会话身份，用于服务端重启后的原会话恢复，状态仍由 Herdr 检测。
安装后用 `herdr integration status` 核对，并从新启动的 agent 会话验证。
现有进程不会因为安装 hook 自动获得恢复信息。

machine 清单、会话、快照、日志和 socket 均留在本机。不要把整个 `.config/herdr` 加入 chezmoi。
旧 `mba` 入口仍用于 tmux/cmux，Herdr Machines 独立使用。

回退时恢复共享偏好模板和已备份的目标配置，再执行 `herdr server reload-config`。
要移除集成，执行 `herdr integration uninstall claude` 和 `herdr integration uninstall codex`；
不要用旧配置整份覆盖后来新增的其他 hooks。
插件可分别通过 `herdr plugin uninstall <plugin-id>` 移除；同时删掉对应的共享快捷键，
恢复备份配置后再热加载。卸载保留插件配置和状态，不删除项目文件。

## Apply and rollback

Preview/apply only these two targets with `chezmoi diff` / `chezmoi apply
--exclude scripts`; create `~/.config/ghostty` first if absent. Do not apply the whole
home tree just to trial a terminal. Back up the current DynamicProfiles JSON and
local iTerm2 plist privately before changing them; never commit a live plist.

Rollback the source with a forward `git revert` of the terminal change, then
restore the backed-up DynamicProfiles JSON. Remove the newly added Ghostty config
if there was no previous file (Git revert alone does not remove an unmanaged target).
Quit only disposable Ghostty sessions and move Ghostty.app to Trash if unwanted.
No default-terminal, startup or accessibility permission change is required.
Do not restore a stale whole plist over newer user preferences; it is a last-resort
backup, to restore only with iTerm2 fully quit and explicit review.

Sources: [installation](https://ghostty.org/download),
[configuration](https://ghostty.org/docs/config),
[shell integration](https://ghostty.org/docs/features/shell-integration).
