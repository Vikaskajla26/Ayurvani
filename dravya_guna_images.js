// ========== DRAVYA GUNA ENHANCED IMAGE DISPLAY ==========
// NOTE: dravyagunaData and dravyagunaLoaded are defined in index.html

// Update results info bar
function updateResultsInfo(filteredCount, totalCount) {
  const resultsInfo = document.getElementById('dravyagunaResultsInfo');
  if (!resultsInfo) return;

  const hasFilters = typeof activeFilters !== 'undefined' && Object.values(activeFilters).some(arr => arr.length > 0);
  const searchInput = document.getElementById('dravyagunaSearchInput');
  const hasSearch = searchInput?.value?.trim()?.length > 0;

  if (filteredCount === totalCount && !hasFilters && !hasSearch) {
    resultsInfo.innerHTML = '';
    return;
  }

  resultsInfo.innerHTML = `
    <div class="dravya-results-info">
      <span class="dravya-results-info-left">
        Showing <strong class="dravya-results-count">${filteredCount}</strong>
        of <strong>${totalCount}</strong> plants
        ${hasFilters ? 'with filters applied' : ''}
      </span>
      ${hasFilters ? `<button onclick="clearAllFilters()" class="dravya-clear-filters-btn">Clear All Filters</button>` : ''}
    </div>
  `;
}

// Initialize Dravya Guna view with filters
async function initDravyagunaView() {
  await loadDravyagunaData();

  // Update plant count display
  const countEl = document.getElementById('dravyaCount');
  if (countEl && dravyagunaData.length > 0) {
    countEl.textContent = dravyagunaData.length + ' plants';
  }

  if (typeof initializeDravyagunaFilters === 'function') {
    initializeDravyagunaFilters();
  }
  renderDravyagunaList_enhanced('');
}

function renderDravyagunaList_enhanced(q = '') {
  const grid = document.getElementById('dravyagunaGrid');
  if (!grid || dravyagunaData.length === 0) return;

  // Apply filters if filter system exists
  let filtered = dravyagunaData;
  if (typeof filterPlants === 'function') {
    filtered = filterPlants(dravyagunaData, q || '');
  } else {
    // Fallback to basic search
    const query = (q || '').trim().toLowerCase();
    filtered = !query ? dravyagunaData : dravyagunaData.filter(p =>
      (p.name?.toLowerCase().includes(query)) ||
      (p.sanskrit_name?.toLowerCase().includes(query)) ||
      (p.botanical_name?.toLowerCase().includes(query))
    );
  }

  // Update results info
  updateResultsInfo(filtered.length, dravyagunaData.length);

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="dravya-results-empty" style="grid-column:1/-1;">
        <div class="dravya-results-empty-icon">🔍</div>
        <div class="dravya-results-empty-text">No plants match your filters</div>
        <div class="dravya-results-empty-suggestion">Try adjusting your filter selections or search query</div>
        <button onclick="clearAllFilters()" class="dravya-clear-filters-btn" style="margin-top:16px;">Clear All Filters</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(p => `
    <div class="dravya-card" onclick="showDravyagunaDetail_enhanced('${p.id}')">
      <div class="dravya-card-image-wrapper">
        ${p.plantPhotoUrl ? `
          <img
            src="${p.plantPhotoUrl}"
            alt="${p.name}"
            class="dravya-card-image"
            loading="lazy"
            onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%23223c2e%22 width=%22200%22 height=%22200%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 fill=%22%23a9c2a0%22 text-anchor=%22middle%22 dy=%22.3em%22 font-family=%22Arial%22%3E🌿%3C/text%3E%3C/svg%3E'"
          />
        ` : `
          <div class="dravya-card-image-placeholder">🌿</div>
        `}
        <div class="dravya-card-overlay">
          <span class="dravya-view-btn">View Details</span>
        </div>
      </div>
      <div class="dravya-card-content">
        <h3>${p.name}</h3>
        <p class="dravya-sanskrit">${p.sanskrit_name}</p>
        <p class="dravya-botanical">${p.botanical_name}</p>
      </div>
    </div>
  `).join('');
}

