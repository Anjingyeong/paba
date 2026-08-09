---
slug: paris-baguette-payroll-automation
status: approved-consumed
intent: clear
review_required: false
pending-action: choose start-work or optional dual high-accuracy review
approach: Build a Dockerized Django 5.2 LTS monolith on Python 3.13 and PostgreSQL 18 with database-backed sessions, server-rendered manager pages, bundled Carbon Web Components, a paired in-store kiosk, immutable punch/audit records, versioned pay policies, monthly close snapshots, and normalized XLSX exports derived from the supplied layouts.
---

# Draft: paris-baguette-payroll-automation

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
1. identity-access | employees authenticate to clock only themselves; managers administer, approve, close, and export | active | user request; OWASP Session Management guidance
2. attendance-clock | immutable clock-in/out events record server time and store context | active | user request
3. manager-review | manager resolves missed/incorrect punches with reasons and approves a monthly attendance ledger | active | user request
4. payroll-close | approved attendance and employee pay policy produce a reproducible monthly payroll snapshot | active | user request; Labor Standards Act Articles 18, 48, 55
5. statement-export | the supplied workbook layout is normalized, populated per employee/month, and exported with a manager summary | active | C:\파리바겟\급여명세서.강혜령.xlsx and C:\파리바겟\급여명세서.현희.xlsx
6. administration-protection | employee/pay settings, audit trail, retention, backup, and role controls protect payroll data | active | PIPA Articles 24-2, 29; user request

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->
auth architecture | same-origin server-side opaque session in Secure/HttpOnly/SameSite cookie; no JWT in sessionStorage and no refresh token | smaller attack surface for one internal web app; OWASP guidance | yes
clock authority | server timestamp is authoritative; client clock is display-only | prevents browser clock tampering | yes
payroll finality | monthly close creates an immutable versioned snapshot; reopening requires manager reason and audit entry | reproducible exports and dispute evidence | yes
insurance automation | store manager-verified deduction inputs/amounts with effective dates and sources; do not auto-decide statutory eligibility or annual settlement | eligibility/rates vary by worker and period | yes
sensitive identifiers | use internal employee IDs; do not use resident registration numbers or health data | data minimization and PIPA restrictions | yes
timezone/currency | Asia/Seoul calendar boundaries and KRW integer arithmetic with explicit rounding rules from the supplied form | store is in Korea; avoids floating-point payroll drift | yes
template normalization | use both workbooks as visual references but generate a clean canonical template with dynamic period/employee fields, computed totals, and no sample PII | the general file contains manager data and stale month text; neither file has complete deductions/net-pay formulas | yes
base wage | calculate exact approved payable minutes against an employee-specific, effective-dated hourly rate; use rational/decimal arithmetic and round once to KRW at the component boundary with the employee-favorable result on half/fractional won | workbook amounts equal exact hour counts times the official 2025/2026 minimum hourly rates, but rates must remain manager-configurable | yes
break handling | scheduled unpaid break rules live in effective-dated pay policies; the manager resolves exceptions before approval; no silent fixed deduction from every shift | attendance evidence must show payable minutes and prevent underpayment | yes
export package | monthly close produces one immutable XLSX per employee plus a manager-only summary XLSX and ZIP; employee files contain a single period sheet and an issue-status record | avoids stale cumulative tabs and limits disclosure | yes
retention | retain payroll/attendance support records for at least 3 years and administrative access logs for at least 1 year; destruction is logged after the applicable period | Labor Standards Act Article 42 and 2026 PIPA safety standard Article 8 | yes
weekly-pay formula | do not copy the workbook's blanket base-pay-times-20-percent formula; calculate per approved contract schedule and weekly statutory conditions, with a manager warning/override reason | workbook lacks hours, scheduled days, attendance, and eligibility evidence | yes

