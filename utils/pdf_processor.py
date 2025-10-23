"""
PDF 처리 및 특허 메타데이터 추출
"""
import re
from typing import Dict, List, Optional
import fitz  # PyMuPDF
from pathlib import Path


class PatentPDFProcessor:
    """특허 PDF 파싱 및 메타데이터 추출"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(pdf_path)
        self.full_text = self._extract_full_text()
        
    def _extract_full_text(self) -> str:
        """PDF 전체 텍스트 추출"""
        text_parts = []
        for page in self.doc:
            text_parts.append(page.get_text())
        return "\n".join(text_parts)
    
    def extract_metadata(self) -> Dict:
        """특허 메타데이터 추출"""
        metadata = {
            "file_name": self.pdf_path.name,
            "number": self._extract_patent_number(),
            "title": self._extract_title(),
            "applicant": self._extract_applicant(),
            "ipc_codes": self._extract_ipc_codes(),
            "application_date": self._extract_application_date(),
            "publication_date": self._extract_publication_date(),
            "claims_count": self._count_claims(),
            "abstract": self._extract_abstract(),
            "drawing_count": self._count_drawings(),  # ✅ 추가
            "inventors": self._extract_inventors(),     # ✅ 추가
            "claims": self._extract_claims()           # ✅ 추가
        }
        return metadata
    
    def _extract_patent_number(self) -> Optional[str]:
        """특허번호 추출 강화 (공개, 출원, 등록)"""
        patterns = [
            # 공개번호
            r'공개번호\s*[:：]?\s*(10-\d{4}-\d{7})',
            r'\(11\)\s*공개번호\s*(10-\d{4}-\d{7})',
            r'공개특허\s*(10-\d{4}-\d{7})',
            
            # 출원번호
            r'출원번호\s*[:：]?\s*(10-\d{4}-\d{7})',
            r'\(21\)\s*출원번호\s*(10-\d{4}-\d{7})',
            
            # 등록번호
            r'등록번호\s*[:：]?\s*(10-\d{7})',
            r'\(11\)\s*등록번호\s*(10-\d{7})',
            
            # 일반 패턴
            r'(10-\d{4}-\d{7})',
            r'(10-\d{7})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.full_text)
            if match:
                number = match.group(1)
                # 유효성 검사
                if len(number) >= 10:
                    return number
        
        return None
    
    def _extract_title(self) -> Optional[str]:
        """발명의 명칭 추출 (여러 줄 처리)"""
        patterns = [
            r'발명의\s*명칭\s*[:：]?\s*(.+?)(?:\n\s*\(\d+\)|발명의\s*설명|요\s*약|청구범위)',
            r'발명의\s*제목\s*[:：]?\s*(.+?)(?:\n\s*\(\d+\)|발명의\s*설명)',
            r'\(54\)[^\n]*발명의\s*명칭\s*(.+?)(?:\n\s*\(\d+\)|\n\n)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.full_text, re.DOTALL)
            if match:
                title = match.group(1).strip()
                # 줄바꿈을 공백으로 변환
                title = re.sub(r'\s+', ' ', title)
                # 특수문자 정리
                title = re.sub(r'[\r\n\t]+', ' ', title)
                return title[:200]  # 최대 200자
        return None
    
    def _extract_applicant(self) -> Optional[str]:
        """출원인 추출"""
        patterns = [
            r'출원인\s*[:：]?\s*([^\n]+)',
            r'특허권자\s*[:：]?\s*([^\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.full_text)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_ipc_codes(self) -> List[str]:
        """IPC 코드 추출"""
        # IPC 코드 패턴: G06F 16/33
        pattern = r'[A-H]\d{2}[A-Z]\s*\d+/\d+'
        matches = re.findall(pattern, self.full_text)
        # 중복 제거 및 정리
        ipc_codes = list(set([m.replace(' ', '') for m in matches]))
        return ipc_codes[:10]  # 최대 10개
    
    def _extract_application_date(self) -> Optional[str]:
        """출원일 추출"""
        patterns = [
            r'출원일\s*[:：]?\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.full_text)
            if match:
                date_str = match.group(1)
                # 날짜 포맷 통일 (YYYY-MM-DD)
                date_str = re.sub(r'[./]', '-', date_str)
                return date_str
        return None
    
    def _extract_publication_date(self) -> Optional[str]:
        """공개일/공고일 추출"""
        patterns = [
            r'공개일\s*[:：]?\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})',
            r'공고일\s*[:：]?\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.full_text)
            if match:
                date_str = match.group(1)
                date_str = re.sub(r'[./]', '-', date_str)
                return date_str
        return None
    
    def _count_claims(self) -> int:
        """청구항 수 카운트"""
        # "청구항 1", "【청구항 1】" 등의 패턴 찾기
        patterns = [
            r'【?청구항\s*(\d+)】?',
            r'\[청구항\s*(\d+)\]',
        ]
        claim_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, self.full_text)
            claim_numbers.extend([int(m) for m in matches])
        
        if claim_numbers:
            return max(claim_numbers)
        return 0
    
    def _extract_abstract(self) -> Optional[str]:
        """요약(초록) 추출 강화"""
        patterns = [
            # 패턴 1: 【요약】 또는 【초록】
            r'【요약】\s*([^【]+?)(?=【|$)',
            r'【초록】\s*([^【]+?)(?=【|$)',
            
            # 패턴 2: (57) 요약 또는 (57) 초록
            r'\(57\)\s*요?\s*약\s*\n([^\(]+?)(?=\(|$)',
            
            # 패턴 3: 요약:, 초록:
            r'요약\s*[:：]\s*([^\n]+(?:\n(?![\(【])[^\n]+)*)',
            r'초록\s*[:：]\s*([^\n]+(?:\n(?![\(【])[^\n]+)*)',
            
            # 패턴 4: [요약], [초록]
            r'\[요약\]\s*([^\[]+?)(?=\[|$)',
            r'\[초록\]\s*([^\[]+?)(?=\[|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.full_text, re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                
                # 정리
                abstract = re.sub(r'\s+', ' ', abstract)  # 공백 정리
                abstract = re.sub(r'^[\s\n\r]+|[\s\n\r]+$', '', abstract)  # 앞뒤 공백 제거
                
                # 너무 짧으면 제외 (최소 20자)
                if len(abstract) >= 20:
                    # 최대 1000자
                    return abstract[:1000]
        
        return None
    
    def _count_drawings(self) -> int:
        """도면 수 카운트"""
        patterns = [
            r'【?도\s*(\d+)】',
            r'\[도\s*(\d+)\]',
            r'도면\s*(\d+)',
            r'Figure\s*(\d+)',
            r'Fig\.\s*(\d+)',
        ]
        
        drawing_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, self.full_text)
            drawing_numbers.extend([int(m) for m in matches])
        
        if drawing_numbers:
            return max(drawing_numbers)
        return 0
    
    def _extract_inventors(self) -> List[str]:
        """발명자 추출"""
        patterns = [
            r'발명자\s*[:：]?\s*([^\n]+)',
            r'발명자의\s*성명\s*[:：]?\s*([^\n]+)',
        ]
        
        inventors = []
        for pattern in patterns:
            matches = re.findall(pattern, self.full_text)
            for match in matches:
                # 쉼표 또는 세미콜론으로 분리
                names = re.split(r'[,;]', match)
                for name in names:
                    name = name.strip()
                    # 괄호 안 내용 제거 (주소 등)
                    name = re.sub(r'\([^)]*\)', '', name).strip()
                    if name and len(name) > 1:
                        inventors.append(name)
        
        # 중복 제거
        inventors = list(set(inventors))
        return inventors[:20]  # 최대 20명
    
    def _extract_claims(self) -> List[str]:
        """청구항 추출 (다양한 형식 대응)"""
        claims = []
        
        # 패턴 1: 【청구항 1】 형식
        pattern1 = r'【청구항\s*(\d+)】([^【]+?)(?=【청구항|\Z)'
        matches1 = re.findall(pattern1, self.full_text, re.DOTALL)
        
        # 패턴 2: 청구항 1 (괄호 없음)
        pattern2 = r'청구항\s*(\d+)\s*\n([^청]+?)(?=청구항\s*\d+|\Z)'
        matches2 = re.findall(pattern2, self.full_text, re.DOTALL)
        
        # 패턴 3: [청구항 1] 형식
        pattern3 = r'\[청구항\s*(\d+)\]([^\[]+?)(?=\[청구항|\Z)'
        matches3 = re.findall(pattern3, self.full_text, re.DOTALL)
        
        # 모든 매칭 결과 수집
        all_matches = []
        for num, text in matches1 + matches2 + matches3:
            all_matches.append((int(num), text.strip()))
        
        # 번호순 정렬 및 중복 제거
        all_matches = sorted(set(all_matches), key=lambda x: x[0])
        
        # 텍스트만 추출
        for num, text in all_matches:
            # 너무 짧은 항목 제외 (최소 20자)
            if len(text) > 20:
                # 최대 2000자로 제한 (더 길게)
                claims.append(text[:2000])
        
        return claims[:100]  # 최대 100개
    
    def get_text_chunks(self, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할 (문단/문장 경계 존중)"""
        text = self.full_text
        chunks = []
        
        # 1단계: 문단으로 분리 (빈 줄 기준)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 현재 청크 + 새 문단이 크기를 초과하면
            if len(current_chunk) + len(para) + 2 > chunk_size:
                if current_chunk:
                    # 현재 청크 저장
                    chunks.append(current_chunk.strip())
                    
                    # 오버랩 처리: 마지막 부분 유지
                    if overlap > 0 and len(current_chunk) > overlap:
                        # 마지막 overlap 크기만큼 잘라서 다음 청크 시작부에 포함
                        sentences = re.split(r'[.!?]\s+', current_chunk)
                        overlap_text = ""
                        for sent in reversed(sentences):
                            if len(overlap_text) + len(sent) < overlap:
                                overlap_text = sent + ". " + overlap_text
                            else:
                                break
                        current_chunk = overlap_text
                    else:
                        current_chunk = ""
                
                # 문단이 청크 크기보다 크면 문장 단위로 분할
                if len(para) > chunk_size:
                    sentences = re.split(r'([.!?])\s+', para)
                    temp_chunk = ""
                    
                    for i in range(0, len(sentences), 2):
                        sentence = sentences[i]
                        if i + 1 < len(sentences):
                            sentence += sentences[i + 1]
                        
                        if len(temp_chunk) + len(sentence) > chunk_size:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = sentence
                        else:
                            temp_chunk += " " + sentence
                    
                    current_chunk = temp_chunk
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para
        
        # 마지막 청크 추가
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def close(self):
        """PDF 문서 닫기"""
        self.doc.close()


def process_multiple_pdfs(pdf_paths: List[str]) -> Dict[str, Dict]:
    """여러 PDF 동시 처리"""
    results = {}
    
    for pdf_path in pdf_paths:
        try:
            processor = PatentPDFProcessor(pdf_path)
            metadata = processor.extract_metadata()
            chunks = processor.get_text_chunks()
            
            results[pdf_path] = {
                "metadata": metadata,
                "chunks": chunks,
                "full_text": processor.full_text
            }
            
            processor.close()
            print(f"✅ {Path(pdf_path).name} 처리 완료")
            
        except Exception as e:
            print(f"❌ {pdf_path} 처리 실패: {e}")
            results[pdf_path] = None
    
    return results


if __name__ == "__main__":
    # 테스트 코드
    test_pdf = "data/patent1.pdf"
    processor = PatentPDFProcessor(test_pdf)
    
    metadata = processor.extract_metadata()
    print("=== 메타데이터 ===")
    for key, value in metadata.items():
        print(f"{key}: {value}")
    
    chunks = processor.get_text_chunks()
    print(f"\n=== 청크 정보 ===")
    print(f"총 청크 수: {len(chunks)}")
    print(f"첫 번째 청크 미리보기:\n{chunks[0][:200]}...")
    
    processor.close()