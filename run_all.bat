@echo off
title Start RAG Knowledge Base System

echo ===================================================
echo   Starting E-commerce RAG Enterprise Knowledge Base System...
echo ===================================================

echo [1/3] Starting backend service (FastAPI on Port 8080)...
start cmd /k "title RAG-Backend && .venv\Scripts\python -m uvicorn backend.app.main:app --port 8080 --reload"

echo [2/3] Starting frontend development service (Vite on Port 3000)...
start cmd /k "title RAG-Frontend && cd frontend && npm run dev"

echo [3/3] Opening system browser for preview...
timeout /t 3 > nul
start http://localhost:3000/

echo ===================================================
echo   System started successfully!
echo   - Backend Swagger API: http://localhost:8080/docs
echo   - Frontend Address: http://localhost:3000/
echo   - Default Admin Username: admin
echo   - Default Admin Password: 123456
echo.
echo   Note: Please DO NOT close the two spawned cmd windows during demo.
echo ===================================================
pause