## Findings (cited - path:lines)
workspace | C:\파리바겟 is a greenfield application workspace with no existing app source, manifest, or tests; both supplied workbooks are present and were inspected | verified 2026-08-09 by root listing, archive inspection, and SHA-256 checks
pay statement duty | Labor Standards Act Article 48 requires a written/electronic statement at wage payment | https://www.law.go.kr/LSW/lsInfoP.do?chrClsCd=010202&efYd=20251023&joNo=002300&lsiSeq=265959&urlMode=lsInfoP
required statement fields | Enforcement Decree Article 27-2 requires employee identifier, pay date, gross pay, component amounts, variable-component calculations including applicable hours, and deduction details | https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=02&joNo=0027&lsiSeq=270551&urlMode=lsScJoRltInfoR
weekly holiday allowance | eligibility is based on statutory conditions including average scheduled weekly hours and attendance, not job title alone | https://1350.moel.go.kr/rtmview.do?id=1000059852
small workplace | the paid weekly-holiday rule applies even below five regular workers; other labor rules can differ by workforce size | https://www.law.go.kr/flDownload.do?flNm=%5B%EB%B3%84%ED%91%9C+1%5D+%EC%83%81%EC%8B%9C+4%EB%AA%85+%EC%9D%B4%ED%95%98%EC%9D%98+%EA%B7%BC%EB%A1%9C%EC%9E%90%EB%A5%BC+%EC%82%AC%EC%9A%A9%ED%95%98%EB%8A%94+%EC%82%AC%EC%97%85+%EB%98%90%EB%8A%94+%EC%82%AC%EC%97%85%EC%9E%A5%EC%97%90+%EC%A0%81%EC%9A%A9%ED%95%98%EB%8A%94+%EB%B2%95+%EA%B7%9C%EC%A0%95%28%EC%A0%9C7%EC%A1%B0+%EA%B4%80%EB%A0%A8%29%0A&flSeq=43334647
four-major-insurance | rates and eligibility vary by effective date, employment pattern, income/hours, and industry; official-source calculations cannot safely be frozen as one formula | https://www.nps.or.kr/pnsinfo/ntpsklg/getOHAF0104M0.do ; https://edi.nhis.or.kr/portal/images/popup/20251204_pop01longdesc.html
privacy/security | payroll and attendance are personal data; PIPA Article 29 requires safeguards and access records; OWASP recommends server-side opaque sessions rather than browser storage for this shape | https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1033215737 ; https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
general workbook | SHA-256 A0C166A110941D7A2F5BF419535EFC63D8F07561CDB479C041C27A73C59067E1; eight sheets 25.05-25.12, all A1:D27, no formulas; every sheet still says employee name Hyunhee and almost every B1 still says May 2025 | C:\파리바겟\급여명세서.강혜령.xlsx
manager workbook | SHA-256 244B103D6D04B6A5FA35EC8D81807FB41C262B23876116AC617ACB813CC1DB27; payroll sheets 25.05-26.01 plus empty Sheet1; formula-bearing examples use B12=B8*0.2 and B25=B8+B12; sheet 26.01 displays July 2026 | C:\파리바겟\급여명세서.현희.xlsx
template fields | period B1; identity headers A3:C4; earnings B8:B12; insurance/tax/other deductions D8:D23; total earnings B25; total deductions D24; net pay D25; no merge ranges, print areas, validations, charts, images, or defined names | direct XLSX archive inspection 2026-08-09
template gaps | deduction values/formulas, deduction total, net pay, attendance hours, scheduled hours/days, hourly rate, insurance bases, and legal weekly-pay eligibility inputs are absent | direct XLSX archive inspection 2026-08-09

