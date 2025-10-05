# 로컬 Confluence 직접 연결 가이드

MCP 서버를 우회하고 로컬 Confluence 서버에 직접 연결하는 방법입니다.

## 왜 직접 연결이 필요한가?

MCP 서버(`mcp-atlassian`)는 **Atlassian Cloud 전용**으로 설계되어 있어서 로컬 Confluence 서버와 호환되지 않습니다.

### 문제점
- ✗ MCP 서버: Atlassian Cloud API Token 사용
- ✗ 로컬 Confluence: Username/Password 인증 사용
- ✗ 두 방식이 호환되지 않음

### 해결 방법
Confluence REST API를 직접 호출하여 데이터 수집

## 사전 준비

### 1. Confluence 서버 확인

```bash
# Confluence가 실행 중인지 확인
curl http://localhost:8090

# Docker 컨테이너 확인
docker ps | findstr confluence
```

### 2. Confluence 초기 설정

처음 Confluence를 시작하면 초기 설정이 필요합니다:

1. **브라우저에서 접속**
   ```
   http://localhost:8090
   ```

2. **라이선스 설정**
   - "Trial License" 또는 "Evaluation License" 선택
   - Atlassian 계정으로 로그인하여 라이선스 받기

3. **관리자 계정 생성**
   - Username: `admin`
   - Password: `admin` (또는 원하는 비밀번호)
   - 이 계정 정보를 기억하세요!

4. **공간(Space) 생성**
   - 좌측 메뉴에서 "만들기" → "공간" 클릭
   - 공간 이름: `MY_TEST` (또는 원하는 이름)
   - 공간 키: `MY_TEST` (대문자, 언더스코어 사용)

5. **페이지 생성**
   - 생성한 공간에서 "만들기" → "페이지" 클릭
   - 제목과 내용 입력 후 게시
   - 최소 3-5개 페이지 생성 권장

## 사용 방법

### 방법 1: 연결 테스트 (먼저 실행 권장)

```bash
cd customer-support-mcp-system

# 기본 설정으로 테스트 (username=admin, password=admin)
python scripts/test_direct_connection.py

# 다른 계정으로 테스트
python scripts/test_direct_connection.py --username myuser --password mypass

# 다른 URL로 테스트
python scripts/test_direct_connection.py --url http://confluence.example.com:8090
```

**예상 출력:**
```
================================================================================
Testing Direct Confluence Connection
================================================================================

URL: http://localhost:8090
Username: admin
Password: *****

================================================================================

1. Initializing client...
   [OK] Client initialized

2. Testing connection...
   [OK] Connection successful

3. Listing spaces...
   [OK] Found 2 space(s):
      - MY_TEST: My Test Space
      - DS: Documentation Space

4. Getting pages from space 'MY_TEST'...
   [OK] Found 3 page(s):
      1. Welcome to Confluence
         ID: 12345, Version: 1
         Created: 2025-10-05 10:30:00
         Content length: 1234 chars
      2. Getting Started
         ID: 12346, Version: 2
         Created: 2025-10-05 11:00:00
         Content length: 567 chars
      3. User Guide
         ID: 12347, Version: 1
         Created: 2025-10-05 11:30:00
         Content length: 890 chars

================================================================================
✓ Connection Test Completed Successfully!
================================================================================

You can now collect data with:
  python scripts/collect_direct_confluence.py \
    --url http://localhost:8090 \
    --username admin \
    --password admin
```

### 방법 2: 데이터 수집

연결 테스트가 성공하면 데이터 수집을 시작합니다.

```bash
# 모든 공간에서 데이터 수집 (기본)
python scripts/collect_direct_confluence.py \
  --url http://localhost:8090 \
  --username admin \
  --password admin

# 특정 공간만 수집
python scripts/collect_direct_confluence.py \
  --url http://localhost:8090 \
  --username admin \
  --password admin \
  --spaces MY_TEST CS

# 더 많은 페이지 수집
python scripts/collect_direct_confluence.py \
  --url http://localhost:8090 \
  --username admin \
  --password admin \
  --max-pages 200
```

**예상 출력:**
```
================================================================================
Direct Confluence Data Collection
================================================================================
Confluence URL: http://localhost:8090
Username: admin
Max pages per space: 100
Target spaces: ALL
================================================================================

1. Initializing Confluence Client...
2025-10-05 14:30:00,123 - ConfluenceDirectClient initialized: http://localhost:8090/rest/api

2. Testing Connection...
✓ Connection successful!

3. Listing Spaces...
✓ Found 2 space(s):
  - MY_TEST: My Test Space (global)
  - DS: Documentation Space (global)

4. Collecting Pages from 2 space(s)...

→ Space: MY_TEST
  ✓ Collected 8 pages
    1. Claude Code MCP 기반 고객 대응 운영자 시스템 개발계획서 (ID: 98305, Version: 4)
    2. Task 상세 프롬프트 모음 (ID: 98306, Version: 2)
    3. 상세개발 Task (Streamlit 기반 UI-스 빌딩) (ID: 98307, Version: 1)
    4. Re: 고객 대응 운영자 시스템 - 상세 Task 정의서 (DoD 기반) (ID: 98308, Version: 3)
    5. 고객 대응 운영자 시스템 - 상세 Task 정의서 (DoD 기반) (ID: 98309, Version: 5)
    ... and 3 more pages

→ Space: DS
  ✓ Collected 5 pages
    1. API Documentation (ID: 12345, Version: 1)
    2. User Guide (ID: 12346, Version: 1)
    3. Troubleshooting (ID: 12347, Version: 2)
    4. FAQ (ID: 12348, Version: 1)
    5. Release Notes (ID: 12349, Version: 1)

5. Saving to Database...
Saving pages: 100%|████████████████████| 1/1 [00:00<00:00, 25.3it/s]
✓ Saved 13 pages

6. Collection Statistics...

📊 Summary:
  Total pages: 13
  Total spaces: 2
  Last sync: 2025-10-05 14:30:15

  Pages per space:
    MY_TEST: 8 pages
    DS: 5 pages

  Date range:
    Oldest: 2025-09-04 14:26:52
    Newest: 2025-10-04 04:22:52

================================================================================
✓ Collection Completed Successfully!
================================================================================

Database: c:\data_analysis\customer-support-mcp-system\app\data\cache\confluence_direct.db
You can now use this data for RAG indexing.

Next steps:
  python scripts/build_index.py --source confluence
```

