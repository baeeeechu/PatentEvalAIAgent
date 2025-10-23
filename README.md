## Overview

Objective: 특허의 기술성, 권리성, 활용성을 객관적으로 평가하여 AAA~C 등급을 산정하고, 상세한 DOCX 보고서를 자동 생성

Methods:
정량평가 (60~70%): PDF 원문에서 추출한 10개 정량 지표 (X1X10) + 구조방정식 모델
정성평가 (30~40%): RAG 기반 LLM 평가 + Binary 체크리스트
웹 서치: 출원인 시장 지위 + 기술 분야 성장성 (DuckDuckGo)

## Tools:

LangChain (Agent 프레임워크)
FAISS (벡터 검색)
GPT-4o-mini (정성 평가)
Python-docx (보고서 생성)
Matplotlib/Seaborn (차트 시각화)
DuckDuckGo (웹 서치)

## Features
#정량평가 중심 시스템

정량 지표 10개 완전 구현 (X1~X10): PDF 원문에서 자동 추출
구조방정식 모델: 투명한 점수 계산식 제공
Binary 체크리스트: True/False 판정으로 명확한 기준

#Multi-Agent 협업 구조

TechnologyAgent: 기술성 평가 (정량 60% + 정성 40%)
RightsAgent: 권리성 평가 (정량 70% + 정성 30%)
MarketAgent: 활용성 평가 (정량+웹서치 70% + 정성 30%)

#자동 보고서 생성

DOCX 보고서: Executive Summary, 정량/정성 분석, 구조방정식, Reference, Appendix
차트 시각화: 막대 차트, 레이더 차트 (PNG)
등급 산정: AAA (90+) ~ 미달 (55점 미만)

#RAG 기반 정성 평가

KoE5 임베딩: 한국어 특화 모델 (nlpai-lab/KoE5)
FAISS 벡터 스토어: 특허 전문 청킹 및 검색
LLM 정성 평가: RAG 컨텍스트 기반 강점/약점 분석

#실시간 웹 서치
출원인 평가: 주요 대기업 / 중견 기업 / 중소기업 자동 판정
기술 분야 평가: IPC 코드 기반 성장성 분석

## Tech Stack
CategoryDetailsFrameworkLangChain, Python 3.11LLMGPT-4o-mini (OpenAI API)RetrievalFAISS, RecursiveCharacterTextSplitterEmbeddingKoE5 (nlpai-lab/KoE5 via HuggingFace)PDF ProcessingPyMuPDF (fitz), pdfplumberDocument Generationpython-docxVisualizationMatplotlib, SeabornWeb SearchDuckDuckGo Search APIEnvironmentPoetry (dependency management)

## Agents
1️⃣ TechnologyAgent (기술성 평가)

정량 지표 (60%):

X7: 도면 수
X8: 발명명칭 길이
X9: 청구항 계열 수

구조방정식: 정량 = X7(도면) × 0.4 + X8(명칭) × 0.3 + X9(계열) × 0.3
정성 평가 (40%): RAG 검색 기반 LLM 평가 (기술적 구체성, 독창성, 실용성)
Binary 체크리스트: 도면 충분성, 명칭 명확성, 계열 구조

2️⃣ RightsAgent (권리성 평가)

정량 지표 (70%):
X1: IPC 수
X2: 독립항 수
X3: 종속항 수
X4: 전체 청구항 수
X5: 독립항 평균 길이
X6: 종속항 평균 길이

구조방정식: 정량 = IPC(25%) + 청구항개수(30%) + 청구항길이(25%) + 계층구조(20%)
정성 평가 (30%): RAG 검색 기반 LLM 평가 (청구범위 명확성, 권리 범위 적절성)
Binary 체크리스트: IPC 다양성, 청구항 충분성, 독립항 상세성

3️⃣ MarketAgent (활용성 평가)

정량 지표 (30%): X10 (발명자 수)
웹 서치 (40%):

출원인 시장 지위: 주요 대기업(100점) / 중견(70점) / 중소(40점)
기술 분야 성장성: 성장 중(100점) / 보통(70점) / 정보 부족(40점)

구조방정식: 정량+웹서치 = 발명자(30%) + 출원인(40%) + 기술분야(30%)
정성 평가 (30%): RAG 검색 기반 LLM 평가 (실무 적용성, 시장 적합성, 상용화 가능성)
Binary 체크리스트: 발명자 다수, 대기업 여부, 성장 분야 여부

