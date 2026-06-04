# Feature Specification: Dashboard Auto-Refresh with Data Freshness

**Feature Branch**: `008-dashboard-auto-refresh`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "implementar auto-refresh en dashboards - polling de index.json, indicadores visuales de data freshness, sincronización automática de datos entre dashboards"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-Detect New Data in Dashboard (Priority: P1)

Dashboard automatically detects when new CSV conversion results are available on the server and updates the display without requiring the user to manually refresh the page or reopen the file. Users see their newly converted data appear in the dashboard within seconds of completion.

**Why this priority**: This is the core value proposition - automating the process of checking for new data eliminates manual refresh steps and provides instant feedback when conversions complete. Without this, users must manually reload the page.

**Independent Test**: Can be fully tested by uploading a CSV, waiting for conversion to complete, and verifying the dashboard updates automatically without page refresh. Delivers value of instant data availability.

**Acceptance Scenarios**:

1. **Given** a dashboard is open and displaying data, **When** a new JSON file becomes available on the server, **Then** the dashboard detects the change and updates with the new data within 5 seconds
2. **Given** a dashboard is open, **When** the underlying JSON file is updated with new records, **Then** the dashboard fetches and displays the updated data automatically
3. **Given** conversion is in progress, **When** conversion completes and JSON output becomes available, **Then** the dashboard immediately displays the new data without user action

---

### User Story 2 - Display Data Freshness Indicator (Priority: P2)

Users see a visual indicator showing when the dashboard data was last updated, with information about data age and refresh status. This builds confidence that they're seeing current data and provides transparency about data timeliness.

**Why this priority**: After implementing auto-refresh, users need to know if data is fresh or stale. The indicator provides transparency and helps users understand if what they're seeing is the latest available data.

**Independent Test**: Can be tested by loading a dashboard and verifying a timestamp/freshness indicator appears showing last update time, then waiting for auto-refresh to occur and confirming the indicator updates.

**Acceptance Scenarios**:

1. **Given** a dashboard displays data, **When** the page loads or data updates, **Then** a freshness indicator shows the last update timestamp (e.g., "Updated 2 minutes ago")
2. **Given** the dashboard has auto-refreshed, **When** data is less than 1 minute old, **Then** the indicator shows "Just now" or similar fresh status
3. **Given** the dashboard hasn't updated in 30+ minutes, **When** the user views the indicator, **Then** a visual warning or distinct style indicates stale data
4. **Given** auto-refresh is in progress, **When** the dashboard is fetching new data, **Then** the indicator shows a loading state (e.g., "Refreshing...")

---

### User Story 3 - Sync Data Across Multiple Dashboards (Priority: P2)

When a user has multiple dashboards open (e.g., Massive Incidents and Postmortem dashboards), they automatically stay in sync. When one dashboard receives new data, the other dashboard also updates to reflect the same dataset changes.

**Why this priority**: Users often work with multiple dashboards simultaneously. Keeping them in sync ensures consistency and prevents confusion from seeing conflicting data across browser tabs.

**Independent Test**: Can be tested by opening two dashboards side-by-side, uploading new data, and verifying both dashboards update with the same new data automatically within the same time window.

**Acceptance Scenarios**:

1. **Given** two dashboards are open displaying the same dataset, **When** new data is available, **Then** both dashboards update to display the same new data
2. **Given** one dashboard auto-refreshes with new data, **When** the other dashboard is currently polling, **Then** the second dashboard receives and displays the same data within the next refresh interval
3. **Given** dashboards are open on different browser tabs/windows, **When** new data becomes available, **Then** all tabs/windows displaying dashboards receive the update

---

### Edge Cases

- What happens when the server is unreachable during a polling cycle?
- How does the system handle when a JSON file is deleted or moved?
- What happens if two uploads complete simultaneously - does the dashboard handle rapid updates?
- How does the system behave if the user is offline and then comes back online?
- What happens if auto-refresh interval is shorter than the time needed to fetch data?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard MUST poll the index.json file at configurable intervals (default: 10 seconds) to detect available datasets
- **FR-002**: When new data is detected in index.json, dashboard MUST automatically fetch the corresponding JSON file and update the display
- **FR-003**: Dashboard MUST display a data freshness indicator showing the last update timestamp
- **FR-004**: Dashboard MUST provide visual feedback during the refresh process (loading indicator)
- **FR-005**: Dashboard MUST handle network errors gracefully and retry polling on connection loss
- **FR-006**: Dashboard MUST persist polling state across page navigations (continues polling if user navigates away and back)
- **FR-007**: Dashboard MUST allow users to manually trigger a refresh independent of the auto-refresh schedule
- **FR-008**: Dashboard MUST be able to be disabled by the user if they prefer manual refresh only
- **FR-009**: Multiple dashboard tabs/windows MUST synchronize their refresh state using browser storage (SharedWorker or similar)
- **FR-010**: Dashboard MUST detect when the underlying data structure changes and handle schema updates gracefully
- **FR-011**: Dashboard MUST not block user interactions while polling and refreshing data in the background

### Key Entities

- **Index Metadata**: Contains list of available datasets with last modified timestamp and file paths
- **Dashboard State**: Current display state, selected filters, active dataset reference
- **Refresh Event**: Notification sent when new data becomes available, triggering other tabs/dashboards to update
- **Freshness Data**: Timestamp and status of last successful data update

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Auto-refresh detects and displays new data within 5 seconds of file availability on server
- **SC-002**: Dashboard remains fully responsive to user interactions (filtering, sorting) while polling runs in background
- **SC-003**: Refresh operations complete in under 2 seconds for typical dataset sizes (1000-10000 records)
- **SC-004**: Multiple dashboards (2-3 tabs) remain synchronized with data updates within 1 refresh cycle
- **SC-005**: Network failures don't cause dashboard to hang or display stale data indefinitely - recovery occurs on next successful poll
- **SC-006**: 95% of scheduled refresh cycles complete successfully under normal network conditions
- **SC-007**: Users understand data freshness within 3 seconds of looking at the dashboard (clear visual indicator)

## Assumptions

- Users have stable internet connectivity for polling to work effectively
- The index.json file will be updated by the CSV conversion service when new data becomes available
- The freshness indicator is for informational purposes only - users don't require guarantees about exact data recency
- Multiple dashboards will be accessed in the same browser session (not across different browsers/devices)
- The polling interval of 10 seconds is appropriate for the use case - users don't need sub-second refresh rates
- The existing dashboard HTML structure will remain compatible with auto-refresh implementation
- JSON files on server are stable once written (no partial writes or concurrent modifications)
- Session storage or localStorage is available and usable for cross-tab synchronization
