"""
특허 평가 관련 상수
"""
from pathlib import Path
from typing import List

# 정량 지표 계산 기준
QUANTITATIVE_SCORING = {
    # 권리성 지표
    'X1_IPC_COUNT': {
        'max': 10,
        'scoring': lambda x: min(100, (x / 5) * 100) if x > 0 else 0
    },
    'X2_CLAIMS_COUNT': {
        'max': 20,
        'scoring': lambda x: min(100, (x / 10) * 100) if x > 0 else 0
    },
    'X3_AVG_CLAIM_LENGTH': {
        'max': 300,
        'scoring': lambda x: min(100, (x / 150) * 100) if x > 0 else 0
    },
    'X4_INDEPENDENT_CLAIMS': {
        'max': 10,
        'scoring': lambda x: min(100, (x / 5) * 100) if x > 0 else 0
    },
    'X5_DEPENDENT_CLAIMS': {
        'max': 15,
        'scoring': lambda x: min(100, (x / 10) * 100) if x > 0 else 0
    },
    'X6_DEPENDENCY_DEPTH': {
        'max': 5,
        'scoring': lambda x: min(100, (x / 3) * 100) if x > 0 else 0
    },
    
    # 기술성 지표
    'X7_DRAWING_COUNT': {
        'max': 10,
        'scoring': lambda x: min(100, (x / 5) * 100) if x > 0 else 0
    },
    'X8_TITLE_LENGTH': {
        'max': 50,
        'scoring': lambda x: min(100, (x / 30) * 100) if x > 10 else 0
    },
    'X9_CLAIM_SERIES': {
        'max': 10,
        'scoring': lambda x: min(100, (x / 5) * 100) if x > 0 else 0
    },
    
    # 활용성 지표
    'X10_INVENTORS_COUNT': {
        'max': 10,
        'scoring': lambda x: min(100, (x / 3) * 100) if x > 0 else 0
    },
}

# 이진 체크리스트 항목
BINARY_CHECKLIST = {
    'technology': [
        '도면 수 충족(3개 이상)',
        '발명명칭 길이 적절(10자 이상)',
        '청구항 계열 충족(3개 이상)',
    ],
    'rights': [
        'IPC 코드 다양성',
        '청구항 수 충족',
        '독립항 존재',
    ],
    'market': [
        '발명자 수 충족',
    ]
}

# 특허 파일 목록 (pdfs 폴더에서 자동 탐색)
PATENT_FILES = []


def validate_patent_files() -> List[str]:
    """
    pdfs 폴더에서 PDF 파일들을 찾아서 반환
    """
    pdf_dir = Path("pdfs")
    
    if not pdf_dir.exists():
        print(f"⚠️ 경고: {pdf_dir} 폴더가 없습니다.")
        return []
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ 경고: {pdf_dir} 폴더에 PDF 파일이 없습니다.")
        return []
    
    return [str(f) for f in sorted(pdf_files)]