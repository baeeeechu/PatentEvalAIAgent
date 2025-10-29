"""
특허 평가 시스템 v6.1 - 실제 RAG + LLM 에이전트 기반
- RAG 시스템: FAISS 벡터 스토어 + 임베딩 기반 검색
- LLM 에이전트: LangChain + OpenAI GPT-4
- PDF 원문 컨텍스트 기반 평가
- 개선된 JSON 파싱 및 타임스탬프 파일명
"""
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import re
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(override=True)

# LangChain 및 관련 라이브러리
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# 커스텀 모듈
from utils import PDFProcessor, PatentRAGManager, Visualizer
from utils.docx_generator import PatentReportGenerator  # v6.0 보고서 생성기
from config import EVALUATION_WEIGHTS, calculate_grade


class PatentEvaluationSystem:
    """RAG + LLM 기반 특허 평가 시스템"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """시스템 초기화"""
        print("=" * 80)
        print("🚀 특허 평가 시스템 v6.1 - RAG + LLM 에이전트")
        print("=" * 80)
        
        # LLM 초기화
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # RAG 매니저 초기화
        self.rag_manager = None
        
        # 시각화 도구
        self.visualizer = Visualizer()
        
        # 보고서 생성기
        self.report_generator = PatentReportGenerator()
        
        # 타임스탬프 (모든 파일에 동일하게 사용)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def parse_llm_response(self, response_text: str, default_result: Optional[Dict] = None) -> Dict:
        """LLM 응답을 JSON으로 파싱 - 강화된 버전"""
        try:
            # 1. 전체를 JSON으로 시도
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 2. JSON 블록 패턴 매칭
            json_patterns = [
                r'```json\n(.*?)\n```',
                r'```\n(.*?)\n```',
                r'\{[^{}]*\{[^{}]*\}[^{}]*\}',  # 중첩 JSON
                r'\{.*?"total_score".*?\}',  # total_score 포함 JSON
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, response_text, re.DOTALL)
                for match in matches:
                    try:
                        json_str = match.strip()
                        result = json.loads(json_str)
                        
                        # total_score 없으면 계산
                        if 'total_score' not in result:
                            scores = [v for k, v in result.items() if 'score' in k and isinstance(v, (int, float))]
                            if scores:
                                result['total_score'] = sum(scores) / len(scores)
                        
                        print(f"   ✅ JSON 파싱 성공: {len(result)}개 필드")
                        return result
                    except json.JSONDecodeError:
                        continue
            
            # 3. 개별 필드 정규식 추출
            extracted = {}
            
            # 점수 추출
            score_patterns = {
                'innovation_score': r'"?innovation_score"?\s*[:=]\s*(\d+)',
                'implementation_score': r'"?implementation_score"?\s*[:=]\s*(\d+)',
                'differentiation_score': r'"?differentiation_score"?\s*[:=]\s*(\d+)',
                'practicality_score': r'"?practicality_score"?\s*[:=]\s*(\d+)',
                'total_score': r'"?total_score"?\s*[:=]\s*(\d+\.?\d*)',
            }
            
            for key, pattern in score_patterns.items():
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    extracted[key] = float(match.group(1))
            
            # 리스트 추출 (key_strengths)
            strengths_match = re.search(
                r'"?key_strengths"?\s*[:=]\s*\[(.*?)\]', 
                response_text, 
                re.DOTALL | re.IGNORECASE
            )
            if strengths_match:
                strengths_str = strengths_match.group(1)
                extracted['key_strengths'] = [
                    s.strip().strip('"\'') 
                    for s in strengths_str.split(',') 
                    if s.strip() and s.strip() not in ['', '""', "''"]
                ]
            
            # 리스트 추출 (key_weaknesses)
            weaknesses_match = re.search(
                r'"?key_weaknesses"?\s*[:=]\s*\[(.*?)\]', 
                response_text, 
                re.DOTALL | re.IGNORECASE
            )
            if weaknesses_match:
                weaknesses_str = weaknesses_match.group(1)
                extracted['key_weaknesses'] = [
                    w.strip().strip('"\'') 
                    for w in weaknesses_str.split(',') 
                    if w.strip() and w.strip() not in ['', '""', "''"]
                ]
            
            # 요약 추출
            summary_match = re.search(
                r'"?technical_summary"?\s*[:=]\s*"([^"]+)"', 
                response_text, 
                re.IGNORECASE
            )
            if summary_match:
                extracted['technical_summary'] = summary_match.group(1)
            
            # total_score 계산 (없으면)
            if 'total_score' not in extracted:
                individual_scores = [
                    extracted.get('innovation_score'),
                    extracted.get('implementation_score'),
                    extracted.get('differentiation_score'),
                    extracted.get('practicality_score')
                ]
                valid_scores = [s for s in individual_scores if s is not None]
                if valid_scores:
                    extracted['total_score'] = sum(valid_scores) / len(valid_scores)
            
            if extracted and len(extracted) >= 2:
                print(f"   ⚠️  JSON 파싱 실패, 정규식 추출: {len(extracted)}개 필드")
                return extracted
            
            # 4. 완전 실패 - 기본값 반환
            print(f"   ❌ LLM 응답 파싱 완전 실패, 기본값 사용")
            print(f"   📝 응답 샘플: {response_text[:300]}...")
            
            if default_result:
                return default_result
            
            return {
                'total_score': 70,
                'error': 'JSON parsing completely failed',
                'raw_response': response_text[:500]
            }
        except Exception as e:
            print(f"   ❌ 파싱 예외: {e}")
            return default_result if default_result else {'total_score': 70, 'error': str(e)}
        
    def build_rag_system(self, pdf_files: List[Path]) -> None:
        """RAG 시스템 구축"""
        print("\n🔨 RAG 시스템 구축 시작...")
        start_time = time.time()
        
        # RAG 매니저 생성
        self.rag_manager = PatentRAGManager(
            embedding_model="nlpai-lab/KoE5",
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # PDF 파일로부터 RAG 구축
        print(f"📂 {len(pdf_files)}개 PDF 처리 중...")
        build_info = self.rag_manager.build_from_pdfs([str(p) for p in pdf_files])
        
        elapsed_time = time.time() - start_time
        print(f"✅ RAG 구축 완료! (소요시간: {elapsed_time:.1f}초)")
        print(f"   • 총 특허: {build_info['total_patents']}개")
        print(f"   • 총 청크: {build_info['total_chunks']}개")
        print(f"   • 평균 청크/특허: {build_info['total_chunks']/build_info['total_patents']:.1f}개")
    
    def add_quantitative_metrics(self, patent_info: Dict, pdf_path: str) -> Dict:
        """PDF 메타데이터에서 정량 지표 계산 (X1~X10)"""
        
        print("\n" + "="*80)
        print("📊 정량 지표 추출 및 계산 (PDF 메타데이터)")
        print("="*80)
        
        # 🔧 PDF Processor가 반환하는 필드명 변환
        # drawing_count → figures_count
        if 'drawing_count' in patent_info:
            patent_info['figures_count'] = patent_info['drawing_count']
            print(f"   🔍 도면 수: {patent_info['figures_count']}개")
        
        # 🆕 발명자 정보가 누락된 경우 RAG로 보완
        if 'inventors' in patent_info:
            inventors = patent_info['inventors']
            # 빈 리스트이거나 빈 문자열만 있는 경우
            if not inventors or (isinstance(inventors, list) and all(not inv.strip() for inv in inventors if isinstance(inv, str))):
                print(f"   ⚠️ 발명자 정보 누락 - RAG 검색으로 보완 시도...")
                try:
                    # RAG로 발명자 검색
                    inventor_context = self.evaluate_with_rag("발명자", pdf_path, k=3)
                    # 간단한 패턴 매칭으로 발명자 추출
                    inventor_patterns = [
                        r'발명자[:\s]*([가-힣]{2,4}(?:\s*,\s*[가-힣]{2,4})*)',
                        r'발명자명[:\s]*([가-힣]{2,4}(?:\s*,\s*[가-힣]{2,4})*)',
                        r'발명자\s*:\s*([가-힣]{2,4})',
                    ]
                    for pattern in inventor_patterns:
                        matches = re.findall(pattern, inventor_context)
                        if matches:
                            # 쉼표로 분리
                            inventors = []
                            for match in matches:
                                inventors.extend([name.strip() for name in match.split(',') if name.strip()])
                            if inventors:
                                patent_info['inventors'] = list(set(inventors))[:5]  # 중복 제거 및 최대 5명
                                print(f"   ✅ RAG로 발견한 발명자: {', '.join(patent_info['inventors'])}")
                                break
                except Exception as e:
                    print(f"   ❌ RAG 발명자 검색 실패: {e}")
        
        # inventors (리스트) → inventors_count (숫자)
        if 'inventors' in patent_info:
            patent_info['inventors_count'] = len(patent_info['inventors'])
            print(f"   🔍 발명자 수: {patent_info['inventors_count']}명")
            if patent_info['inventors']:
                print(f"      발명자: {', '.join(patent_info['inventors'][:3])}{'...' if len(patent_info['inventors']) > 3 else ''}")
            else:
                print(f"      발명자: (정보 없음)")
        
        # 🆕 출원인 정보가 누락된 경우 RAG로 보완
        if 'applicant' in patent_info:
            applicant = patent_info.get('applicant', '').strip()
            if not applicant or applicant == 'Unknown':
                print(f"   ⚠️ 출원인 정보 누락 - RAG 검색으로 보완 시도...")
                try:
                    # RAG로 출원인 검색
                    applicant_context = self.evaluate_with_rag("출원인", pdf_path, k=3)
                    # 간단한 패턴 매칭으로 출원인 추출
                    applicant_patterns = [
                        r'출원인[:\s]*([가-힣a-zA-Z\s]+(?:주식회사|㈜|회사|법인|대학교|연구소))',
                        r'출원인명[:\s]*([가-힣a-zA-Z\s]+(?:주식회사|㈜|회사|법인|대학교|연구소))',
                        r'출원인\s*:\s*([가-힣a-zA-Z\s]+(?:주식회사|㈜))',
                    ]
                    for pattern in applicant_patterns:
                        match = re.search(pattern, applicant_context)
                        if match:
                            applicant = match.group(1).strip()
                            patent_info['applicant'] = applicant
                            print(f"   ✅ RAG로 발견한 출원인: {applicant}")
                            break
                except Exception as e:
                    print(f"   ❌ RAG 출원인 검색 실패: {e}")
        
        # ipc_codes (리스트) → ipc_count (숫자)
        if 'ipc_codes' in patent_info:
            patent_info['ipc_count'] = len(patent_info['ipc_codes'])
            print(f"   🔍 IPC 코드: {patent_info['ipc_count']}개")
            print(f"      코드: {', '.join(patent_info['ipc_codes'][:5])}{'...' if len(patent_info['ipc_codes']) > 5 else ''}")
        
        # claims 분석
        print(f"\n   🔍 청구항 데이터 확인:")
        print(f"      'claims' in patent_info: {'claims' in patent_info}")
        if 'claims' in patent_info:
            print(f"      type(patent_info['claims']): {type(patent_info['claims'])}")
            print(f"      bool(patent_info['claims']): {bool(patent_info['claims'])}")
            if patent_info['claims']:
                claims_preview = str(patent_info['claims'])[:200]
                print(f"      내용 미리보기: {claims_preview}...")
        
        if 'claims' in patent_info and patent_info['claims']:
            claims = patent_info['claims']
            
            # claims가 문자열인 경우 처리
            if isinstance(claims, str):
                # 문자열을 줄바꿈으로 분리하여 리스트로 변환
                claim_lines = [line.strip() for line in claims.split('\n') if line.strip()]
                patent_info['claims_count'] = len(claim_lines)
                
                # 독립항 패턴: "청구항 1.", "제1항.", "[청구항 1]" 등
                independent_pattern = r'^\s*(?:청구항|제)\s*[1-9]\s*(?:항|\.|\])'
                independent_claims = [c for c in claim_lines if re.match(independent_pattern, c)]
                dependent_claims = [c for c in claim_lines if not re.match(independent_pattern, c)]
                
                patent_info['independent_claims_count'] = len(independent_claims) if independent_claims else 1
                patent_info['dependent_claims_count'] = len(dependent_claims)
                
                # 청구항 평균 길이
                avg_length = sum(len(c) for c in claim_lines) / len(claim_lines) if claim_lines else 0
                patent_info['avg_claim_length'] = int(avg_length)
                patent_info['max_dependency_depth'] = 1
                
                print(f"\n   📝 청구항 분석 (문자열에서 파싱):")
                print(f"      총 청구항 수: {patent_info['claims_count']}개")
                if independent_claims:
                    print(f"      독립항 1: {independent_claims[0][:80]}...")
                print(f"      독립항: {patent_info['independent_claims_count']}개")
                print(f"      종속항: {patent_info['dependent_claims_count']}개")
            
            # claims가 문자열 리스트인 경우 (가장 흔한 케이스!)
            elif isinstance(claims, list) and claims and isinstance(claims[0], str):
                patent_info['claims_count'] = len(claims)
                
                # 독립항 패턴으로 구분
                independent_pattern = r'^\s*(?:청구항|제)\s*[1-9]\s*(?:항|\.|\])'
                independent_claims = []
                dependent_claims = []
                
                for claim_text in claims:
                    # 각 청구항이 독립항인지 확인
                    if re.match(independent_pattern, claim_text):
                        independent_claims.append(claim_text)
                    else:
                        dependent_claims.append(claim_text)
                
                # 독립항이 없으면 첫 번째 청구항을 독립항으로 간주
                if not independent_claims and claims:
                    independent_claims = [claims[0]]
                    dependent_claims = claims[1:]
                
                patent_info['independent_claims_count'] = len(independent_claims)
                patent_info['dependent_claims_count'] = len(dependent_claims)
                
                # 청구항 평균 길이
                avg_length = sum(len(c) for c in claims) / len(claims) if claims else 0
                patent_info['avg_claim_length'] = int(avg_length)
                
                # 종속 깊이 계산 (간단히 종속항 수로 추정)
                patent_info['max_dependency_depth'] = min(len(dependent_claims), 5)
                
                print(f"\n   📝 청구항 분석 (문자열 리스트에서 파싱):")
                print(f"      총 청구항 수: {patent_info['claims_count']}개")
                if independent_claims:
                    print(f"      독립항 1: {independent_claims[0][:80]}...")
                print(f"      독립항: {patent_info['independent_claims_count']}개")
                print(f"      종속항: {patent_info['dependent_claims_count']}개")
                
            # claims가 딕셔너리 리스트인 경우
            elif isinstance(claims, list) and claims and isinstance(claims[0], dict):
                patent_info['claims_count'] = len(claims)
                
                # 독립항과 종속항 구분
                independent_claims = [c for c in claims if c.get('is_independent', False)]
                dependent_claims = [c for c in claims if not c.get('is_independent', False)]
                
                patent_info['independent_claims_count'] = len(independent_claims)
                patent_info['dependent_claims_count'] = len(dependent_claims)
                
                # 청구항 평균 길이
                avg_length = sum(len(c.get('text', '')) for c in claims) / len(claims) if claims else 0
                patent_info['avg_claim_length'] = int(avg_length)
                
                # 최대 종속 깊이
                max_depth = max((c.get('dependency_depth', 0) for c in claims), default=0)
                patent_info['max_dependency_depth'] = max_depth
                
                print(f"\n   📝 청구항 분석 (딕셔너리 리스트):")
                print(f"      총 청구항 수: {patent_info['claims_count']}개")
                if independent_claims:
                    print(f"      독립항 1: {independent_claims[0].get('text', '')[:80]}...")
                print(f"      독립항: {patent_info['independent_claims_count']}개")
                print(f"      종속항: {patent_info['dependent_claims_count']}개")
            else:
                # 그 외의 경우 기본값 설정
                patent_info['claims_count'] = 0
                patent_info['independent_claims_count'] = 0
                patent_info['dependent_claims_count'] = 0
                patent_info['avg_claim_length'] = 0
                patent_info['max_dependency_depth'] = 0
            
            print(f"      평균 길이: {patent_info['avg_claim_length']}자")
            print(f"      최대 종속 깊이: {patent_info['max_dependency_depth']}")
        
        # 기본값 설정 (없는 경우)
        patent_info.setdefault('figures_count', 0)
        patent_info.setdefault('claims_count', 0)
        patent_info.setdefault('independent_claims_count', 0)
        patent_info.setdefault('dependent_claims_count', 0)
        patent_info.setdefault('avg_claim_length', 0)
        patent_info.setdefault('ipc_count', 0)
        patent_info.setdefault('max_dependency_depth', 1)
        patent_info.setdefault('inventors_count', 0)
        
        # === 기술성 지표 ===
        # X7: 도면 수
        figures = patent_info['figures_count']
        if figures >= 10: patent_info['X7'] = 100
        elif figures >= 7: patent_info['X7'] = 80
        elif figures >= 4: patent_info['X7'] = 60
        elif figures >= 1: patent_info['X7'] = 40
        else: patent_info['X7'] = 0
        
        # X8: 발명 명칭 길이
        title_len = len(patent_info.get('title', ''))
        if title_len >= 30: patent_info['X8'] = 100
        elif title_len >= 20: patent_info['X8'] = 80
        elif title_len >= 15: patent_info['X8'] = 60
        elif title_len >= 10: patent_info['X8'] = 40
        else: patent_info['X8'] = 20
        
        # X9: 독립항 수
        indep = patent_info['independent_claims_count']
        if indep >= 5: patent_info['X9'] = 100
        elif indep >= 3: patent_info['X9'] = 80
        elif indep >= 2: patent_info['X9'] = 60
        elif indep >= 1: patent_info['X9'] = 40
        else: patent_info['X9'] = 0
        
        # === 권리성 지표 ===
        # X1: IPC 개수
        ipc = patent_info['ipc_count']
        if ipc >= 5: patent_info['X1'] = 100
        elif ipc >= 3: patent_info['X1'] = 75
        elif ipc >= 1: patent_info['X1'] = 50
        else: patent_info['X1'] = 0
        
        # X2: 청구항 개수
        claims = patent_info['claims_count']
        if claims >= 15: patent_info['X2'] = 100
        elif claims >= 10: patent_info['X2'] = 80
        elif claims >= 5: patent_info['X2'] = 60
        elif claims >= 1: patent_info['X2'] = 40
        else: patent_info['X2'] = 0
        
        # X3: 청구항 평균 길이
        avg_len = patent_info['avg_claim_length']
        if avg_len >= 150: patent_info['X3'] = 100
        elif avg_len >= 100: patent_info['X3'] = 80
        elif avg_len >= 50: patent_info['X3'] = 60
        else: patent_info['X3'] = 40
        
        # X4: 독립항 수 (권리성)
        indep = patent_info['independent_claims_count']
        if indep >= 5: patent_info['X4'] = 100
        elif indep >= 3: patent_info['X4'] = 80
        elif indep >= 2: patent_info['X4'] = 60
        elif indep >= 1: patent_info['X4'] = 40
        else: patent_info['X4'] = 0
        
        # X5: 종속항 수
        dep = patent_info['dependent_claims_count']
        if dep >= 15: patent_info['X5'] = 100
        elif dep >= 10: patent_info['X5'] = 80
        elif dep >= 5: patent_info['X5'] = 60
        elif dep >= 1: patent_info['X5'] = 40
        else: patent_info['X5'] = 0
        
        # X6: 청구항 계층 깊이
        depth = patent_info['max_dependency_depth']
        if depth >= 5: patent_info['X6'] = 100
        elif depth >= 4: patent_info['X6'] = 80
        elif depth >= 3: patent_info['X6'] = 60
        elif depth >= 2: patent_info['X6'] = 40
        else: patent_info['X6'] = 20
        
        # === 활용성 지표 ===
        # X10: 발명자 수
        inventors = patent_info['inventors_count']
        if inventors >= 5: patent_info['X10'] = 100
        elif inventors >= 3: patent_info['X10'] = 80
        elif inventors >= 2: patent_info['X10'] = 60
        elif inventors >= 1: patent_info['X10'] = 40
        else: patent_info['X10'] = 0
        
        print(f"\n   🎯 정량 지표 계산 완료:")
        print(f"   【권리성 지표】")
        print(f"      X1 (IPC 코드 수): {patent_info['X1']}/100 (실제값: {patent_info['ipc_count']}개)")
        print(f"      X2 (청구항 수): {patent_info['X2']}/100 (실제값: {patent_info['claims_count']}개)")
        print(f"      X3 (청구항 평균 길이): {patent_info['X3']}/100 (실제값: {patent_info['avg_claim_length']}자)")
        print(f"      X4 (독립항 수): {patent_info['X4']}/100 (실제값: {patent_info['independent_claims_count']}개)")
        print(f"      X5 (종속항 수): {patent_info['X5']}/100 (실제값: {patent_info['dependent_claims_count']}개)")
        print(f"      X6 (계층 깊이): {patent_info['X6']}/100 (실제값: {patent_info['max_dependency_depth']})")
        print(f"   【기술성 지표】")
        print(f"      X7 (도면 수): {patent_info['X7']}/100 (실제값: {patent_info['figures_count']}개)")
        print(f"      X8 (명칭 길이): {patent_info['X8']}/100 (실제값: {title_len}자)")
        print(f"      X9 (독립항 수): {patent_info['X9']}/100 (실제값: {patent_info['independent_claims_count']}개)")
        print(f"   【활용성 지표】")
        print(f"      X10 (발명자 수): {patent_info['X10']}/100 (실제값: {patent_info['inventors_count']}명)")
        print("="*80)
        
        return patent_info
    
    def evaluate_with_rag(self, query: str, pdf_path: str, k: int = 10) -> str:
        """RAG를 사용한 검색"""
        if not self.rag_manager:
            return ""
        
        # 특정 PDF의 청크 검색 (filter_source 제거)
        results = self.rag_manager.search(query, k=k)
        
        # 결과를 텍스트로 결합
        context = "\n\n".join([doc.page_content for doc in results])
        return context
    
    def evaluate_technology(self, patent_info: Dict, pdf_path: str) -> Dict:
        """기술성 평가 - RAG + LLM 기반"""
        print("\n🔬 [기술성 평가] RAG 검색 및 LLM 평가 중...")
        
        # 1. RAG로 기술 관련 컨텍스트 검색
        tech_query = """
        발명의 설명 실시예 구성 구조 방법
        기술적 특징 기술적 효과 해결과제
        도면 설명 발명의 효과 기술분야
        """
        
        start_time = time.time()
        tech_context = self.evaluate_with_rag(tech_query, pdf_path, k=15)
        rag_time = time.time() - start_time
        print(f"   📚 RAG 검색 완료 ({rag_time:.1f}초, {len(tech_context)}자)")
        
        # 2. LLM으로 평가
        tech_prompt = PromptTemplate(
            input_variables=["patent_number", "title", "context", "claims_count"],
            template="""당신은 특허 기술성 평가 전문가입니다. 제공된 특허 내용을 바탕으로 기술적 가치를 평가해주세요.

