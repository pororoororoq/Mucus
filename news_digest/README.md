# 📰 한국 뉴스 다이제스트 (Korean News Digest)

주요 뉴스를 **자동 수집**해 매일 아침 **스타일드 HTML 다이제스트** 2종으로 만들어 주는
GitHub Actions 워크플로입니다. (브라우저로 열어도, 이메일로 받아도 그대로 렌더링)

1. **📰 신문 지면 다이제스트** — 조선·동아·중앙·한국·한겨레의 **네이버 지면보기**를 스크래핑해
   **1면부터 지면(A1면→A2면→…) 편집 순서**로 정리 → 각 신문의 톱기사·편집 우선순위 비교. (`jimyeon.py`)
2. **📺 방송 다이제스트** — SBS 8뉴스·KBS 뉴스9·MBC 뉴스데스크를 **실제 방송 편성 순서**로
   직접 스크래핑(순번·제목·링크, SBS는 섹션칩 포함), YTN은 최신순. `scrape.py` 참고.

## 왜 이렇게 만들었나

Claude Code 웹 세션의 원격 환경은 조직 이그레스 정책으로 네이버/신문사 도메인 접근이
막혀 있습니다. 반면 **GitHub Actions 러너는 오픈 인터넷**이라 뉴스 소스에 자유롭게
접근할 수 있어, 수집 작업을 CI에서 돌리는 구조로 설계했습니다.

## 데이터 소스

| 소스 | 비용 | 키 | 기본값 |
|---|---|---|---|
| **Google 뉴스 RSS** | 무료 | 불필요 | ✅ 기본 (첫 실행부터 동작) |
| **네이버 검색(뉴스) API** | 무료 | 필요 (Client ID/Secret) | 선택 (`naver_api.py`) |

- Google 뉴스 RSS는 `site:<domain> when:1d` 쿼리로 **언론사별·최근 24시간** 기사를 가져오고,
  `사설`·`정치`·`경제` 등 키워드로 섹션을 근사합니다.
- 네이버는 공식 **지면(1면) API가 없습니다.** 진짜 1~3면 지면 순서가 필요하면
  `media.naver.com` 지면보기 스크래핑을 별도로 추가해야 합니다.

## 실행 방법

### 1) GitHub Actions (권장)

두 개의 스케줄 워크플로로 나뉘어 있습니다:

| 워크플로 | 실행 시각(KST) | cron(UTC) | 내용 |
|---|---|---|---|
| `newspaper-digest.yml` | **07:30** | `30 22 * * *` | 📰 신문 지면 표 |
| `broadcast-digest.yml` | **22:00** | `0 13 * * *` | 📺 방송 편성 |

- **자동:** 위 시각에 실행됩니다. ⚠️ GitHub는 **기본 브랜치(main)** 의 스케줄 워크플로만 자동
  실행하므로, 켜려면 `main`에 머지하세요.
- **수동:** **Actions → (워크플로 선택) → Run workflow** 로 즉시 실행 가능. 결과는
  `digests/`에 커밋되고 job summary·아티팩트로도 확인됩니다.

### 2) 로컬 실행

```bash
pip install -r news_digest/requirements.txt
python -m news_digest.jimyeon        # 신문 지면 표 → digests/YYYY-MM-DD.html, digests/latest.html
python -m news_digest.broadcast      # 방송        → digests/broadcast-YYYY-MM-DD.html, digests/broadcast-latest.html
```

환경 변수:

| 변수 | 기본 | 설명 |
|---|---|---|
| `RECENCY` | `1d` | 수집 범위 (`2d`, `12h` 등) |
| `OUTPUT_DIR` | `<repo>/digests` | 출력 폴더 |

## 텔레그램 발송 (권장 · 설정 간단)

이메일보다 훨씬 쉽습니다. 리포 **Settings → Secrets and variables → Actions** 에 2개만:

| 시크릿 | 값 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 **@BotFather** 에서 `/newbot` 으로 만든 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 본인 숫자 chat id (**@userinfobot** 에게 말 걸면 알려줌) |

- 봇에게 먼저 아무 말이나 한 번 보내야(대화 시작) 봇이 메시지를 보낼 수 있습니다.
- 다이제스트는 **HTML 파일 첨부 + 짧은 캡션**으로 전송됩니다(탭하면 표/목록이 열림).
- 두 시크릿이 없으면 텔레그램 단계는 자동으로 건너뜁니다. 이메일과 **병행**해도 됩니다.

## 이메일 발송 (kimphil9@gmail.com)

다이제스트를 이메일로도 받으려면 GitHub 리포 **Settings → Secrets and variables → Actions** 에
아래 2개를 추가하세요. (미설정 시 이메일 단계는 자동으로 건너뛰고, 커밋·아티팩트는 정상 동작)

| 시크릿 | 값 |
|---|---|
| `MAIL_USERNAME` | 발송용 Gmail 주소 (예: `you@gmail.com`) |
| `MAIL_PASSWORD` | Gmail **앱 비밀번호**(16자리) — 2단계 인증 필요, 일반 비번 아님 |

- 앱 비밀번호 발급: Google 계정 → 보안 → 2단계 인증 → **앱 비밀번호**.
- 수신자는 두 워크플로에 `DIGEST_TO: kimphil9@gmail.com` 로 지정돼 있습니다. 바꾸려면
  `.github/workflows/newspaper-digest.yml`·`broadcast-digest.yml` 의 `DIGEST_TO` 값을 편집하세요.
- 발송은 `smtp.gmail.com:465`(SSL)로 이뤄지며, **HTML 본문**(다이제스트 전문) + HTML 첨부가 포함됩니다.
- 신문 지면은 아침 **07:30**, 방송은 밤 **22:00**(저녁뉴스 종료 후)에 각각 발송됩니다.

## (선택) 네이버 검색 API 추가

1. https://developers.naver.com 에서 애플리케이션 등록 → **Client ID / Secret** 발급 (무료).
2. GitHub 리포 **Settings → Secrets and variables → Actions** 에
   `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 추가.
3. 단독 테스트:
   ```bash
   NAVER_CLIENT_ID=... NAVER_CLIENT_SECRET=... python news_digest/naver_api.py 조선일보 사설
   ```

## 커스터마이징

- 신문사·섹션·수집 개수: `news_digest/sources.py` 의 `PAPERS`, `SECTIONS`,
  `MAX_ITEMS_PER_SECTION`, `RECENCY` 를 편집하세요.
- 특정 언론사에서 결과가 없으면 도메인 값(`chosun.com` 등)이나 섹션 키워드를 조정하면 됩니다.

## 구조

```
news_digest/
├─ sources.py     # 신문사·섹션·수집 설정
├─ fetch.py       # RSS 수집·파싱·요약 보강
├─ main.py        # 신문 다이제스트 생성 (digests/*.html)
├─ broadcast.py   # 방송 다이제스트 생성 (digests/broadcast-*.html)
├─ naver_api.py   # (선택) 네이버 검색 API 헬퍼
└─ requirements.txt
.github/workflows/newspaper-digest.yml   # 07:30 KST — 신문 지면
.github/workflows/broadcast-digest.yml   # 22:00 KST — 방송
```