function showDravyagunaDetail_enhanced(id) {
  const plant = dravyagunaData.find(p => p.id === id);
  if (!plant) return;

  const detailView = document.getElementById('dravyagunaDetailView');
  const listView = document.getElementById('dravyagunaListView');
  const contentDiv = document.getElementById('dravyagunaDetailContent');

  if (!detailView || !contentDiv) return;

  // Build detail HTML with image gallery
  const hasPlantPhoto = plant.plantPhotoUrl;
  const hasUsefulPartPhoto = plant.usefulPartPhotoUrl;

  contentDiv.innerHTML = `
    <div class="dravya-detail-container">
      <button class="dravya-back-btn" onclick="hideDravyagunaDetail_enhanced()">← Back to Plants</button>

      <div class="dravya-detail-header">
        <div class="dravya-detail-title">
          <h1>${plant.name}</h1>
          <p class="dravya-detail-sanskrit">${plant.sanskrit_name}</p>
          <p class="dravya-detail-botanical">${plant.botanical_name}</p>
        </div>
      </div>

      ${(hasPlantPhoto || hasUsefulPartPhoto) ? `
        <div class="dravya-image-gallery">
          <div class="dravya-gallery-tabs">
            ${hasPlantPhoto ? `<button class="dravya-tab-btn active" onclick="switchDravyaImageTab(event, 'plant')">🌿 Plant</button>` : ''}
            ${hasUsefulPartPhoto ? `<button class="dravya-tab-btn" onclick="switchDravyaImageTab(event, 'useful')">🌱 ${plant.usefulPart || 'Useful Part'}</button>` : ''}
          </div>

          <div class="dravya-gallery-content">
            ${hasPlantPhoto ? `
              <div class="dravya-image-tab active" id="dravya-tab-plant">
                <div class="dravya-image-container" onclick="openDravyaImageLightbox('${plant.plantPhotoUrl}', '${plant.name}')">
                  <img src="${plant.plantPhotoUrl}" alt="${plant.name} plant" class="dravya-detail-image" loading="lazy" />
                  <div class="dravya-zoom-indicator">🔍 Click to zoom</div>
                </div>
                ${plant.plantPhotoAttribution ? `<p class="dravya-image-credit">Photo: ${plant.plantPhotoAttribution}</p>` : ''}
              </div>
            ` : ''}

            ${hasUsefulPartPhoto ? `
              <div class="dravya-image-tab" id="dravya-tab-useful">
                <div class="dravya-image-container" onclick="openDravyaImageLightbox('${plant.usefulPartPhotoUrl}', '${plant.usefulPart || 'Useful part'}')">
                  <img src="${plant.usefulPartPhotoUrl}" alt="${plant.usefulPart || 'Useful part'}" class="dravya-detail-image" loading="lazy" />
                  <div class="dravya-zoom-indicator">🔍 Click to zoom</div>
                </div>
                ${plant.usefulPartAttribution ? `<p class="dravya-image-credit">Photo: ${plant.usefulPartAttribution}</p>` : ''}
              </div>
            ` : ''}
          </div>
        </div>
      ` : ''}

      <div class="dravya-detail-content">
        ${plant.sloka ? `
          <section class="dravya-section">
            <h2>Traditional Verse</h2>
            <p class="dravya-sloka">${plant.sloka}</p>
            ${plant.sloka_source ? `<p class="dravya-sloka-source">— ${plant.sloka_source}</p>` : ''}
          </section>
        ` : ''}

        ${plant.synonyms && plant.synonyms.length > 0 ? `
          <section class="dravya-section">
            <h2>Synonyms</h2>
            <div class="dravya-synonyms">
              ${plant.synonyms.map(s => `
                <div class="dravya-synonym-item">
                  <strong>${s.term}</strong> — ${s.meaning}
                </div>
              `).join('')}
            </div>
          </section>
        ` : ''}

        ${plant.rasa_panchaka ? `
          <section class="dravya-section">
            <h2>Rasa Panchaka (Properties)</h2>
            <div class="dravya-rasa-panchaka">
              ${plant.rasa_panchaka.rasa ? `<div class="dravya-property"><strong>Rasa:</strong> ${plant.rasa_panchaka.rasa}</div>` : ''}
              ${plant.rasa_panchaka.guna ? `<div class="dravya-property"><strong>Guna:</strong> ${plant.rasa_panchaka.guna}</div>` : ''}
              ${plant.rasa_panchaka.virya ? `<div class="dravya-property"><strong>Virya:</strong> ${plant.rasa_panchaka.virya}</div>` : ''}
              ${plant.rasa_panchaka.vipaka ? `<div class="dravya-property"><strong>Vipaka:</strong> ${plant.rasa_panchaka.vipaka}</div>` : ''}
            </div>
          </section>
        ` : ''}

        ${plant.rogaghnata ? `
          <section class="dravya-section">
            <h2>Therapeutic Uses</h2>
            <p>${plant.rogaghnata}</p>
          </section>
        ` : ''}

        ${plant.pharmacological_actions && plant.pharmacological_actions.length > 0 ? `
          <section class="dravya-section">
            <h2>Pharmacological Actions</h2>
            <div class="dravya-actions">
              ${plant.pharmacological_actions.map(a => `<span class="dravya-action-badge">${a}</span>`).join('')}
            </div>
          </section>
        ` : ''}
      </div>
    </div>
  `;

  // Hide list, show detail
  if (listView) listView.style.display = 'none';
  detailView.style.display = 'block';
}

