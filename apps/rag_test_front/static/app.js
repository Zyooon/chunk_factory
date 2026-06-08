'use strict';

// makeup 확장 시: personal_color, makeup_recommendations 항목 추가 가능

// ── 앱 상태 ──────────────────────────────────────────────────────────────────
const appState = {
  chatHistory: [],
  dbRecommended: [],  // DB에서 불러온 추천 스타일 목록
};

// ── DOM 헬퍼 ─────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── 초기화 ───────────────────────────────────────────────────────────────────
function init() {
  setGender('남성');

  $('btn-sample-male').addEventListener('click', fillSampleMale);
  $('btn-sample-female').addEventListener('click', fillSampleFemale);
  $('btn-load-options').addEventListener('click', handleLoadOptions);
  $('btn-analyze').addEventListener('click', handleAnalyze);
  $('btn-chat').addEventListener('click', handleChat);
  $('btn-reset-chat').addEventListener('click', resetChat);
}

// ── 샘플 데이터 채우기 ────────────────────────────────────────────────────────
function fillSampleMale() {
  setGender('남성');
  $('face-shape').value = '둥근형';
  $('face-proportion').value = '균형';
  handleLoadOptions(); // 조건 채우고 자동 호출
}

function fillSampleFemale() {
  setGender('여성');
  $('face-shape').value = '둥근형';
  $('face-proportion').value = '균형';
  handleLoadOptions();
}

function setGender(value) {
  document.querySelectorAll('input[name="gender"]').forEach((r) => {
    r.checked = r.value === value;
  });
}

function getGender() {
  const r = document.querySelector('input[name="gender"]:checked');
  return r ? r.value : '';
}

// ── DB 기반 추천 헤어 불러오기 ────────────────────────────────────────────────
async function handleLoadOptions() {
  const gender = getGender();
  const face_shape = $('face-shape').value;
  const face_proportion = $('face-proportion').value;

  hideError('options-error');

  if (!gender) return showError('options-error', '성별을 선택해주세요.');

  const btn = $('btn-load-options');
  setLoading(btn, true, '불러오는 중...');
  $('btn-analyze').disabled = true;

  try {
    const res = await fetch('/api/hair-options', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gender, face_shape, face_proportion }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showError('options-error', data.error || `서버 오류 (HTTP ${res.status})`);
      return;
    }

    if (data.recommended_styles.length === 0) {
      showError('options-error', '해당 조건의 추천 데이터가 없습니다. 다른 조건을 선택해주세요.');
      $('hair-options-area').classList.add('hidden');
      return;
    }

    appState.dbRecommended = data.recommended_styles;
    renderHairOptions(gender, data);
    $('hair-options-area').classList.remove('hidden');

  } catch (e) {
    showError('options-error', `네트워크 오류: ${e.message}`);
  } finally {
    setLoading(btn, false, '추천 헤어 불러오기');
  }
}

function renderHairOptions(gender, data) {
  // 추천 체크박스 렌더링
  const container = $('style-list');
  container.innerHTML = '';
  setStyleCount(0);
  $('btn-analyze').disabled = true;

  data.recommended_styles.forEach(({ style_name, style_code }) => {
    const label = document.createElement('label');

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = style_code || style_name; // style_code 없으면 style_name을 value로
    cb.dataset.name = style_name;
    cb.dataset.code = style_code || '';
    cb.addEventListener('change', onStyleCheck);

    const span = document.createElement('span');
    span.textContent = style_name;
    if (style_code) span.title = `코드: ${style_code}`;

    label.appendChild(cb);
    label.appendChild(span);
    container.appendChild(label);
  });

  // 비추천 목록 렌더링
  const worstArea = $('worst-area');
  const worstList = $('worst-list');
  worstList.innerHTML = '';

  if (data.worst_styles && data.worst_styles.length > 0) {
    worstArea.classList.remove('hidden');
    data.worst_styles.forEach(({ style_name }) => {
      const span = document.createElement('span');
      span.className = 'worst-tag';
      span.textContent = style_name;
      worstList.appendChild(span);
    });
  } else {
    worstArea.classList.add('hidden');
  }
}

