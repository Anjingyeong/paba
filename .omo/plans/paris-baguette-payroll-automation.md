# paris-baguette-payroll-automation - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** 매장 태블릿 출퇴근, 점장 확인·정정·승인, 주휴/보험 확정, 월마감, 직원별 급여명세서와 점장용 엑셀 묶음까지 이어지는 한 매장 전용 웹앱입니다.

**Why this approach:** 공유 기기에는 짧은 PIN만 쓰되 급여·설정은 점장 다중인증으로 분리하고, 원본 출퇴근과 마감 결과를 버전별로 보존해 잘못된 기록을 고쳐도 과거 근거가 사라지지 않게 합니다. 주휴와 보험은 자동 추정하되 법 적용과 기관 고지액은 점장이 확정합니다.

**What it will NOT do:** 급여이체·세금신고·공단제출·이메일 발송은 하지 않습니다. 위치추적·생체인식·주민번호 저장이나 직원용 급여 포털도 포함하지 않습니다. 원본 엑셀의 개인정보와 잘못된 20% 수식은 제품에 들어가지 않습니다.

**Effort:** XL
**Risk:** High - 임금·4대보험·개인정보와 동시 출퇴근 기록을 함께 다루며 엑셀 결과가 법정 기재사항과 정확히 맞아야 합니다.
**Decisions to sanity-check:** 한 매장만 지원, 월~일 근로주, AWS 서울 관리형 배포, 직원 6자리 PIN, 점장 TOTP, 점장 세션 15분 유휴/8시간 절대 만료, 오프라인 기록 대신 점장 사후정정을 기본으로 채택했습니다.

Your next move: 바로 실행하거나, 법률·급여 위험을 감안해 먼저 고정밀 이중검토를 한 번 더 실행합니다. Full execution detail follows below.

---

> TL;DR (machine): XL/high-risk greenfield Django monolith; paired kiosk, audited attendance, manager-confirmed payroll, immutable monthly close, compliant XLSX export, AWS Seoul operations; 16 implementation todos in 3 waves plus 4 final gates.

## Scope
### Must have
- 한 매장 전용 Django/PostgreSQL 웹앱: 등록된 매장 태블릿에서 직원이 개인 PIN으로 출근·휴게시작·휴게종료·퇴근을 기록하고 즉시 잠금 화면으로 복귀한다.
- 점장 계정은 TOTP MFA로 로그인해 예외 출퇴근을 정정·승인하고, 직원별 유효기간 기반 근로계약·시급·주휴·4대보험 설정을 관리한다.
- 승인된 근태로 기본급과 점장이 적용 확정한 주휴수당을 산정한다. GENERAL은 주휴/보험 기본 꺼짐, MANAGER는 기본 켜짐이지만 역할명만으로 법 적용을 확정하지 않는다.
- 국민연금·건강보험·장기요양·고용보험은 버전이 붙은 공식 기준으로 예상하고 점장이 기관 고지액과 대사해 확정한다. 산재보험은 직원 공제에서 제외한다.
- 월 마감은 입력·규칙·계산 설명을 불변 스냅샷으로 만들고, 재오픈/재마감은 이전 버전을 보존한 새 버전으로 만든다.
- 원본 두 XLSX의 시각 언어를 따르되 PII와 오류 수식을 제거한 단일기간 표준 명세서, 점장 요약 XLSX, ZIP/manifest를 생성한다.
- 한국어/CJK, 키보드, 200% 확대, 44x44 터치, WCAG 2.2 AA를 만족하는 Carbon Web Components 기반 키오스크/점장 UI를 제공한다.
- AWS 서울 리전에 암호화·비공개·백업 가능한 관리형 배포와 복원/사고/권한/요율갱신/파기 런북을 제공한다.
### Must NOT have (guardrails, anti-slop, scope boundaries)
- JWT, sessionStorage/localStorage 토큰, refresh token, 공개 API, SPA, 마이크로서비스를 만들지 않는다.
- 생체인식, GPS 추적, 주민등록번호·건강정보 저장, 직원명 노출형 파일명, 직원 명단 열거형 PIN 화면을 만들지 않는다.
- 급여 이체, 세금 신고, 공단 제출, 이메일 발송, 직원 급여 포털, 본사/다점포/멀티테넌시, 오프라인 펀치 큐를 만들지 않는다.
- 법적 적용 여부를 시스템이 단정하지 않는다. 명시 입력으로 경고·예상값만 만들고 점장이 적용 여부와 사유를 확정한다.
- 원본 강혜령/현희 파일, 그 안의 개인정보, `B8*0.2`, `TODAY()` 등 샘플 수식을 커밋·이미지 포함·서비스하지 않는다.
- 원시 펀치나 닫힌 스냅샷을 수정·삭제하지 않으며, 증거 없는 고정 휴게시간을 자동 차감하지 않는다.
- v1에서 자동 산정하는 지급항목은 기본급과 확정된 주휴수당뿐이다. 상여·연장·야간·휴일·기타 지급과 세금/기타 공제는 점장 최종 입력 및 계산근거 기록 범위로 제한한다.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD. `pytest`/`pytest-django`와 실제 PostgreSQL 통합 테스트로 도메인·권한·동시성을 먼저 실패시킨 뒤 구현하고, Playwright Chromium + axe-core로 실제 화면 흐름을 검증한다.
- 정적/배포 게이트: `ruff`, `basedpyright`, `Biome`, `tsc --noEmit`, `python manage.py check --deploy`, migration drift, `pip-audit`, `bun audit`, Docker healthcheck, Terraform validate.
- 산출물 게이트: openpyxl/XML 단언, LibreOffice headless PDF 변환, 한 페이지 너비·오류 셀·PII·휘발성 수식 검사, 합성 golden 이미지 diff.
- 시각 게이트: 375/768/1280px, 한국어 장문, 200% 확대, 키보드 전용, reduced-motion, 명암/비색상 상태, axe serious/critical 0건, 실제 Chromium Lighthouse 모바일·데스크톱 전 카테고리 100.
- Evidence: `<attemptDir>/task-<N>-paris-baguette-payroll-automation.*` (`attemptDir`는 `omo ulw-loop status --json`의 `currentAttemptDir`; loop 밖에서는 `.omo/evidence/`). 비밀값·PIN·직원명 등 PII는 증거에서 합성값으로 대체한다.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- Wave 1, 기반 5개: 1(프로젝트), 2(디자인 시스템), 3(핵심 데이터), 4(인증/키오스크 페어링), 5(감사/보존). 2는 1 이후, 3은 1 이후, 4·5는 3 이후 진행한다.
- Wave 2, 도메인 5개: 6(펀치), 7(정정/승인), 8(시간 산정), 9(급여/주휴), 10(보험/공제). 6과 8은 병렬 가능하고, 7은 6 뒤, 9는 7·8 뒤, 10은 3·5 뒤 진행한다.
- Wave 3, 제품화 6개: 11(마감), 12(키오스크 UI), 13(점장 UI), 14(XLSX), 15(통합 품질게이트), 16(배포/운영). 12는 2·4·6 뒤, 13은 2·4·7·9·10 뒤, 11은 7·9·10 뒤, 14는 11 뒤, 15는 11~14 뒤, 16은 5·11·14 뒤 진행한다.
- 각 todo는 구현과 해당 테스트를 함께 커밋한다. 공유 기반 파일 충돌을 피하기 위해 1이 설정/의존성, 2가 `DESIGN.md`·정적 디자인 자산, 3~10이 각 Django 앱, 11~14가 워크플로/화면/내보내기, 15~16이 CI/인프라를 소유한다.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | - | 2, 3 | - |
| 2 | 1 | 12, 13 | 3 |
| 3 | 1 | 4, 5, 6, 8, 10 | 2 |
| 4 | 3 | 12, 13 | 5, 6, 8, 10 |
| 5 | 3 | 10, 16 | 4, 6, 8 |
| 6 | 3 | 7, 12 | 4, 5, 8, 10 |
| 7 | 6 | 9, 11, 13 | 8, 10, 12 |
| 8 | 3 | 9 | 4, 5, 6, 7, 10 |
| 9 | 7, 8 | 11, 13 | 10, 12 |
| 10 | 3, 5 | 11, 13 | 6, 7, 8, 9, 12 |
| 11 | 7, 9, 10 | 14, 15, 16 | 12, 13 |
| 12 | 2, 4, 6 | 15 | 7, 8, 9, 10, 11 |
| 13 | 2, 4, 7, 9, 10 | 15 | 11, 12 |
| 14 | 11 | 15, 16 | 12, 13 |
| 15 | 11, 12, 13, 14 | F1-F4 | 16 |
| 16 | 5, 11, 14 | F1-F4 | 15 |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. Django/PostgreSQL/Carbon 개발 기반과 반복 가능한 테스트 셸 구성
  What to do / Must NOT do: Python 3.13, Django 5.2 LTS 최신 패치, PostgreSQL 18 최신 마이너, `uv`, `openpyxl`, 서버 렌더링 템플릿, Bun으로 번들한 `@carbon/web-components`, Docker Compose 로컬 DB를 구성한다. 설정은 `config/settings/{base,local,test,production}.py`로 분리하고 `/health/live`, `/health/ready`를 만든다. `pyproject.toml`, `manage.py`, `package.json`, `bun.lock`, `Dockerfile`, `compose.yaml`, `.env.example`, `config/`, `tests/smoke/`를 이 todo가 소유한다. 먼저 부팅/DB 연결 실패 테스트를 작성한다. 비밀값을 커밋하거나 CDN·SQLite 운영경로·SPA 프레임워크·불필요한 API 레이어를 추가하지 않는다.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2, 3
  References (executor has NO interview context - be exhaustive): https://www.djangoproject.com/download/ ; https://docs.djangoproject.com/en/5.2/releases/5.2/ ; https://www.postgresql.org/support/versioning/ ; https://carbondesignsystem.com/developing/web-components-tutorial/overview/
  Acceptance criteria (agent-executable): `uv sync --all-groups`; `bun install --frozen-lockfile`; `docker compose up -d db`; `uv run python manage.py migrate --check`; `uv run python manage.py check`; `uv run pytest tests/smoke -q`; `bun run build`; 컨테이너 안의 `/health/ready`가 DB 정상 시 200, DB 중단 시 503이고 응답에 비밀/스택이 없어야 한다.
  QA scenarios (name the exact tool + invocation): happy - `docker compose up --build -d` 후 Playwright `request.get('/health/ready')` 200을 캡처. failure - DB 컨테이너를 중지한 테스트 프로필에서 readiness 503/liveness 200을 확인. Evidence `<attemptDir>/task-1-paris-baguette-payroll-automation.{log,json}`
  Commit: Y | `chore(scaffold): establish Django PostgreSQL application shell`

