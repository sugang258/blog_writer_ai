@echo off
chcp 65001 > nul
cd /d C:\naver_blog_bot

if not exist logs mkdir logs

call .venv\Scripts\activate
python main.py 2 >> logs\account2.log 2>&1