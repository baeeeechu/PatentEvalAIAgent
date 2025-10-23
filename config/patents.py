"""
특허 파일 명시적 지정
- 평가할 특허 PDF 파일 목록 관리
"""

# 평가 대상 특허 파일 (data/ 디렉토리 기준)
PATENT_FILES = [
    {
        "filename": "patent1samsung.pdf",
        "company": "삼성생명",
        "tech_area": "LLM 고객상담",
        "priority": "high",
        "description": "LLM 기반 고객상담 시스템의 Hallucination 방지 기술"
    },
    {
        "filename": "patent2yanolja.pdf",
        "company": "야놀자",
        "tech_area": "LLM 고객상담",
        "priority": "medium",
        "description": "숙박 플랫폼 고객 응대 LLM 시스템"
    },
    {
        "filename": "patent3kakaobank.pdf",
        "company": "카카오뱅크",
        "tech_area": "LLM 고객상담",
        "priority": "medium",
        "description": "금융 서비스 AI 챗봇 시스템"
    }
]

# 파일 검증
def validate_patent_files():
    """특허 파일 존재 여부 검증"""
    import os
    missing_files = []
    
    for patent in PATENT_FILES:
        filepath = os.path.join("data", patent["filename"])
        if not os.path.exists(filepath):
            missing_files.append(filepath)
    
    if missing_files:
        print(f"⚠️ 다음 파일을 찾을 수 없습니다:")
        for f in missing_files:
            print(f"   - {f}")
        return False
    
    print(f"✅ 모든 특허 파일 확인 완료 ({len(PATENT_FILES)}개)")
    return True