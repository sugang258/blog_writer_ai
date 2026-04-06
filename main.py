from blog_bot import (
    login_once_and_save_session,
    check_brandconnect_login,
    issue_brandconnect_link,
    run_generate_review_flow,
    run_write_blog_from_latest_review,
)

mode = input("1: 1번 블로그 작성 > / 2: 2번 블로그 작성 > / 3: 모두 작성")

if mode == "1":
    run_generate_review_flow(post_count=1, account_index=1)
elif mode == "2":
    run_generate_review_flow(post_count=3, account_index=2)
elif mode == "3":
    run_generate_review_flow(post_count=3, account_index=1)
    run_generate_review_flow(post_count=3, account_index=2)
else:
    print("잘못된 입력입니다.")