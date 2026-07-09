// ========== DRAVYA GUNA - Smart Filters + Images + Detail View ==========

var dgData = [];
var dgLoaded = false;
var dgActiveFilters = { dosha: {}, rasa: {}, virya: {}, family: {} };

// ---- Helpers ----
function dgExtractDosha(p) {
  var d = (p.doshaghnata || '').toLowerCase();
  if (d.indexOf('त्रिदोष') !== -1 || d.indexOf('tridosha') !== -1 || d.indexOf('tridos') !== -1) return ['Vata','Pitta','Kapha'];
  var r = [];
  if (d.indexOf('वात') !== -1 || d.indexOf('vata') !== -1) r.push('Vata');
  if (d.indexOf('पित्त') !== -1 || d.indexOf('pitta') !== -1) r.push('Pitta');
  if (d.indexOf('कफ') !== -1 || d.indexOf('kapha') !== -1 || d.indexOf('shlesh') !== -1) r.push('Kapha');
  var k = (p.karma && p.karma.dosha_karma || '').toLowerCase();
  if (k.indexOf('त्रिदोष') !== -1 || k.indexOf('tridosha') !== -1 || k.indexOf('tridos') !== -1) {
    if (r.indexOf('Vata')===-1) r.push('Vata');
    if (r.indexOf('Pitta')===-1) r.push('Pitta');
    if (r.indexOf('Kapha')===-1) r.push('Kapha');
  }
  if (k.indexOf('vata') !== -1 && r.indexOf('Vata')===-1) r.push('Vata');
  if (k.indexOf('pitta') !== -1 && r.indexOf('Pitta')===-1) r.push('Pitta');
  if (k.indexOf('kapha') !== -1 && r.indexOf('Kapha')===-1) r.push('Kapha');
  return r.length ? r : [];
}

function dgExtractRasa(p) {
  var rp = p.rasa_panchaka || {};
  var r = (rp.rasa || '').toLowerCase();
  var result = [];
  if (r.indexOf('katu') !== -1 || r.indexOf('कटु') !== -1) result.push('Katu');
  if (r.indexOf('tikta') !== -1 || r.indexOf('तिक्त') !== -1) result.push('Tikta');
  if (r.indexOf('kashaya') !== -1 || r.indexOf('कषाय') !== -1) result.push('Kashaya');
  if (r.indexOf('madhura') !== -1 || r.indexOf('मधुर') !== -1 || r.indexOf('madhu') !== -1) result.push('Madhura');
  if (r.indexOf('amla') !== -1 || r.indexOf('आम्ल') !== -1) result.push('Amla');
  if (r.indexOf('lavana') !== -1 || r.indexOf('लवण') !== -1) result.push('Lavana');
  if (r.indexOf('पंचरस') !== -1) { result=['Katu','Tikta','Kashaya','Madhura','Amla']; }
  return result;
}

function dgExtractVirya(p) {
  var v = ((p.rasa_panchaka || {}).virya || '').toLowerCase();
  if (v.indexOf('ushna') !== -1 || v.indexOf('उष्ण') !== -1) return 'Ushna';
  if (v.indexOf('sheeta') !== -1 || v.indexOf('शीत') !== -1 || v.indexOf('shita') !== -1) return 'Sheeta';
  return '';
}

function dgExtractFamily(p) {
  return (p.family || '').trim() || 'Unknown';
}

// ---- Load ----
async function dgLoadData() {
  if (dgLoaded) return;
  try {
    var resp = await fetch('/dravyaguna_data.json');
    dgData = await resp.json();
    dgLoaded = true;
    var el = document.getElementById('dravyaCount');
    if (el) el.textContent = dgData.length + ' plants';
  } catch(e) { console.error('DG load error:', e); }
}