## Decisions (with rationale)
classification | Architecture: greenfield product spanning identity, attendance, approval, payroll, export, and operations
intent | CLEAR: endpoint and main workflow are explicit; remaining forks are owner decisions
review | optional at present; legal/payroll risk makes the later dual high-accuracy review recommended
benefit authority | manager role alone configures weekly-holiday allowance and four-insurance treatment for every employee; job title is not the eligibility rule | user selected recommended option
clock channel | a registered in-store tablet is the employee clock channel; each employee uses a personal PIN and the UI returns immediately to the locked screen | user selected recommended option; limits remote punches and shared-session leakage
test strategy | TDD for domain rules, authorization, close/reopen, and export mapping; agent-executed happy/failure QA remains required | user selected recommended option
deployment | managed cloud with private domain, HTTPS, managed relational database, automated encrypted backup, and a registered kiosk device | user selected recommended option
insurance calculation | versioned official rates produce estimates after manager enters eligibility and remuneration bases; manager reconciles and finalizes against institution notices with an audit reason | user selected recommended option
template timing | both exact XLSX files were attached and inspected before plan completion; mappings and defects are evidence-backed | user action plus archive inspection
template role evidence | user identifies Kang Hyeryeong file as general-employee layout and Hyunhee file as manager example; workbook internals do not contain a distinct schema, so role behavior must come from pay-policy data, not separate hard-coded forms | user clarification plus workbook comparison
pay profiles | GENERAL defaults to base hourly pay with weekly/insurance estimates off; MANAGER defaults them on; any employee meeting a statutory-warning condition blocks close until the manager resolves it with an auditable reason | user selected role defaults plus legal warning
authorization separation | account role (EMPLOYEE/MANAGER) is separate from compensation profile (GENERAL/MANAGER) so a manager account does not silently change pay policy | prevents privilege and compensation from being conflated
technology | Python 3.13, Django 5.2 LTS current patch, PostgreSQL 18 current minor, openpyxl, bundled @carbon/web-components, minimal TypeScript/JavaScript asset entry, Docker OCI image | LTS/security support and official framework/design-system sources
frontend direction | greenfield DESIGN.md before screens; IBM Carbon-inspired operational UI, official Carbon Web Components, fixed-sidenav/scroll-body manager shell, full-screen kiosk cover, WCAG 2.2 AA, Korean/CJK and 375/768/1280 content-stress QA | frontend/designpowers routing
personas | rushed employee using a shared touch tablet; manager reviewing exceptions and closing payroll; low-vision/keyboard user; temporary one-hand/situational motor constraint | designpowers inclusive planning requirement
insurance boundary | estimate national pension, health, long-term care, and employment-insurance employee deductions from effective-dated manager inputs; manager reconciles to institution notices; industrial-accident insurance is employer-only and stays off employee deductions | official agency research plus workbook rows D8:D11
tax boundary | income tax, local income tax, union dues, savings, year-end adjustment, and other deductions are manager-entered final amounts; the system totals and reports them but does not invent tax calculations | source workbooks contain labels but no formulas or inputs

## Scope IN
Employee and manager authentication; clock-in/out; missed-punch correction request; manager adjustment/approval with reasons; monthly close; base wage and explicitly configured allowance/deduction calculation; wage ledger/statement generation; Excel export using the supplied template; audit log; backups and restore test; responsive internal web UI.

## Scope OUT (Must NOT have)
No payroll bank transfer, tax filing, agency submission, biometric recognition, continuous GPS tracking, franchise/head-office integration, automatic labor-law eligibility adjudication, client-side JWT/refresh tokens, microservices, public API, or storage of resident registration/health data. Raw source payroll workbooks containing personal data must not be committed, baked into images, or served; only a sanitized canonical template may ship.

## Open questions
None. Any unprovided employee-specific rates, schedules, hire dates, insurance bases, and deduction amounts are manager-entered business data, not implementation decisions.

## Approval gate
status: approved-consumed
approach: Django/PostgreSQL monolith, paired kiosk, manager review, versioned payroll close, sanitized template-based XLSX export, Carbon operational UI, TDD and agent-executed QA.
next action: the completed `.omo/plans/paris-baguette-payroll-automation.md` is the execution source of truth; choose direct start-work or optional dual high-accuracy review. Do not implement in this planner session.
<!-- Approval was received on 2026-08-09; this draft is consumed by the completed plan. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
