"""
기술성 평가 에이전트 v5.0 - 정량평가 중심 + Binary 체크리스트
- 정량평가 60% + 정성평가(LLM) 40%
- 32개 평가요소 중 기술성 3개 완전 구현: X7, X8, X9
- 구조방정식 모델 적용
- PDF 원문 기반 (하드코딩 제거)
"""
import os
import json
from pathlib import Path
from typing import Dict, Any

from langchain_openai import ChatOpenAI


class TechnologyAgent:
    """기술성 평가 에이전트 v5.0"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 프롬프트 로드
        prompt_path = Path("prompts/tech_eval.txt")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        else:
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
    
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """기술성 평가 수행"""
        print("\n🔬 기술성 평가 중...")
        
        patent_path = state["current_patent"]
        patent_info = state["patent_info"][patent_path]
        rag_manager = state["rag_manager"]
        
        print(f"   📄 평가 대상: {patent_info.get('title', 'N/A')[:50]}...")
        
        # === 1단계: 정량 지표 계산 (X7, X8, X9) ===
        print("   📊 정량 지표 계산 중...")
        quantitative_metrics = self._calculate_quantitative_metrics(patent_info)
        
        print(f"      X7: 도면 수 = {quantitative_metrics['X7_drawing_count']}")
        print(f"      X8: 발명명칭 길이 = {quantitative_metrics['X8_title_length']}자")
        print(f"      X9: 청구항 계열 수 = {quantitative_metrics['X9_claim_series']}")
        
        # === 2단계: Binary 체크리스트 ===
        binary_checklist = self._binary_checklist(quantitative_metrics)
        
        print(f"   ✅ Binary 체크리스트:")
        for key, value in binary_checklist.items():
            status = "✓" if value else "✗"
            print(f"      {status} {key}")
        
        # === 3단계: 정량 점수 계산 (구조방정식 모델) ===
        print("   🔢 정량 점수 계산 중 (구조방정식)...")
        quantitative_score = self._calculate_quantitative_score(quantitative_metrics)
        
        print(f"      • 도면 점수: {quantitative_score['drawing_score']:.1f}")
        print(f"      • 명칭 점수: {quantitative_score['title_score']:.1f}")
        print(f"      • 계열 점수: {quantitative_score['series_score']:.1f}")
        print(f"      ➜ 정량 점수: {quantitative_score['total']:.1f}/100")
        
        # === 4단계: LLM 정성 평가 (보조) ===
        print("   🤖 LLM 정성 평가 중 (40%)...")
        
        rag_context = rag_manager.get_patent_summary(patent_path, max_chunks=10)
        
        prompt = self.prompt_template.format(
            patent_number=patent_info.get('number', 'N/A'),
            patent_title=patent_info.get('title', 'N/A'),
            applicant=patent_info.get('applicant', 'N/A'),
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
        
        # === 5단계: 최종 점수 계산 (정량 60% + 정성 40%) ===
        tech_score = quantitative_score['total'] * 0.6 + qualitative_score * 0.4
        
        print(f"   ✅ 기술성 최종 점수: {tech_score:.1f}/100")
        print(f"      = 정량({quantitative_score['total']:.1f}) × 60%")
        print(f"      + 정성({qualitative_score:.1f}) × 40%")
        
        # State 업데이트
        state['tech_score'] = tech_score
        state['tech_quantitative'] = quantitative_score
        state['tech_qualitative'] = qualitative_result
        state['tech_metrics'] = quantitative_metrics
        state['tech_binary'] = binary_checklist
        state['tech_insights'] = self._format_insights(
            quantitative_metrics,
            quantitative_score,
            qualitative_result,
            tech_score
        )
        
        return state
    
    def _calculate_quantitative_metrics(self, patent_info: Dict) -> Dict:
        """정량 지표 계산 (X7, X8, X9)"""
        claims = patent_info.get('claims', [])
        
        # X7: 도면 수
        drawing_count = patent_info.get('drawing_count', 0)
        
        # X8: 발명명칭 길이
        title_length = len(patent_info.get('title', ''))
        
        # X9: 청구항 계열 수 (독립항 수로 추정)
        independent_claims = self._classify_independent_claims(claims)
        claim_series = len(independent_claims)
        
        return {
            "X7_drawing_count": drawing_count,
            "X8_title_length": title_length,
            "X9_claim_series": claim_series,
        }
    
    def _classify_independent_claims(self, claims: list) -> list:
        """독립항 추출"""
        independent = []
        
        dependent_patterns = [
            '제', '항에', '있어서', '청구항', '또는', '내지'
        ]
        
        for claim in claims:
            is_dependent = any(pattern in claim[:50] for pattern in dependent_patterns)
            if not is_dependent:
                independent.append(claim)
        
        return independent if independent else claims[:1]  # 최소 1개
    
    def _binary_checklist(self, metrics: Dict) -> Dict[str, bool]:
        """Binary 체크리스트 (기술성 관련)"""
        return {
            "has_sufficient_drawings": metrics['X7_drawing_count'] >= 3,
            "has_clear_title": 10 <= metrics['X8_title_length'] <= 100,
            "has_claim_series": metrics['X9_claim_series'] >= 1,
            "title_not_too_long": metrics['X8_title_length'] <= 100,
        }
    
    def _calculate_quantitative_score(self, metrics: Dict) -> Dict:
        """
        정량 점수 계산 (구조방정식 모델)
        
        기술성 = X7(도면) × 0.4 + X8(명칭) × 0.3 + X9(계열) × 0.3
        """
        
        # X7: 도면 수 점수 (최대 40점)
        # 기준: 0개=0점, 3개=20점, 5개=30점, 10개 이상=40점
        drawing_count = metrics['X7_drawing_count']
        if drawing_count >= 10:
            drawing_score = 100
        elif drawing_count >= 5:
            drawing_score = 75
        elif drawing_count >= 3:
            drawing_score = 60
        elif drawing_count >= 1:
            drawing_score = 40
        else:
            drawing_score = 0
        
        # X8: 발명명칭 길이 점수 (최대 30점)
        # 기준: 20-80자=100점, 10-100자=70점, 그 외=40점
        title_length = metrics['X8_title_length']
        if 20 <= title_length <= 80:
            title_score = 100
        elif 10 <= title_length <= 100:
            title_score = 70
        elif title_length > 0:
            title_score = 40
        else:
            title_score = 0
        
        # X9: 청구항 계열 수 점수 (최대 30점)
        # 기준: 3개 이상=100점, 2개=70점, 1개=40점
        claim_series = metrics['X9_claim_series']
        if claim_series >= 3:
            series_score = 100
        elif claim_series >= 2:
            series_score = 70
        elif claim_series >= 1:
            series_score = 40
        else:
            series_score = 0
        
        # 가중 합산
        total_score = (
            drawing_score * 0.4 +
            title_score * 0.3 +
            series_score * 0.3
        )
        
        return {
            "drawing_score": drawing_score,
            "title_score": title_score,
            "series_score": series_score,
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
            "competitive_analysis": "평가 실패",
            "rnd_recommendation": "평가 실패"
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
        
        insights = f"""## 기술성 평가 상세 결과

