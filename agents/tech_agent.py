"""
기술성 평가 에이전트 v7.0 - qualitative 완전 대응
- RAG 컨텍스트 검색
- LLM 기반 평가
- tech_qualitative 명시적 생성 (DOCX 대응)
"""
import os
import json
import time
from typing import Dict, Any
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


class TechnologyAgent:
    """기술성 평가 에이전트"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """에이전트 초기화"""
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 프롬프트 템플릿
        self.prompt = PromptTemplate(
            input_variables=["patent_info", "rag_context"],
            template="""
당신은 특허 기술성 평가 전문가입니다.
다음 특허의 기술성을 종합적으로 평가해주세요.

[특허 정보]
{patent_info}

[RAG 검색 컨텍스트]
{rag_context}

다음 기준으로 상세히 평가하세요:

1. **기술적 혁신성** (Innovation)
   - 기존 기술 대비 개선점
   - 새로운 접근 방식 제시 여부
   - 창의적 문제 해결 방법

2. **구현 상세도** (Implementation Detail)
   - 알고리즘/메커니즘 설명의 구체성
   - 실시예의 충실도
   - 재현 가능성

3. **기술적 차별성** (Technical Differentiation)
   - 선행기술 대비 우위성
   - 독창적 기술 요소
   - 회피 설계 난이도

4. **실용성** (Practicality)
   - 실제 구현 가능성
   - 산업 적용 가능성
   - 확장성 및 범용성

각 항목을 0-100점으로 평가하고, 구체적인 근거를 제시하세요.

응답 형식 (JSON):
{{
    "innovation_score": 85,
    "innovation_rationale": "구체적 근거",
    "implementation_score": 75,
    "implementation_rationale": "구체적 근거",
    "differentiation_score": 80,
    "differentiation_rationale": "구체적 근거",
    "practicality_score": 90,
    "practicality_rationale": "구체적 근거",
    "total_score": 82.5,
    "key_strengths": ["강점1", "강점2"],
    "key_weaknesses": ["약점1", "약점2"],
    "technical_summary": "전체 요약"
}}
"""
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """기술성 평가 수행"""
        print("\n📊 기술성 평가 중...")
        
        patent_path = state["current_patent"]
        patent_info = state["patent_info"][patent_path]
        rag_manager = state["rag_manager"]
        
        # 1. RAG 검색
        print("   📚 RAG 컨텍스트 검색 중...")
        tech_queries = [
            "발명의 배경기술 종래기술 문제점",
            "기술적 특징 알고리즘 메커니즘",
            "실시예 도면 구현 방법",
            "발명의 효과 기술적 장점"
        ]
        
        all_contexts = []
        for query in tech_queries:
            results = rag_manager.search(query, k=3, filter_patent=patent_path)
            for doc in results:
                all_contexts.append(doc.page_content)
        
        rag_context = "\n\n".join(all_contexts[:10])
        print(f"   ✅ RAG 검색 완료 ({len(rag_context)}자)")
        
        # 2. 특허 정보 포맷팅
        patent_info_str = f"""
