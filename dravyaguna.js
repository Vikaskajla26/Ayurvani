// ========== DRAVYA GUNA - All functions in global scope ==========

// Variables
var dgData = [];
var dgLoaded = false;

// Load plant data
async function dgLoadData() {
  if (dgLoaded) return;
  try {
    var resp = await fetch('/dravyaguna_data.json');
    dgData = await resp.json();
    dgLoaded = true;
    var el = document.getElementById('dravyaCount');
    if (el) el.textContent = dgData.length + ' plants';
  } catch(e) {
    console.error('DG load error:', e);
  }
}

// Render plant grid
function dgRender() {
  var grid = document.getElementById('dravyagunaGrid');
  var searchInput = document.getElementById('dravyagunaSearchInput');
  if (!grid || !dgData.length) return;

  var q = (searchInput && searchInput.value || '').trim().toLowerCase();
  var filtered = q ? dgData.filter(function(p) {
    return (p.name || '').toLowerCase().indexOf(q) !== -1 ||
           (p.sanskrit_name || '').toLowerCase().indexOf(q) !== -1 ||
           (p.botanical_name || '').toLowerCase().indexOf(q) !== -1;
  }) : dgData;

  if (!filtered.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--sage);">No plants found</div>';
    return;
  }

  var html = '';
  for (var i = 0; i < filtered.length; i++) {
    var p = filtered[i];
    var safeId = p.id.replace(/'/g, "\\'");
    html += '<div class="dravya-card" onclick="dgShowDetail(\'' + safeId + '\')" style="cursor:pointer;">' +
      '<div class="dravya-card-content" style="padding:16px;text-align:center;display:flex;flex-direction:column;justify-content:center;height:100%;">' +
      '<h3 style="margin:0 0 4px;color:var(--gold-light);font-family:\'Cormorant Garamond\',serif;">' + (p.name || '') + '</h3>' +
      '<p style="margin:0 0 2px;font-size:0.9rem;color:var(--cream);font-family:\'Tiro Devanagari Hindi\',sans-serif;">' + (p.sanskrit_name || '') + '</p>' +
      '<p style="margin:0;font-size:0.75rem;color:var(--sage);font-style:italic;">' + (p.botanical_name || '') + '</p>' +
      '</div></div>';
  }
  grid.innerHTML = html;
}

