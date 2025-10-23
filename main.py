"""
특허 평가 시스템 v5.0 - 정량평가 중심 + 구조방정식 모델
- 정량평가 중심: 기술성 60%, 권리성 70%, 활용성 70%
- 32개 평가요소 중 10개 완전 구현 (X1~X10)
- 구조방정식 모델 적용
- Binary 체크리스트 강화
- PDF 원문 기반 (하드코딩 제거)
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️ python-dotenv 패키지가 없습니다. 환경 변수만 사용합니다.")
    print("   설치: poetry add python-dotenv")

# 환경 변수 체크
if not os.getenv("OPENAI_API_KEY"):
    print("\n❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    print("\n해결 방법:")
    print("1. .env 파일 생성 (프로젝트 루트):")
    print("   OPENAI_API_KEY=sk-your-api-key-here")
    print("\n2. 또는 명령어로 설정:")
    print("   Windows: set OPENAI_API_KEY=sk-your-api-key-here")
    print("   Linux/Mac: export OPENAI_API_KEY=sk-your-api-key-here")
    sys.exit(1)
else:
    # API 키 일부만 표시
    api_key = os.getenv("OPENAI_API_KEY")
    masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 11 else "***"
    print(f"✅ OPENAI_API_KEY 확인: {masked_key}\n")

# 모듈 임포트
try:
    from utils import PDFProcessor, PatentRAGManager, Visualizer, PatentReportGenerator
    from agents.tech_agent import TechnologyAgent
    from agents.rights_agent import RightsAgent
    from agents.market_agent import MarketAgent
    from config import EVALUATION_WEIGHTS, PATENT_FILES, calculate_grade
except ImportError as e:
    print(f"⚠️ 모듈 임포트 실패: {e}")
    print("   필요한 패키지를 설치하세요: poetry install")
    sys.exit(1)


def main():
    print("=" * 80)
    print("🚀 특허 평가 시스템 v5.0 - 정량평가 중심 + 구조방정식 모델")
    print("   ✅ 정량평가: 기술성 60%, 권리성 70%, 활용성 70%")
    print("   ✅ 32개 평가요소 중 10개 완전 구현 (X1~X10)")
    print("   ✅ 구조방정식 모델 적용 (투명한 계산식)")
    print("   ✅ Binary 체크리스트 강화")
    print("   ✅ PDF 원문 기반 (하드코딩 제거)")
    print(f"   ✅ 가중치: 기술성 {EVALUATION_WEIGHTS['technology']*100:.0f}%, "
          f"권리성 {EVALUATION_WEIGHTS['rights']*100:.0f}%, "
          f"활용성 {EVALUATION_WEIGHTS['market']*100:.0f}%")
    print("=" * 80)
    print()
    
    # === 1. PDF 파일 수집 (config/patents.py 우선) ===
    pdf_dir = Path("data")
    if not pdf_dir.exists():
        pdf_dir = Path("/mnt/user-data/uploads")
    
    # config/patents.py 파일 사용 시도
    try:
        pdf_files = [pdf_dir / patent['filename'] for patent in PATENT_FILES]
        print(f"📂 config/patents.py에서 {len(pdf_files)}개 특허 로드")
        for patent in PATENT_FILES:
            print(f"   • {patent['filename']} ({patent['company']}, {patent['tech_area']})")
        print()
    except Exception as e:
        # 실패 시 디렉토리 스캔
        print(f"⚠️ config/patents.py 로드 실패: {e}")
        print(f"   디렉토리 스캔으로 전환...")
        pdf_files = list(pdf_dir.glob("*.pdf"))
        print(f"📂 PDF 파일 {len(pdf_files)}개 발견")
        for pdf in pdf_files:
            print(f"   • {pdf.name}")
        print()
    
    if not pdf_files:
        print(f"❌ PDF 파일이 없습니다: {pdf_dir}")
        return
    
    # 파일 존재 확인
    existing_files = [f for f in pdf_files if f.exists()]
    if len(existing_files) < len(pdf_files):
        missing = [f.name for f in pdf_files if not f.exists()]
        print(f"⚠️ 다음 파일을 찾을 수 없습니다:")
        for m in missing:
            print(f"   • {m}")
        pdf_files = existing_files
    
    if not pdf_files:
        print(f"❌ 유효한 PDF 파일이 없습니다.")
        return
    
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    # === 2. PDF 파싱 및 메타데이터 추출 ===
    print("=" * 80)
    print("📄 1단계: PDF 파싱 및 메타데이터 추출")
    print("=" * 80)
    
    patent_info_dict = {}
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{len(pdf_files)}] {pdf_path.name}")
        try:
            processor = PDFProcessor(str(pdf_path))
            patent_info = processor.extract_metadata()
            processor.close()
            
            patent_info_dict[str(pdf_path)] = patent_info
            
            print(f"   ✅ 특허번호: {patent_info.get('number', 'N/A')}")
            print(f"   ✅ 제목: {patent_info.get('title', 'N/A')[:50]}...")
            print(f"   ✅ 출원인: {patent_info.get('applicant', 'N/A')[:30]}...")
            print(f"   ✅ 청구항: {patent_info.get('claims_count', 0)}개")
            print(f"   ✅ IPC: {len(patent_info.get('ipc_codes', []))}개")
            print(f"   ✅ 발명자: {len(patent_info.get('inventors', []))}명")
            
        except Exception as e:
            print(f"   ❌ 파싱 실패: {e}")
            continue
    
    if not patent_info_dict:
        print("\n❌ 파싱된 특허가 없습니다.")
        return
    
    # === 3. RAG 시스템 구축 ===
    print("\n" + "=" * 80)
    print("🔨 2단계: RAG 시스템 구축 (청킹 + 임베딩 + FAISS)")
    print("=" * 80)
    print()
    
    rag_manager = PatentRAGManager(
        embedding_model="nlpai-lab/KoE5",
        chunk_size=1000,
        chunk_overlap=200
    )
    
    build_info = rag_manager.build_from_pdfs([str(p) for p in pdf_files if p.exists()])
    
    print(f"\n✅ RAG 구축 완료!")
    print(f"   • 총 특허: {build_info['total_patents']}개")
    print(f"   • 총 청크: {build_info['total_chunks']}개")
    print(f"   • 평균 청크/특허: {build_info['total_chunks'] / build_info['total_patents']:.1f}개")
    
    # RAG 인덱스 저장 (선택)
    try:
        rag_manager.save_index()
        print(f"   • 인덱스 저장: faiss_index/")
    except Exception as e:
        print(f"   ⚠️ 인덱스 저장 실패: {e}")
    
    # === 4. 에이전트 초기화 ===
    print("\n" + "=" * 80)
    print("🤖 3단계: AI 에이전트 초기화 (v5.0)")
    print("=" * 80)
    print()
    
    tech_agent = TechnologyAgent(model_name="gpt-4o-mini")
    rights_agent = RightsAgent(model_name="gpt-4o-mini")
    market_agent = MarketAgent(model_name="gpt-4o-mini")
    
    print("✅ 에이전트 준비 완료:")
    print(f"   • 기술성 평가 (정량 60% + 정성 40%, 가중치 {EVALUATION_WEIGHTS['technology']*100:.0f}%)")
    print(f"   • 권리성 평가 (정량 70% + 정성 30%, 가중치 {EVALUATION_WEIGHTS['rights']*100:.0f}%)")
    print(f"   • 활용성 평가 (정량+웹서치 70% + 정성 30%, 가중치 {EVALUATION_WEIGHTS['market']*100:.0f}%)")
    
    # === 5. 특허별 평가 수행 ===
    print("\n" + "=" * 80)
    print("⚡ 4단계: 특허별 AI 평가 수행")
    print("=" * 80)
    
    visualizer = Visualizer()
    report_generator = PatentReportGenerator()
    
    for idx, (pdf_path, patent_info) in enumerate(patent_info_dict.items(), 1):
        print(f"\n{'=' * 80}")
        print(f"[{idx}/{len(patent_info_dict)}] {Path(pdf_path).name}")
        print(f"특허번호: {patent_info.get('number', 'N/A')}")
        print(f"제목: {patent_info.get('title', 'N/A')[:60]}...")
        print("=" * 80)
        
        # State 초기화 (v5.0용 확장)
        state = {
            "current_patent": pdf_path,
            "patent_info": patent_info_dict,
            "rag_manager": rag_manager,
            
            # 기본 점수
            "tech_score": 0,
            "rights_score": 0,
            "market_score": 0,
            
            # 기술성 상세
            "tech_quantitative": {},
            "tech_qualitative": {},
            "tech_metrics": {},
            "tech_binary": {},
            "tech_insights": "",
            
            # 권리성 상세
            "rights_quantitative": {},
            "rights_qualitative": {},
            "rights_metrics": {},
            "rights_binary": {},
            "rights_insights": "",
            
            # 활용성 상세
            "market_quantitative": {},
            "market_qualitative": {},
            "market_metrics": {},
            "market_binary": {},
            "market_web_search": {},
            "market_insights": "",
        }
        
        try:
            # 3개 에이전트 순차 평가
            print("\n🔬 [1/3] 기술성 평가...")
            state = tech_agent.evaluate(state)
            
            print("\n⚖️  [2/3] 권리성 평가...")
            state = rights_agent.evaluate(state)
            
            print("\n📊 [3/3] 활용성 평가 (웹 서치 포함)...")
            state = market_agent.evaluate(state)
            
            # 종합 점수 계산 (config/weights.py 기준)
            overall_score = (
                state['tech_score'] * EVALUATION_WEIGHTS['technology'] +
                state['rights_score'] * EVALUATION_WEIGHTS['rights'] +
                state['market_score'] * EVALUATION_WEIGHTS['market']
            )
            
            # 등급 산정 (config/weights.py 함수 사용)
            final_grade = calculate_grade(overall_score)
            
            state['overall_score'] = overall_score
            state['final_grade'] = final_grade
            
            print("\n" + "=" * 80)
            print("📊 평가 결과 요약")
            print("=" * 80)
            print(f"✅ 기술성: {state['tech_score']:.1f}점 (정량 {state['tech_quantitative'].get('total', 0):.1f} + 정성 {state['tech_qualitative'].get('qualitative_score', 0):.1f})")
            print(f"✅ 권리성: {state['rights_score']:.1f}점 (정량 {state['rights_quantitative'].get('total', 0):.1f} + 정성 {state['rights_qualitative'].get('qualitative_score', 0):.1f})")
            print(f"✅ 활용성: {state['market_score']:.1f}점 (정량+웹서치 {state['market_quantitative'].get('total', 0):.1f} + 정성 {state['market_qualitative'].get('qualitative_score', 0):.1f})")
            print(f"🏆 종합 점수: {overall_score:.1f}점")
            print(f"🎖️  최종 등급: {final_grade}")
            print("=" * 80)
            
            # 차트 생성
            print("\n📈 차트 생성 중...")
            chart_scores = {
                "technology": state['tech_score'],
                "rights": state['rights_score'],
                "market": state['market_score'],
                "overall": overall_score
            }
            
            patent_number = patent_info.get('number', 'unknown')
            safe_patent_number = patent_number.replace('/', '_')
            
            chart_paths = visualizer.create_all_charts(
                chart_scores,
                patent_number,
                patent_info.get('applicant', 'N/A'),
                str(output_dir)
            )
            
            state['chart_paths'] = chart_paths
            
            print(f"   ✅ 차트 저장:")
            print(f"      • {Path(chart_paths['bar']).name}")
            print(f"      • {Path(chart_paths['radar']).name}")
            
            # DOCX 보고서 생성 (v5.0용 - Reference/Appendix 포함)
            print("\n📝 DOCX 보고서 생성 중...")
            docx_path = output_dir / f"{safe_patent_number}_report.docx"
            
            report_generator.generate_report(
                patent_info=patent_info,
                state=state,
                chart_paths=chart_paths,
                output_path=str(docx_path)
            )
            
            print(f"   ✅ DOCX 보고서: {docx_path.name}")
            
        except Exception as e:
            print(f"\n❌ 평가 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # === 6. 완료 ===
    print("\n" + "=" * 80)
    print("✅ 모든 처리 완료!")
    print("=" * 80)
    print(f"📂 결과 파일 위치: {output_dir.absolute()}")
    print()
    print("📊 생성된 파일:")
    for file in output_dir.glob("*"):
        if file.is_file():
            print(f"   • {file.name}")
    print()
    print("=" * 80)
    print("🎯 시스템 특징 (v5.0):")
    print("   ✅ 정량평가 중심: 기술성 60%, 권리성 70%, 활용성 70%")
    print("   ✅ 32개 평가요소 중 10개 완전 구현 (X1~X10)")
    print("   ✅ 구조방정식 모델: 투명한 계산식")
    print("   ✅ Binary 체크리스트: True/False 판정")
    print("   ✅ PDF 원문 기반: 하드코딩 제거")
    print("   ✅ 웹 서치: 출원인 시장 지위 + IPC 성장성")
    print(f"   ✅ 가중치: {EVALUATION_WEIGHTS['technology']*100:.0f}%/{EVALUATION_WEIGHTS['rights']*100:.0f}%/{EVALUATION_WEIGHTS['market']*100:.0f}% (R&D 팀 기준)")
    print("=" * 80)


if __name__ == "__main__":
    main()