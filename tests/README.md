# MCP Client Unit Tests

## 테스트 개요

`test_mcp_client.py`는 MCP Client의 핵심 기능을 검증하는 단위 테스트 모음입니다.

## 테스트 범위

### 1. 연결 테스트 (`TestMCPClientConnection`)
- ✅ `test_connect_success`: 연결 성공 케이스
- ✅ `test_connect_failure_with_retry`: 연결 실패 시 3회 재시도 검증
- ✅ `test_connect_success_after_retry`: 재시도 후 연결 성공
- ✅ `test_disconnect`: 안전한 연결 종료

### 2. 타임아웃 테스트 (`TestMCPClientTimeout`)
- ✅ `test_timeout_during_connect`: 연결 시 타임아웃 발생
- ✅ `test_timeout_configuration`: 타임아웃 설정 검증 (기본 30초)

### 3. Tool 작업 테스트 (`TestMCPClientToolOperations`)
- ✅ `test_list_tools_success`: Tool 목록 조회 성공
- ✅ `test_call_tool_success`: Tool 호출 성공
- ✅ `test_call_tool_error`: Tool 호출 실패 처리

### 4. Health Check 테스트 (`TestMCPClientHealthCheck`)
- ✅ `test_health_check_healthy`: 서버 정상 상태 확인
- ✅ `test_health_check_unhealthy`: 서버 비정상 상태 확인

### 5. 재시도 로직 테스트 (`TestMCPClientRetryLogic`)
- ✅ `test_exponential_backoff_delays`: 지수 백오프 검증 (1초, 2초, 4초)
- ✅ `test_max_retry_attempts`: 최대 3회 재시도 검증

### 6. 환경변수 테스트 (`TestMCPClientEnvironmentVariables`)
- ✅ `test_env_var_configuration`: 환경변수 기반 설정
- ✅ `test_parameter_override_env_vars`: 파라미터 우선순위

## 테스트 실행 방법

### Prerequisites
```bash
# 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 전체 테스트 실행
```bash
# 모든 테스트 실행
pytest tests/test_mcp_client.py -v

# 커버리지 포함
pytest tests/test_mcp_client.py --cov=app.mcp --cov-report=html

# 상세한 출력
pytest tests/test_mcp_client.py -vv --tb=long
```

### 특정 테스트 클래스 실행
```bash
# 연결 테스트만 실행
pytest tests/test_mcp_client.py::TestMCPClientConnection -v

# 재시도 로직 테스트만 실행
pytest tests/test_mcp_client.py::TestMCPClientRetryLogic -v
```

### 특정 테스트 케이스 실행
```bash
# 연결 성공 테스트만 실행
pytest tests/test_mcp_client.py::TestMCPClientConnection::test_connect_success -v

# 타임아웃 테스트만 실행
pytest tests/test_mcp_client.py::TestMCPClientTimeout::test_timeout_during_connect -v
```

### Python 스크립트로 직접 실행
```bash
# 테스트 파일 직접 실행
python tests/test_mcp_client.py
```

## 테스트 커버리지 목표

- 연결 성공/실패: 100%
- 재시도 로직: 100%
- 타임아웃 처리: 100%
- Tool 호출: 90%+
- Health Check: 100%

## Mock 전략

모든 테스트는 실제 MCP 서버 없이 실행됩니다:
- `requests.Session` → Mock으로 대체
- `time.sleep` → Mock으로 대체 (테스트 속도 향상)
- 환경변수 → `@patch.dict`로 격리

## 주요 검증 항목

### 재시도 로직
```python
retry_delays = [1, 2, 4]  # 지수 백오프
max_attempts = 3          # 최대 시도 횟수
```

### 타임아웃 설정
```python
default_timeout = 30      # 기본 30초
configurable = True       # 설정 가능
```

### 환경변수
```python
MCP_SERVER_HOST = "localhost"  # 기본값
MCP_SERVER_PORT = "9000"       # 기본값
```

## 트러블슈팅

### Import Error
```bash
# sys.path에 프로젝트 루트 추가
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### pytest not found
```bash
pip install pytest pytest-cov
```

### Mock 관련 에러
```bash
# unittest.mock은 Python 3.3+ 기본 제공
python --version  # 3.3 이상 확인
```

## 지속적 통합 (CI)

GitHub Actions 예시:
```yaml
- name: Run MCP Client Tests
  run: |
    pytest tests/test_mcp_client.py -v --cov=app.mcp
```