- [ ] 2. Carbon 기반 운영형 디자인 시스템과 화면 토폴로지 확정
  What to do / Must NOT do: frontend 스킬 절차에 따라 실제 운영 대시보드/키오스크 화면 연구를 `docs/design-research.md`에 URL·관찰·채택/배제 사유로 남기고, imagegen으로 2~3개 합성 개념안을 만든 뒤 하나를 선택한다. 루트 `DESIGN.md`에 색·타이포·간격·레이어·상태·포커스·터치·반응형 토큰과 키오스크 full-screen cover, 점장 fixed-sidenav/scroll-body shell을 결정한다. `assets/styles/{tokens,app}.css`, `assets/ts/app.ts`, `templates/design-system/showcase.html`, `tests/e2e/design-system.spec.ts`를 소유한다. Carbon Web Components를 로컬 번들하고 한국어/CJK, 375/768/1280, 200% 확대, reduced motion, visible focus, 44x44 터치 타깃을 적용한다. 원본 엑셀을 화면 배경 이미지로 쓰거나 회사 로고/브랜드 자산을 임의 복제하지 않는다.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 12, 13
  References (executor has NO interview context - be exhaustive): https://carbondesignsystem.com/developing/get-started/ ; https://carbondesignsystem.com/elements/color/overview/ ; https://www.w3.org/WAI/WCAG22/quickref/ ; planned `DESIGN.md`; planned `docs/design-research.md`
  Acceptance criteria (agent-executable): `bun run build`; `bun run biome check assets tests/e2e`; `bun run tsc --noEmit`; `bun run test:e2e -- tests/e2e/design-system.spec.ts --project=chromium`; 테스트는 네 핵심 페르소나(공유 태블릿 급한 직원, 월마감 점장, 저시력/키보드 사용자, 한 손 사용 제약)를 명시하고 세 viewport/200% zoom에서 overflow 0, focus 표시, target 44x44 이상, axe serious/critical 0을 단언한다.
  QA scenarios (name the exact tool + invocation): happy - Playwright로 showcase의 폼/테이블/상태/모달/토스트를 키보드만으로 순회하고 스크린샷 비교. failure - 한국어 2배 장문·오류상태·reduced-motion을 주입해 잘림/색상만 의존/포커스 손실이 없음을 확인. Evidence `<attemptDir>/task-2-paris-baguette-payroll-automation.{png,json,md}`
  Commit: Y | `feat(design): define accessible kiosk and manager design system`

