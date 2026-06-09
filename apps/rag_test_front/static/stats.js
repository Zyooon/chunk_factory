'use strict';

// ── 마스터 스타일 목록 (헤어스타일_그룹.md 기준) ─────────────────────────────
const FEMALE_STYLES = [
  { code: 'f-01', name: '픽시' },    { code: 'f-02', name: '프리다' },
  { code: 'f-03', name: '보브' },    { code: 'f-04', name: '태슬' },
  { code: 'f-05', name: '원랭스' },  { code: 'f-06', name: '허그' },
  { code: 'f-07', name: '빌드' },    { code: 'f-08', name: '레이어드' },
  { code: 'f-09', name: '허쉬' },    { code: 'f-10', name: '샌드' },
  { code: 'f-11', name: '샤기' },    { code: 'f-12', name: '울프' },
  { code: 'f-13', name: '버드' },    { code: 'f-14', name: '히메' },
  { code: 'f-15', name: '다이앤' },  { code: 'f-16', name: '레아' },
  { code: 'f-17', name: '레인' },    { code: 'f-18', name: '그레이스' },
  { code: 'f-19', name: '엘리자벳' },{ code: 'f-20', name: '페미닌' },
  { code: 'f-21', name: '벌룬' },    { code: 'f-22', name: '코튼' },
  { code: 'f-23', name: '발롱' },    { code: 'f-24', name: '구름' },
  { code: 'f-25', name: '젤리' },    { code: 'f-26', name: '러플' },
  { code: 'f-27', name: '바그' },    { code: 'f-28', name: '프릴' },
  { code: 'f-29', name: '윈드' },    { code: 'f-30', name: '그런지' },
];

const MALE_STYLES = [
  { code: 'm-01', name: '버즈' },      { code: 'm-02', name: '하이앤타이트' },
  { code: 'm-03', name: '아이비리그' }, { code: 'm-04', name: '크롭' },
  { code: 'm-05', name: '드롭' },      { code: 'm-06', name: '슬릭' },
  { code: 'm-07', name: '허밍' },      { code: 'm-08', name: '댄디' },
  { code: 'm-09', name: '리프' },      { code: 'm-10', name: '퀴프' },
  { code: 'm-11', name: '울프' },      { code: 'm-12', name: '애즈' },
  { code: 'm-13', name: '시스루' },    { code: 'm-14', name: '쉐도우' },
  { code: 'm-15', name: '베이비' },    { code: 'm-16', name: '포마드' },
  { code: 'm-17', name: '히피' },      { code: 'm-18', name: '그런지' },
  { code: 'm-19', name: '리젠트' },
];

const EXPECTED_FACE_SHAPES  = ['계란형', '둥근형', '각진형', '장방형', '역삼각형'];
const EXPECTED_PROPORTIONS  = ['균형', '상안부_긴형', '중안부_긴형', '하안부_긴형'];
const EXPECTED_GENDERS      = ['여성', '남성'];

// ── 전역 상태 ────────────────────────────────────────────────────────────────
let byCondition = [];
let byStyle     = [];

// ── 유틸 ─────────────────────────────────────────────────────────────────────
function fmtProp(p) { return (p || '').replace(/_/g, ' '); }

function genderBadge(g) {
  const cls = g === '남성' ? 'male' : 'female';
  return `<span class="badge ${cls}">${g}</span>`;
}

// ── 초기화 ───────────────────────────────────────────────────────────────────
async function init() {
  try {
    const res  = await fetch('/api/beauty-stats');
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || `서버 오류 (HTTP ${res.status})`);
      return;
    }

    byCondition = data.by_condition || [];
    byStyle     = data.by_style     || [];

    document.getElementById('loading-msg').classList.add('hidden');

    renderSummary(data.summary);
    populateConditionFilters();
    renderConditionTable();
    renderStyleTable();
    renderMissingList();

    ['card-summary', 'card-condition', 'card-style', 'card-missing'].forEach((id) => {
      document.getElementById(id).classList.remove('hidden');
    });

    // 필터 이벤트
    ['cond-gender', 'cond-shape', 'cond-prop'].forEach((id) => {
      document.getElementById(id).addEventListener('change', renderConditionTable);
    });
    document.getElementById('style-gender').addEventListener('change', renderStyleTable);

  } catch (e) {
    showError(`네트워크 오류: ${e.message}`);
  }
}

