from __future__ import annotations

import json
import re
from typing import Any

from apps.chatbot_rag.intents import INTENT_OUTFIT_FIT_CHECK

_OUTFIT_CONTEXT_LABELS: dict[str, str] = {
    "daily": "데일리룩",
    "date": "데이트룩",
    "wedding_guest": "결혼식 하객룩",
    "office": "출근/면접룩",
    "formal": "격식 있는 자리",
    "casual": "꾸안꾸 캐주얼",
}


def _format_hair(hair: dict[str, Any]) -> str:
    name = hair.get("style_name") or ""
    summary = hair.get("hair_analysis_summary") or hair.get("summary") or ""
    if not name and not summary:
        return "헤어스타일 정보 없음"
    parts = []
    if name:
        parts.append(f"스타일명: {name}")
    if summary:
        parts.append(f"요약: {summary}")
    return "\n".join(parts)


def _format_makeup(makeup: dict[str, Any]) -> str:
    name = makeup.get("style_name") or ""
    summary = makeup.get("makeup_analysis_summary") or makeup.get("summary") or ""
    if not name and not summary:
        return "메이크업 정보 없음"
    parts = []
    if name:
        parts.append(f"스타일명: {name}")
    if summary:
        parts.append(f"요약: {summary}")
    return "\n".join(parts)


def _format_image_analysis(analysis: dict[str, Any] | None) -> str:
    if not analysis:
        return "없음"
    lines = []
    for key, label in [
        ("outfit_type", "의상 종류"),
        ("colors", "색상"),
        ("silhouette", "핏/실루엣"),
        ("formality", "격식도"),
        ("style_mood", "스타일 무드"),
        ("match_points", "어울리는 포인트"),
        ("risk_points", "주의할 포인트"),
    ]:
        val = analysis.get(key)
        if val:
            lines.append(f"- {label}: {val}")
    return "\n".join(lines) if lines else "분석 결과 없음"


def build_outfit_coordination_prompt(
    *,
    gender: str | None,
    face_shape: str | None,
    face_proportion: str | None,
    personal_color: str | None,
    hair_summary: dict[str, Any],
    makeup_summary: dict[str, Any],
    outfit_context: str | None,
    outfit_image_analysis: dict[str, Any] | None,
    outfit_intent: str | None,
    user_message: str,
    previous_analysis: Any = None,
) -> str:
    context_label = _OUTFIT_CONTEXT_LABELS.get(outfit_context or "", outfit_context or "상황 정보 없음")
    is_fit_check = outfit_intent == INTENT_OUTFIT_FIT_CHECK

    if is_fit_check:
        task_description = "사용자가 업로드한 의상 이미지를 분석하고, 현재 추천된 헤어·메이크업과의 조화를 판단하세요."
        output_instruction = """
[출력 형식]
아래 두 섹션을 반드시 포함해서 답변하세요.

[답변]
(한국어 대화형 답변. 의상과 헤어/메이크업 조화에 대해 2~4문장으로 설명하세요.)
[/답변]

[의상후보]
[{"id": "uploaded_outfit", "label": "업로드한 의상", "source": "image"}]
[/의상후보]
""".strip()
    else:
        task_description = f"사용자의 헤어·메이크업 스타일을 바탕으로 '{context_label}' 상황에 어울리는 의상 3가지를 추천하세요."
        output_instruction = """
[출력 형식]
아래 두 섹션을 반드시 포함해서 답변하세요.

[답변]
(한국어 대화형 답변. 추천 의상을 간략히 소개하세요. 2~4문장.)
[/답변]

[의상후보]
[
  {
    "id": "look_1",
    "label": "의상 이름 (간결하게)",
    "description": "이 의상을 추천하는 이유",
    "colors": ["주요 색상1", "주요 색상2"],
    "items": ["아이템1", "아이템2"],
    "avoid": ["피해야 할 것"]
  },
  { "id": "look_2", ... },
  { "id": "look_3", ... }
]
[/의상후보]
""".strip()

    return f"""
당신은 헤어와 메이크업 추천 결과를 바탕으로 의상 코디를 추천하거나 판단하는 AI 어시스턴트입니다.

[역할]
{task_description}

[사용자 진단 정보]
- 성별: {gender or "정보 없음"}
- 얼굴형: {face_shape or "정보 없음"}
- 삼정비율: {face_proportion or "정보 없음"}
- 퍼스널컬러: {personal_color or "정보 없음"}

[추천된 헤어스타일]
{_format_hair(hair_summary)}

[추천된 메이크업]
{_format_makeup(makeup_summary)}

[의상 상황]
{context_label}

[의상 이미지 분석 결과]
{_format_image_analysis(outfit_image_analysis)}

[사용자 질문]
{user_message}

[답변 원칙]
- 존댓말을 사용하세요.
- 인사말, 감탄문, 과한 칭찬은 쓰지 마세요.
- 헤어와 메이크업 스타일과의 연결성을 이유로 설명하세요.
- 피해야 할 아이템도 간략히 언급하세요.
- 내부 식별자(id, code 등)를 답변에 노출하지 마세요.

{output_instruction}
""".strip()


def parse_outfit_response(
    content: str,
    outfit_intent: str | None,
) -> tuple[str, list[dict]]:
    """
    LLM 응답에서 [답변]과 [의상후보] 블록을 파싱한다.
    파싱 실패 시 content 전체를 answer로, 빈 리스트를 outfit_options로 반환한다.
    """
    answer = content
    outfit_options: list[dict] = []

    # 의상후보 블록 추출
    candidate_match = re.search(
        r"\[의상후보\]\s*(.*?)\s*\[/의상후보\]",
        content,
        re.DOTALL,
    )
    if candidate_match:
        raw_json = candidate_match.group(1).strip()
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, list):
                outfit_options = parsed
        except (json.JSONDecodeError, ValueError):
            pass
        # 의상후보 블록을 answer에서 제거
        answer = content[: candidate_match.start()].strip()

    # 답변 블록 추출
    answer_match = re.search(
        r"\[답변\]\s*(.*?)\s*\[/답변\]",
        answer,
        re.DOTALL,
    )
    if answer_match:
        answer = answer_match.group(1).strip()

    # fit_check이고 outfit_options가 비어 있으면 기본값 설정
    if outfit_intent == INTENT_OUTFIT_FIT_CHECK and not outfit_options:
        outfit_options = [{"id": "uploaded_outfit", "label": "업로드한 의상", "source": "image"}]

    return answer, outfit_options
