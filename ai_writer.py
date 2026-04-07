from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

OPENAI_MODEL = os.getenv("OPENAI_MODEL_DRAFT", "gpt-4o-mini")


def load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def clean_blog_text(text: str, affiliate_url: str = "") -> str:
    if not text:
        return ""

    # 라벨 제거
    text = text.replace("[제목]", "")
    text = text.replace("[본문]", "")
    text = text.replace("[해시태그]", "")

    # markdown bold 제거
    text = text.replace("**", "")

    # [구매링크](실제URL) -> 실제URL
    if affiliate_url:
        text = re.sub(rf'\[구매링크\]\({re.escape(affiliate_url)}\)', affiliate_url, text)
        text = re.sub(rf'\[{re.escape(affiliate_url)}\]\({re.escape(affiliate_url)}\)', affiliate_url, text)

    # 일반적인 [텍스트](url) -> url
    text = re.sub(r'\[[^\]]*\]\((https?://[^)]+)\)', r'\1', text)

    # "구매링크" 문자열이 남아 있으면 실제 url로 치환
    if affiliate_url:
        text = text.replace("구매링크", affiliate_url)

    # 줄 끝 공백 정리
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines).strip()

    return text


def count_purchase_links(body: str) -> int:
    pattern = r'👉 구매하러 가기\s*\nhttps?://\S+'
    return len(re.findall(pattern, body))


def insert_missing_purchase_link(body: str, affiliate_url: str) -> str:
    """
    구매 링크가 1개만 있을 때, 본문 중간에 링크 1개를 추가한다.
    """
    link_block = f"👉 구매하러 가기\n{affiliate_url}"

    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

    if len(paragraphs) < 4:
        # 문단이 너무 적으면 본문 앞쪽 적당한 위치에 삽입
        if paragraphs:
            paragraphs.insert(1, link_block)
        else:
            paragraphs = [link_block]
        return "\n\n".join(paragraphs).strip()

    # 중간쯤 삽입
    insert_index = max(2, len(paragraphs) // 2)
    paragraphs.insert(insert_index, link_block)

    return "\n\n".join(paragraphs).strip()


def force_fix_purchase_links(body: str, affiliate_url: str) -> str:
    link_block = f"👉 구매하러 가기\n{affiliate_url}"

    # 구매링크 문자열/마크다운 정리
    body = clean_blog_text(body, affiliate_url)

    # 링크 블록이 아예 없으면 2개 추가
    link_count = count_purchase_links(body)

    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

    if link_count == 0:
        if len(paragraphs) >= 4:
            paragraphs.insert(max(2, len(paragraphs)//2), link_block)
            paragraphs.append(link_block)
        else:
            paragraphs.append(link_block)
            paragraphs.append(link_block)

    elif link_count == 1:
        paragraphs.insert(max(2, len(paragraphs)//2), link_block)

    body = "\n\n".join(paragraphs).strip()

    # 2개 초과면 처음 2개만 남기고 나머지 제거까지 하고 싶으면 추가 가능
    return body


def normalize_image_markers(text: str) -> str:
    if not text:
        return ""

    # 대괄호 없는 것도 대괄호 형식으로 보정
    text = re.sub(r'(?<!\[)이미지\s*1(?!\])', '[이미지1]', text)
    text = re.sub(r'(?<!\[)이미지\s*2(?!\])', '[이미지2]', text)
    text = re.sub(r'(?<!\[)이미지\s*3(?!\])', '[이미지3]', text)
    text = re.sub(r'(?<!\[)이미지\s*4(?!\])', '[이미지4]', text)
    text = re.sub(r'(?<!\[)이미지\s*5(?!\])', '[이미지5]', text)

    # 공백 섞인 대괄호 형태도 정규화
    text = re.sub(r'\[\s*이미지\s*1\s*\]', '[이미지1]', text)
    text = re.sub(r'\[\s*이미지\s*2\s*\]', '[이미지2]', text)
    text = re.sub(r'\[\s*이미지\s*3\s*\]', '[이미지3]', text)
    text = re.sub(r'\[\s*이미지\s*4\s*\]', '[이미지4]', text)
    text = re.sub(r'\[\s*이미지\s*5\s*\]', '[이미지5]', text)

    return text


def split_review_text(text: str, affiliate_url: str = "") -> dict:
    text = text.strip()

    title = ""
    body = ""
    hashtags = ""

    if "[제목]" in text and "[본문]" in text and "[해시태그]" in text:
        try:
            title = text.split("[제목]", 1)[1].split("[본문]", 1)[0].strip()
            body = text.split("[본문]", 1)[1].split("[해시태그]", 1)[0].strip()
            hashtags = text.split("[해시태그]", 1)[1].strip()

            title = clean_blog_text(title, affiliate_url)
            body = clean_blog_text(body, affiliate_url)
            hashtags = clean_blog_text(hashtags, affiliate_url)

            return {
                "title": title,
                "body": body,
                "hashtags": hashtags
            }
        except Exception as e:
            raise ValueError(f"리뷰 텍스트 라벨 파싱 실패: {e}")

    # fallback
    lines = [line.rstrip() for line in text.splitlines()]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return {
            "title": "",
            "body": "",
            "hashtags": ""
        }

    title = clean_blog_text(lines[0].strip())

    hashtag_index = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("#"):
            hashtag_index = i
            break

    hashtags = ""
    body_lines = lines[1:]

    if hashtag_index != -1:
        hashtags = clean_blog_text(lines[hashtag_index].strip())
        body_lines = lines[1:hashtag_index]

    body = clean_blog_text("\n".join(body_lines).strip())

    return {
        "title": title,
        "body": body,
        "hashtags": hashtags
    }


def generate_blog_review(affiliate_url, product_name, account_index) -> dict:
    prompt_filename = f"blog_review_prompt_{account_index}.txt"
    system_prompt = load_prompt(prompt_filename)

    user_prompt = f"""
상품명: {product_name}

구매링크: {affiliate_url}
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_text = response.output_text.strip()
    parsed = split_review_text(raw_text, affiliate_url)

    parsed["title"] = clean_blog_text(parsed["title"], affiliate_url)
    parsed["body"] = force_fix_purchase_links(parsed["body"], affiliate_url)
    parsed["body"] = normalize_image_markers(parsed["body"])
    parsed["hashtags"] = clean_blog_text(parsed["hashtags"], affiliate_url)

    return parsed


def save_review_result(parsed: dict, filename: str = "latest_review.txt"):
    output_path = OUTPUT_DIR / filename

    content = (
        f"[제목]\n{parsed['title']}\n\n"
        f"[본문]\n{parsed['body']}\n\n"
        f"[해시태그]\n{parsed['hashtags']}\n"
    )

    output_path.write_text(content, encoding="utf-8")
    return str(output_path)