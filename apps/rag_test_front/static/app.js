'use strict';

// ── 앱 상태 ──────────────────────────────────────────────────────────────────
const appState = {
  chatHistory: [],
  ragCoverage: new Set(),   // ChromaDB에 데이터가 있는 style_code 집합
};

const MAKEUP_STYLES_BY_GENDER_AND_PERSONAL_COLOR = {
  '여성': {
    '봄웜': [
      { category: 'makeup', style_name: '피치 메이크업', style_code: 'mk-sp-peach', makeup_group: 'peach' },
      { category: 'makeup', style_name: '코랄 메이크업', style_code: 'mk-sp-coral', makeup_group: 'coral' },
      { category: 'makeup', style_name: '주시 메이크업', style_code: 'mk-sp-juicy', makeup_group: 'juicy' },
    ],
    '여름쿨': [
      { category: 'makeup', style_name: '듀이 메이크업', style_code: 'mk-su-dewy', makeup_group: 'dewy' },
      { category: 'makeup', style_name: '내추럴 메이크업', style_code: 'mk-su-natural', makeup_group: 'natural' },
      { category: 'makeup', style_name: '로즈 메이크업', style_code: 'mk-su-rose', makeup_group: 'rose' },
    ],
    '가을웜': [
      { category: 'makeup', style_name: '브라운 메이크업', style_code: 'mk-au-brown', makeup_group: 'brown' },
      { category: 'makeup', style_name: '시크 메이크업', style_code: 'mk-au-chic', makeup_group: 'chic' },
      { category: 'makeup', style_name: '오피스 메이크업', style_code: 'mk-au-office', makeup_group: 'office' },
    ],
    '겨울쿨': [
      { category: 'makeup', style_name: '버건디 메이크업', style_code: 'mk-wi-burgundy', makeup_group: 'burgundy' },
      { category: 'makeup', style_name: '글램 메이크업', style_code: 'mk-wi-glam', makeup_group: 'glam' },
      { category: 'makeup', style_name: '레드 메이크업', style_code: 'mk-wi-red', makeup_group: 'red' },
    ],
  },
  '남성': {
    '봄웜': [
      { category: 'makeup', style_name: '봄웜 내추럴 메이크업', style_code: 'mk-m-sp-natural', makeup_group: 'male_spring_natural' },
    ],
    '여름쿨': [
      { category: 'makeup', style_name: '여름쿨 클린 메이크업', style_code: 'mk-m-su-clean', makeup_group: 'male_summer_clean' },
    ],
    '가을웜': [
      { category: 'makeup', style_name: '가을웜 소프트 메이크업', style_code: 'mk-m-au-soft', makeup_group: 'male_autumn_soft' },
    ],
    '겨울쿨': [
      { category: 'makeup', style_name: '겨울쿨 샤프 메이크업', style_code: 'mk-m-wi-sharp', makeup_group: 'male_winter_sharp' },
    ],
  },
};

// ── DOM 헬퍼 ─────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── 초기화 ───────────────────────────────────────────────────────────────────
async function init() {
  setGender('남성');
  $('personal-color').value = '봄웜';
  renderMakeupOptions();
  await loadRagCoverage();

  $('btn-sample-male').addEventListener('click', fillSampleMale);
  $('btn-sample-female').addEventListener('click', fillSampleFemale);
  $('personal-color').addEventListener('change', renderMakeupOptions);
  document.querySelectorAll('input[name="gender"]').forEach((r) => {
    r.addEventListener('change', renderMakeupOptions);
  });
  $('btn-load-options').addEventListener('click', handleLoadOptions);
  $('btn-analyze').addEventListener('click', handleAnalyze);
  $('btn-chat').addEventListener('click', handleChat);
  $('btn-reset-chat').addEventListener('click', resetChat);
}

async function loadRagCoverage() {
  try {
    const res = await fetch('/api/hair-rag-coverage');
    if (res.ok) {
      const data = await res.json();
      appState.ragCoverage = new Set(data.covered_codes || []);
    }
  } catch {
    appState.ragCoverage = new Set();
  }
}

