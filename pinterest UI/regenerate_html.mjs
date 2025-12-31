import fs from 'fs';

const INPUT_FILE = 'bulk_content.json';
const OUTPUT_FILE = 'bulk_content.html';

function cleanUrl(url) {
  if (!url) return '';
  try {
    const parsed = new URL(url);
    return parsed.origin + parsed.pathname;
  } catch {
    return url;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function generateHtml(pins) {
  const pinsWithContent = pins.filter(p => p.content?.pin_title);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pinterest Bulk Content - ${pinsWithContent.length} Pins</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }
    h1 { text-align: center; color: #e60023; }
    .stats {
      display: flex;
      justify-content: center;
      gap: 20px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }
    .stat {
      background: white;
      padding: 15px 25px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stat-num { font-size: 24px; font-weight: bold; color: #e60023; }
    .stat-label { font-size: 12px; color: #666; }
    .filters {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
      justify-content: center;
      flex-wrap: wrap;
    }
    .filter-btn {
      padding: 8px 16px;
      border: none;
      border-radius: 20px;
      cursor: pointer;
      background: white;
      color: #333;
      font-weight: 500;
      transition: all 0.2s;
    }
    .filter-btn:hover, .filter-btn.active { background: #e60023; color: white; }
    .pin-card {
      background: white;
      margin: 15px 0;
      padding: 20px;
      border-radius: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .pin-card.done { opacity: 0.5; }
    .pin-card.done .pin-header { text-decoration: line-through; }
    .pin-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px solid #eee;
    }
    .pin-num {
      font-weight: bold;
      color: #e60023;
      font-size: 14px;
    }
    .pin-analytics {
      display: flex;
      gap: 15px;
      font-size: 12px;
      color: #666;
    }
    .field {
      margin: 10px 0;
    }
    .field-label {
      font-size: 11px;
      text-transform: uppercase;
      color: #999;
      margin-bottom: 4px;
    }
    .field-value {
      background: #f8f8f8;
      padding: 12px;
      border-radius: 8px;
      cursor: pointer;
      border: 2px solid transparent;
      transition: all 0.2s;
      line-height: 1.5;
    }
    .field-value:hover { border-color: #e60023; }
    .field-value.copied {
      background: #d4edda;
      border-color: #28a745;
    }
    .product-link {
      color: #e60023;
      text-decoration: none;
      font-weight: 500;
      cursor: pointer;
    }
    .product-link:hover { text-decoration: underline; }
    .mark-done {
      padding: 8px 16px;
      background: #28a745;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 12px;
    }
    .mark-done:hover { background: #218838; }
    .original-title {
      font-size: 11px;
      color: #999;
      margin-top: 5px;
    }
    .hidden { display: none !important; }
  </style>
</head>
<body>
  <h1>🎯 Pinterest Bulk Content</h1>

  <div class="stats">
    <div class="stat">
      <div class="stat-num">${pinsWithContent.length}</div>
      <div class="stat-label">Total Pins</div>
    </div>
    <div class="stat">
      <div class="stat-num" id="doneCount">0</div>
      <div class="stat-label">Done</div>
    </div>
    <div class="stat">
      <div class="stat-num" id="remainingCount">${pinsWithContent.length}</div>
      <div class="stat-label">Remaining</div>
    </div>
  </div>

  <div class="filters">
    <button class="filter-btn active" onclick="filterPins('all')">All</button>
    <button class="filter-btn" onclick="filterPins('pending')">Pending</button>
    <button class="filter-btn" onclick="filterPins('done')">Done</button>
  </div>

  <div id="pinsContainer">
${pinsWithContent.map((pin, i) => {
  const c = pin.content;
  const cleanDestUrl = cleanUrl(pin.destUrl);
  return `
    <div class="pin-card" data-id="${pin.pinId}" data-status="pending">
      <div class="pin-header">
        <div>
          <span class="pin-num">#${i + 1}</span>
          <a href="${escapeHtml(pin.pinUrl)}" target="_blank" style="color:#666;font-size:12px;margin-left:10px;">Open Pin ↗</a>
        </div>
        <div style="display:flex;align-items:center;gap:15px;">
          <div class="pin-analytics">
            <span>👁 ${pin.analytics?.impressions || 0}</span>
            <span>🖱 ${pin.analytics?.clicks || 0}</span>
            <span>💾 ${pin.analytics?.saves || 0}</span>
          </div>
          <button class="mark-done" onclick="toggleDone('${pin.pinId}')">✓ Done</button>
        </div>
      </div>

      <div class="field">
        <div class="field-label">Title</div>
        <div class="field-value" onclick="copyField(this)">${escapeHtml(c.pin_title)}</div>
      </div>

      <div class="field">
        <div class="field-label">Description</div>
        <div class="field-value" onclick="copyField(this)">${escapeHtml(c.pin_description)}</div>
      </div>

      <div class="field">
        <div class="field-label">Alt Text</div>
        <div class="field-value" onclick="copyField(this)">${escapeHtml(c.alt_text)}</div>
      </div>

      <div class="field">
        <div class="field-label">Product Link (click to copy)</div>
        <span class="product-link" onclick="copyLink(this, '${escapeHtml(cleanDestUrl)}')">${escapeHtml(cleanDestUrl)}</span>
      </div>

      <div class="original-title">Original: ${escapeHtml(pin.title?.slice(0, 100))}</div>
    </div>
  `;
}).join('')}
  </div>

  <script>
    // Load saved progress
    const savedProgress = JSON.parse(localStorage.getItem('pinterestProgress') || '{}');
    Object.keys(savedProgress).forEach(id => {
      const card = document.querySelector(\`[data-id="\${id}"]\`);
      if (card && savedProgress[id] === 'done') {
        card.classList.add('done');
        card.dataset.status = 'done';
      }
    });
    updateCounts();

    function copyField(el) {
      navigator.clipboard.writeText(el.textContent);
      el.classList.add('copied');
      setTimeout(() => el.classList.remove('copied'), 1000);
    }

    function copyLink(el, url) {
      navigator.clipboard.writeText(url);
      el.style.color = '#28a745';
      setTimeout(() => el.style.color = '#e60023', 1000);
    }

    function toggleDone(id) {
      const card = document.querySelector(\`[data-id="\${id}"]\`);
      if (card.classList.contains('done')) {
        card.classList.remove('done');
        card.dataset.status = 'pending';
        delete savedProgress[id];
      } else {
        card.classList.add('done');
        card.dataset.status = 'done';
        savedProgress[id] = 'done';
      }
      localStorage.setItem('pinterestProgress', JSON.stringify(savedProgress));
      updateCounts();
    }

    function updateCounts() {
      const total = document.querySelectorAll('.pin-card').length;
      const done = document.querySelectorAll('.pin-card.done').length;
      document.getElementById('doneCount').textContent = done;
      document.getElementById('remainingCount').textContent = total - done;
    }

    function filterPins(filter) {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');

      document.querySelectorAll('.pin-card').forEach(card => {
        if (filter === 'all') {
          card.classList.remove('hidden');
        } else if (filter === 'done') {
          card.classList.toggle('hidden', !card.classList.contains('done'));
        } else {
          card.classList.toggle('hidden', card.classList.contains('done'));
        }
      });
    }
  </script>
</body>
</html>`;
}

// Main
const pins = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));
const html = generateHtml(pins);
fs.writeFileSync(OUTPUT_FILE, html);

const count = pins.filter(p => p.content?.pin_title).length;
console.log(\`✅ Generated \${OUTPUT_FILE} with \${count} pins\`);
