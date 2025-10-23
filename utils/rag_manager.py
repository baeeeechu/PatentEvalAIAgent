"""
RAG (Retrieval-Augmented Generation) 시스템
- FAISS 벡터 스토어
- 한국어 임베딩 모델 (nlpai-lab/KoE5)
"""
import os
from typing import List, Dict, Optional
from pathlib import Path
import pickle

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

from utils.pdf_processor import PatentPDFProcessor


class PatentRAGManager:
    """특허 문서 RAG 관리"""
    
    def __init__(
        self, 
        embedding_model: str = "nlpai-lab/KoE5",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        index_path: str = "faiss_index"
    ):
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.index_path = Path(index_path)
        
        # 임베딩 모델 초기화
        print(f"📦 임베딩 모델 로딩: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        self.vector_store = None
        self.metadata_store = {}
        
    def build_from_pdfs(self, pdf_paths: List[str]) -> Dict:
        """PDF 파일들로부터 RAG 구축"""
        print(f"\n🔨 {len(pdf_paths)}개 특허 PDF로 RAG 구축 시작...")
        
        all_documents = []
        
        for pdf_path in pdf_paths:
            try:
                print(f"  처리 중: {Path(pdf_path).name}")
                
                # PDF 파싱
                processor = PatentPDFProcessor(pdf_path)
                metadata = processor.extract_metadata()
                chunks = processor.get_text_chunks(
                    chunk_size=self.chunk_size,
                    overlap=self.chunk_overlap
                )
                processor.close()
                
                # Document 객체 생성
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "source": pdf_path,
                            "patent_number": metadata.get("number", "Unknown"),
                            "patent_title": metadata.get("title", "Unknown"),
                            "applicant": metadata.get("applicant", "Unknown"),
                            "chunk_id": i,
                            "total_chunks": len(chunks)
                        }
                    )
                    all_documents.append(doc)
                
                # 메타데이터 저장
                self.metadata_store[pdf_path] = metadata
                
                print(f"    ✅ 청크 수: {len(chunks)}")
                
            except Exception as e:
                print(f"    ❌ 오류: {e}")
                continue
        
        # FAISS 벡터 스토어 생성
        print(f"\n🔍 FAISS 벡터 스토어 생성 중... (총 {len(all_documents)}개 청크)")
        self.vector_store = FAISS.from_documents(
            documents=all_documents,
            embedding=self.embeddings
        )
        
        print("✅ RAG 구축 완료!\n")
        
        # ✅ 수정: total_chunks 키 추가
        return {
            "total_documents": len(all_documents),
            "total_chunks": len(all_documents),  # ✅ 추가
            "total_patents": len(pdf_paths),
            "metadata": self.metadata_store
        }
    
    def search(
        self, 
        query: str, 
        k: int = 5,
        filter_patent: Optional[str] = None
    ) -> List[Document]:
        """유사도 검색"""
        if not self.vector_store:
            raise ValueError("벡터 스토어가 초기화되지 않았습니다. build_from_pdfs()를 먼저 실행하세요.")
        
        # 특정 특허로 필터링
        if filter_patent:
            # 더 많이 검색하여 필터링 후 k개 확보
            results = self.vector_store.similarity_search(
                query, 
                k=k*3
            )
            # 메타데이터 필터링
            filtered_results = [
                doc for doc in results 
                if filter_patent in doc.metadata.get("source", "")
            ]
            
            # 필터링 결과 반환
            return filtered_results[:k]
        else:
            results = self.vector_store.similarity_search(query, k=k)
            return results
    
    def get_patent_summary(self, pdf_path: str, max_chunks: int = 10) -> str:
        """특정 특허의 요약 생성 (처음 N개 청크)"""
        results = self.search(
            query="발명의 내용 배경기술 해결과제",
            k=max_chunks,
            filter_patent=pdf_path
        )
        
        summary_parts = []
        for doc in results:
            summary_parts.append(doc.page_content)
        
        return "\n\n".join(summary_parts)
    
    def save_index(self):
        """벡터 스토어 저장"""
        if not self.vector_store:
            raise ValueError("저장할 벡터 스토어가 없습니다.")
        
        self.index_path.mkdir(exist_ok=True)
        
        # FAISS 인덱스 저장
        self.vector_store.save_local(str(self.index_path))
        
        # 메타데이터 저장
        metadata_path = self.index_path / "metadata.pkl"
        with open(metadata_path, "wb") as f:
            pickle.dump(self.metadata_store, f)
        
        print(f"💾 인덱스 저장 완료: {self.index_path}")
    
    def load_index(self):
        """저장된 벡터 스토어 로드"""
        if not self.index_path.exists():
            raise FileNotFoundError(f"인덱스 경로가 존재하지 않습니다: {self.index_path}")
        
        # FAISS 인덱스 로드
        self.vector_store = FAISS.load_local(
            str(self.index_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        # 메타데이터 로드
        metadata_path = self.index_path / "metadata.pkl"
        if metadata_path.exists():
            with open(metadata_path, "rb") as f:
                self.metadata_store = pickle.load(f)
        
        print(f"📂 인덱스 로드 완료: {self.index_path}")


def create_rag_system(pdf_paths: List[str], save: bool = True) -> PatentRAGManager:
    """RAG 시스템 생성 헬퍼 함수"""
    rag_manager = PatentRAGManager()
    
    # RAG 구축
    build_info = rag_manager.build_from_pdfs(pdf_paths)
    
    print(f"📊 구축 정보:")
    print(f"  - 총 특허: {build_info['total_patents']}개")
    print(f"  - 총 청크: {build_info['total_documents']}개")
    
    # 저장
    if save:
        rag_manager.save_index()
    
    return rag_manager


if __name__ == "__main__":
    # 테스트 코드
    test_pdfs = [
        "data/patent1.pdf",
        "data/patent2.pdf",
        "data/patent3.pdf"
    ]
    
    # RAG 구축
    rag = create_rag_system(test_pdfs)
    
    # 검색 테스트
    print("\n🔍 검색 테스트:")
    query = "LLM 기반 고객 상담"
    results = rag.search(query, k=3)
    
    for i, doc in enumerate(results, 1):
        print(f"\n[결과 {i}]")
        print(f"특허: {doc.metadata.get('patent_number')}")
        print(f"내용: {doc.page_content[:200]}...")