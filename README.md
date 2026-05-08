# 엘리엇 파동 주식 분석기

ZigZag 알고리즘으로 OHLC 데이터의 피벗을 추출하고, 엘리엇 파동(임펄스 5파 + 조정 ABC) 패턴을
자동 식별/시각화하는 Flask 웹앱입니다.

## 기능

- yfinance 기반 글로벌 시세 (미국·유럽·아시아 주식, ETF, 지수, 암호화폐 등)
- ZigZag 피벗 검출 (민감도 조절 가능)
- 엘리엇 파동 3대 규칙 기반 검증
  - 2파는 1파를 100% 이상 되돌릴 수 없다
  - 3파는 1·3·5파 중 가장 짧을 수 없다
  - 4파의 가격대는 1파의 가격대와 겹칠 수 없다
- 1·3·5파 길이비, 2·4파 되돌림 비율 산출
- 다음 국면(조정 또는 신규 임펄스)에 대한 피보나치 목표가 투영
- Plotly 캔들 차트 + 파동 라벨 + 목표가 레벨 오버레이

## 두 가지 실행 모드

### A. Flask 서버 모드 (권장)

```bash
pip install -r requirements.txt
python app.py
```

브라우저에서 <http://localhost:5000> 접속.

### B. 단독 HTML 모드 (백엔드 불필요)

`standalone.html` 파일을 더블클릭해 브라우저에서 바로 열면 됩니다.
설치/서버 실행이 필요 없습니다.

- **티커 자동 수집** 탭: Yahoo Finance를 공개 CORS 프록시(`corsproxy.io`,
  `allorigins.win`) 경유로 호출. 프록시 가용성에 따라 실패할 수 있습니다.
- **CSV 업로드** 탭: Yahoo Finance Historical Data 등에서 받은 CSV
  (`Date,Open,High,Low,Close,Volume`)를 드래그/선택해 분석. 네트워크 불필요.

## 사용법

1. 티커 입력
   - 미국: `AAPL`, `TSLA`, `MSFT`, `NVDA`
   - 지수: `^GSPC` (S&P 500), `^IXIC` (Nasdaq), `^KS11` (KOSPI)
   - 암호화폐: `BTC-USD`, `ETH-USD`
   - 한국 주식: `005930.KS` (삼성전자), `035420.KS` (네이버)
2. 기간/간격 선택 (yfinance 제약상 시간봉은 최대 730일)
3. ZigZag 민감도(%) 조절
   - 낮을수록 미세한 흐름까지 포착 → 단기 파동
   - 높을수록 큰 흐름의 피벗만 포착 → 중장기 파동
4. **분석** 클릭

## 한계 및 주의

- 엘리엇 파동 카운트는 본질적으로 주관적이며, 동일 차트에서 여러 카운트가 가능합니다.
- 본 도구는 가장 단순한 형태의 임펄스+ABC 패턴만 인식합니다(연장파, 삼각형, 플랫·지그재그
  세부 분류는 미구현).
- 결과는 보조 지표일 뿐, 단독 매매 근거로 사용하지 마십시오.

## 파일 구조

```
.
├── app.py               # Flask 라우트
├── elliott_wave.py      # ZigZag + 파동 검출 + 분석 로직 (Python)
├── standalone.html      # 백엔드 불필요한 단독 HTML 버전 (JS 포팅)
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```