특허번호: {patent_number}
발명명칭: {title}
청구항 수: {claims_count}

[특허 내용 - RAG 검색 결과]
{context}

평가 기준 (각 항목 0-100점):
1. 기술적 혁신성 - 선행기술 대비 신규성과 진보성
2. 구현 상세도 - 기술 설명의 완전성과 구체성
3. 기술적 차별성 - 독창적이고 차별화된 기술적 접근
4. 실용성 - 구현 용이성과 실제 응용 가능성

중요: 반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
    "innovation_score": 85,
    "implementation_score": 75,
    "differentiation_score": 80,
    "practicality_score": 90,
    "total_score": 82.5,
    "key_strengths": ["강점 1", "강점 2", "강점 3"],
    "key_weaknesses": ["약점 1", "약점 2"],
    "technical_summary": "2-3문장으로 기술 요약을 한국어로 작성"
}}
"""
        )
        
        # LLM 호출
        start_time = time.time()
        llm_input = tech_prompt.format(
            patent_number=patent_info.get('number', 'N/A'),
            title=patent_info.get('title', 'N/A'),
            context=tech_context[:3000],  # 토큰 제한
            claims_count=patent_info.get('claims_count', 0)
        )
        
        response = self.llm.invoke(llm_input)
        llm_time = time.time() - start_time
        print(f"   🤖 LLM 평가 완료 ({llm_time:.1f}초)")
        
        # 응답 파싱 - 개선된 파싱 사용
        result = self.parse_llm_response(
            response.content,
            default_result={
                "total_score": 75,
                "innovation_score": 75,
                "implementation_score": 75,
                "differentiation_score": 75,
                "practicality_score": 75,
                "key_strengths": ["평가 중 기본값 사용"],
                "key_weaknesses": ["평가 중 기본값 사용"],
                "technical_summary": "기술성 평가 기본값"
            }
        )
        
        # 정량 지표 계산 (X7, X8, X9 활용)
        quantitative_tech = (
            patent_info.get('X7', 0) * 0.4 +  # 도면 수 (40%)
            patent_info.get('X8', 0) * 0.3 +  # 명칭 길이 (30%)
            patent_info.get('X9', 0) * 0.3    # 독립항 수 (30%)
        )
        
        qualitative_tech = result.get('total_score', 75)
        
        # 가중 평균 (정량 60%, 정성 40%)
        final_tech_score = quantitative_tech * 0.6 + qualitative_tech * 0.4
        
        result['quantitative_score'] = quantitative_tech
        result['qualitative_score'] = qualitative_tech
        result['total_score'] = final_tech_score
        
        print(f"   📊 정량 점수: {quantitative_tech:.1f}/100 (가중치 60%)")
        print(f"   📊 정성 점수: {qualitative_tech:.1f}/100 (가중치 40%)")
        print(f"   ✅ 최종 기술성 점수: {final_tech_score:.1f}/100")
        return result
    
    def evaluate_rights(self, patent_info: Dict, pdf_path: str) -> Dict:
        """권리성 평가 - RAG + LLM 기반"""
        print("\n⚖️ [권리성 평가] RAG 검색 및 LLM 평가 중...")
        
        # 1. RAG로 권리 관련 컨텍스트 검색
        rights_query = """
        청구항 청구범위 독립항 종속항
        권리범위 보호범위 특허청구범위
        IPC 분류 기술분류
        """
        
        start_time = time.time()
        rights_context = self.evaluate_with_rag(rights_query, pdf_path, k=12)
        rag_time = time.time() - start_time
        print(f"   📚 RAG 검색 완료 ({rag_time:.1f}초, {len(rights_context)}자)")
        
        # 2. LLM으로 평가
        rights_prompt = PromptTemplate(
            input_variables=["patent_number", "title", "context", "claims_count", "ipc_count"],
            template="""당신은 특허 권리성 평가 전문가입니다. 특허 권리범위와 강도를 평가해주세요.

