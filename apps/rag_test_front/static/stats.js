'use strict';

// ── 전역 상태 ──────────────────────────────────────────────────────────────────
let rawItems      = [];   // { gender, face_shape, face_proportion, style_name, style_code, is_recommended }
let conditionCounts = []; // { gender, face_shape, face_proportion, doc_count }
let coverageData  = [];   // 계산된 커버리지 배열 (체크박스 토글 시 재사용)
let sortCol = 'recommended_count';
let sortDir = 'desc';
let selectedStyle = null; // 클릭된 스타일 행

// ── 스타일 정규화 유틸 ──────────────────────────────────────────────────────────
function normalizeStyleItem(item) {
  if (typeof item === 'string') return { style_name: item, style_code: null };
  return { style_name: item.style_name || '', style_code: item.style_code || null };
}

function getStyleKey(style) {
  return style.style_code || style.style_name || '';
}

function getStyleName(style) {
  return style.style_name || '';
}

function getStyleCode(style) {
  return style.style_code || null;
}

function formatFaceProportion(fp) {
  return (fp || '').replace(/_/g, ' ');
}

// ── 필터 값 읽기 ───────────────────────────────────────────────────────────────
function getGenderFilter()      { return document.getElementById('gender-filter').value; }
function getFaceShapeFilter()   { return document.getElementById('face-shape-filter').value; }
function getFaceProportionFilter() { return document.getElementById('face-proportion-filter').value; }

// ── 초기화 ─────────────────────────────────────────────────────────────────────
async function init() {
  await loadStats();

  document.getElementById('gender-filter').addEventListener('change', onFilterChange);
  document.getElementById('face-shape-filter').addEventListener('change', onFilterChange);
  document.getElementById('face-proportion-filter').addEventListener('change', onFilterChange);
  document.getElementById('only-insufficient-cb').addEventListener('change', renderCoverageTable);
  document.getElementById('detail-close-btn').addEventListener('click', closeDetailPanel);

  document.querySelectorAll('#stats-table thead th[data-col]').forEach((th) => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (sortCol === col) {
        sortDir = sortDir === 'desc' ? 'asc' : 'desc';
      } else {
        sortCol = col;
        sortDir = ['recommended_count', 'worst_count', 'total_count'].includes(col) ? 'desc' : 'asc';
      }
      renderStyleTable();
    });
  });
}

// ── 데이터 로드 ─────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res  = await fetch('/api/hair-stats-raw');
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || `서버 오류 (HTTP ${res.status})`);
      return;
    }

    rawItems        = data.items           || [];
    conditionCounts = data.condition_counts || [];

    document.getElementById('sum-rows').textContent   = (data.summary?.total_rows   ?? '-').toLocaleString();
    document.getElementById('sum-styles').textContent = (data.summary?.total_styles ?? '-').toLocaleString();

    populateFilterOptions(data.face_shapes || [], data.face_proportions || []);

    document.getElementById('loading-msg').classList.add('hidden');
    document.getElementById('table-wrap').classList.remove('hidden');
    document.getElementById('coverage-card').classList.remove('hidden');

    renderAll();
  } catch (e) {
    showError(`네트워크 오류: ${e.message}`);
  }
}

function populateFilterOptions(faceShapes, faceProportions) {
  const fsSelect = document.getElementById('face-shape-filter');
  faceShapes.forEach((fs) => {
    const opt = document.createElement('option');
    opt.value = fs;
    opt.textContent = fs;
    fsSelect.appendChild(opt);
  });

  const fpSelect = document.getElementById('face-proportion-filter');
  faceProportions.forEach((fp) => {
    const opt = document.createElement('option');
    opt.value = fp;
    opt.textContent = formatFaceProportion(fp);
    fpSelect.appendChild(opt);
  });
}

// ── 필터 변경 처리 ──────────────────────────────────────────────────────────────
function onFilterChange() {
  selectedStyle = null;
  document.getElementById('style-detail-panel').classList.add('hidden');
  renderAll();
}

