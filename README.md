# Naver Blog Affiliate Auto Writer 🤖✍️

네이버 쇼핑커넥트(BrandConnect) 상품 링크를 자동으로 발급받고  
AI를 이용해 체험형 후기 블로그 글을 생성한 뒤  
네이버 블로그에 자동으로 작성/발행하는 Python 자동화 프로젝트입니다.

---

# 주요 기능 🚀

## 1️⃣ 브랜드커넥트 자동 링크 발급

- 상품 리스트 자동 탐색
- 이미 발급된 상품 자동 제외
- 가격 범위 필터 지원
- 무한 스크롤 대응
- 상품 이미지 자동 다운로드

---

## 2️⃣ AI 블로그 후기 자동 생성

- 체험형 후기 스타일 자동 생성
- 광고 느낌 최소화
- 네이버 블로그 에디터 최적화 포맷
- 링크 2회 자동 삽입 보장
- 해시태그 자동 생성

---

## 3️⃣ 네이버 블로그 자동 작성

- 로그인 세션 재사용
- 기존 임시글 팝업 자동 취소 처리
- 제목 / 본문 / 해시태그 자동 입력
- 링크 입력 후 미리보기 생성 대기 처리
- 이미지 자동 업로드

---

## 4️⃣ 계정별 자동 실행 지원

- 계정별 playwright 세션 분리
- 계정별 카테고리 설정 가능
- 계정별 브랜드커넥트 URL 설정 가능

---

# 프로젝트 구조 📂

```python
  naver_blog_bot/
  │
  ├── blog_bot.py
  ├── blog_writer.py
  ├── ai_writer.py
  ├── config.py
  │
  ├── prompts/
  │ └── blog_review_prompt.txt
  │
  ├── output/
  ├── images/
  │
  ├── browser_profile_acc1/
  ├── browser_profile_acc2/
  ├── browser_profile_acc3/
  │
  ├── .env
  └── README.md
```


---

# 실행 환경 🧩

Python 3.10 이상 권장

필수 패키지

```python
  playwright
  python-dotenv
  openai
  pyperclip
  requests
```

설치 방법

```python
  pip install -r requirements.txt
  playwright install
```



---

# 환경 변수 설정 (.env) 🔐

예시

```python
  OPENAI_API_KEY=your_api_key
  
  NAVER_ID_1=example_id
  NAVER_PW_1=example_pw
  NAVER_CATEGORY_1=의자
  BRAND_CONNECT_URL_1=https://brandconnect.naver.com/xxxxxxxx
  
  NAVER_ID_2=example_id
  NAVER_PW_2=example_pw
  NAVER_CATEGORY_2=가전
  BRAND_CONNECT_URL_2=https://brandconnect.naver.com/xxxxxxxx
  
  MIN_PRICE=70000
  MAX_PRICE=9000000
```

설명

| 변수 | 설명 |
|------|------|
| NAVER_ID_n | 네이버 계정 ID |
| NAVER_PW_n | 네이버 계정 비밀번호 |
| NAVER_CATEGORY_n | 검색할 상품 키워드 |
| BRAND_CONNECT_URL_n | 브랜드커넥트 상품 페이지 URL |
| MIN_PRICE | 최소 상품 가격 |
| MAX_PRICE | 최대 상품 가격 |


주의

```python
  .env 파일은 절대 GitHub에 업로드하지 않습니다
```



---

# 실행 방법 ▶️

기본 실행

```python
  python main.py
```

또는 코드 내부 실행

```python
  run_generate_review_flow(post_count=3, account_index=1)
```


옵션 설명

| 옵션 | 설명 |
|------|------|
| post_count | 작성할 글 개수 |
| account_index | 사용할 계정 번호 |

예시

```python
  run_generate_review_flow(post_count=20, account_index=1)
```

---

# 자동 로그인 방식 🔑

본 프로젝트는 자동 로그인 대신

Playwright Persistent Session 방식 사용

최초 1회 로그인 후

```python
  browser_profile_acc1/
```


폴더에 세션 저장

이후 자동 로그인 유지됩니다

자동입력 방지 문자 대응 목적입니다

---

# 가격 필터 기능 💰

.env 설정

```pyhton
  MIN_PRICE=70000
  MAX_PRICE=9000000
```



설정 범위 내 상품만 자동 선택됩니다

---

# 자동화 안정 실행 권장 설정 ⚠️

네이버 블로그 자동화는 과도한 실행 시 제한될 수 있습니다

권장 설정

- 계정당 하루 10 ~ 20개 작성
- 게시글 간 30 ~ 90초 랜덤 대기
- 계정별 실행 시간 분산

---

# 보안 안내 🔒

다음 파일은 GitHub 업로드 제외 권장

```python
  .env
  browser_profile_acc*
  output/
  images/
```


로그인 세션 및 개인정보 보호 목적입니다

---

# 사용 기술 🛠️

Python  
Playwright  
OpenAI API  
dotenv  
Requests  
pyperclip  

---

# 향후 개선 예정 기능 📌

- 자동 예약 발행 기능
- 카테고리 자동 선택 기능
- 썸네일 위치 지정 옵션
- 프롬프트 자동 최적화
- 다계정 스케줄 실행 기능

---

# License

개인 학습 및 자동화 연구 목적 프로젝트







