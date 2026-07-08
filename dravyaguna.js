// ========== DRAVYA GUNA - Sidebar Module ==========

// Variables
let dgData = [];
let dgLoaded = false;

// Load plant data
async function dgLoadData() {
  if (dgLoaded) return;
  try {
    const resp = await fetch('/dravyaguna_data.json');
    dgData = await resp.json();
    dgLoaded = true;
    const el = document.getElementById('dravyaCount');
    if (el) el.textContent = dgData.length + ' plants';
  } catch(e) {
    console.error('DG load error:', e);
  }
}

// Render plant grid
function dgRender() {
  const grid = document.getElementById('dravyagunaGrid');
  const searchInput = document.getElementById('dravyagunaSearchInput');
  if (!grid || !dgData.length) return;

  const q = (searchInput?.value || '').trim().toLowerCase();
  const filtered = q ? dgData.filter(p =>
    (p.name || '').toLowerCase().includes(q) ||
    (p.sanskrit_name || '').toLowerCase().includes(q) ||
    (p.botanical_name || '').toLowerCase().includes(q)
  ) : dgData;

  if (!filtered.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--sage);">No plants found</div>';
    return;
  }

  grid.innerHTML = filtered.map(p => {
    const safeId = p.id.replace(/'/g, "\\'");
    return '<div class="dravya-card" onclick="dgShowDetail(\'' + safeId + '\')" style="cursor:pointer;">' +
      '<div class="dravya-card-content" style="padding:16px;text-align:center;display:flex;flex-direction:column;justify-content:center;height:100%;">' +
      '<h3 style="margin:0 0 4px;color:var(--gold-light);font-family:\'Cormorant Garamond\',serif;">' + (p.name || '') + '</h3>' +
      '<p style="margin:0 0 2px;font-size:0.9rem;color:var(--cream);font-family:\'Tiro Devanagari Hindi\',sans-serif;">' + (p.sanskrit_name || '') + '</p>' +
      '<p style="margin:0;font-size:0.75rem;color:var(--sage);font-style:italic;">' + (p.botanical_name || '') + '</p>' +
      '</div></div>';
  }).join('');
}

