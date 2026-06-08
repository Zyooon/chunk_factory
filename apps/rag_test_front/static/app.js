'use strict';

// ── 헤어스타일 데이터 ────────────────────────────────────────────────────────
// makeup 확장 시: personal_color, makeup_recommendations 항목 추가 가능

const STYLES = {
  남성: [
    { code: 'm-01', name: '버즈' },
    { code: 'm-02', name: '하이앤타이트' },
    { code: 'm-03', name: '아이비리그' },
    { code: 'm-04', name: '크롭' },
    { code: 'm-05', name: '드롭' },
    { code: 'm-06', name: '슬릭' },
    { code: 'm-07', name: '허밍' },
    { code: 'm-08', name: '댄디' },
    { code: 'm-09', name: '리프' },
    { code: 'm-10', name: '퀴프' },
    { code: 'm-11', name: '울프' },
    { code: 'm-12', name: '애즈' },
    { code: 'm-13', name: '시스루' },
    { code: 'm-14', name: '쉐도우' },
    { code: 'm-15', name: '베이비' },
    { code: 'm-16', name: '포마드' },
    { code: 'm-17', name: '히피' },
    { code: 'm-18', name: '그런지' },
    { code: 'm-19', name: '리젠트' },
  ],
  여성: [
    { code: 'f-01', name: '픽시' },
    { code: 'f-02', name: '프리다' },
    { code: 'f-03', name: '보브' },
    { code: 'f-04', name: '태슬' },
    { code: 'f-05', name: '원랭스' },
    { code: 'f-06', name: '허그' },
    { code: 'f-07', name: '빌드' },
    { code: 'f-08', name: '레이어드' },
    { code: 'f-09', name: '허쉬' },
    { code: 'f-10', name: '샌드' },
    { code: 'f-11', name: '샤기' },
    { code: 'f-12', name: '울프' },
    { code: 'f-13', name: '버드' },
    { code: 'f-14', name: '히메' },
    { code: 'f-15', name: '다이앤' },
    { code: 'f-16', name: '레아' },
    { code: 'f-17', name: '레인' },
    { code: 'f-18', name: '그레이스' },
    { code: 'f-19', name: '엘리자벳' },
    { code: 'f-20', name: '페미닌' },
    { code: 'f-21', name: '벌룬' },
    { code: 'f-22', name: '코튼' },
    { code: 'f-23', name: '발롱' },
    { code: 'f-24', name: '구름' },
    { code: 'f-25', name: '젤리' },
    { code: 'f-26', name: '러플' },
    { code: 'f-27', name: '바그' },
    { code: 'f-28', name: '프릴' },
    { code: 'f-29', name: '윈드' },
    { code: 'f-30', name: '그런지' },
  ],
};

// ── 앱 상태 ──────────────────────────────────────────────────────────────────
const appState = {
  chatHistory: [],
};

// ── DOM 헬퍼 ─────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── 초기화 ───────────────────────────────────────────────────────────────────
function init() {
  // 기본 성별 선택
  setGender('남성');
  renderStyleList('남성');

  // 성별 변경 → 스타일 목록 갱신
  document.querySelectorAll('input[name="gender"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      renderStyleList(radio.value);
    });
  });

  $('btn-sample-male').addEventListener('click', fillSampleMale);
  $('btn-sample-female').addEventListener('click', fillSampleFemale);
  $('btn-analyze').addEventListener('click', handleAnalyze);
  $('btn-chat').addEventListener('click', handleChat);
  $('btn-reset-chat').addEventListener('click', resetChat);
}

// ── 스타일 체크박스 목록 렌더링 ──────────────────────────────────────────────
function renderStyleList(gender) {
  const list = STYLES[gender] || [];
  const container = $('style-list');
  container.innerHTML = '';
  setStyleCount(0);

  list.forEach(({ code, name }) => {
    const label = document.createElement('label');

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = code;
    cb.dataset.name = name;
    cb.addEventListener('change', onStyleCheck);

    const span = document.createElement('span');
    span.textContent = name;
    span.title = code; // 코드 툴팁으로 제공 (UI 직접 노출 없음)

    label.appendChild(cb);
    label.appendChild(span);
    container.appendChild(label);
  });
}

function onStyleCheck() {
  const checked = getCheckedStyles();
  if (checked.length > 3) {
    // 4번째 선택 방지
    this.checked = false;
    return;
  }
  setStyleCount(checked.length);
}

function setStyleCount(n) {
  const el = $('style-count');
  el.textContent = `${n} / 3 선택됨`;
  el.className = 'style-count' + (n === 3 ? ' done' : '');
}

function getCheckedStyles() {
  return Array.from(
    document.querySelectorAll('#style-list input[type="checkbox"]:checked')
  ).map((cb) => ({ style_code: cb.value, style_name: cb.dataset.name }));
}

function getGender() {
  const r = document.querySelector('input[name="gender"]:checked');
  return r ? r.value : '';
}

// ── 샘플 데이터 채우기 ────────────────────────────────────────────────────────
function fillSampleMale() {
  setGender('남성');
  renderStyleList('남성');
  $('face-shape').value = '둥근형';
  $('face-proportion').value = '균형';
  checkByCodes(['m-09', 'm-10', 'm-08']); // 리프, 퀴프, 댄디
}

function fillSampleFemale() {
  setGender('여성');
  renderStyleList('여성');
  $('face-shape').value = '둥근형';
  $('face-proportion').value = '균형';
  checkByCodes(['f-08', 'f-09', 'f-15']); // 레이어드, 허쉬, 다이앤
}

function setGender(value) {
  document.querySelectorAll('input[name="gender"]').forEach((r) => {
    r.checked = r.value === value;
  });
}

function checkByCodes(codes) {
  document.querySelectorAll('#style-list input[type="checkbox"]').forEach((cb) => {
    cb.checked = codes.includes(cb.value);
  });
  setStyleCount(codes.length);
}

// ── 분석 요청 ─────────────────────────────────────────────────────────────────
async function handleAnalyze() {
  const gender = getGender();
  const face_shape = $('face-shape').value;
  const face_proportion = $('face-proportion').value;
  const recommended_hair_styles = getCheckedStyles();

  hideError('analysis-error');

  if (!gender) {
    return showError('analysis-error', '성별을 선택해주세요.');
  }
  if (recommended_hair_styles.length !== 3) {
    return showError('analysis-error', '헤어스타일을 정확히 3개 선택해주세요.');
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
  }
}

function renderAnalysisResult(data) {
  $('analysis-result').classList.remove('hidden');

  $('res-summary').textContent = data.analysis_summary || '(없음)';

  const hairLines = (data.hair_recommendations || []).map(
    (h) => `${h.style_name} (${h.style_code}) — 검색 ${h.retrieved_count}건, fallback: ${h.fallback_stage ?? 'none'}`
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
  // 챗봇에는 style_name + style_code 모두 전달 (디버그 목적)
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
      showError('chatbot-error', 'previous_recommendations JSON 파싱 오류 — 올바른 JSON을 입력해주세요.');
      return;
    }
  }

  try {
    user_profile = JSON.parse($('chat-user-profile').value || '{}');
  } catch {
    showError('chatbot-error', 'user_profile JSON 파싱 오류 — 올바른 JSON을 입력해주세요.');
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

    const answer = data.answer || '(응답 없음)';
    appendBubble('assistant', answer);

    // 대화 기록 누적 (다음 요청에 사용)
    appState.chatHistory = data.updated_chat_history || appState.chatHistory;

    // user_profile 업데이트
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

  // 첫 메시지면 빈 상태 메시지 제거
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

// ── 진입점 ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
