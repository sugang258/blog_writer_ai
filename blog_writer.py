from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent


########################################################
################## 로그인 ###############################
########################################################

## 자동로그인
## NAVER_ID , NAVER_PW
def login_naver_blog(context, blog_id, blog_pw):
    page = context.new_page()
    try:
        page.goto("https://nid.naver.com/nidlogin.login?mode=form&url=https://www.naver.com/")
        page.wait_for_timeout(2000)

        id_box = page.get_by_role("textbox", name="아이디 또는 전화번호")
        pw_box = page.get_by_role("textbox", name="비밀번호")

        id_box.click()
        id_box.press_sequentially(blog_id, delay=120)

        pw_box.click()
        pw_box.press_sequentially(blog_pw, delay=120)
        page.get_by_role("button", name="로그인", exact=True).click()
        page.wait_for_timeout(3000)


        # 자동입력방지 / 추가 인증 등으로 로그인 페이지에 남아 있으면 수동 처리 대기
        while "nid.naver.com" in page.url:
            print("[INFO] 자동입력방지 문자 또는 추가 인증이 필요할 수 있습니다.")
            print("[INFO] 브라우저에서 직접 처리한 뒤 엔터를 누르세요.")
            input()

            page.wait_for_timeout(3000)

            if "nid.naver.com" in page.url:
                print("[WARN] 아직 로그인 페이지에 있습니다. 다시 확인해주세요.")
            else:
                break

        print("네이버 블로그 로그인 시도 완료")
    finally:
        page.close()

## 자동 로그인 세션 확인 > 없으면 로그인 진행
def ensure_blog_login(context, blog_id, blog_pw):
    page = context.new_page()
    BLOG_WRITE_URL = f"https://blog.naver.com/{blog_id}?Redirect=Write&categoryNo="
    try:
        page.goto(BLOG_WRITE_URL)
        page.wait_for_timeout(3000)

        if "nid.naver.com" in page.url:
            print("[INFO] 블로그 세션 없음 → 로그인 진행")
            page.close()
            login_naver_blog(context, blog_id, blog_pw)
        else:
            print("[INFO] 블로그 로그인 세션 유지 중")
    finally:
        try:
            page.close()
        except Exception:
            pass



########################################################
################# helper ###############################
########################################################

## 본문 나누는 함수
def split_body_for_mid_images(body: str):
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

    p1 = paragraphs[0] if len(paragraphs) >= 1 else ""
    p2 = paragraphs[1] if len(paragraphs) >= 2 else ""
    p3 = paragraphs[2] if len(paragraphs) >= 3 else ""
    rest = "\n\n".join(paragraphs[3:]).strip() if len(paragraphs) >= 4 else ""

    return p1, p2, p3, rest


## 이미지 업로드
def upload_image(page, frame, image_path):
    if not image_path:
        return

    with page.expect_file_chooser() as fc_info:
        frame.get_by_role("button", name="사진 추가").click(timeout=5000)

    file_chooser = fc_info.value
    file_chooser.set_files(image_path)

    print("이미지 업로드 완료")
    page.wait_for_timeout(3000)


def split_text_keep_links(text: str):
    pattern = r'👉 구매하러 가기\s*\nhttps?://\S+'
    parts = re.split(f'({pattern})', text)

    chunks = []
    for part in parts:
        if not part or not part.strip():
            continue

        part = part.strip()

        if re.fullmatch(pattern, part):
            chunks.append(("link", part))
        else:
            chunks.append(("text", part))

    return chunks



## 링크 입력 후 5초 대기
def type_text_with_link_pause(page, text: str, pause_ms: int = 3000):
    chunks = split_text_keep_links(text)

    for idx, (chunk_type, chunk_text) in enumerate(chunks):
        page.keyboard.type(chunk_text)
        page.keyboard.press("Enter")


        if chunk_type == "link":
            print(f"링크 입력 완료")
            page.wait_for_timeout(pause_ms)

        if idx != len(chunks) - 1:
            page.keyboard.press("Enter")
            page.keyboard.press("Enter")