function onStyleCheck() {
  const checked = getCheckedStyles();
  if (checked.length > 3) {
    this.checked = false;
    return;
  }
  setStyleCount(checked.length);
  $('btn-analyze').disabled = checked.length !== 3;
}

function setStyleCount(n) {
  const el = $('style-count');
  el.textContent = `${n} / 3 선택됨`;
  el.className = 'style-count' + (n === 3 ? ' done' : '');
}

function getCheckedStyles() {
  return Array.from(
    document.querySelectorAll('#style-list input[type="checkbox"]:checked')
  ).map((cb) => ({
    style_name: cb.dataset.name,
    style_code: cb.dataset.code || null,
  }));
}

// ── 분석 요청 ─────────────────────────────────────────────────────────────────
async function handleAnalyze() {
  const gender = getGender();
  const face_shape = $('face-shape').value;
  const face_proportion = $('face-proportion').value;
  const recommended_hair_styles = getCheckedStyles();

  hideError('analysis-error');

  if (!gender) return showError('analysis-error', '성별을 선택해주세요.');
  if (recommended_hair_styles.length !== 3) {
    return showError('analysis-error', '헤어스타일을 정확히 3개 선택해주세요.');
  }
  // style_code 없는 스타일이 있으면 경고 (분석 가능하면 진행)
  const noCode = recommended_hair_styles.filter((s) => !s.style_code);
  if (noCode.length > 0) {
    const names = noCode.map((s) => s.style_name).join(', ');
    showError('analysis-error',
      `[경고] 다음 스타일은 RAG 코드 매핑이 없어 검색 정확도가 낮을 수 있습니다: ${names}\n계속 진행합니다.`
    );
  }

  const btn = $('btn-analyze');
  setLoading(btn, true, '생성 중...');

  try {
    const res = await fetch('/api/analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gender, face_shape, face_proportion, recommended_hair_styles }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showError('analysis-error', data.error || `서버 오류 (HTTP ${res.status})`);
      return;
    }

    renderAnalysisResult(data);
    injectAnalysisToChat({ gender, face_shape, face_proportion, data });
  } catch (e) {
    showError('analysis-error', `네트워크 오류: ${e.message}`);
  } finally {
    setLoading(btn, false, '분석 결과 생성');
    // 3개 선택 상태면 다시 활성화
    $('btn-analyze').disabled = getCheckedStyles().length !== 3;
  }
}

function renderAnalysisResult(data) {
  $('analysis-result').classList.remove('hidden');

  $('res-summary').textContent = data.analysis_summary || '(없음)';

  const hairLines = (data.hair_recommendations || []).map(
    (h) => `${h.style_name} (${h.style_code ?? 'code 없음'}) — 검색 ${h.retrieved_count}건, fallback: ${h.fallback_stage ?? 'none'}`
  );
  $('res-hair').textContent = hairLines.join('\n') || '(없음)';

  const ri = data.retrieval_info || {};
  $('res-retrieval').textContent =
    `헤어 문서: ${ri.hair_docs ?? 0}건 | fallback stages: ${JSON.stringify(ri.fallback_stages)}`;

  $('res-raw-json').textContent = JSON.stringify(data, null, 2);
}

// ── 분석 결과 → 챗봇 컨텍스트 자동 주입 ──────────────────────────────────────
function injectAnalysisToChat({ gender, face_shape, face_proportion, data }) {
  $('chat-gender').value = gender;
  $('chat-face-shape').value = face_shape;
  $('chat-face-proportion').value = face_proportion;
  $('chat-prev-analysis').value = data.analysis_summary || '';
  $('chat-prev-recs').value = JSON.stringify(data.hair_recommendations || [], null, 2);
  $('chat-user-profile').value = '{}';
}