- [ ] 3. 단일 매장·직원·권한·보상 프로필·유효기간 정책 모델링
  What to do / Must NOT do: `apps/core/`, `apps/identity/`, `apps/payroll/models/`, 해당 migrations/tests를 소유한다. 한 법적 사용자/한 매장만 두고 `AccountRole={EMPLOYEE,MANAGER}`와 `CompensationProfile={GENERAL,MANAGER}`를 분리한다. 직원코드, 표시명, 입사/퇴사일, 미성년 여부, 계약 주간(Monday-Sunday), 주휴일, 사업장 상시근로자 구간, 통상근로자 기준일수, 근무요일/소정시간, 시급, 휴게정책, 주휴/보험 적용 결정과 출처를 유효기간 기반으로 저장한다. 동일 직원·항목의 기간 중첩을 PostgreSQL exclusion/constraint로 막고 모든 금액은 integer KRW, 계산은 `Decimal`을 사용한다. GENERAL은 주휴/보험 off, MANAGER는 on인 생성 기본값만 제공하고 역할이 법적 자격을 확정하지 않게 한다. 주민번호·주소·건강정보·다점포 tenant key는 넣지 않는다.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 4, 5, 6, 8, 10
  References (executor has NO interview context - be exhaustive): https://www.law.go.kr/LSW/lsInfoP.do?ancNo=21373&ancYd=20260219&efYd=20260820&lsiSeq=283457 ; https://1350.moel.go.kr/rtmview.do?id=1000059852 ; planned `apps/identity/models.py`; planned `apps/payroll/models/policies.py`
  Acceptance criteria (agent-executable): 먼저 중첩 정책·역할/보상 혼동·필수 사실 누락 실패 테스트를 작성한다. `uv run pytest tests/identity tests/payroll/test_policy_models.py -q`; `uv run python manage.py makemigrations --check --dry-run`; PostgreSQL에서 인접 기간은 허용, 하루라도 겹치면 `IntegrityError`; MANAGER 권한+GENERAL 보상 조합과 EMPLOYEE 권한+MANAGER 보상 조합 모두 가능해야 한다.
  QA scenarios (name the exact tool + invocation): happy - synthetic 직원 두 명을 만들고 기본값 및 2026-01/2026-07 시급 변경을 정확히 조회. failure - 겹치는 시급/스케줄, 퇴사 전 입사, 이름을 파일식별자로 쓰는 입력을 거부. Evidence `<attemptDir>/task-3-paris-baguette-payroll-automation.{log,json}`
  Commit: Y | `feat(domain): add employees roles and effective pay policies`

- [ ] 4. 서버 세션·점장 MFA·직원 PIN·키오스크 페어링 보안 구현
  What to do / Must NOT do: `apps/identity/auth/`, `apps/devices/`, 관련 views/forms/templates/tests를 소유한다. 점장은 Django 계정+Argon2id+필수 TOTP로 로그인하고 민감 설정/내보내기에서 재인증한다. TOTP seed는 애플리케이션 키로 암호화하고 recovery code는 단방향 hash한다. 세션은 DB 저장 opaque ID와 `__Host-` Secure/HttpOnly/SameSite=Lax cookie, CSRF, 로그인 시 rotation, idle 15분/absolute 8시간으로 한다. 직원은 등록 태블릿에서 직원코드+암호학적으로 생성한 6자리 PIN을 사용하고 Argon2id hash만 저장한다. 직원/기기별 rate limit, 일정 지연, 열거 방지 동일 응답, 점장 PIN reset을 제공한다. 페어링은 일회성 단기 코드와 폐기 가능한 device secret를 발급하고 서버에는 hash만, 기기에는 `__Host-kiosk` Secure/HttpOnly/SameSite=Strict cookie만 둔다. 직원 인증 세션은 한 action 뒤 폐기한다. JWT·refresh token·local/session storage 토큰·공유 직원 세션을 만들지 않는다.
  Parallelization: Wave 1 | Blocked by: 3 | Blocks: 12, 13
  References (executor has NO interview context - be exhaustive): https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html ; https://docs.djangoproject.com/en/5.2/topics/auth/passwords/ ; planned routes `/manager/login/`, `/manager/mfa/`, `/manager/devices/pair/`, `/kiosk/activate/`, `/kiosk/unlock/`
  Acceptance criteria (agent-executable): `uv run pytest tests/security/test_sessions.py tests/identity/test_manager_mfa.py tests/devices/test_pairing.py tests/identity/test_pin_auth.py -q`; Set-Cookie 단언은 Secure/HttpOnly/SameSite/host-only를 확인하고 CSRF 없음, 만료 세션, 재사용 pairing code, 폐기 device, 10회 PIN 실패, 다른 직원 객체 접근이 모두 차단되어야 한다. 저장소 전체 `rg -n "localStorage|sessionStorage|refresh[_-]?token|JWT"` 결과가 설계 문서의 금지 설명 외 0건이어야 한다.
  QA scenarios (name the exact tool + invocation): happy - Playwright에서 점장 password→TOTP→재인증과 기기 pair→직원 unlock을 실제 쿠키로 수행. failure - PIN/직원코드 오류가 존재 여부를 구분하지 않고 rate-limit되며 pair code 재사용/CSRF POST가 403인지 확인. Evidence `<attemptDir>/task-4-paris-baguette-payroll-automation.{har,json,png}`
  Commit: Y | `feat(auth): secure manager and paired kiosk access`