## state
state = {
    # === 기본 정보 (3개) ===
    "current_patent": str,           # 현재 평가 중인 특허 PDF 경로
    "patent_info": Dict,             # 모든 특허의 메타데이터 딕셔너리
    "rag_manager": PatentRAGManager, # RAG 시스템 객체
    
    # === 최종 점수 (3개) ===
    "tech_score": float,             # 기술성 최종 점수 (0-100)
    "rights_score": float,           # 권리성 최종 점수 (0-100)
    "market_score": float,           # 활용성 최종 점수 (0-100)
    
    # === 기술성 평가 상세 (5개) ===
    "tech_quantitative": Dict,       # 정량 점수 {'total': 64.5, 'drawing_score': 75, ...}
    "tech_qualitative": Dict,        # 정성 점수 {'qualitative_score': 72, 'strengths': [...], ...}
    "tech_metrics": Dict,            # 정량 지표 {'X7_drawing_count': 5, 'X8_title_length': 48, ...}
    "tech_binary": Dict,             # Binary 체크리스트 {'has_sufficient_drawings': True, ...}
    "tech_insights": str,            # Markdown 형식 상세 평가 결과
    
    # === 권리성 평가 상세 (5개) ===
    "rights_quantitative": Dict,     # 정량 점수 {'total': 81.8, 'ipc_score': 75, ...}
    "rights_qualitative": Dict,      # 정성 점수 {'qualitative_score': 78, 'strengths': [...], ...}
    "rights_metrics": Dict,          # 정량 지표 {'X1_ipc_count': 8, 'X2_independent_claims': 1, ...}
    "rights_binary": Dict,           # Binary 체크리스트 {'has_multiple_ipc': True, ...}
    "rights_insights": str,          # Markdown 형식 상세 평가 결과
    
    # === 활용성 평가 상세 (6개) ===
    "market_quantitative": Dict,     # 정량+웹서치 점수 {'total': 100, 'inventor_score': 100, ...}
    "market_qualitative": Dict,      # 정성 점수 {'qualitative_score': 82, 'applicability_summary': ...}
    "market_metrics": Dict,          # 정량 지표 {'X10_inventor_count': 8, ...}
    "market_binary": Dict,           # Binary 체크리스트 {'has_multiple_inventors': True, ...}
    "market_web_search": Dict,       # 웹 서치 결과 {'applicant_grade': 'Major', 'tech_grade': 'High', ...}
    "market_insights": str,          # Markdown 형식 상세 평가 결과
    
    # === 종합 평가 (2개, agents 완료 후 main.py에서 추가) ===
    "overall_score": float,          # 종합 점수 (가중 평균)
    "final_grade": str,              # 최종 등급 (AAA, AA, A, BBB, ...)
    
    # === 시각화 (1개, visualizer 완료 후 추가) ===
    "chart_paths": Dict,             # 차트 파일 경로 {'bar': 'path/to/bar.png', 'radar': ...}
}


##  Directory Structure
PatentEvalAIAgent/
├── data/                          # 특허 PDF 파일
│   ├── patent1samsung.pdf
│   ├── patent2yanolja.pdf
│   └── patent3kakaobank.pdf
│
├── agents/                        # 평가 에이전트 모듈
│   ├── __init__.py
│   ├── tech_agent.py             # 기술성 평가 (v5.0)
│   ├── rights_agent.py           # 권리성 평가 (v5.0)
│   └── market_agent.py           # 활용성 평가 (v5.0)
│
├── prompts/                       # 프롬프트 템플릿
│   ├── tech_eval.txt             # 기술성 정성 평가 프롬프트
│   ├── rights_eval.txt           # 권리성 정성 평가 프롬프트
│   └── market_eval.txt           # 활용성 정성 평가 프롬프트
│
├── config/                        # 설정 파일
│   ├── __init__.py
│   ├── weights.py                # 평가 가중치 설정
│   └── patents.py                # 특허 파일 목록
│
├── utils/                         # 유틸리티 모듈
│   ├── __init__.py
│   ├── pdf_processor.py          # PDF 파싱 및 메타데이터 추출
│   ├── rag_manager.py            # RAG 시스템 (FAISS + KoE5)
│   ├── visualizer.py             # 차트 생성 (막대, 레이더)
│   └── docx_generator.py         # DOCX 보고서 생성
│
├── outputs/                       # 평가 결과 저장
│   ├── {patent_number}_report.docx
│   ├── {patent_number}_bar_chart.png
│   ├── {patent_number}_radar_chart.png
│   └── {patent_number}_evaluation_v2.json
│
├── faiss_index/                   # FAISS 벡터 인덱스
│   ├── index.faiss
│   └── index.pkl
│
├── main.py                        # 실행 스크립트
├── pyproject.toml                 # Poetry 의존성 관리
├── .env                           # 환경 변수 (OpenAI API Key)
└── README.md                      # 프로젝트 문서

## Architecture
<img width="276" height="1470" alt="image" src="https://github.com/user-attachments/assets/fec9a87b-d608-4a7b-8fe2-863034598837" />


## Contributors 
- 백선재 : Agent Designer
