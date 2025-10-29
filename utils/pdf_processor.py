"""
PDF 처리 모듈 v6.0 - 한국 특허 문서 최적화
- 한글 특허공보 포맷 정확히 파싱
- 정량 지표 완벽 추출 (X1~X10)
"""
import re
import logging
from typing import Dict, List, Tuple
from pathlib import Path
import pdfplumber

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 처리 클래스 - 한국 특허 전용"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.text = ""
        self.metadata = {}
        
    def process(self) -> Dict:
        """PDF 처리 메인"""
        logger.info(f"PDF 처리 시작: {self.pdf_path}")
        
        # 1. PDF 텍스트 추출
        self.text = self._extract_text_with_pdfplumber()
        
        # 2. 메타데이터 추출
        self.metadata = self.extract_metadata()
        
        # 3. 청구항 추출
        claims = self._extract_claims_list()
        self.metadata['claims'] = claims
        self.metadata['claims_count'] = len(claims)
        
        logger.info(f"✅ PDF 처리 완료")
        logger.info(f"   - 추출된 텍스트: {len(self.text)}자")
        logger.info(f"   - IPC 코드: {len(self.metadata.get('ipc_codes', []))}개")
        logger.info(f"   - 청구항: {self.metadata['claims_count']}개")
        logger.info(f"   - 도면: {self.metadata.get('drawing_count', 0)}개")
        logger.info(f"   - 발명자: {self.metadata.get('inventors_count', 0)}명")
        
        return {
            "text": self.text,
            "metadata": self.metadata,
            "file_path": str(self.pdf_path)
        }
    
    def _extract_text_with_pdfplumber(self) -> str:
        """pdfplumber로 텍스트 추출"""
        try:
            full_text = []
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                        logger.debug(f"페이지 {page_num}: {len(text)}자 추출")
            
            combined_text = "\n\n".join(full_text)
            logger.info(f"총 {len(pdf.pages)}페이지에서 {len(combined_text)}자 추출")
            return combined_text
            
        except Exception as e:
            logger.error(f"PDF 텍스트 추출 실패: {e}")
            return ""
    
    def extract_metadata(self) -> Dict:
        """완전한 메타데이터 추출"""
        title = self._extract_title()
        
        metadata = {
            # 기본 정보
            "number": self._extract_patent_number(),
            "title": title,
            "applicant": self._extract_applicant(),
            "inventors": self._extract_inventors(),
            
            # 권리성 관련 (X1~X6)
            "ipc_codes": self._extract_ipc_codes(),
            "claims": [],  # 나중에 채움
            "claims_count": 0,  # 나중에 채움
            
            # 기술성 관련 (X7~X9)
            "drawing_count": self._extract_drawing_count(),
            "title_length": len(title) if title else 0,
            "concept_keywords": [],  # 청구항 추출 후 계산
            
            # 활용성 관련 (X10)
            "inventors_count": 0,  # 발명자 추출 후 계산
        }
        
        # 발명자 수 계산
        metadata['inventors_count'] = len(metadata['inventors'])
        
        return metadata
    
    def _extract_patent_number(self) -> str:
        """특허번호 추출"""
        patterns = [
            r'공개번호\s*(\d{2}-\d{4}-\d{7})',
            r'출원번호\s*(\d{2}-\d{4}-\d{7})',
            r'등록번호\s*(\d{2}-\d{7})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                number = match.group(1)
                logger.info(f"특허번호: {number}")
                return number
        
        logger.warning("특허번호를 찾을 수 없음")
        return "Unknown"
    
    def _extract_title(self) -> str:
        """발명의 명칭 추출"""
        patterns = [
            r'발명의\s*명칭\s*[)）]?\s*(.+?)(?:\n|$)',
            r'\(54\)\s*발명의\s*명칭\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                # 괄호 등 제거
                title = re.sub(r'[\(（].+?[\)）]', '', title).strip()
                logger.info(f"발명의 명칭: {title[:50]}...")
                return title
        
        logger.warning("발명의 명칭을 찾을 수 없음")
        return "Unknown"
    
    def _extract_applicant(self) -> str:
        """출원인 추출"""
        patterns = [
            r'\(71\)\s*출원인\s*(.+?)(?:\n|$)',
            r'출원인\s*[：:]\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.MULTILINE)
            if match:
                applicant = match.group(1).strip()
                logger.info(f"출원인: {applicant}")
                return applicant
        
        return "Unknown"
    
    def _extract_inventors(self) -> List[str]:
        """발명자 정보 추출 (X10)"""
        try:
            patterns = [
                r'\(72\)\s*발명자\s*(.+?)(?:\n\(|$)',
                r'발명자\s*[：:]\s*(.+?)(?:\n|$)',
            ]
            
            inventors = []
            for pattern in patterns:
                matches = re.findall(pattern, self.text, re.DOTALL)
                for match in matches:
                    # 여러 명인 경우 파싱
                    inventor_text = match.strip()
                    # 줄바꿈으로 구분된 발명자들 파싱
                    lines = inventor_text.split('\n')
                    for line in lines:
                        # 한글 이름만 추출 (주소 등 제외)
                        name_match = re.match(r'([가-힣]{2,4})', line.strip())
                        if name_match:
                            name = name_match.group(1)
                            if name not in inventors:
                                inventors.append(name)
                    
                    if inventors:
                        break
                
                if inventors:
                    break
            
            logger.info(f"발명자 {len(inventors)}명: {', '.join(inventors)}")
            return inventors
            
        except Exception as e:
            logger.warning(f"발명자 추출 실패: {e}")
            return []
    
    def _extract_ipc_codes(self) -> List[str]:
        """IPC 코드 추출 (X1)"""
        try:
            patterns = [
                r'\(51\)\s*국제특허분류.*?\n(.+?)(?:\n\(|$)',
                r'IPC.*?\n(.+?)(?:\n|$)',
            ]
            
            ipc_codes = []
            for pattern in patterns:
                match = re.search(pattern, self.text, re.DOTALL)
                if match:
                    ipc_section = match.group(1)
                    # IPC 코드 패턴: G06F 16/33 등
                    codes = re.findall(r'([A-H]\d{2}[A-Z]\s*\d+/\d+)', ipc_section)
                    ipc_codes.extend(codes)
                    
                    if ipc_codes:
                        break
            
            # 중복 제거 및 정규화
            ipc_codes = list(set([code.replace(' ', '') for code in ipc_codes]))
            logger.info(f"IPC 코드 {len(ipc_codes)}개: {', '.join(ipc_codes[:3])}")
            return ipc_codes
            
        except Exception as e:
            logger.warning(f"IPC 코드 추출 실패: {e}")
            return []
    
    def _extract_drawing_count(self) -> int:
        """도면 수 추출 (X7)"""
        try:
            # 방법 1: 도면의 간단한 설명 섹션
            pattern1 = r'도면의\s*간단한\s*설명.*?\n(.+?)(?:\n\n|발명을\s*실시하기)'
            match1 = re.search(pattern1, self.text, re.DOTALL)
            
            if match1:
                section = match1.group(1)
                # "도 1", "도1" 등의 패턴 찾기
                fig_numbers = set()
                for fig_match in re.finditer(r'도\s*(\d+)', section):
                    fig_numbers.add(int(fig_match.group(1)))
                
                if fig_numbers:
                    count = max(fig_numbers)
                    logger.info(f"도면 {count}개 (도면의 간단한 설명)")
                    return count
            
            # 방법 2: 본문에서 도면 언급 카운트
            fig_numbers = set()
            for match in re.finditer(r'도\s*(\d+)', self.text):
                fig_numbers.add(int(match.group(1)))
            
            if fig_numbers:
                count = max(fig_numbers)
                logger.info(f"도면 {count}개 (본문 기준)")
                return count
            
            logger.warning("도면 수를 찾을 수 없음")
            return 0
            
        except Exception as e:
            logger.warning(f"도면 수 추출 실패: {e}")
            return 0
    
    def _extract_claims_list(self) -> List[str]:
        """청구항 목록 추출 - 개선 버전"""
        try:
            # 청구범위 섹션 찾기
            claim_section_pattern = r'청구범위\s*(.+?)(?:명\s*세\s*서|발명의\s*설명|$)'
            match = re.search(claim_section_pattern, self.text, re.DOTALL)
            
            if not match:
                logger.warning("청구범위 섹션을 찾을 수 없음")
                return []
            
            claim_section = match.group(1)
            
            # 각 청구항 추출
            claims = []
            claim_pattern = r'청구항\s*(\d+)\s*(.+?)(?=청구항\s*\d+|$)'
            
            for claim_match in re.finditer(claim_pattern, claim_section, re.DOTALL):
                claim_num = int(claim_match.group(1))
                claim_text = claim_match.group(2).strip()
                
                # 줄바꿈을 공백으로 변환하고 중복 공백 제거
                claim_text = re.sub(r'\s+', ' ', claim_text)
                
                if claim_text:
                    claims.append(claim_text)
                    logger.debug(f"청구항 {claim_num}: {len(claim_text)}자")
            
            logger.info(f"청구항 {len(claims)}개 추출 완료")
            
            # 개념 키워드도 여기서 추출
            if claims:
                self.metadata['concept_keywords'] = self._extract_concept_keywords_from_claim(claims[0])
            
            return claims
            
        except Exception as e:
            logger.error(f"청구항 추출 실패: {e}")
            return []
    
    def _extract_concept_keywords_from_claim(self, first_claim: str) -> List[str]:
        """청구항 1번에서 핵심 개념 키워드 추출 (X9)"""
        try:
            keywords = set()
            
            # 한글 기술용어 패턴
            noun_patterns = [
                r'[가-힣]{2,}(?:부|기|체|판|층|막|소자|장치|시스템|모듈|유닛)',
                r'[가-힣]{2,}(?:방법|공정|단계|과정|수단)',
                r'[가-힣]{3,}(?:모델|데이터|정보|신호)',
            ]
            
            for pattern in noun_patterns:
                matches = re.findall(pattern, first_claim)
                keywords.update(matches)
            
            # 영문 기술용어
            english_terms = re.findall(r'\b[A-Z]{2,}\b', first_claim)  # LLM, RAG 등
            keywords.update(english_terms)
            
            result = list(keywords)[:20]  # 최대 20개
            logger.info(f"개념 키워드 {len(result)}개 추출")
            return result
            
        except Exception as e:
            logger.warning(f"개념 키워드 추출 실패: {e}")
            return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 테스트
    pdf_path = "/mnt/user-data/uploads/patent1samsung.pdf"
    processor = PDFProcessor(pdf_path)
    result = processor.process()
    
    print("\n📊 추출 결과:")
    print(f"특허번호: {result['metadata']['number']}")
    print(f"발명명칭: {result['metadata']['title']}")
    print(f"IPC: {len(result['metadata']['ipc_codes'])}개")
    print(f"청구항: {result['metadata']['claims_count']}개")
    print(f"도면: {result['metadata']['drawing_count']}개")
    print(f"발명자: {result['metadata']['inventors_count']}명")