"""
특허 평가 시스템 v7.0 - 진짜 에이전트 시스템
- main.py는 오케스트레이터 역할만 수행
- 실제 평가는 agents/에 위임
- Utils는 순수 도구로 사용
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(override=True)

# Utils (도구)
from utils import PDFProcessor, PatentRAGManager, Visualizer
from utils.docx_generator import PatentReportGenerator

# Agents (평가자)
from agents import TechnologyAgent, RightsAgent, MarketAgent

# Config
from config import EVALUATION_WEIGHTS, calculate_grade


class PatentEvaluationSystem:
    """특허 평가 시스템 - 오케스트레이터"""
    
    def __init__(self):
        """시스템 초기화"""
        print("=" * 80)
        print("🚀 특허 평가 시스템 v7.0 - 진짜 에이전트 시스템")
        print("=" * 80)
        
        # 1. Utils 초기화 (도구)
        self.rag_manager = None
        self.visualizer = Visualizer()
        self.report_generator = PatentReportGenerator()
        
        # 2. Agents 초기화 (평가자)
        print("\n📦 에이전트 초기화 중...")
        self.tech_agent = TechnologyAgent()
        self.rights_agent = RightsAgent()
        self.market_agent = MarketAgent()
        print("   ✅ TechnologyAgent")
        print("   ✅ RightsAgent")
        print("   ✅ MarketAgent")
        
        # 3. 타임스탬프
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def build_rag_system(self, pdf_paths: List[str]):
        """RAG 시스템 구축 (Utils 사용)"""
        print("\n" + "=" * 80)
        print("🔨 RAG 시스템 구축 중...")
        print("=" * 80)
        
        self.rag_manager = PatentRAGManager()
        rag_info = self.rag_manager.build_from_pdfs(pdf_paths)
        
        print(f"\n✅ RAG 구축 완료!")
        print(f"   총 특허: {rag_info['total_patents']}개")
        print(f"   총 청크: {rag_info['total_chunks']}개")
        
        return rag_info
    
    def process_pdfs(self, pdf_paths: List[str]) -> Dict[str, Dict]:
        """PDF 처리 (Utils 사용)"""
        print("\n" + "=" * 80)
        print("📄 PDF 처리 중...")
        print("=" * 80)
        
        patent_data = {}
        
        for pdf_path in pdf_paths:
            print(f"\n처리 중: {Path(pdf_path).name}")
            
            processor = PDFProcessor(pdf_path)
            result = processor.process()
            
            patent_data[pdf_path] = result['metadata']
            
            print(f"✅ 완료:")
            print(f"   특허번호: {result['metadata']['number']}")
            print(f"   발명명칭: {result['metadata']['title'][:50]}...")
            print(f"   청구항: {result['metadata']['claims_count']}개")
        
        return patent_data
    
    def evaluate_patent(self, pdf_path: str, patent_info: Dict) -> Dict:
        """
        특허 평가 수행 - Agents에 위임
        
        이 함수는 단순히 state를 구성하고 각 agent에게 위임합니다.
        """
        print("\n" + "=" * 80)
        print(f"🎯 특허 평가 시작: {patent_info['number']}")
        print("=" * 80)
        
        # State 구성 (Agents가 필요로 하는 데이터)
        state = {
            "current_patent": pdf_path,
            "patent_info": {pdf_path: patent_info},
            "rag_manager": self.rag_manager,
            "timestamp": self.timestamp
        }
        
        # === 1. 기술성 평가 (TechnologyAgent) ===
        print("\n" + "=" * 80)
        print("1️⃣ 기술성 평가 - TechnologyAgent에 위임")
        print("=" * 80)
        
        # ✅ 에이전트에 위임 - main은 결과만 받음
        try:
            # tech_agent는 자체적으로 RAG 검색, LLM 호출, 점수 계산 수행
            state = self.tech_agent.evaluate(state)
            tech_score = state.get('tech_score', 0)
            print(f"\n✅ 기술성 평가 완료: {tech_score:.1f}점")
        except Exception as e:
            print(f"\n❌ 기술성 평가 실패: {e}")
            state['tech_score'] = 65
            state['tech_evaluation'] = {"error": str(e)}
        
        # === 2. 권리성 평가 (RightsAgent) ===
        print("\n" + "=" * 80)
        print("2️⃣ 권리성 평가 - RightsAgent에 위임")
        print("=" * 80)
        
        try:
            state = self.rights_agent.evaluate(state)
            rights_score = state.get('rights_score', 0)
            print(f"\n✅ 권리성 평가 완료: {rights_score:.1f}점")
        except Exception as e:
            print(f"\n❌ 권리성 평가 실패: {e}")
            state['rights_score'] = 65
            state['rights_evaluation'] = {"error": str(e)}
        
        # === 3. 활용성 평가 (MarketAgent) ===
        print("\n" + "=" * 80)
        print("3️⃣ 활용성 평가 - MarketAgent에 위임")
        print("=" * 80)
        
        try:
            state = self.market_agent.evaluate(state)
            market_score = state.get('market_score', 0)
            print(f"\n✅ 활용성 평가 완료: {market_score:.1f}점")
        except Exception as e:
            print(f"\n❌ 활용성 평가 실패: {e}")
            state['market_score'] = 65
            state['market_evaluation'] = {"error": str(e)}
        
        # === 4. 종합 점수 계산 ===
        print("\n" + "=" * 80)
        print("4️⃣ 종합 점수 계산")
        print("=" * 80)
        
        tech_score = state.get('tech_score', 0)
        rights_score = state.get('rights_score', 0)
        market_score = state.get('market_score', 0)
        
        overall_score = (
            tech_score * EVALUATION_WEIGHTS['technology'] +
            rights_score * EVALUATION_WEIGHTS['rights'] +
            market_score * EVALUATION_WEIGHTS['market']
        )
        
        grade = calculate_grade(overall_score)
        
        print(f"\n📊 최종 점수:")
        print(f"   기술성: {tech_score:.1f}점 × {EVALUATION_WEIGHTS['technology']*100:.0f}%")
        print(f"   권리성: {rights_score:.1f}점 × {EVALUATION_WEIGHTS['rights']*100:.0f}%")
        print(f"   활용성: {market_score:.1f}점 × {EVALUATION_WEIGHTS['market']*100:.0f}%")
        print(f"   ─────────────────")
        print(f"   종합: {overall_score:.1f}점 ({grade})")
        
        state['overall_score'] = overall_score
        state['grade'] = grade
        state['final_grade'] = grade  # ✅ docx_generator가 사용하는 키
        
        return state
    
    def generate_outputs(self, state: Dict, patent_info: Dict):
        """
        출력물 생성 - Utils 사용
        1. 시각화 차트
        2. DOCX 보고서
        """
        print("\n" + "=" * 80)
        print("📊 출력물 생성 중...")
        print("=" * 80)
        
        patent_number = patent_info['number']
        applicant = patent_info.get('applicant', 'Unknown')
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        # 점수 딕셔너리
        scores = {
            'technology': state.get('tech_score', 0),
            'rights': state.get('rights_score', 0),
            'market': state.get('market_score', 0),
            'overall': state.get('overall_score', 0)
        }
        
        # 1. 차트 생성 (Visualizer - Utils)
        print("\n1️⃣ 차트 생성 중...")
        chart_paths = self.visualizer.create_all_charts(
            scores=scores,
            patent_number=patent_number,
            applicant=applicant,
            output_dir=str(output_dir)
        )
        print(f"   ✅ 막대 그래프: {chart_paths['bar']}")
        print(f"   ✅ 레이더 차트: {chart_paths['radar']}")
        
        # 2. DOCX 보고서 생성 (ReportGenerator - Utils)
        print("\n2️⃣ DOCX 보고서 생성 중...")
        
        # docx_generator.py의 실제 시그니처에 맞게 호출
        # generate_report(patent_info, state, chart_paths, output_path)
        safe_patent_number = patent_number.replace('/', '_')
        output_path = output_dir / f"{safe_patent_number}_report_{self.timestamp}.docx"
        
        docx_path = self.report_generator.generate_report(
            patent_info=patent_info,
            state=state,
            chart_paths=chart_paths,
            output_path=str(output_path)
        )
        
        print(f"   ✅ DOCX 보고서: {docx_path}")
        
        return {
            'charts': chart_paths,
            'docx': docx_path
        }
    
    def run(self, pdf_paths: List[str]):
        """전체 파이프라인 실행"""
        print("\n" + "=" * 80)
        print("🎬 특허 평가 파이프라인 시작")
        print("=" * 80)
        print(f"평가 대상: {len(pdf_paths)}개 특허\n")
        
        # 1. RAG 시스템 구축
        self.build_rag_system(pdf_paths)
        
        # 2. PDF 처리
        patent_data = self.process_pdfs(pdf_paths)
        
        # 3. 각 특허 평가
        results = []
        
        for pdf_path in pdf_paths:
            patent_info = patent_data[pdf_path]
            
            # 평가 수행 (Agents에 위임)
            state = self.evaluate_patent(pdf_path, patent_info)
            
            # 출력물 생성 (Utils 사용)
            outputs = self.generate_outputs(state, patent_info)
            
            results.append({
                'patent_number': patent_info['number'],
                'patent_title': patent_info['title'],
                'overall_score': state['overall_score'],
                'grade': state['grade'],
                'outputs': outputs
            })
            
            print("\n" + "─" * 80)
        
        # 최종 요약
        print("\n" + "=" * 80)
        print("🎉 전체 평가 완료!")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['patent_number']}")
            print(f"   명칭: {result['patent_title'][:50]}...")
            print(f"   점수: {result['overall_score']:.1f}점 ({result['grade']})")
            print(f"   보고서: {result['outputs']['docx']}")
        
        return results


def main():
    """메인 함수"""
    # PDF 파일 목록
    pdf_paths = [
        "data/patent1samsung.pdf",
        "data/patent2yanolja.pdf", 
        "data/patent3kakaobank.pdf"
    ]
    
    # 시스템 실행
    system = PatentEvaluationSystem()
    results = system.run(pdf_paths)
    
    print("\n✅ 모든 작업 완료!")
    return results


if __name__ == "__main__":
    main()