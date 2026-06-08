'use strict';

// ── 상태 ─────────────────────────────────────────────────────────────────────
let allItems = [];
let sortCol = 'recommended_count';
let sortDir = 'desc';

// ── 초기화 ───────────────────────────────────────────────────────────────────
async function init() {
  await loadStats();

  document.getElementById('gender-filter').addEventListener('change', renderTable);

  // 컬럼 헤더 정렬
  document.querySelectorAll('#stats-table thead th').forEach((th) => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (!col) return;
      if (sortCol === col) {
        sortDir = sortDir === 'desc' ? 'asc' : 'desc';
      } else {
        sortCol = col;
        sortDir = col === 'recommended_count' || col === 'worst_count' || col === 'total_count'
          ? 'desc' : 'asc';
      }
      renderTable();
    });
  });
}

// ── 데이터 로드 ───────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch('/api/hair-style-stats');
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || `서버 오류 (HTTP ${res.status})`);
      return;
    }

    allItems = data.items || [];
    document.getElementById('sum-rows').textContent = (data.summary?.total_rows ?? '-').toLocaleString();
    document.getElementById('sum-styles').textContent = (data.summary?.total_styles ?? '-').toLocaleString();

    document.getElementById('loading-msg').classList.add('hidden');
    document.getElementById('table-wrap').classList.remove('hidden');

    renderTable();
  } catch (e) {
    showError(`네트워크 오류: ${e.message}`);
  }
}

// ── 테이블 렌더링 ─────────────────────────────────────────────────────────────
function renderTable() {
  const filter = document.getElementById('gender-filter').value;
  let items = filter === 'all' ? allItems : allItems.filter((r) => r.gender === filter);

  // 정렬
  items = [...items].sort((a, b) => {
    let va = a[sortCol] ?? '';
    let vb = b[sortCol] ?? '';
    if (typeof va === 'number' && typeof vb === 'number') {
      return sortDir === 'desc' ? vb - va : va - vb;
    }
    va = String(va);
    vb = String(vb);
    return sortDir === 'desc' ? vb.localeCompare(va, 'ko') : va.localeCompare(vb, 'ko');
  });

  // 최대값 (막대그래프 비율 계산용)
  const maxRec  = Math.max(1, ...items.map((r) => r.recommended_count));
  const maxWrst = Math.max(1, ...items.map((r) => r.worst_count));

  // 헤더 정렬 표시
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

    const genderClass = row.gender === '남성' ? 'male' : 'female';
    const codeHtml = row.style_code
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
    tbody.appendChild(tr);
  });
}

// ── 에러 표시 ─────────────────────────────────────────────────────────────────
function showError(msg) {
  document.getElementById('loading-msg').classList.add('hidden');
  const el = document.getElementById('stats-error');
  el.textContent = `오류: ${msg}`;
  el.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', init);
