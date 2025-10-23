"""
특허 평가 결과 시각화
- 막대 그래프 (출원인 표시)
- 레이더 차트 (출원인 표시)
- 한글 폰트 지원
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from typing import Dict, List
import numpy as np
import platform

# 한글 폰트 설정
def set_korean_font():
    """운영체제에 맞는 한글 폰트 설정"""
    system = platform.system()
    
    if system == 'Windows':
        plt.rcParams['font.family'] = 'Malgun Gothic'
    elif system == 'Darwin':
        plt.rcParams['font.family'] = 'AppleGothic'
    else:
        plt.rcParams['font.family'] = 'NanumGothic'
    
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()


class Visualizer:
    """특허 평가 결과 시각화"""
    
    def __init__(self):
        """시각화 도구 초기화"""
        pass
    
    def create_bar_chart(
        self,
        scores: Dict[str, float],
        patent_number: str,
        applicant: str,
        output_dir: str
    ) -> str:
        """
        막대 그래프 생성 (출원인 표시)
        
        Args:
            scores: 점수 딕셔너리 (technology, rights, market, overall)
            patent_number: 특허번호
            applicant: 출원인
            output_dir: 출력 디렉토리
        """
        # 파일명 생성
        safe_patent_number = patent_number.replace('/', '_')
        output_path = Path(output_dir) / f"{safe_patent_number}_bar_chart.png"
        
        # 데이터 준비
        categories = ['기술성\n(35%)', '권리성\n(35%)', '활용성\n(30%)', '종합']
        values = [
            scores.get('technology', 0),
            scores.get('rights', 0),
            scores.get('market', 0),
            scores.get('overall', 0)
        ]
        colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
        
        # 그래프 생성
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(categories, values, color=colors, alpha=0.8, edgecolor='black')
        
        # 값 표시
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f'{height:.1f}',
                ha='center',
                va='bottom',
                fontsize=14,
                fontweight='bold'
            )
        
        # 기준선
        ax.axhline(y=80, color='red', linestyle='--', label='우수 기준 (80점)', linewidth=2, alpha=0.7)
        ax.axhline(y=55, color='orange', linestyle='--', label='기본 기준 (55점)', linewidth=2, alpha=0.7)
        
        # 스타일링
        ax.set_ylim(0, 105)
        ax.set_ylabel('점수', fontsize=12, fontweight='bold')
        ax.set_xlabel('평가 항목', fontsize=12, fontweight='bold')
        
        # 출원인이 길면 줄바꿈
        if len(applicant) > 30:
            applicant = applicant[:30] + '...'
        
        title = f'특허 평가결과 - {patent_number}\n출원인: {applicant}'
        ax.set_title(title, fontsize=13, fontweight='bold', pad=20)
        
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def create_radar_chart(
        self,
        scores: Dict[str, float],
        patent_number: str,
        applicant: str,
        output_dir: str
    ) -> str:
        """
        레이더 차트 생성 (출원인 표시)
        
        Args:
            scores: 점수 딕셔너리 (technology, rights, market, overall)
            patent_number: 특허번호
            applicant: 출원인
            output_dir: 출력 디렉토리
        """
        # 파일명 생성
        safe_patent_number = patent_number.replace('/', '_')
        output_path = Path(output_dir) / f"{safe_patent_number}_radar_chart.png"
        
        # 데이터 준비
        categories = ['기술성\n(35%)', '권리성\n(35%)', '활용성\n(30%)']
        values = [
            scores.get('technology', 0),
            scores.get('rights', 0),
            scores.get('market', 0)
        ]
        
        # 각도 계산
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]
        
        # 그래프 생성
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        # 데이터 플롯
        ax.plot(angles, values, 'o-', linewidth=2, color='#3498db', label='평가 점수')
        ax.fill(angles, values, alpha=0.25, color='#3498db')
        
        # 스타일링
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 출원인이 길면 줄바꿈
        if len(applicant) > 30:
            applicant = applicant[:30] + '...'
        
        title = f'특허 레이더차트 - {patent_number}\n출원인: {applicant}'
        ax.set_title(title, fontsize=13, fontweight='bold', pad=20)
        
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def create_all_charts(
        self,
        scores: Dict[str, float],
        patent_number: str,
        applicant: str,
        output_dir: str
    ) -> Dict[str, str]:
        """모든 차트 생성"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 차트 생성
        bar_path = self.create_bar_chart(scores, patent_number, applicant, str(output_dir))
        radar_path = self.create_radar_chart(scores, patent_number, applicant, str(output_dir))
        
        return {
            "bar": bar_path,
            "radar": radar_path
        }


if __name__ == "__main__":
    # 테스트
    print("시각화 도구 테스트")
    
    visualizer = Visualizer()
    
    test_scores = {
        "technology": 85,
        "rights": 80,
        "market": 75,
        "overall": 82
    }
    
    test_patent_number = "10-2025-0090445"
    test_applicant = "삼성생명보험주식회사"
    
    visualizer.create_all_charts(test_scores, test_patent_number, test_applicant, "test_output")