// ── 샘플 데이터 채우기 ────────────────────────────────────────────────────────
function fillSampleMale() {
  setGender('남성');
  $('face-shape').value = '둥근형';
  $('face-proportion').value = '균형';
  $('personal-color').value = '봄웜';
  renderMakeupOptions();
  handleLoadOptions();
}

function fillSampleFemale() {
  setGender('여성');
  $('face-shape').value = '둥근형';
  $('face-proportion').value = '균형';
  $('personal-color').value = '여름쿨';
  renderMakeupOptions();
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

function getRecommendedMakeupStyles() {
  const gender = getGender();
  const personalColor = $('personal-color').value;
  return (MAKEUP_STYLES_BY_GENDER_AND_PERSONAL_COLOR[gender] || {})[personalColor] || [];
}

function renderMakeupOptions() {
  const container = $('makeup-list');
  if (!container) return;

  const styles = getRecommendedMakeupStyles();
  container.innerHTML = '';

  styles.forEach((style) => {
    const label = document.createElement('label');
    const span = document.createElement('span');
    span.textContent = style.style_name;
    span.title = `코드: ${style.style_code} / 그룹: ${style.makeup_group}`;

    if (!appState.ragCoverage.has(style.style_code)) {
      span.classList.add('no-rag-data');
    }

    label.appendChild(span);
    container.appendChild(label);
  });
}

// ── DB 기반 추천 헤어 불러오기 ─────────────────────────────────────────────────
async function handleLoadOptions() {
  const gender          = getGender();
  const face_shape      = $('face-shape').value;
  const face_proportion = $('face-proportion').value;

  hideError('options-error');
  if (!gender) return showError('options-error', '성별을 선택해주세요.');

  const btn = $('btn-load-options');
  setLoading(btn, true, '불러오는 중...');
  $('btn-analyze').disabled = true;

  try {
    const res = await fetch('/api/hair-options', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ gender, face_shape, face_proportion }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError('options-error', data.error || `서버 오류 (HTTP ${res.status})`);
      $('hair-options-area').classList.add('hidden');
      return;
    }

    const recommended = data.recommended_styles || [];
    const worst       = data.worst_styles       || [];

    if (recommended.length === 0 && worst.length === 0) {
      showError('options-error', '해당 조건의 데이터가 없습니다. 다른 조건을 선택해주세요.');
      $('hair-options-area').classList.add('hidden');
      return;
    }

    renderHairOptions({ recommended, worst });
    $('hair-options-area').classList.remove('hidden');

  } catch (e) {
    showError('options-error', `오류: ${e.message}`);
  } finally {
    setLoading(btn, false, '추천 헤어 불러오기');
  }
}

function renderHairOptions({ recommended, worst }) {
  const container = $('style-list');
  container.innerHTML = '';
  setStyleCount(0);
  $('btn-analyze').disabled = true;

  if (recommended.length === 0) {
    const msg = document.createElement('div');
    msg.style.cssText = 'color:#aeaeb2;font-size:0.82rem;padding:8px 0;';
    msg.textContent = '추천 스타일 없음';
    container.appendChild(msg);
  } else {
    recommended.forEach(({ style_name, style_code }) => {
      const hasData = style_code && appState.ragCoverage.has(style_code);

      const label = document.createElement('label');
      const cb    = document.createElement('input');
      cb.type         = 'checkbox';
      cb.value        = style_code || style_name;
      cb.dataset.name = style_name;
      cb.dataset.code = style_code || '';
      cb.addEventListener('change', onStyleCheck);

      const span = document.createElement('span');
      span.textContent = style_name;
      if (style_code) span.title = `코드: ${style_code}`;
      if (!hasData)   span.classList.add('no-rag-data');

      label.appendChild(cb);
      label.appendChild(span);
      container.appendChild(label);
    });
  }

  if (worst.length > 0) {
    $('worst-area').classList.remove('hidden');
    const worstList = $('worst-list');
    worstList.innerHTML = '';
    worst.forEach(({ style_name, style_code }) => {
      const tag = document.createElement('span');
      tag.className   = 'worst-tag';
      tag.textContent = style_code ? `${style_name} (${style_code})` : style_name;
      worstList.appendChild(tag);
    });
  } else {
    $('worst-area').classList.add('hidden');
  }
}

