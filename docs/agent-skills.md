# Agent skills

Claude Code 和 Codex 共用一份 skill：正本在 `~/.agents/skills/<name>`（Codex 直接读取），
`~/.claude/skills/<name>` 是指向正本的相对软链接。

分工很简单：**自写或本地改过的 skill 由这个仓库管理；和上游一致的 skill 用官方安装器安装和更新。**
仓库只管自己的那部分，`~/.agents/skills` 和 `~/.claude/skills` 都不是 exact 目录，其余 skill 原样保留。

## 由仓库管理

[`home/dot_agents/skills/`](../home/dot_agents/skills) 里每个 skill 一个目录，
[`home/private_dot_claude/skills/`](../home/private_dot_claude/skills) 里对应一个
`symlink_<name>`（`tests/test_updates.py` 会检查两者是否一致）。上游 skill 都附带了上游 LICENSE。

| Skill | 上游 | 说明 |
| --- | --- | --- |
| review-smart | 自写 | 按改动范围挑选评审流程 |
| ppt-style-director、product-architecture-coach | 自写 | |
| architecture-critic、code-simplify | anthropics/claude-plugins-official（Apache-2.0） | 本地改编，见各自 SOURCE.json |
| design-critique | anthropics/knowledge-work-plugins（Apache-2.0） | 本地改编 |
| systematic-debugging | obra/superpowers（MIT） | 本地改编 |
| swiftui-pro | twostraws/SwiftUI-Agent-Skill（MIT） | 本地改编 |
| swift-testing-expert、swiftui-expert-skill | AvdLee（MIT） | 本地改编 |
| app-store-changelog、project-skill-audit、review-and-simplify-changes | Dimillian/Skills（MIT） | 本地改编 |

改动流程：在 `~/.agents/skills` 改好并审阅后，用 `chezmoi re-add` 写回 source，再正常提交、plan/apply。
新增 skill：放进 `home/dot_agents/skills/<name>`，并添加内容为 `../../.agents/skills/<name>` 的
`home/private_dot_claude/skills/symlink_<name>`。只放可公开再分发、不含个人路径的 skill。

## 用官方安装器

这些 skill 和上游一致，直接安装、更新，不进仓库。`npx skills add -g` 会装到
`~/.agents/skills`（Codex 直接读取），并给 Claude Code 建链接；之后用 `npx skills update -g` 更新。

安装时始终加 `-a codex claude-code`，只装给这两个 agent。不加的话 CLI 会沿用上次选过的
agent 列表，给 Cursor、Gemini、Copilot 等各建一份 `~/.<agent>/skills`。`-a` 会吞掉后面所有
不以 `-` 开头的参数，所以仓库名要写在它前面。

| Skill | 安装 |
| --- | --- |
| asc-*（App Store Connect，需要 `asc`） | `npx skills add rorkai/app-store-connect-cli-skills -g -a codex claude-code` |
| lark-*（飞书，需要 `lark-cli`） | `npx skills add larksuite/cli -g -a codex claude-code` |
| meegle（飞书项目） | `npx skills add larksuite/meegle-cli -g -a codex claude-code --skill meegle` |
| defuddle、json-canvas、obsidian-bases、obsidian-cli、obsidian-markdown | `npx skills add kepano/obsidian-skills -g -a codex claude-code` |
| swift-concurrency-expert | `npx skills add Dimillian/Skills -g -a codex claude-code --skill swift-concurrency-expert` |
| find-skills | `npx skills add vercel-labs/skills -g -a codex claude-code --skill find-skills` |
| playwright | 在 Codex 里用自带的 `skill-installer` 安装（装到 `~/.codex/skills`） |

不加 `--skill` 时会列出仓库里所有 skill 让你选。

## 不在这里管理

- Claude.ai 账号同步的 skill（docx、pptx、xlsx、pdf、computer-use 等）：许可证不允许再分发，由账号同步维护。
- 带个人路径的 skill（例如指向本机 Obsidian 库的研究项目 skill）。
- 工具自己附带的 skill（例如 `meegle-plugin*`）。

## Matt Pocock 插件（Codex）

[`home/dot_agents/skill-sources/mattpocock/`](../home/dot_agents/skill-sources/mattpocock) 是
mattpocock/skills 1.3.1 的本地改编版（MIT，见其 SOURCE.json），作为 Codex 本地 marketplace
`dotfiles-local` 提供插件 `mattpocock-skills`。chezmoi 只同步插件源文件；在 Codex 里注册
marketplace、安装插件仍用 Codex 自己的命令，这样配置和插件缓存才能保持一致。

每台 Mac 上做一次（apply 之后）：

```sh
codex plugin marketplace list            # 找出 source 指向 ~/.agents/skill-sources/mattpocock 的旧名称
codex plugin remove mattpocock-skills@<旧名称>
codex plugin marketplace remove <旧名称>
codex plugin marketplace add ~/.agents/skill-sources/mattpocock
codex plugin add mattpocock-skills@dotfiles-local
```

从没注册过的 Mac 只需要最后两行。插件源有更新时，重新运行 `codex plugin add mattpocock-skills@dotfiles-local` 刷新缓存。
