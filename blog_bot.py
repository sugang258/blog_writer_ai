from pathlib import Path
import pyperclip
import requests
import re

from config import get_account_credentials, validate_required_env, MIN_PRICE, MAX_PRICE
from playwright.sync_api import sync_playwright
from ai_writer import generate_blog_review, save_review_result
from blog_writer import write_naver_blog

BASE_DIR = Path(__file__).resolve().parent

###################################################################
#################### 로그인 ########################################
###################################################################

## 계정에 따라 프로필 경로 변경
def get_user_data_dir(account_index: int) -> str:
    return str(BASE_DIR / f"browser_profile_acc{account_index}")

## 자동 로그인
## requset : NAVER_ID, NAVER_PW 
def login_brandconnect(page, naver_id, naver_pw):
    page.goto("https://nid.naver.com/nidlogin.login?url=https://brandconnect.naver.com")
    page.wait_for_timeout(2000)

    id_box = page.get_by_role("textbox", name="아이디 또는 전화번호")
    pw_box = page.get_by_role("textbox", name="비밀번호")

    id_box.click()
    id_box.press_sequentially(naver_id, delay=120)

    pw_box.click()
    pw_box.press_sequentially(naver_pw, delay=120)
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

    print("브랜드커넥트 로그인 시도 완료")


## 자동 로그인 세션 확인 -> 세션 없으면 로그인 진행
def ensure_brandconnect_login(page, naver_id, naver_pw, brand_connect_url):
    target_url = brand_connect_url

    page.goto(target_url)
    page.wait_for_timeout(3000)

    if "/affiliate/products" not in page.url:
        print("[INFO] 브랜드커넥트 세션 없음 → 로그인 진행")
        login_brandconnect(page, naver_id, naver_pw)
        page.goto(target_url)
        page.wait_for_timeout(3000)
    else:
        print("[INFO] 브랜드커넥트 로그인 세션 유지 중")


## 직접 로그인
def login_once_and_save_session(account_index=1):
    user_data_dir = get_user_data_dir(account_index)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False
        )

        try:
            page = context.new_page()
            page.goto("https://brandconnect.naver.com")

            print(f"현재 프로필 저장 경로: {user_data_dir}")
            print("브랜드커넥트와 블로그 로그인까지 직접 완료하세요.")
            print("완료 후 엔터를 누르세요.")
            input()

            page.wait_for_timeout(5000)

            cookies = context.cookies()
            print(f"저장된 쿠키 개수: {len(cookies)}")

        finally: 
            context.close()



## 직접 로그인 세션 확인
def check_brandconnect_login(account_index=1):
    user_data_dir = get_user_data_dir(account_index)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False
        )

        try:
            page = context.new_page()
            page.goto("https://brandconnect.naver.com")
            page.wait_for_timeout(5000)

            print(f"현재 프로필 저장 경로: {user_data_dir}")
            print(f"현재 URL: {page.url}")

            cookies = context.cookies()
            print(f"불러온 쿠키 개수: {len(cookies)}")

            input("브랜드커넥트 로그인 유지 여부를 확인한 뒤 엔터를 누르세요...")

        finally:
            context.close()



###########################################################################
########################## brand connect ##################################
###########################################################################

# 가격 문자열을 숫자로 바꾸는 함수
def parse_price_to_int(price_text: str) -> int | None:
    if not price_text:
        return None

    digits = re.sub(r"[^0-9]", "", price_text)
    if not digits:
        return None

    return int(digits)


