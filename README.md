## Overview

### 프로젝트 소개

본 시스템은 **LangChain 기반 멀티 에이전트 아키텍처**를 활용하여 특허를 자동으로 평가하는 AI 시스템입니다. 3개의 전문 에이전트(TechnologyAgent, RightsAgent, MarketAgent)가 협업하여 특허의 기술성, 권리성, 활용성을 정량적·정성적으로 분석하고, 전문가 수준의 평가 보고서를 자동 생성

### 핵심 가치

- **자동화**: 수동 평가 대비 **시간 절약**
- **객관성**: 32개 정량 지표 기반 데이터 중심 평가
- **전문성**: LLM + RAG를 활용한 전문가 수준의 정성 분석
- **일관성**: 표준화된 평가 프레임워크로 평가자 편향 제거

### 평가 프레임워크

```
최종 점수 = (기술성 × 40%) + (권리성 × 35%) + (활용성 × 25%)
```

| 점수 범위 | 등급 | 설명 |
|----------|------|------|
| 95~100 | AAA | 최우수 (혁신적, 강력한 권리, 높은 시장성) |
| 90~94 | AA | 우수 |
| 85~89 | A | 양호 |
| 75~84 | BBB | 보통 상위 |
| 65~74 | BB | 보통 |
| 55~64 | B | 개선 필요 |
| 0~54 | D | 부족 |

---

## Tools

본 시스템에서 사용하는 핵심 도구들입니다.

### 1. PDF Processing

| 도구 | 용도 | 버전 |
|------|------|------|
| **pdfplumber** | PDF 텍스트 추출 | 0.10+ |
| **PyPDF2** | PDF 메타데이터 | 3.0+ |

### 2. RAG (Retrieval-Augmented Generation)

| 도구 | 용도 | 버전 |
|------|------|------|
| **FAISS** | 벡터 데이터베이스 | 1.7+ |
| **OpenAI Embeddings** | 텍스트 임베딩 | text-embedding-3-small |
| **LangChain** | RAG 오케스트레이션 | 0.1.0+ |

### 3. LLM (Large Language Model)

| 도구 | 용도 | 버전 |
|------|------|------|
| **OpenAI GPT-4o-mini** | 정성 평가 | Latest |
| **LangChain** | LLM 체인 관리 | 0.1.0+ |

### 4. Web Search

| 도구 | 용도 | 버전 |
|------|------|------|
| **DuckDuckGo Search** | 실시간 웹 검색 | Latest |

### 5. Document Generation

| 도구 | 용도 | 버전 |
|------|------|------|
| **python-docx** | DOCX 생성 | 1.1+ |
| **matplotlib** | 그래프 생성 | 3.8+ |

---

## Features

### 1. 정량 평가 (32개 지표)

#### 권리성 지표 (X1~X6)
| 지표 | 설명 | 우수 기준 |
|------|------|----------|
| X1 | IPC 코드 수 | ≥ 5개 |
| X2 | 독립항 수 | ≥ 3개 |
| X3 | 종속항 수 | ≥ 10개 |
| X4 | 전체 청구항 수 | ≥ 20개 |
| X5 | 독립항 평균 길이 | ≥ 200자 |
| X6 | 종속항 평균 길이 | 측정값 |

#### 기술성 지표 (X7~X9)
| 지표 | 설명 | 우수 기준 |
|------|------|----------|
| X7 | 도면 수 | ≥ 3개 |
| X8 | 발명명칭 길이 | 10~60자 |
| X9 | 청구항 계열 수 | ≥ 15개 |

#### 활용성 지표 (X10)
| 지표 | 설명 | 우수 기준 |
|------|------|----------|
| X10 | 발명자 수 | ≥ 2명 |

---

### 2. 정성 평가 (LLM 기반)

