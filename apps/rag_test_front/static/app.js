'use strict';

// ── hair_style_mapping.md 내장 데이터 ─────────────────────────────────────────
// 키: 성별 → 얼굴형 → 삼정(select value 기준) → { rank1, rank2 }
const HAIR_STYLE_MAPPING = {
  '여성': {
    '계란형': {
      '균형':       { rank1: ['프리다', '코튼'],                        rank2: ['원랭스', '페미닌', '바그'] },
      '상안부_긴형': { rank1: ['울프', '버드', '다이앤'],               rank2: ['히메'] },
      '중안부_긴형': { rank1: ['윈드', '빌드'],                         rank2: [] },
      '하안부_긴형': { rank1: ['허그'],                                 rank2: ['페미닌'] },
    },
    '둥근형': {
      '균형':       { rank1: ['페미닌'],                               rank2: ['레이어드'] },
      '상안부_긴형': { rank1: ['태슬'],                                 rank2: ['구름'] },
      '중안부_긴형': { rank1: ['빌드', '샌드', '레아', '엘리자벳'],    rank2: ['발롱'] },
      '하안부_긴형': { rank1: ['레이어드'],                            rank2: ['빌드', '샌드'] },
    },
    '각진형': {
      '균형':       { rank1: ['보브', '레이어드'],                     rank2: ['프리다', '레인', '코튼'] },
      '상안부_긴형': { rank1: ['샤기', '다이앤'],                      rank2: ['구름', '프릴'] },
      '중안부_긴형': { rank1: ['빌드', '샌드'],                        rank2: ['엘리자벳', '벌룬', '발롱', '젤리', '러플', '윈드'] },
      '하안부_긴형': { rank1: ['허그', '허쉬'],                        rank2: [] },
    },
    '장방형': {
      '균형':       { rank1: ['보브', '원랭스', '레이어드', '레인', '그레이스', '바그'], rank2: ['코튼'] },
      '상안부_긴형': { rank1: ['샤기', '구름', '프릴'],                rank2: [] },
      '중안부_긴형': { rank1: ['벌룬', '발롱', '젤리', '러플', '윈드'], rank2: ['빌드', '엘리자벳'] },
      '하안부_긴형': { rank1: ['허쉬', '발롱'],                        rank2: ['구름'] },
    },
    '역삼각형': {
      '균형':       { rank1: ['원랭스', '페미닌'],                     rank2: ['바그', '태슬'] },
      '상안부_긴형': { rank1: ['히메'],                                rank2: ['태슬'] },
      '중안부_긴형': { rank1: ['레아', '벌룬'],                        rank2: ['러플', '윈드'] },
      '하안부_긴형': { rank1: ['태슬', '러플'],                        rank2: ['레아', '발롱'] },
    },
    '긴얼굴형': {
      '균형':       { rank1: ['구름', '발롱'],                         rank2: ['빌드', '벌룬'] },
      '상안부_긴형': { rank1: ['다이앤', '프릴'],                      rank2: ['샤기', '태슬'] },
      '중안부_긴형': { rank1: ['벌룬', '구름'],                        rank2: ['젤리', '러플'] },
      '하안부_긴형': { rank1: ['허쉬', '발롱'],                        rank2: ['레이어드', '그런지'] },
    },
  },
  '남성': {
    '계란형': {
      '균형':       { rank1: ['아이비리그', '댄디'],                   rank2: ['하이앤타이트', '허밍'] },
      '상안부_긴형': { rank1: ['드롭', '슬릭', '울프', '시스루'],      rank2: [] },
      '중안부_긴형': { rank1: ['애즈'],                                rank2: [] },
      '하안부_긴형': { rank1: ['울프', '애즈', '포마드'],              rank2: [] },
    },
    '둥근형': {
      '균형':       { rank1: ['버즈'],                                 rank2: ['하이앤타이트', '아이비리그'] },
      '상안부_긴형': { rank1: ['크롭', '퀴프'],                        rank2: ['슬릭', '울프', '시스루'] },
      '중안부_긴형': { rank1: ['퀴프'],                                rank2: ['애즈'] },
      '하안부_긴형': { rank1: ['포마드'],                              rank2: ['울프', '애즈'] },
    },
    '각진형': {
      '균형':       { rank1: ['하이앤타이트'],                         rank2: ['아이비리그', '허밍', '베이비'] },
      '상안부_긴형': { rank1: ['드롭', '쉐도우'],                      rank2: ['크롭', '퀴프', '울프', '베이비', '히피'] },
      '중안부_긴형': { rank1: ['리프', '애즈'],                        rank2: ['퀴프', '히피', '그런지'] },
      '하안부_긴형': { rank1: ['포마드', '그런지'],                    rank2: ['울프', '애즈'] },
    },
    '장방형': {
      '균형':       { rank1: ['허밍', '베이비'],                       rank2: ['댄디'] },
      '상안부_긴형': { rank1: ['쉐도우', '베이비', '히피'],            rank2: ['드롭', '울프', '시스루'] },
      '중안부_긴형': { rank1: ['리프', '히피', '그런지'],              rank2: [] },
      '하안부_긴형': { rank1: ['그런지'],                              rank2: ['울프'] },
    },
    '역삼각형': {
      '균형':       { rank1: ['히피', '퀴프'],                         rank2: ['베이비', '슬릭'] },
      '상안부_긴형': { rank1: ['크롭', '슬릭'],                        rank2: ['울프', '쉐도우'] },
      '중안부_긴형': { rank1: ['히피', '애즈'],                        rank2: ['퀴프', '그런지'] },
      '하안부_긴형': { rank1: ['울프', '포마드'],                      rank2: ['애즈', '히피'] },
    },
    '긴얼굴형': {
      '균형':       { rank1: ['허밍', '댄디'],                         rank2: ['아이비리그', '시스루'] },
      '상안부_긴형': { rank1: ['크롭', '베이비'],                      rank2: ['드롭', '쉐도우'] },
      '중안부_긴형': { rank1: ['퀴프', '히피'],                        rank2: ['리프', '애즈'] },
      '하안부_긴형': { rank1: ['울프', '그런지'],                      rank2: ['포마드', '애즈'] },
    },
  },
};

