"""
DOCX 보고서 생성기 v5.0 - Reference & Appendix 추가
- 정량평가 상세 표시
- 구조방정식 모델 명시
- Reference: 참고 문서 출처
- Appendix: 평가 지표 상세
"""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class PatentReportGenerator:
    """특허 평가 DOCX 보고서 생성기 v5.0"""
    
    def __init__(self):
        pass
    
    def generate_report(
        self,
        patent_info: Dict[str, Any],
        state: Dict[str, Any],
        chart_paths: Dict[str, str],
        output_path: str
    ) -> str:
        """
        보고서 생성
        
        Args:
            patent_info: PDF에서 추출한 특허 정보
            state: 에이전트 평가 결과 (v5.0 확장 구조)
            chart_paths: 차트 파일 경로들
            output_path: 출력 경로
        """
        doc = Document()
        self._set_korean_font(doc)
        
        # 1. 표지
        self._add_cover_page(doc, patent_info, state)
        doc.add_page_break()
        
        # 2. Executive Summary
        self._add_executive_summary(doc, patent_info, state)
        doc.add_page_break()
        
        # 3. 평가 결과 시각화
        self._add_evaluation_charts(doc, chart_paths)
        doc.add_page_break()
        
        # 4. 기술성 평가 (v5.0 - 정량/정성 분리)
        self._add_technology_evaluation_v5(doc, state)
        doc.add_page_break()
        
        # 5. 권리성 평가 (v5.0 - 정량/정성 분리)
        self._add_rights_evaluation_v5(doc, state)
        doc.add_page_break()
        
        # 6. 활용성 평가 (v5.0 - 웹서치 포함)
        self._add_market_evaluation_v5(doc, state)
        doc.add_page_break()
        
        # 7. 종합 평가 및 제언
        self._add_recommendations(doc, state)
        doc.add_page_break()
        
        # 8. Reference (v5.0 신규)
        self._add_references_v5(doc, patent_info, state)
        doc.add_page_break()
        
        # 9. Appendix (v5.0 신규)
        self._add_appendix_v5(doc, state)
        
        # 저장
        doc.save(output_path)
        return output_path
    
    def _set_korean_font(self, doc: Document):
        """한글 폰트 설정"""
        style = doc.styles['Normal']
        font = style.font
        font.name = '맑은 고딕'
        font.size = Pt(10)
        
        rFonts = style.element.rPr.rFonts
        rFonts.set(qn('w:eastAsia'), '맑은 고딕')
    
    def _add_cover_page(self, doc: Document, patent_info: Dict, state: Dict):
        """표지 페이지"""
        # 제목
        title = doc.add_heading('특허 기술 평가 보고서', level=0)
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        doc.add_paragraph()
        doc.add_paragraph()
        
        # 특허 정보
        p = doc.add_paragraph()
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        run = p.add_run(f"특허번호: {patent_info.get('number', 'N/A')}\n\n")
        run.font.size = Pt(14)
        run.font.bold = True
        
        run = p.add_run(f"{patent_info.get('title', 'N/A')}\n\n")
        run.font.size = Pt(12)
        
        run = p.add_run(f"출원인: {patent_info.get('applicant', 'N/A')}\n")
        run.font.size = Pt(11)
        
        doc.add_paragraph()
        doc.add_paragraph()
        
        # 평가 결과 요약
        p = doc.add_paragraph()
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        overall_score = state.get('overall_score', 0)
        final_grade = state.get('final_grade', 'N/A')
        
        run = p.add_run(f"종합 점수: {overall_score:.1f}점\n")
        run.font.size = Pt(16)
        run.font.bold = True
        
        run = p.add_run(f"최종 등급: {final_grade}\n\n")
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 102, 204)
        
        # 날짜
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        run = p.add_run(f"평가일: {datetime.now().strftime('%Y년 %m월 %d일')}")
        run.font.size = Pt(10)
        
        # v5.0 표시
        p = doc.add_paragraph()
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        run = p.add_run("평가 시스템 v5.0 (정량평가 중심)")
        run.font.size = Pt(9)
        run.font.italic = True
        run.font.color.rgb = RGBColor(128, 128, 128)
    
    def _add_executive_summary(self, doc: Document, patent_info: Dict, state: Dict):
        """Executive Summary"""
        doc.add_heading('Executive Summary', level=1)
        
        # 종합 평가
        doc.add_heading('1. 종합 평가', level=2)
        
        overall_score = state.get('overall_score', 0)
        final_grade = state.get('final_grade', 'N/A')
        tech_score = state.get('tech_score', 0)
        rights_score = state.get('rights_score', 0)
        market_score = state.get('market_score', 0)
        
        p = doc.add_paragraph()
        p.add_run(f"• 종합 점수: ").bold = True
        p.add_run(f"{overall_score:.1f}점 ({final_grade})\n")
        
        p.add_run(f"• 기술성: ").bold = True
        p.add_run(f"{tech_score:.1f}점\n")
        
        p.add_run(f"• 권리성: ").bold = True
        p.add_run(f"{rights_score:.1f}점\n")
        
        p.add_run(f"• 활용성: ").bold = True
        p.add_run(f"{market_score:.1f}점\n")
        
        # v5.0 정량/정성 표시
        doc.add_paragraph()
        doc.add_heading('2. 평가 방법 (v5.0)', level=2)
        
        p = doc.add_paragraph()
        p.add_run("본 평가는 정량평가 중심으로 수행되었습니다:\n")
        p.add_run("• 기술성: ").bold = True
        p.add_run(f"정량 60% + 정성(LLM) 40%\n")
        p.add_run("• 권리성: ").bold = True
        p.add_run(f"정량 70% + 정성(LLM) 30%\n")
        p.add_run("• 활용성: ").bold = True
        p.add_run(f"정량+웹서치 70% + 정성(LLM) 30%\n")
        
        # 특허 기본 정보
        doc.add_heading('3. 특허 기본 정보', level=2)
        
        p = doc.add_paragraph()
        p.add_run(f"• 특허번호: ").bold = True
        p.add_run(f"{patent_info.get('number', 'N/A')}\n")
        
        p.add_run(f"• 출원인: ").bold = True
        p.add_run(f"{patent_info.get('applicant', 'N/A')}\n")
        
        p.add_run(f"• 청구항 수: ").bold = True
        p.add_run(f"{patent_info.get('claims_count', 0)}개\n")
        
        p.add_run(f"• IPC 코드: ").bold = True
        ipc_codes = patent_info.get('ipc_codes', [])
        p.add_run(f"{', '.join(ipc_codes[:5])}\n")
        
        p.add_run(f"• 발명자 수: ").bold = True
        p.add_run(f"{len(patent_info.get('inventors', []))}명\n")
    
    def _add_evaluation_charts(self, doc: Document, chart_paths: Dict[str, str]):
        """평가 결과 시각화"""
        doc.add_heading('평가 결과 시각화', level=1)
        
        # 막대 차트
        if 'bar' in chart_paths and Path(chart_paths['bar']).exists():
            doc.add_paragraph('평가 영역별 점수', style='Heading 2')
            doc.add_picture(chart_paths['bar'], width=Inches(6))
            doc.add_paragraph()
        
        # 레이더 차트
        if 'radar' in chart_paths and Path(chart_paths['radar']).exists():
            doc.add_paragraph('종합 평가 레이더 차트', style='Heading 2')
            doc.add_picture(chart_paths['radar'], width=Inches(5))
    
    def _add_technology_evaluation_v5(self, doc: Document, state: Dict):
        """기술성 평가 (v5.0 - 정량/정성 분리)"""
        doc.add_heading('기술성 평가', level=1)
        
        tech_score = state.get('tech_score', 0)
        tech_quantitative = state.get('tech_quantitative', {})
        tech_qualitative = state.get('tech_qualitative', {})
        tech_metrics = state.get('tech_metrics', {})
        tech_binary = state.get('tech_binary', {})
        
        # 최종 점수
        doc.add_heading(f'최종 점수: {tech_score:.1f}/100', level=2)
        
        p = doc.add_paragraph()
        p.add_run("• 정량 평가 (60%): ").bold = True
        p.add_run(f"{tech_quantitative.get('total', 0):.1f}점\n")
        
        p.add_run("• 정성 평가 (40%): ").bold = True
        p.add_run(f"{tech_qualitative.get('qualitative_score', 0):.1f}점\n")
        
        # 정량 지표 상세
        doc.add_heading('1. 정량 지표 (PDF 원문 기반)', level=2)
        
        p = doc.add_paragraph()
        p.add_run(f"X7. 도면 수: ").bold = True
        p.add_run(f"{tech_metrics.get('X7_drawing_count', 0)}개 ")
        p.add_run(f"→ {tech_quantitative.get('drawing_score', 0):.1f}점\n")
        
        p.add_run(f"X8. 발명명칭 길이: ").bold = True
        p.add_run(f"{tech_metrics.get('X8_title_length', 0)}자 ")
        p.add_run(f"→ {tech_quantitative.get('title_score', 0):.1f}점\n")
        
        p.add_run(f"X9. 청구항 계열 수: ").bold = True
        p.add_run(f"{tech_metrics.get('X9_claim_series', 0)}개 ")
        p.add_run(f"→ {tech_quantitative.get('series_score', 0):.1f}점\n")
        
        # 구조방정식 모델
        doc.add_heading('2. 구조방정식 모델', level=2)
        
        p = doc.add_paragraph()
        drawing_score = tech_quantitative.get('drawing_score', 0)
        title_score = tech_quantitative.get('title_score', 0)
        series_score = tech_quantitative.get('series_score', 0)
        quant_total = tech_quantitative.get('total', 0)
        qual_score = tech_qualitative.get('qualitative_score', 0)
        
        p.add_run(f"정량 점수 = X7(도면) × 0.4 + X8(명칭) × 0.3 + X9(계열) × 0.3\n")
        p.add_run(f"          = {drawing_score:.1f} × 0.4 + {title_score:.1f} × 0.3 + {series_score:.1f} × 0.3\n")
        p.add_run(f"          = {quant_total:.1f}점\n\n")
        
        p.add_run(f"최종 점수 = 정량({quant_total:.1f}) × 60% + 정성({qual_score:.1f}) × 40%\n")
        p.add_run(f"          = {tech_score:.1f}점\n")
        
        # Binary 체크리스트
        doc.add_heading('3. Binary 체크리스트', level=2)
        
        p = doc.add_paragraph()
        for key, value in tech_binary.items():
            status = "✓" if value else "✗"
            p.add_run(f"{status} {key}\n")
        
        # 정성 평가 (LLM)
        doc.add_heading('4. 정성 평가 (LLM)', level=2)
        
        strengths = tech_qualitative.get('strengths', [])
        weaknesses = tech_qualitative.get('weaknesses', [])
        
        if strengths:
            doc.add_paragraph('강점:', style='Heading 3')
            for s in strengths:
                doc.add_paragraph(f"• {s}", style='List Bullet')
        
        if weaknesses:
            doc.add_paragraph('약점:', style='Heading 3')
            for w in weaknesses:
                doc.add_paragraph(f"• {w}", style='List Bullet')
    
    def _add_rights_evaluation_v5(self, doc: Document, state: Dict):
        """권리성 평가 (v5.0 - 정량/정성 분리)"""
        doc.add_heading('권리성 평가', level=1)
        
        rights_score = state.get('rights_score', 0)
        rights_quantitative = state.get('rights_quantitative', {})
        rights_qualitative = state.get('rights_qualitative', {})
        rights_metrics = state.get('rights_metrics', {})
        rights_binary = state.get('rights_binary', {})
        
        # 최종 점수
        doc.add_heading(f'최종 점수: {rights_score:.1f}/100', level=2)
        
        p = doc.add_paragraph()
        p.add_run("• 정량 평가 (70%): ").bold = True
        p.add_run(f"{rights_quantitative.get('total', 0):.1f}점\n")
        
        p.add_run("• 정성 평가 (30%): ").bold = True
        p.add_run(f"{rights_qualitative.get('qualitative_score', 0):.1f}점\n")
        
        # 정량 지표 상세
        doc.add_heading('1. 정량 지표 (PDF 원문 기반)', level=2)
        
        p = doc.add_paragraph()
        p.add_run(f"X1. IPC 수: ").bold = True
        p.add_run(f"{rights_metrics.get('X1_ipc_count', 0)}개 ")
        p.add_run(f"→ {rights_quantitative.get('ipc_score', 0):.1f}점\n")
        
        p.add_run(f"X2. 독립항 수: ").bold = True
        p.add_run(f"{rights_metrics.get('X2_independent_claims', 0)}개\n")
        
        p.add_run(f"X3. 종속항 수: ").bold = True
        p.add_run(f"{rights_metrics.get('X3_dependent_claims', 0)}개\n")
        
        p.add_run(f"X4. 전체 청구항 수: ").bold = True
        p.add_run(f"{rights_metrics.get('X4_total_claims', 0)}개 ")
        p.add_run(f"→ {rights_quantitative.get('claims_count_score', 0):.1f}점\n")
        
        p.add_run(f"X5. 독립항 평균 길이: ").bold = True
        p.add_run(f"{rights_metrics.get('X5_independent_avg_length', 0):.1f}자 ")
        p.add_run(f"→ {rights_quantitative.get('claims_length_score', 0):.1f}점\n")
        
        p.add_run(f"X6. 종속항 평균 길이: ").bold = True
        p.add_run(f"{rights_metrics.get('X6_dependent_avg_length', 0):.1f}자\n")
        
        # 구조방정식 모델
        doc.add_heading('2. 구조방정식 모델', level=2)
        
        p = doc.add_paragraph()
        ipc_score = rights_quantitative.get('ipc_score', 0)
        claims_count = rights_quantitative.get('claims_count_score', 0)
        claims_length = rights_quantitative.get('claims_length_score', 0)
        hierarchy = rights_quantitative.get('hierarchy_score', 0)
        quant_total = rights_quantitative.get('total', 0)
        qual_score = rights_qualitative.get('qualitative_score', 0)
        
        p.add_run(f"정량 = IPC(25%) + 청구항개수(30%) + 청구항길이(25%) + 계층구조(20%)\n")
        p.add_run(f"     = {ipc_score:.1f} × 0.25 + {claims_count:.1f} × 0.30 + {claims_length:.1f} × 0.25 + {hierarchy:.1f} × 0.20\n")
        p.add_run(f"     = {quant_total:.1f}점\n\n")
        
        p.add_run(f"최종 = 정량({quant_total:.1f}) × 70% + 정성({qual_score:.1f}) × 30%\n")
        p.add_run(f"     = {rights_score:.1f}점\n")
        
        # Binary 체크리스트
        doc.add_heading('3. Binary 체크리스트', level=2)
        
        p = doc.add_paragraph()
        for key, value in rights_binary.items():
            status = "✓" if value else "✗"
            p.add_run(f"{status} {key}\n")
        
        # 정성 평가 (LLM)
        doc.add_heading('4. 정성 평가 (LLM)', level=2)
        
        strengths = rights_qualitative.get('strengths', [])
        weaknesses = rights_qualitative.get('weaknesses', [])
        
        if strengths:
            doc.add_paragraph('강점:', style='Heading 3')
            for s in strengths:
                doc.add_paragraph(f"• {s}", style='List Bullet')
        
        if weaknesses:
            doc.add_paragraph('약점:', style='Heading 3')
            for w in weaknesses:
                doc.add_paragraph(f"• {w}", style='List Bullet')
    
    def _add_market_evaluation_v5(self, doc: Document, state: Dict):
        """활용성 평가 (v5.0 - 웹서치 포함)"""
        doc.add_heading('활용성 평가', level=1)
        
        market_score = state.get('market_score', 0)
        market_quantitative = state.get('market_quantitative', {})
        market_qualitative = state.get('market_qualitative', {})
        market_metrics = state.get('market_metrics', {})
        market_binary = state.get('market_binary', {})
        market_web_search = state.get('market_web_search', {})
        
        # 최종 점수
        doc.add_heading(f'최종 점수: {market_score:.1f}/100', level=2)
        
        p = doc.add_paragraph()
        p.add_run("• 정량+웹서치 (70%): ").bold = True
        p.add_run(f"{market_quantitative.get('total', 0):.1f}점\n")
        
        p.add_run("• 정성 평가 (30%): ").bold = True
        p.add_run(f"{market_qualitative.get('qualitative_score', 0):.1f}점\n")
        
        # 정량 지표
        doc.add_heading('1. 정량 지표 (PDF 원문 기반)', level=2)
        
        p = doc.add_paragraph()
        p.add_run(f"X10. 발명자 수: ").bold = True
        p.add_run(f"{market_metrics.get('X10_inventor_count', 0)}명 ")
        p.add_run(f"→ {market_quantitative.get('inventor_score', 0):.1f}점\n")
        
        # 웹 서치 결과
        doc.add_heading('2. 웹 서치 결과', level=2)
        
        p = doc.add_paragraph()
        p.add_run(f"출원인 시장 지위: ").bold = True
        p.add_run(f"{market_web_search.get('applicant_grade', 'Unknown')} ")
        p.add_run(f"→ {market_quantitative.get('applicant_score', 0):.1f}점\n")
        p.add_run(f"   {market_web_search.get('applicant_summary', 'N/A')}\n\n")
        
        p.add_run(f"기술 분야 성장성: ").bold = True
        p.add_run(f"{market_web_search.get('tech_grade', 'Unknown')} ")
        p.add_run(f"→ {market_quantitative.get('tech_field_score', 0):.1f}점\n")
        p.add_run(f"   {market_web_search.get('tech_summary', 'N/A')}\n")
        
        # 구조방정식 모델
        doc.add_heading('3. 구조방정식 모델', level=2)
        
        p = doc.add_paragraph()
        inventor_score = market_quantitative.get('inventor_score', 0)
        applicant_score = market_quantitative.get('applicant_score', 0)
        tech_field_score = market_quantitative.get('tech_field_score', 0)
        quant_total = market_quantitative.get('total', 0)
        qual_score = market_qualitative.get('qualitative_score', 0)
        
        p.add_run(f"정량+웹서치 = 발명자(30%) + 출원인(40%) + 기술분야(30%)\n")
        p.add_run(f"            = {inventor_score:.1f} × 0.30 + {applicant_score:.1f} × 0.40 + {tech_field_score:.1f} × 0.30\n")
        p.add_run(f"            = {quant_total:.1f}점\n\n")
        
        p.add_run(f"최종 = (정량+웹서치)({quant_total:.1f}) × 70% + 정성({qual_score:.1f}) × 30%\n")
        p.add_run(f"     = {market_score:.1f}점\n")
        
        # Binary 체크리스트
        doc.add_heading('4. Binary 체크리스트', level=2)
        
        p = doc.add_paragraph()
        for key, value in market_binary.items():
            status = "✓" if value else "✗"
            p.add_run(f"{status} {key}\n")
        
        # 정성 평가 (LLM)
        doc.add_heading('5. 정성 평가 (LLM)', level=2)
        
        p = doc.add_paragraph()
        p.add_run("실무 적용성:\n").bold = True
        p.add_run(f"{market_qualitative.get('applicability_summary', 'N/A')}\n\n")
        
        p.add_run("시장 적합성:\n").bold = True
        p.add_run(f"{market_qualitative.get('market_fit_summary', 'N/A')}\n\n")
        
        p.add_run("상용화 가능성:\n").bold = True
        p.add_run(f"{market_qualitative.get('commercialization_summary', 'N/A')}\n")
    
    def _add_recommendations(self, doc: Document, state: Dict):
        """종합 평가 및 제언"""
        doc.add_heading('종합 평가 및 제언', level=1)
        
        overall_score = state.get('overall_score', 0)
        final_grade = state.get('final_grade', 'N/A')
        
        doc.add_heading('1. 종합 의견', level=2)
        
        p = doc.add_paragraph()
        p.add_run(f"본 특허는 종합 {overall_score:.1f}점({final_grade})으로 평가되었습니다. ")
        
        if overall_score >= 80:
            p.add_run("매우 우수한 특허로서 기술성, 권리성, 활용성 모든 면에서 높은 점수를 받았습니다.")
        elif overall_score >= 70:
            p.add_run("우수한 특허로서 활용 가치가 높습니다.")
        elif overall_score >= 60:
            p.add_run("양호한 특허이나 일부 개선이 필요합니다.")
        else:
            p.add_run("개선이 필요한 특허입니다.")
        
        doc.add_heading('2. 제언', level=2)
        
        tech_score = state.get('tech_score', 0)
        rights_score = state.get('rights_score', 0)
        market_score = state.get('market_score', 0)
        
        # 점수에 따른 제언
        if tech_score < 70:
            doc.add_paragraph("• 기술성 강화: 구현 방법 상세화, 실험 데이터 추가", style='List Bullet')
        
        if rights_score < 70:
            doc.add_paragraph("• 권리성 강화: 청구항 보완, 종속항 추가", style='List Bullet')
        
        if market_score < 70:
            doc.add_paragraph("• 활용성 강화: 시장 검증, POC 수행", style='List Bullet')
    
    def _add_references_v5(self, doc: Document, patent_info: Dict, state: Dict):
        """Reference - 참고 문서 (v5.0 신규)"""
        doc.add_heading('Reference - 참고 문서', level=1)
        
        doc.add_heading('1. 특허 원문', level=2)
        p = doc.add_paragraph()
        p.add_run(f"• 특허번호: {patent_info.get('number', 'N/A')}\n")
        p.add_run(f"• 발명명칭: {patent_info.get('title', 'N/A')}\n")
        p.add_run(f"• 출원인: {patent_info.get('applicant', 'N/A')}\n")
        
        doc.add_heading('2. 웹 서치 출처', level=2)
        market_web_search = state.get('market_web_search', {})
        
        p = doc.add_paragraph()
        p.add_run("• 출원인 정보:\n")
        p.add_run(f"  {market_web_search.get('applicant_summary', 'N/A')}\n")
        p.add_run(f"  출처: DuckDuckGo 검색 (실시간)\n\n")
        
        p.add_run("• 기술 분야 정보:\n")
        p.add_run(f"  {market_web_search.get('tech_summary', 'N/A')}\n")
        p.add_run(f"  출처: DuckDuckGo 검색 (실시간)\n")
        
        doc.add_heading('3. 평가 모델', level=2)
        p = doc.add_paragraph()
        p.add_run("• 평가 시스템: 특허 평가 시스템 v5.0\n")
        p.add_run("• 평가 방법: 정량평가 중심 (기술성 60%, 권리성 70%, 활용성 70%)\n")
        p.add_run("• RAG 모델: nlpai-lab/KoE5 (HuggingFace)\n")
        p.add_run("• LLM 모델: GPT-4o-mini (OpenAI)\n")
    
    def _add_appendix_v5(self, doc: Document, state: Dict):
        """Appendix - 평가 지표 상세 (v5.0 신규)"""
        doc.add_heading('Appendix - 평가 지표 상세', level=1)
        
        doc.add_heading('1. 정량 지표 (10개)', level=2)
        
        tech_metrics = state.get('tech_metrics', {})
        rights_metrics = state.get('rights_metrics', {})
        market_metrics = state.get('market_metrics', {})
        
        # 표 생성
        table = doc.add_table(rows=11, cols=4)
        table.style = 'Light Grid Accent 1'
        
        # 헤더
        header_cells = table.rows[0].cells
        header_cells[0].text = '지표'
        header_cells[1].text = '측정값'
        header_cells[2].text = '범주'
        header_cells[3].text = 'Agent'
        
        # 데이터
        data = [
            ('X1. IPC 수', f"{rights_metrics.get('X1_ipc_count', 0)}개", '권리성', 'rights'),
            ('X2. 독립항 수', f"{rights_metrics.get('X2_independent_claims', 0)}개", '권리성', 'rights'),
            ('X3. 종속항 수', f"{rights_metrics.get('X3_dependent_claims', 0)}개", '권리성', 'rights'),
            ('X4. 전체 청구항 수', f"{rights_metrics.get('X4_total_claims', 0)}개", '권리성', 'rights'),
            ('X5. 독립항 평균 길이', f"{rights_metrics.get('X5_independent_avg_length', 0):.1f}자", '권리성', 'rights'),
            ('X6. 종속항 평균 길이', f"{rights_metrics.get('X6_dependent_avg_length', 0):.1f}자", '권리성', 'rights'),
            ('X7. 도면 수', f"{tech_metrics.get('X7_drawing_count', 0)}개", '기술성', 'tech'),
            ('X8. 발명명칭 길이', f"{tech_metrics.get('X8_title_length', 0)}자", '기술성', 'tech'),
            ('X9. 청구항 계열 수', f"{tech_metrics.get('X9_claim_series', 0)}개", '기술성', 'tech'),
            ('X10. 발명자 수', f"{market_metrics.get('X10_inventor_count', 0)}명", '활용성', 'market'),
        ]
        
        for i, (label, value, category, agent) in enumerate(data, start=1):
            cells = table.rows[i].cells
            cells[0].text = label
            cells[1].text = value
            cells[2].text = category
            cells[3].text = agent
        
        doc.add_paragraph()
        
        doc.add_heading('2. 구조방정식 모델', level=2)
        
        p = doc.add_paragraph()
        p.add_run("기술성 = X7(도면) × 0.4 + X8(명칭) × 0.3 + X9(계열) × 0.3\n")
        p.add_run("권리성 = IPC(25%) + 청구항개수(30%) + 청구항길이(25%) + 계층구조(20%)\n")
        p.add_run("활용성 = 발명자(30%) + 출원인(40%) + 기술분야(30%)\n\n")
        p.add_run("종합 = 기술성(45%) + 권리성(35%) + 활용성(20%)\n")
        
        doc.add_heading('3. Binary 체크리스트', level=2)
        
        tech_binary = state.get('tech_binary', {})
        rights_binary = state.get('rights_binary', {})
        market_binary = state.get('market_binary', {})
        
        p = doc.add_paragraph()
        p.add_run("기술성:\n").bold = True
        for key, value in tech_binary.items():
            status = "✓" if value else "✗"
            p.add_run(f"  {status} {key}\n")
        
        p.add_run("\n권리성:\n").bold = True
        for key, value in rights_binary.items():
            status = "✓" if value else "✗"
            p.add_run(f"  {status} {key}\n")
        
        p.add_run("\n활용성:\n").bold = True
        for key, value in market_binary.items():
            status = "✓" if value else "✗"
            p.add_run(f"  {status} {key}\n")
        
        doc.add_heading('4. 평가 기준', level=2)
        
        p = doc.add_paragraph()
        p.add_run("AAA (90점 이상): 최고 수준\n")
        p.add_run("AA (85-89점): 매우 우수\n")
        p.add_run("A (80-84점): 우수\n")
        p.add_run("BBB (75-79점): 양호\n")
        p.add_run("BB (70-74점): 보통 상위\n")
        p.add_run("B (65-69점): 보통\n")
        p.add_run("CCC (60-64점): 보통 하위\n")
        p.add_run("CC (57-59점): 미흡\n")
        p.add_run("C (55-56점): 개선 필요\n")
        p.add_run("미달 (55점 미만): 재평가 필요\n")


if __name__ == "__main__":
    print("DOCX 보고서 생성기 v5.0 - Reference & Appendix 포함")