- [ ] 5. 불변 감사로그·개인정보 최소화·보존/파기 제어 구현
  What to do / Must NOT do: `apps/auditlog/`, 공통 authorization/log-redaction middleware, retention commands/tests를 소유한다. actor/time/action/subject opaque ID/result/request ID와 before/after digest를 append-only로 기록하고 관리자 UI·서비스 양쪽에 객체 단위 권한을 강제한다. 급여/근태/정정 증거 3년 이상, 관리 접근기록 1년 이상을 보존하며 legal hold, 만료 후보 dry-run, 승인된 파기, 백업 만료 후 완료 기록을 지원한다. 앱 로그에서 이름·PIN·TOTP·급여액·세션을 구조적으로 redact하고 전송/DB/백업 암호화를 운영 설정으로 강제한다. 일반 ORM update/delete로 감사기록을 바꾸거나 원본 XLSX를 등록 자산으로 만들지 않는다.
  Parallelization: Wave 1 | Blocked by: 3 | Blocks: 10, 16
  References (executor has NO interview context - be exhaustive): https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1033215737 ; https://www.law.go.kr/LSW/admRulSideInfoP.do?admRulSeq=2100000281400&chrClsCd=010201&dashNo=&docCls=jo&joBrNo=00&joNo=0008&urlMode=admRulScJoRltInfoR ; https://www.law.go.kr/LSW/lsLawLinkInfo.do?chrClsCd=010202&lsJoLnkSeq=900079401 ; https://law.go.kr/LSW/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1012792795
  Acceptance criteria (agent-executable): `uv run pytest tests/auditlog tests/security/test_object_authorization.py tests/security/test_log_redaction.py tests/core/test_retention.py -q`; DB trigger/권한으로 audit UPDATE/DELETE가 실패하고 legal hold 대상은 파기되지 않으며 dry-run은 쓰기 0건, 확정 파기는 synthetic 만료 데이터와 파기 감사만 남겨야 한다.
  QA scenarios (name the exact tool + invocation): happy - 합성 직원의 조회/수정/내보내기/파기를 수행하고 actor-result chain을 검증. failure - 일반 직원·폐기 기기·권한 없는 점장 객체 ID 조작과 audit mutation을 거부하고 로그 grep에 합성 PII가 없음을 확인. Evidence `<attemptDir>/task-5-paris-baguette-payroll-automation.{log,json}`
  Commit: Y | `feat(audit): enforce privacy retention and immutable access records`

- [ ] 6. 동시성 안전한 출퇴근·휴게 이벤트 상태기계 구현
  What to do / Must NOT do: `apps/attendance/models.py`, `apps/attendance/services/punches.py`, kiosk punch views/forms와 PostgreSQL 통합 테스트를 소유한다. 이벤트는 `CLOCK_IN→BREAK_START↔BREAK_END→CLOCK_OUT`의 append-only 순서, 서버의 Asia/Seoul timestamp, 기기 ID, idempotency key를 기록한다. 직원당 열린 shift 하나를 DB constraint/transaction lock으로 보장하고 동시 double tap/재전송은 이벤트 하나만 만든다. 클라이언트 시간은 표시만 하며 GPS를 저장하지 않는다. 네트워크 장애 시 브라우저 큐/뒤늦은 원시 펀치를 만들지 않고 점장 정정 안내로 보낸다.
  Parallelization: Wave 2 | Blocked by: 3 | Blocks: 7, 12
  References (executor has NO interview context - be exhaustive): planned `apps/attendance/models.py`; planned `apps/attendance/services/punches.py`; planned POST `/kiosk/punch/`; database transaction guidance https://docs.djangoproject.com/en/5.2/topics/db/transactions/
  Acceptance criteria (agent-executable): 상태전이 표를 먼저 parameterized failing test로 작성한다. `uv run pytest tests/attendance/test_state_machine.py tests/attendance/test_punch_concurrency.py -q`; 실제 PostgreSQL에서 20개 동시 동일 POST는 1 event/1 open shift, 서로 다른 CLOCK_OUT 경쟁도 하나만 성공해야 하고 잘못된 전이는 명시 오류 코드로 남아야 한다.
  QA scenarios (name the exact tool + invocation): happy - pair된 기기/PIN으로 출근→휴게→복귀→퇴근하고 서버시각·상태를 확인. failure - double click, 퇴근부터 시작, 미등록 기기, 네트워크 차단 후 재연결을 시험해 중복/오프라인 이벤트가 없음을 확인. Evidence `<attemptDir>/task-6-paris-baguette-payroll-automation.{log,json,har}`
  Commit: Y | `feat(attendance): record idempotent server-authoritative punches`

- [ ] 7. 직원 정정요청과 점장 정정·예외검토·근태승인 구현
  What to do / Must NOT do: `apps/attendance/services/corrections.py`, `apps/attendance/services/approvals.py`, 관련 views/forms/tests를 소유한다. 직원은 PIN 재확인 후 해당 shift의 정정요청 사유만 제출할 수 있고 급여 이력/직원목록은 보지 못한다. 점장은 open/missed/invalid break/스케줄 불일치 queue에서 원본을 참조하는 superseding correction을 작성하며 before/after, actor, reason, evidence note, timestamp를 남긴다. 승인 단위는 shift이고 수정 시 기존 승인은 무효화한다. 원시 event UPDATE/DELETE, 이유 없는 수정, 자기 점포 밖 ID 접근은 금지한다.
  Parallelization: Wave 2 | Blocked by: 6 | Blocks: 9, 11, 13
  References (executor has NO interview context - be exhaustive): planned `apps/attendance/services/corrections.py`; planned `apps/attendance/services/approvals.py`; planned routes `/kiosk/corrections/new/`, `/manager/attendance/exceptions/`, `/manager/attendance/shifts/<id>/`
  Acceptance criteria (agent-executable): `uv run pytest tests/attendance/test_corrections.py tests/attendance/test_approvals.py tests/security/test_attendance_idor.py -q`; 원본 hash는 정정 전후 동일하고 correction chain만 증가, 수정 후 승인상태는 pending, 이유 공백/다른 직원 요청/재사용 form은 거부되어야 한다.
  QA scenarios (name the exact tool + invocation): happy - 직원 missed-punch 요청→점장 보정→승인 흐름을 Playwright로 완료. failure - 승인 후 새 정정, 동시 두 점장 승인, URL ID 변조를 실행해 stale-write/권한 오류와 감사로그를 확인. Evidence `<attemptDir>/task-7-paris-baguette-payroll-automation.{png,json,log}`
  Commit: Y | `feat(attendance): add audited correction and approval workflow`