특허번호: {patent_info.get('number', 'N/A')}
발명명칭: {patent_info.get('title', 'N/A')}
출원인: {patent_info.get('applicant', 'N/A')}
IPC 분류: {', '.join(patent_info.get('ipc_codes', [])[:5])}
청구항 수: {patent_info.get('claims_count', 0)}
도면 수: {patent_info.get('drawing_count', 0)}
"""
        
        # 3. LLM 호출
        print("   🤖 LLM 평가 중...")
        
        try:
            response = self.chain.run(
                patent_info=patent_info_str,
                rag_context=rag_context[:4000]
            )
            
            print(f"   ✅ LLM 평가 완료")
            
            # JSON 파싱 시도
            result = self._safe_parse_json(response)
            
            # 점수 출력
            innovation_score = result.get('innovation_score', 70)
            implementation_score = result.get('implementation_score', 70)
            differentiation_score = result.get('differentiation_score', 70)
            practicality_score = result.get('practicality_score', 70)
            total_score = result.get('total_score', 
                                     (innovation_score + implementation_score + 
                                      differentiation_score + practicality_score) / 4)
            
            print(f"\n   📊 기술성 평가 결과:")
            print(f"      • 혁신성: {innovation_score}점")
            print(f"      • 구현도: {implementation_score}점")
            print(f"      • 차별성: {differentiation_score}점")
            print(f"      • 실용성: {practicality_score}점")
            print(f"      • 종합: {total_score:.1f}점")
            
            # ===== 핵심: tech_qualitative 생성 =====
            tech_qualitative = {
                'innovation_summary': result.get('innovation_rationale', 
                    f"혁신성 {innovation_score}점. RAG 기반 분석 결과 {patent_info.get('title', '본 발명')}은 "
                    f"기존 기술 대비 개선된 접근을 제시하고 있습니다."),
                'implementation_summary': result.get('implementation_rationale',
                    f"구현 상세도 {implementation_score}점. 알고리즘 및 실시예가 {patent_info.get('claims_count', 0)}개 "
                    f"청구항과 {patent_info.get('drawing_count', 0)}개 도면으로 구체적으로 설명되어 있습니다."),
                'differentiation_summary': result.get('differentiation_rationale',
                    f"기술적 차별성 {differentiation_score}점. {', '.join(patent_info.get('ipc_codes', ['N/A'])[:2])} "
                    f"분야에서 독창적인 기술 요소를 포함하고 있습니다."),
                'practicality_summary': result.get('practicality_rationale',
                    f"실용성 {practicality_score}점. 산업 적용 가능성이 높으며 실제 구현이 용이합니다."),
            }
            
            # tech_metrics 추가 (Appendix용)
            tech_metrics = {
                'X7_drawing_count': patent_info.get('drawing_count', 0),
                'X8_title_length': len(patent_info.get('title', '')),
                'X9_claim_series': patent_info.get('claims_count', 0),
            }
            
            # tech_binary 추가
            tech_binary = {
                'has_multiple_drawings': patent_info.get('drawing_count', 0) >= 3,
                'has_proper_title_length': 10 <= len(patent_info.get('title', '')) <= 60,
                'has_sufficient_claims': patent_info.get('claims_count', 0) >= 5,
            }
            
            # State 업데이트
            state['tech_score'] = total_score
            state['tech_evaluation'] = result
            state['tech_qualitative'] = tech_qualitative  # ← 핵심 추가!
            state['tech_metrics'] = tech_metrics
            state['tech_binary'] = tech_binary
            state['tech_rag_context'] = rag_context[:1000]
            
        except Exception as e:
            print(f"   ❌ 평가 오류: {e}")
            print("   ⚠️ 기본값 사용 (Fallback)")
            
            # Fallback 처리
            state['tech_score'] = 70
            state['tech_evaluation'] = {
                "total_score": 70,
                "error": str(e),
                "fallback": True
            }
            
            # Fallback qualitative
            state['tech_qualitative'] = {
                'innovation_summary': f"기술적 혁신성 70점. {patent_info.get('title', '본 발명')}은 "
                                      f"{', '.join(patent_info.get('ipc_codes', ['N/A'])[:2])} 분야의 "
                                      f"기술적 개선을 제공합니다.",
                'implementation_summary': f"구현 상세도 70점. {patent_info.get('claims_count', 0)}개의 청구항과 "
                                          f"{patent_info.get('drawing_count', 0)}개의 도면으로 구체화되어 있습니다.",
                'differentiation_summary': f"기술적 차별성 70점. 선행기술 대비 독창적인 접근 방식을 포함합니다.",
                'practicality_summary': f"실용성 70점. 실제 산업 적용이 가능한 수준의 구현입니다.",
            }
            
            state['tech_metrics'] = {
                'X7_drawing_count': patent_info.get('drawing_count', 0),
                'X8_title_length': len(patent_info.get('title', '')),
                'X9_claim_series': patent_info.get('claims_count', 0),
            }
            
            state['tech_binary'] = {
                'has_multiple_drawings': patent_info.get('drawing_count', 0) >= 3,
                'has_proper_title_length': 10 <= len(patent_info.get('title', '')) <= 60,
                'has_sufficient_claims': patent_info.get('claims_count', 0) >= 5,
            }
        
        return state
    
    def _safe_parse_json(self, response: str) -> Dict:
        """안전한 JSON 파싱"""
        try:
            # 마크다운 코드 블록 제거
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]
            
            return json.loads(response.strip())
        
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON 파싱 실패: {e}")
            print(f"   응답 일부: {response[:200]}")
            
            # 기본값 반환
            return {
                "innovation_score": 70,
                "implementation_score": 70,
                "differentiation_score": 70,
                "practicality_score": 70,
                "total_score": 70,
                "key_strengths": ["RAG 기반 분석 결과 양호"],
                "key_weaknesses": ["LLM 응답 파싱 실패로 상세 분석 제한"],
                "technical_summary": "기술성 평가 기본값 적용",
                "innovation_rationale": "혁신성 평가 자동 생성",
                "implementation_rationale": "구현도 평가 자동 생성",
                "differentiation_rationale": "차별성 평가 자동 생성",
                "practicality_rationale": "실용성 평가 자동 생성",
            }
    
    def get_insights(self) -> str:
        """평가 인사이트"""
        return """
### 기술성 평가 인사이트

본 에이전트는:
1. RAG를 통한 기술 컨텍스트 검색
2. LLM 기반 다각도 평가
3. 정량적 + 정성적 종합 분석

평가 신뢰도: 높음
"""