## 브랜드 커넥트 링크 발급 (현재 사용 O)
def find_product_card_and_issue_link(page, max_scroll_tries=10):
    close_brandconnect_alert_if_exists(page)

    last_count = 0
    scroll_try = 0

    while scroll_try <= max_scroll_tries:
        cards = page.locator("div.ProductItem_root__UR21w")
        count = cards.count()

        print(f"[DEBUG] 카드 개수: {count}")
        print(f"[DEBUG] 가격 필터: {MIN_PRICE}원 ~ {MAX_PRICE}원")

        for i in range(count):
            card = cards.nth(i)

            try:
                product_name = card.locator(
                    ".ProductItem_title__I3r9G .ProductItem_ell__9YeTU"
                ).inner_text().strip()
            except Exception:
                product_name = "상품"
            
            detail_url = None
            try:
                detail_link = card.locator("a.ProductItem_link__Vm1vw").first
                detail_url = detail_link.get_attribute("href")

                if detail_url and detail_url.startswith("/"):
                    detail_url = "https://brandconnect.naver.com" + detail_url
            except Exception:
                detail_url = None

            # 가격 추출
            price_text = ""
            price_value = None
            try:
                price_text = card.locator("ins strong").last.inner_text().strip()
                price_value = parse_price_to_int(price_text)
            except Exception:
                try:
                    price_text = card.locator(".ProductItem_price__yTp_T strong").last.inner_text().strip()
                    price_value = parse_price_to_int(price_text)
                except Exception:
                    price_text = ""
                    price_value = None

            button = card.locator("button.ProductItem_btn__6S6T0")
            button_text = button.inner_text().strip()

            print(f"[DEBUG] card[{i}] 상품명: {product_name}")
            print(f"[DEBUG] card[{i}] 상세URL: {detail_url}")
            print(f"[DEBUG] card[{i}] 버튼텍스트: {button_text}")
            print(f"[DEBUG] card[{i}] 가격텍스트: {price_text}")
            print(f"[DEBUG] card[{i}] 가격값: {price_value}")

            # 가격 정보 없으면 스킵
            if price_value is None:
                print(f"[SKIP] 가격 추출 실패: {product_name}")
                continue

            # 최소/최대 금액 범위 밖이면 스킵
            if price_value < MIN_PRICE or price_value > MAX_PRICE:
                print(f"[SKIP] 가격 범위 밖: {product_name} / {price_value}원")
                continue

            # 이미 링크 발급된 상품은 건너뜀
            if "링크 복사" in button_text:
                print(f"[SKIP] 이미 링크 발급된 상품: {product_name}")
                continue

            # 아직 발급 전인 상품만 처리
            if "링크 발급" in button_text:
                close_brandconnect_alert_if_exists(page)

                button.scroll_into_view_if_needed()
                page.wait_for_timeout(500)

                with page.expect_response(
                    lambda r: "gw-brandconnect.naver.com/affiliate/command/affiliate-urls" in r.url
                ) as resp_info:
                    button.click()

                resp = resp_info.value
                data = resp.json()
                issued_link = data.get("url")

                if not issued_link:
                    raise Exception(f"url 필드 없음: {data}")

                page.wait_for_timeout(500)

                try:
                    page.get_by_role("button", name="확인").click(timeout=2000)
                except Exception:
                    pass

                pyperclip.copy(issued_link)

                return {
                    "product_name": product_name,
                    "affiliate_link": issued_link,
                    "detail_url": detail_url,
                    "price": price_value
                }

        # 현재 보이는 카드에서 조건 맞는 상품이 없으면 스크롤
        print("[DEBUG] 현재 화면에서 조건 맞는 상품 없음 → 아래로 스크롤")

        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(2000)

        new_count = page.locator("div.ProductItem_root__UR21w").count()
        print(f"[DEBUG] 스크롤 후 카드 개수: {new_count}")

        # 카드 수가 안 늘었으면 바닥까지 한 번 더
        if new_count == count:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2500)
            new_count = page.locator("div.ProductItem_root__UR21w").count()
            print(f"[DEBUG] 바닥 스크롤 후 카드 개수: {new_count}")

        # 더 이상 새 카드가 안 나오면 종료
        if new_count <= last_count and new_count == count:
            scroll_try += 1
            print(f"[DEBUG] 새 카드 없음. scroll_try={scroll_try}/{max_scroll_tries}")
        else:
            scroll_try = 0

        last_count = new_count

    print("[종료] 더 이상 조건에 맞는 상품이 없거나 새 카드가 로드되지 않음")
    return None


    

###################################################################
########################## main flow ###############################
###################################################################