function onStyleCheck() {
  const checked = getCheckedStyles();
  if (checked.length > 3) {
    this.checked = false;
    return;
  }
  setStyleCount(checked.length);
  $('btn-analyze').disabled = checked.length < 1;
}

function setStyleCount(n) {
  const el = $('style-count');
  el.textContent = `${n} / 3 선택됨`;
  el.className = 'style-count' + (n >= 1 ? ' done' : '');
}

function getCheckedStyles() {
  return Array.from(
    document.querySelectorAll('#style-list input[type="checkbox"]:checked')
  ).map((cb) => ({
    category: 'hair',
    style_name: cb.dataset.name,
    style_code: cb.dataset.code || null,
  }));
}

// ── 분석 요청 ─────────────────────────────────────────────────────────────────
async function handleAnalyze() {
  const gender                     = getGender();
  const face_shape                 = $('face-shape').value;
  const face_proportion            = $('face-proportion').value;
  const personal_color             = $('personal-color').value;
  const recommended_hair_styles    = getCheckedStyles();
  const recommended_makeup_styles  = getRecommendedMakeupStyles();

  hideError('analysis-error');

  if (!gender) return showError('analysis-error', '성별을 선택해주세요.');
  if (!personal_color) return showError('analysis-error', '퍼스널컬러를 선택해주세요.');
  if (recommended_hair_styles.length < 1 || recommended_hair_styles.length > 3) {
    return showError('analysis-error', '헤어스타일을 1~3개 선택해주세요.');
  }

  const noCode = recommended_hair_styles.filter((s) => !s.style_code);
  if (noCode.length > 0) {
    const names = noCode.map((s) => s.style_name).join(', ');
    showError('analysis-error',
      `[경고] 다음 스타일은 RAG 코드 매핑이 없어 검색 정확도가 낮을 수 있습니다: ${names}\n계속 진행합니다.`
    );
  }

  const btn = $('btn-analyze');
  setLoading(btn, true, '생성 중...');

  const elapsedEl = $('analysis-elapsed');
  const startTime = Date.now();
  elapsedEl.textContent = '';
  const timerInterval = setInterval(() => {
    elapsedEl.textContent = `(${((Date.now() - startTime) / 1000).toFixed(1)}초)`;
  }, 100);

  try {
    const res = await fetch('/api/analysis', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        gender,
        face_shape,
        face_proportion,
        personal_color,
        recommended_hair_styles,
        recommended_makeup_styles,
      }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError('analysis-error', data.error || `서버 오류 (HTTP ${res.status})`);
      return;
    }

    renderAnalysisResult(data);
    injectAnalysisToChat({ gender, face_shape, face_proportion, personal_color, data });
  } catch (e) {
    showError('analysis-error', `네트워크 오류: ${e.message}`);
  } finally {
    clearInterval(timerInterval);
    elapsedEl.textContent = `(${((Date.now() - startTime) / 1000).toFixed(1)}초 소요)`;
    setLoading(btn, false, '헤어 + 메이크업 분석 결과 생성');
    $('btn-analyze').disabled = getCheckedStyles().length < 1;
  }
}

