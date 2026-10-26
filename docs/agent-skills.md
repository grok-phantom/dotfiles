# Agent skills

Claude Code 和 Codex 共用一份 skill：正本在 `~/.agents/skills/<name>`（Codex 直接读取），
`~/.claude/skills/<name>` 是指向正本的相对软链接。这里只管理通用、可公开再分发的 skill。

## 管理方式

| 类别 | 来源 | 何时生效 |
| --- | --- | --- |
| 提交在仓库里 | [`home/dot_agents/skills/`](../home/dot_agents/skills)：自写的 skill，以及带本地改编或体积很小的 MIT / Apache-2.0 上游 skill，每个都附上游 LICENSE | 任意 profile 的普通 apply |
| 锁定的上游归档 | [`external-lock.json`](../home/.chezmoidata/external-lock.json) 里 `kind: skills` 的条目：固定 commit 和 SHA-256，每个 skill 解压成一个 exact 目录 | `--profile full --component externals`，并且本机 PATH 上有该组 skill 依赖的 CLI（`requires`） |
| Claude 软链接 | [`home/private_dot_claude/skills/`](../home/private_dot_claude/skills)，每个 skill 一个 `symlink_<name>` | 跟随对应的 skill；外部 skill 的链接只在 externals 运行中管理，平时只更新 config 时不会留下悬空链接 |

`~/.agents/skills` 和 `~/.claude/skills` 都不是 exact 目录：没有纳入管理的 skill
（Claude.ai 账号同步的、各工具自己安装的）原样保留。外部 skill 的目录是 exact 的，
上游删掉的文件在下次 externals apply 时会被删除。

## 提交在仓库里的 skill

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
| swift-concurrency-expert | Dimillian/Skills `05ba982`（MIT） | 与上游一致 |
| defuddle、json-canvas、obsidian-bases、obsidian-cli、obsidian-markdown | kepano/obsidian-skills（MIT） | 与上游一致，各自停在不同 commit |
| playwright | openai/skills `.curated/playwright` `972cb86`（Apache-2.0） | 与上游一致 |
| find-skills | vercel-labs/skills `773fb2c`（MIT） | 与上游一致 |

## 锁定的上游归档

| Skills | 上游 commit | requires |
| --- | --- | --- |
| `asc-*`（26 个） | rorkai/app-store-connect-cli-skills `a5702a6` | `asc` |
| `lark-*`（28 个） | larksuite/cli `017b19a` | `lark-cli` |
| `meegle` | larksuite/meegle-cli `e690ee5` | `lark-cli` |

固定的 commit 是 2026-10-26 时与本机已安装内容的 git tree hash 完全一致的上游提交，
接管前后文件没有变化。

## 不在这里管理

- Claude.ai 账号同步的 skill（docx、pptx、xlsx、pdf、computer-use 等）：许可证不允许再分发，由账号同步维护。
- 带个人路径的 skill（例如指向本机 Obsidian 库的研究项目 skill）。
- 来源不明的工具附带 skill（`meegle-plugin*`）。
- Matt Pocock 的 Codex 插件源（`~/.agents/skill-sources/mattpocock`）：它的 marketplace 名称带本机标识，公开前需要先改名，并同步修改各 Mac 的 Codex 配置。

## 更新

- 提交在仓库里的 skill：在 `~/.agents/skills` 审阅改动后，用 `chezmoi re-add` 或 `chezmoi add` 写回 source，再走正常的提交和 plan/apply 流程。
- 锁定归档：按 [依赖锁](../locks/README.md) 的流程审阅上游差异，一起修改 `revision`、`url`、`sha256`；上游新增或删除 skill 时同步修改 `skills` 列表和 Claude 软链接（`tests/test_updates.py` 会检查两者是否一致）。不要再对这些 skill 运行 `npx skills update`，否则下次 externals apply 会把它们改回锁定版本。
- 新增 skill：放进 `home/dot_agents/skills/<name>`，并添加 `home/private_dot_claude/skills/symlink_<name>`，内容为 `../../.agents/skills/<name>`。