#### 기술성 평가 (4개 항목)
```
1. 기술적 혁신성 (Innovation)
   - 기존 기술 대비 개선점
   - 새로운 접근 방식 제시 여부
   - 창의적 문제 해결 방법

2. 구현 상세도 (Implementation)
   - 알고리즘/메커니즘 설명의 구체성
   - 실시예의 충실도
   - 재현 가능성

3. 기술적 차별성 (Differentiation)
   - 선행기술 대비 우위성
   - 독창적 기술 요소
   - 회피 설계 난이도

4. 실용성 (Practicality)
   - 실제 구현 가능성
   - 산업 적용 가능성
   - 확장성 및 범용성
```

#### 권리성 평가 (3개 항목)
```
1. 권리범위 (Scope)
   - IPC 분류 커버리지
   - 청구항 포괄성
   - 보호 범위의 넓이

2. 청구항 견고성 (Robustness)
   - 독립항/종속항 계층 구조
   - 청구항 명확성
   - 무효화 위험도

3. 회피 설계 난이도 (Avoidance Difficulty)
   - 핵심 청구항 우회 가능성
   - 대안 기술 존재 여부
   - 다층 방어 구조
```

#### 활용성 평가 (3개 항목)
```
1. 적용 가능성 (Applicability)
   - 실제 산업 적용 경로
   - 기술 성숙도
   - 표준화 가능성

2. 시장 적합성 (Market Fit)
   - 시장 규모 및 성장성
   - 경쟁 우위
   - 진입 장벽

3. 상용화 가능성 (Commercialization)
   - 즉시 상용화 가능 여부
   - 추가 개발 필요 사항
   - ROI 전망
```

---

### 3. Binary 체크리스트

각 평가 영역별 필수 조건 충족 여부를 체크합니다.

#### 기술성 체크리스트
```python
tech_binary = {
    "has_multiple_drawings": drawing_count >= 3,
    "has_proper_title_length": 10 <= title_length <= 60,
    "has_sufficient_claims": claims_count >= 5,
}
```

#### 권리성 체크리스트
```python
rights_binary = {
    "has_multiple_ipc": ipc_count >= 2,
    "has_independent_claims": independent_claims >= 1,
    "has_dependent_claims": dependent_claims >= 3,
    "has_sufficient_claims": total_claims >= 10,
    "has_proper_claim_length": independent_avg_length >= 100,
}
```

#### 활용성 체크리스트
```python
market_binary = {
    "has_multiple_inventors": inventor_count >= 2,
    "has_known_applicant": applicant != "Unknown",
    "has_ipc_classification": ipc_count >= 1,
}
```

---

### 4. 웹 검색 통합

실시간 웹 검색을 통해 외부 정보를 수집합니다.

```python
# 출원인 정보 (활용성 평가의 35%)
{
    "applicant_grade": "A",  # A/B/C
    "applicant_summary": "삼성생명보험은 국내 1위 생명보험사로..."
}

# 기술 분야 정보 (활용성 평가의 35%)
{
    "tech_grade": "High",  # High/Medium/Low
    "tech_summary": "AI 기반 고객 서비스는 고성장 분야로..."
}
```

---

### 5. Fallback 메커니즘

모든 평가 단계에서 오류 발생 시 안정적인 기본값을 제공합니다.

```python
try:
    # LLM 정성 평가
    result = llm.invoke(prompt)
    qualitative = parse_json(result)
except Exception as e:
    # Fallback: 정량 지표 기반 자동 서술 생성
    qualitative = generate_fallback_summary(
        quantitative_metrics=metrics,
        patent_info=info
    )
```

**Fallback 적용 사례**:
- LLM JSON 파싱 실패 → 정량 지표 기반 기본 서술
- 웹 검색 실패 → "Unknown" 등급 + 기본 설명
- PDF 메타데이터 누락 → 최소값 또는 추정값 사용

---

## Agent 역할 및 책임

#### 1️. TechnologyAgent (기술성 평가)

**역할**: 특허의 기술적 우수성을 평가

**입력**:
```python
{
    "patent_info": {...},        # PDF 메타데이터
    "rag_manager": RAGManager,   # 벡터 검색 시스템
}
```