- [ ] 8. 스케줄·휴게·야간·경계 분할 기반 지급시간 산정 구현
  What to do / Must NOT do: `apps/attendance/services/time_calculation/`과 golden fixtures를 소유한다. 원시 초 단위 시각을 반올림하지 않고 `Decimal` 분/시간으로 계산하며 자정, 시급, 스케줄, 휴게정책, 입퇴사 경계에서 구간을 분할한다. 근로주는 월~일, 급여기간은 Asia/Seoul 달력월로 고정한다. 기록된 BREAK 구간 또는 점장 승인 휴게만 무급으로 빼고 증거 없는 예정휴게는 review blocker로 만든다. overnight, 월경계, 주경계, mid-shift rate change, 다중 shift, 무급휴가를 결정론적으로 처리한다. interval/day 단위 금액 반올림을 하지 않는다.
  Parallelization: Wave 2 | Blocked by: 3 | Blocks: 9
  References (executor has NO interview context - be exhaustive): planned `apps/attendance/services/time_calculation/`; planned `tests/fixtures/time_calculation/`; timezone rule `Asia/Seoul`; https://www.law.go.kr/LSW/flDownload.do?bylClsCd=110201&flSeq=150840429&gubun=
  Acceptance criteria (agent-executable): `uv run pytest tests/attendance/test_time_calculation.py -q`; fixture는 30초 단위 fractional minute, 23:30~00:30, 월말 일요일~월초 월요일, 중간 시급변경, 휴게누락, 입퇴사 중간월을 포함한다. 구간 합계는 원시 지속시간-승인휴게와 정확히 같고 입력 순서와 무관해야 한다.
  QA scenarios (name the exact tool + invocation): happy - 2026-07-31 야간 shift를 다음 달과 규칙버전으로 정확히 분할. failure - 휴게 START만 있음, open shift, 겹치는 correction은 계산하지 않고 명시 blocker code를 반환. Evidence `<attemptDir>/task-8-paris-baguette-payroll-automation.{json,log}`
  Commit: Y | `feat(attendance): calculate payable time across policy boundaries`

- [ ] 9. 기본급·주휴 경고/확정·기타 지급 입력 급여엔진 구현
  What to do / Must NOT do: `apps/payroll/services/earnings/`, calculation explanation types, fixtures/tests를 소유한다. 기본급은 승인 지급시간×해당 시점 시급을 `Decimal`로 합산하고 중간 반올림 없이 양수 지급항목 끝에서 KRW `ROUND_CEILING`한다. 음수 조정은 점장 별도 항목/사유로 저장하고 자동 ceiling하지 않는다. 주휴는 4주 평균 주 소정시간 15시간 이상, 소정근로일 개근, 고용관계, 주휴일·주휴시간의 입력으로 warning candidate를 만들되 점장이 `APPLICABLE/NOT_APPLICABLE`와 사유를 확정한다. 주휴시간 제안은 통상 근로형태의 1일 소정시간 또는 단시간근로자의 `4주 소정시간 ÷ 같은 기간 통상근로자 총 소정근로일수`이며 점장 확인값×통상시급으로 주별 산정한다. 주휴는 설정한 유급주휴일이 속한 월에 귀속하고 월경계 주가 완결되지 않으면 마감을 막는다. GENERAL off/MANAGER on은 기본값일 뿐이며 충돌 warning 미해결을 차단한다. `base*20%`를 쓰지 않는다. 상여·연장·야간·휴일·기타 지급은 점장 최종 금액과 시간/산식 설명 입력만 받아 자동 산정하지 않는다.
  Parallelization: Wave 2 | Blocked by: 7, 8 | Blocks: 11, 13
  References (executor has NO interview context - be exhaustive): https://1350.moel.go.kr/rtmview.do?id=1000059852 ; https://1350.moel.go.kr/rtmview.do?id=1000074928 ; https://www.law.go.kr/LSW/flDownload.do?bylClsCd=110201&flSeq=150840429&gubun= ; source workbook anti-reference `C:\파리바겟\급여명세서.현희.xlsx` SHA-256 `244B103D6D04B6A5FA35EC8D81807FB41C262B23876116AC617ACB813CC1DB27`
  Acceptance criteria (agent-executable): `uv run pytest tests/payroll/test_base_pay.py tests/payroll/test_weekly_allowance.py tests/payroll/test_earnings_rounding.py -q`; 14.99/15.00시간 경계, 개근/결근, 일반/매니저 기본값, 불규칙/단시간, 입퇴사, 월경계, 0.5원, fractional minute, 음수조정을 모두 golden 값과 비교한다. 코드/생성 XLSX에 `0.2` 또는 주휴=`base*` 규칙이 없어야 한다.
  QA scenarios (name the exact tool + invocation): happy - 합성 MANAGER 1명과 GENERAL 1명의 preview에서 각 기본값과 점장 확정 결과/계산설명을 확인. failure - 필수 계약사실 누락, 경고와 반대되는 결정을 사유 없이 저장, 미완결 월경계 주를 close-ready로 표시하지 않음을 확인. Evidence `<attemptDir>/task-9-paris-baguette-payroll-automation.{json,log}`
  Commit: Y | `feat(payroll): calculate base pay and manager-confirmed weekly allowance`

- [ ] 10. 4대보험 예상·기관고지 대사와 수동 세금/공제 구현
  What to do / Must NOT do: `apps/payroll/services/deductions/`, `apps/payroll/data/insurance_rates/`, reconciliation models/forms/tests를 소유한다. 국민연금·건강보험·장기요양·고용보험 각각 `NOT_APPLICABLE|ESTIMATED|RECONCILED` 상태, 공식 출처 URL/공표일/시행일, 보수기준, rate/version, 공식별 반올림, 예상액, 최종액, 차이, 점장/사유를 저장한다. 초기 2026 golden rate/계산 사례는 공식 자료에서 수동 검증해 버전 파일로 고정하고 runtime 외부 호출은 하지 않는다. close에는 네 항목 모두 점장 최종상태가 필요하다. 산재보험은 employer-only로 별도 참고만 저장하고 직원 공제·명세서 D열에서 제외한다. 소득세·지방소득세·노조·저축·연말정산·기타는 integer KRW 최종 입력만 합산하고 세금 계산/신고를 하지 않는다.
  Parallelization: Wave 2 | Blocked by: 3, 5 | Blocks: 11, 13
  References (executor has NO interview context - be exhaustive): https://edi.nhis.or.kr/portal/images/popup/20251204_pop01longdesc.html ; https://www.nps.or.kr/pnsinfo/ntpsklg/getOHAF0104M0.do ; planned `apps/payroll/data/insurance_rates/2026.json`; source rows `급여명세서.현희.xlsx` D8:D16
  Acceptance criteria (agent-executable): `uv run pytest tests/payroll/test_insurance_estimates.py tests/payroll/test_insurance_reconciliation.py tests/payroll/test_manual_deductions.py -q`; 공식 golden fixtures와 component별 exact match, rate 시행일 경계, 미가입, estimate/final variance, 음수/소수 공제 거부, 산재보험 순공제 제외, 네 상태 미확정 close blocker를 검증한다.
  QA scenarios (name the exact tool + invocation): happy - versioned 2026 rate로 예상→기관 고지액 입력→차이/사유→RECONCILED. failure - 출처 없는 rate, 과거 snapshot rate 변조, ESTIMATED 상태 마감, 산재를 직원공제에 넣는 요청을 거부. Evidence `<attemptDir>/task-10-paris-baguette-payroll-automation.{json,log}`
  Commit: Y | `feat(payroll): reconcile versioned insurance and manual deductions`