// ── 챗봇 요청 ─────────────────────────────────────────────────────────────────
async function handleChat() {
  const user_message = $('chat-message').value.trim();
  if (!user_message) return;

  const skipAnalysis = $('skip-analysis').checked;
  const gender = $('chat-gender').value.trim();
  const face_shape = $('chat-face-shape').value.trim();
  const face_proportion = $('chat-face-proportion').value.trim();

  let previous_analysis = null;
  let previous_recommendations = [];
  let user_profile = {};

  if (!skipAnalysis) {
    previous_analysis = $('chat-prev-analysis').value.trim() || null;
    try {
      previous_recommendations = JSON.parse($('chat-prev-recs').value || '[]');
    } catch {
      showError('chatbot-error', 'previous_recommendations JSON 파싱 오류');
      return;
    }
  }

  try {
    user_profile = JSON.parse($('chat-user-profile').value || '{}');
  } catch {
    showError('chatbot-error', 'user_profile JSON 파싱 오류');
    return;
  }

  hideError('chatbot-error');
  appendBubble('user', user_message);
  $('chat-message').value = '';

  const btn = $('btn-chat');
  setLoading(btn, true, '생성 중...');

  const payload = {
    user_message,
    gender,
    face_shape,
    face_proportion,
    previous_analysis,
    previous_recommendations,
    user_profile,
    chat_history: appState.chatHistory,
  };

  try {
    const res = await fetch('/api/chatbot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showError('chatbot-error', data.error || `서버 오류 (HTTP ${res.status})`);
      return;
    }

    appendBubble('assistant', data.answer || '(응답 없음)');
    appState.chatHistory = data.updated_chat_history || appState.chatHistory;

    if (data.updated_user_profile && Object.keys(data.updated_user_profile).length > 0) {
      $('chat-user-profile').value = JSON.stringify(data.updated_user_profile, null, 2);
    }

    renderChatResult(data);
  } catch (e) {
    showError('chatbot-error', `네트워크 오류: ${e.message}`);
  } finally {
    setLoading(btn, false, '챗봇 질문 보내기');
  }
}

function renderChatResult(data) {
  $('chatbot-result').classList.remove('hidden');

  $('res-intent').textContent =
    `intent: ${data.intent ?? '(없음)'}   category: ${data.category ?? '(없음)'}   needs_clarification: ${data.needs_clarification ?? false}`;

  const ri = data.retrieval_info || {};
  $('res-chat-retrieval').textContent =
    `retrieved_count: ${ri.retrieved_count ?? 0}   fallback_stage: ${ri.fallback_stage ?? 'none'}`;

  $('res-updated-profile').textContent = JSON.stringify(data.updated_user_profile || {}, null, 2);
  $('res-chat-raw-json').textContent = JSON.stringify(data, null, 2);
}

// ── 채팅 버블 ─────────────────────────────────────────────────────────────────
function appendBubble(role, text) {
  const container = $('chat-history');
  const empty = container.querySelector('.chat-empty');
  if (empty) empty.remove();

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;

  const roleEl = document.createElement('div');
  roleEl.className = 'bubble-role';
  roleEl.textContent = role === 'user' ? '나' : 'AI';

  const textEl = document.createElement('div');
  textEl.className = 'bubble-text';
  textEl.textContent = text;

  bubble.appendChild(roleEl);
  bubble.appendChild(textEl);
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ── 대화 초기화 ───────────────────────────────────────────────────────────────
function resetChat() {
  appState.chatHistory = [];
  $('chat-history').innerHTML = '<div class="chat-empty">대화 기록이 없습니다.</div>';
  $('chatbot-result').classList.add('hidden');
  $('chat-user-profile').value = '{}';
  hideError('chatbot-error');
}

// ── 공통 유틸 ─────────────────────────────────────────────────────────────────
function showError(id, msg) {
  const el = $(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}

function hideError(id) {
  $(id).classList.add('hidden');
}

function setLoading(btn, loading, label) {
  btn.disabled = loading;
  btn.textContent = label;
}

document.addEventListener('DOMContentLoaded', init);
