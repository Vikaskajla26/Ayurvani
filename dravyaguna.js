// ========== DRAVYA GUNA - Standalone Module ==========
// This file loads independently. All functions are self-contained.

(function() {
  'use strict';

  // Wait for window load to ensure everything is ready
  window.addEventListener('load', function() {

    // Hook into showView when dravyaguna is called
    const originalShowView = window.showView;
    if (typeof originalShowView !== 'function') return;

    // Patch showView to trigger our init
    window.showView = function(id) {
      originalShowView(id);
      if (id === 'dravyaguna') {
        setTimeout(initDravyaguna, 100);
      }
    };

    // Main initialization
    async function initDravyaguna() {
      // Load data
      if (!window.dravyagunaLoaded) {
        try {
          const resp = await fetch('/dravyaguna_data.json');
          window.dravyagunaData = await resp.json();
          window.dravyagunaLoaded = true;
          const countEl = document.getElementById('dravyaCount');
          if (countEl) countEl.textContent = window.dravyagunaData.length + ' plants';
        } catch(e) {
          console.error('Failed to load plant data:', e);
          return;
        }
      }

      const data = window.dravyagunaData;
      if (!data || !data.length) return;

      // Build filter container
      buildFilters(data);

      // Render plants
      renderPlants(data, '');
    }

    // Build filter UI
    function buildFilters(data) {
      const container = document.getElementById('dravyagunaFiltersContainer');
      if (!container) return;

      // Extract unique filter options
      const doshas = new Set();
      const rasas = new Set();
      const viryas = new Set();
      const families = new Set();

      data.forEach(p => {
        if (p.doshaghnata) {
          const d = p.doshaghnata.toLowerCase();
          if (d.includes('vata') || d.includes('वात')) doshas.add('Vata');
          if (d.includes('pitta') || d.includes('पित्त')) doshas.add('Pitta');
          if (d.includes('kapha') || d.includes('कफ')) doshas.add('Kapha');
        }
        if (p.rasa_panchaka?.rasa) {
          p.rasa_panchaka.rasa.split(',').forEach(r => {
            const c = r.replace(/\(.*?\)/g,'').trim();
            if (c) rasas.add(c);
          });
        }
        if (p.rasa_panchaka?.virya) {
          const v = p.rasa_panchaka.virya.toLowerCase();
          if (v.includes('sheeta')||v.includes('cold')||v.includes('शीत')) viryas.add('Sheeta (Cold)');
          if (v.includes('ushna')||v.includes('hot')||v.includes('उष्ण')) viryas.add('Ushna (Hot)');
        }
        if (p.family) {
          p.family.split(',').forEach(f => {
            const c = f.trim();
            if (c && c.length > 2) families.add(c);
          });
        }
      });

      const sortArr = s => [...s].sort();

      container.innerHTML = `
        <div class="dravya-filters-container">
          <div class="dravya-filters-header">
            <h3>Filter Plants</h3>
            <button class="dravya-clear-filters-btn" id="dravyaClearFilters">Clear All</button>
          </div>
          <div class="dravya-filters-grid">
            <div class="dravya-filter-group">
              <h4>Dosha Effect</h4>
              <div class="dravya-filter-options">
                ${sortArr(doshas).map(d => `<label class="dravya-filter-label"><input type="checkbox" class="dravya-filter-cb" data-filter="dosha" value="${d}"/><span>${d}</span></label>`).join('')}
              </div>
            </div>
            <div class="dravya-filter-group">
              <h4>Rasa (Taste)</h4>
              <div class="dravya-filter-options">
                ${sortArr(rasas).map(r => `<label class="dravya-filter-label"><input type="checkbox" class="dravya-filter-cb" data-filter="rasa" value="${r}"/><span>${r}</span></label>`).join('')}
              </div>
            </div>
            <div class="dravya-filter-group">
              <h4>Virya (Potency)</h4>
              <div class="dravya-filter-options">
                ${sortArr(viryas).map(v => `<label class="dravya-filter-label"><input type="checkbox" class="dravya-filter-cb" data-filter="virya" value="${v}"/><span>${v}</span></label>`).join('')}
              </div>
            </div>
            <div class="dravya-filter-group">
              <h4>Plant Family</h4>
              <div class="dravya-filter-options">
                ${sortArr(families).map(f => `<label class="dravya-filter-label"><input type="checkbox" class="dravya-filter-cb" data-filter="family" value="${f}"/><span>${f}</span></label>`).join('')}
              </div>
            </div>
          </div>
        </div>
      `;

      // Wire up filter checkboxes
      container.querySelectorAll('.dravya-filter-cb').forEach(cb => {
        cb.addEventListener('change', function() {
          applyFilters(data);
        });
      });

      // Wire up clear button
      const clearBtn = document.getElementById('dravyaClearFilters');
      if (clearBtn) {
        clearBtn.addEventListener('click', function() {
          container.querySelectorAll('.dravya-filter-cb').forEach(cb => cb.checked = false);
          applyFilters(data);
        });
      }
    }

    // Apply filters and re-render
    function applyFilters(data) {
      const searchVal = document.getElementById('dravyagunaSearchInput')?.value || '';
      const activeFilters = getActiveFilters();

      const filtered = data.filter(p => {
        // Text search
        if (searchVal.trim()) {
          const q = searchVal.toLowerCase();
          if (!(p.name?.toLowerCase().includes(q) ||
                p.sanskrit_name?.toLowerCase().includes(q) ||
                p.botanical_name?.toLowerCase().includes(q))) {
            return false;
          }
        }

        // Dosha filter
        if (activeFilters.dosha.length) {
          const d = (p.doshaghnata || '').toLowerCase();
          const match = activeFilters.dosha.some(f =>
            (f === 'Vata' && (d.includes('vata') || d.includes('वात'))) ||
            (f === 'Pitta' && (d.includes('pitta') || d.includes('पित्त'))) ||
            (f === 'Kapha' && (d.includes('kapha') || d.includes('कफ')))
          );
          if (!match) return false;
        }

        // Rasa filter
        if (activeFilters.rasa.length) {
          const rasa = (p.rasa_panchaka?.rasa || '').toLowerCase();
          const match = activeFilters.rasa.some(f => rasa.includes(f.toLowerCase()));
          if (!match) return false;
        }

        // Virya filter
        if (activeFilters.virya.length) {
          const v = (p.rasa_panchaka?.virya || '').toLowerCase();
          const match = activeFilters.virya.some(f => {
            const l = f.toLowerCase();
            return (v.includes('sheeta') || v.includes('cold') || v.includes('शीत')) && (l.includes('sheeta') || l.includes('cold')) ||
                   (v.includes('ushna') || v.includes('hot') || v.includes('उष्ण')) && (l.includes('ushna') || l.includes('hot'));
          });
          if (!match) return false;
        }

        // Family filter
        if (activeFilters.family.length) {
          const family = (p.family || '').toLowerCase();
          const match = activeFilters.family.some(f => family.includes(f.toLowerCase()));
          if (!match) return false;
        }

        return true;
      });

      // Update results info
      updateResults(filtered.length, data.length, activeFilters);

      // Render filtered plants
      renderPlants(filtered, searchVal);
    }

    function getActiveFilters() {
      const filters = { dosha: [], rasa: [], virya: [], family: [] };
      document.querySelectorAll('.dravya-filter-cb:checked').forEach(cb => {
        const type = cb.dataset.filter;
        if (filters[type]) filters[type].push(cb.value);
      });
      return filters;
    }

    function updateResults(count, total, filters) {
      const el = document.getElementById('dravyagunaResultsInfo');
      if (!el) return;
      const hasFilters = Object.values(filters).some(a => a.length);
      const hasSearch = document.getElementById('dravyagunaSearchInput')?.value?.trim()?.length > 0;
      if (count === total && !hasFilters && !hasSearch) {
        el.innerHTML = '';
        return;
      }
      el.innerHTML = `<div class="dravya-results-info"><span class="dravya-results-info-left">Showing <strong class="dravya-results-count">${count}</strong> of <strong>${total}</strong> plants${hasFilters ? ' with filters applied' : ''}</span></div>`;
    }

    // Render plant grid
    function renderPlants(plants, searchQuery) {
      const grid = document.getElementById('dravyagunaGrid');
      if (!grid) return;

      // Hide detail view, show list
      const detailView = document.getElementById('dravyagunaDetailView');
      const listView = document.getElementById('dravyagunaListView');
      if (detailView) detailView.style.display = 'none';
      if (listView) listView.style.display = 'block';

      if (!plants.length) {
        grid.innerHTML = '<div class="dravya-results-empty" style="grid-column:1/-1;padding:40px;text-align:center;"><div style="font-size:3rem;opacity:0.6;">🔍</div><div style="margin-top:12px;">No plants match your filters</div><div style="font-size:0.85rem;color:var(--sage);margin-top:4px;">Try adjusting your selections</div></div>';
        return;
      }

      grid.innerHTML = plants.map(p => `
        <div class="dravya-card" onclick="showPlantDetail('${p.id.replace(/'/g, "\\'")}')">
          <div class="dravya-card-content" style="padding:16px;text-align:center;display:flex;flex-direction:column;justify-content:center;height:100%;">
            <h3 style="margin:0 0 4px;color:var(--gold-light);font-family:'Cormorant Garamond',serif;">${p.name || ''}</h3>
            <p style="margin:0 0 2px;font-size:0.9rem;color:var(--cream);font-family:'Tiro Devanagari Hindi',sans-serif;">${p.sanskrit_name || ''}</p>
            <p style="margin:0;font-size:0.75rem;color:var(--sage);font-style:italic;">${p.botanical_name || ''}</p>
          </div>
        </div>
      `).join('');
    }

    // Show plant detail with all notes
    window.showPlantDetail = function(id) {
      const plant = window.dravyagunaData?.find(p => p.id === id);
      if (!plant) return;

      const detailView = document.getElementById('dravyagunaDetailView');
      const listView = document.getElementById('dravyagunaListView');
      const contentDiv = document.getElementById('dravyagunaDetailContent');
      if (!detailView || !contentDiv) return;

      // Helper functions
      const section = (title, content) => content ? `<section class="dravya-section"><h2>${title}</h2>${content}</section>` : '';
      const list = (arr) => arr?.length ? `<ul class="dravya-list">${arr.map(x => `<li>${x}</li>`).join('')}</ul>` : '';

      contentDiv.innerHTML = `
        <div class="dravya-detail-container">
          <button class="dravya-back-btn" onclick="hidePlantDetail()">← Back to Plants</button>
          <div class="dravya-detail-header">
            <div class="dravya-detail-title">
              <h1>${plant.name || ''}</h1>
              <p class="dravya-detail-sanskrit">${plant.sanskrit_name || ''}</p>
              <p class="dravya-detail-botanical">${plant.botanical_name || ''}</p>
              ${plant.family ? `<p class="dravya-detail-family">Family: ${plant.family}</p>` : ''}
            </div>
          </div>
          <div class="dravya-detail-content">
            ${section('श्लोक (Traditional Verse)', plant.sloka ? `<p class="dravya-sloka">${plant.sloka}</p>${plant.sloka_source ? `<p class="dravya-sloka-source">— ${plant.sloka_source}</p>` : ''}` : '')}
            ${section('Synonyms', plant.synonyms?.length ? `<div class="dravya-synonyms">${plant.synonyms.map(s => `<div class="dravya-synonym-item"><strong>${s.term}</strong>${s.meaning ? ' — ' + s.meaning : ''}</div>`).join('')}</div>` : '')}
            ${section('Vernacular Names', plant.vernacular_names?.length ? `<div class="dravya-vernacular">${plant.vernacular_names.map(v => `<div class="dravya-vernacular-item"><strong>${v.lang}:</strong> ${v.name}</div>`).join('')}</div>` : '')}
            ${section('Classification of Gana', list(plant.classification_of_gana))}
            ${section('External Morphology', plant.external_morphology ? (plant.external_morphology.habitat ? '<p><strong>Habitat:</strong> ' + plant.external_morphology.habitat + '</p>' : '') + (plant.external_morphology.details?.length ? list(plant.external_morphology.details) : '') : '')}
            ${section('Useful Parts', plant.useful_parts ? '<p>' + plant.useful_parts + '</p>' : '')}
            ${section('Important Phytoconstituents', plant.phytoconstituents ? '<p>' + plant.phytoconstituents + '</p>' : '')}
            ${section('Rasa Panchaka (Properties)', plant.rasa_panchaka ? `<div class="dravya-rasa-panchaka">${(plant.rasa_panchaka.rasa ? `<div class="dravya-property"><strong>Rasa:</strong> ${plant.rasa_panchaka.rasa}</div>` : '') + (plant.rasa_panchaka.guna ? `<div class="dravya-property"><strong>Guna:</strong> ${plant.rasa_panchaka.guna}</div>` : '') + (plant.rasa_panchaka.virya ? `<div class="dravya-property"><strong>Virya:</strong> ${plant.rasa_panchaka.virya}</div>` : '') + (plant.rasa_panchaka.vipaka ? `<div class="dravya-property"><strong>Vipaka:</strong> ${plant.rasa_panchaka.vipaka}</div>` : '')}</div>` : '')}
            ${section('Prabhava', plant.prabhava ? '<p>' + plant.prabhava + '</p>' : '')}
            ${section('Karma', plant.karma ? `<p><strong>Dosha Karma:</strong> ${plant.karma.dosha_karma || ''}</p><p><strong>Karma:</strong> ${plant.karma.karma || plant.karma.general || ''}</p>` : '')}
            ${section('Doshaghnata', plant.doshaghnata ? '<p>' + plant.doshaghnata + '</p>' : '')}
            ${section('Rogaghnata (Therapeutic Uses)', plant.rogaghnata ? '<p>' + plant.rogaghnata + '</p>' : '')}
            ${section('Amayika Prayoga (Clinical Applications)', list(plant.amayika_prayoga))}
            ${section('Matra (Dosage)', plant.matra?.length ? `<div class="dravya-matra">${plant.matra.map(m => `<div class="dravya-matra-item"><strong>${m.form}:</strong> ${m.dose}</div>`).join('')}</div>` : '')}
            ${section('Pharmacological Actions', plant.pharmacological_actions?.length ? `<div class="dravya-actions">${plant.pharmacological_actions.map(a => `<span class="dravya-action-badge">${a}</span>`).join('')}</div>` : '')}
            ${section('Kalpana (Formulations)', list(plant.kalpana))}
            ${section('Varieties', plant.varieties ? '<p>' + (typeof plant.varieties === 'string' ? plant.varieties : plant.varieties.join(', ')) + '</p>' : '')}
            ${section('Research Updates', list(plant.research_updates))}
          </div>
        </div>
      `;

      listView.style.display = 'none';
      detailView.style.display = 'block';
    };

    window.hidePlantDetail = function() {
      document.getElementById('dravyagunaDetailView').style.display = 'none';
      document.getElementById('dravyagunaListView').style.display = 'block';
    };

    // Wire up search input
    const searchInput = document.getElementById('dravyagunaSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        applyFilters(window.dravyagunaData);
      });
    }

    console.log('Dravya Guna module initialized');
  });
})();