function renderAll() {
  renderConditionLabel();
  renderStyleTable();
  computeAndRenderCoverage();
}

// ── 현재 조건 라벨 ──────────────────────────────────────────────────────────────
function renderConditionLabel() {
  const gender  = getGenderFilter();
  const shape   = getFaceShapeFilter();
  const prop    = getFaceProportionFilter();

  const parts = [
    gender === 'all' ? '전체 성별' : gender,
    shape  === 'all' ? '얼굴형 전체' : shape,
    prop   === 'all' ? '삼정 전체'   : formatFaceProportion(prop),
  ];
  document.getElementById('condition-label').textContent = `현재 조건: ${parts.join(' / ')}`;
}

// ── rawItems 필터링 ────────────────────────────────────────────────────────────
function filterRawItems(gender, shape, prop) {
  return rawItems.filter((r) => {
    if (gender !== 'all' && r.gender          !== gender) return false;
    if (shape  !== 'all' && r.face_shape      !== shape)  return false;
    if (prop   !== 'all' && r.face_proportion !== prop)   return false;
    return true;
  });
}

// ── 스타일별 집계 ──────────────────────────────────────────────────────────────
function aggregateStyleStats(items) {
  const map = new Map();
  items.forEach((r) => {
    const key = `${r.gender}__${r.style_code || r.style_name}`;
    if (!map.has(key)) {
      map.set(key, {
        gender:            r.gender,
        style_name:        r.style_name,
        style_code:        r.style_code,
        recommended_count: 0,
        worst_count:       0,
        total_count:       0,
      });
    }
    const e = map.get(key);
    if (r.is_recommended) e.recommended_count++;
    else                  e.worst_count++;
    e.total_count++;
  });
  return Array.from(map.values());
}

// ── 스타일 테이블 렌더링 ───────────────────────────────────────────────────────
function renderStyleTable() {
  const gender = getGenderFilter();
  const shape  = getFaceShapeFilter();
  const prop   = getFaceProportionFilter();

  let items = aggregateStyleStats(filterRawItems(gender, shape, prop));

  items = [...items].sort((a, b) => {
    let va = a[sortCol] ?? '';
    let vb = b[sortCol] ?? '';
    if (typeof va === 'number' && typeof vb === 'number') {
      return sortDir === 'desc' ? vb - va : va - vb;
    }
    va = String(va); vb = String(vb);
    return sortDir === 'desc' ? vb.localeCompare(va, 'ko') : va.localeCompare(vb, 'ko');
  });

  const maxRec  = Math.max(1, ...items.map((r) => r.recommended_count));
  const maxWrst = Math.max(1, ...items.map((r) => r.worst_count));

  document.querySelectorAll('#stats-table thead th').forEach((th) => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.col === sortCol) {
      th.classList.add(sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
    }
  });

  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = '';

  if (items.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="6" style="text-align:center;color:#aeaeb2;padding:20px;">데이터 없음</td>';
    tbody.appendChild(tr);
    return;
  }

  items.forEach((row) => {
    const tr = document.createElement('tr');
    tr.classList.add('clickable');

    const isSelected = selectedStyle &&
      (selectedStyle.style_code
        ? selectedStyle.style_code === row.style_code && selectedStyle.gender === row.gender
        : selectedStyle.style_name === row.style_name && selectedStyle.gender === row.gender);

    if (isSelected) tr.classList.add('selected-row');

    const genderClass = row.gender === '남성' ? 'male' : 'female';
    const codeHtml    = row.style_code
      ? `<span class="code-cell">${row.style_code}</span>`
      : `<span class="no-code">미등록</span>`;

    const recPct  = ((row.recommended_count / maxRec)  * 100).toFixed(0);
    const wrstPct = ((row.worst_count       / maxWrst) * 100).toFixed(0);

    tr.innerHTML = `
      <td><span class="gender-badge ${genderClass}">${row.gender}</span></td>
      <td>${row.style_name}</td>
      <td>${codeHtml}</td>
      <td class="bar-cell">
        <div class="bar-wrap">
          <div class="bar-bg"><div class="bar-fill rec" style="width:${recPct}%"></div></div>
          <span class="bar-num rec">${row.recommended_count}</span>
        </div>
      </td>
      <td class="bar-cell">
        <div class="bar-wrap">
          <div class="bar-bg"><div class="bar-fill wrst" style="width:${wrstPct}%"></div></div>
          <span class="bar-num wrst">${row.worst_count}</span>
        </div>
      </td>
      <td><strong>${row.total_count}</strong></td>
    `;
    tr.title = '클릭하면 조건별 등장 상세를 볼 수 있습니다';
    tr.addEventListener('click', () => onStyleRowClick(row));
    tbody.appendChild(tr);
  });
}

