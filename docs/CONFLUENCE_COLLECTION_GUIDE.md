# Confluence 데이터 수집 가이드

이 가이드는 실제 Confluence 인스턴스에서 데이터를 수집하는 방법을 설명합니다.

## 현재 상태 확인

스크린샷에서 보이는 Docker 컨테이너 상태:
- ✅ `confluence` - Confluence 서버 (포트 8090:8090)
- ✅ `mcp-atlassian` - MCP 서버 (포트 9000:9000)
- ✅ `confluence-postgres` - PostgreSQL 데이터베이스
- ⚠️ `jira` - Jira 서버 (선택사항)

## 사전 준비사항

### 1. 컨테이너 상태 확인

```bash
# 모든 컨테이너가 실행 중인지 확인
docker ps

# 출력 예시:
# CONTAINER ID   IMAGE                                    PORTS                    NAMES
# 119e5329b1fe   atlassian/confluence:latest             8090->8090              confluence
# e88fefd9e5f0   sooperset/mcp-atlassian:latest          9000->9000              mcp-atlassian
# 48355f7bff88   postgres:14-alpine                      5432                     confluence-postgres
```

### 2. Confluence 접속 및 초기 데이터 생성

1. **브라우저에서 Confluence 접속**
   ```
   http://localhost:8090
   ```

2. **공간(Space) 생성**
   - 좌측 메뉴에서 "만들기" → "공간" 클릭
   - 공간 이름 입력 (예: `MY_TEST`)
   - 공간 키 설정 (예: `MY_TEST`)

3. **페이지 생성**
   - 생성한 공간에서 "만들기" → "페이지" 클릭
   - 제목과 내용 입력
   - 최소 3-5개 페이지 생성 권장

스크린샷에 보이는 예시 페이지들:
- "고객 대응 운영자 시스템 - 상세 Task 정의서 DoD"
- "Task 상세 프롬프트 모음"
- "상세개발 Task (Streamlit 기반 UI-스 빌딩)"
- 등등...

### 3. MCP 서버 연결 테스트

```bash
cd customer-support-mcp-system

# MCP 서버 연결 테스트
python scripts/test_mcp_connection.py
```

**예상 출력:**
```
Testing connection to MCP server at localhost:9000...
✓ Connected to MCP server
✓ Available tools: 4
  - jira_search: Search Jira issues using JQL
  - jira_get_issue: Get details of a specific Jira issue
  - confluence_search: Search Confluence pages
  - confluence_get_page: Get details of a specific Confluence page
```

**만약 Confluence 도구가 없다면:**
```
✗ No Confluence tools found!
  This might mean the MCP server couldn't authenticate with Confluence
```

→ MCP 서버 로그 확인:
```bash
docker logs mcp-atlassian
```

## 데이터 수집 방법

### 방법 1: 자동 스크립트 사용 (권장)

```bash
cd customer-support-mcp-system

# 기본 사용 - 모든 공간에서 최대 50개 페이지 수집
python scripts/collect_from_real_confluence.py

# 특정 공간만 수집
python scripts/collect_from_real_confluence.py --spaces MY_TEST CS

# 더 많은 페이지 수집
python scripts/collect_from_real_confluence.py --max-pages 100

# Mock 서버로 테스트 (개발용)
python scripts/collect_from_real_confluence.py --port 9001
```

**출력 예시:**
```
================================================================================
Collecting Confluence Data from Real MCP Server
================================================================================
MCP Server: localhost:9000
Max pages per space: 50
Target spaces: ALL
================================================================================

Testing MCP server connection...
✓ Connected to MCP server
✓ Available tools: 4
✓ Found 2 Confluence tools

✓ Collector initialized with database: app/data/cache/confluence_real.db

================================================================================
STEP 1: Listing Available Spaces
================================================================================

✓ Found 2 spaces:
  - MY_TEST: My Test Space (global)
  - CS: Customer Support (global)

================================================================================
STEP 2: Collecting Pages
================================================================================
Collecting from 2 space(s): MY_TEST, CS

→ Collecting from space: MY_TEST
  ✓ Found 8 pages
    1. Claude Code MCP 기반 고객 대응 운영자 시스템 개발계획서 (ID: 12345)
    2. Task 상세 프롬프트 모음 (ID: 12346)
    3. 상세개발 Task (Streamlit 기반 UI-스 빌딩) (ID: 12347)
    ... and 5 more pages

================================================================================
STEP 3: Saving to Database
================================================================================
Saving pages: 100%|████████████████████| 1/1 [00:00<00:00, 15.2it/s]
✓ Saved 8 pages to database

================================================================================
STEP 4: Collection Statistics
================================================================================

📊 Collection Summary:
  Total pages: 8
  Total spaces: 2
  Last sync: 2025-10-05 12:34:56

  Pages per space:
    MY_TEST: 8 pages

  Date range:
    Oldest: 2025-09-04 14:26:52
    Newest: 2025-10-04 04:22:52

================================================================================
✓ Collection completed successfully!
================================================================================

Database location: app/data/cache/confluence_real.db
You can now use this data for RAG indexing.
```

### 방법 2: Python 코드로 직접 사용

```python
from app.mcp.mcp_client import MCPClient
from app.mcp.confluence_collector import ConfluenceCollector

# MCP 클라이언트 초기화
client = MCPClient(host="localhost", port=9000)
client.connect()

# Confluence Collector 초기화
collector = ConfluenceCollector(
    mcp_client=client,
    db_path="app/data/cache/confluence_real.db"
)

# 공간 목록 조회
spaces = collector.list_spaces()
print(f"Available spaces: {[s['key'] for s in spaces]}")

# 특정 공간의 페이지 수집
pages = collector.list_pages(space_key="MY_TEST", limit=50)
print(f"Collected {len(pages)} pages")

# 데이터베이스에 저장
saved_count = collector.save_to_cache(pages)
print(f"Saved {saved_count} pages")

# 통계 조회
stats = collector.get_collection_stats()
print(f"Total pages in DB: {stats['total_pages']}")
```