// Build detail HTML for a plant
function dgBuildDetailHtml(plant) {
  function sec(title, content) {
    return content ? '<section class="dravya-section"><h2>' + title + '</h2>' + content + '</section>' : '';
  }
  function mkUl(arr) {
    if (!arr || !arr.length) return '';
    var h = '<ul class="dravya-list">';
    for (var i = 0; i < arr.length; i++) h += '<li>' + arr[i] + '</li>';
    return h + '</ul>';
  }

  var h = '';
  h += '<div class="dravya-detail-container">';
  h += '<button class="dravya-back-btn" onclick="dgHideDetail()">&larr; Back to Plants</button>';
  h += '<div class="dravya-detail-header">';
  h += '<div class="dravya-detail-title">';
  h += '<h1>' + (plant.name || '') + '</h1>';
  h += '<p class="dravya-detail-sanskrit">' + (plant.sanskrit_name || '') + '</p>';
  h += '<p class="dravya-detail-botanical">' + (plant.botanical_name || '') + '</p>';
  if (plant.family) h += '<p class="dravya-detail-family">Family: ' + plant.family + '</p>';
  h += '</div></div>';
  h += '<div class="dravya-detail-content">';

  // श्लोक
  if (plant.sloka) {
    var sl = '<p class="dravya-sloka">' + plant.sloka + '</p>';
    if (plant.sloka_source) sl += '<p class="dravya-sloka-source">&mdash; ' + plant.sloka_source + '</p>';
    h += sec('श्लोक (Traditional Verse)', sl);
  }

  // Synonyms
  if (plant.synonyms && plant.synonyms.length) {
    var syn = '<div class="dravya-synonyms">';
    for (var si = 0; si < plant.synonyms.length; si++) {
      syn += '<div class="dravya-synonym-item"><strong>' + plant.synonyms[si].term + '</strong>';
      if (plant.synonyms[si].meaning) syn += ' &mdash; ' + plant.synonyms[si].meaning;
      syn += '</div>';
    }
    syn += '</div>';
    h += sec('Synonyms', syn);
  }

  // Vernacular Names
  if (plant.vernacular_names && plant.vernacular_names.length) {
    var vn = '<div class="dravya-vernacular">';
    for (var vi = 0; vi < plant.vernacular_names.length; vi++) {
      vn += '<div class="dravya-vernacular-item"><strong>' + plant.vernacular_names[vi].lang + ':</strong> ' + plant.vernacular_names[vi].name + '</div>';
    }
    vn += '</div>';
    h += sec('Vernacular Names', vn);
  }

  // Classification
  h += sec('Classification of Gana', mkUl(plant.classification_of_gana));

  // Morphology
  if (plant.external_morphology) {
    var morph = '';
    if (plant.external_morphology.habitat) morph += '<p><strong>Habitat:</strong> ' + plant.external_morphology.habitat + '</p>';
    morph += mkUl(plant.external_morphology.details);
    h += sec('External Morphology', morph);
  }

  // Useful Parts
  h += sec('Useful Parts', plant.useful_parts ? '<p>' + plant.useful_parts + '</p>' : '');

  // Phytoconstituents
  h += sec('Important Phytoconstituents', plant.phytoconstituents ? '<p>' + plant.phytoconstituents + '</p>' : '');

  // Rasa Panchaka
  if (plant.rasa_panchaka) {
    var rp = plant.rasa_panchaka;
    var rphtml = '<div class="dravya-rasa-panchaka">';
    if (rp.rasa) rphtml += '<div class="dravya-property"><strong>Rasa (Taste):</strong> ' + rp.rasa + '</div>';
    if (rp.guna) rphtml += '<div class="dravya-property"><strong>Guna (Qualities):</strong> ' + rp.guna + '</div>';
    if (rp.virya) rphtml += '<div class="dravya-property"><strong>Virya (Potency):</strong> ' + rp.virya + '</div>';
    if (rp.vipaka) rphtml += '<div class="dravya-property"><strong>Vipaka (Post-digestive):</strong> ' + rp.vipaka + '</div>';
    rphtml += '</div>';
    h += sec('Rasa Panchaka (Properties)', rphtml);
  }

  // Karma
  if (plant.karma) {
    var km = '';
    if (plant.karma.dosha_karma) km += '<p><strong>Dosha Karma:</strong> ' + plant.karma.dosha_karma + '</p>';
    var kv = plant.karma.karma || plant.karma.general || '';
    if (kv) km += '<p><strong>Karma:</strong> ' + kv + '</p>';
    h += sec('Karma (Actions)', km);
  }

  // Doshaghnata
  h += sec('Doshaghnata (Dosha Effect)', plant.doshaghnata ? '<p>' + plant.doshaghnata + '</p>' : '');

  // Rogaghnata
  h += sec('Rogaghnata (Therapeutic Uses)', plant.rogaghnata ? '<p>' + plant.rogaghnata + '</p>' : '');

  // Amayika Prayoga
  h += sec('Amayika Prayoga (Clinical Applications)', mkUl(plant.amayika_prayoga));

  // Matra
  if (plant.matra && plant.matra.length) {
    var mt = '<div class="dravya-matra">';
    for (var mi = 0; mi < plant.matra.length; mi++) {
      mt += '<div class="dravya-matra-item"><strong>' + plant.matra[mi].form + ':</strong> ' + plant.matra[mi].dose + '</div>';
    }
    mt += '</div>';
    h += sec('Matra (Dosage)', mt);
  }

  // Marga
  h += sec('Marga (Route of Administration)', plant.marga ? '<p>' + plant.marga + '</p>' : '');

  // Pharmacological Actions
  if (plant.pharmacological_actions && plant.pharmacological_actions.length) {
    var pa = '<div class="dravya-actions">';
    for (var ai = 0; ai < plant.pharmacological_actions.length; ai++) {
      pa += '<span class="dravya-action-badge">' + plant.pharmacological_actions[ai] + '</span>';
    }
    pa += '</div>';
    h += sec('Pharmacological Actions', pa);
  }

  // Kalpana
  h += sec('Kalpana (Formulations)', mkUl(plant.kalpana));

  // Varieties
  h += sec('Varieties', plant.varieties ? '<p>' + (typeof plant.varieties === 'string' ? plant.varieties : plant.varieties.join(', ')) + '</p>' : '');

  // Research Updates
  h += sec('Research Updates', mkUl(plant.research_updates));

  h += '</div></div></div>';
  return h;
}

// Show plant detail
function dgShowDetail(id) {
  var plant = null;
  for (var i = 0; i < dgData.length; i++) {
    if (dgData[i].id === id) { plant = dgData[i]; break; }
  }
  if (!plant) return;

  var detailView = document.getElementById('dravyagunaDetailView');
  var listView = document.getElementById('dravyagunaListView');
  var contentDiv = document.getElementById('dravyagunaDetailContent');
  if (!detailView || !contentDiv) return;

  contentDiv.innerHTML = dgBuildDetailHtml(plant);
  listView.style.display = 'none';
  detailView.style.display = 'block';
}

// Hide detail view
function dgHideDetail() {
  document.getElementById('dravyagunaDetailView').style.display = 'none';
  document.getElementById('dravyagunaListView').style.display = 'block';
}

// Initialize
async function dgInit() {
  await dgLoadData();
  var countEl = document.getElementById('dravyaCount');
  if (countEl && dgData.length) countEl.textContent = dgData.length + ' plants';
  dgRender();

  // Wire up search
  var searchInput = document.getElementById('dravyagunaSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', function() { dgRender(); });
  }

  // Wire up wrappers
  window.renderDravyagunaList = function(q) { dgRender(); };
  window.showDravyagunaDetail = function(id) { dgShowDetail(id); };
  window.hideDravyagunaDetail = function() { dgHideDetail(); };
  window.dgShowDetail = dgShowDetail;
  window.dgHideDetail = dgHideDetail;
}

// Auto-init if grid is already on page
(function() {
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(dgInit, 100);
  } else {
    document.addEventListener('DOMContentLoaded', function() { setTimeout(dgInit, 100); });
  }
})();
