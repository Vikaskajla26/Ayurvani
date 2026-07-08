// ========== DRAVYA GUNA ADVANCED FILTERING SYSTEM ==========

// Active filters state
let activeFilters = {
  dosha: [],
  rasa: [],
  family: [],
  virya: []
};

// Extract unique filter values from plant data
function extractFilterOptions(plants) {
  const options = {
    dosha: new Set(),
    rasa: new Set(),
    family: new Set(),
    virya: new Set()
  };

  plants.forEach(plant => {
    // Extract Dosha
    if (plant.doshaghnata) {
      const doshaText = plant.doshaghnata.toLowerCase();
      if (doshaText.includes('vata')) options.dosha.add('Vata');
      if (doshaText.includes('pitta')) options.dosha.add('Pitta');
      if (doshaText.includes('kapha')) options.dosha.add('Kapha');
      if ((doshaText.includes('vata') || doshaText.includes('pitta') || doshaText.includes('kapha')) &&
          (doshaText.includes('त्रिदोष') || doshaText.includes('tridosha'))) {
        options.dosha.add('Tridoshic');
      }
    }

    // Extract Rasa
    if (plant.rasa_panchaka && plant.rasa_panchaka.rasa) {
      const rasas = plant.rasa_panchaka.rasa.split(',').map(r => r.trim());
      rasas.forEach(rasa => {
        const cleanRasa = rasa.replace(/\(.*?\)/g, '').trim();
        if (cleanRasa) options.rasa.add(cleanRasa);
      });
    }

    // Extract Family
    if (plant.family) {
      const familyList = plant.family.split(',').map(f => f.trim());
      familyList.forEach(f => {
        const cleanFamily = f.replace(/[0-9]+$/g, '').trim();
        if (cleanFamily && cleanFamily.length > 2) options.family.add(cleanFamily);
      });
    }

    // Extract Virya
    if (plant.rasa_panchaka && plant.rasa_panchaka.virya) {
      const virya = plant.rasa_panchaka.virya.toLowerCase();
      if (virya.includes('sheeta') || virya.includes('cold')) options.virya.add('Sheeta (Cold)');
      if (virya.includes('ushna') || virya.includes('hot')) options.virya.add('Ushna (Hot)');
    }
  });

  // Convert Sets to sorted Arrays
  return {
    dosha: Array.from(options.dosha).sort(),
    rasa: Array.from(options.rasa).sort(),
    family: Array.from(options.family).sort(),
    virya: Array.from(options.virya).sort()
  };
}

// Check if plant matches a dosha filter
function matchesDosha(plant, doshaFilters) {
  if (doshaFilters.length === 0) return true;

  const doshaghnata = plant.doshaghnata?.toLowerCase() || '';

  return doshaFilters.some(dosha => {
    switch(dosha.toLowerCase()) {
      case 'vata':
        return doshaghnata.includes('वातशामक') || doshaghnata.includes('vata');
      case 'pitta':
        return doshaghnata.includes('पित्तशामक') || doshaghnata.includes('pitta');
      case 'kapha':
        return doshaghnata.includes('कफशामक') || doshaghnata.includes('kapha');
      case 'tridoshic':
        return (doshaghnata.includes('त्रिदोष') || doshaghnata.includes('tridosha'));
      default:
        return false;
    }
  });
}

// Check if plant matches a rasa filter
function matchesRasa(plant, rasaFilters) {
  if (rasaFilters.length === 0) return true;

  const rasa = plant.rasa_panchaka?.rasa?.toLowerCase() || '';

  return rasaFilters.some(selectedRasa => {
    return rasa.includes(selectedRasa.toLowerCase());
  });
}

// Check if plant matches a family filter
function matchesFamily(plant, familyFilters) {
  if (familyFilters.length === 0) return true;

  const family = plant.family?.toLowerCase() || '';

  return familyFilters.some(selectedFamily => {
    return family.includes(selectedFamily.toLowerCase());
  });
}

// Check if plant matches a virya filter
function matchesVirya(plant, viryaFilters) {
  if (viryaFilters.length === 0) return true;

  const virya = plant.rasa_panchaka?.virya?.toLowerCase() || '';

  return viryaFilters.some(selectedVirya => {
    const viryaLower = selectedVirya.toLowerCase();
    return virya.includes('sheeta') && viryaLower.includes('sheeta') ||
           virya.includes('cold') && viryaLower.includes('cold') ||
           virya.includes('ushna') && viryaLower.includes('ushna') ||
           virya.includes('hot') && viryaLower.includes('hot');
  });
}

// Apply all filters to plant data
function filterPlants(plants, searchQuery = '', filters = activeFilters) {
  return plants.filter(plant => {
    // Text search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        plant.name?.toLowerCase().includes(q) ||
        plant.sanskrit_name?.toLowerCase().includes(q) ||
        plant.botanical_name?.toLowerCase().includes(q);

      if (!matchesSearch) return false;
    }

    // Apply all filter types
    return (
      matchesDosha(plant, filters.dosha) &&
      matchesRasa(plant, filters.rasa) &&
      matchesFamily(plant, filters.family) &&
      matchesVirya(plant, filters.virya)
    );
  });
}