function renderAnalysisResult(data) {
  $('analysis-result').classList.remove('hidden');

  $('res-hair-summary').textContent = data.hair_analysis_summary || '(없음)';
  $('res-makeup-summary').textContent = data.makeup_analysis_summary || '(메이크업 RAG 데이터 없음)';

  const hairLines = (data.hair_recommendations || []).map(
    (h) => `${h.style_name} (${h.style_code ?? 'code 없음'}) — 검색 ${h.retrieved_count}건, fallback: ${h.fallback_stage ?? 'none'}, has_rag_data: ${h.has_rag_data}`
  );
  $('res-hair').textContent = hairLines.join('\n') || '(없음)';

  const makeupLines = (data.makeup_recommendations || []).map(
    (m) => `${m.style_name} (${m.style_code ?? 'code 없음'}, group: ${m.makeup_group ?? '-'}) — 검색 ${m.retrieved_count}건, fallback: ${m.fallback_stage ?? 'none'}, has_rag_data: ${m.has_rag_data}`
  );
  $('res-makeup').textContent = makeupLines.join('\n') || '(없음)';

  const ri = data.retrieval_info || {};
  $('res-retrieval').textContent = [
    `헤어 문서: ${ri.hair_docs ?? 0}건 | fallback stages: ${JSON.stringify(ri.hair_fallback_stages || [])}`,
    `메이크업 문서: ${ri.makeup_docs ?? 0}건 | fallback stages: ${JSON.stringify(ri.makeup_fallback_stages || [])}`,
  ].join('\n');

  $('res-raw-json').textContent = JSON.stringify(data, null, 2);
}

// ── 분석 결과 → 챗봇 컨텍스트 자동 주입 ──────────────────────────────────────
function injectAnalysisToChat({ gender, face_shape, face_proportion, personal_color, data }) {
  $('chat-gender').value           = gender;
  $('chat-face-shape').value       = face_shape;
  $('chat-face-proportion').value  = face_proportion;
  $('chat-personal-color').value   = personal_color;

  const previousAnalysis = {
    hair_analysis_summary: data.hair_analysis_summary || null,
    makeup_analysis_summary: data.makeup_analysis_summary || null,
  };
  const previousRecommendations = [
    ...(data.hair_recommendations || []).map((item) => ({ ...item, category: 'hair' })),
    ...(data.makeup_recommendations || []).map((item) => ({ ...item, category: 'makeup' })),
  ];

  $('chat-prev-analysis').value    = JSON.stringify(previousAnalysis, null, 2);
  $('chat-prev-recs').value        = JSON.stringify(previousRecommendations, null, 2);
  $('chat-user-profile').value     = '{}';
}

// ── 챗봇 요청 ─────────────────────────────────────────────────────────────────
async function handleChat() {
  const user_message = $('chat-message').value.trim();
  if (!user_message) return;

  const skipAnalysis    = $('skip-analysis').checked;
  const gender          = $('chat-gender').value.trim();
  const face_shape      = $('chat-face-shape').value.trim();
  const face_proportion = $('chat-face-proportion').value.trim();
  const personal_color  = $('chat-personal-color').value.trim();

  let previous_analysis        = null;
  let previous_recommendations = [];
  let user_profile             = {};

  if (!skipAnalysis) {
    const rawPreviousAnalysis = $('chat-prev-analysis').value.trim();
    if (rawPreviousAnalysis) {
      try {
        previous_analysis = JSON.parse(rawPreviousAnalysis);
      } catch {
        previous_analysis = rawPreviousAnalysis;
      }
    }

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

  try {
    const res = await fetch('/api/chatbot', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        user_message,
        gender,
        face_shape,
        face_proportion,
        personal_color,
        previous_analysis,
        previous_recommendations,
        user_profile,
        chat_history: appState.chatHistory,
      }),
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
    `category: ${ri.category ?? data.category ?? '(없음)'}   retrieved_count: ${ri.retrieved_count ?? 0}   fallback_stage: ${ri.fallback_stage ?? 'none'}\nused_filter: ${JSON.stringify(ri.used_filter || {})}`;

  $('res-updated-profile').textContent  = JSON.stringify(data.updated_user_profile || {}, null, 2);
  $('res-chat-raw-json').textContent    = JSON.stringify(data, null, 2);
}

// ── 채팅 버블 ─────────────────────────────────────────────────────────────────
function appendBubble(role, text) {
  const container = $('chat-history');
  const empty = container.querySelector('.chat-empty');
  if (empty) empty.remove();

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;

  const roleEl = document.createElement('div');
  roleEl.className   = 'bubble-role';
  roleEl.textContent = role === 'user' ? '나' : 'AI';

  const textEl = document.createElement('div');
  textEl.className   = 'bubble-text';
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
  btn.disabled    = loading;
  btn.textContent = label;
}

document.addEventListener('DOMContentLoaded', init);
