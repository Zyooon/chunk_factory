# apps/rag_core/schemas.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


Metadata = Dict[str, Any]


@dataclass
class RetrievalQuery:
    """
    ChromaDB 검색에 사용할 입력 조건.

    예:
        category="hair"
        gender="남성"
        face_shape="둥근형"
        face_proportion="균형"
        style_code="m-10"
        query="둥근형 남성에게 어울리는 헤어스타일 추천해줘"
    """

    query: str
    category: str = "hair"

    gender: Optional[str] = None
    face_shape: Optional[str] = None
    face_proportion: Optional[str] = None
    style_code: Optional[str] = None
    style_name: Optional[str] = None

    k: int = 5


@dataclass
class RetrievedDocument:
    """
    ChromaDB에서 검색된 문서 1개를 표현하는 구조.

    page_content:
        LLM에게 근거 문맥으로 전달할 본문

    metadata:
        category, gender, face_shape, style_code 등 검색/출처 확인용 정보

    score:
        검색 점수.
        Chroma/LangChain 검색 방식에 따라 없을 수도 있으므로 Optional 처리
    """

    page_content: str
    metadata: Metadata = field(default_factory=dict)
    score: Optional[float] = None


@dataclass
class RetrievalResult:
    """
    검색 결과 전체를 표현하는 구조.

    documents:
        실제 검색된 문서 목록

    retrieved_count:
        검색된 문서 개수

    fallback_stage:
        몇 번째 fallback 조건에서 검색에 성공했는지 기록

    used_filter:
        실제 ChromaDB 검색에 사용된 metadata filter

    query:
        원래 사용자 검색 문장
    """

    query: str
    documents: List[RetrievedDocument] = field(default_factory=list)
    retrieved_count: int = 0
    fallback_stage: int | str | None = None
    used_filter: Metadata = field(default_factory=dict)


@dataclass
class GenerationInput:
    """
    Gemini 답변 생성을 위한 입력 구조.

    retrieval_result:
        retriever.py에서 반환한 검색 결과

    user_question:
        사용자의 실제 질문

    system_instruction:
        답변 규칙 또는 시스템 프롬프트
    """

    user_question: str
    retrieval_result: RetrievalResult
    system_instruction: Optional[str] = None
    user_context: dict[str, Any] = field(default_factory=dict)

@dataclass
class AnalysisGenerationInput:
    '''
    종합 분석용 입력 스키마
    
    gender / face_shape / face_proportion
    → 사용자 진단 정보

    recommended_styles
    → 알고리즘이 추천한 스타일 3개

    retrieval_results
    → 각 스타일별 RAG 검색 결과
    '''
    gender: str
    face_shape: str
    face_proportion: str
    recommended_styles: list[dict[str, Any]]
    retrieval_results: list[RetrievalResult]

@dataclass
class ChatGenerationInput:
    """
    챗봇 답변 생성을 위한 입력 스키마.

    chatbot_rag는 최초 분석 이후의 후속 상담 기능이므로
    사용자 질문뿐 아니라 이전 분석 결과, 추천 결과, 대화 히스토리를 함께 사용한다.

    user_message:
        사용자의 현재 질문

    gender / face_shape / face_proportion:
        최초 분석에서 확보된 사용자 진단 정보

    previous_analysis:
        analysis_rag가 생성한 최초 종합 분석문

    previous_recommendations:
        알고리즘이 추천한 헤어스타일 목록

    user_profile:
        대화 중 누적된 유저 취향 정보

    chat_history:
        최근 대화 기록

    retrieval_result:
        현재 질문에 대해 ChromaDB에서 검색한 RAG 결과

    intent:
        classify_intent 노드에서 분류한 질문 의도
    """

    user_message: str
    gender: str
    face_shape: str
    face_proportion: str

    previous_analysis: str | dict[str, Any] | None = None
    previous_recommendations: list[dict[str, Any]] = field(default_factory=list)

    user_profile: dict[str, Any] = field(default_factory=dict)
    chat_history: list[dict[str, str]] = field(default_factory=list)

    retrieval_result: RetrievalResult = field(
        default_factory=lambda: RetrievalResult(query="")
    )

    intent: Optional[str] = None

@dataclass
class GenerationResult:
    """
    Gemini 답변 생성 결과.

    answer:
        최종 생성 답변

    retrieval_result:
        어떤 검색 결과를 근거로 답변했는지 추적하기 위해 포함

    model_name:
        사용한 Gemini 모델명
    """

    answer: str
    retrieval_result: RetrievalResult
    model_name: Optional[str] = None