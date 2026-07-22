# 📰 한국 뉴스 다이제스트 (Korean News Digest)

주요 뉴스를 **자동 수집**해 매일 아침 **스타일드 HTML 다이제스트** 2종으로 만들어 주는
GitHub Actions 워크플로입니다. (브라우저로 열어도, 이메일로 받아도 그대로 렌더링)

1. **📰 신문 다이제스트** — 조선·동아·중앙·한국·한겨레를 **언론사·섹션별**로 정리.
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

- **자동:** 매일 07:00 KST에 실행됩니다. ⚠️ GitHub는 **기본 브랜치(main)** 에 있는
  스케줄 워크플로만 자동 실행하므로, 자동화를 켜려면 이 워크플로를 `main`에 머지하세요.
- **수동:** 리포지토리 **Actions → Korean News Digest → Run workflow** 로 아무 브랜치에서나
  즉시 실행할 수 있습니다. 결과는 `digests/YYYY-MM-DD.md` 에 커밋되고, 실행 요약(job summary)과
  아티팩트로도 확인할 수 있습니다.

### 2) 로컬 실행

```bash
pip install -r news_digest/requirements.txt
python -m news_digest.main          # 신문  → digests/YYYY-MM-DD.html, digests/latest.html
python -m news_digest.broadcast     # 방송  → digests/broadcast-YYYY-MM-DD.html, digests/broadcast-latest.html
```

환경 변수:

| 변수 | 기본 | 설명 |
|---|---|---|
| `ENRICH` | `1` | `0`이면 요약 없이 헤드라인만 (더 빠름) |
| `RECENCY` | `1d` | 수집 범위 (`2d`, `12h` 등) |
| `OUTPUT_DIR` | `<repo>/digests` | 출력 폴더 |

## 이메일 발송 (jakekim070917@gmail.com)

다이제스트를 이메일로도 받으려면 GitHub 리포 **Settings → Secrets and variables → Actions** 에
아래 2개를 추가하세요. (미설정 시 이메일 단계는 자동으로 건너뛰고, 커밋·아티팩트는 정상 동작)

| 시크릿 | 값 |
|---|---|
| `MAIL_USERNAME` | 발송용 Gmail 주소 (예: `you@gmail.com`) |
| `MAIL_PASSWORD` | Gmail **앱 비밀번호**(16자리) — 2단계 인증 필요, 일반 비번 아님 |

- 앱 비밀번호 발급: Google 계정 → 보안 → 2단계 인증 → **앱 비밀번호**.
- 수신자는 워크플로에 `DIGEST_TO: jakekim070917@gmail.com` 로 지정돼 있습니다. 바꾸려면
  `.github/workflows/news-digest.yml` 의 `DIGEST_TO` 값을 편집하세요.
- 발송은 `smtp.gmail.com:465`(SSL)로 이뤄지며, **HTML 본문**(다이제스트 전문) + `latest.html` 첨부가 포함됩니다.

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
.github/workflows/news-digest.yml   # 매일 07:00 KST 실행 (신문+방송 모두)
```
