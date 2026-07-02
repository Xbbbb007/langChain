---
name: git-save
description: |
  Saves the current workspace state by staging all changes, committing them, and pushing to the remote GitHub repository.
  Triggered when the user runs /git-save or requests to save progress using Git.
---

# Git Save Skill

此技能用于自动将当前工作区的代码修改使用 Git 提交并推送到 GitHub 远程仓库。

## 何时使用

* 用户显式键入 `/git-save`。
* 用户请求“备份”、“保存进度”、“提交并推送”或“上传到 GitHub”。

## 任务工作流

1. **定位本地辅助脚本**：
   * 本地脚本路径：`.agents/plugins/testing-plugin/skills/git-save/scripts/git-save.ps1`。

2. **执行保存与提交命令**：
   * 在当前工作区执行该脚本。
   * 如果用户提供了自定义提交信息（例如 `/git-save "initial commit"`），将其作为参数传入：
     ```powershell
     powershell -ExecutionPolicy Bypass -File .agents/plugins/testing-plugin/skills/git-save/scripts/git-save.ps1 "用户自定义提交信息"
     ```
   * 如果未提供，直接运行脚本，脚本会自动根据修改文件列表生成自动摘要：
     ```powershell
     powershell -ExecutionPolicy Bypass -File .agents/plugins/testing-plugin/skills/git-save/scripts/git-save.ps1
     ```

3. **呈现执行结果**：
   * 将 Git 命令行的阶段（Stage）、提交（Commit）、推送（Push）控制台日志反馈给用户。
