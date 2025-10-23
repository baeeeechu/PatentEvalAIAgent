"""
활용성 평가 에이전트 v5.0 - 웹서치 + 정량평가
- 정량평가 30% + 웹서치 40% + 정성평가(LLM) 30%
- 32개 평가요소 중 활용성 1개 구현: X10 (발명자 수)
- 웹 서치: 출원인 시장 지위, IPC 성장성
- PDF 원문 기반 (하드코딩 제거)
"""
import os
import json
from pathlib import Path
from typing import Dict, Any
from duckduckgo_search import DDGS

from langchain_openai import ChatOpenAI


class MarketAgent:
    """활용성 평가 에이전트 v5.0"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 웹 서치 도구
        self.ddgs = DDGS()
        
        # 프롬프트 로드
        prompt_path = Path("prompts/market_eval.txt")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        else:
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
    
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """활용성 평가 수행"""
        print("\n📊 활용성 평가 중...")
        
        patent_path = state["current_patent"]
        patent_info = state["patent_info"][patent_path]
        rag_manager = state["rag_manager"]
        
        print(f"   📄 평가 대상: {patent_info.get('title', 'N/A')[:50]}...")
        
        # === 1단계: 정량 지표 계산 (X10) ===
        print("   📊 정량 지표 계산 중...")
        quantitative_metrics = self._calculate_quantitative_metrics(patent_info)
        
        print(f"      X10: 발명자 수 = {quantitative_metrics['X10_inventor_count']}명")
        
        # === 2단계: 웹 서치 수행 ===
        print("   🌐 웹 서치 수행 중...")
        web_search_result = self._web_search(patent_info)
        
        print(f"      ✅ 출원인 평가: {web_search_result['applicant_summary']}")
        print(f"      ✅ 기술 분야: {web_search_result['tech_summary']}")
        
        # === 3단계: Binary 체크리스트 ===
        binary_checklist = self._binary_checklist(
            quantitative_metrics,
            web_search_result
        )
        
        print(f"   ✅ Binary 체크리스트:")
        for key, value in binary_checklist.items():
            status = "✓" if value else "✗"
            print(f"      {status} {key}")
        
        # === 4단계: 정량 + 웹서치 점수 계산 ===
        print("   🔢 정량 + 웹서치 점수 계산 중...")
        quantitative_score = self._calculate_quantitative_score(
            quantitative_metrics,
            web_search_result
        )
        
        print(f"      • 발명자 점수: {quantitative_score['inventor_score']:.1f}")
        print(f"      • 출원인 점수: {quantitative_score['applicant_score']:.1f}")
        print(f"      • 기술분야 점수: {quantitative_score['tech_field_score']:.1f}")
        print(f"      ➜ 정량+웹서치 점수: {quantitative_score['total']:.1f}/100")
        
        # === 5단계: LLM 정성 평가 (보조) ===
        print("   🤖 LLM 정성 평가 중 (30%)...")
        
        rag_context = rag_manager.get_patent_summary(patent_path, max_chunks=5)
        
        prompt = self.prompt_template.format(
            patent_number=patent_info.get('number', 'N/A'),
            patent_title=patent_info.get('title', 'N/A'),
            applicant=patent_info.get('applicant', 'N/A'),
            quantitative_metrics=json.dumps(quantitative_metrics, indent=2, ensure_ascii=False),
            quantitative_score=json.dumps(quantitative_score, indent=2, ensure_ascii=False),
            binary_checklist=json.dumps(binary_checklist, indent=2, ensure_ascii=False),
            web_search_summary=web_search_result['full_summary'],
            patent_summary=rag_context[:3000],
            rag_context=rag_context[:2000]
        )
        
        response = self.llm.invoke(prompt)
        qualitative_result = self._parse_response(response.content)
        
        qualitative_score = qualitative_result.get('qualitative_score', 60)
        
        print(f"      ➜ 정성 점수: {qualitative_score:.1f}/100")
        
        # === 6단계: 최종 점수 계산 ===
        # 정량(30%) + 웹서치(40%) + 정성(30%)
        # quantitative_score['total']은 이미 정량+웹서치 합산이므로
        # 정량(30%) + 웹서치(40%) = 70%를 quantitative_score['total']로 계산
        market_score = quantitative_score['total'] * 0.7 + qualitative_score * 0.3
        
        print(f"   ✅ 활용성 최종 점수: {market_score:.1f}/100")
        print(f"      = (정량+웹서치)({quantitative_score['total']:.1f}) × 70%")
        print(f"      + 정성({qualitative_score:.1f}) × 30%")
        
        # State 업데이트
        state['market_score'] = market_score
        state['market_quantitative'] = quantitative_score
        state['market_qualitative'] = qualitative_result
        state['market_metrics'] = quantitative_metrics
        state['market_binary'] = binary_checklist
        state['market_web_search'] = web_search_result
        state['market_insights'] = self._format_insights(
            quantitative_metrics,
            quantitative_score,
            qualitative_result,
            web_search_result,
            market_score
        )
        
        return state
    
    def _calculate_quantitative_metrics(self, patent_info: Dict) -> Dict:
        """정량 지표 계산 (X10)"""
        return {
            "X10_inventor_count": len(patent_info.get('inventors', [])),
            "applicant": patent_info.get('applicant', 'N/A'),
            "ipc_count": len(patent_info.get('ipc_codes', [])),
        }
    
    def _web_search(self, patent_info: Dict) -> Dict[str, Any]:
        """웹 서치로 시장성 정보 수집"""
        applicant = patent_info.get('applicant', '')
        ipc_codes = patent_info.get('ipc_codes', [])
        
        result = {
            'applicant_grade': 'Unknown',
            'applicant_summary': '정보 없음',
            'tech_grade': 'Unknown',
            'tech_summary': '정보 없음',
            'full_summary': ''
        }
        
        # 1. 출원인 평가
        if applicant and applicant != 'N/A':
            try:
                # 주요 대기업 체크
                major_companies = [
                    '삼성', 'samsung', 'lg', '엘지', '현대', 'hyundai',
                    'sk', '네이버', 'naver', '카카오', 'kakao',
                    '한화', 'hanwha', '포스코', 'posco', '롯데', 'lotte'
                ]
                
                is_major = any(comp in applicant.lower() for comp in major_companies)
                
                if is_major:
                    result['applicant_grade'] = 'Major'
                    result['applicant_summary'] = f"{applicant}은(는) 주요 대기업"
                else:
                    # DDG 검색
                    query = f"{applicant} 기업 정보 시가총액"
                    search_results = list(self.ddgs.text(query, max_results=3))
                    
                    if search_results:
                        text = ' '.join([r.get('body', '') for r in search_results]).lower()
                        
                        if any(kw in text for kw in ['대기업', '상장', 'kospi', '코스피']):
                            result['applicant_grade'] = 'Medium'
                            result['applicant_summary'] = f"{applicant}은(는) 중견 기업"
                        else:
                            result['applicant_grade'] = 'Small'
                            result['applicant_summary'] = f"{applicant}은(는) 일반 기업"
                    else:
                        result['applicant_summary'] = f"{applicant} (정보 부족)"
                        
            except Exception as e:
                print(f"      ⚠️ 출원인 검색 실패: {e}")
                result['applicant_summary'] = f"{applicant} (검색 실패)"
        
        # 2. 기술 분야 평가
        if ipc_codes:
            try:
                # 성장 분야 IPC
                growing_ipc = ['G06N', 'G06F16', 'G06Q', 'H04L', 'H01L', 'C12N', 'A61K']
                
                main_ipc = ipc_codes[0].split('/')[0] if ipc_codes else ''
                is_growing = any(main_ipc.startswith(g) for g in growing_ipc)
                
                if is_growing:
                    result['tech_grade'] = 'High'
                    result['tech_summary'] = f"{main_ipc} 기술 분야는 성장 중"
                else:
                    # DDG 검색
                    query = f"{main_ipc} 기술 분야 시장 전망"
                    search_results = list(self.ddgs.text(query, max_results=2))
                    
                    if search_results:
                        text = ' '.join([r.get('body', '') for r in search_results]).lower()
                        
                        if any(kw in text for kw in ['성장', 'growth', '증가']):
                            result['tech_grade'] = 'Medium'
                            result['tech_summary'] = f"{main_ipc} 기술 분야는 성장 가능성"
                        else:
                            result['tech_grade'] = 'Low'
                            result['tech_summary'] = f"{main_ipc} 기술 분야 (정보 부족)"
                    else:
                        result['tech_summary'] = f"{main_ipc} (정보 부족)"
                        
            except Exception as e:
                print(f"      ⚠️ IPC 검색 실패: {e}")
                result['tech_summary'] = "IPC 정보 없음"
        
        # 전체 요약
        result['full_summary'] = (
            f"[출원인 평가]\n{result['applicant_summary']}\n\n"
            f"[기술 분야 평가]\n{result['tech_summary']}"
        )
        
        return result
    
    def _binary_checklist(
        self,
        metrics: Dict,
        web_result: Dict
    ) -> Dict[str, bool]:
        """Binary 체크리스트 (활용성 관련)"""
        return {
            "has_multiple_inventors": metrics['X10_inventor_count'] >= 2,
            "is_major_company": web_result['applicant_grade'] in ['Major', 'Medium'],
            "is_growing_field": web_result['tech_grade'] in ['High', 'Medium'],
        }
    
    def _calculate_quantitative_score(
        self,
        metrics: Dict,
        web_result: Dict
    ) -> Dict:
        """
        정량 + 웹서치 점수 계산
        
        활용성 = 발명자(30%) + 출원인(40%) + 기술분야(30%)
        """
        
        # 1. 발명자 수 점수 (30%)
        # 기준: 8명 이상=100, 5명=80, 2명=60, 1명=40
        inventor_count = metrics['X10_inventor_count']
        if inventor_count >= 8:
            inventor_score = 100
        elif inventor_count >= 5:
            inventor_score = 80
        elif inventor_count >= 2:
            inventor_score = 60
        elif inventor_count >= 1:
            inventor_score = 40
        else:
            inventor_score = 0
        
        # 2. 출원인 시장 지위 점수 (40%)
        # Major=100, Medium=70, Small=40, Unknown=20
        applicant_grade = web_result['applicant_grade']
        if applicant_grade == 'Major':
            applicant_score = 100
        elif applicant_grade == 'Medium':
            applicant_score = 70
        elif applicant_grade == 'Small':
            applicant_score = 40
        else:
            applicant_score = 20
        
        # 3. 기술 분야 성장성 점수 (30%)
        # High=100, Medium=70, Low=40, Unknown=20
        tech_grade = web_result['tech_grade']
        if tech_grade == 'High':
            tech_field_score = 100
        elif tech_grade == 'Medium':
            tech_field_score = 70
        elif tech_grade == 'Low':
            tech_field_score = 40
        else:
            tech_field_score = 20
        
        # 가중 합산
        total_score = (
            inventor_score * 0.30 +
            applicant_score * 0.40 +
            tech_field_score * 0.30
        )
        
        return {
            "inventor_score": inventor_score,
            "applicant_score": applicant_score,
            "tech_field_score": tech_field_score,
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
            "applicability_summary": "평가 실패 - 기본값",
            "market_fit_summary": "평가 실패 - 기본값",
            "commercialization_summary": "평가 실패 - 기본값",
            "note": "LLM 응답 파싱 실패"
        }
    
    def _format_insights(
        self,
        quantitative_metrics: Dict,
        quantitative_score: Dict,
        qualitative_result: Dict,
        web_search_result: Dict,
        final_score: float
    ) -> str:
        """평가 결과를 Markdown 형식으로 포맷"""
        
        insights = f"""## 활용성 평가 상세 결과

