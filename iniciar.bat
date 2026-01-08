@echo off
echo ========================================
echo    LISTA TRF - Analisador de Listas
echo ========================================
echo.

cd /d "%~dp0"

echo Verificando dependencias...
pip install -r requirements.txt -q

echo.
echo Iniciando servidor na porta 5002...
echo Acesse: http://127.0.0.1:5002
echo.
echo Pressione Ctrl+C para encerrar.
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 5002 --reload
