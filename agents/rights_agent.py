"""
권리성 평가 에이전트 v5.0 - 정량평가 중심 + Binary 체크리스트
- 정량평가 70% + 정성평가(LLM) 30%
- 32개 평가요소 중 권리성 6개 완전 구현: X1~X6
- 구조방정식 모델 적용
- PDF 원문 기반 (하드코딩 제거)
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List

from langchain_openai import ChatOpenAI


class RightsAgent:
    """권리성 평가 에이전트 v5.0"""
    
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
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
    
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """권리성 평가 수행"""
        print("\n⚖️  권리성 평가 중...")
        
        patent_path = state["current_patent"]
        patent_info = state["patent_info"][patent_path]
        rag_manager = state["rag_manager"]
        
        print(f"   📄 평가 대상: {patent_info.get('title', 'N/A')[:50]}...")
        
        # === 1단계: 정량 지표 계산 (X1~X6) ===
        print("   📊 정량 지표 계산 중...")
        quantitative_metrics = self._calculate_quantitative_metrics(patent_info)
        
        print(f"      X1: IPC 수 = {quantitative_metrics['X1_ipc_count']}")
        print(f"      X2: 독립항 수 = {quantitative_metrics['X2_independent_claims']}")
        print(f"      X3: 종속항 수 = {quantitative_metrics['X3_dependent_claims']}")
        print(f"      X4: 전체 청구항 수 = {quantitative_metrics['X4_total_claims']}")
        print(f"      X5: 독립항 평균 길이 = {quantitative_metrics['X5_independent_avg_length']:.0f}자")
        print(f"      X6: 종속항 평균 길이 = {quantitative_metrics['X6_dependent_avg_length']:.0f}자")
        
        # === 2단계: Binary 체크리스트 ===
        binary_checklist = self._binary_checklist(quantitative_metrics)
        
        print(f"   ✅ Binary 체크리스트:")
        for key, value in binary_checklist.items():
            status = "✓" if value else "✗"
            print(f"      {status} {key}")
        
        # === 3단계: 정량 점수 계산 (구조방정식 모델) ===
        print("   🔢 정량 점수 계산 중 (구조방정식)...")
        quantitative_score = self._calculate_quantitative_score(quantitative_metrics)
        
        print(f"      • IPC 점수: {quantitative_score['ipc_score']:.1f}")
        print(f"      • 청구항 개수 점수: {quantitative_score['claims_count_score']:.1f}")
        print(f"      • 청구항 길이 점수: {quantitative_score['claims_length_score']:.1f}")
        print(f"      • 계층 구조 점수: {quantitative_score['hierarchy_score']:.1f}")
        print(f"      ➜ 정량 점수: {quantitative_score['total']:.1f}/100")
        
        # === 4단계: LLM 정성 평가 (보조) ===
        print("   🤖 LLM 정성 평가 중 (30%)...")
        
        rag_context = rag_manager.get_patent_summary(patent_path, max_chunks=8)
        
        prompt = self.prompt_template.format(
            patent_number=patent_info.get('number', 'N/A'),
            patent_title=patent_info.get('title', 'N/A'),
            applicant=patent_info.get('applicant', 'N/A'),
            claims_count=patent_info.get('claims_count', 0),
            ipc_codes=', '.join(patent_info.get('ipc_codes', [])[:3]),
            quantitative_metrics=json.dumps(quantitative_metrics, indent=2, ensure_ascii=False),
            quantitative_score=json.dumps(quantitative_score, indent=2, ensure_ascii=False),
            binary_checklist=json.dumps(binary_checklist, indent=2, ensure_ascii=False),
            patent_summary=rag_context[:3000],
            rag_context=rag_context[:2000]
        )
        
        response = self.llm.invoke(prompt)
        qualitative_result = self._parse_response(response.content)
        
        qualitative_score = qualitative_result.get('qualitative_score', 60)
        
        print(f"      ➜ 정성 점수: {qualitative_score:.1f}/100")
        
        # === 5단계: 최종 점수 계산 (정량 70% + 정성 30%) ===
        rights_score = quantitative_score['total'] * 0.7 + qualitative_score * 0.3
        
        print(f"   ✅ 권리성 최종 점수: {rights_score:.1f}/100")
        print(f"      = 정량({quantitative_score['total']:.1f}) × 70%")
        print(f"      + 정성({qualitative_score:.1f}) × 30%")
        
        # State 업데이트
        state['rights_score'] = rights_score
        state['rights_quantitative'] = quantitative_score
        state['rights_qualitative'] = qualitative_result
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
        
        # 독립항/종속항 분류
        independent_claims, dependent_claims = self._classify_claims(claims)
        
        # X1: IPC 수
        ipc_count = len(patent_info.get('ipc_codes', []))
        
        # X2: 독립항 수
        independent_count = len(independent_claims)
        
        # X3: 종속항 수
        dependent_count = len(dependent_claims)
        
        # X4: 전체 청구항 수
        total_claims = patent_info.get('claims_count', 0)
        
        # X5: 독립항 평균 길이
        independent_avg_length = (
            sum(len(c) for c in independent_claims) / len(independent_claims)
            if independent_claims else 0
        )
        
        # X6: 종속항 평균 길이
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
        """청구항을 독립항/종속항으로 분류"""
        independent = []
        dependent = []
        
        # 종속항 패턴
        dependent_patterns = [
            '제', '항에', '있어서', '청구항', '또는', '내지'
        ]
        
        for claim in claims:
            # 첫 50자 내에 종속항 패턴이 있는지 확인
            is_dependent = any(pattern in claim[:50] for pattern in dependent_patterns)
            
            if is_dependent:
                dependent.append(claim)
            else:
                independent.append(claim)
        
        # 최소 1개의 독립항 보장
        if not independent and claims:
            independent = [claims[0]]
            dependent = claims[1:]
        
        return independent, dependent
    
    def _binary_checklist(self, metrics: Dict) -> Dict[str, bool]:
        """Binary 체크리스트 (권리성 관련)"""
        return {
            "has_multiple_ipc": metrics['X1_ipc_count'] >= 2,
            "has_sufficient_claims": metrics['X4_total_claims'] >= 10,
            "has_independent_claim": metrics['X2_independent_claims'] >= 1,
            "has_detailed_independent_claim": metrics['X5_independent_avg_length'] >= 100,
            "has_dependent_hierarchy": metrics['X3_dependent_claims'] >= metrics['X2_independent_claims'],
            "claims_length_balanced": (
                50 <= metrics['X6_dependent_avg_length'] <= metrics['X5_independent_avg_length']
                if metrics['X5_independent_avg_length'] > 0 else False
            ),
        }
    
    def _calculate_quantitative_score(self, metrics: Dict) -> Dict:
        """
        정량 점수 계산 (구조방정식 모델)
        
        권리성 = IPC(25%) + 청구항개수(30%) + 청구항길이(25%) + 계층구조(20%)
        """
        
        # 1. IPC 수 점수 (최대 25점)
        # 기준: 10개 이상=100, 5개=75, 2개=60, 1개=40
        ipc_count = metrics['X1_ipc_count']
        if ipc_count >= 10:
            ipc_score = 100
        elif ipc_count >= 5:
            ipc_score = 75
        elif ipc_count >= 2:
            ipc_score = 60
        elif ipc_count >= 1:
            ipc_score = 40
        else:
            ipc_score = 0
        
        # 2. 청구항 개수 점수 (최대 30점)
        # 기준: 30개 이상=100, 20개=80, 10개=60, 5개=40
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
        
        # 3. 청구항 길이 점수 (최대 25점)
        # 독립항: 200자 이상=100, 100자=70, 50자=40
        independent_length = metrics['X5_independent_avg_length']
        if independent_length >= 200:
            length_score = 100
        elif independent_length >= 100:
            length_score = 70
        elif independent_length >= 50:
            length_score = 40
        else:
            length_score = 20
        
        # 4. 계층 구조 점수 (최대 20점)
        # 종속항/독립항 비율: 5 이상=100, 3=75, 1=50
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
        
        # 가중 합산
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
                print("⚠️ JSON 파싱 실패 - 기본값 사용")
                return self._default_qualitative_result()
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 파싱 오류: {e}")
            return self._default_qualitative_result()
    
    def _default_qualitative_result(self) -> Dict:
        """기본 정성 평가 결과"""
        return {
            "qualitative_score": 60,
            "strengths": ["평가 실패 - 기본값"],
            "weaknesses": ["평가 실패 - 기본값"],
            "legal_risk": "평가 실패",
            "defense_strategy": "평가 실패",
            "portfolio_fit": "평가 실패"
        }
    
    def _format_insights(
        self,
        quantitative_metrics: Dict,
        quantitative_score: Dict,
        qualitative_result: Dict,
        final_score: float
    ) -> str:
        """평가 결과를 Markdown 형식으로 포맷"""
        
        strengths = '\n'.join([f"- {s}" for s in qualitative_result.get('strengths', [])])
        weaknesses = '\n'.join([f"- {w}" for w in qualitative_result.get('weaknesses', [])])
        
        insights = f"""## 권리성 평가 상세 결과

