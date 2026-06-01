# Contract: Dashboard Hub User Interface

## Purpose
Defines the expected structure, behavior, and appearance of the Dashboard Hub page and its integration with child dashboards.

---

## HTML Structure Contract

### Dashboard Hub Page (dashboard-hub.html)

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Dashboard Hub</title>
    <link rel="stylesheet" href="dashboard-hub.css">
  </head>
  <body>
    <nav class="hub-navigation">
      <!-- Navigation items with links to dashboards -->
      <a href="postmortem-dashboard.html" class="nav-item">Postmortem Dashboard</a>
      <a href="massive-incidents-dashboard.html" class="nav-item">Massive Incidents Dashboard</a>
    </nav>
    
    <main class="hub-container">
      <header class="hub-header">
        <h1>System Status Dashboard Hub</h1>
      </header>
      
      <div class="kpi-summary">
        <!-- KPI cards for both dashboards -->
        <section class="dashboard-kpis massive-incidents">
          <h2>Massive Incidents</h2>
          <!-- KPI cards here -->
        </section>
        
        <section class="dashboard-kpis postmortem">
          <h2>Postmortem Dashboard</h2>
          <!-- KPI cards here -->
        </section>
      </div>
      
      <footer class="hub-footer">
        <p>Data last updated: <span id="last-updated">--:--</span></p>
      </footer>
    </main>
    
    <script src="dashboard-hub.js"></script>
  </body>
</html>
```

### KPI Card Component

```html
<div class="kpi-card" data-metric="[metric-id]">
  <div class="kpi-header">
    <h3 class="kpi-label">[Label]</h3>
  </div>
  <div class="kpi-content">
    <div class="kpi-value">[Value]</div>
    <div class="kpi-trend [direction]">
      <span class="trend-icon">[↑/↓/→]</span>
      <span class="trend-percentage">[±X.X%]</span>
    </div>
  </div>
  <a href="[target-dashboard]" class="kpi-link">View Details</a>
</div>
```

---

## JavaScript API Contract

### Core Functions

#### `initHub()`
Initializes the Dashboard Hub on page load.

```javascript
// Execution flow
initHub() {
  1. Fetch file list from data/output/
  2. Find latest JSON file (by timestamp)
  3. Load and parse JSON
  4. Extract KPI metrics
  5. Render components
  6. Update last-updated timestamp
  7. Handle errors gracefully
}
```

#### `loadLatestJSON()`
Loads the most recent JSON file from `data/output/`.

```javascript
async loadLatestJSON() → Promise<Array>
  // Returns: Array of incident records
  // Throws: Error if no files found or parsing fails
```

#### `extractKPIs(incidentData)`
Extracts KPI metrics from incident data.

```javascript
extractKPIs(data: Array) → Object
  // Returns: { massiveIncidents: [KPICard], postmortem: [KPICard] }
```

#### `renderHub(kpiData)`
Renders the complete hub with KPI cards.

```javascript
renderHub(data: Object) → void
  // Renders DOM elements and applies styling
```

---

## Child Dashboard Integration Contract

### Back-to-Hub Navigation

Both `postmortem-dashboard.html` and `massive-incidents-dashboard.html` must include:

```html
<nav class="breadcrumb">
  <a href="dashboard-hub.html" class="breadcrumb-item back-to-hub">
    ← Back to Dashboard Hub
  </a>
</nav>
```

---

## CSS Classes Contract

### Layout Classes
- `.hub-container`: Main content container
- `.hub-header`: Header section
- `.hub-navigation`: Navigation bar
- `.kpi-summary`: Grid container for KPI sections
- `.dashboard-kpis`: Section for dashboard-specific KPIs
- `.kpi-card`: Individual KPI card
- `.hub-footer`: Footer with timestamps

### State Classes
- `.loading`: Applied during data fetch
- `.error`: Applied when error state
- `.success`: Applied when data loaded
- `.trend-up`: For positive trends
- `.trend-down`: For negative trends
- `.trend-neutral`: For stable trends

### Responsive Classes
- `.mobile`: Applied on small screens
- `.tablet`: Applied on medium screens
- `.desktop`: Applied on large screens

---

## Error Contract

### Error States

When errors occur, display user-friendly messages:

```javascript
ErrorScenarios:
  1. No JSON files in data/output/
     → "No data files found. Please upload CSV files to data/output/"
  
  2. Corrupted/invalid JSON
     → "Data file is corrupted. Please check file format."
  
  3. Directory access denied
     → "Unable to access data directory. Check permissions."
  
  4. Browser compatibility
     → "Your browser is not supported. Please use Chrome, Firefox, Safari, or Edge."
```

---

## Performance Contract

### Load Time Requirements
- Full page load: < 2 seconds
- JSON parsing: < 500ms
- KPI rendering: < 100ms
- Total interactive: < 2 seconds

### Memory Requirements
- JSON data: < 5MB in memory
- DOM elements: < 100 KPI cards
- No memory leaks on navigation

---

## Browser Compatibility

**Supported**:
- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)

**Not Supported**:
- IE 11 and earlier
- Mobile browsers < iOS 12, < Android 5