// ---- Filters ----
function dgBuildFilters() {
  var container = document.getElementById('dravyagunaFiltersContainer');
  if (!container) return;

  // Collect all unique values
  var doshas = {}; var rasas = {}; var viryas = {}; var families = {};
  for (var i = 0; i < dgData.length; i++) {
    var p = dgData[i];
    dgExtractDosha(p).forEach(function(d) { doshas[d] = (doshas[d]||0)+1; });
    dgExtractRasa(p).forEach(function(r) { rasas[r] = (rasas[r]||0)+1; });
    var v = dgExtractVirya(p);
    if (v) viryas[v] = (viryas[v]||0)+1;
    var f = dgExtractFamily(p);
    families[f] = (families[f]||0)+1;
  }

  var doshaSorted = ['Vata','Pitta','Kapha'];
  var rasaSorted = ['Madhura','Amla','Lavana','Katu','Tikta','Kashaya'];
  var viryaSorted = ['Ushna','Sheeta'];
  var familySorted = Object.keys(families).sort(function(a,b) { return families[b]-families[a]; }).slice(0,12);

  var html = '<div class="dravya-filters-container">';
  html += '<div class="dravya-filters-header"><h3>🔬 Advanced Filters</h3><button class="dravya-clear-filters-btn" onclick="dgClearFilters()">Clear All</button></div>';
  html += '<div class="dravya-filters-grid">';

  // Dosha filter
  html += '<div class="dravya-filter-group"><h4>Dosha</h4><div class="dravya-filter-options">';
  doshaSorted.forEach(function(d) {
    var count = doshas[d] || 0;
    if (!count) return;
    var checked = dgActiveFilters.dosha[d] ? 'checked' : '';
    html += '<label class="dravya-filter-label"><input type="checkbox" data-filter-type="dosha" data-filter-value="' + d + '" ' + checked + ' onchange="dgToggleFilter(\'dosha\',\'' + d + '\')"><span>' + d + ' (' + count + ')</span></label>';
  });
  html += '</div></div>';

  // Rasa filter
  html += '<div class="dravya-filter-group"><h4>Rasa (Taste)</h4><div class="dravya-filter-options">';
  rasaSorted.forEach(function(r) {
    var count = rasas[r] || 0;
    if (!count) return;
    var checked = dgActiveFilters.rasa[r] ? 'checked' : '';
    html += '<label class="dravya-filter-label"><input type="checkbox" data-filter-type="rasa" data-filter-value="' + r + '" ' + checked + ' onchange="dgToggleFilter(\'rasa\',\'' + r + '\')"><span>' + r + ' (' + count + ')</span></label>';
  });
  html += '</div></div>';

  // Virya filter
  html += '<div class="dravya-filter-group"><h4>Virya (Potency)</h4><div class="dravya-filter-options">';
  viryaSorted.forEach(function(v) {
    var count = viryas[v] || 0;
    if (!count) return;
    var checked = dgActiveFilters.virya[v] ? 'checked' : '';
    html += '<label class="dravya-filter-label"><input type="checkbox" data-filter-type="virya" data-filter-value="' + v + '" ' + checked + ' onchange="dgToggleFilter(\'virya\',\'' + v + '\')"><span>' + v + ' (' + count + ')</span></label>';
  });
  html += '</div></div>';

  // Family filter
  html += '<div class="dravya-filter-group"><h4>Family</h4><div class="dravya-filter-options">';
  familySorted.forEach(function(f) {
    var count = families[f] || 0;
    if (!count) return;
    var checked = dgActiveFilters.family[f] ? 'checked' : '';
    html += '<label class="dravya-filter-label"><input type="checkbox" data-filter-type="family" data-filter-value="' + f.replace(/'/g,"&#39;") + '" ' + checked + ' onchange="dgToggleFilter(\'family\',\'' + f.replace(/'/g,"\\'") + '\')"><span>' + f + ' (' + count + ')</span></label>';
  });
  html += '</div></div>';

  html += '</div></div>';

  container.innerHTML = html;
}

function dgToggleFilter(type, value) {
  if (dgActiveFilters[type][value]) {
    delete dgActiveFilters[type][value];
  } else {
    dgActiveFilters[type][value] = true;
  }
  dgRender();
}

function dgClearFilters() {
  dgActiveFilters = { dosha: {}, rasa: {}, virya: {}, family: {} };
  // Update checkboxes
  var checks = document.querySelectorAll('#dravyagunaFiltersContainer input[type="checkbox"]');
  for (var i = 0; i < checks.length; i++) { checks[i].checked = false; }
  dgRender();
}

function dgFilterMatches(p) {
  // If no active filters, everything matches
  var hasActive = false;
  for (var t in dgActiveFilters) { for (var k in dgActiveFilters[t]) { hasActive = true; break; } if (hasActive) break; }
  if (!hasActive) return true;

  // Dosha
  var doshaKeys = Object.keys(dgActiveFilters.dosha);
  if (doshaKeys.length) {
    var pDosha = dgExtractDosha(p);
    var match = false;
    for (var di = 0; di < pDosha.length; di++) { if (doshaKeys.indexOf(pDosha[di]) !== -1) { match = true; break; } }
    if (!match) return false;
  }

  // Rasa
  var rasaKeys = Object.keys(dgActiveFilters.rasa);
  if (rasaKeys.length) {
    var pRasa = dgExtractRasa(p);
    var match = false;
    for (var ri = 0; ri < pRasa.length; ri++) { if (rasaKeys.indexOf(pRasa[ri]) !== -1) { match = true; break; } }
    if (!match) return false;
  }

  // Virya
  var viryaKeys = Object.keys(dgActiveFilters.virya);
  if (viryaKeys.length) {
    var pVirya = dgExtractVirya(p);
    if (viryaKeys.indexOf(pVirya) === -1) return false;
  }

  // Family
  var familyKeys = Object.keys(dgActiveFilters.family);
  if (familyKeys.length) {
    var pFamily = dgExtractFamily(p);
    if (familyKeys.indexOf(pFamily) === -1) return false;
  }

  return true;
}

// ---- Render ----
function dgRender() {
  var grid = document.getElementById('dravyagunaGrid');
  var searchInput = document.getElementById('dravyagunaSearchInput');
  var resultsInfo = document.getElementById('dravyagunaResultsInfo');
  if (!grid || !dgData.length) return;

  var q = (searchInput && searchInput.value || '').trim().toLowerCase();

  var filtered = dgData.filter(function(p) {
    // Search filter
    if (q) {
      var inName = (p.name || '').toLowerCase().indexOf(q) !== -1;
      var inSans = (p.sanskrit_name || '').toLowerCase().indexOf(q) !== -1;
      var inBot = (p.botanical_name || '').toLowerCase().indexOf(q) !== -1;
      if (!inName && !inSans && !inBot) return false;
    }
    // Advanced filters
    return dgFilterMatches(p);
  });

  // Results info
  if (resultsInfo) {
    var totalText = 'Showing ' + filtered.length + ' of ' + dgData.length + ' plants';
    resultsInfo.innerHTML = '<div class="dravya-results-info"><span class="dravya-results-info-left"><span class="dravya-results-count">' + filtered.length + '</span> / ' + dgData.length + ' plants</span></div>';
  }

  if (!filtered.length) {
    grid.innerHTML = '<div class="dravya-results-empty"><div class="dravya-results-empty-icon">🔍</div><div class="dravya-results-empty-text">No plants match your filters</div><div class="dravya-results-empty-suggestion">Try adjusting your search or clearing filters</div></div>';
    return;
  }

  var html = '';
  for (var i = 0; i < filtered.length; i++) {
    var p = filtered[i];
    var safeId = p.id.replace(/'/g, "\\'");
    var thumb = p.plantPhotoUrl || '';
    var thumbStyle = thumb ? 'background-image:url(' + thumb + ');background-size:cover;background-position:center;min-height:120px;' : 'min-height:80px;';

    html += '<div class="dravya-card" onclick="dgShowDetail(\'' + safeId + '\')" style="cursor:pointer;">';
    // Thumbnail
    if (thumb) {
      html += '<div class="dravya-card-thumb" style="' + thumbStyle + 'border-radius:8px 8px 0 0;position:relative;overflow:hidden;"></div>';
    }
    html += '<div class="dravya-card-content" style="padding:12px 16px;text-align:center;">';
    html += '<h3 style="margin:0 0 4px;color:var(--gold-light);font-family:\'Cormorant Garamond\',serif;">' + (p.name || '') + '</h3>';
    html += '<p style="margin:0 0 2px;font-size:0.9rem;color:var(--cream);font-family:\'Tiro Devanagari Hindi\',sans-serif;">' + (p.sanskrit_name || '') + '</p>';
    html += '<p style="margin:0;font-size:0.75rem;color:var(--sage);font-style:italic;">' + (p.botanical_name || '') + '</p>';
    html += '</div></div>';
  }
  grid.innerHTML = html;
}

// ---- Detail View ----
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

  // ---- Image Gallery ----
  var galHtml = '<div class="dravya-image-gallery"><div class="dravya-gallery-tabs">';
  var plantImg = plant.plantPhotoUrl || '';
  var usefulImg = plant.usefulPartPhotoUrl || '';
  if (plantImg) galHtml += '<button class="dravya-tab-btn active" onclick="dgSwitchTab(\'plantTab\',event)">🌿 Plant</button>';
  if (usefulImg) galHtml += '<button class="dravya-tab-btn" onclick="dgSwitchTab(\'usefulTab\',event)">🔬 ' + (plant.usefulPart || 'Useful Part') + '</button>';
  galHtml += '</div><div class="dravya-gallery-content">';
  if (plantImg) {
    galHtml += '<div id="dgPlantTab" class="dravya-image-tab active">';
    galHtml += '<div class="dravya-image-container" onclick="dgOpenLightbox(\'' + plantImg + '\')">';
    galHtml += '<img class="dravya-detail-image" src="' + plantImg + '" alt="' + plant.name + '" loading="lazy" onerror="this.parentElement.innerHTML=\'<p style=padding:40px;color:var(--sage)>Image unavailable</p>\'">';
    galHtml += '<span class="dravya-zoom-indicator">🔍 Click to enlarge</span>';
    galHtml += '</div>';
    if (plant.plantPhotoAttribution) galHtml += '<p class="dravya-image-credit">📷 ' + plant.plantPhotoAttribution + '</p>';
    galHtml += '</div>';
  }
  if (usefulImg) {
    galHtml += '<div id="dgUsefulTab" class="dravya-image-tab">';
    galHtml += '<div class="dravya-image-container" onclick="dgOpenLightbox(\'' + usefulImg + '\')">';
    galHtml += '<img class="dravya-detail-image" src="' + usefulImg + '" alt="' + (plant.usefulPart || 'Useful part') + '" loading="lazy" onerror="this.parentElement.innerHTML=\'<p style=padding:40px;color:var(--sage)>Image unavailable</p>\'">';
    galHtml += '<span class="dravya-zoom-indicator">🔍 Click to enlarge</span>';
    galHtml += '</div>';
    if (plant.usefulPartAttribution) galHtml += '<p class="dravya-image-credit">📷 ' + plant.usefulPartAttribution + '</p>';
    galHtml += '</div>';
  }
  galHtml += '</div></div>';
  h += sec('Plant Images', galHtml);

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

// ---- Image tab switching ----
window.dgSwitchTab = function(tabId, event) {
  var tabs = document.querySelectorAll('.dravya-image-tab');
  for (var i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');
  var btns = document.querySelectorAll('.dravya-tab-btn');
  for (var i = 0; i < btns.length; i++) btns[i].classList.remove('active');

  document.getElementById(tabId).classList.add('active');
  if (event && event.target) event.target.classList.add('active');
  else {
    var idx = tabId === 'dgPlantTab' ? 0 : 1;
    var allBtns = document.querySelectorAll('.dravya-tab-btn');
    if (allBtns[idx]) allBtns[idx].classList.add('active');
  }
};

// ---- Lightbox ----
window.dgOpenLightbox = function(src) {
  var overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.92);z-index:9999;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
  var img = document.createElement('img');
  img.src = src;
  img.style.cssText = 'max-width:90vw;max-height:90vh;border-radius:8px;box-shadow:0 8px 48px rgba(0,0,0,0.5);';
  overlay.appendChild(img);
  overlay.onclick = function() { document.body.removeChild(overlay); };
  document.body.appendChild(overlay);
};

// ---- Show/Hide Detail ----
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
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function dgHideDetail() {
  document.getElementById('dravyagunaDetailView').style.display = 'none';
  document.getElementById('dravyagunaListView').style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---- Init ----
var dgInited = false;
async function dgInit() {
  await dgLoadData();
  var countEl = document.getElementById('dravyaCount');
  if (countEl && dgData.length) countEl.textContent = dgData.length + ' plants';
  // Rebuild filters + grid each call (section transitions cause re-render gaps)
  dgBuildFilters();
  dgRender();

  if (!dgInited) {
    var searchInput = document.getElementById('dravyagunaSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', function() { dgRender(); });
    }
    window.renderDravyagunaList = function(q) { dgRender(); };
    window.showDravyagunaDetail = function(id) { dgShowDetail(id); };
    window.hideDravyagunaDetail = function() { dgHideDetail(); };
    window.dgShowDetail = dgShowDetail;
    window.dgHideDetail = dgHideDetail;
    dgInited = true;
  }
}

// Pre-load data on page load so first Dravya click shows content