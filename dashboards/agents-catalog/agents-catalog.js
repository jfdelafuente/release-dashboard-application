/* ============================================================
   Orange — Catálogo de Agentes y Skills IA
   dashboards/agents-catalog/agents-catalog.js
   ============================================================ */

(function () {
  "use strict";

  // State Management
  var state = {
    catalog: null,
    agents: [],
    skills: [],
    domains: [],
    activeTab: "agents", // 'agents' | 'skills'
    activeDomain: "all",
    searchQuery: "",
    targetRepo: "<TargetRepo>",
    currentDetailItem: null // item currently displayed in detail modal
  };

  // DOM Elements Cache
  var dom = {};

  // Storage key for TargetRepo preference
  var STORAGE_KEY_TARGET_REPO = "mo_agents_target_repo";

  // Initialize
  document.addEventListener("DOMContentLoaded", init);

  function init() {
    cacheDom();
    loadPreferences();
    bindEvents();
    fetchCatalogData();
  }

  function cacheDom() {
    dom.tabAgents = document.getElementById("tab-agents");
    dom.tabSkills = document.getElementById("tab-skills");
    dom.tabBadgeAgents = document.getElementById("tab-badge-agents");
    dom.tabBadgeSkills = document.getElementById("tab-badge-skills");

    dom.agentsView = document.getElementById("agents-view");
    dom.skillsView = document.getElementById("skills-view");
    dom.agentsContent = document.getElementById("agents-content");
    dom.skillsContent = document.getElementById("skills-content");

    dom.searchInput = document.getElementById("search-input");
    dom.searchClearBtn = document.getElementById("search-clear-btn");
    dom.resultsCount = document.getElementById("results-count");
    dom.domainChips = document.getElementById("domain-chips-container");
    dom.chipCountAll = document.getElementById("chip-count-all");
    dom.chipCountBrand = document.getElementById("chip-count-brand");
    dom.chipCountIt = document.getElementById("chip-count-it");

    dom.loadingState = document.getElementById("loading-state");
    dom.emptyState = document.getElementById("empty-state");
    dom.btnResetFilters = document.getElementById("btn-reset-filters");

    // Hero Repo Config Button
    dom.btnConfigTarget = document.getElementById("btn-config-target");
    dom.currentTargetDisplay = document.getElementById("current-target-display");

    // Detail Modal
    dom.detailModal = document.getElementById("detail-modal");
    dom.detailModalClose = document.getElementById("detail-modal-close");
    dom.detailModalTitle = document.getElementById("detail-modal-title");
    dom.detailModalMeta = document.getElementById("detail-modal-meta");
    dom.detailModalContent = document.getElementById("detail-modal-content");
    dom.modalCopyCmdBtn = document.getElementById("modal-copy-cmd-btn");
    dom.modalCopyPromptBtn = document.getElementById("modal-copy-prompt-btn");

    // Config Modal
    dom.configModal = document.getElementById("config-modal");
    dom.configModalClose = document.getElementById("config-modal-close");
    dom.configRepoInput = document.getElementById("config-repo-input");
    dom.configPreviewCmd = document.getElementById("config-preview-cmd");
    dom.configBtnSave = document.getElementById("config-btn-save");
    dom.configBtnReset = document.getElementById("config-btn-reset");
  }

  function loadPreferences() {
    try {
      var savedRepo = localStorage.getItem(STORAGE_KEY_TARGET_REPO);
      if (savedRepo && savedRepo.trim()) {
        state.targetRepo = savedRepo.trim();
      }
    } catch (e) {
      console.warn("No se pudo leer localStorage:", e);
    }
    updateTargetRepoDisplay();
  }

  function savePreferences(newRepo) {
    state.targetRepo = (newRepo && newRepo.trim()) ? newRepo.trim() : "<TargetRepo>";
    try {
      localStorage.setItem(STORAGE_KEY_TARGET_REPO, state.targetRepo);
    } catch (e) {
      console.warn("No se pudo guardar en localStorage:", e);
    }
    updateTargetRepoDisplay();
    render();
  }

  function updateTargetRepoDisplay() {
    if (dom.currentTargetDisplay) {
      dom.currentTargetDisplay.textContent = state.targetRepo;
      dom.currentTargetDisplay.title = state.targetRepo;
    }
  }

  function bindEvents() {
    // Search input
    if (dom.searchInput) {
      dom.searchInput.addEventListener("input", function (e) {
        state.searchQuery = e.target.value.trim().toLowerCase();
        if (dom.searchClearBtn) {
          dom.searchClearBtn.style.display = state.searchQuery ? "block" : "none";
        }
        render();
      });
    }

    // Search clear button
    if (dom.searchClearBtn) {
      dom.searchClearBtn.addEventListener("click", function () {
        if (dom.searchInput) dom.searchInput.value = "";
        state.searchQuery = "";
        dom.searchClearBtn.style.display = "none";
        if (dom.searchInput) dom.searchInput.focus();
        render();
      });
    }

    // Reset filters button in empty state
    if (dom.btnResetFilters) {
      dom.btnResetFilters.addEventListener("click", function () {
        resetAllFilters();
      });
    }

    // Domain chips filtering
    if (dom.domainChips) {
      dom.domainChips.addEventListener("click", function (e) {
        var btn = e.target.closest(".chip-btn");
        if (!btn) return;
        var domain = btn.dataset.domain;
        if (!domain) return;

        state.activeDomain = domain;
        var allChips = dom.domainChips.querySelectorAll(".chip-btn");
        allChips.forEach(function (c) { c.classList.remove("active"); });
        btn.classList.add("active");

        render();
      });
    }

    // Tab buttons
    if (dom.tabAgents) {
      dom.tabAgents.addEventListener("click", function () {
        switchTab("agents");
      });
    }
    if (dom.tabSkills) {
      dom.tabSkills.addEventListener("click", function () {
        switchTab("skills");
      });
    }

    // Target Repo Config Modal
    if (dom.btnConfigTarget) {
      dom.btnConfigTarget.addEventListener("click", openConfigModal);
    }
    if (dom.configModalClose) {
      dom.configModalClose.addEventListener("click", closeConfigModal);
    }
    if (dom.configModal) {
      dom.configModal.addEventListener("click", function (e) {
        if (e.target === dom.configModal) closeConfigModal();
      });
    }
    if (dom.configRepoInput) {
      dom.configRepoInput.addEventListener("input", function (e) {
        updateConfigPreview(e.target.value);
      });
    }
    // Presets in config modal
    document.querySelectorAll(".config-preset-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var path = btn.dataset.path;
        if (dom.configRepoInput) {
          dom.configRepoInput.value = path;
          updateConfigPreview(path);
        }
      });
    });
    if (dom.configBtnSave) {
      dom.configBtnSave.addEventListener("click", function () {
        var val = dom.configRepoInput ? dom.configRepoInput.value : "";
        savePreferences(val);
        closeConfigModal();
        notify("Ruta destino actualizada: " + state.targetRepo, "success");
      });
    }
    if (dom.configBtnReset) {
      dom.configBtnReset.addEventListener("click", function () {
        if (dom.configRepoInput) {
          dom.configRepoInput.value = "<TargetRepo>";
          updateConfigPreview("<TargetRepo>");
        }
      });
    }

    // Detail Modal Events
    if (dom.detailModalClose) {
      dom.detailModalClose.addEventListener("click", closeDetailModal);
    }
    if (dom.detailModal) {
      dom.detailModal.addEventListener("click", function (e) {
        if (e.target === dom.detailModal) closeDetailModal();
      });
    }
    if (dom.modalCopyCmdBtn) {
      dom.modalCopyCmdBtn.addEventListener("click", function () {
        if (!state.currentDetailItem) return;
        var cmd = buildDeploymentCommand(state.currentDetailItem.id);
        copyToClipboard(cmd, dom.modalCopyCmdBtn, "Comando CLI copiado");
      });
    }
    if (dom.modalCopyPromptBtn) {
      dom.modalCopyPromptBtn.addEventListener("click", function () {
        if (!state.currentDetailItem || !state.currentDetailItem.markdown_content) return;
        copyToClipboard(state.currentDetailItem.markdown_content, dom.modalCopyPromptBtn, "Markdown completo copiado");
      });
    }

    // Keyboard navigation (ESC closes open modal)
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        closeDetailModal();
        closeConfigModal();
      }
    });
  }

  function resetAllFilters() {
    state.searchQuery = "";
    state.activeDomain = "all";
    if (dom.searchInput) dom.searchInput.value = "";
    if (dom.searchClearBtn) dom.searchClearBtn.style.display = "none";
    if (dom.domainChips) {
      var allChips = dom.domainChips.querySelectorAll(".chip-btn");
      allChips.forEach(function (c) {
        if (c.dataset.domain === "all") c.classList.add("active");
        else c.classList.remove("active");
      });
    }
    render();
  }

  function switchTab(tabId) {
    state.activeTab = tabId;
    if (tabId === "agents") {
      dom.tabAgents.classList.add("active");
      dom.tabAgents.setAttribute("aria-selected", "true");
      dom.tabSkills.classList.remove("active");
      dom.tabSkills.setAttribute("aria-selected", "false");
      dom.agentsView.style.display = "block";
      dom.skillsView.style.display = "none";
      if (dom.domainChips) dom.domainChips.style.display = "flex";
    } else {
      dom.tabSkills.classList.add("active");
      dom.tabSkills.setAttribute("aria-selected", "true");
      dom.tabAgents.classList.remove("active");
      dom.tabAgents.setAttribute("aria-selected", "false");
      dom.skillsView.style.display = "grid";
      dom.agentsView.style.display = "none";
      if (dom.domainChips) dom.domainChips.style.display = "none";
    }
    render();
  }

  // ============================================================
  // Data Fetching with Graceful Fallback
  // ============================================================
  function fetchCatalogData() {
    var primaryUrl = "/api/agents-catalog";
    var fallbackUrl = "/data/output/agents_catalog.json";

    fetch(primaryUrl)
      .then(function (res) {
        if (!res.ok) throw new Error("Status " + res.status);
        return res.json();
      })
      .then(function (json) {
        processCatalogData(json);
      })
      .catch(function (err) {
        console.warn("Fallback a lectura directa de JSON estático:", err);
        return fetch(fallbackUrl)
          .then(function (res) {
            if (!res.ok) throw new Error("Fallback failed with status " + res.status);
            return res.json();
          })
          .then(function (json) {
            processCatalogData(json);
          })
          .catch(function (fallbackErr) {
            console.error("Error crítico cargando catálogo:", fallbackErr);
            showLoadError(fallbackErr);
          });
      });
  }

  function processCatalogData(catalog) {
    state.catalog = catalog;
    var data = catalog.data || {};
    state.agents = data.agents || [];
    state.skills = data.skills || [];
    state.domains = data.domains || [];

    updateTabBadges();
    updateChipCounts();

    if (dom.loadingState) dom.loadingState.style.display = "none";
    render();
  }

  function showLoadError(err) {
    if (dom.loadingState) {
      dom.loadingState.innerHTML =
        '<div style="color: #DC2626; text-align: center; max-width: 480px;">' +
        '<p style="font-weight: 700; font-size: 16px;">Error cargando catálogo de agentes</p>' +
        '<p style="font-size: 13px; color: var(--text-muted);">' + escapeHtml(err.message) + '</p>' +
        '<p style="font-size: 12px; margin-top: 10px;">Asegúrate de haber generado el archivo ejecutando <code>python converters/cli/build_agents_catalog.py</code>.</p>' +
        '</div>';
    }
  }

  function updateTabBadges() {
    if (dom.tabBadgeAgents) dom.tabBadgeAgents.textContent = state.agents.length;
    if (dom.tabBadgeSkills) dom.tabBadgeSkills.textContent = state.skills.length;
  }

  function updateChipCounts() {
    if (dom.chipCountAll) dom.chipCountAll.textContent = state.agents.length;

    var brandCount = 0;
    var itCount = 0;
    state.agents.forEach(function (a) {
      if (a.domain === "brand-content") brandCount++;
      if (a.domain === "it-incidents") itCount++;
    });

    if (dom.chipCountBrand) dom.chipCountBrand.textContent = brandCount;
    if (dom.chipCountIt) dom.chipCountIt.textContent = itCount;
  }

  // ============================================================
  // Rendering Engine
  // ============================================================
  function render() {
    if (state.activeTab === "agents") {
      renderAgentsView();
    } else {
      renderSkillsView();
    }
  }

  function renderAgentsView() {
    var filtered = state.agents.filter(function (agent) {
      // Domain filter
      if (state.activeDomain !== "all" && agent.domain !== state.activeDomain) {
        return false;
      }
      // Search query
      if (state.searchQuery) {
        var q = state.searchQuery;
        var matchName = (agent.name || "").toLowerCase().indexOf(q) !== -1;
        var matchAlias = (agent.alias || "").toLowerCase().indexOf(q) !== -1;
        var matchDesc = (agent.description || "").toLowerCase().indexOf(q) !== -1;
        var matchDomain = (agent.domain_label || "").toLowerCase().indexOf(q) !== -1;
        var matchSkills = (agent.recommended_skills || []).some(function (s) {
          return s.toLowerCase().indexOf(q) !== -1;
        });
        if (!matchName && !matchAlias && !matchDesc && !matchDomain && !matchSkills) {
          return false;
        }
      }
      return true;
    });

    // Update Counter
    if (dom.resultsCount) {
      var label = filtered.length === 1 ? "1 agente encontrado" : filtered.length + " agentes encontrados";
      dom.resultsCount.textContent = label;
    }

    if (filtered.length === 0) {
      dom.agentsContent.innerHTML = "";
      if (dom.emptyState) dom.emptyState.style.display = "block";
      return;
    }

    if (dom.emptyState) dom.emptyState.style.display = "none";

    // Group agents by domain
    var grouped = {};
    filtered.forEach(function (agent) {
      var d = agent.domain || "general";
      if (!grouped[d]) grouped[d] = [];
      grouped[d].push(agent);
    });

    var html = "";

    // Iterate through domains in predefined or discovered order
    var domainKeys = Object.keys(grouped);
    domainKeys.forEach(function (domKey) {
      var agentsInDom = grouped[domKey];
      var firstAgent = agentsInDom[0];
      var domainLabel = (firstAgent && firstAgent.domain_label) || domKey;
      var domainBadgeClass = domKey === "brand-content" ? "domain-badge-brand" : "domain-badge-it";

      html += '<section class="domain-section">';
      html += '  <header class="domain-section-header">';
      html += '    <div class="domain-title-group">';
      html += '      <h2 class="domain-title">' + escapeHtml(domainLabel) + '</h2>';
      html += '      <span class="domain-badge-pill ' + domainBadgeClass + '">' + agentsInDom.length + ' ' + (agentsInDom.length === 1 ? 'agente' : 'agentes') + '</span>';
      html += '    </div>';
      html += '    <button class="domain-deploy-btn" data-domain-id="' + escapeHtml(domKey) + '" title="Copiar comando para desplegar todos los agentes de este dominio">';
      html += '      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
      html += '      Desplegar Dominio';
      html += '    </button>';
      html += '  </header>';

      html += '  <div class="agents-grid">';
      agentsInDom.forEach(function (agent) {
        html += renderAgentCard(agent);
      });
      html += '  </div>';
      html += '</section>';
    });

    dom.agentsContent.innerHTML = html;
    bindDynamicCardEvents(dom.agentsContent);
  }

  function renderAgentCard(agent) {
    var deployCmd = buildDeploymentCommand(agent.name);
    var domainBadgeClass = agent.domain === "brand-content" ? "domain-badge-brand" : "domain-badge-it";

    var skillsHtml = "";
    if (agent.recommended_skills && agent.recommended_skills.length > 0) {
      skillsHtml += '<div class="agent-skills-box">';
      skillsHtml += '  <span class="skills-label">Skills recomendadas:</span>';
      skillsHtml += '  <div class="skills-pill-list">';
      agent.recommended_skills.forEach(function (skill) {
        skillsHtml += '    <button type="button" class="skill-pill" data-skill="' + escapeHtml(skill) + '" title="Filtrar por esta skill o ver inventario">' + escapeHtml(skill) + '</button>';
      });
      skillsHtml += '  </div>';
      skillsHtml += '</div>';
    }

    var card =
      '<article class="agent-card" id="agent-card-' + escapeHtml(agent.id) + '">' +
      '  <div>' +
      '    <div class="agent-card-header">' +
      '      <span class="domain-badge-pill ' + domainBadgeClass + '">' + escapeHtml(agent.domain_label || agent.domain) + '</span>' +
      '      <div class="agent-badges">' +
      (agent.version ? '        <span class="badge-version">v' + escapeHtml(agent.version) + '</span>' : '') +
      '        <span class="badge-owner">' + escapeHtml(agent.owner || 'Orange') + '</span>' +
      '      </div>' +
      '    </div>' +
      '    <h3 class="agent-title">' + escapeHtml(agent.name) + '</h3>' +
      (agent.alias ? '    <div class="agent-alias"><code>@' + escapeHtml(agent.alias) + '</code></div>' : '') +
      '    <p class="agent-desc">' + escapeHtml(agent.description) + '</p>' +
      skillsHtml +
      '  </div>' +
      '  <div>' +
      '    <div class="cmd-snippet-box">' +
      '      <span class="cmd-text" title="' + escapeHtml(deployCmd) + '">' + escapeHtml(deployCmd) + '</span>' +
      '      <button type="button" class="cmd-copy-mini-btn btn-copy-cmd" data-cmd="' + escapeHtml(deployCmd) + '" title="Copiar comando CLI" aria-label="Copiar comando">' +
      '        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' +
      '      </button>' +
      '    </div>' +
      '    <div class="agent-card-actions">' +
      '      <button type="button" class="btn-primary-action btn-copy-cmd" data-cmd="' + escapeHtml(deployCmd) + '">' +
      '        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' +
      '        Copiar Comando' +
      '      </button>' +
      '      <button type="button" class="btn-secondary-action btn-view-details" data-agent-id="' + escapeHtml(agent.id) + '">' +
      '        Ficha Técnica' +
      '      </button>' +
      '    </div>' +
      '  </div>' +
      '</article>';

    return card;
  }

  function renderSkillsView() {
    var filtered = state.skills.filter(function (skill) {
      if (state.searchQuery) {
        var q = state.searchQuery;
        var matchName = (skill.name || "").toLowerCase().indexOf(q) !== -1;
        var matchDesc = (skill.description || "").toLowerCase().indexOf(q) !== -1;
        var matchPath = (skill.file_path || "").toLowerCase().indexOf(q) !== -1;
        var matchAgents = (skill.used_by_agents || []).some(function (a) {
          return a.toLowerCase().indexOf(q) !== -1;
        });
        if (!matchName && !matchDesc && !matchPath && !matchAgents) {
          return false;
        }
      }
      return true;
    });

    if (dom.resultsCount) {
      var label = filtered.length === 1 ? "1 skill encontrada" : filtered.length + " skills encontradas";
      dom.resultsCount.textContent = label;
    }

    if (filtered.length === 0) {
      dom.skillsContent.innerHTML = "";
      if (dom.emptyState) dom.emptyState.style.display = "block";
      return;
    }

    if (dom.emptyState) dom.emptyState.style.display = "none";

    var html = "";
    filtered.forEach(function (skill) {
      var usedByHtml = "";
      if (skill.used_by_agents && skill.used_by_agents.length > 0) {
        usedByHtml += '<div class="skill-agents-box">';
        usedByHtml += '  <span class="skills-label">Utilizada por agentes:</span>';
        usedByHtml += '  <div class="skills-pill-list">';
        skill.used_by_agents.forEach(function (agentName) {
          usedByHtml += '    <button type="button" class="used-by-badge btn-jump-agent" data-agent-name="' + escapeHtml(agentName) + '">' + escapeHtml(agentName) + '</button>';
        });
        usedByHtml += '  </div>';
        usedByHtml += '</div>';
      } else {
        usedByHtml += '<div class="skill-agents-box"><span class="used-by-none">Skill transversal / independiente</span></div>';
      }

      html +=
        '<article class="skill-card" id="skill-card-' + escapeHtml(skill.id) + '">' +
        '  <div>' +
        '    <div class="skill-card-header">' +
        '      <h3 class="skill-title">' + escapeHtml(skill.name) + '</h3>' +
        '      <span class="skill-type-badge">Skill</span>' +
        '    </div>' +
        '    <div class="skill-path"><code>' + escapeHtml(skill.file_path) + '</code></div>' +
        '    <p class="skill-desc">' + escapeHtml(skill.description) + '</p>' +
        usedByHtml +
        '  </div>' +
        '  <div class="agent-card-actions">' +
        '    <button type="button" class="btn-secondary-action btn-view-skill" data-skill-id="' + escapeHtml(skill.id) + '" style="width: 100%;">' +
        '      Ver Directrices SKILL.md' +
        '    </button>' +
        '  </div>' +
        '</article>';
    });

    dom.skillsContent.innerHTML = html;
    bindDynamicSkillEvents(dom.skillsContent);
  }

  // ============================================================
  // Dynamic Card Event Delegation
  // ============================================================
  function bindDynamicCardEvents(container) {
    // Copy command buttons
    container.querySelectorAll(".btn-copy-cmd").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var cmd = btn.dataset.cmd;
        if (!cmd) return;
        copyToClipboard(cmd, btn, "Comando CLI copiado");
      });
    });

    // Domain deploy buttons
    container.querySelectorAll(".domain-deploy-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var domainId = btn.dataset.domainId;
        var cmd = buildDomainDeploymentCommand(domainId);
        copyToClipboard(cmd, btn, "Comando de despliegue por dominio copiado");
      });
    });

    // View agent details sheet
    container.querySelectorAll(".btn-view-details").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var agentId = btn.dataset.agentId;
        var agent = state.agents.find(function (a) { return a.id === agentId; });
        if (agent) openAgentDetailModal(agent);
      });
    });

    // Clicking skill pills in agent cards
    container.querySelectorAll(".skill-pill").forEach(function (pill) {
      pill.addEventListener("click", function (e) {
        e.stopPropagation();
        var skillName = pill.dataset.skill;
        if (!skillName) return;
        // Switch to skills tab and filter by that skill
        switchTab("skills");
        if (dom.searchInput) {
          dom.searchInput.value = skillName;
          state.searchQuery = skillName.toLowerCase();
          if (dom.searchClearBtn) dom.searchClearBtn.style.display = "block";
        }
        render();
      });
    });
  }

  function bindDynamicSkillEvents(container) {
    // Jump to agent button
    container.querySelectorAll(".btn-jump-agent").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var agentName = btn.dataset.agentName;
        if (!agentName) return;
        switchTab("agents");
        if (dom.searchInput) {
          dom.searchInput.value = agentName;
          state.searchQuery = agentName.toLowerCase();
          if (dom.searchClearBtn) dom.searchClearBtn.style.display = "block";
        }
        render();
      });
    });

    // View skill instructions modal
    container.querySelectorAll(".btn-view-skill").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var skillId = btn.dataset.skillId;
        var skill = state.skills.find(function (s) { return s.id === skillId; });
        if (skill) openSkillDetailModal(skill);
      });
    });
  }

  // ============================================================
  // CLI Deployment Command Generator (Contract Compliant)
  // ============================================================
  function buildDeploymentCommand(agentName) {
    var target = state.targetRepo || "<TargetRepo>";
    return '.\\deploy-agents.cmd "' + target + '" -Agents "' + agentName + '"';
  }

  function buildDomainDeploymentCommand(domainId) {
    var target = state.targetRepo || "<TargetRepo>";
    return '.\\deploy-agents.cmd "' + target + '" -Domain "' + domainId + '"';
  }

  function updateConfigPreview(target) {
    if (!dom.configPreviewCmd) return;
    var previewPath = (target && target.trim()) ? target.trim() : "<TargetRepo>";
    dom.configPreviewCmd.textContent = '.\\deploy-agents.cmd "' + previewPath + '" -Agents "incident-analyzer"';
  }

  // ============================================================
  // Clipboard and Toast Notifications
  // ============================================================
  function copyToClipboard(text, triggerBtn, successMessage) {
    if (!text) return;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(function () {
          handleCopySuccess(triggerBtn, successMessage);
        })
        .catch(function () {
          fallbackExecCommand(text, triggerBtn, successMessage);
        });
    } else {
      fallbackExecCommand(text, triggerBtn, successMessage);
    }
  }

  function fallbackExecCommand(text, triggerBtn, successMessage) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      handleCopySuccess(triggerBtn, successMessage);
    } catch (e) {
      notify("No se pudo copiar automáticamente: " + text, "error");
    } finally {
      document.body.removeChild(ta);
    }
  }

  function handleCopySuccess(triggerBtn, successMessage) {
    notify(successMessage || "Copiado al portapapeles", "success");

    if (triggerBtn) {
      var origText = triggerBtn.innerHTML;
      triggerBtn.classList.add("copied");
      var hasSvg = origText.indexOf("<svg") !== -1;
      triggerBtn.innerHTML = (hasSvg ? '<span style="font-weight: bold;">✓</span> ' : '') + "Copiado";

      setTimeout(function () {
        triggerBtn.classList.remove("copied");
        triggerBtn.innerHTML = origText;
      }, 2000);
    }
  }

  function notify(message, type) {
    if (window.Toast && typeof window.Toast.show === "function") {
      window.Toast.show(message, type || "info");
    } else if (window.UIFeedback && typeof window.UIFeedback.toast === "function") {
      window.UIFeedback.toast(message, type || "info");
    } else {
      console.log("[" + (type || "INFO") + "] " + message);
    }
  }

  // ============================================================
  // Modals Management & Markdown Formatting
  // ============================================================
  function openAgentDetailModal(agent) {
    state.currentDetailItem = agent;

    if (dom.detailModalTitle) {
      dom.detailModalTitle.textContent = agent.name;
    }

    if (dom.detailModalMeta) {
      var domainBadgeClass = agent.domain === "brand-content" ? "domain-badge-brand" : "domain-badge-it";
      var metaHtml =
        '<span class="domain-badge-pill ' + domainBadgeClass + '">' + escapeHtml(agent.domain_label || agent.domain) + '</span>' +
        (agent.version ? '<span class="badge-version">v' + escapeHtml(agent.version) + '</span>' : '') +
        (agent.alias ? '<code>@' + escapeHtml(agent.alias) + '</code>' : '') +
        (agent.file_path ? '<span style="color: var(--text-light); font-family: var(--font-mono); font-size: 11px;">' + escapeHtml(agent.file_path) + '</span>' : '');
      dom.detailModalMeta.innerHTML = metaHtml;
    }

    if (dom.detailModalContent) {
      var md = agent.markdown_content || "# Sin directrices disponibles";
      dom.detailModalContent.innerHTML = renderMarkdown(md);
    }

    if (dom.modalCopyCmdBtn) {
      dom.modalCopyCmdBtn.style.display = "inline-flex";
    }

    dom.detailModal.classList.add("active");
    dom.detailModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function openSkillDetailModal(skill) {
    state.currentDetailItem = skill;

    if (dom.detailModalTitle) {
      dom.detailModalTitle.textContent = skill.name;
    }

    if (dom.detailModalMeta) {
      var metaHtml =
        '<span class="skill-type-badge">Skill Normativa</span>' +
        '<span style="color: var(--text-light); font-family: var(--font-mono); font-size: 11px;">' + escapeHtml(skill.file_path) + '</span>';
      dom.detailModalMeta.innerHTML = metaHtml;
    }

    if (dom.detailModalContent) {
      var md = skill.markdown_content || "# Sin especificaciones disponibles";
      dom.detailModalContent.innerHTML = renderMarkdown(md);
    }

    if (dom.modalCopyCmdBtn) {
      // Skills don't have direct single -Agents command; hide or show deploy instruction
      dom.modalCopyCmdBtn.style.display = "none";
    }

    dom.detailModal.classList.add("active");
    dom.detailModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeDetailModal() {
    if (!dom.detailModal) return;
    dom.detailModal.classList.remove("active");
    dom.detailModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    state.currentDetailItem = null;
  }

  function openConfigModal() {
    if (!dom.configModal) return;
    if (dom.configRepoInput) {
      dom.configRepoInput.value = state.targetRepo;
      updateConfigPreview(state.targetRepo);
    }
    dom.configModal.classList.add("active");
    dom.configModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    if (dom.configRepoInput) dom.configRepoInput.focus();
  }

  function closeConfigModal() {
    if (!dom.configModal) return;
    dom.configModal.classList.remove("active");
    dom.configModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  // ============================================================
  // Lightweight Client-Side Markdown Formatter
  // ============================================================
  function renderMarkdown(md) {
    if (!md) return "";

    var lines = md.split("\n");
    var out = [];
    var inCodeBlock = false;
    var codeLang = "";
    var codeContent = [];
    var inList = false;
    var listType = ""; // 'ul' | 'ol'
    var inTable = false;
    var tableHeaderDone = false;

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];

      // Fenced Code Blocks (```)
      if (line.trim().indexOf("```") === 0) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeLang = line.trim().slice(3).trim();
          codeContent = [];
        } else {
          inCodeBlock = false;
          out.push("<pre><code>" + escapeHtml(codeContent.join("\n")) + "</code></pre>");
          codeContent = [];
        }
        continue;
      }

      if (inCodeBlock) {
        codeContent.push(line);
        continue;
      }

      // Close open lists if an empty line or non-list element arrives
      var trimmed = line.trim();
      var isUlItem = trimmed.indexOf("- ") === 0 || trimmed.indexOf("* ") === 0;
      var isOlItem = /^\d+\.\s/.test(trimmed);

      if (inList && !isUlItem && !isOlItem) {
        out.push(listType === "ol" ? "</ol>" : "</ul>");
        inList = false;
      }

      // Table Row Detection
      var isTableRow = trimmed.indexOf("|") === 0 && trimmed.lastIndexOf("|") > 0;
      if (isTableRow) {
        if (!inTable) {
          inTable = true;
          tableHeaderDone = false;
          out.push("<table>");
        }
        // Check if it's separator row (| --- | --- |)
        if (/^\|[\s\-:|]+\|$/.test(trimmed)) {
          tableHeaderDone = true;
          continue;
        }
        var cells = trimmed.split("|").slice(1, -1);
        var tag = tableHeaderDone ? "td" : "th";
        var rowHtml = "<tr>" + cells.map(function (c) {
          return "<" + tag + ">" + formatInlineMarkdown(c.trim()) + "</" + tag + ">";
        }).join("") + "</tr>";
        out.push(rowHtml);
        continue;
      } else if (inTable) {
        out.push("</table>");
        inTable = false;
        tableHeaderDone = false;
      }

      // Empty line
      if (!trimmed) {
        continue;
      }

      // Headings
      if (trimmed.indexOf("### ") === 0) {
        out.push("<h3>" + formatInlineMarkdown(trimmed.slice(4)) + "</h3>");
        continue;
      }
      if (trimmed.indexOf("## ") === 0) {
        out.push("<h2>" + formatInlineMarkdown(trimmed.slice(3)) + "</h2>");
        continue;
      }
      if (trimmed.indexOf("# ") === 0) {
        out.push("<h1>" + formatInlineMarkdown(trimmed.slice(2)) + "</h1>");
        continue;
      }

      // Horizontal Rule
      if (trimmed === "---" || trimmed === "***" || trimmed === "___") {
        out.push("<hr style=\"border: none; border-top: 1px solid var(--border-main); margin: 20px 0;\">");
        continue;
      }

      // Blockquote
      if (trimmed.indexOf("> ") === 0) {
        out.push("<blockquote>" + formatInlineMarkdown(trimmed.slice(2)) + "</blockquote>");
        continue;
      }

      // Unordered list item
      if (isUlItem) {
        if (!inList || listType !== "ul") {
          out.push("<ul>");
          inList = true;
          listType = "ul";
        }
        out.push("<li>" + formatInlineMarkdown(trimmed.slice(2)) + "</li>");
        continue;
      }

      // Ordered list item
      if (isOlItem) {
        if (!inList || listType !== "ol") {
          out.push("<ol>");
          inList = true;
          listType = "ol";
        }
        var itemContent = trimmed.replace(/^\d+\.\s/, "");
        out.push("<li>" + formatInlineMarkdown(itemContent) + "</li>");
        continue;
      }

      // Normal paragraph
      out.push("<p>" + formatInlineMarkdown(trimmed) + "</p>");
    }

    if (inList) {
      out.push(listType === "ol" ? "</ol>" : "</ul>");
    }
    if (inTable) {
      out.push("</table>");
    }

    return out.join("\n");
  }

  function formatInlineMarkdown(text) {
    if (!text) return "";
    var res = escapeHtml(text);

    // Bold (**text**)
    res = res.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Inline code (`text`)
    res = res.replace(/`(.*?)`/g, "<code>$1</code>");

    // Links [label](url)
    res = res.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    return res;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

})();

