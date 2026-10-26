---
name: review-smart
description: 代码评审入口：先看改动范围，再决定只跑 code-review，还是追加 architecture-critic、design-critique 或某个专项 skill，最后合并成一份结论。用于"review 一下""评审这次改动""帮我看看这个 PR"等没有指定具体评审流程的请求；用户已点名某个评审 skill 时直接用那个，不经过这里。
---

# Review Smart

用最少的评审流程覆盖这次改动的风险。不要默认把所有评审叠在一起跑：每多一个流程，就多一遍完整读代码，结论也更容易互相冲突。

## 1. 确定范围

- 用户给了 PR 号、分支或路径就用它；否则取当前分支相对默认分支的提交，加上未提交的改动（`git diff --stat <base>...HEAD`、`git status --short`）。
- 记下：改动文件数、增删行数、涉及哪些顶层目录、是否新增模块或目录、文件类型。
- 没有改动就说明并停止。

## 2. 选流程

默认只跑 code-review，再按下面的信号追加。每追加一项都要写出触发它的具体信号。

| 信号 | 追加 |
|---|---|
| 新增模块或目录、跨多个顶层目录、改了公共接口或数据模型、引入新依赖或新抽象层、改动超过约 400 行 | `architecture-critic` |
| 改了界面（SwiftUI View、storyboard/xib、HTML/CSS/JSX/TSX 组件、样式或设计 token），并且能拿到截图或运行起来的界面 | `design-critique` |
| 涉及鉴权、密钥、shell 拼接、反序列化、外部输入或权限 | `security-review`（有这个 skill 时） |
| SwiftUI 代码 | `swiftui-pro` |
| async/await、actor、Sendable、Task | `swift-concurrency-expert` |
| 主要是 Swift 测试改动 | `swift-testing-expert` |

- 除 code-review 外最多追加两项；信号更多时取风险最高的两项，其余列为"可选，未运行"。
- 纯文档、配置值、重命名、格式化：只跑 code-review。少于约 20 行的改动直接通读评审，不启动任何流程。
- 界面改动拿不到截图时，不跑 design-critique，在结论里说明缺什么。

## 3. 执行顺序

1. 先跑 `architecture-critic`：方向错了，细节 bug 就没有意义。如果它的结论是需要推倒重来，先停下来报告，问用户是否还要继续细审。
2. 再跑 code-review。Claude Code 里是 `/code-review`；没有这个 skill 时（例如在 Codex 里）用内置的 `/review`，或者自己按正确性逐项审查。
3. 最后跑专项 skill 和 `design-critique`。

所有流程都只读。除非用户要求，不自动修复。

## 4. 汇总

- 第一行：选了哪些流程，各自因为什么信号。
- 合并去重后按严重程度排序；多个流程提到同一个问题时只列一次，并标注来源。
- 建议互相冲突时（例如 architecture-critic 建议删掉，code-review 建议补全），并列给出两边的理由，再给出推荐。
- 最后列出没跑、但可能值得跑的流程，每项一句理由。
