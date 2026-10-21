# 分支与 worktree 维护

在新功能或文档工作前先刷新远端引用，确认 main、当前分支、PR 和 worktree 状态。
本机清单只用于现场检查，不把私有路径、主机状态和未发布工作写进公共文档。

## 查看现状

```sh
git status --short
git fetch --prune origin
git branch -a -vv
git worktree list
git log --graph --oneline --decorate --all -30
```

`fetch --prune` 更新远端跟踪引用，不删除本地分支，也不更新本地 main。
`[gone]` 只表示 upstream 已不存在，不能证明提交已合并。
PR 的 open/closed/merged 状态在 [GitHub PR 列表](https://github.com/grok-phantom/dotfiles/pulls)
核对；closed 不等于 merged。PR 合并后还要检查该分支是否继续新增了提交。

对某个候选分支检查：

```sh
git rev-list --left-right --count origin/main...feature-name
git log --oneline origin/main..feature-name
git cherry origin/main feature-name
git diff --stat origin/main...feature-name
git branch --merged origin/main
```

第一条左边为落后 main 的提交数，右边为分支独有的提交数。`git cherry` 的 `+`
表示有未找到等价补丁的提交，`-` 表示找到等价补丁。Squash/rebase 合并后原提交
可能不是 main 的祖先；多个提交被 squash 时也未必能逐个匹配 patch，所以同时
检查 PR 的 head/merge commit 和实际改动，不只依赖一个命令。

## 清理判断

| 情况 | 处理 |
| --- | --- |
| main 或默认分支 | 保留；工作区干净时用 `git merge --ff-only origin/main` 更新 |
| PR 已合并，所有分支提交已被包含或确认等价 | 本地与远端功能分支通常可以清理 |
| PR 仍 open，或存在未合并的独有改动 | 保留；有冲突时先协调，不当作废弃分支 |
| 已明确退役的未合并功能 | 先确认范围、保存可恢复备份并关闭 PR，再按核对过的提交删除分支 |
| 仅本地存在、没有 upstream | 先检查独有提交；需要保留时推送或另作可恢复备份 |
| upstream 已删除，但本地有新增提交 | 保留新增工作，不根据 `[gone]` 删除 |
| 分支仍被 worktree 使用 | 先检查该 worktree 的 tracked、untracked、ignored 文件和使用情况 |

需要退出某个已完成的 worktree 时，先在那个目录检查：

```sh
git status --short
git ls-files --others --ignored --exclude-standard
```

干净不代表没有正在运行的终端/agent。保存需要的文件、确认 worktree 已不再使用后，
回到主工作区再清理。以下是显式操作示例，不是自动清理脚本：

```sh
git worktree remove /path/to/completed-worktree
git switch main
git merge --ff-only origin/main
git branch -d feature-name
# 仅当远端分支仍存在、合并状态已确认且无需继续使用时：
git push origin --delete feature-name
```

若 `worktree remove` 或 `branch -d` 拒绝操作，检查原因和需要保存的内容。
不以 `--force`、`-D`、reset/clean 绕过检查。Squash 分支需要额外审查时保留即可。

## 开始文档或独立任务

工作区干净后，从已同步的 main 创建专用分支，避免把文档维护混入未合并功能：

```sh
git switch main
git merge --ff-only origin/main
git switch -c docs/topic-name
```

若现有工作尚未提交，使用独立 worktree，不自动 stash。文档描述该分支真实拥有的
功能；未合并功能用 PR 链接明确标注。分支切换只改变 source，不等于已应用到本机 home。
