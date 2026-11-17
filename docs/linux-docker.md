# Ubuntu Docker 安装验证

在专用 Ubuntu 24.04 / 26.04 amd64 容器中验证从空环境安装到终端运行。
使用普通测试用户和独立 HOME，原始日志留在容器外；不操作宿主用户配置。
服务器与桌面选择见 [Linux 部署范围](linux.md#部署范围)。

## 创建隔离环境

以下命令在有 Docker 权限的 Linux 测试机执行。源码使用公开仓库的独立 checkout。
不要挂载真实 HOME、SSH 密钥、agent 凭据或 Docker socket，不使用 privileged。

```sh
# Ubuntu 26.04 amd64 manifest。
image=ubuntu@sha256:0d5255be560e2d2ddcfbfda88549e9e815ef29e7cd7fc62183d5709e6e2963c6
# Ubuntu 24.04 的已验证镜像；同样配合 --platform linux/amd64 使用。
# image=ubuntu@sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8
container=dotfiles-linux-validation
artifacts="$(mktemp -d)"
git rev-parse HEAD > "$artifacts/source-commit.txt"
git archive HEAD > "$artifacts/source.tar"
docker pull --platform linux/amd64 "$image"
docker run -d --name "$container" --platform linux/amd64 \
  --cpus 2 --memory 4g --memory-swap 4g --pids-limit 512 \
  "$image" sleep infinity
docker cp "$artifacts/source.tar" "$container:/tmp/source.tar"
docker exec "$container" sh -c 'mkdir /src && tar -xf /tmp/source.tar -C /src'
docker exec "$container" bash /src/tests/linux-container-bootstrap.sh \
  > "$artifacts/bootstrap.log" 2>&1
docker exec -u tester -e HOME=/home/tester -e TERM=xterm-256color "$container" \
  python3 /home/tester/repo/tests/check_linux_container.py \
  > "$artifacts/acceptance.log" 2>&1
```

镜像 digest 固定；Ubuntu apt 索引和包版本随安全更新变化，脚本记录实际安装版本。
bootstrap 使用 `tests/ci-tools.json` 中的 chezmoi 版本与 SHA-256。
它只在容器内安装基础依赖，创建测试用户和免密 sudo；不修改登录宿主。
Ubuntu 精简镜像默认排除文档，bootstrap 单独保留 `/usr/share/doc/fzf/*`，
避免把 fzf 的 Vim 集成也删掉。
验证脚本在隔离副本中创建合成 Git 提交，源提交以 `source-commit.txt` 为准。
未提交修改须另外导出到隔离副本，并记录 diff，不能用 HEAD 的通过结果代替。

需要代理时，在 `docker run` 中显式传入 `http_proxy`、`https_proxy` 和 `no_proxy`。
若代理仅监听 Linux 宿主回环地址，可为该测试容器加 `--network host`。
只有此时容器才能通过 `127.0.0.1` 访问宿主代理。不要改变生产代理监听或防火墙。
bootstrap 会把显式代理写进容器 apt 配置，使后续 sudo apt 请求也走相同代理。

Docker daemon 拉镜像与容器内 apt/curl 是两条独立链路。
容器环境变量不会影响 `docker pull`。镜像也应在目标测试机经代理获取；
若采用 registry 下载后 `docker load`，需校验 manifest、config 和每个 layer 的 digest。
不要为了容器测试修改生产 daemon 或改从另一台开发机拉取。

## 执行内容

1. 从空镜像安装基础命令、测试用 jq/rsync 和校验过的 chezmoi。
2. 普通用户运行离线测试，再通过真实 `chezmoi init` 生成配置。
3. core plan/apply/verify 执行两次，确认没有生成 full 的工具配置。
4. 通过 `scripts/software` 计划、安装、验证完整 apt 清单。
5. 记录 apt full 预检：24.04 的 fzf 过旧；26.04 应直接通过。
6. full 下载并校验锁定插件，plan/apply/verify 执行两次。
7. apt 路线仅在 fzf 过旧时补充固定版本；Yazi/ya 使用固定官方发布包并验证 SHA-256。
   brew 路线使用预先安装的 Homebrew，执行现有软件清单及重复安装，再重新应用配置。
8. 运行 Vim Python/Jedi/fzf/Tagbar/ALE、Tmux 配置和会话检查。
9. 在 Tmux 伪终端中运行 Zsh，检查 p10k 与 Git 补全；运行 Yazi，验证 smart-enter
   进入目录、退出并写出实际目录。
10. brew 路线检查登录 shell 的可执行文件解析、`/usr/bin` 工具仍可运行、Vim/Tmux 的动态库，
    并对 Vim/Tmux/fzf/Yazi 执行 `brew linkage --test`。

首次交互启动 p10k 会按锁定插件中的 `gitstatus/install.info` 下载并校验 gitstatusd。
这一步需要网络；普通离线 runtime suite 会关闭它，不能替代此处的伪终端检查。

fzf/Yazi 是测试补充依赖，不会写进生产 apt 清单，也不代表 apt 已提供这些版本。
具体版本、官方发布 URL 和 digest 保存在 `tests/check_linux_container.py` 中。
默认走 apt 路线。`--manager brew` 要求先在另一个空容器中按官方说明安装 Homebrew，
并通过其 `shellenv` 设置 PATH。基础编译依赖由 apt 提供：
`build-essential procps curl file git`。使用普通测试用户和默认前缀
`/home/linuxbrew/.linuxbrew`，记录官方安装器提交及 SHA-256。
然后用登录 shell 执行 `python3 /home/tester/repo/tests/check_linux_container.py --manager brew`。
该路线仍先安装 apt 清单，覆盖重复软件并存的情况；关闭 Herdr/Memex，不验证其服务或插件。

## 取证与清理

无论命令成功或失败，先取出日志再清理。失败时保留容器便于重试诊断；完整复测另建新容器，
不要将已装依赖或已应用配置的 HOME 算作空环境。

```sh
docker cp "$container:/home/tester/evidence" "$artifacts/evidence"
docker inspect "$container" > "$artifacts/container.json"
# 确认日志已保存后，只清理本次测试容器：
docker rm -f "$container"
```

离线报告中的通过、跳过和运行环境，与 `acceptance.log` 中的安装和运行结果分开看。
日志和容器状态可能包含本机网络信息，不提交到公开仓库。

容器不覆盖 systemd 服务、真实 SSH 认证、Orca 终端、手机字体和键盘、剪贴板、
图片预览、桌面文件打开、音视频、GPU 或重启恢复。这些仍需目标设备验收。