## 수집된 데이터 확인

### SQLite 데이터베이스 조회

```bash
# SQLite CLI 사용
sqlite3 app/data/cache/confluence_direct.db

sqlite> SELECT page_id, title, space_key FROM confluence_pages LIMIT 5;

sqlite> SELECT COUNT(*) FROM confluence_pages;

sqlite> .quit
```

### Python으로 조회

```python
import sqlite3

conn = sqlite3.connect('app/data/cache/confluence_direct.db')
cursor = conn.execute('''
    SELECT page_id, title, space_key,
           LENGTH(body_cleaned) as content_length
    FROM confluence_pages
    ORDER BY updated_at DESC
    LIMIT 10
''')

for row in cursor:
    print(f"{row[0]}: {row[1]} ({row[2]}) - {row[3]} chars")

conn.close()
```

## 문제 해결

### 1. 연결 실패 (Connection refused)

**증상:**
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=8090)
```

**해결:**
```bash
# Confluence 컨테이너 확인
docker ps | findstr confluence

# 컨테이너가 없으면 시작
docker-compose up -d confluence

# 로그 확인
docker logs confluence
```

### 2. 401 Unauthorized

**증상:**
```
requests.exceptions.HTTPError: 401 Client Error: Unauthorized
```

**해결:**
1. 사용자명과 비밀번호가 정확한지 확인
2. Confluence에 직접 로그인하여 테스트:
   ```
   http://localhost:8090
   ```
3. 초기 설정이 완료되었는지 확인

### 3. 404 Not Found (REST API)

**증상:**
```
requests.exceptions.HTTPError: 404 Client Error: Not Found for url: http://localhost:8090/rest/api/space
```

**해결:**
1. Confluence 초기 설정 완료 확인
2. REST API 플러그인 활성화 확인
3. URL에 `/confluence` 컨텍스트 경로 필요한지 확인:
   ```bash
   # /confluence 경로 포함
   python scripts/test_direct_connection.py --url http://localhost:8090/confluence
   ```

### 4. 빈 공간 (No spaces found)

**증상:**
```
[WARN] No spaces found
```

**해결:**
1. http://localhost:8090 접속
2. "만들기" → "공간" 클릭
3. 공간 이름과 키 입력 후 생성

### 5. 빈 페이지 (No pages found)

**증상:**
```
[WARN] No pages found in space 'MY_TEST'
```

**해결:**
1. http://localhost:8090 접속
2. 해당 공간으로 이동
3. "만들기" → "페이지" 클릭
4. 내용 입력 후 게시

## 고급 사용법

### CQL 검색 사용

```python
from app.mcp.confluence_direct_client import ConfluenceDirectClient

client = ConfluenceDirectClient(
    base_url="http://localhost:8090",
    username="admin",
    password="admin"
)

# 최근 7일 동안 수정된 페이지
pages = client.search_pages(
    cql="type=page AND lastModified >= now('-7d')",
    limit=50
)

# 특정 텍스트 포함 페이지
pages = client.search_pages(
    cql="type=page AND text ~ 'customer support'",
    limit=100
)

# 특정 공간의 특정 라벨
pages = client.search_pages(
    cql="type=page AND space=MY_TEST AND label='important'",
    limit=50
)
```

### 페이지네이션

```python
# 대량 데이터 수집 (1000+ 페이지)
all_pages = []
start = 0
limit = 50

while True:
    pages = client.get_space_pages(
        space_key="MY_TEST",
        limit=limit,
        start=start
    )

    if not pages:
        break

    all_pages.extend(pages)
    start += limit

    if len(pages) < limit:
        break

print(f"Total collected: {len(all_pages)} pages")
```

## 다음 단계

데이터 수집이 완료되면:

1. **RAG 인덱스 빌드** (Phase 2)
   ```bash
   python scripts/build_index.py --source confluence --rebuild
   ```

2. **LangGraph 워크플로우 테스트** (Phase 3)
   ```bash
   python scripts/test_workflow.py
   ```

3. **Streamlit UI 실행** (Phase 4)
   ```bash
   streamlit run app/main.py
   ```

## 참고 자료

- [Confluence REST API 공식 문서](https://docs.atlassian.com/confluence/REST/latest/)
- [CQL (Confluence Query Language)](https://confluence.atlassian.com/doc/confluence-search-syntax-158720.html)
- [Confluence 설치 가이드](https://confluence.atlassian.com/doc/installing-confluence-on-linux-143556824.html)
