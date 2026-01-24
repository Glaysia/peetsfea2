# AGENTS

## MCP 알림 규칙
- 작업이 끝나면 `notify/show`를 호출해 알림을 띄운다.
- 성공 시 제목은 `Codex 완료`, 메시지에는 요약 1~2줄 + 다음 행동(있다면)을 넣는다.
- 실패/중단 시 제목은 `Codex 실패`, 메시지에는 실패 원인 요약을 넣는다.
- `notify/show` 호출 메시지에 본인이 어떤 `codex*` 인스턴스인지 명시한다 (예: codex1/codex2/codex3/codex_main).

## MCP 알림 서버 설정(로컬)
- `~/.codex/config.toml`에 아래를 추가한다.

```
[mcp_servers.notify]
url = "http://127.0.0.1:17999/sse"
enabled = true
```

- systemd 사용자 서비스 `mcp-notify.service`가 실행 중이어야 한다.
- 만약 `/mcp`가 400 에러를 반환하면 `/sse`를 사용한다.

## 테스트
- 간단 확인: `notify/show` 호출로 `hello` 알림을 띄운다.

## Python 환경
- 기본 가상환경: `/home/harry/Projects/PythonProjects/.venv`
- 설치: `uv pip install -e /home/harry/Projects/PythonProjects/peetsfea2`
- 실행 시에는 위 venv의 python을 사용한다.
