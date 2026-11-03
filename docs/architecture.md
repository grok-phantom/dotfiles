# 架构与维护

本仓库管理用户环境。配置、软件安装和本机运行状态分别维护。

| 范围 | 入口或位置 | 职责 |
| --- | --- | --- |
| 配置正本 | `home/` | chezmoi 目标、模板、用户命令；保留平台与 profile 守卫 |
| 配置更新 | `scripts/dotfiles` | 提交快照、plan/apply/verify、漂移和过期计划检查 |
| 软件维护 | `scripts/software` | packages、Miniforge、Herdr 插件；默认 plan，写入须显式执行 |
| 共用实现 | `scripts/dotfiles_lib/` | 子进程与诊断、平台检查、Herdr 安装验证和 Quicklook 补丁 |
| 手动操作 | `scripts/manual/` | 系统偏好、agent 集成；旧插件脚本转发到软件入口 |
| 本机状态 | 目标机器 | 身份、凭据、主机清单、会话、日志、索引和插件注册表 |

配置 apply 不调用包管理器、插件安装器或重启服务。
Herdr 先应用本地插件配置，再预检并显式安装，最后只读验证。
外部归档、Miniforge、Herdr 各保留适合其安装器的锁格式。
Homebrew/apt 清单只选择软件，不保证相同版本。

## 共享配置的所有权

`modify_` 模板只修改明确归仓库管理的字段，保留其他字段。
无变化时保留原文；发生变化时允许格式化。

Herdr 的快捷键与速查表共用 `.chezmoidata/herdr.json`。
当前 `bindings` 负责新增和更新；`retired_commands` 只列曾由仓库创建、需要删除的旧 command。
删除或重命名 action 必须同步维护退役清单，并测试旧配置迁移。
同一快捷键被用户命令占用时停止，不覆盖。

Claude/Codex hooks 以精确 command 识别托管条目。
启用或关闭集成时，只移除自己的 hook，保留同组的其他 hook 与 matcher。
由 Herdr 官方安装器维护的 hooks 不归 chezmoi 接管，卸载仍走其官方入口。

## 本机选择与恢复

保留 core/full 两档；Herdr 和 cmux 使用少量独立开关，默认兼容已有 full 主机。
开关定义、初始化保留和关闭行为见[本机配置](configuration.md)。
软件安装失败会保留已完成的步骤，不声称事务回滚。
Herdr 重试先运行 plan，再 install；版本匹配的插件会跳过。
发现本地文件差异、注册冲突或未知补丁字节时先检查差异，不自动覆盖。

## 维护入口的验证

提交前运行 `./scripts/test all`。新增维护行为应使用临时目录和替身命令验证失败路径。
修改模板需验证已有配置保留、重复应用和关闭或退役行为。
本机 verify 与 GUI、远端验收分开记录；具体操作见[终端说明](terminals.md#herdr)。
