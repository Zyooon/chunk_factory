'use strict';

// ── 전역 상태 ──────────────────────────────────────────────────────────────────
// 고정 기준 조합 (얼굴형 5 × 삼정 4 × 성별 2 = 40)
const EXPECTED_GENDERS     = ['남성', '여성'];
const EXPECTED_FACE_SHAPES = ['계란형', '둥근형', '각진형', '장방형', '역삼각형'];
const EXPECTED_PROPORTIONS = ['균형', '상안부_긴형', '중안부_긴형', '하안부_긴형'];

let rawItems        = [];   // { gender, face_shape, face_proportion, style_name, style_code, is_recommended }
let conditionCounts = [];   // { gender, face_shape, face_proportion, doc_count }
let allHairStyles   = [];   // hair_styles 테이블 전체 (매핑 없는 스타일 포함)
let coverageData    = [];   // 계산된 커버리지 배열 (체크박스 토글 시 재사용)
let sortCol = 'recommended_count';
let sortDir = 'desc';
let selectedStyle       = null; // 클릭된 스타일 행
let selectedMatrixCombo = null; // 클릭된 매트릭스 셀 { gender, face_shape, face_proportion }

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
  document.getElementById('matrix-detail-close-btn').addEventListener('click', closeMatrixDetailPanel);

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

    rawItems        = data.items            || [];
    conditionCounts = data.condition_counts || [];
    allHairStyles   = data.all_hair_styles  || [];

    document.getElementById('sum-rows').textContent   = (data.summary?.total_rows   ?? '-').toLocaleString();
    document.getElementById('sum-styles').textContent = (data.summary?.total_styles ?? '-').toLocaleString();

    populateFilterOptions(data.face_shapes || [], data.face_proportions || []);

    document.getElementById('loading-msg').classList.add('hidden');
    document.getElementById('table-wrap').classList.remove('hidden');
    document.getElementById('coverage-card').classList.remove('hidden');
    document.getElementById('matrix-card').classList.remove('hidden');

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
  selectedStyle       = null;
  selectedMatrixCombo = null;
  document.getElementById('style-detail-panel').classList.add('hidden');
  document.getElementById('matrix-detail-panel').classList.add('hidden');
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
function aggregateStyleStats(items, genderFilter = 'all') {
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
        no_data:           false,
      });
    }
    const e = map.get(key);
    if (r.is_recommended) e.recommended_count++;
    else                  e.worst_count++;
    e.total_count++;
  });

  // 매핑 데이터가 없는 스타일도 0건으로 포함
  allHairStyles.forEach((style) => {
    const gender = style.style_code?.startsWith('f-') ? '여성'
                 : style.style_code?.startsWith('m-') ? '남성'
                 : null;
    if (!gender) return;
    if (genderFilter !== 'all' && gender !== genderFilter) return;
    const key = `${gender}__${style.style_code || style.style_name}`;
    if (!map.has(key)) {
      map.set(key, {
        gender,
        style_name:        style.style_name,
        style_code:        style.style_code,
        recommended_count: 0,
        worst_count:       0,
        total_count:       0,
        no_data:           true,
      });
    }
  });

  return Array.from(map.values());
}

