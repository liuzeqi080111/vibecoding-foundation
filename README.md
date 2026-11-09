# Vibe Coding 项目底座

一个中文协作 skill，帮助 AI 在空项目或已有 Demo 上建立可持续开发的底座：保护现场，分轮确认产品、技术与里程碑。

适合需求散落在聊天中、先规划再开发、多人或多个 AI 接续的项目。不会强制重写框架，也不会把创建目录等同于完成产品。

## 安装与使用

将整个仓库复制或克隆到支持 SKILL.md 的工具的 skill 目录，并按工具的方式加载。例如 Codex 的默认目录：

```text
git clone https://github.com/liuzeqi080111/vibecoding-foundation.git ~/.codex/skills/vibecoding-foundation
```

自定义 CODEX_HOME 时使用对应的 skills 目录。已存在同名目录时先检查，不覆盖。

示例：

```text
使用 $vibecoding-foundation，检查当前项目，保留已有内容。
一次只问我一个小问题，先整理底座，不开始功能开发。
```

也可只请求一步：“沿用已有事实，讨论里程碑，整份确认后再保存”。

## 产物与边界

按需建立协作入口、唯一工程规则、已确认的产品事实、故事优先级、功能页面、技术方案、必要数据结构及可验收里程碑。已有同职责文件优先复用；最终目标与本轮目标分别保留。

- [SKILL.md](SKILL.md)：执行入口。
- [结构与规则](references/foundation.md)：目录、Git、迁移、发布。
- [分轮讨论](references/planning.md)：产品到里程碑。
- [验收交接](references/verification.md)：完成标准。
- [验证报告](VALIDATION.md)：实际检查和限制。

## 可选只读检查

需要 Python 3.10+；Git 元数据需要本机 Git：

```text
python scripts/audit_foundation.py /path/to/project
python -m unittest discover -s tests -v
```

不修改项目，不打印源码、环境变量、远端 URL 或密钥。只检查结构、本地链接和有限 Git 元数据，不代替需求审阅、业务测试或秘密扫描。文件路径仍可能含私人信息，分享报告前请检查。

本仓库不包含来源项目的源码、产品事实、私有路径或配置。公开便于获取；再分发许可尚未单独指定。
