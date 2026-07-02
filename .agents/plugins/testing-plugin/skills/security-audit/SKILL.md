---
name: security-audit
description: |
  检查代码文件或目录中的安全隐患，包括敏感数据泄露（密码、API 密钥）、SQL 注入漏洞风险、配置文件明文凭证以及其他安全隐患（如危险函数、跨域配置风险等）。
  当用户执行 /security-audit <file_or_dir_path> 或要求检查系统安全性时触发。
---

# Code Security Audit Skill (security-audit)

此技能用于对指定的代码文件或整个目录进行多维度的静态与语义安全漏洞审计，协助开发人员在编码阶段规避安全风险。

## 何时使用

1. 用户输入 `/security-audit <path>` 或请求“安全审查”、“检查代码漏洞”、“扫描密钥泄露”。
2. 代码上线、合并分支或发布前，作为安全红线检查。

## 审计与检查标准

1. **敏感信息泄露（Secrets Leak）**：
   * 严禁在代码、注释及提交的代码库中硬编码密码、Private Key、Bearer Token、JWT 密钥或云端 API Key（如阿里云/OpenAI 密钥等）。
2. **注入漏洞防范（SQL Injection & Command Injection）**：
   * 严禁使用字符串拼接（f-strings、`.format()` 或 `%`）的方式直接构造 SQL 语句并在数据库中执行。必须使用参数化查询。
   * 慎用 `os.system` 或未转义的 `subprocess` 以免发生系统命令注入漏洞。
3. **配置文件凭证规范**：
   * 检查 `.env` 等配置文件中是否存在显式提交的真实敏感参数，确保包含真实的密钥时仅放在本地不可提交的 `.env` 中，而非托管进代码库的配置文件。
4. **其他高风险函数与配置**：
   * 检查是否调用了 `eval()`、`exec()` 等任意代码执行风险函数。
   * 检查 FastAPI 或 Express 中的跨域配置，验证是否同时开启了全局通配 `allow_origins = ["*"]` 以及凭证携带 `allow_credentials = True`。

## 任务工作流

1. **执行安全审计脚本**：
   对目标路径进行静态分析，捕获已有的漏洞指标：
   ```bash
   .venv\Scripts\python .agents/plugins/testing-plugin/skills/security-audit/scripts/run_audit.py <target_path>
   ```
2. **语义化人工审计**：
   * 结合脚本分析结果，审阅对应段落的业务环境。判断被标记的项是真实的风险（如拼写 SQL 或硬编码密钥），还是合理的测试 Mock 数据。
3. **输出审计报告**：
   在项目根目录下生成 `security_report.md`。报告须包含以下部分：
   * **安全状况概要**：发现的问题总数，按严重程度（高/中/低）进行数量统计，以及总体健康评估。
   * **详细漏洞详情表**：列出每个问题的“文件路径”、“行号”、“漏洞类型”、“严重等级”、“风险描述”以及“对应的代码快照”。
   * **整改方案建议**：针对发现的每类隐患，提供符合安全标准的修复或重构示范代码（如将拼接 SQL 改为参数化，将硬编码密码改为从环境变量读取等）。
4. **呈现结果**：
   向用户输出审计核心结论并提供 [security_report.md](file:///d:/Dev/langchain/security_report.md) 的文件访问链接。
