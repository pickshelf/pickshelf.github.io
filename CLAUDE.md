# pickshelf.github.io

GitHub Pages 정적 사이트(빌드 없음, `.nojekyll`). 쿠팡·아고다·트립닷컴 제휴 링크 모음.
`index.html`(홈) · `travel/` · `living/` · `hotels/` 각각 `index.html` 한 장.

- `inapp.js` — 인스타·스레드·카톡 인앱 브라우저에서 외부 브라우저/제휴 앱으로 넘김. 넘길 때 `utm_source=<앱>` 을 붙여 유입 경로를 남긴다.
- `analytics.js` — GA4(측정 ID `G-VDRYK1K890`). `link_click`(partner·item_no·item_name·link_type·button), `search`(search_term) 이벤트.
- 스크립트 버전(`?v=`)을 올려야 방문자 브라우저가 새 파일을 받는다.

## 방문자 분석 (scripts/ga_report.py)

"pickshelf 분석해줘" 류 요청은 이걸 돌려서 답한다. 읽기 전용.

```bash
pip install google-auth requests
python3 scripts/ga_report.py              # 최근 28일
python3 scripts/ga_report.py --days 7
python3 scripts/ga_report.py --json
```

- GA4 속성 ID `560488821`. 서비스계정 `pickshelf-ga-reader@pickshelf-ga.iam.gserviceaccount.com`(속성 편집자).
- 키는 Claude Code 환경변수 `PICKSHELF_GA_SA_B64`(또는 `_JSON`). trablind·staycat 키(`TRABLIND_*`·`STAYCAT_*`)는 쓰지 않는다 — 여러 저장소가 환경 하나를 공유해서 접두사로 구분한다.
- link_click 맞춤 측정기준 5개는 등록 완료(2026-10-24). 등록 전 클릭은 파트너·상품이 `(not set)` 으로 나온다.
- 봇 세션(헤드리스 브라우저·링크 미리보기 크롤러)은 기본으로 뺀다 — 기준은 스크립트 상단 `BOT_*` 한 곳. `--include-bots` 로 포함.
- 이 저장소는 그대로 공개 웹에 올라가므로 키·비밀값을 커밋하지 말 것.