// Show plant detail with ALL notes
window.dgShowDetail = function(id) {
  const plant = dgData.find(p => p.id === id);
  if (!plant) return;

  const detailView = document.getElementById('dravyagunaDetailView');
  const listView = document.getElementById('dravyagunaListView');
  const contentDiv = document.getElementById('dravyagunaDetailContent');
  if (!detailView || !contentDiv) return;

  // Helper: section with title
  function sec(title, content) {
    if (!content) return '';
    return '<section class="dravya-section">' +
      '<h2>' + title + '</h2>' +
      content +
      '</section>';
  }

  // Helper: unordered list
  function mkUl(arr) {
    if (!arr || !arr.length) return '';
    return '<ul class="dravya-list">' + arr.map(function(x) { return '<li>' + x + '</li>'; }).join('') + '</ul>';
  }

  var html = '<div class="dravya-detail-container">' +
    '<button class="dravya-back-btn" onclick="dgHideDetail()">&larr; Back to Plants</button>' +
    '<div class="dravya-detail-header">' +
    '<div class="dravya-detail-title">' +
    '<h1>' + (plant.name || '') + '</h1>' +
    '<p class="dravya-detail-sanskrit">' + (plant.sanskrit_name || '') + '</p>' +
    '<p class="dravya-detail-botanical">' + (plant.botanical_name || '') + '</p>' +
    (plant.family ? '<p class="dravya-detail-family">Family: ' + plant.family + '</p>' : '') +
    '</div></div>' +
    '<div class="dravya-detail-content">';

  // श्लोक
  if (plant.sloka) {
    html += sec('श्लोक (Traditional Verse)',
      '<p class="dravya-sloka">' + plant.sloka + '</p>' +
      (plant.sloka_source ? '<p class="dravya-sloka-source">&mdash; ' + plant.sloka_source + '</p>' : ''));
  }

  // Synonyms
  if (plant.synonyms && plant.synonyms.length) {
    var synHtml = '<div class="dravya-synonyms">';
    for (var si = 0; si < plant.synonyms.length; si++) {
      var s = plant.synonyms[si];
      synHtml += '<div class="dravya-synonym-item"><strong>' + s.term + '</strong>' +
        (s.meaning ? ' &mdash; ' + s.meaning : '') + '</div>';
    }
    synHtml += '</div>';
    html += sec('Synonyms', synHtml);
  }

  // Vernacular Names
  if (plant.vernacular_names && plant.vernacular_names.length) {
    var vnHtml = '<div class="dravya-vernacular">';
    for (var vi = 0; vi < plant.vernacular_names.length; vi++) {
      var v = plant.vernacular_names[vi];
      vnHtml += '<div class="dravya-vernacular-item"><strong>' + v.lang + ':</strong> ' + v.name + '</div>';
    }
    vnHtml += '</div>';
    html += sec('Vernacular Names', vnHtml);
  }

  // Classification
  html += sec('Classification of Gana', mkUl(plant.classification_of_gana));

  // Morphology
  if (plant.external_morphology) {
    var morphHtml = '';
    if (plant.external_morphology.habitat) {
      morphHtml += '<p><strong>Habitat:</strong> ' + plant.external_morphology.habitat + '</p>';
    }
    morphHtml += mkUl(plant.external_morphology.details);
    html += sec('External Morphology', morphHtml);
  }

  // Useful Parts
  html += sec('Useful Parts', plant.useful_parts ? '<p>' + plant.useful_parts + '</p>' : '');

  // Phytoconstituents
  html += sec('Important Phytoconstituents', plant.phytoconstituents ? '<p>' + plant.phytoconstituents + '</p>' : '');

  // Rasa Panchaka
  if (plant.rasa_panchaka) {
    var rp = plant.rasa_panchaka;
    var rpHtml = '<div class="dravya-rasa-panchaka">';
    if (rp.rasa) rpHtml += '<div class="dravya-property"><strong>Rasa (Taste):</strong> ' + rp.rasa + '</div>';
    if (rp.guna) rpHtml += '<div class="dravya-property"><strong>Guna (Qualities):</strong> ' + rp.guna + '</div>';
    if (rp.virya) rpHtml += '<div class="dravya-property"><strong>Virya (Potency):</strong> ' + rp.virya + '</div>';
    if (rp.vipaka) rpHtml += '<div class="dravya-property"><strong>Vipaka (Post-digestive):</strong> ' + rp.vipaka + '</div>';
    rpHtml += '</div>';
    html += sec('Rasa Panchaka (Properties)', rpHtml);
  }

  // Karma
  if (plant.karma) {
    var kmHtml = '';
    if (plant.karma.dosha_karma) kmHtml += '<p><strong>Dosha Karma:</strong> ' + plant.karma.dosha_karma + '</p>';
    var kVal = plant.karma.karma || plant.karma.general || '';
    if (kVal) kmHtml += '<p><strong>Karma:</strong> ' + kVal + '</p>';
    html += sec('Karma (Actions)', kmHtml);
  }

  // Doshaghnata
  html += sec('Doshaghnata (Dosha Effect)', plant.doshaghnata ? '<p>' + plant.doshaghnata + '</p>' : '');

  // Rogaghnata
  html += sec('Rogaghnata (Therapeutic Uses)', plant.rogaghnata ? '<p>' + plant.rogaghnata + '</p>' : '');

  // Amayika Prayoga
  html += sec('Amayika Prayoga (Clinical Applications)', mkUl(plant.amayika_prayoga));

  // Matra
  if (plant.matra && plant.matra.length) {
    var mtHtml = '<div class="dravya-matra">';
    for (var mi = 0; mi < plant.matra.length; mi++) {
      mtHtml += '<div class="dravya-matra-item"><strong>' + plant.matra[mi].form + ':</strong> ' + plant.matra[mi].dose + '</div>';
    }
    mtHtml += '</div>';
    html += sec('Matra (Dosage)', mtHtml);
  }

  // Marga
  html += sec('Marga (Route of Administration)', plant.marga ? '<p>' + plant.marga + '</p>' : '');

  // Pharmacological Actions
  if (plant.pharmacological_actions && plant.pharmacological_actions.length) {
    var phHtml = '<div class="dravya-actions">';
    for (var ai = 0; ai < plant.pharmacological_actions.length; ai++) {
      phHtml += '<span class="dravya-action-badge">' + plant.pharmacological_actions[ai] + '</span>';
    }
    phHtml += '</div>';
    html += sec('Pharmacological Actions', phHtml);
  }

  // Kalpana
  html += sec('Kalpana (Formulations)', mkUl(plant.kalpana));

  // Varieties
  html += sec('Varieties', plant.varieties ? '<p>' + (typeof plant.varieties === 'string' ? plant.varieties : plant.varieties.join(', ')) + '</p>' : '');

  // Research Updates
  html += sec('Research Updates', mkUl(plant.research_updates));

  html += '</div></div></div>';

  contentDiv.innerHTML = html;
  listView.style.display = 'none';
  detailView.style.display = 'block';
};

// Hide detail view
window.dgHideDetail = function() {
  document.getElementById('dravyagunaDetailView').style.display = 'none';
  document.getElementById('dravyagunaListView').style.display = 'block';
};

// Initialize everything
async function dgInit() {
  await dgLoadData();
  const countEl = document.getElementById('dravyaCount');
  if (countEl && dgData.length) countEl.textContent = dgData.length + ' plants';
  dgRender();

  // Wire up search
  var searchInput = document.getElementById('dravyagunaSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', dgRender);
  }

  // Also wire up inline callbacks from search
  var oldRender = window.renderDravyagunaList;
  window.renderDravyagunaList = function(q) { dgRender(); };
  window.showDravyagunaDetail = function(id) { dgShowDetail(id); };
  window.hideDravyagunaDetail = function() { dgHideDetail(); };
}

// Hook into showView
(function() {
  var origShowView = window.showView;
  if (typeof origShowView === 'function') {
    window.showView = function(id) {
      origShowView(id);
      if (id === 'dravyaguna') {
        setTimeout(dgInit, 50);
      }
    };
  }

  // If document is ready, also run init directly to ensure data loads
  function tryInit() {
    if (document.getElementById('dravyagunaGrid')) {
      dgInit();
    }
  }

  if (document.readyState === 'complete') {
    tryInit();
  } else {
    window.addEventListener('load', tryInit);
  }
})();
