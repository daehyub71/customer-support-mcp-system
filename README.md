# Jira/Confluence MCP 기반 고객 대응 운영자 AI 시스템

## 프로젝트 개요

기존 Jira/Confluence에 축적된 고객 문의 이력, 해결 방법, 기술 문서를 활용하여 고객 문의에 대한 답변을 자동으로 생성하는 AI 시스템입니다.

### 주요 기능

- 📧 **자동 답변 생성**: RAG 기반으로 고객 문의에 가장 적합한 답변 자동 도출
- 🔍 **지능형 문서 검색**: FAISS 벡터 DB를 활용한 고속 유사 문서 검색
- 🤖 **멀티 에이전트 워크플로우**: LangGraph 기반 4단계 질의 처리 (분석 → 검색 → 생성 → 작성)
- 🔄 **실시간 데이터 동기화**: MCP를 통한 Jira/Confluence 실시간 조회
- 📊 **운영자 친화적 UI**: Streamlit 기반 직관적인 웹 인터페이스

## 기술 스택

- **Frontend**: Streamlit
- **Workflow Engine**: LangGraph
- **LLM**: Azure OpenAI GPT-4o
- **Embedding**: Azure OpenAI text-embedding-3-large
- **Vector DB**: FAISS
- **MCP Server**: sooperset/mcp-atlassian (Docker)
- **Cache DB**: SQLite
- **Framework**: LangChain

## 사전 요구사항

- Python 3.10 이상
- Docker Desktop
- Azure OpenAI API 키
- Atlassian API Token

## 빠른 시작

### 1. 저장소 클론

```bash
git clone <repository-url>
cd data_analysis
```

### 2. 환경 설정

`.env` 파일을 생성하고 필요한 환경변수를 설정합니다:

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일 편집 (실제 값으로 변경)
# - AOAI_API_KEY: Azure OpenAI API 키
# - AOAI_ENDPOINT: Azure OpenAI 엔드포인트
# - ATLASSIAN_URL: Atlassian 도메인 (예: https://your-domain.atlassian.net)
# - ATLASSIAN_EMAIL: Atlassian 계정 이메일
# - ATLASSIAN_API_TOKEN: Atlassian API 토큰
```

#### Atlassian API Token 발급 방법

1. https://id.atlassian.com/manage-profile/security/api-tokens 접속
2. "Create API token" 클릭
3. 토큰 이름 입력 후 생성
4. 생성된 토큰을 `.env` 파일의 `ATLASSIAN_API_TOKEN`에 입력

### 3. MCP Server 실행 (Docker)

```bash
# Docker 컨테이너 시작
docker-compose up -d

# 컨테이너 상태 확인
docker ps | grep mcp-atlassian

# 로그 확인
docker logs mcp-atlassian

# Health check 확인
curl http://localhost:3000/health
```

**예상 출력:**
```json
{"status": "ok"}
```

### 4. Python 가상환경 설정

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 5. 데이터 수집 (최초 1회)

```bash
# Jira 이슈 수집 (최근 6개월)
python scripts/collect_data.py --source jira --jql "status=Done AND resolved>=-180d" --limit 100

# Confluence 페이지 수집
python scripts/collect_data.py --source confluence --spaces CS,TECH --limit 50
```

### 6. RAG 인덱스 빌드

```bash
# FAISS 인덱스 생성
python scripts/build_index.py --source all --rebuild
```

### 7. Streamlit 앱 실행

```bash
streamlit run app/main.py
```

브라우저에서 http://localhost:8501 접속

## Docker 관리

### MCP Server 중지

```bash
docker-compose down
```

### MCP Server 재시작

```bash
docker-compose restart
```

### 로그 실시간 확인

```bash
docker-compose logs -f mcp-atlassian
```

### 컨테이너 Health Check

```bash
docker inspect --format='{{.State.Health.Status}}' mcp-atlassian
```

## 프로젝트 구조

```
data_analysis/
├── docker-compose.yml          # MCP Server 설정
├── .env                        # 환경변수 (Git 제외)
├── .env.example                # 환경변수 템플릿
├── requirements.txt            # Python 의존성
│
├── app/
│   ├── main.py                 # Streamlit 메인 앱
│   ├── mcp/                    # MCP 클라이언트
│   ├── services/               # 핵심 서비스 (RAG, Embedding 등)
│   ├── workflows/              # LangGraph 워크플로우
│   ├── ui/                     # Streamlit UI 컴포넌트
│   ├── utils/                  # 유틸리티
│   └── data/                   # 데이터 저장소
│       ├── cache/              # SQLite DB
│       ├── index/              # FAISS 인덱스
│       └── templates/          # 메일 템플릿
│
├── scripts/                    # 유틸리티 스크립트
│   ├── collect_data.py         # 데이터 수집
│   ├── build_index.py          # 인덱스 빌드
│   └── trigger_collection.py   # 수동 수집 트리거
│
├── tests/                      # 테스트 코드
│
└── docs/                       # 문서
    ├── 개발계획서.md
    ├── 상세_Task_정의서_DoD.md
    └── Task_실행_프롬프트_모음.md
```

## 트러블슈팅

### MCP Server 연결 실패

```bash
# Docker 컨테이너 상태 확인
docker ps -a | grep mcp-atlassian

# 로그에서 에러 확인
docker logs mcp-atlassian

# 환경변수 확인
docker exec mcp-atlassian env | grep ATLASSIAN

# 재시작
docker-compose restart
```

### Health Check 실패

- Atlassian API Token 유효성 확인
- 네트워크 연결 확인
- Atlassian URL 형식 확인 (https:// 포함)

### 데이터 수집 실패

- `.env` 파일의 환경변수 확인
- Atlassian API 제한 확인 (Rate Limiting)
- JQL 쿼리 문법 확인

## 주요 명령어

```bash
# Docker 관련
docker-compose up -d              # MCP Server 시작
docker-compose down               # MCP Server 중지
docker-compose logs -f            # 로그 실시간 확인

# 데이터 수집
python scripts/collect_data.py --source jira --limit 100
python scripts/collect_data.py --source confluence --spaces CS,TECH

# 인덱스 빌드
python scripts/build_index.py --source all --rebuild

# 앱 실행
streamlit run app/main.py

# 테스트
pytest tests/ -v
```

## 개발 가이드

자세한 개발 가이드는 다음 문서를 참고하세요:

- [개발계획서](고객대응_운영자_시스템_개발계획서.md)
- [상세 Task 정의서](상세_Task_정의서_DoD.md)
- [Task 실행 프롬프트 모음](Task_실행_프롬프트_모음.md)

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 지원

문의사항은 [이슈](https://github.com/your-repo/issues)를 통해 제출해주세요.

---

**개발 상태**: Phase 1 - MCP 연동 진행 중 ✅
