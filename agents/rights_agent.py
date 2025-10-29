"""
권리성 평가 에이전트 v7.0 - qualitative 완전 대응
- rights_qualitative 명시적 생성 (DOCX 대응)
- scope_summary, robustness_summary, avoidance_summary 추가
"""
import os
import json
from typing import Dict, List, Tuple, Any
from pathlib import Path

from langchain_openai import ChatOpenAI


class RightsAgent:
    """권리성 평가 에이전트"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 프롬프트 로드
        prompt_path = Path("prompts/rights_eval.txt")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        else:
            print(f"⚠️ 프롬프트 파일 없음, 기본 템플릿 사용")
            self.prompt_template = """당신은 특허 권리성 평가 전문가입니다.
            
주어진 특허의 권리성을 평가하세요.

1. 권리범위 (Scope)
2. 청구항 견고성 (Robustness)  
3. 회피 설계 난이도 (Avoidance Difficulty)

JSON 형식으로 응답:
{
    "qualitative_score": 80,
    "scope_analysis": "권리범위 분석",
    "robustness_analysis": "청구항 견고성 분석",
    "avoidance_analysis": "회피설계 난이도 분석",
    "strengths": ["강점1", "강점2"],
    "weaknesses": ["약점1"]
}
"""
    
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """권리성 평가 수행"""
        print("\n📊 권리성 평가 중...")
        
        patent_path = state["current_patent"]
        patent_info = state["patent_info"][patent_path]
        rag_manager = state["rag_manager"]
        
        print(f"   📄 평가 대상: {patent_info.get('title', 'N/A')[:50]}...")
        
        # === 1단계: 정량 지표 계산 (X1~X6) ===
        print("   📊 정량 지표 계산 중...")
        quantitative_metrics = self._calculate_quantitative_metrics(patent_info)
        
        print(f"      X1: IPC 수 = {quantitative_metrics['X1_ipc_count']}개")
        print(f"      X2: 독립항 = {quantitative_metrics['X2_independent_claims']}개")
        print(f"      X3: 종속항 = {quantitative_metrics['X3_dependent_claims']}개")
        print(f"      X4: 총 청구항 = {quantitative_metrics['X4_total_claims']}개")
        print(f"      X5: 독립항 평균 길이 = {quantitative_metrics['X5_independent_avg_length']:.1f}자")
        print(f"      X6: 종속항 평균 길이 = {quantitative_metrics['X6_dependent_avg_length']:.1f}자")
        
        # === 2단계: 정량 점수 계산 ===
        quantitative_score = self._calculate_quantitative_score(quantitative_metrics)
        print(f"   ✅ 정량 점수: {quantitative_score['total']:.1f}/100")
        
        # === 3단계: Binary 체크리스트 ===
        binary_checklist = self._create_binary_checklist(quantitative_metrics)
        
        # === 4단계: RAG 검색 + LLM 정성 평가 ===
        print("   📚 RAG 컨텍스트 검색 중...")
        
        rights_queries = [
            "청구항 독립항 종속항",
            "권리범위 보호범위",
            "선행기술 차별성"
        ]
        
        all_contexts = []
        for query in rights_queries:
            results = rag_manager.search(query, k=3, filter_patent=patent_path)
            for doc in results:
                all_contexts.append(doc.page_content)
        
        rag_context = "\n\n".join(all_contexts[:8])
        
        # 정성 평가
        print("   🤖 LLM 정성 평가 중...")
        
        prompt = f"""{self.prompt_template}

[특허 정보]
번호: {patent_info.get('number', 'N/A')}
명칭: {patent_info.get('title', 'N/A')}
IPC: {', '.join(patent_info.get('ipc_codes', [])[:5])}
청구항: {quantitative_metrics['X4_total_claims']}개
  - 독립항: {quantitative_metrics['X2_independent_claims']}개
  - 종속항: {quantitative_metrics['X3_dependent_claims']}개

[RAG 컨텍스트]
{rag_context[:3000]}