###################################################
############### 블로그 작성 #########################
###################################################

## 블로그 작성
def write_naver_blog(context, blog_id, title, body, hashtags, image_path=None, auto_publish=True):
    page = context.new_page()
    BLOG_WRITE_URL = f"https://blog.naver.com/{blog_id}?Redirect=Write&categoryNo="

    try:
        page.goto(BLOG_WRITE_URL)
        page.wait_for_timeout(3000)

        print("블로그 글쓰기 페이지 진입 완료")

        frame = page.frame_locator("iframe[name='mainFrame']")

        # 팝업 닫기 / 이어쓰기 취소 처리
        for btn_name in ["취소", "닫기"]:
            try:
                frame.get_by_role("button", name=btn_name, exact=True).click(timeout=2000)
                page.wait_for_timeout(1000)
                print(f"[frame] {btn_name} 버튼 클릭")
            except Exception:
                try:
                    page.get_by_role("button", name=btn_name, exact=True).click(timeout=2000)
                    page.wait_for_timeout(1000)
                    print(f"[page] {btn_name} 버튼 클릭")
                except Exception:
                    pass

        # 제목 입력
        frame.get_by_text("제목", exact=True).click(timeout=5000)
        page.wait_for_timeout(1000)
        page.keyboard.type(title)
        print("제목 입력 완료")

        page.wait_for_timeout(1000)

        # 본문 입력
        frame.get_by_text("글감과 함께 나의 일상을 기록해보세요!").click(timeout=5000)
        page.wait_for_timeout(1000)

        formatted_body = re.sub(
            r'\n*👉 구매하러 가기\s*\n(https?://\S+)\n*',
            r'\n\n👉 구매하러 가기\n\1\n\n',
            body
        ).strip()

        p1, p2, p3, rest_body = split_body_for_mid_images(formatted_body)

        # 1번째 문단
        if p1:
            type_text_with_link_pause(page, p1, pause_ms=3000)
            print("1번째 문단 입력 완료")
            page.keyboard.press("Enter")
            page.keyboard.press("Enter")

        # 2번째 문단
        if p2:
            type_text_with_link_pause(page, p2, pause_ms=3000)
            print("2번째 문단 입력 완료")
            page.keyboard.press("Enter")
            page.keyboard.press("Enter")

        # 첫 번째 이미지 (2번째 문단 뒤)
        if image_path:
            upload_image(page, frame, image_path)
            page.keyboard.press("Enter")
            page.keyboard.press("Enter")

        # 3번째 문단
        if p3:
            type_text_with_link_pause(page, p3, pause_ms=3000)
            print("3번째 문단 입력 완료")
            page.keyboard.press("Enter")
            page.keyboard.press("Enter")

        # 두 번째 이미지 (3번째 문단 뒤)
        if image_path:
            upload_image(page, frame, image_path)
            page.keyboard.press("Enter")
            page.keyboard.press("Enter")

        # 나머지 본문
        if rest_body:
            type_text_with_link_pause(page, rest_body, pause_ms=3000)
            print("나머지 본문 입력 완료")

        # 해시태그
        page.keyboard.press("Enter")
        page.keyboard.press("Enter")
        page.keyboard.type(hashtags)
        print("해시태그 입력 완료")\

        page.wait_for_timeout(1500)

        if auto_publish:
            # 1차 발행 버튼
            frame.get_by_role("button", name="발행").click(timeout=5000)
            print("1차 발행 버튼 클릭")
            page.wait_for_timeout(2000)

            # 2차 최종 발행 버튼
            frame.get_by_test_id("seOnePublishBtn").click(timeout=5000)
            print("최종 발행 버튼 클릭")
            page.wait_for_timeout(5000)

            print("발행 완료")
        else:
            print("auto_publish=False, 발행은 하지 않음")
                

    finally:
        page.close()