- [ ] 11. 검증 차단형 월마감·재오픈·불변 급여 스냅샷 구현
  What to do / Must NOT do: `apps/payroll/services/close.py`, snapshot/revision models, `prepare_payroll_periods` idempotent command, preview/close/reopen endpoints와 동시성 테스트를 소유한다. Asia/Seoul 매월 1일 이전 달의 DRAFT를 자동 준비해 점장 dashboard에 표시하되 승인·close는 점장만 한다. close 전 open/missed/unaligned shift, 미승인 정정, 휴게 검토, 누락 계약사실, 주휴 결정, 월경계 주, 보험 최종상태, 음수 실수령을 모두 blocker로 반환한다. close는 직원별 resolved event/correction IDs, schedule/rate/rule IDs, 입력값, 계산설명, 항목값, gross/deduction/net, content checksum을 한 transaction에서 불변 snapshot으로 복사한다. 중복/동시 prepare/close는 각각 한 period/version만 만든다. reopen은 사유와 원 snapshot 링크가 있는 새 open revision을 만들고, reclose는 `supersedes_id`를 가진 새 snapshot을 만든다. 이전 snapshot/checksum/export는 수정·삭제하지 않고 기본 조회/내보내기만 최신 버전을 가리킨다.
  Parallelization: Wave 3 | Blocked by: 7, 9, 10 | Blocks: 14, 15, 16
  References (executor has NO interview context - be exhaustive): planned `apps/payroll/services/close.py`; planned routes `/manager/payroll/<YYYY-MM>/preview/`, `/close/`, `/reopen/`; wage statement duty https://www.law.go.kr/LSW/lsInfoP.do?chrClsCd=010202&efYd=20251023&joNo=002300&lsiSeq=265959&urlMode=lsInfoP
  Acceptance criteria (agent-executable): `uv run pytest tests/payroll/test_period_preparation.py tests/payroll/test_close.py tests/payroll/test_close_concurrency.py tests/payroll/test_reopen.py -q`; 매월 1일 command 반복/동시 실행이 이전 달 DRAFT 하나만 만들고, 20개 동시 close가 snapshot/version 하나만 만든다. reopen/reclose 후 v1/v2 checksum과 계산값이 모두 조회 가능하며 latest는 v2여야 한다. snapshot 테이블 UPDATE/DELETE와 과거 정책변경에 따른 재계산 변조가 DB 수준에서 실패해야 한다.
  QA scenarios (name the exact tool + invocation): happy - 승인된 synthetic 2026-07 월을 preview→close→reopen(reason)→수정→reclose하고 버전 비교. failure - open shift, 미대사 보험, 음수 net, stale preview checksum, 이유 없는 reopen을 각각 거부하고 blocker code를 표시. Evidence `<attemptDir>/task-11-paris-baguette-payroll-automation.{json,log}`
  Commit: Y | `feat(payroll): close immutable versioned payroll snapshots`

- [ ] 12. 공유 태블릿용 한국어 키오스크 화면 완성
  What to do / Must NOT do: `templates/kiosk/`, kiosk-specific CSS/TS, `tests/e2e/kiosk.spec.ts`를 소유한다. 화면상태를 기기 페어링, 잠금, 직원코드+PIN, 현재 가능한 단일 punch action, 휴게상태, 성공 확인, 정정요청, 네트워크 실패로 제한한다. 매 action 후 합성 이름 최소 표시와 함께 3초 이내 자동 잠금/세션 정리를 하고 뒤로가기·새로고침에도 타 직원 정보가 남지 않게 한다. 터치 44x44, 큰 한국어 텍스트, focus, screen-reader live region을 제공한다. 직원목록/급여내역/관리기능/오프라인 큐를 노출하지 않는다.
  Parallelization: Wave 3 | Blocked by: 2, 4, 6 | Blocks: 15
  References (executor has NO interview context - be exhaustive): planned `DESIGN.md`; planned `templates/kiosk/`; planned `tests/e2e/kiosk.spec.ts`; https://www.w3.org/WAI/WCAG22/quickref/
  Acceptance criteria (agent-executable): `bun run test:e2e -- tests/e2e/kiosk.spec.ts --project=chromium`; 375/768/1280, touch/keyboard, 200% zoom에서 모든 상태를 통과하고 axe serious/critical 0, 성공 후 PIN/이름 DOM·history·storage 0, local/session storage key 0을 단언한다.
  QA scenarios (name the exact tool + invocation): happy - 페어링→출근→잠금→휴게→잠금→퇴근 전체를 실제 Chromium으로 실행. failure - 잘못된 PIN, rate limit, device revoke, double tap, network abort를 실행해 열거/중복/정보잔류 없이 복구 안내를 확인. Evidence `<attemptDir>/task-12-paris-baguette-payroll-automation.{png,webm,json}`
  Commit: Y | `feat(kiosk): deliver private touch-first attendance clock`

