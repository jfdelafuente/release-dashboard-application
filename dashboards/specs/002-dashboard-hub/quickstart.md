# Quick Start: Dashboard Hub Integration

## What is Dashboard Hub?

A unified entry point providing analysts with quick access to both dashboards and an at-a-glance view of key metrics (KPIs) from incident and postmortem data.

## Before Implementation

### Prerequisites
- `data/output/` directory exists with incident JSON files
- CSV-to-JSON converter is running and producing JSON files
- Both dashboards (postmortem-dashboard.html, massive-incidents-dashboard.html) are deployed

### Expected Data Source
```
data/output/
├── incident-data-2026-05-13.json
├── incident-data-2026-05-12.json
└── (more JSON files...)
```

---

## Implementation Checklist

### Step 1: Create Hub Files
- [ ] Create `dashboard-hub.html` (main page)
- [ ] Create `dashboard-hub.css` (responsive styles)
- [ ] Create `dashboard-hub.js` (data loading & rendering logic)
- [ ] Deploy in root directory (alongside existing dashboards)

### Step 2: Update Child Dashboards
- [ ] Add "Back to Dashboard Hub" link to `postmortem-dashboard.html`
- [ ] Add "Back to Dashboard Hub" link to `massive-incidents-dashboard.html`
- [ ] Test navigation from both directions

### Step 3: Test Auto-Load Feature
- [ ] Place sample JSON in `data/output/`
- [ ] Open dashboard-hub.html
- [ ] Verify latest JSON loads automatically
- [ ] Check KPI values display correctly

### Step 4: Test Error Handling
- [ ] Remove all JSON from `data/output/` → should show "no data" message
- [ ] Place corrupted JSON → should show "invalid file" message
- [ ] Verify error messages are helpful

### Step 5: Responsive Testing
- [ ] Test on desktop (1920x1080, 1366x768)
- [ ] Test on tablet (iPad width ~768px)
- [ ] Test on mobile (iPhone width ~375px)
- [ ] Verify all elements are accessible

---

## File Organization

```
release-dashboard-application/
├── dashboard-hub.html          ← NEW
├── dashboard-hub.css           ← NEW
├── dashboard-hub.js            ← NEW
├── postmortem-dashboard.html   ← UPDATE (add back link)
├── massive-incidents-dashboard.html  ← UPDATE (add back link)
├── data/
│   └── output/
│       ├── incidents-2026-05-13.json
│       └── (more JSON files)
└── specs/
    └── 002-dashboard-hub/
        ├── plan.md
        ├── spec.md
        └── quickstart.md (this file)
```

---

## Development Workflow

### 1. Create Dashboard Hub Page

```javascript
// dashboard-hub.js - Core logic

async function initHub() {
  try {
    // 1. Load latest JSON
    const incidents = await loadLatestJSON();
    
    // 2. Extract KPIs
    const kpis = extractKPIs(incidents);
    
    // 3. Render page
    renderHub(kpis);
    
  } catch (error) {
    showError(error.message);
  }
}

async function loadLatestJSON() {
  // Auto-detect and load latest file from data/output/
  // Return parsed JSON array
}

function extractKPIs(incidents) {
  return {
    massiveIncidents: [
      { label: "Total Incidents", value: incidents.length },
      { label: "Pending", value: countPending(incidents) },
      // ... more KPIs
    ],
    postmortem: [
      // ... postmortem KPIs
    ]
  };
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initHub);
```

### 2. Add Navigation Back Links

In both child dashboards, add:
```html
<nav class="breadcrumb">
  <a href="dashboard-hub.html" class="back-to-hub">← Back to Dashboard Hub</a>
</nav>
```

### 3. Style Responsive Layout

```css
/* dashboard-hub.css */

.hub-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  padding: 20px;
}

.kpi-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  transition: box-shadow 0.2s;
}

.kpi-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .hub-container {
    grid-template-columns: 1fr;
  }
}
```

---

## Testing Guide

### Functional Testing
```
✓ Open dashboard-hub.html
✓ Verify latest JSON auto-loads
✓ Check KPI values match source data
✓ Click navigation links → redirect to dashboards
✓ Click back link in dashboards → return to hub
✓ Remove JSON files → error message displays
```

### Browser Testing
```
Chrome ✓
Firefox ✓
Safari ✓
Edge ✓
Mobile Safari (iOS) ✓
Chrome Mobile (Android) ✓
```

### Performance Testing
```
Page load time: < 2 seconds
JSON parsing: < 500ms
Interactive content: < 2 seconds
```

---

## Deployment

1. **Development**:
   - Test locally with `python -m http.server 8000`
   - Verify all functionality works

2. **Staging**:
   - Deploy alongside existing dashboards
   - Test with real data from `data/output/`

3. **Production**:
   - Deploy dashboard-hub.html, css, js
   - Update existing dashboards with back links
   - Announce new unified access point to users

---

## Troubleshooting

### Issue: "No data files found"
**Solution**: Ensure CSV-to-JSON converter is running and output files exist in `data/output/`

### Issue: KPI values are incorrect
**Solution**: Check that JSON format matches expected schema; verify field names match exactly

### Issue: Back navigation doesn't work
**Solution**: Confirm back links were added to postmortem and massive-incidents dashboards

### Issue: Page doesn't load on mobile
**Solution**: Check that viewport meta tag exists; test CSS media queries in browser dev tools

---

## Success Criteria

- ✅ Dashboard Hub page loads in < 2 seconds
- ✅ Latest JSON auto-loads without user prompting
- ✅ KPI metrics display from both dashboards
- ✅ Navigation works bidirectionally
- ✅ Error messages are clear and helpful
- ✅ Responsive on all device sizes
- ✅ Zero JavaScript console errors