// ── 앱 상태 ──────────────────────────────────────────────────────────────────
const appState = {
  chatHistory: [],
  styleCodeMap: {},     // style_name → style_code (서버에서 1회 로드)
  ragCoverage: new Set(), // ChromaDB 데이터가 있는 style_code 집합
};

// ── DOM 헬퍼 ─────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── 초기화 ───────────────────────────────────────────────────────────────────
async function init() {
  setGender('남성');
  await Promise.all([loadStyleCodeMap(), loadRagCoverage()]);

  $('btn-sample-male').addEventListener('click', fillSampleMale);
  $('btn-sample-female').addEventListener('click', fillSampleFemale);
  $('btn-load-options').addEventListener('click', handleLoadOptions);
  $('btn-analyze').addEventListener('click', handleAnalyze);
  $('btn-chat').addEventListener('click', handleChat);
  $('btn-reset-chat').addEventListener('click', resetChat);
}

async function loadStyleCodeMap() {
  try {
    const res = await fetch('/api/hair-style-map');
    if (res.ok) appState.styleCodeMap = await res.json();
  } catch {
    appState.styleCodeMap = {};
  }
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

// ── 매핑 기반 추천 헤어 불러오기 (hair_style_mapping.md 기준) ─────────────────
async function handleLoadOptions() {
  const gender       = getGender();
  const face_shape   = $('face-shape').value;
  const face_proportion = $('face-proportion').value;

  hideError('options-error');
  if (!gender) return showError('options-error', '성별을 선택해주세요.');

  const btn = $('btn-load-options');
  setLoading(btn, true, '불러오는 중...');
  $('btn-analyze').disabled = true;

  try {
    const mapping = HAIR_STYLE_MAPPING[gender]?.[face_shape]?.[face_proportion];

    if (!mapping || (mapping.rank1.length === 0 && mapping.rank2.length === 0)) {
      showError('options-error', '해당 조건의 매핑 데이터가 없습니다. 다른 조건을 선택해주세요.');
      $('hair-options-area').classList.add('hidden');
      return;
    }

    const toStyleObj = (name) => ({
      style_name: name,
      style_code:  appState.styleCodeMap[name] ?? null,
    });

    renderHairOptions({
      rank1: mapping.rank1.map(toStyleObj),
      rank2: mapping.rank2.map(toStyleObj),
    });
    $('hair-options-area').classList.remove('hidden');

  } catch (e) {
    showError('options-error', `오류: ${e.message}`);
  } finally {
    setLoading(btn, false, '추천 헤어 불러오기');
  }
}

function renderHairOptions({ rank1, rank2 }) {
  const container = $('style-list');
  container.innerHTML = '';
  setStyleCount(0);
  $('btn-analyze').disabled = true;

  const addGroup = (styles, rankLabel) => {
    if (styles.length === 0) return;

    const divider = document.createElement('div');
    divider.className = 'style-rank-label';
    divider.textContent = rankLabel;
    container.appendChild(divider);

    styles.forEach(({ style_name, style_code }) => {
      const hasData = style_code && appState.ragCoverage.has(style_code);

      const label = document.createElement('label');
      const cb    = document.createElement('input');
      cb.type          = 'checkbox';
      cb.value         = style_code || style_name;
      cb.dataset.name  = style_name;
      cb.dataset.code  = style_code || '';
      cb.addEventListener('change', onStyleCheck);

      const span = document.createElement('span');
      span.textContent = style_name;
      if (style_code) span.title = `코드: ${style_code}`;
      if (!hasData) span.classList.add('no-rag-data');

      label.appendChild(cb);
      label.appendChild(span);
      container.appendChild(label);
    });
  };

  const hasRank2 = rank2.length > 0;
  addGroup(rank1, hasRank2 ? '★ 1순위' : '추천');
  addGroup(rank2, '2순위+');

  // 비추천은 MD에 없으므로 숨김
  $('worst-area').classList.add('hidden');
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
  if (recommended_hair_styles.length < 1 || recommended_hair_styles.length > 3) {
    return showError('analysis-error', '헤어스타일을 1~3개 선택해주세요.');
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

  const elapsedEl = $('analysis-elapsed');
  const startTime = Date.now();
  elapsedEl.textContent = '';
  const timerInterval = setInterval(() => {
    const s = ((Date.now() - startTime) / 1000).toFixed(1);
    elapsedEl.textContent = `(${s}초)`;
  }, 100);

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
    clearInterval(timerInterval);
    const finalS = ((Date.now() - startTime) / 1000).toFixed(1);
    elapsedEl.textContent = `(${finalS}초 소요)`;
    setLoading(btn, false, '분석 결과 생성');
    $('btn-analyze').disabled = getCheckedStyles().length < 1;
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