### 📊 최종 점수: {final_score:.1f}/100
- **정량+웹서치** (70%): {quantitative_score['total']:.1f}점
- **정성 평가** (30%): {qualitative_result.get('qualitative_score', 60):.1f}점

### 📏 정량 지표 (PDF 원문 기반)
- **X10. 발명자 수**: {quantitative_metrics['X10_inventor_count']}명 → {quantitative_score['inventor_score']:.1f}점

### 🌐 웹 서치 결과
- **출원인 시장 지위**: {web_search_result['applicant_grade']} → {quantitative_score['applicant_score']:.1f}점
  - {web_search_result['applicant_summary']}
- **기술 분야 성장성**: {web_search_result['tech_grade']} → {quantitative_score['tech_field_score']:.1f}점
  - {web_search_result['tech_summary']}

### 🔢 구조방정식 모델
```
활용성 = 발명자(30%) + 출원인(40%) + 기술분야(30%)
       = {quantitative_score['inventor_score']:.1f} × 0.30 + {quantitative_score['applicant_score']:.1f} × 0.40 + {quantitative_score['tech_field_score']:.1f} × 0.30
       = {quantitative_score['total']:.1f}점 (정량+웹서치)

최종 = (정량+웹서치)({quantitative_score['total']:.1f}) × 70% + 정성({qualitative_result.get('qualitative_score', 60):.1f}) × 30%
     = {final_score:.1f}점
```

### 💡 실무 적용성 (LLM 정성 평가)
{qualitative_result.get('applicability_summary', 'N/A')}

### 📈 시장 적합성 (LLM 정성 평가)
{qualitative_result.get('market_fit_summary', 'N/A')}

### 🚀 상용화 가능성 (LLM 정성 평가)
{qualitative_result.get('commercialization_summary', 'N/A')}

### 📝 비고
{qualitative_result.get('note', 'N/A')}
"""
        return insights


if __name__ == "__main__":
    print("활용성 평가 에이전트 v5.0 - 웹서치 + 정량평가")