function hideDravyagunaDetail_enhanced() {
  const detailView = document.getElementById('dravyagunaDetailView');
  const listView = document.getElementById('dravyagunaListView');

  if (detailView) detailView.style.display = 'none';
  if (listView) listView.style.display = 'block';
}

function switchDravyaImageTab(e, tabName) {
  // Remove active class from all tabs and buttons
  document.querySelectorAll('.dravya-image-tab').forEach(tab => tab.classList.remove('active'));
  document.querySelectorAll('.dravya-tab-btn').forEach(btn => btn.classList.remove('active'));

  // Add active class to clicked button and corresponding tab
  e.target.classList.add('active');
  const tab = document.getElementById(`dravya-tab-${tabName}`);
  if (tab) tab.classList.add('active');
}

function openDravyaImageLightbox(imageUrl, title) {
  // Create lightbox if it doesn't exist
  let lightbox = document.getElementById('dravyaImageLightbox');
  if (!lightbox) {
    lightbox = document.createElement('div');
    lightbox.id = 'dravyaImageLightbox';
    lightbox.className = 'dravya-lightbox';
    lightbox.innerHTML = `
      <div class="dravya-lightbox-content">
        <button class="dravya-lightbox-close" onclick="closeDravyaImageLightbox()">✕</button>
        <img id="dravya-lightbox-image" src="" alt="" class="dravya-lightbox-image" />
        <p id="dravya-lightbox-title" class="dravya-lightbox-title"></p>
      </div>
    `;
    document.body.appendChild(lightbox);
    lightbox.addEventListener('click', function(e) {
      if (e.target === lightbox) closeDravyaImageLightbox();
    });
  }

  // Set image and title
  document.getElementById('dravya-lightbox-image').src = imageUrl;
  document.getElementById('dravya-lightbox-title').textContent = title;
  lightbox.classList.add('active');
}

function closeDravyaImageLightbox() {
  const lightbox = document.getElementById('dravyaImageLightbox');
  if (lightbox) lightbox.classList.remove('active');
}

// Pre-load data silently when page loads
document.addEventListener('DOMContentLoaded', function() {
  if (!dravyagunaLoaded) {
    fetch('/dravyaguna_data.json')
      .then(resp => resp.json())
      .then(data => {
        dravyagunaData = data;
        dravyagunaLoaded = true;
        const countEl = document.getElementById('dravyaCount');
        if (countEl) countEl.textContent = data.length + ' plants';
      })
      .catch(err => console.error('Error pre-loading dravya guna data:', err));
  }
});

