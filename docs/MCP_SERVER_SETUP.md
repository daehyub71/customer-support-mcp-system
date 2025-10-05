# MCP Server Setup Guide

## 문제: MCP 서버에 툴이 없음

현재 Atlassian MCP 서버(v1.9.4)가 실행 중이지만 툴이 등록되지 않았습니다.

```
Available Tools: []
Available Resources: []
```

## 원인

Atlassian MCP 서버 설정에서 Jira/Confluence 연동이 누락되었을 가능성이 높습니다.

## 해결 방법

### 1. Atlassian MCP 서버 설정 확인

`.env` 파일의 Atlassian 설정을 확인하세요:

```bash
# Atlassian MCP Server Configuration
ATLASSIAN_URL=http://host.docker.internal:8090
ATLASSIAN_EMAIL=daehyub
ATLASSIAN_API_TOKEN=none
```

**문제점:**
- `ATLASSIAN_URL`이 로컬 Confluence 서버를 가리킴 (http://host.docker.internal:8090)
- `ATLASSIAN_API_TOKEN=none` - 유효한 API 토큰이 아님
- 로컬 Confluence 서버가 실행 중이지 않을 수 있음

### 2. 로컬 Confluence 서버 확인

```bash
curl http://localhost:8090
```

만약 Confluence 서버가 없다면:
- Atlassian Cloud 계정 사용
- 또는 로컬 Confluence 인스턴스 설치

### 3. Atlassian Cloud 사용 (권장)

Atlassian Cloud를 사용하는 경우:

```bash
# .env 파일 수정
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_EMAIL=your-email@company.com
ATLASSIAN_API_TOKEN=your-real-api-token
```

API 토큰 생성:
1. https://id.atlassian.com/manage-profile/security/api-tokens
2. "Create API token" 클릭
3. 생성된 토큰을 `.env`에 저장

### 4. MCP 서버 재시작

설정 변경 후 MCP 서버 재시작:

```bash
# MCP 서버 프로세스 종료
# Windows
taskkill /F /PID <mcp-server-pid>

# 재시작 (MCP 서버 실행 명령)
# ... (MCP 서버 시작 명령)
```

### 5. Mock 모드 사용 (개발/테스트)

실제 Atlassian 서버 없이 테스트하려면:

```bash
# Mock 모드로 수집 (구현 예정)
python scripts/collect_data.py --source jira --mock

# 또는 샘플 데이터 사용
python scripts/collect_data.py --source jira --sample-data
```

## 예상되는 툴 목록

정상적으로 설정되면 다음 툴들이 나타나야 합니다:

**Jira Tools:**
- `jira_search_issues` - JQL로 이슈 검색
- `jira_get_issue` - 특정 이슈 조회
- `jira_list_projects` - 프로젝트 목록
- `jira_create_issue` - 이슈 생성

**Confluence Tools:**
- `confluence_search` - 페이지 검색
- `confluence_get_page` - 페이지 조회
- `confluence_list_spaces` - Space 목록
- `confluence_get_space` - Space 조회

## 확인 방법

```bash
# 툴 목록 확인
python scripts/list_mcp_tools.py

# 연결 테스트
python scripts/test_mcp_connection.py
```

## 트러블슈팅

### MCP 서버 로그 확인

MCP 서버의 로그를 확인하여 에러 메시지를 찾으세요.

### Atlassian 연결 테스트

```bash
# Jira API 직접 테스트
curl -u "email:api_token" \
  https://your-domain.atlassian.net/rest/api/3/myself

# Confluence API 직접 테스트
curl -u "email:api_token" \
  https://your-domain.atlassian.net/wiki/rest/api/space
```

### 방화벽/프록시 확인

회사 방화벽이나 프록시가 Atlassian Cloud 접근을 차단하는지 확인하세요.

## 대안: 샘플 데이터로 개발

Atlassian 서버 설정이 어려운 경우, 샘플 데이터를 사용하여 개발을 계속할 수 있습니다.

샘플 데이터 파일:
- `app/data/samples/jira_sample.json`
- `app/data/samples/confluence_sample.json`

사용 방법:
```bash
# 샘플 데이터 수집
python scripts/collect_data.py --source jira --sample-file app/data/samples/jira_sample.json
```

## 참고 자료

- [Atlassian MCP Server Documentation](https://github.com/modelcontextprotocol/servers/tree/main/src/atlassian)
- [Atlassian API Token Guide](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
