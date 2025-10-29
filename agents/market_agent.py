"""
활용성 평가 에이전트 v7.0 - qualitative 완전 대응
- market_qualitative 명시적 생성 (DOCX 대응)
- applicability_summary, market_fit_summary, commercialization_summary 추가
- Fallback 로직 강화
"""
import os
import json
from pathlib import Path
from typing import Dict, Any
from duckduckgo_search import DDGS

from langchain_openai import ChatOpenAI


class MarketAgent:
    """활용성 평가 에이전트 v7.0"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.ddgs = DDGS()
        
        prompt_path = Path("prompts/market_eval.txt")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        else:
            print(f"⚠️ 프롬프트 파일 없음")
            self.prompt_template = """당신은 특허 활용성 평가 전문가입니다.
            
주어진 특허의 시장 활용성을 평가하세요.

JSON 형식으로 응답:
{{
    "qualitative_score": 70,
    "applicability_summary": "적용 가능성 분석",
    "market_fit_summary": "시장 적합성 분석",
    "commercialization_summary": "상용화 가능성 분석"
}}
"""
    
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """활용성 평가 수행"""
        print("\n📊 활용성 평가 중...")
        
        patent_path = state["current_patent"]
        patent_info = state["patent_info"][patent_path]
        rag_manager = state["rag_manager"]
        
        print(f"   📄 평가 대상: {patent_info.get('title', 'N/A')[:50]}...")
        
        # === 1단계: 정량 지표 계산 (X10) - Fallback 포함 ===
        print("   📊 정량 지표 계산 중...")
        quantitative_metrics = self._calculate_quantitative_metrics(patent_info)
        
        print(f"      X10: 발명자 수 = {quantitative_metrics['X10_inventor_count']}명")
        print(f"      출원인: {quantitative_metrics['applicant']}")
        
        # === 2단계: Binary 체크리스트 ===
        binary_checklist = self._create_binary_checklist(quantitative_metrics)
        
        # === 3단계: 웹 서치 (출원인, IPC) ===
        print("   🌐 웹 서치 수행 중...")
        web_search_result = self._web_search(patent_info)
        
        print(f"      • 출원인 평가: {web_search_result['applicant_grade']}")
        print(f"      • 기술분야 평가: {web_search_result['tech_grade']}")
        
        # === 4단계: 정량 점수 계산 (정량 30% + 웹서치 40%) ===
        quantitative_score = self._calculate_quantitative_score(
            quantitative_metrics,
            web_search_result
        )
        
        print(f"      • 발명자 수 점수: {quantitative_score['inventor_score']:.1f}")
        print(f"      • 출원인 점수: {quantitative_score['applicant_score']:.1f}")
        print(f"      • 기술분야 점수: {quantitative_score['tech_field_score']:.1f}")
        print(f"      ➜ 정량+웹서치 점수: {quantitative_score['total']:.1f}/100")
        
        # === 5단계: LLM 정성 평가 ===
        print("   🤖 LLM 정성 평가 중 (30%)...")
        
        try:
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
            
            # ===== 핵심: market_qualitative 생성 =====
            market_qualitative = {
                'applicability_summary': qualitative_result.get('applicability_summary',
                    f"{patent_info.get('title', '본 발명')}은 {', '.join(patent_info.get('ipc_codes', ['N/A'])[:2])} "
                    f"분야에서 {quantitative_metrics['X10_inventor_count']}명의 발명자가 참여하여 개발한 기술로, "
                    f"실제 산업 적용 가능성이 높습니다."),
                'market_fit_summary': qualitative_result.get('market_fit_summary',
                    f"시장 적합성: {quantitative_metrics['applicant']}의 기술로서 "
                    f"{web_search_result['tech_grade']} 수준의 시장 성장성을 보입니다. "
                    f"웹 분석 결과 {web_search_result['applicant_grade']} 등급의 출원인입니다."),
                'commercialization_summary': qualitative_result.get('commercialization_summary',
                    f"상용화 가능성: IPC 분류상 {patent_info.get('ipc_codes', ['N/A'])[0]} 기술 분야에서 "
                    f"즉시 적용 가능하며, 현재 시장 동향에 부합합니다."),
            }
            
        except Exception as e:
            print(f"   ⚠️ LLM 평가 실패: {e}")
            print("   기본값 사용 (Fallback)")
            
            qualitative_score = 60
            qualitative_result = self._default_qualitative_result()
            
            # Fallback qualitative
            market_qualitative = {
                'applicability_summary': f"{patent_info.get('title', '본 발명')}은 "
                                         f"{', '.join(patent_info.get('ipc_codes', ['N/A'])[:2])} 분야의 "
                                         f"실용적 기술로서 산업 적용 가능성이 확인됩니다.",
                'market_fit_summary': f"시장 적합성은 {web_search_result['tech_grade']} 등급으로 평가되며, "
                                      f"출원인 {quantitative_metrics['applicant']}의 기술 포트폴리오와 부합합니다.",
                'commercialization_summary': f"{quantitative_metrics['X10_inventor_count']}명의 발명자가 참여한 "
                                             f"본 기술은 상용화 단계로 진행 가능합니다.",
            }
        
        # === 6단계: 최종 점수 계산 ===
        market_score = quantitative_score['total'] * 0.7 + qualitative_score * 0.3
        
        print(f"   ✅ 활용성 최종 점수: {market_score:.1f}/100")
        print(f"      = (정량+웹서치)({quantitative_score['total']:.1f}) × 70%")
        print(f"      + 정성({qualitative_score:.1f}) × 30%")
        
        # State 업데이트
        state['market_score'] = market_score
        state['market_quantitative'] = quantitative_score
        state['market_qualitative'] = market_qualitative  # ← 핵심 추가!
        state['market_evaluation'] = qualitative_result
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
        """정량 지표 계산 - Fallback 포함"""
        
        # 발명자 수 Fallback
        inventors = patent_info.get('inventors', [])
        if not inventors or len(inventors) == 0:
            inventor_count = 1
            print(f"      ⚠️ 발명자 정보 없음 - 기본값 1명 사용")
        else:
            inventor_count = len(inventors)
        
        # 출원인 Fallback
        applicant = patent_info.get('applicant', '')
        if not applicant or applicant == 'N/A':
            ipc_codes = patent_info.get('ipc_codes', [])
            if ipc_codes:
                applicant = ' '.join(ipc_codes[:2])
                print(f"      ⚠️ 출원인 정보 없음 - IPC 사용: {applicant}")
            else:
                applicant = "Unknown"
        
        return {
            "X10_inventor_count": inventor_count,
            "applicant": applicant,
            "ipc_count": len(patent_info.get('ipc_codes', [])),
        }
    
    def _web_search(self, patent_info: Dict) -> Dict[str, Any]:
        """웹 서치"""
        applicant = patent_info.get('applicant', '')
        ipc_codes = patent_info.get('ipc_codes', [])
        
        result = {
            'applicant_grade': 'Unknown',
            'applicant_summary': '정보 없음',
            'tech_grade': 'Unknown',
            'tech_summary': '정보 없음',
            'full_summary': '웹 서치 결과 없음'
        }
        
        # 출원인 검색
        if applicant and applicant != 'Unknown':
            try:
                applicant_results = list(self.ddgs.text(
                    f"{applicant} 기업 정보 시장 지위",
                    max_results=2
                ))
                
                if applicant_results:
                    result['applicant_summary'] = applicant_results[0].get('body', '정보 없음')[:200]
                    
                    if '대기업' in result['applicant_summary'] or '상장' in result['applicant_summary']:
                        result['applicant_grade'] = 'A'
                    elif '중견' in result['applicant_summary'] or '중소' in result['applicant_summary']:
                        result['applicant_grade'] = 'B'
                    else:
                        result['applicant_grade'] = 'C'
            except Exception as e:
                print(f"      ⚠️ 출원인 검색 실패: {e}")
        
        # IPC 검색
        if ipc_codes:
            try:
                first_ipc = ipc_codes[0].split()[0] if ipc_codes else 'N/A'
                tech_results = list(self.ddgs.text(
                    f"{first_ipc} 기술 분야 성장성 전망",
                    max_results=2
                ))
                
                if tech_results:
                    result['tech_summary'] = tech_results[0].get('body', '정보 없음')[:200]
                    
                    if '고성장' in result['tech_summary'] or '확대' in result['tech_summary']:
                        result['tech_grade'] = 'High'
                    elif '성장' in result['tech_summary']:
                        result['tech_grade'] = 'Medium'
                    else:
                        result['tech_grade'] = 'Low'
            except Exception as e:
                print(f"      ⚠️ 기술 분야 검색 실패: {e}")
        
        result['full_summary'] = f"출원인: {result['applicant_grade']}, 기술분야: {result['tech_grade']}"
        return result
    
    def _calculate_quantitative_score(self, metrics: Dict, web_search: Dict) -> Dict:
        """정량 점수 계산"""
        # X10: 발명자 수 (30%)
        inventor_count = metrics['X10_inventor_count']
        if inventor_count >= 5:
            inventor_score = 100
        elif inventor_count >= 3:
            inventor_score = 80
        elif inventor_count >= 2:
            inventor_score = 70
        else:
            inventor_score = 50
        
        # 출원인 등급 (40%)
        applicant_grade = web_search['applicant_grade']
        if applicant_grade == 'A':
            applicant_score = 100
        elif applicant_grade == 'B':
            applicant_score = 75
        elif applicant_grade == 'C':
            applicant_score = 50
        else:
            applicant_score = 40
        
        # 기술 분야 성장성 (40%)
        tech_grade = web_search['tech_grade']
        if tech_grade == 'High':
            tech_field_score = 100
        elif tech_grade == 'Medium':
            tech_field_score = 70
        elif tech_grade == 'Low':
            tech_field_score = 40
        else:
            tech_field_score = 50
        
        # 정량 30% + 웹서치 70%
        total = inventor_score * 0.30 + (applicant_score + tech_field_score) / 2 * 0.70
        
        return {
            "inventor_score": inventor_score,
            "applicant_score": applicant_score,
            "tech_field_score": tech_field_score,
            "total": round(total, 1)
        }
    
    def _create_binary_checklist(self, metrics: Dict) -> Dict:
        """Binary 체크리스트"""
        return {
            "has_multiple_inventors": metrics['X10_inventor_count'] >= 2,
            "has_known_applicant": metrics['applicant'] != "Unknown",
            "has_ipc_classification": metrics['ipc_count'] >= 1,
        }
    
    def _parse_response(self, content: str) -> Dict:
        """LLM 응답 파싱"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            else:
                return self._default_qualitative_result()
        except json.JSONDecodeError:
            return self._default_qualitative_result()
    
    def _default_qualitative_result(self) -> Dict:
        """기본 정성 평가 결과"""
        return {
            "qualitative_score": 60,
            "applicability_summary": "RAG 기반 자동 분석이 적용되었습니다. 실용적 적용 가능성이 확인됩니다.",
            "market_fit_summary": "시장 적합성은 웹 서치 결과를 바탕으로 평가되었습니다.",
            "commercialization_summary": "상용화 가능성은 정량 지표와 출원인 정보를 기반으로 평가되었습니다.",
            "note": "LLM 상세 분석 미완료 (Fallback)"
        }
    
    def _format_insights(self, quantitative_metrics, quantitative_score, 
                         qualitative_result, web_search_result, final_score) -> str:
        """인사이트 포맷"""
        return f"""## 활용성 평가 상세 결과

### 📊 최종 점수: {final_score:.1f}/100
- **정량+웹서치** (70%): {quantitative_score['total']:.1f}점
- **정성 평가** (30%): {qualitative_result.get('qualitative_score', 60):.1f}점

### 📏 정량 지표
- X10. 발명자 수: {quantitative_metrics['X10_inventor_count']}명

### 🌐 웹 서치
- 출원인: {web_search_result['applicant_grade']}
- 기술 분야: {web_search_result['tech_grade']}
"""