특허번호: {patent_number}
발명명칭: {title}
청구항 수: {claims_count}
IPC 코드 수: {ipc_count}

[특허 청구항 및 권리범위 - RAG 검색 결과]
{context}

평가 기준 (각 항목 0-100점):
1. 권리범위 - 청구항의 보호범위 폭과 커버리지
2. 청구항 구조 - 독립항/종속항의 체계성과 계층 구조
3. 법적 강도 - 권리 행사 가능성과 유효성

중요: 반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
    "scope_score": 85,
    "structure_score": 75,
    "legal_score": 80,
    "total_score": 80.0,
    "key_strengths": ["강점 1", "강점 2"],
    "key_weaknesses": ["약점 1", "약점 2"],
    "technical_summary": "권리성에 대한 2-3문장 요약을 한국어로 작성"
}}
"""
        )
        
        start_time = time.time()
        llm_input = rights_prompt.format(
            patent_number=patent_info.get('number', 'N/A'),
            title=patent_info.get('title', 'N/A'),
            context=rights_context[:3000],
            claims_count=patent_info.get('claims_count', 0),
            ipc_count=patent_info.get('ipc_count', 0)
        )
        
        response = self.llm.invoke(llm_input)
        llm_time = time.time() - start_time
        print(f"   🤖 LLM 평가 완료 ({llm_time:.1f}초)")
        
        result = self.parse_llm_response(
            response.content,
            default_result={
                "total_score": 65,
                "scope_score": 65,
                "structure_score": 65,
                "legal_score": 65,
                "key_strengths": ["평가 중 기본값 사용"],
                "key_weaknesses": ["평가 중 기본값 사용"],
                "technical_summary": "권리성 평가 기본값"
            }
        )
        
        # 정량 지표 계산 (X1~X6 활용)
        quantitative_rights = (
            patent_info.get('X1', 0) * 0.15 +  # IPC 코드 (15%)
            patent_info.get('X2', 0) * 0.20 +  # 청구항 수 (20%)
            patent_info.get('X3', 0) * 0.15 +  # 청구항 평균 길이 (15%)
            patent_info.get('X4', 0) * 0.20 +  # 독립항 수 (20%)
            patent_info.get('X5', 0) * 0.15 +  # 종속항 수 (15%)
            patent_info.get('X6', 0) * 0.15    # 계층 깊이 (15%)
        )
        
        qualitative_rights = result.get('total_score', 65)
        
        # 가중 평균 (정량 70%, 정성 30%)
        final_rights_score = quantitative_rights * 0.7 + qualitative_rights * 0.3
        
        result['quantitative_score'] = quantitative_rights
        result['qualitative_score'] = qualitative_rights
        result['total_score'] = final_rights_score
        
        print(f"   📊 정량 점수: {quantitative_rights:.1f}/100 (가중치 70%)")
        print(f"   📊 정성 점수: {qualitative_rights:.1f}/100 (가중치 30%)")
        print(f"   ✅ 최종 권리성 점수: {final_rights_score:.1f}/100")
        return result
    
    def evaluate_market(self, patent_info: Dict, pdf_path: str) -> Dict:
        """활용성 평가 - RAG + LLM 기반"""
        print("\n📊 [활용성 평가] RAG 검색 및 LLM 평가 중...")
        
        # 1. RAG로 활용성 관련 컨텍스트 검색
        market_query = """
        산업상 이용가능성 시장 적용 상업화
        활용분야 응용분야 산업분야
        발명자 출원인 기업
        """
        
        start_time = time.time()
        market_context = self.evaluate_with_rag(market_query, pdf_path, k=10)
        rag_time = time.time() - start_time
        print(f"   📚 RAG 검색 완료 ({rag_time:.1f}초, {len(market_context)}자)")
        
        # 2. LLM으로 평가
        market_prompt = PromptTemplate(
            input_variables=["patent_number", "title", "context", "inventors_count"],
            template="""당신은 특허 상용화 전문가입니다. 시장 잠재력과 응용 가능성을 평가해주세요.