// ── 스타일 행 클릭 ─────────────────────────────────────────────────────────────
function onStyleRowClick(row) {
  const sameStyle = selectedStyle &&
    selectedStyle.gender === row.gender &&
    (selectedStyle.style_code
      ? selectedStyle.style_code === row.style_code
      : selectedStyle.style_name === row.style_name);

  if (sameStyle) {
    closeDetailPanel();
    return;
  }

  selectedStyle = row;
  renderStyleTable();
  renderStyleDetailPanel(row);
}

function closeDetailPanel() {
  selectedStyle = null;
  document.getElementById('style-detail-panel').classList.add('hidden');
  renderStyleTable();
}

// ── 스타일 상세 패널 렌더링 ───────────────────────────────────────────────────
function renderStyleDetailPanel(style) {
  const gender = getGenderFilter();

  document.getElementById('detail-title').textContent =
    `[${style.style_name}] 조건별 등장 현황`;
  document.getElementById('detail-gender-label').textContent =
    gender === 'all' ? '현재 성별 기준 상세: 전체 성별' : `현재 성별 기준 상세: ${gender}`;

  // 이 스타일이 등장하는 rawItems 필터 (얼굴형/삼정 필터 무시, 성별만 적용)
  const styleCode = style.style_code;
  const filtered  = rawItems.filter((r) => {
    if (gender !== 'all' && r.gender !== gender) return false;
    return styleCode ? r.style_code === styleCode : r.style_name === style.style_name;
  });

  // (gender, face_shape, face_proportion) 별 집계
  const map = new Map();
  filtered.forEach((r) => {
    const key = `${r.gender}|${r.face_shape}|${r.face_proportion}`;
    if (!map.has(key)) {
      map.set(key, {
        gender:            r.gender,
        face_shape:        r.face_shape,
        face_proportion:   r.face_proportion,
        recommended_count: 0,
        worst_count:       0,
        total_count:       0,
      });
    }
    const e = map.get(key);
    if (r.is_recommended) e.recommended_count++;
    else                  e.worst_count++;
    e.total_count++;
  });

  const detailItems = Array.from(map.values()).sort((a, b) => {
    if (b.total_count !== a.total_count) return b.total_count - a.total_count;
    return b.recommended_count - a.recommended_count;
  });

  const tbody = document.getElementById('detail-tbody');
  tbody.innerHTML = '';

  if (detailItems.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="6" style="text-align:center;color:#aeaeb2;padding:16px;">해당 조건의 데이터 없음</td>';
    tbody.appendChild(tr);
  } else {
    detailItems.forEach((r) => {
      const tr = document.createElement('tr');
      const gc = r.gender === '남성' ? 'male' : 'female';
      tr.innerHTML = `
        <td><span class="gender-badge ${gc}">${r.gender}</span></td>
        <td>${r.face_shape}</td>
        <td>${formatFaceProportion(r.face_proportion)}</td>
        <td class="rec-count">${r.recommended_count}</td>
        <td class="wrst-count">${r.worst_count}</td>
        <td><strong>${r.total_count}</strong></td>
      `;
      tbody.appendChild(tr);
    });
  }

  document.getElementById('style-detail-panel').classList.remove('hidden');
}