**처리 과정**:
```python
1. RAG 검색
   ├─ "발명의 배경기술 종래기술 문제점"
   ├─ "기술적 특징 알고리즘 메커니즘"
   ├─ "실시예 도면 구현 방법"
   └─ "발명의 효과 기술적 장점"
   
2. 정량 지표 계산
   ├─ X7: 도면 수
   ├─ X8: 명칭 길이
   └─ X9: 청구항 수
   
3. LLM 정성 평가
   ├─ 혁신성 점수
   ├─ 구현도 점수
   ├─ 차별성 점수
   └─ 실용성 점수
   
4. 점수 집계
   └─ (정량 60% + 정성 40%)
```
---

#### 2. RightsAgent (권리성 평가)

**역할**: 특허의 법적 권리 강도를 평가

**입력**:
```python
{
    "patent_info": {...},
    "rag_manager": RAGManager,
}
```

**처리 과정**:
```python
1. 청구항 분류
   ├─ 독립항 추출
   └─ 종속항 추출
   
2. 정량 지표 계산
   ├─ X1: IPC 코드 수
   ├─ X2: 독립항 수
   ├─ X3: 종속항 수
   ├─ X4: 전체 청구항 수
   ├─ X5: 독립항 평균 길이
   └─ X6: 종속항 평균 길이
   
3. RAG 검색 + LLM 평가
   ├─ 권리범위 분석
   ├─ 청구항 견고성 분석
   └─ 회피 설계 난이도 분석
   
4. 점수 집계
   └─ (정량 70% + 정성 30%)
```

---

#### 3. MarketAgent (활용성 평가)

**역할**: 특허의 시장 활용 가능성을 평가

**입력**:
```python
{
    "patent_info": {...},
    "rag_manager": RAGManager,
}
```

**처리 과정**:
```python
1. 정량 지표 계산 (Fallback 포함)
   └─ X10: 발명자 수
   
2. 웹 검색
   ├─ 출원인 시장 지위 (A/B/C)
   └─ 기술 분야 성장성 (High/Medium/Low)
   
3. 정량 점수 계산
   ├─ 발명자 수 점수 (30%)
   ├─ 출원인 등급 점수 (35%)
   └─ 기술 분야 점수 (35%)
   
4. LLM 정성 평가
   ├─ 적용 가능성 분석
   ├─ 시장 적합성 분석
   └─ 상용화 가능성 분석
   
5. 점수 집계
   └─ (정량 30% + 웹검색 40% + 정성 30%)
```

---

### Agent 간 데이터 흐름

```python
# 1. 초기 State 생성
state = {
    "current_patent": "patents/patent.pdf",
    "patent_info": {...},      # PDF 메타데이터
    "rag_manager": RAGManager,  # 공유 RAG 시스템
}

# 2. TechnologyAgent 평가
state = tech_agent.evaluate(state)
# state에 tech_score, tech_qualitative 등이 추가됨

# 3. RightsAgent 평가
state = rights_agent.evaluate(state)
# state에 rights_score, rights_qualitative 등이 추가됨

# 4. MarketAgent 평가
state = market_agent.evaluate(state)
# state에 market_score, market_qualitative 등이 추가됨

# 5. 종합 점수 계산
final_score = (
    state["tech_score"] * 0.40 +
    state["rights_score"] * 0.35 +
    state["market_score"] * 0.25
)

# 6. 등급 산정
grade = calculate_grade(final_score)

state["final_score"] = final_score
state["final_grade"] = grade

# 7. 보고서 생성
docx_generator.generate(state)
```
---

## 🔧 Tech Stack

### Core Framework

| 기술 | 버전 | 용도 | 선택 이유 |
|------|------|------|----------|
| **Python** | 3.10+ | 메인 언어 | AI/ML 생태계 지원 |
| **LangChain** | 0.1.0+ | LLM 오케스트레이션 | 표준 프레임워크 |
| **Poetry** | 1.7+ | 패키지 관리 | 의존성 관리 단순화 |