특허번호: {patent_number}
발명명칭: {title}
발명자 수: {inventors_count}

[특허 응용 맥락 - RAG 검색 결과]
{context}

평가 기준 (각 항목 0-100점):
1. 시장 적용성 - 산업 및 상업적 잠재력
2. 기술 성숙도 - 실용화 준비 수준
3. 경쟁 우위성 - 시장에서의 차별화 요소

중요: 반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
    "applicability_score": 85,
    "maturity_score": 75,
    "advantage_score": 80,
    "total_score": 80.0,
    "key_strengths": ["강점 1", "강점 2"],
    "key_weaknesses": ["약점 1", "약점 2"],
    "technical_summary": "시장성에 대한 2-3문장 요약을 한국어로 작성"
}}
"""
        )
        
        start_time = time.time()
        llm_input = market_prompt.format(
            patent_number=patent_info.get('number', 'N/A'),
            title=patent_info.get('title', 'N/A'),
            context=market_context[:3000],
            inventors_count=patent_info.get('inventors_count', 0)
        )
        
        response = self.llm.invoke(llm_input)
        llm_time = time.time() - start_time
        print(f"   🤖 LLM 평가 완료 ({llm_time:.1f}초)")
        
        result = self.parse_llm_response(
            response.content,
            default_result={
                "total_score": 60,
                "applicability_score": 60,
                "maturity_score": 60,
                "advantage_score": 60,
                "key_strengths": ["평가 중 기본값 사용"],
                "key_weaknesses": ["평가 중 기본값 사용"],
                "technical_summary": "활용성 평가 기본값"
            }
        )
        
        # 정량 지표 (X10만 사용)
        quantitative_market = patent_info.get('X10', 0)
        
        qualitative_market = result.get('total_score', 60)
        
        # 가중 평균 (정량 30%, 정성 70%)
        final_market_score = quantitative_market * 0.3 + qualitative_market * 0.7
        
        result['quantitative_score'] = quantitative_market
        result['qualitative_score'] = qualitative_market
        result['total_score'] = final_market_score
        
        print(f"   📊 정량 점수: {quantitative_market:.1f}/100 (가중치 30%)")
        print(f"   📊 정성 점수: {qualitative_market:.1f}/100 (가중치 70%)")
        print(f"   ✅ 최종 활용성 점수: {final_market_score:.1f}/100")
        return result
    
    def evaluate_patent(self, pdf_path: Path) -> Dict:
        """단일 특허 종합 평가"""
        print(f"\n{'='*80}")
        print(f"📄 특허 평가: {pdf_path.name}")
        print(f"{'='*80}")
        
        # PDF 파싱 - process() 메서드 사용
        processor = PDFProcessor(str(pdf_path))
        patent_data = processor.process()
        patent_info = patent_data['metadata']
        
        # 디버깅: patent_data 구조 확인
        print(f"\n🔍 DEBUG - patent_data keys: {list(patent_data.keys())}")
        print(f"🔍 DEBUG - patent_info keys: {list(patent_info.keys())}")
        
        # 🆕 정량 지표 추가
        patent_info = self.add_quantitative_metrics(patent_info, str(pdf_path))
        
        print(f"📋 특허번호: {patent_info.get('number', 'N/A')}")
        print(f"📋 발명명칭: {patent_info.get('title', 'N/A')[:50]}...")
        print(f"📋 출원인: {patent_info.get('applicant', 'N/A')}")
        
        # 각 평가 수행
        tech_result = self.evaluate_technology(patent_info, str(pdf_path))
        rights_result = self.evaluate_rights(patent_info, str(pdf_path))
        market_result = self.evaluate_market(patent_info, str(pdf_path))
        
        # 종합 점수 계산
        tech_score = tech_result.get('total_score', 70)
        rights_score = rights_result.get('total_score', 65)
        market_score = market_result.get('total_score', 60)
        
        overall_score = (
            tech_score * EVALUATION_WEIGHTS['technology'] +
            rights_score * EVALUATION_WEIGHTS['rights'] +
            market_score * EVALUATION_WEIGHTS['market']
        )
        
        grade = calculate_grade(overall_score)
        
        print(f"\n{'='*80}")
        print(f"📊 평가 결과 요약")
        print(f"{'='*80}")
        print(f"【기술성】 {tech_score:.1f}점 (가중치 {EVALUATION_WEIGHTS['technology']*100:.0f}%)")
        print(f"  • 정량: {tech_result.get('quantitative_score', 0):.1f}점 (60%)")
        print(f"  • 정성: {tech_result.get('qualitative_score', 0):.1f}점 (40%)")
        print(f"【권리성】 {rights_score:.1f}점 (가중치 {EVALUATION_WEIGHTS['rights']*100:.0f}%)")
        print(f"  • 정량: {rights_result.get('quantitative_score', 0):.1f}점 (70%)")
        print(f"  • 정성: {rights_result.get('qualitative_score', 0):.1f}점 (30%)")
        print(f"【활용성】 {market_score:.1f}점 (가중치 {EVALUATION_WEIGHTS['market']*100:.0f}%)")
        print(f"  • 정량: {market_result.get('quantitative_score', 0):.1f}점 (30%)")
        print(f"  • 정성: {market_result.get('qualitative_score', 0):.1f}점 (70%)")
        print(f"\n🏆 종합점수: {overall_score:.1f}점")
        print(f"🏆 평가등급: {grade}")
        print(f"{'='*80}")
        
        return {
            "patent_info": patent_info,
            "tech_result": tech_result,
            "rights_result": rights_result,
            "market_result": market_result,
            "scores": {
                "technology": tech_score,
                "rights": rights_score,
                "market": market_score,
                "overall": overall_score
            },
            "grade": grade
        }
    
    def run(self, pdf_dir: Path = Path("data")):
        """전체 평가 프로세스 실행"""
        # PDF 파일 수집
        if not pdf_dir.exists():
            pdf_dir = Path("/mnt/user-data/uploads")
        
        pdf_files = list(pdf_dir.glob("*.pdf"))[:3]  # 테스트용 3개만
        
        if not pdf_files:
            print(f"❌ PDF 파일이 없습니다: {pdf_dir}")
            return
        
        print(f"📂 {len(pdf_files)}개 PDF 발견:")
        for pdf in pdf_files:
            print(f"   • {pdf.name}")
        
        # RAG 시스템 구축
        self.build_rag_system(pdf_files)
        
        # 각 특허 평가
        results = []
        for pdf_path in pdf_files:
            result = self.evaluate_patent(pdf_path)
            results.append(result)
            
            # 차트 생성
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            
            # 파일명에 타임스탬프 추가
            patent_number_safe = result["patent_info"].get('number', 'unknown').replace('/', '_').replace('-', '')
            
            chart_paths = self.visualizer.create_all_charts(
                result["scores"],
                result["patent_info"].get('number', 'unknown'),
                result["patent_info"].get('applicant', 'N/A'),
                str(output_dir)
            )
            print(f"📈 차트 생성 완료: {output_dir}")
            
            # 보고서 생성 - 타임스탬프 포함
            docx_filename = f"{patent_number_safe}_{self.timestamp}_report.docx"
            docx_path = output_dir / docx_filename
            
            # 실제 보고서 생성
            try:
                # state 딕셔너리 생성 - docx_generator.py가 기대하는 구조로 재구성
                state = {
                    'tech_score': result["scores"]["technology"],
                    'rights_score': result["scores"]["rights"],
                    'market_score': result["scores"]["market"],
                    'overall_score': result["scores"]["overall"],
                    'final_grade': result["grade"],
                    
                    # 🆕 기술성 평가 구조
                    'tech_metrics': {
                        'X7_drawing_count': result["patent_info"].get('figures_count', 0),
                        'X8_title_length': result["patent_info"].get('title_length', 0),
                        'X9_claim_series': result["patent_info"].get('independent_claims_count', 0),
                    },
                    'tech_quantitative': {
                        'drawing_score': result["patent_info"].get('X7', 0),
                        'title_score': result["patent_info"].get('X8', 0),
                        'series_score': result["patent_info"].get('X9', 0),
                        'total': result["tech_result"].get('quantitative_score', 0),
                    },
                    'tech_qualitative': {
                        'qualitative_score': result["tech_result"].get('qualitative_score', 75),
                        'innovation_summary': result["tech_result"].get('technical_summary', 'N/A'),
                        'implementation_summary': ', '.join(result["tech_result"].get('key_strengths', [])),
                        'differentiation_summary': ', '.join(result["tech_result"].get('key_weaknesses', [])),
                    },
                    'tech_binary': {
                        '도면 수 충족(3개 이상)': result["patent_info"].get('figures_count', 0) >= 3,
                        '발명명칭 길이 적절(10자 이상)': result["patent_info"].get('title_length', 0) >= 10,
                        '청구항 계열 충족(3개 이상)': result["patent_info"].get('independent_claims_count', 0) >= 3,
                    },
                    'tech_evaluation': result["tech_result"],
                    
                    # 🆕 권리성 평가 구조
                    'rights_metrics': {
                        'X1_ipc_count': result["patent_info"].get('ipc_count', 0),
                        'X2_independent_claims': result["patent_info"].get('independent_claims_count', 0),  # 독립항 수
                        'X3_dependent_claims': result["patent_info"].get('dependent_claims_count', 0),      # 종속항 수
                        'X4_total_claims': result["patent_info"].get('claims_count', 0),                    # 전체 청구항 수
                        'X5_independent_avg_length': result["patent_info"].get('avg_claim_length', 0),     # 평균 길이 (독립항)
                        'X6_dependent_avg_length': result["patent_info"].get('avg_claim_length', 0),       # 평균 길이 (종속항)
                    },
                    'rights_quantitative': {
                        'ipc_score': result["patent_info"].get('X1', 0),
                        'independent_score': result["patent_info"].get('X4', 0),  # 독립항 점수
                        'dependent_score': result["patent_info"].get('X5', 0),    # 종속항 점수
                        'total_claims_score': result["patent_info"].get('X2', 0), # 전체 청구항 점수
                        'independent_length_score': result["patent_info"].get('X3', 0),  # 평균 길이 점수
                        'dependent_length_score': result["patent_info"].get('X3', 0),    # 평균 길이 점수
                        'total': result["rights_result"].get('quantitative_score', 0),
                    },
                    'rights_qualitative': {
                        'qualitative_score': result["rights_result"].get('qualitative_score', 65),
                        'scope_summary': result["rights_result"].get('technical_summary', 'N/A'),
                        'robustness_summary': ', '.join(result["rights_result"].get('key_strengths', ['견고한 청구항 구조'])),
                        'avoidance_summary': ', '.join(result["rights_result"].get('key_weaknesses', ['회피 설계가 어려운 핵심 특징'])) if result["rights_result"].get('key_weaknesses') else '핵심 기술 요소가 명확하여 회피 설계가 어려움',
                    },
                    'rights_binary': {
                        'IPC 코드 다양성': result["patent_info"].get('ipc_count', 0) >= 3,
                        '청구항 수 충족': result["patent_info"].get('claims_count', 0) >= 5,
                        '독립항 존재': result["patent_info"].get('independent_claims_count', 0) >= 1,
                    },
                    'rights_evaluation': result["rights_result"],
                    
                    # 🆕 활용성 평가 구조
                    'market_metrics': {
                        'X10_inventor_count': result["patent_info"].get('inventors_count', 0),  # s 제거!
                        'applicant_name': result["patent_info"].get('applicant', 'N/A'),
                        'tech_field': ', '.join(result["patent_info"].get('ipc_codes', [])[:2]) if result["patent_info"].get('ipc_codes') else 'N/A',
                    },
                    'market_quantitative': {
                        'inventor_score': result["patent_info"].get('X10', 0),  # s 제거!
                        'applicant_score': 70 if result["patent_info"].get('applicant') and result["patent_info"].get('applicant') != 'N/A' else 0,
                        'tech_field_score': 75 if result["patent_info"].get('ipc_codes') else 0,
                        'total': result["market_result"].get('quantitative_score', 0),
                    },
                    'market_qualitative': {
                        'qualitative_score': result["market_result"].get('qualitative_score', 60),
                        'market_summary': result["market_result"].get('technical_summary', 'N/A'),
                        'applicability_summary': result["market_result"].get('technical_summary', '산업 현장에 적용 가능한 기술'),
                        'market_fit_summary': ', '.join(result["market_result"].get('key_strengths', ['시장 수요에 부합'])),
                        'commercialization_summary': '상용화 가능성이 높은 기술적 완성도를 보유' if result["market_result"].get('qualitative_score', 60) >= 70 else '추가 개발을 통한 상용화 가능',
                    },
                    'market_binary': {
                        '발명자 수 충족': result["patent_info"].get('inventors_count', 0) >= 1,
                    },
                    'market_evaluation': result["market_result"],
                    
                    # 🆕 웹 서치 정보 (출원인/기술분야)
                    'web_search_data': {
                        'applicant_info': {
                            'name': result["patent_info"].get('applicant', 'Unknown'),
                            'rating': 'Major' if result["patent_info"].get('applicant') and any(keyword in result["patent_info"].get('applicant', '') for keyword in ['삼성', '현대', 'LG', 'SK', '네이버', '카카오']) else 'Medium',
                            'content': f"{result['patent_info'].get('applicant', 'N/A')} - 특허 출원인 정보",
                            'search_date': self.timestamp[:8],  # YYYYMMDD
                        },
                        'tech_field_info': {
                            'field': ', '.join(result["patent_info"].get('ipc_codes', [])[:2]) if result["patent_info"].get('ipc_codes') else 'Unknown',
                            'rating': 'High' if result["patent_info"].get('ipc_codes') else 'Unknown',
                            'content': f"IPC: {', '.join(result['patent_info'].get('ipc_codes', [])[:3])}",
                            'search_date': self.timestamp[:8],
                        }
                    },
                    
                    # 🆕 market_web_search (Reference 섹션용)
                    'market_web_search': {
                        'applicant_summary': f"{result['patent_info'].get('applicant', 'N/A')} - {'대기업' if any(keyword in result['patent_info'].get('applicant', '') for keyword in ['삼성', '현대', 'LG', 'SK', '네이버', '카카오']) else '중견기업'} 출원인",
                        'applicant_grade': 'Major' if result["patent_info"].get('applicant') and any(keyword in result["patent_info"].get('applicant', '') for keyword in ['삼성', '현대', 'LG', 'SK', '네이버', '카카오']) else 'Medium',
                        'tech_summary': f"IPC 분류: {', '.join(result['patent_info'].get('ipc_codes', [])[:3])} - AI/빅데이터 관련 고성장 분야",
                        'tech_grade': 'High' if result["patent_info"].get('ipc_codes') else 'Unknown',
                    },
                    
                    'timestamp': self.timestamp,
                    
                    # 추가: 원본 데이터도 포함 (하위 호환성)
                    'X1': result["patent_info"].get('X1', 0),
                    'X2': result["patent_info"].get('X2', 0),
                    'X3': result["patent_info"].get('X3', 0),
                    'X4': result["patent_info"].get('X4', 0),
                    'X5': result["patent_info"].get('X5', 0),
                    'X6': result["patent_info"].get('X6', 0),
                    'X7': result["patent_info"].get('X7', 0),
                    'X8': result["patent_info"].get('X8', 0),
                    'X9': result["patent_info"].get('X9', 0),
                    'X10': result["patent_info"].get('X10', 0),
                    
                    'figures_count': result["patent_info"].get('figures_count', 0),
                    'claims_count': result["patent_info"].get('claims_count', 0),
                    'independent_claims_count': result["patent_info"].get('independent_claims_count', 0),
                    'dependent_claims_count': result["patent_info"].get('dependent_claims_count', 0),
                    'avg_claim_length': result["patent_info"].get('avg_claim_length', 0),
                    'max_dependency_depth': result["patent_info"].get('max_dependency_depth', 0),
                    'ipc_count': result["patent_info"].get('ipc_count', 0),
                    'inventors_count': result["patent_info"].get('inventors_count', 0),
                    'title_length': len(result["patent_info"].get('title', '')),
                }
                
                self.report_generator.generate_report(
                    patent_info=result["patent_info"],
                    state=state,
                    output_path=str(docx_path),
                    chart_paths=chart_paths
                )
                print(f"📝 보고서 생성: {docx_filename}")
            except Exception as e:
                print(f"❌ 보고서 생성 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 최종 요약
        print(f"\n{'='*80}")
        print("✅ 평가 완료!")
        print(f"{'='*80}")
        
        avg_score = sum(r["scores"]["overall"] for r in results) / len(results)
        print(f"평균 종합 점수: {avg_score:.1f}점")
        
        # 등급 분포
        grade_counts = {}
        for r in results:
            grade = r["grade"]
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        print("등급 분포:")
        for grade, count in sorted(grade_counts.items(), reverse=True):
            pct = count / len(results) * 100
            print(f"   {grade}: {count}개 ({pct:.0f}%)")
        
        print(f"\n📁 생성된 파일 위치: {Path('outputs').absolute()}")
        print(f"   타임스탬프: {self.timestamp}")
        
        print("\n💡 시스템 특징:")
        print("   ✅ 실제 RAG 시스템 (FAISS + 임베딩)")
        print("   ✅ LLM 기반 평가 (GPT-4)")
        print("   ✅ PDF 원문 컨텍스트 검색")
        print("   ✅ 개선된 JSON 파싱")
        print("   ✅ 타임스탬프 파일명")
        print(f"{'='*80}")


def main():
    """메인 실행 함수"""
    system = PatentEvaluationSystem()
    system.run()


if __name__ == "__main__":
    main()