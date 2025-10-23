"""
기업 R&D 특허 평가 설정
- 기술성 45%, 권리성 35%, 시장성 20%
"""

# 평가 가중치 (R&D 팀 기준)
EVALUATION_WEIGHTS = {
    "technology": 0.45,  # 기술성 (기술 우위성 중심)
    "rights": 0.35,      # 권리성 (특허 방어력)
    "market": 0.20       # 시장성 (참고용)
}

# 재평가 가중치 (점수 < 55점일 때)
RE_EVALUATION_WEIGHTS = {
    "technology": 0.50,  # 기술성 더 강조
    "rights": 0.35,      
    "market": 0.15       # 시장성 최소화
}

# 등급 기준 (내림차순 정렬)
GRADE_THRESHOLDS = [
    ("AAA", 90),
    ("AA", 85),
    ("A", 80),
    ("BBB", 75),
    ("BB", 70),
    ("B", 65),
    ("CCC", 60),
    ("CC", 57),
    ("C", 55),
    ("미달", 0)
]

# 재평가 기준
RE_EVAL_THRESHOLD = 55

def calculate_grade(score: float) -> str:
    """점수를 등급으로 변환"""
    for grade, threshold in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "미달"

def calculate_percentile(score: float) -> float:
    """
    간이 백분위 계산 (정규분포 가정)
    실제로는 과거 특허 데이터베이스와 비교 필요
    """
    # 평균 70, 표준편차 10 가정
    from scipy import stats
    percentile = stats.norm.cdf(score, loc=70, scale=10) * 100
    return round(percentile, 1)

# 평가 항목별 세부 기준 (R&D 팀 관점)
TECH_EVALUATION_CRITERIA = {
    "innovation": 0.30,      # 기술 혁신성
    "technical_depth": 0.25, # 기술 깊이
    "differentiation": 0.25, # 차별성
    "implementation": 0.20   # 구현 완성도
}

RIGHTS_EVALUATION_CRITERIA = {
    "claim_strength": 0.35,    # 청구항 강도
    "protection_scope": 0.30,  # 보호 범위
    "legal_stability": 0.20,   # 법적 안정성
    "ipc_coverage": 0.15       # IPC 커버리지
}

MARKET_EVALUATION_CRITERIA = {
    "applicability": 0.50,      # 실무 적용성
    "market_fit": 0.30,         # 시장 적합성
    "commercialization": 0.20   # 상용화 가능성
}