---

### AI & Machine Learning

| 기술 | 버전 | 용도 | 비용 |
|------|------|------|------|
| **OpenAI GPT-4o-mini** | Latest | LLM 정성 평가 | 특허 1건당 $0.10~0.20 |
| **OpenAI Embeddings** | text-embedding-3-small | 텍스트 벡터화 | 특허 1건당 $0.01~0.02 |

---

### Vector Database & RAG

| 기술 | 버전 | 용도 | 특징 |
|------|------|------|------|
| **FAISS** | 1.7+ | 벡터 검색 | 오프라인 지원, 빠른 속도 |
| **LangChain FAISS** | 0.1.0+ | RAG 통합 | LangChain 생태계 |

---

### PDF Processing

| 기술 | 버전 | 용도 |
|------|------|------|
| **pdfplumber** | 0.10+ | 텍스트 추출 |
| **PyPDF2** | 3.0+ | 메타데이터 |

---

### Document Generation

| 기술 | 버전 | 용도 |
|------|------|------|
| **python-docx** | 1.1+ | DOCX 생성 |
| **matplotlib** | 3.8+ | 그래프 생성 |

---

### Web Search

| 기술 | 버전 | 용도 |
|------|------|------|
| **duckduckgo-search** | Latest | 실시간 웹 검색 |

---

### Utilities

| 기술 | 버전 | 용도 |
|------|------|------|
| **python-dotenv** | 1.0+ | 환경 변수 |
| **logging** | Built-in | 로그 관리 |

---

## 📦 State

State는 모든 에이전트가 공유하는 중앙 데이터 구조

### State 구조

```python
state = {
    # ===== 입력 =====
    "current_patent": str,          # 현재 처리 중인 특허 경로
    "patent_info": Dict,            # PDF 메타데이터
    "rag_manager": RAGManager,      # 공유 RAG 시스템
    
    # ===== TechnologyAgent 결과 =====
    "tech_score": float,            # 기술성 점수 (0-100)
    "tech_evaluation": Dict,        # LLM 원본 평가 결과
    "tech_qualitative": Dict,       # DOCX용 정성 평가
    "tech_metrics": Dict,           # X7, X8, X9
    "tech_binary": Dict,            # Binary 체크리스트
    "tech_rag_context": str,        # 사용된 RAG 컨텍스트 (디버깅용)
    "tech_insights": str,           # Markdown 형식 인사이트
    
    # ===== RightsAgent 결과 =====
    "rights_score": float,          # 권리성 점수 (0-100)
    "rights_evaluation": Dict,      # LLM 원본 평가 결과
    "rights_qualitative": Dict,     # DOCX용 정성 평가
    "rights_quantitative": Dict,    # 정량 점수 상세
    "rights_metrics": Dict,         # X1~X6
    "rights_binary": Dict,          # Binary 체크리스트
    "rights_insights": str,         # Markdown 형식 인사이트
    
    # ===== MarketAgent 결과 =====
    "market_score": float,          # 활용성 점수 (0-100)
    "market_evaluation": Dict,      # LLM 원본 평가 결과
    "market_qualitative": Dict,     # DOCX용 정성 평가
    "market_quantitative": Dict,    # 정량 점수 상세
    "market_metrics": Dict,         # X10
    "market_binary": Dict,          # Binary 체크리스트
    "market_web_search": Dict,      # 웹 검색 결과
    "market_insights": str,         # Markdown 형식 인사이트
    
    # ===== 최종 결과 =====
    "final_score": float,           # 종합 점수 (0-100)
    "final_grade": str,             # 등급 (AAA~D)
}
```

---

### State 예시 (실제 데이터)

