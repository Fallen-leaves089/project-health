# 参与贡献

[中文](CONTRIBUTING.md) | [English](CONTRIBUTING.en.md)

感谢你愿意改进这个技能包。它面向的是“真实项目体检”，所以最有价值的贡献通常不是多一个漂亮的清单，而是：

- 一条可复现的环境坑（命令、报错、绕法、验证结果）
- 一个能证明守护脚本有效的反例
- 一个让检查更少假阴性的流程改进

## 提交 Issue

标题建议加前缀：

- `[Bug]`：技能流程、脚本或文档有错误
- `[Pitfall]`：新的 Windows / 跨平台环境坑
- `[Feature]`：新的检查维度或报告能力
- `[Security]`：疑似脱敏遗漏（不要在 Issue 里粘贴敏感值）

Issue 里请写清：

1. 触发场景
2. 实际行为
3. 期望行为
4. 最小复现命令或步骤
5. 环境（OS、PowerShell 版本、相关工具版本）

## 提交 Pull Request

- 改动尽量小，一次只解决一个问题。
- 修改行为时同步更新 `CHANGELOG.md`。
- 新增环境坑时，写清“坑 / 绕法 / 验证方式”，不要只写结论。
- 新增脚本时，必须自带正反例验证；只跑正例的守护不接受。
- 提交前运行：

  ```bash
  python -B -m unittest discover -s tests -p "test_*.py"
  python scripts/verify_package.py
  ```

- Windows 也可以运行：

  ```powershell
  python -B -m unittest discover -s tests -p "test_*.py"
  python scripts\verify_package.py
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-package.ps1
  ```

- 不要在仓库里放个人绝对路径、真实用户名、项目/客户名、域名、内网 IP、密钥或未脱敏日志。
- 中文文档统一 UTF-8 无 BOM。

## 许可与贡献授权

本项目采用 PolyForm Noncommercial License 1.0.0。提交贡献即表示你同意：

- 你的贡献按同一许可提供，允许非商业使用、修改和分发；
- 你保留自己贡献的版权，但不因此获得项目的商业授权；
- 商业授权仍由项目作者与使用方单独协商，见 `COMMERCIAL.md`。

如果你不希望按上述方式授权，请不要提交 PR，可以先开 Issue 讨论。

## 行为准则

- 对事不对人，聚焦可复现的事实。
- 不公开他人的密钥、客户数据或未脱敏日志。
- 不把“我这里能跑”当成“所有人都能跑”；附上环境和命令。
