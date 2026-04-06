import sys
from blog_bot import run_generate_review_flow

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def main():
    if len(sys.argv) < 2:
        print("사용법: python main.py 1 | 2 | 3")
        return

    mode = sys.argv[1]

    if mode == "1":
        run_generate_review_flow(post_count=9, account_index=1)
    elif mode == "2":
        run_generate_review_flow(post_count=20, account_index=2)
    elif mode == "3":
        run_generate_review_flow(post_count=20, account_index=1)
        run_generate_review_flow(post_count=20, account_index=2)
    else:
        print("잘못된 입력입니다. 1, 2, 3 중 하나를 사용하세요.")

if __name__ == "__main__":
    main()