```python
{
    # 입력
    "current_patent": "patents/10-2025-0090445.pdf",
    "patent_info": {
        "number": "10-2025-0090445",
        "title": "LLM 기반 고객 상담 서비스 제공 방법 및 장치",
        "applicant": "삼성생명보험주식회사",
        "inventors": ["김철수", "이영희"],
        "ipc_codes": ["G06F 16/33 (2025.01)", "G06F 16/332 (2025.01)"],
        "claims": ["청구항 1...", "청구항 2...", ...],
        "claims_count": 15,
        "drawing_count": 3,
        "title_length": 27
    },
    
    # TechnologyAgent 결과
    "tech_score": 82.5,
    "tech_metrics": {
        "X7_drawing_count": 3,
        "X8_title_length": 27,
        "X9_claim_series": 15
    },
    "tech_qualitative": {
        "innovation_summary": "LLM과 RAG를 결합한 혁신적 접근으로...",
        "implementation_summary": "15개 청구항과 3개 도면으로 알고리즘이...",
        "differentiation_summary": "선행기술 대비 컨텍스트 이해도가 월등히...",
        "practicality_summary": "즉시 상용화 가능한 수준의 완성도..."
    },
    
    # RightsAgent 결과
    "rights_score": 78.3,
    "rights_metrics": {
        "X1_ipc_count": 2,
        "X2_independent_claims": 3,
        "X3_dependent_claims": 12,
        "X4_total_claims": 15,
        "X5_independent_avg_length": 287.5,
        "X6_dependent_avg_length": 156.3
    },
    "rights_qualitative": {
        "scope_summary": "IPC 2개 분류로 15개 청구항에 걸쳐...",
        "robustness_summary": "독립항 평균 287자, 종속항 12개로...",
        "avoidance_summary": "핵심 기술 요소를 3개 독립항으로..."
    },
    
    # MarketAgent 결과
    "market_score": 87.5,
    "market_metrics": {
        "X10_inventor_count": 2,
        "applicant": "삼성생명보험주식회사",
        "ipc_count": 2
    },
    "market_web_search": {
        "applicant_grade": "A",
        "applicant_summary": "삼성생명보험은 국내 1위 생명보험사로...",
        "tech_grade": "High",
        "tech_summary": "AI 기반 고객 서비스는 고성장 분야로..."
    },
    "market_qualitative": {
        "applicability_summary": "G06F 16/33 분야에서 즉시 적용 가능하며...",
        "market_fit_summary": "A 등급 출원인의 기술로서 High 성장성을...",
        "commercialization_summary": "상용화 단계로 진행 가능하며..."
    },
    
    # 최종 결과
    "final_score": 82.3,
    "final_grade": "BBB"
}
```

---

### State 접근 패턴

```python
# 1. State 초기화
def init_state(patent_path: str) -> Dict:
    state = {
        "current_patent": patent_path,
        "patent_info": pdf_processor.process(patent_path),
        "rag_manager": RAGManager(),
    }
    return state

# 2. Agent가 State 업데이트
def evaluate(self, state: Dict) -> Dict:
    # State에서 필요한 데이터 읽기
    patent_info = state["patent_info"]
    rag_manager = state["rag_manager"]
    
    # 평가 수행
    score = self._calculate_score(patent_info)
    
    # State에 결과 쓰기
    state["tech_score"] = score
    state["tech_qualitative"] = {...}
    
    return state

# 3. 최종 결과 생성
def generate_report(state: Dict) -> str:
    # State에서 모든 평가 결과 읽기
    docx = DOCXGenerator()
    report_path = docx.generate(state)
    return report_path
```

---

## 📂 Directory Structure