// Update active filters
function updateFilter(filterType, value, checked) {
  if (checked) {
    if (!activeFilters[filterType].includes(value)) {
      activeFilters[filterType].push(value);
    }
  } else {
    activeFilters[filterType] = activeFilters[filterType].filter(f => f !== value);
  }

  // Re-render plant list with new filters
  const searchInput = document.getElementById('dravyagunaSearchInput');
  renderDravyagunaList_enhanced(searchInput?.value || '');
}

// Clear all filters
function clearAllFilters() {
  activeFilters = {
    dosha: [],
    rasa: [],
    family: [],
    virya: []
  };

  // Uncheck all checkboxes
  document.querySelectorAll('.dravya-filter-checkbox').forEach(cb => {
    cb.checked = false;
  });

  // Re-render plant list
  const searchInput = document.getElementById('dravyagunaSearchInput');
  renderDravyagunaList_enhanced(searchInput?.value || '');
}

// Build filter UI HTML
function buildFilterUI(filterOptions) {
  return `
    <div class="dravya-filters-container">
      <div class="dravya-filters-header">
        <h3>Filter Plants</h3>
        <button class="dravya-clear-filters-btn" onclick="clearAllFilters()">Clear All</button>
      </div>

      <div class="dravya-filters-grid">
        <!-- Dosha Filter -->
        <div class="dravya-filter-group">
          <h4>Dosha Effect</h4>
          <div class="dravya-filter-options">
            ${filterOptions.dosha.map(dosha => `
              <label class="dravya-filter-label">
                <input
                  type="checkbox"
                  class="dravya-filter-checkbox"
                  onchange="updateFilter('dosha', '${dosha}', this.checked)"
                />
                <span>${dosha}</span>
              </label>
            `).join('')}
          </div>
        </div>

        <!-- Rasa Filter -->
        <div class="dravya-filter-group">
          <h4>Rasa (Taste)</h4>
          <div class="dravya-filter-options">
            ${filterOptions.rasa.map(rasa => `
              <label class="dravya-filter-label">
                <input
                  type="checkbox"
                  class="dravya-filter-checkbox"
                  onchange="updateFilter('rasa', '${rasa}', this.checked)"
                />
                <span>${rasa}</span>
              </label>
            `).join('')}
          </div>
        </div>

        <!-- Virya Filter -->
        <div class="dravya-filter-group">
          <h4>Virya (Potency)</h4>
          <div class="dravya-filter-options">
            ${filterOptions.virya.map(virya => `
              <label class="dravya-filter-label">
                <input
                  type="checkbox"
                  class="dravya-filter-checkbox"
                  onchange="updateFilter('virya', '${virya}', this.checked)"
                />
                <span>${virya}</span>
              </label>
            `).join('')}
          </div>
        </div>

        <!-- Family Filter -->
        <div class="dravya-filter-group">
          <h4>Plant Family</h4>
          <div class="dravya-filter-options">
            ${filterOptions.family.map(family => `
              <label class="dravya-filter-label">
                <input
                  type="checkbox"
                  class="dravya-filter-checkbox"
                  onchange="updateFilter('family', '${family.replace(/'/g, "\\'")}', this.checked)"
                />
                <span>${family}</span>
              </label>
            `).join('')}
          </div>
        </div>
      </div>

      <div class="dravya-active-filters" id="dravyaActiveFilters"></div>
    </div>
  `;
}

// Update active filters display
function updateActiveFiltersDisplay() {
  const container = document.getElementById('dravyaActiveFilters');
  if (!container) return;

  const allActive = [
    ...activeFilters.dosha,
    ...activeFilters.rasa,
    ...activeFilters.family,
    ...activeFilters.virya
  ];

  if (allActive.length === 0) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = `
    <div class="dravya-active-filters-list">
      <span class="dravya-active-label">Active Filters:</span>
      ${allActive.map(filter => `
        <span class="dravya-active-filter-tag">
          ${filter}
          <button onclick="removeFilter('${filter}')" class="dravya-remove-filter">✕</button>
        </span>
      `).join('')}
    </div>
  `;
}

// Remove a single filter
function removeFilter(filterValue) {
  // Find which filter type this belongs to and remove it
  for (const filterType in activeFilters) {
    const index = activeFilters[filterType].indexOf(filterValue);
    if (index > -1) {
      activeFilters[filterType].splice(index, 1);

      // Uncheck the corresponding checkbox
      const checkbox = document.querySelector(
        `.dravya-filter-checkbox[value="${filterValue}"]`
      );
      if (checkbox) checkbox.checked = false;

      break;
    }
  }

  // Re-render
  const searchInput = document.getElementById('dravyagunaSearchInput');
  renderDravyagunaList_enhanced(searchInput?.value || '');
}

// Initialize filters UI on page load
function initializeDravyagunaFilters() {
  if (dravyagunaData.length === 0) return;

  const filterContainer = document.getElementById('dravyagunaFiltersContainer');
  if (!filterContainer) return;

  const filterOptions = extractFilterOptions(dravyagunaData);
  filterContainer.innerHTML = buildFilterUI(filterOptions);
}
