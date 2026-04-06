## batch 예시 파일
@echo off
chcp 65001 > nul
cd /d C:\your_project_path

if not exist logs mkdir logs

call .venv\Scripts\activate
python main.py 1 >> logs\account1.log 2>&1