```
patent-evaluation-system/
│
├── 📄 README.md                     # 프로젝트 메인 문서
├── 📄 QUICKSTART.md                 # 빠른 시작 가이드
├── 📄 CHANGELOG.md                  # 변경 이력
├── 📄 LICENSE                       # 라이선스
│
├── 📁 agents/                       # AI 에이전트
│   ├── __init__.py
│   ├── tech_agent.py               # 기술성 평가 에이전트
│   ├── rights_agent.py             # 권리성 평가 에이전트
│   └── market_agent.py             # 활용성 평가 에이전트
│
├── 📁 utils/                        # 유틸리티 모듈
│   ├── __init__.py
│   ├── pdf_processor.py            # PDF 텍스트 추출 & 파싱
│   ├── rag_manager.py              # RAG 시스템 (FAISS)
│   ├── docx_generator.py           # DOCX 보고서 생성
│   └── grade_calculator.py         # 종합 점수 계산 & 등급 산정
│
├── 📁 prompts/                      # LLM 프롬프트 템플릿
│   ├── tech_eval.txt               # 기술성 평가 프롬프트
│   ├── rights_eval.txt             # 권리성 평가 프롬프트
│   └── market_eval.txt             # 활용성 평가 프롬프트
│
├── 📁 patents/                      # 입력 특허 PDF (사용자가 추가)
│   └── your-patent.pdf
│
├── 📁 outputs/                      # 출력 결과물 (자동 생성)
│   ├── *_report.docx               # DOCX 평가 보고서
│   ├── *_insights.json             # JSON 상세 데이터
│   └── evaluation_log_*.txt        # 평가 로그
│
├── 📁 docs/                         # 상세 문서
│   └── ARCHITECTURE.md             # 기술 아키텍처 문서
│
├── 📄 main.py                       #  메인 실행 파일
├── 📄 pyproject.toml                #  Poetry 패키지 설정
├── 📄 poetry.lock                   #  의존성 잠금 파일
├── 📄 .env                          #  환경 변수 (생성 필요)
├── 📄 .env.example                  #  환경 변수 예시
└── 📄 .gitignore                    #  Git 제외 파일
```

---

### 주요 모듈 설명

#### `agents/`
각 평가 영역을 담당하는 독립적인 에이전트들입니다.

```python
# agents/tech_agent.py
class TechnologyAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini")
    
    def evaluate(self, state: Dict) -> Dict:
        # RAG 검색 → 정량 계산 → LLM 평가 → State 업데이트
        pass

# agents/rights_agent.py
class RightsAgent:
    def evaluate(self, state: Dict) -> Dict:
        # 청구항 분석 → 정량 계산 → LLM 평가 → State 업데이트
        pass

# agents/market_agent.py
class MarketAgent:
    def evaluate(self, state: Dict) -> Dict:
        # 웹 검색 → 정량 계산 → LLM 평가 → State 업데이트
        pass
```

---

#### `utils/`
공통으로 사용되는 유틸리티 모듈들입니다.

```python
# utils/pdf_processor.py
class PDFProcessor:
    def process(self, pdf_path: str) -> Dict:
        # PDF → 텍스트 + 메타데이터
        pass

# utils/rag_manager.py
class RAGManager:
    def build_vectorstore(self, documents: List) -> None:
        # 문서 → FAISS 벡터 DB
        pass
    
    def search(self, query: str, k: int = 5) -> List:
        # 의미론적 유사도 검색
        pass

# utils/docx_generator.py
class DOCXGenerator:
    def generate(self, state: Dict) -> str:
        # State → DOCX 보고서
        pass

# utils/grade_calculator.py
def calculate_grade(score: float) -> str:
    # 점수 → 등급 (AAA~D)
    pass
```

---

#### `prompts/`
LLM에 전달되는 프롬프트 템플릿들입니다.

```
prompts/
├── tech_eval.txt      # "당신은 특허 기술성 평가 전문가입니다..."
├── rights_eval.txt    # "당신은 특허 권리성 평가 전문가입니다..."
└── market_eval.txt    # "당신은 특허 활용성 평가 전문가입니다..."
```

각 프롬프트는 다음 구조를 따릅니다:
- 역할 정의
- 평가 기준 상세
- 출력 형식 (JSON)
- 예시

---

## Architecture
<img width="637" height="1134" alt="image" src="https://github.com/user-attachments/assets/05160b4d-5300-4a43-b344-b45658b85a2e" />


## Contributors 
- 백선재 : Agent Designer