// ── 스타일 테이블 렌더링 ───────────────────────────────────────────────────────
function renderStyleTable() {
  const gender = getGenderFilter();
  const shape  = getFaceShapeFilter();
  const prop   = getFaceProportionFilter();

  let items = aggregateStyleStats(filterRawItems(gender, shape, prop), gender);

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
    if (row.no_data) tr.classList.add('no-data-row');

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

    const noDataBadge = row.no_data
      ? `<span style="font-size:0.68rem;color:#aeaeb2;margin-left:4px;">(매핑 없음)</span>`
      : '';

    tr.innerHTML = `
      <td><span class="gender-badge ${genderClass}">${row.gender}</span></td>
      <td>${row.style_name}${noDataBadge}</td>
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
  const genders = gender === 'all' ? EXPECTED_GENDERS : [gender];

  // 고정 기준 40조합(성별 필터 적용)에서 출발 — conditionCounts에 없으면 doc_count=0
  const expectedCombos = [];
  genders.forEach((g) => {
    EXPECTED_FACE_SHAPES.forEach((s) => {
      EXPECTED_PROPORTIONS.forEach((p) => {
        const found = conditionCounts.find(
          (c) => c.gender === g && c.face_shape === s && c.face_proportion === p
        );
        expectedCombos.push({
          gender:          g,
          face_shape:      s,
          face_proportion: p,
          doc_count:       found ? found.doc_count : 0,
        });
      });
    });
  });

  coverageData = expectedCombos.map((combo) => {
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

  document.getElementById('cov-total').textContent        = total;
  document.getElementById('cov-no-data').textContent      = noData;
  document.getElementById('cov-insufficient').textContent = insufficient;
  document.getElementById('cov-biased').textContent       = biased;

  renderCoverageTable();
  renderMissingMatrix();
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

// ── 수집 현황 매트릭스 ─────────────────────────────────────────────────────────
const MATRIX_STATUS_CLASS = {
  '없음':    'm-none',
  '매우 부족': 'm-very-poor',
  '부족':    'm-poor',
  '편향':    'm-biased',
  '보통':    'm-normal',
};

function renderMissingMatrix() {
  const wrap = document.getElementById('matrix-tables');
  if (!wrap) return;
  wrap.innerHTML = '';

  const gender  = getGenderFilter();
  const genders = gender === 'all' ? EXPECTED_GENDERS : [gender];

  genders.forEach((g) => {
    const block = document.createElement('div');
    block.className = 'matrix-block';

    // 성별 타이틀
    const titleEl = document.createElement('div');
    titleEl.className = `matrix-gender-title ${g === '남성' ? 'male' : 'female'}`;
    titleEl.textContent = g;
    block.appendChild(titleEl);

    // grid: 1 label col + 4 proportion cols
    const cols = 1 + EXPECTED_PROPORTIONS.length;
    const grid = document.createElement('div');
    grid.className = 'matrix-grid';
    grid.style.gridTemplateColumns = `80px repeat(${EXPECTED_PROPORTIONS.length}, 1fr)`;

    // 헤더 행
    const cornerCell = document.createElement('div');
    cornerCell.className = 'matrix-cell m-header';
    grid.appendChild(cornerCell);

    EXPECTED_PROPORTIONS.forEach((p) => {
      const cell = document.createElement('div');
      cell.className = 'matrix-cell m-header';
      cell.textContent = formatFaceProportion(p);
      grid.appendChild(cell);
    });

    // 데이터 행 (얼굴형별)
    EXPECTED_FACE_SHAPES.forEach((shape) => {
      const labelCell = document.createElement('div');
      labelCell.className = 'matrix-cell m-row-label';
      labelCell.textContent = shape;
      grid.appendChild(labelCell);

      EXPECTED_PROPORTIONS.forEach((prop) => {
        const combo = coverageData.find(
          (c) => c.gender === g && c.face_shape === shape && c.face_proportion === prop
        );
        const cell = document.createElement('div');
        const status = combo ? combo.status : '없음';
        const count  = combo ? combo.doc_count : 0;
        cell.className = `matrix-cell clickable ${MATRIX_STATUS_CLASS[status] || 'm-none'}`;
        cell.textContent = count;
        cell.title = `${g} / ${shape} / ${formatFaceProportion(prop)}\n상태: ${status} (${count}건)\n클릭하면 상세 보기`;

        const isSel = selectedMatrixCombo &&
          selectedMatrixCombo.gender       === g     &&
          selectedMatrixCombo.face_shape   === shape &&
          selectedMatrixCombo.face_proportion === prop;
        if (isSel) cell.classList.add('matrix-cell-selected');

        cell.addEventListener('click', () => onMatrixCellClick(g, shape, prop));
        grid.appendChild(cell);
      });
    });

    block.appendChild(grid);
    wrap.appendChild(block);
  });

  // 요약 문구
  const summaryEl = document.getElementById('matrix-summary');
  if (summaryEl) {
    const totalExpected = genders.length * EXPECTED_FACE_SHAPES.length * EXPECTED_PROPORTIONS.length;
    const missingCount  = coverageData.filter((c) => c.status === '없음').length;
    const normalCount   = coverageData.filter((c) => c.status === '보통').length;
    summaryEl.innerHTML =
      `<span style="color:#ff3b30;font-weight:700;">${missingCount}조합</span> 데이터 없음 &nbsp;/&nbsp; ` +
      `<span style="color:#34c759;font-weight:700;">${normalCount}조합</span> 보통 &nbsp;/&nbsp; ` +
      `전체 <strong>${totalExpected}조합</strong> 기준`;
  }

  // 없는 조합 목록
  const listWrap = document.getElementById('missing-list-wrap');
  const listEl   = document.getElementById('missing-list');
  if (listWrap && listEl) {
    const missingCombos = coverageData.filter((c) => c.status === '없음');
    if (missingCombos.length > 0) {
      listEl.innerHTML = '';
      missingCombos.forEach((c) => {
        const li = document.createElement('li');
        li.textContent = `${c.gender} / ${c.face_shape} / ${formatFaceProportion(c.face_proportion)}`;
        listEl.appendChild(li);
      });
      listWrap.classList.remove('hidden');
    } else {
      listWrap.classList.add('hidden');
    }
  }
}

// ── 매트릭스 셀 클릭 ──────────────────────────────────────────────────────────
function onMatrixCellClick(gender, faceShape, faceProportion) {
  const isSame = selectedMatrixCombo &&
    selectedMatrixCombo.gender          === gender      &&
    selectedMatrixCombo.face_shape      === faceShape   &&
    selectedMatrixCombo.face_proportion === faceProportion;

  if (isSame) {
    closeMatrixDetailPanel();
    return;
  }

  selectedMatrixCombo = { gender, face_shape: faceShape, face_proportion: faceProportion };
  renderMissingMatrix();
  renderMatrixDetailPanel(gender, faceShape, faceProportion);
}

function closeMatrixDetailPanel() {
  selectedMatrixCombo = null;
  document.getElementById('matrix-detail-panel').classList.add('hidden');
  renderMissingMatrix();
}

function renderMatrixDetailPanel(gender, faceShape, faceProportion) {
  const combo = coverageData.find(
    (c) => c.gender === gender && c.face_shape === faceShape && c.face_proportion === faceProportion
  );

  // rawItems에서 이 조합의 스타일별 추천/비추천 집계
  const styleMap = new Map();
  rawItems
    .filter((r) => r.gender === gender && r.face_shape === faceShape && r.face_proportion === faceProportion)
    .forEach((r) => {
      const key = r.style_code || r.style_name;
      if (!styleMap.has(key)) {
        styleMap.set(key, { style_name: r.style_name, style_code: r.style_code, rec_count: 0, worst_count: 0 });
      }
      const e = styleMap.get(key);
      if (r.is_recommended) e.rec_count++;
      else                  e.worst_count++;
    });

  const allStyles   = Array.from(styleMap.values());
  const recStyles   = allStyles.filter((s) => s.rec_count   > 0).sort((a, b) => b.rec_count   - a.rec_count);
  const worstStyles = allStyles.filter((s) => s.worst_count > 0).sort((a, b) => b.worst_count - a.worst_count);

  // 헤더
  document.getElementById('matrix-detail-title').textContent =
    `${gender} / ${faceShape} / ${formatFaceProportion(faceProportion)}`;

  const status    = combo ? combo.status   : '없음';
  const docCount  = combo ? combo.doc_count : 0;
  const statusCls = MATRIX_STATUS_CLASS[status] || 'm-none';
  document.getElementById('matrix-detail-info').innerHTML =
    `상태: <span class="matrix-cell ${statusCls}" style="display:inline-block;padding:2px 10px;border-radius:6px;">${status}</span>` +
    `&nbsp;&nbsp; 분석 문서 수: <strong>${docCount}</strong>건`;

  // 추천 테이블
  const recTbody = document.getElementById('matrix-detail-rec-tbody');
  recTbody.innerHTML = '';
  if (recStyles.length === 0) {
    recTbody.innerHTML = '<tr><td colspan="3" style="color:#aeaeb2;text-align:center;padding:12px;">데이터 없음</td></tr>';
  } else {
    recStyles.forEach((s) => {
      const tr = document.createElement('tr');
      const codeHtml = s.style_code
        ? `<span class="code-cell">${s.style_code}</span>`
        : `<span class="no-code">미등록</span>`;
      tr.innerHTML = `<td>${s.style_name}</td><td>${codeHtml}</td><td class="rec-count">${s.rec_count}</td>`;
      recTbody.appendChild(tr);
    });
  }

  // 비추천 테이블
  const worstTbody = document.getElementById('matrix-detail-worst-tbody');
  worstTbody.innerHTML = '';
  if (worstStyles.length === 0) {
    worstTbody.innerHTML = '<tr><td colspan="3" style="color:#aeaeb2;text-align:center;padding:12px;">데이터 없음</td></tr>';
  } else {
    worstStyles.forEach((s) => {
      const tr = document.createElement('tr');
      const codeHtml = s.style_code
        ? `<span class="code-cell">${s.style_code}</span>`
        : `<span class="no-code">미등록</span>`;
      tr.innerHTML = `<td>${s.style_name}</td><td>${codeHtml}</td><td class="wrst-count">${s.worst_count}</td>`;
      worstTbody.appendChild(tr);
    });
  }

  const panel = document.getElementById('matrix-detail-panel');
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── 에러 표시 ──────────────────────────────────────────────────────────────────
function showError(msg) {
  document.getElementById('loading-msg').classList.add('hidden');
  const el = document.getElementById('stats-error');
  el.textContent = `오류: ${msg}`;
  el.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', init);