// ── 커버리지 섹션 ──────────────────────────────────────────────────────────────
const STATUS_ORDER = { '없음': 0, '매우 부족': 1, '부족': 2, '편향': 3, '보통': 4 };
const STATUS_CLASS = {
  '없음':    's-none',
  '매우 부족': 's-very-poor',
  '부족':    's-poor',
  '편향':    's-biased',
  '보통':    's-normal',
};

function getStatus(docCount, recCount, worstCount) {
  if (docCount === 0)                         return '없음';
  if (docCount <= 2)                          return '매우 부족';
  if (docCount <= 5)                          return '부족';
  if (recCount === 0 || worstCount === 0)     return '편향';
  return '보통';
}

function computeAndRenderCoverage() {
  const gender = getGenderFilter();

  const combos = conditionCounts.filter((c) =>
    gender === 'all' || c.gender === gender
  );

  coverageData = combos.map((combo) => {
    const filtered = rawItems.filter((r) =>
      r.gender          === combo.gender &&
      r.face_shape      === combo.face_shape &&
      r.face_proportion === combo.face_proportion
    );

    let recCount = 0, worstCount = 0;
    const recStyles   = new Set();
    const worstStyles = new Set();

    filtered.forEach((r) => {
      const key = r.style_code || r.style_name;
      if (r.is_recommended) { recCount++;   recStyles.add(key); }
      else                  { worstCount++; worstStyles.add(key); }
    });

    const status = getStatus(combo.doc_count, recCount, worstCount);

    return {
      gender:              combo.gender,
      face_shape:          combo.face_shape,
      face_proportion:     combo.face_proportion,
      doc_count:           combo.doc_count,
      rec_count:           recCount,
      worst_count:         worstCount,
      unique_rec_styles:   recStyles.size,
      unique_worst_styles: worstStyles.size,
      status,
    };
  });

  // 상태 심각도 → 문서 수 오름차순
  coverageData.sort((a, b) => {
    const sa = STATUS_ORDER[a.status];
    const sb = STATUS_ORDER[b.status];
    if (sa !== sb) return sa - sb;
    return a.doc_count - b.doc_count;
  });

  // 요약 카드
  const total        = coverageData.length;
  const noData       = coverageData.filter((c) => c.status === '없음').length;
  const insufficient = coverageData.filter((c) => ['매우 부족', '부족'].includes(c.status)).length;
  const biased       = coverageData.filter((c) => c.status === '편향').length;

  document.getElementById('cov-total').textContent       = total;
  document.getElementById('cov-no-data').textContent     = noData;
  document.getElementById('cov-insufficient').textContent = insufficient;
  document.getElementById('cov-biased').textContent      = biased;

  renderCoverageTable();
}

function renderCoverageTable() {
  const onlyInsufficient = document.getElementById('only-insufficient-cb').checked;
  const items = onlyInsufficient
    ? coverageData.filter((c) => c.status !== '보통')
    : coverageData;

  const tbody = document.getElementById('coverage-tbody');
  tbody.innerHTML = '';

  if (items.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="9" style="text-align:center;color:#aeaeb2;padding:20px;">표시할 데이터 없음</td>';
    tbody.appendChild(tr);
    return;
  }

  items.forEach((r) => {
    const tr   = document.createElement('tr');
    const gc   = r.gender === '남성' ? 'male' : 'female';
    const sCls = STATUS_CLASS[r.status] || 's-normal';
    tr.innerHTML = `
      <td><span class="gender-badge ${gc}">${r.gender}</span></td>
      <td>${r.face_shape}</td>
      <td>${formatFaceProportion(r.face_proportion)}</td>
      <td>${r.doc_count}</td>
      <td class="rec-count">${r.rec_count}</td>
      <td class="wrst-count">${r.worst_count}</td>
      <td>${r.unique_rec_styles}</td>
      <td>${r.unique_worst_styles}</td>
      <td><span class="status-badge ${sCls}">${r.status}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

// ── 에러 표시 ──────────────────────────────────────────────────────────────────
function showError(msg) {
  document.getElementById('loading-msg').classList.add('hidden');
  const el = document.getElementById('stats-error');
  el.textContent = `오류: ${msg}`;
  el.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', init);