- [ ] 13. 점장용 근태·정책·급여·감사 운영 화면 완성
  What to do / Must NOT do: `templates/manager/`, manager-specific views/forms/CSS/TS, `tests/e2e/manager.spec.ts`를 소유한다. fixed sidenav/scroll-body shell 안에 로그인/MFA, 오늘 현황, 예외 queue, shift 상세 정정/승인, 직원/계약/시급/스케줄/주휴·보험 설정, 급여 preview, 경고 해결, 보험 대사, close/reopen, export 목록, audit history를 제공한다. destructive/sensitive action은 재인증·명시 확인·사유가 필요하고, 표는 모바일에서 의미 있는 카드/스크롤 전략을 쓴다. 분석 대시보드나 다점포 전환기를 만들지 않는다.
  Parallelization: Wave 3 | Blocked by: 2, 4, 7, 9, 10 | Blocks: 15
  References (executor has NO interview context - be exhaustive): planned `DESIGN.md`; planned `templates/manager/`; planned `tests/e2e/manager.spec.ts`; https://carbondesignsystem.com/components/data-table/usage/ ; https://carbondesignsystem.com/components/notification/usage/
  Acceptance criteria (agent-executable): `bun run test:e2e -- tests/e2e/manager.spec.ts --project=chromium`; 세 viewport/200% zoom/keyboard에서 핵심 흐름, CJK 장문, 빈/로딩/오류/권한없음/대량 100명 상태를 검증하고 axe serious/critical 0, fixed shell 이중스크롤 0, focus loss 0이어야 한다.
  QA scenarios (name the exact tool + invocation): happy - 합성 직원 생성→정책설정→예외정정→승인→preview→보험대사→close까지 UI로 수행. failure - 권한 없는 계정, stale form, 미해결 blocker, 재인증 만료, 100행 장문 데이터에서 올바른 오류·포커스 복귀를 확인. Evidence `<attemptDir>/task-13-paris-baguette-payroll-automation.{png,webm,json}`
  Commit: Y | `feat(manager): deliver attendance and payroll operations console`

- [ ] 14. 법정 필드가 보강된 불변 XLSX·요약·ZIP 내보내기 구현
  What to do / Must NOT do: `apps/exports/`, `apps/exports/templates/pay_statement_v1.xlsx`, synthetic golden, tests를 소유한다. 원본 `급여명세서.강혜령.xlsx`(SHA-256 `A0C166A110941D7A2F5BF419535EFC63D8F07561CDB479C041C27A73C59067E1`)와 `급여명세서.현희.xlsx`(SHA-256 `244B103D6D04B6A5FA35EC8D81807FB41C262B23876116AC617ACB813CC1DB27`)는 읽기 전용 시각 참조로만 사용한다. PII 없는 합성 단일 sheet 표준을 만들고 `B1` 귀속월, A3:C4 직원식별/부서·직급, `B8:B23` 지급, `D8:D23` 공제, `B25` 총지급, `D24` 총공제, `D25` 실지급을 정적 integer 값으로 채운다. row 27 이후에 지급일·산정기간·지급항목별 시간/단가/산식·주휴 주별 근거·해당 시 연장/야간/휴일 시간·공제 기준·발급버전/checksum을 명시한다. 한 visible sheet, A:D 명시 width, A4 portrait, print area `A1:D<last-row>`, fit-to-one-page-width를 사용한다. 월별 직원 XLSX, 점장 요약 XLSX, 직원ID 기반 파일명의 ZIP과 manifest(DB+JSON: snapshot/version/checksum/status/requester/expiry)을 만들고 5분 private-object URL로만 내려준다. 직원 sheet에 별도 상태 sheet, 공식/휘발성 수식, sample name, raw template, 이메일 발송을 넣지 않는다.
  Parallelization: Wave 3 | Blocked by: 11 | Blocks: 15, 16
  References (executor has NO interview context - be exhaustive): `C:\파리바겟\급여명세서.강혜령.xlsx`; `C:\파리바겟\급여명세서.현희.xlsx`; https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=02&joNo=0027&lsiSeq=270551&urlMode=lsScJoRltInfoR ; https://www.moel.go.kr/wageCal.do ; planned `apps/exports/templates/pay_statement_v1.xlsx`
  Acceptance criteria (agent-executable): `uv run pytest tests/exports -q`; openpyxl/XML 검사는 `B25=sum(B8:B23)`, `D24=sum(D8:D23)`, `D25=B25-D24`, 모든 금액 integer, formula 0개, 원본 이름/잘못된 월/`TODAY`/`0.2` 0개, visible sheet 1개, pay date/calculation details 존재, snapshot checksum 일치를 단언한다. `soffice --headless --convert-to pdf --outdir <evidence> <xlsx>` 후 한 페이지 너비, `#REF!/#VALUE!` 0, synthetic golden image diff 허용치 이내를 검사한다.
  QA scenarios (name the exact tool + invocation): happy - GENERAL/MANAGER synthetic snapshot 각각과 manager ZIP을 생성해 LibreOffice로 열고 manifest/checksum/총계를 역검증. failure - 다른 직원/이전 만료 URL, 변조 snapshot checksum, 이름 포함 파일명, 원본 workbook 등록 시도를 거부하고 다운로드 감사기록을 확인. Evidence `<attemptDir>/task-14-paris-baguette-payroll-automation.{xlsx,zip,pdf,png,json}`
  Commit: Y | `feat(exports): generate compliant immutable payroll workbooks`

- [ ] 15. 전체 테스트·접근성·보안·성능·산출물 CI 게이트 고정
  What to do / Must NOT do: `.github/workflows/ci.yml`, `scripts/verify.*`, 통합 fixtures, Playwright/Lighthouse/axe 설정을 소유한다. 단일 재현 명령으로 PostgreSQL 도메인/동시성, Django deploy/migration, Python/TS 정적검사, dependency audit, 실제 kiosk/manager E2E, XLSX render, 디자인 diff, 컨테이너 health를 실행한다. Lighthouse는 인증 가능한 synthetic 환경의 실제 Chromium에서 모바일·데스크톱 Performance/Accessibility/Best Practices/SEO 100을 요구한다. flaky retry로 결함을 숨기거나 screenshot baseline을 실패 후 자동 갱신하지 않는다.
  Parallelization: Wave 3 | Blocked by: 11, 12, 13, 14 | Blocks: F1-F4
  References (executor has NO interview context - be exhaustive): planned `.github/workflows/ci.yml`; planned `tests/e2e/`; planned `tests/exports/`; https://developer.chrome.com/docs/lighthouse/overview/ ; https://playwright.dev/docs/test-accessibility
  Acceptance criteria (agent-executable): `uv run ruff check .`; `uv run basedpyright`; `uv run python manage.py makemigrations --check --dry-run`; `uv run python manage.py check --deploy`; `uv run pip-audit`; `bun run biome check .`; `bun run tsc --noEmit`; `bun audit`; `uv run pytest -q`; `bun run test:e2e`; `bun run lighthouse:ci`; `docker compose --profile test run --rm verify`; 모두 exit 0이고 evidence index가 각 gate의 SHA/명령/결과를 가리켜야 한다.
  QA scenarios (name the exact tool + invocation): happy - 새 clone 상당의 빈 cache에서 verify image를 build해 모든 gate 실행. failure - synthetic migration drift, axe violation, workbook volatile formula, duplicate punch race를 하나씩 test fixture로 주입했을 때 해당 gate가 정확한 원인으로 실패한 뒤 fixture 제거 시 green인지 확인. Evidence `<attemptDir>/task-15-paris-baguette-payroll-automation.{log,json,html}`
  Commit: Y | `test(system): enforce end-to-end payroll quality gates`

