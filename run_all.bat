@echo off
chcp 65001 > nul
title 启动 RAG 知识库问答系统

echo ===================================================
echo   正在启动 电商 RAG 企业级知识库问答系统...
echo ===================================================

echo [1/3] 正在后台启动后端服务 (FastAPI on Port 8000)...
start cmd /k "title RAG 后端服务 && .venv\Scripts\python -m uvicorn backend.app.main:app --port 8000 --reload"

echo [2/3] 正在后台启动前端开发服务 (Vite on Port 5173)...
start cmd /k "title RAG 前端开发 && cd frontend && npm run dev"

echo [3/3] 正在打开系统浏览器进行预览...
timeout /t 3 > nul
start http://localhost:5173/

echo ===================================================
echo   系统已成功启动！
echo   - 后端交互式 API 文档 (Swagger): http://localhost:8000/docs
echo   - 前端系统访问地址: http://localhost:5173/
echo   - 默认管理员用户名: admin
echo   - 默认管理员密码: 123456
echo.
echo   注意：演示期间请不要关闭弹出的两个命令行黑色窗口。
echo ===================================================
pause