### 📊 최종 점수: {final_score:.1f}/100
- **정량 평가** (70%): {quantitative_score['total']:.1f}점
- **정성 평가** (30%): {qualitative_result.get('qualitative_score', 60):.1f}점

### 📏 정량 지표 (PDF 원문 기반)
- **X1. IPC 수**: {quantitative_metrics['X1_ipc_count']}개 → {quantitative_score['ipc_score']:.1f}점
- **X2. 독립항 수**: {quantitative_metrics['X2_independent_claims']}개
- **X3. 종속항 수**: {quantitative_metrics['X3_dependent_claims']}개
- **X4. 전체 청구항 수**: {quantitative_metrics['X4_total_claims']}개 → {quantitative_score['claims_count_score']:.1f}점
- **X5. 독립항 평균 길이**: {quantitative_metrics['X5_independent_avg_length']:.0f}자 → {quantitative_score['claims_length_score']:.1f}점
- **X6. 종속항 평균 길이**: {quantitative_metrics['X6_dependent_avg_length']:.0f}자

### 🔢 구조방정식 모델
```
권리성 = IPC(25%) + 청구항개수(30%) + 청구항길이(25%) + 계층구조(20%)
       = {quantitative_score['ipc_score']:.1f} × 0.25 + {quantitative_score['claims_count_score']:.1f} × 0.30 
         + {quantitative_score['claims_length_score']:.1f} × 0.25 + {quantitative_score['hierarchy_score']:.1f} × 0.20
       = {quantitative_score['total']:.1f}점 (정량)

최종 = 정량({quantitative_score['total']:.1f}) × 70% + 정성({qualitative_result.get('qualitative_score', 60):.1f}) × 30%
     = {final_score:.1f}점
```

### ✅ 강점 (LLM 정성 평가)
{strengths}

### ⚠️ 약점 (LLM 정성 평가)
{weaknesses}

### ⚖️ 법적 리스크
{qualitative_result.get('legal_risk', 'N/A')}

### 🛡️ 방어 전략
{qualitative_result.get('defense_strategy', 'N/A')}

### 📂 포트폴리오 적합성
{qualitative_result.get('portfolio_fit', 'N/A')}
"""
        return insights


if __name__ == "__main__":
    print("권리성 평가 에이전트 v5.0 - 정량평가 중심")