## 블로그 작성
def run_generate_review_flow(post_count=3, account_index=1):
    validate_required_env(account_index)

    naver_id, naver_pw, category, brand_connect_url = get_account_credentials(account_index)
    user_data_dir = get_user_data_dir(account_index)
    success_count = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False
        )

        try:
            page = context.new_page()
            
            # 브랜드커넥트 로그인 보장
            ensure_brandconnect_login(page, naver_id, naver_pw, brand_connect_url)

            print(category)
            search_box = page.get_by_role("searchbox", name="상품명 또는 스토어명을 입력해 주세요")
            search_box.click()
            search_box.fill(category)
            search_box.press("Enter")
            page.wait_for_timeout(3000)


            while success_count < post_count:
                result = find_product_card_and_issue_link(page)

                if not result:
                    print("[종료] 더 이상 처리할 상품이 없습니다.")
                    break

                product_name = result["product_name"]
                affiliate_link = result["affiliate_link"]
                price_value = result.get("price")
                detail_url = result.get("detail_url")

                print("상품명:", product_name)
                print("링크:", affiliate_link)
                print("가격:", price_value)
                print("상세 URL:", detail_url)

                image_paths = {}

                if detail_url:
                    try:
                        image_paths = download_product_detail_images(context, detail_url, max_images=5)
                        for idx, path in image_paths.items():
                            print(f"상세 이미지 {idx} 저장 완료: {path}")
                    except Exception as e:
                        print("상세 이미지 다운로드 실패: ", e)

                parsed = generate_blog_review(
                    affiliate_url=affiliate_link,
                    product_name=product_name,
                    account_index=account_index
                )

                print("\n===== 제목 =====\n")
                print(parsed["title"])

                print("\n===== 본문 =====\n")
                print(parsed["body"])

                print("\n===== 해시태그 =====\n")
                print(parsed["hashtags"])

                saved_path = save_review_result(parsed)
                print(f"\n저장 완료: {saved_path}")

                full_post = f"{parsed['body']}\n\n{parsed['hashtags']}".strip()
                pyperclip.copy(full_post)
                print("본문+해시태그 클립보드 복사 완료")

                write_naver_blog(
                    context=context,
                    blog_id=naver_id,
                    title=parsed["title"],
                    body=parsed["body"],
                    hashtags=parsed["hashtags"],
                    image_paths=image_paths
                )

                # 성공 카운트 증가
                success_count += 1

                print(f"[완료] {success_count}/{post_count} - {product_name}")

                # 브랜드커넥트 페이지 다시 앞으로
                page.bring_to_front()
                page.wait_for_timeout(2000)
                close_brandconnect_alert_if_exists(page)

        finally:
            context.close()



###################################################################
######################## 이미지 처리 ###############################
###################################################################

# 상세 페이지 이미지 가져오기
def get_detail_image_urls(detail_page, max_images=5):
    imgs = detail_page.locator(".ProductDetail_img__TLpyf img")
    count = imgs.count()

    print(f"[DEBUG] 상세 이미지 개수: {count}")

    image_urls = []

    for i in range(min(count, max_images)):
        img = imgs.nth(i)
        image_url = img.get_attribute("src") or img.get_attribute("data-src")

        if image_url:
            image_urls.append(image_url)

    for idx, url in enumerate(image_urls, start=1):
        print(f"[DEBUG] image_url_{idx} = {url}")

    return image_urls


## 이미지 저장
def download_image_to_file(image_url, file_path):
    response = requests.get(image_url, timeout=15)
    response.raise_for_status()

    with open(file_path, "wb") as f:
        f.write(response.content)

    return str(file_path)


def download_product_detail_images(context, detail_url, max_images=5):
    detail_page = context.new_page()
    try:
        detail_page.goto(detail_url, wait_until="domcontentloaded")
        detail_page.wait_for_timeout(3000)

        image_urls = get_detail_image_urls(detail_page, max_images=max_images)

        images_dir = BASE_DIR / "images"
        images_dir.mkdir(exist_ok=True)

        image_paths = {}

        for idx, image_url in enumerate(image_urls, start=1):
            image_path = download_image_to_file(
                image_url,
                images_dir / f"product_detail_{idx}.jpg"
            )
            image_paths[idx] = image_path

        return image_paths

    finally:
        detail_page.close()



###################################################################
######################## alert 처리 ################################
###################################################################

## 브랜드 커넥터 alert 창 닫기
def close_brandconnect_alert_if_exists(page):
    try:
        alert = page.locator("div[role='alertdialog']")
        if alert.count() > 0 and alert.first.is_visible():
            print("[DEBUG] 브랜드커넥트 alertdialog 감지, 닫기 시도")

            # 확인 버튼 우선
            try:
                page.get_by_role("button", name="확인").click(timeout=2000)
                page.wait_for_timeout(1000)
                print("[DEBUG] alertdialog 확인 버튼 클릭")
                return
            except Exception:
                pass

            # 닫기 버튼 시도
            try:
                page.get_by_role("button", name="닫기").click(timeout=2000)
                page.wait_for_timeout(1000)
                print("[DEBUG] alertdialog 닫기 버튼 클릭")
                return
            except Exception:
                pass

            # ESC로 닫기 시도
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            print("[DEBUG] alertdialog ESC 닫기 시도")

    except Exception as e:
        print("[DEBUG] alertdialog 닫기 실패:", e)