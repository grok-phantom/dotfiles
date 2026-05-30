# 仓库宪法

这是一个公开的、由 chezmoi 管理的 dotfiles 仓库。把它视为个人环境的
source tree，而不是通用软件项目。

## 硬性规则

- 保持本文件适合公开发布到 GitHub。不要加入 secrets、tokens、私有主机名、
  内部 URL、机器专属状态，或不应公开的身份细节。
- 保持 chezmoi 语义不变。仓库根目录通过 `.chezmoiroot` 指向 `home/`；
  `home/` 下的文件会映射到目标机器的 home directory。
- 不要重写大块生成文件或来自上游/vendor 的配置文件，除非用户请求明确需要。
- 不要随意移除平台或角色守卫。现有的 macOS、Linux、ephemeral machine、
  company machine、Homebrew、sudo access 等条件，是为了让同一份 source tree
  能在不同主机上使用。
- 优先做小而可逆的改动。dotfiles 会影响交互式 shell、包安装、编辑器、终端和
  Git 行为；大范围重构必须有清晰理由。
- 永远不要提交渲染后的 secrets 或本地运行时产物。私有值应按场景留在 chezmoi
  data、prompt、ignored files 或本地环境中。

## 仓库地图

- `home/.chezmoi.toml.tmpl` 定义 prompt 数据和 host-specific flags。
- `home/.chezmoidata/packages.yaml` 是受支持平台的软件包清单。
- `home/.chezmoiexternal.toml.tmpl` 声明外部获取的 archives、repositories、
  fonts 和 plugins。
- `home/.chezmoiignore.tmpl` 控制不同平台下哪些目标文件会被忽略。
- `home/.chezmoiscripts/` 包含由 chezmoi 运行的安装和配置脚本。
- `home/dot_zshrc.tmpl`、`home/dot_zprofile.tmpl` 及相关 shell 文件定义交互式
  shell 行为。
- `home/private_dot_config/` 映射到 `~/.config/` 下的 private files。
- `home/Library/` 是 macOS-specific target content。

## 命名与结构

- 遵循 chezmoi 命名约定：
  - `dot_foo` 渲染为 `.foo`。
  - `private_foo` 渲染为 private permissions。
  - `exact_foo` 管理 exact directory。
  - `*.tmpl` 文件是由 chezmoi 渲染的 Go templates。
- 新增托管文件时，放在 `home/` 下，并用文件名编码目标路径。
- 平台特定行为优先放在 template 条件或平台特定脚本目录中，不要复制整份文件。
- 软件包变更集中放在 `home/.chezmoidata/packages.yaml`，除非该包确实属于外部资源
  声明。

## Template 规则

- 引入新模式之前，优先沿用现有 chezmoi template helpers 和风格。
- 编辑 templated config files 时，保留设置编辑器 filetype 的 template 注释，例如
  Vim modelines。
- 优先使用 `lookPath`、`stat`、`.chezmoi.os` 等 capability checks，不要假设某个
  工具或路径一定存在。
- 公开仓库中的角色 flags 应保持泛化。可以提到 `company`、`ephemeral`、`sudo`
  行为，但不要加入私有操作细节。

## Shell 与脚本规则

- Shell scripts 应明确使用 POSIX shell 或 Bash；shebang 必须和实际语法一致。
- 现有 Bash scripts 使用 strict mode。除非有明确兼容性理由，否则保留
  `set -eufo pipefail`。
- 在加入会安装、删除、覆盖或获取资源的命令前，尽量让它们具备条件判断和幂等性。
- 避免在脚本里加入交互式 prompt，除非该脚本明确用于 chezmoi 初始化阶段提问。

## 验证

使用能证明改动的最小验证方式：

- 对 chezmoi 渲染或目标文件变更，优先在可用时运行 `chezmoi diff`。
- 对 template 编辑，尽量用 `chezmoi execute-template` 或其他聚焦的 chezmoi 命令渲染
  受影响文件。
- 对 shell scripts，运行 `bash -n <script>` 或对应 shell 的语法检查。
- 对 JSON、TOML、YAML，使用可用的 parser 或 formatter check。
- 对 Git 配置变更，在声称行为正确前，先检查渲染后的文件。

如果某个命令不可用，或验证会对真实机器产生非平凡影响，最终回复里必须明确说明。

## 变更纪律

- 编辑前先阅读周围上下文；很多设置依赖顺序。
- 注释保持有用且简短。解释不直观的选择，不解释显而易见的赋值。
- 匹配每个文件已有的缩进和格式风格。
- alias、keybinding 和 shell startup 改动应保持顺手且快速。
- 修改软件包列表时，同时考虑 macOS 和 Linux 的对应关系。
- 修改外部资源时，避免引入未固定或随时间移动的引用，除非现有模式已经有意这样做。

## 沟通

- 总结改了什么、触碰了哪些文件、运行了哪些验证。
- 点明任何依赖平台、chezmoi prompt 数据或可选工具的行为。
- 如果用户请求可能把私有信息暴露到这个公开仓库，先停下来，提出公开安全的替代方案。