## 단위 테스트 실행

### 1. 전체 테스트 실행

```bash
cd customer-support-mcp-system

# pytest가 설치되어 있어야 함
pip install pytest

# Confluence Collector 테스트 실행
pytest tests/test_confluence_collector.py -v
```

**예상 출력:**
```
tests/test_confluence_collector.py::TestConfluenceCollectorInitialization::test_init_creates_database PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorInitialization::test_init_creates_schema PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorSpaces::test_list_spaces_success PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorSpaces::test_list_spaces_saves_to_cache PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorPages::test_list_pages_success PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorPages::test_get_page_content PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorCaching::test_save_to_cache PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorCaching::test_save_to_cache_batch_processing PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorHTMLCleaning::test_clean_html_removes_scripts PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorHTMLCleaning::test_clean_html_removes_styles PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorHTMLCleaning::test_clean_html_normalizes_whitespace PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorHTMLCleaning::test_clean_html_extracts_text PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorStats::test_get_collection_stats PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorStats::test_get_cached_pages PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorStats::test_get_cached_pages_with_filter PASSED
tests/test_confluence_collector.py::TestConfluenceCollectorStats::test_clear_cache PASSED

==================== 16 passed in 2.34s ====================
```

### 2. 특정 테스트만 실행

```bash
# HTML 정리 기능 테스트만 실행
pytest tests/test_confluence_collector.py::TestConfluenceCollectorHTMLCleaning -v

# 캐싱 기능 테스트만 실행
pytest tests/test_confluence_collector.py::TestConfluenceCollectorCaching -v
```

### 3. 모든 테스트 실행

```bash
# 전체 테스트 스위트 실행
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=app/mcp --cov-report=html
```

## 수집된 데이터 확인

### SQLite 데이터베이스 직접 조회

```bash
# SQLite CLI 사용
sqlite3 app/data/cache/confluence_real.db

# 또는 Python으로 조회
python -c "
import sqlite3
conn = sqlite3.connect('app/data/cache/confluence_real.db')
cursor = conn.execute('SELECT page_id, title, space_key FROM confluence_pages LIMIT 10')
for row in cursor:
    print(row)
"
```

### 프로그래밍 방식 조회

```python
from app.mcp.confluence_collector import ConfluenceCollector
from app.mcp.mcp_client import MCPClient

client = MCPClient(host="localhost", port=9000)
collector = ConfluenceCollector(client, "app/data/cache/confluence_real.db")

# 캐시된 페이지 조회
pages = collector.get_cached_pages(limit=10)
for page in pages:
    print(f"{page['title']} ({page['space_key']})")

# 통계 조회
stats = collector.get_collection_stats()
print(f"Total pages: {stats['total_pages']}")
print(f"Space distribution: {stats['space_distribution']}")
```

## 문제 해결 (Troubleshooting)

### 1. MCP 서버 연결 실패

**증상:**
```
✗ Connection failed: [Errno 111] Connection refused
```

**해결:**
```bash
# 컨테이너 상태 확인
docker ps | grep mcp-atlassian

# 재시작
docker-compose restart mcp-atlassian

# 로그 확인
docker logs mcp-atlassian
```

### 2. Confluence 도구를 찾을 수 없음

**증상:**
```
✗ No Confluence tools found!
```

**원인:**
- MCP 서버가 Confluence에 인증하지 못함
- Confluence가 초기화되지 않음

**해결:**
1. Confluence 설정 확인: http://localhost:8090
2. MCP 서버 로그 확인:
   ```bash
   docker logs mcp-atlassian | grep -i confluence
   ```
3. 환경 변수 확인 (.env 파일):
   ```bash
   docker exec mcp-atlassian env | grep ATLASSIAN
   ```

### 3. 페이지를 찾을 수 없음

**증상:**
```
⚠ No pages found in MY_TEST
```

**해결:**
1. Confluence에 실제로 페이지가 있는지 확인: http://localhost:8090
2. 공간 키가 정확한지 확인
3. 공간이 비어있지 않은지 확인

### 4. 데이터베이스 권한 오류

**증상:**
```
PermissionError: [Errno 13] Permission denied: 'app/data/cache/confluence_real.db'
```

**해결:**
```bash
# 디렉토리 생성
mkdir -p app/data/cache

# 권한 부여 (Linux/Mac)
chmod 755 app/data/cache

# Windows에서는 탐색기에서 폴더 권한 확인
```

## 다음 단계

수집이 완료되면:

1. **RAG 인덱스 빌드** (Phase 2)
   ```bash
   python scripts/build_index.py --source confluence --rebuild
   ```

2. **데이터 품질 검증**
   - HTML 정리가 제대로 되었는지 확인
   - 중복 페이지 체크
   - 메타데이터 확인

3. **점진적 업데이트 설정**
   ```python
   # 최근 24시간 동안 업데이트된 페이지만 수집
   collector.incremental_update(since_hours=24)
   ```

## 참고 자료

- [MCP 서버 설정 가이드](MCP_SERVER_SETUP.md)
- [Jira Collector 가이드](JIRA_COLLECTOR.md)
- [테스트 요약](../tests/TEST_SUMMARY.md)
- [Mock 서버 문서](../MOCK_SERVER_README.md)
