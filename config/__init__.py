# config/__init__.py
"""
Config Package v5.0
- 평가 가중치 설정
- 특허 파일 목록 관리
"""

from .weights import (
    EVALUATION_WEIGHTS,
    RE_EVALUATION_WEIGHTS,
    GRADE_THRESHOLDS,
    RE_EVAL_THRESHOLD,
    calculate_grade,
    calculate_percentile,
    TECH_EVALUATION_CRITERIA,
    RIGHTS_EVALUATION_CRITERIA,
    MARKET_EVALUATION_CRITERIA
)

from .patents import (
    PATENT_FILES,
    validate_patent_files,
    QUANTITATIVE_SCORING,
    BINARY_CHECKLIST
)

__all__ = [
    # 가중치
    "EVALUATION_WEIGHTS",
    "RE_EVALUATION_WEIGHTS",
    "GRADE_THRESHOLDS",
    "RE_EVAL_THRESHOLD",
    "calculate_grade",
    "calculate_percentile",
    
    # 세부 기준
    "TECH_EVALUATION_CRITERIA",
    "RIGHTS_EVALUATION_CRITERIA",
    "MARKET_EVALUATION_CRITERIA",
    
    # 특허 파일
    "PATENT_FILES",
    "validate_patent_files",
    "QUANTITATIVE_SCORING",
    "BINARY_CHECKLIST"
]