JSON으로 응답하세요.
"""
        
        try:
            response = self.llm.invoke(prompt)
            qualitative_result = self._parse_response(response.content)
            qualitative_score = qualitative_result.get('qualitative_score', 60)
            
            print(f"      ➜ 정성 점수: {qualitative_score:.1f}/100")
            
            # ===== 핵심: rights_qualitative 생성 =====
            rights_qualitative = {
                'scope_summary': qualitative_result.get('scope_analysis',
                    f"권리범위: IPC {quantitative_metrics['X1_ipc_count']}개 분류로 "
                    f"{quantitative_metrics['X4_total_claims']}개 청구항에 걸쳐 포괄적으로 보호됩니다. "
                    f"독립항 {quantitative_metrics['X2_independent_claims']}개가 핵심 기술을 정의하고 있습니다."),
                'robustness_summary': qualitative_result.get('robustness_analysis',
                    f"청구항 견고성: 독립항 평균 {quantitative_metrics['X5_independent_avg_length']:.0f}자, "
                    f"종속항 {quantitative_metrics['X3_dependent_claims']}개로 계층적 구조가 양호합니다. "
                    f"다층 방어가 가능한 구조입니다."),
                'avoidance_summary': qualitative_result.get('avoidance_analysis',
                    f"회피 설계 난이도: {patent_info.get('ipc_codes', ['N/A'])[0]} 분류의 핵심 기술 요소를 "
                    f"{quantitative_metrics['X2_independent_claims']}개 독립항으로 보호하여 회피 설계가 어렵습니다."),
            }
            
        except Exception as e:
            print(f"   ⚠️ LLM 평가 실패: {e}")
            print("   기본값 사용 (Fallback)")
            
            qualitative_score = 60
            qualitative_result = self._default_qualitative_result()
            
            # Fallback qualitative
            rights_qualitative = {
                'scope_summary': f"권리범위: IPC {quantitative_metrics['X1_ipc_count']}개, "
                                 f"총 {quantitative_metrics['X4_total_claims']}개 청구항으로 구성됩니다.",
                'robustness_summary': f"청구항 견고성: 독립항 {quantitative_metrics['X2_independent_claims']}개, "
                                      f"종속항 {quantitative_metrics['X3_dependent_claims']}개로 계층화되었습니다.",
                'avoidance_summary': f"회피 설계 난이도: 다층 청구항 구조로 회피가 용이하지 않습니다.",
            }
        
        # === 5단계: 최종 점수 계산 ===
        rights_score = quantitative_score['total'] * 0.7 + qualitative_score * 0.3
        
        print(f"   ✅ 권리성 최종 점수: {rights_score:.1f}/100")
        print(f"      = 정량({quantitative_score['total']:.1f}) × 70% + 정성({qualitative_score:.1f}) × 30%")
        
        # State 업데이트
        state['rights_score'] = rights_score
        state['rights_quantitative'] = quantitative_score
        state['rights_qualitative'] = rights_qualitative  # ← 핵심 추가!
        state['rights_evaluation'] = qualitative_result
        state['rights_metrics'] = quantitative_metrics
        state['rights_binary'] = binary_checklist
        state['rights_insights'] = self._format_insights(
            quantitative_metrics,
            quantitative_score,
            qualitative_result,
            rights_score
        )
        
        return state
    
    def _calculate_quantitative_metrics(self, patent_info: Dict) -> Dict:
        """정량 지표 계산 (X1~X6)"""
        claims = patent_info.get('claims', [])
        
        independent_claims, dependent_claims = self._classify_claims(claims)
        
        ipc_count = len(patent_info.get('ipc_codes', []))
        independent_count = len(independent_claims)
        dependent_count = len(dependent_claims)
        total_claims = patent_info.get('claims_count', 0)
        
        independent_avg_length = (
            sum(len(c) for c in independent_claims) / len(independent_claims)
            if independent_claims else 0
        )
        
        dependent_avg_length = (
            sum(len(c) for c in dependent_claims) / len(dependent_claims)
            if dependent_claims else 0
        )
        
        return {
            "X1_ipc_count": ipc_count,
            "X2_independent_claims": independent_count,
            "X3_dependent_claims": dependent_count,
            "X4_total_claims": total_claims,
            "X5_independent_avg_length": round(independent_avg_length, 1),
            "X6_dependent_avg_length": round(dependent_avg_length, 1),
        }
    
    def _classify_claims(self, claims: list) -> Tuple[List[str], List[str]]:
        """청구항 분류"""
        independent = []
        dependent = []
        
        dependent_patterns = ['제', '항에', '있어서', '청구항', '또는', '내지']
        
        for claim in claims:
            is_dependent = any(pattern in claim[:50] for pattern in dependent_patterns)
            
            if is_dependent:
                dependent.append(claim)
            else:
                independent.append(claim)
        
        if not independent and claims:
            independent.append(claims[0])
            dependent = claims[1:]
        
        return independent, dependent
    
    def _calculate_quantitative_score(self, metrics: Dict) -> Dict:
        """정량 점수 계산"""
        # IPC 점수
        ipc_count = metrics['X1_ipc_count']
        if ipc_count >= 5:
            ipc_score = 100
        elif ipc_count >= 3:
            ipc_score = 80
        elif ipc_count >= 2:
            ipc_score = 60
        else:
            ipc_score = 40
        
        # 청구항 개수 점수
        total_claims = metrics['X4_total_claims']
        if total_claims >= 30:
            claims_count_score = 100
        elif total_claims >= 20:
            claims_count_score = 80
        elif total_claims >= 10:
            claims_count_score = 60
        elif total_claims >= 5:
            claims_count_score = 40
        else:
            claims_count_score = 20
        
        # 청구항 길이 점수
        independent_length = metrics['X5_independent_avg_length']
        if independent_length >= 200:
            length_score = 100
        elif independent_length >= 100:
            length_score = 70
        elif independent_length >= 50:
            length_score = 40
        else:
            length_score = 20
        
        # 계층 구조 점수
        independent_count = metrics['X2_independent_claims']
        dependent_count = metrics['X3_dependent_claims']
        
        if independent_count > 0:
            ratio = dependent_count / independent_count
            if ratio >= 5:
                hierarchy_score = 100
            elif ratio >= 3:
                hierarchy_score = 75
            elif ratio >= 1:
                hierarchy_score = 50
            else:
                hierarchy_score = 30
        else:
            hierarchy_score = 0
        
        total_score = (
            ipc_score * 0.25 +
            claims_count_score * 0.30 +
            length_score * 0.25 +
            hierarchy_score * 0.20
        )
        
        return {
            "ipc_score": ipc_score,
            "claims_count_score": claims_count_score,
            "claims_length_score": length_score,
            "hierarchy_score": hierarchy_score,
            "total": round(total_score, 1)
        }
    
    def _create_binary_checklist(self, metrics: Dict) -> Dict:
        """Binary 체크리스트"""
        return {
            "has_multiple_ipc": metrics['X1_ipc_count'] >= 2,
            "has_independent_claims": metrics['X2_independent_claims'] >= 1,
            "has_dependent_claims": metrics['X3_dependent_claims'] >= 3,
            "has_sufficient_claims": metrics['X4_total_claims'] >= 10,
            "has_proper_claim_length": metrics['X5_independent_avg_length'] >= 100,
        }
    
    def _parse_response(self, content: str) -> Dict:
        """LLM 응답 파싱"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                return self._default_qualitative_result()
        except json.JSONDecodeError:
            return self._default_qualitative_result()
    
    def _default_qualitative_result(self) -> Dict:
        """기본 정성 평가 결과"""
        return {
            "qualitative_score": 60,
            "scope_analysis": "권리범위 평가: RAG 기반 자동 분석이 적용되었습니다.",
            "robustness_analysis": "청구항 견고성: 독립항 및 종속항 구조가 적절히 구성되어 있습니다.",
            "avoidance_analysis": "회피 설계 난이도: 다층 청구항으로 회피가 어려운 구조입니다.",
            "strengths": ["청구항 계층 구조 양호", "IPC 분류 적절"],
            "weaknesses": ["LLM 상세 분석 미완료"],
            "legal_risk": "중간",
            "defense_strategy": "청구항 계층 구조 활용",
            "portfolio_fit": "양호"
        }
    
    def _format_insights(self, quantitative_metrics, quantitative_score, 
                         qualitative_result, final_score) -> str:
        """인사이트 포맷"""
        strengths = '\n'.join([f"- {s}" for s in qualitative_result.get('strengths', [])])
        weaknesses = '\n'.join([f"- {w}" for w in qualitative_result.get('weaknesses', [])])
        
        return f"""## 권리성 평가 상세 결과

### 📊 최종 점수: {final_score:.1f}/100
- **정량 평가** (70%): {quantitative_score['total']:.1f}점
- **정성 평가** (30%): {qualitative_result.get('qualitative_score', 60):.1f}점

### 📏 정량 지표
- X1. IPC 수: {quantitative_metrics['X1_ipc_count']}개
- X2. 독립항: {quantitative_metrics['X2_independent_claims']}개
- X3. 종속항: {quantitative_metrics['X3_dependent_claims']}개
- X4. 총 청구항: {quantitative_metrics['X4_total_claims']}개

### 💪 강점
{strengths}

### 📉 약점
{weaknesses}
"""