### 📊 최종 점수: {final_score:.1f}/100
- **정량 평가** (60%): {quantitative_score['total']:.1f}점
- **정성 평가** (40%): {qualitative_result.get('qualitative_score', 60):.1f}점

### 📏 정량 지표 (PDF 원문 기반)
- **X7. 도면 수**: {quantitative_metrics['X7_drawing_count']}개 → {quantitative_score['drawing_score']:.1f}점
- **X8. 발명명칭 길이**: {quantitative_metrics['X8_title_length']}자 → {quantitative_score['title_score']:.1f}점
- **X9. 청구항 계열 수**: {quantitative_metrics['X9_claim_series']}개 → {quantitative_score['series_score']:.1f}점

### 🔢 구조방정식 모델
```
기술성 = X7(도면) × 0.4 + X8(명칭) × 0.3 + X9(계열) × 0.3
       = {quantitative_score['drawing_score']:.1f} × 0.4 + {quantitative_score['title_score']:.1f} × 0.3 + {quantitative_score['series_score']:.1f} × 0.3
       = {quantitative_score['total']:.1f}점 (정량)

최종 = 정량({quantitative_score['total']:.1f}) × 60% + 정성({qualitative_result.get('qualitative_score', 60):.1f}) × 40%
     = {final_score:.1f}점
```

### ✅ 강점 (LLM 정성 평가)
{strengths}

### ⚠️ 약점 (LLM 정성 평가)
{weaknesses}

### 🔍 경쟁 분석
{qualitative_result.get('competitive_analysis', 'N/A')}

### 💡 R&D 제언
{qualitative_result.get('rnd_recommendation', 'N/A')}
"""
        return insights


if __name__ == "__main__":
    print("기술성 평가 에이전트 v5.0 - 정량평가 중심")