- [ ] 16. AWS 서울 관리형 배포·비공개 내보내기·백업복원 운영 준비
  What to do / Must NOT do: `infra/terraform/`, production container config, `docs/runbooks/`를 소유한다. 기본 배포는 AWS `ap-northeast-2`의 ECS/Fargate, ALB+ACM, private Multi-AZ RDS PostgreSQL 18 최신 마이너, private S3+KMS, Secrets Manager, CloudWatch로 고정하고 EventBridge Scheduler가 매일 `prepare_payroll_periods` one-off task를 호출하게 한다. DB PITR/백업 35일, RPO≤5분, RTO≤4시간, 분기 자동 복원+smoke, S3 versioning/lifecycle, 최소권한 task role, egress/ingress 제한, audit/backup encryption과 알람을 Terraform으로 선언한다. private export object는 5분 presigned URL만 발급하고 사용자명 대신 직원ID를 쓴다. 배포, 복원, 사고대응, 분기 권한검토, 보험요율 갱신, legal hold/파기 런북을 쓴다. 실제 AWS apply/DNS 변경은 사용자가 제공한 계정·도메인과 별도 실행 승인 전 수행하지 않는다.
  Parallelization: Wave 3 | Blocked by: 5, 11, 14 | Blocks: F1-F4
  References (executor has NO interview context - be exhaustive): https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-versions.html ; https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html ; planned `infra/terraform/`; planned `docs/runbooks/restore.md`
  Acceptance criteria (agent-executable): `terraform -chdir=infra/terraform fmt -check`; `terraform -chdir=infra/terraform init -backend=false`; `terraform -chdir=infra/terraform validate`; `tflint --chdir=infra/terraform`; `checkov -d infra/terraform`; container를 production env로 띄워 `uv run python manage.py check --deploy`; localstack/test-double에서 private object ACL, 5분 expiry, KMS metadata, expired URL 403을 검증한다. restore runbook dry-run은 새 DB 식별자에 복원→migration check→synthetic snapshot checksum→삭제 전 수동 승인 지점까지 자동화하며 RPO/RTO 측정 JSON을 남긴다.
  QA scenarios (name the exact tool + invocation): happy - Terraform plan과 격리된 restore rehearsal/test-double을 실행해 health/로그/알람/export expiry를 확인. failure - public S3/RDS, 암호화 off, broad IAM, 누락 backup, 만료 URL을 정책 테스트가 차단하는지 확인. Evidence `<attemptDir>/task-16-paris-baguette-payroll-automation.{log,json,tfplan}`
  Commit: Y | `ops(aws): define secure Seoul deployment and recovery controls`

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit
  `lazycodex-gate-reviewer`가 현재 SHA에서 Must have/Must NOT have와 todos 1~16의 증거를 양방향 추적해 누락·근거 없는 완료가 0건인지 확인한다. Evidence `<attemptDir>/final-F1-plan-compliance.md`.
- [ ] F2. Code quality and security review
  `lazycodex-code-reviewer`와 security 관점 리뷰가 타입·transaction·IDOR/CSRF/session/PIN·PII·snapshot immutability·dependency·IaC를 실제 diff와 테스트로 검토하고 blocking finding 0건을 승인한다. Evidence `<attemptDir>/final-F2-code-security.md`.
- [ ] F3. Real manual QA
  `lazycodex-qa-executor`가 합성 데이터와 실제 Chromium에서 pair→punch→correction→approval→pay preview→insurance reconcile→close→reopen/reclose→XLSX/ZIP download를 직접 수행하고 LibreOffice 렌더·세 viewport 스크린샷·Lighthouse를 관찰한다. Evidence `<attemptDir>/final-F3-manual-qa/`.
- [ ] F4. Scope and design fidelity
  독립 reviewer가 원본 두 통합문서의 시각적 맥락, `DESIGN.md`, 법정 필드, GENERAL/MANAGER 기본값, 금지범위를 비교해 hard-coded screenshot/PII/raw workbook/hidden extra product가 없고 계획 범위와 일치함을 승인한다. Evidence `<attemptDir>/final-F4-scope-fidelity.md`.

## Commit strategy
- todo별 Conventional Commit을 사용하고 구현+해당 테스트를 같은 atomic commit에 둔다. 공유 기반을 건드려야 하면 소유 todo와 먼저 동기화하고 다른 작업자의 변경을 되돌리지 않는다.
- 원본 `급여명세서.강혜령.xlsx`, `급여명세서.현희.xlsx`, `.env`, DB dump, evidence의 PII, 실제 export는 절대 stage하지 않는다. 커밋 가능한 통합문서는 합성 이름/금액만 가진 sanitized canonical/golden뿐이다.
- Wave 종료마다 현재 SHA에서 `scripts/verify` 축소 게이트를 실행하고, 최종 검증은 모든 commit이 합쳐진 동일 SHA를 기준으로 새로 수행한다.

## Success criteria
- 등록 태블릿에서 직원이 본인 PIN으로 유효한 출퇴근/휴게만 기록하고 double tap·재전송·다른 기기·오프라인에서 중복/위조 이벤트가 생기지 않는다.
- 점장은 원시기록을 보존한 채 정정·승인하며 모든 변경/조회/내보내기가 사유와 감사기록으로 추적된다.
- GENERAL/MANAGER 기본값은 요청대로 작동하되 주휴·보험 법적 적용은 점장 확정이며, 필수 사실/경고/보험 대사/근태 예외가 남으면 월마감이 실패한다.
- 월마감과 재마감의 모든 버전·checksum·계산설명이 재현되고 과거 정책 변경이 닫힌 결과를 바꾸지 않는다.
- 직원별 한 장 XLSX, 점장 요약, ZIP이 법정 식별·지급일·항목·산식·공제 정보를 포함하고 총계가 snapshot과 일치하며 원본 PII/휘발성 수식이 없다.
- 관리자 세션/TOTP, 키오스크 PIN/페어링, 객체권한, CSRF, 보존/파기, 비공개 5분 다운로드, 암호화 백업/복원 검증이 통과한다.
- 모든 Python/TS/DB/E2E/axe/Lighthouse/XLSX/Container/IaC gate가 동일 SHA에서 green이고 F1~F4가 모두 APPROVE한다.