// ── ① 요약 카드 ──────────────────────────────────────────────────────────────
function renderSummary(s) {
  document.getElementById('sum-total').textContent  = s.total.toLocaleString();
  document.getElementById('sum-rec').textContent    = s.recommended.toLocaleString();
  document.getElementById('sum-notrec').textContent = s.not_recommended.toLocaleString();
  document.getElementById('sum-review').textContent = s.needs_review.toLocaleString();
  document.getElementById('sum-reason').textContent = s.needs_reason_fill.toLocaleString();
}

// ── ② 조건별 테이블 ──────────────────────────────────────────────────────────
function populateConditionFilters() {
  const shapes = [...new Set(byCondition.map((r) => r.face_shape))].sort();
  const props  = [...new Set(byCondition.map((r) => r.face_proportion))].sort();

  const shapeEl = document.getElementById('cond-shape');
  shapes.forEach((s) => {
    const opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    shapeEl.appendChild(opt);
  });

  const propEl = document.getElementById('cond-prop');
  props.forEach((p) => {
    const opt = document.createElement('option');
    opt.value = p; opt.textContent = fmtProp(p);
    propEl.appendChild(opt);
  });
}

function renderConditionTable() {
  const gender = document.getElementById('cond-gender').value;
  const shape  = document.getElementById('cond-shape').value;
  const prop   = document.getElementById('cond-prop').value;

  const rows = byCondition.filter((r) => {
    if (gender !== 'all' && r.gender          !== gender) return false;
    if (shape  !== 'all' && r.face_shape      !== shape)  return false;
    if (prop   !== 'all' && r.face_proportion !== prop)   return false;
    return true;
  });

  const tbody = document.getElementById('cond-tbody');
  tbody.innerHTML = '';

  if (rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#aeaeb2;padding:20px;">데이터 없음</td></tr>';
    return;
  }

  rows.forEach((r) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${genderBadge(r.gender)}</td>
      <td>${r.face_shape}</td>
      <td>${fmtProp(r.face_proportion)}</td>
      <td><strong>${r.total}</strong></td>
      <td class="num-rec">${r.recommended}</td>
      <td class="num-notrec">${r.not_recommended}</td>
      <td class="num-review">${r.needs_review}</td>
      <td class="num-reason">${r.needs_reason_fill}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── ③ 스타일별 등록 현황 ─────────────────────────────────────────────────────
function renderStyleTable() {
  const gender = document.getElementById('style-gender').value;

  // DB에 있는 스타일
  const dbRows = byStyle.filter((r) => gender === 'all' || r.gender === gender);

  // 마스터에 있으나 DB에 없는 스타일 (미등록)
  const dbKeys = new Set(byStyle.map((r) => r.style_code));
  const unregistered = [];

  const checkMaster = (styles, g) => {
    if (gender !== 'all' && g !== gender) return;
    styles.forEach((s) => {
      if (!dbKeys.has(s.code)) {
        unregistered.push({ gender: g, style_code: s.code, style_name: s.name });
      }
    });
  };
  checkMaster(FEMALE_STYLES, '여성');
  checkMaster(MALE_STYLES,   '남성');

  const tbody = document.getElementById('style-tbody');
  tbody.innerHTML = '';

  // DB 등록 행
  dbRows.forEach((r) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${genderBadge(r.gender)}</td>
      <td class="code-cell">${r.style_code}</td>
      <td>${r.style_name}</td>
      <td><strong>${r.total}</strong></td>
      <td class="num-rec">${r.recommended}</td>
      <td class="num-notrec">${r.not_recommended}</td>
      <td class="num-review">${r.needs_review}</td>
      <td class="num-reason">${r.needs_reason_fill}</td>
    `;
    tbody.appendChild(tr);
  });

  // 미등록 행 (회색)
  unregistered.forEach((r) => {
    const tr = document.createElement('tr');
    tr.classList.add('row-unreg');
    tr.innerHTML = `
      <td>${genderBadge(r.gender)}</td>
      <td class="code-cell">${r.style_code}</td>
      <td>${r.style_name} <span class="badge unreg">미등록</span></td>
      <td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
    `;
    tbody.appendChild(tr);
  });

  if (dbRows.length === 0 && unregistered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#aeaeb2;padding:20px;">데이터 없음</td></tr>';
  }
}

// ── ④ 부족 데이터 목록 ───────────────────────────────────────────────────────
function renderMissingList() {
  // -- 미등록/부족 조합 --
  const condMap = new Map(
    byCondition.map((r) => [`${r.gender}|${r.face_shape}|${r.face_proportion}`, r.total])
  );

  const missingConds = [];
  const insufficientConds = [];

  EXPECTED_GENDERS.forEach((g) => {
    EXPECTED_FACE_SHAPES.forEach((s) => {
      EXPECTED_PROPORTIONS.forEach((p) => {
        const key   = `${g}|${s}|${p}`;
        const count = condMap.get(key) ?? 0;
        if (count === 0)       missingConds.push({ g, s, p, count });
        else if (count <= 4)   insufficientConds.push({ g, s, p, count });
      });
    });
  });

  const renderConds = (listId, cntId, items, tagClass) => {
    const listEl = document.getElementById(listId);
    const cntEl  = document.getElementById(cntId);
    cntEl.textContent = `(${items.length}건)`;
    listEl.innerHTML  = '';
    if (items.length === 0) {
      listEl.innerHTML = '<span class="no-data-msg">없음</span>';
      return;
    }
    items.forEach(({ g, s, p, count }) => {
      const span = document.createElement('span');
      span.className = `tag ${tagClass}`;
      span.textContent = count !== undefined && count > 0
        ? `${g} / ${s} / ${fmtProp(p)} (${count}건)`
        : `${g} / ${s} / ${fmtProp(p)}`;
      listEl.appendChild(span);
    });
  };

  renderConds('list-missing-cond', 'cnt-missing-cond', missingConds, 'missing');
  renderConds('list-insuf-cond',   'cnt-insuf-cond',   insufficientConds, 'insufficient');

  // -- 미등록 스타일 --
  const dbKeys = new Set(byStyle.map((r) => r.style_code));
  const missingStyles = [];

  FEMALE_STYLES.forEach((s) => { if (!dbKeys.has(s.code)) missingStyles.push({ ...s, g: '여성' }); });
  MALE_STYLES.forEach((s)   => { if (!dbKeys.has(s.code)) missingStyles.push({ ...s, g: '남성' }); });

  const styleListEl = document.getElementById('list-missing-style');
  const styleCntEl  = document.getElementById('cnt-missing-style');
  styleCntEl.textContent = `(${missingStyles.length}건)`;
  styleListEl.innerHTML  = '';

  if (missingStyles.length === 0) {
    styleListEl.innerHTML = '<span class="no-data-msg">없음</span>';
  } else {
    missingStyles.forEach(({ g, code, name }) => {
      const span = document.createElement('span');
      span.className = 'tag style-miss';
      span.textContent = `${g} ${code} ${name}`;
      styleListEl.appendChild(span);
    });
  }
}

// ── 에러 ─────────────────────────────────────────────────────────────────────
function showError(msg) {
  document.getElementById('loading-msg').classList.add('hidden');
  const el = document.getElementById('stats-error');
  el.textContent = `오류: ${msg}`;
  el.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', init);
