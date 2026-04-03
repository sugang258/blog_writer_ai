from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL_DRAFT = os.getenv("OPENAI_MODEL_DRAFT", "gpt-4o-mini").strip()

MIN_PRICE = int(os.getenv("MIN_PRICE", "0"))
MAX_PRICE = int(os.getenv("MAX_PRICE", "99999999"))


def get_account_credentials(account_index: int):
    naver_id = os.getenv(f"NAVER_ID_{account_index}", "").strip()
    naver_pw = os.getenv(f"NAVER_PW_{account_index}", "").strip()
    category = os.getenv(f"CATEGORY_{account_index}", "").strip()
    brand_connect_url = os.getenv(f"BRAND_CONNECT_URL_{account_index}", "").strip()

    if not naver_id or not naver_pw or not category:
        raise RuntimeError(f"{account_index}번 계정 환경변수 누락")

    return naver_id, naver_pw, category, brand_connect_url


def validate_required_env(account_index: int = 1):
    missing = []

    naver_id = os.getenv(f"NAVER_ID_{account_index}", "").strip()
    naver_pw = os.getenv(f"NAVER_PW_{account_index}", "").strip()
    category = os.getenv(f"CATEGORY_{account_index}", "").strip()
    brand_connect_url = os.getenv(f"BRAND_CONNECT_URL_{account_index}", "").strip()

    if not naver_id:
        missing.append(f"NAVER_ID_{account_index}")
    if not naver_pw:
        missing.append(f"NAVER_PW_{account_index}")
    if not category:
        missing.append(f"CATEGORY_{account_index}")
    if not brand_connect_url:
        missing.append(f"BRAND_CONNECT_URL_{account_index}")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    if missing:
        raise RuntimeError(f"환경변수 누락: {', '.join(missing)}")