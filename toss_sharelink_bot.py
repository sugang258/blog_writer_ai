from pathlib import Path
from PIL import Image
import re
import time
import random
import requests

from playwright.sync_api import sync_playwright

from config import get_account_credentials, validate_required_env
from ai_writer import generate_blog_review, save_review_result
from blog_writer import write_naver_blog
from blog_bot import get_user_data_dir
from blog_writer import ensure_blog_login


BASE_DIR = Path(__file__).resolve().parent
(BASE_DIR / "images").mkdir(exist_ok=True)


def extract_main_image_from_sharelink(page, share_link):

    page.goto(share_link, wait_until="domcontentloaded")

    page.wait_for_timeout(3000)

    try:
        image_url = page.locator(
            "meta[property='og:image']"
        ).get_attribute("content")

        if image_url:
            return image_url

    except:
        pass

    # fallback JSON 파싱 방식
    html = page.content()

    match = re.search(
        r'"mainImageUrls":\[(.*?)\]',
        html
    )

    if match:
        raw = match.group(1)
        img_url = raw.replace('"', '').split(",")[0]
        return img_url

    return None


def download_image(img_url, filename="toss_image.jpg"):
    res = requests.get(img_url, timeout=15)
    res.raise_for_status()

    file_path = Path(filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(res.content)

    resize_image(file_path, max_size=500)

    return str(file_path)


def resize_image(image_path, max_size=500):
    image_path = Path(image_path)

    with Image.open(image_path) as img:
        # JPG 저장 대비
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        original_width, original_height = img.size

        # 이미 긴 쪽이 500 이하이면 그대로 저장
        if max(original_width, original_height) <= max_size:
            print(f"[INFO] 리사이즈 생략: {original_width}x{original_height}")
            return

        ratio = max_size / max(original_width, original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        resized = img.resize((new_width, new_height), Image.LANCZOS)
        resized.save(image_path, quality=90, optimize=True)

        print(
            f"[INFO] 이미지 리사이즈 완료: "
            f"{original_width}x{original_height} -> {new_width}x{new_height}"
        )


def extract_title_from_html(html: str) -> str:
    if not html:
        return ""

    patterns = [
        r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*name=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
        r'<title>(.*?)</title>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()
            if title:
                return title

    return ""


def clean_product_name(title: str) -> str:
    if not title:
        return "추천 상품"

    title = re.sub(r"\s+", " ", title).strip()

    remove_keywords = [
        "토스",
        "Toss",
        "토스쇼핑",
        "쇼핑",
        "공식몰",
        "스마트스토어",
        "네이버 스마트스토어",
        "브랜드관",
        "스토어",
    ]

    for keyword in remove_keywords:
        title = title.replace(keyword, "")

    title = re.sub(r"[|\-–—/]+.*$", "", title).strip()
    title = re.sub(r"\[[^\]]+\]", "", title).strip()
    title = re.sub(r"\([^)]+\)", "", title).strip()
    title = re.sub(r"\s+", " ", title).strip()

    if len(title) < 2:
        return "추천 상품"

    return title


def resolve_product_name_from_sharelink(share_link: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    try:
        resp = requests.get(
            share_link,
            headers=headers,
            timeout=15,
            allow_redirects=True,
        )
        resp.raise_for_status()

        html = resp.text
        title = extract_title_from_html(html)
        product_name = clean_product_name(title)

        print(f"[INFO] 링크에서 추정한 상품명: {product_name}")
        return product_name

    except Exception as e:
        print(f"[WARN] 상품명 추출 실패: {e}")
        return "추천 상품"
    

def parse_toss_clipboard_block(block: str):
    """
    토스 쉐어링크 복사 텍스트에서
    상품명 + 링크 추출
    """

    lines = [line.strip() for line in block.split("\n") if line.strip()]

    if len(lines) < 2:
        return None, None

    product_name = None
    link = None

    for line in lines:
        if line.startswith("http"):
            link = line
        elif "수수료" in line:
            continue
        else:
            product_name = line

    return product_name, link


def input_share_links():
    print("토스 쉐어링크를 한 줄씩 입력하세요.")
    print("입력 완료 후 빈 줄(엔터)만 입력하면 시작됩니다.")
    print("예시:")
    print("https://example.com/aaa")
    print("https://example.com/bbb")
    print("")

    links = []

    while True:
        line = input().strip()

        if not line:
            break

        if not line.startswith("http"):
            print(f"[SKIP] URL 형식이 아닙니다: {line}")
            continue

        links.append(line)

    unique_links = []
    seen = set()

    for link in links:
        if link not in seen:
            unique_links.append(link)
            seen.add(link)

    return unique_links


def input_toss_blocks():
    print("토스 쉐어링크 복사 내용을 그대로 붙여넣으세요.")
    print("입력 완료 후 빈 줄(엔터) 입력하면 시작합니다.\n")

    blocks = []
    current_block = []

    while True:
        line = input()

        if line.strip() == "":
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            else:
                break
        else:
            current_block.append(line)

    parsed_list = []

    for block in blocks:
        product_name, link = parse_toss_clipboard_block(block)

        if product_name and link:
            parsed_list.append((product_name, link))

    return parsed_list


def run_toss_sharelink_flow(account_index=1, delay_min=20, delay_max=45):

    validate_required_env(account_index)

    naver_id, naver_pw, category, brand_connect_url = get_account_credentials(account_index)
    user_data_dir = get_user_data_dir(account_index)

    pairs = input_toss_blocks()

    if not pairs:
        print("입력된 링크가 없습니다.")
        return

    print(f"[INFO] 총 {len(pairs)}개 링크 발행 시작")

    with sync_playwright() as p:

        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False
        )

        try:

            ensure_blog_login(context, naver_id, naver_pw)

            success_count = 0

            for idx, (product_name, share_link) in enumerate(pairs, start=1):

                print(f"\n===== {idx}/{len(pairs)} 처리 시작 =====")
                print(f"상품명: {product_name}")
                print(f"링크: {share_link}")

                try:

                    page = context.new_page()

                    img_url = extract_main_image_from_sharelink(
                        page,
                        share_link
                    )

                    image_path = None

                    if img_url:
                        print("대표 이미지 발견:", img_url)

                        image_path = download_image(
                            img_url,
                            filename=BASE_DIR / "images" / f"toss_img_{idx}.jpg"
                        )

                    page.close()

                    parsed = generate_blog_review(
                        affiliate_url=share_link,
                        product_name=product_name,
                        urlType="toss",
                        account_index=account_index
                    )

                    print("\n===== 제목 =====\n")
                    print(parsed["title"])

                    print("\n===== 본문 =====\n")
                    print(parsed["body"])

                    print("\n===== 해시태그 =====\n")
                    print(parsed["hashtags"])

                    save_name = f"toss_review_{idx}.txt"
                    saved_path = save_review_result(parsed, filename=save_name)

                    print(f"\n저장 완료: {saved_path}")

                    write_naver_blog(
                        context=context,
                        blog_id=naver_id,
                        title=parsed["title"],
                        body=parsed["body"],
                        hashtags=parsed["hashtags"],
                        image_paths={
                            1: image_path
                        } if image_path else {},
                        auto_publish=True
                    )

                    success_count += 1

                    print(f"[완료] {success_count}/{len(pairs)} 발행 성공")

                except Exception as e:

                    print(f"[ERROR] 발행 실패: {e}")

                if idx < len(pairs):

                    wait_sec = random.randint(delay_min, delay_max)

                    print(f"[INFO] 다음 발행 전 {wait_sec}초 대기")

                    time.sleep(wait_sec)

            print(f"\n[종료] 총 {success_count}/{len(pairs)}개 발행 완료")

        finally:

            context.close()


