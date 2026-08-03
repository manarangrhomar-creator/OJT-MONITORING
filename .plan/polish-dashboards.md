# Polish Plan — OJT Monitoring System Dashboards

## Status: PENDING APPROVAL
## Last Updated: 2026-08-03

---

## Triage Summary

| Priority | Finding | Impact | Effort |
|----------|---------|--------|--------|
| CRITICAL | No modal focus traps | Keyboard users cannot use modals | 2h |
| CRITICAL | No `prefers-reduced-motion` | Vestibular disorder users harmed | 1h |
| HIGH | Global scrollbar hiding | Accessibility violation | 30min |
| HIGH | Duplicate CSS across 3 files | Maintenance burden, drift risk | 4h |
| HIGH | Tab ARIA patterns missing | Screen reader users lost | 1h |
| MEDIUM | Primary color drift | Inconsistent branding | 30min |
| MEDIUM | Skeleton loaders missing | No loading feedback | 2h |
| MEDIUM | Stats card uniformity | No focal hierarchy | 1h |
| LOW | Button icons missing | Minor visual polish | 30min |
| LOW | Transition standardization | Minor visual polish | 1h |

---

## Execution Plan

### Step 1: Design Tokens (30min)
**Create:** `static/css/design-tokens.css`

Canonical values (resolved from coordinator/admin majority):
```css
:root {
  --primary: #11693A;
  --primary-dark: #0e5630;
  --primary-light: #E8F5EE;
  --gold: #C8A44A;
  --gold-light: #E8D5A0;
  --bg-body: #F4F5F9;
  --card-bg: #FFFFFF;
  --card-bg-secondary: #F9FAFB;
  --card-border: #E8E9F0;
  --fg: #1A1A2E;
  --fg-muted: #7C7C8D;
  --fg-dim: #9CA3AF;
  --success: #10B981;
  --danger: #EF4444;
  --info: #3B82F6;
  --radius-sm: 0.75rem;
  --radius-md: 1rem;
  --radius-lg: 1.5rem;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.03);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.03);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.06), 0 16px 40px rgba(0,0,0,0.04);
  --shadow-hover: 0 4px 12px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.03);
  --font-display: 'Inter', sans-serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}
```

### Step 2: Global Scrollbar Fix (15min)
**Edit:** `coordinator_dashboard.html`
- Remove: `* { scrollbar-width: none; -ms-overflow-style: none; }`
- Add scoped hiding only to tab content containers

### Step 3: Modal Focus Traps (2h)
**Files:** All 3 dashboards

Each modal gets:
1. `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to title
2. Focus trap: Tab cycles through focusable elements within modal
3. ESC handler: closes modal, returns focus to trigger
4. `aria-describedby` for error message containers

Implementation pattern:
```javascript
function trapFocus(modal) {
  const focusable = modal.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  
  modal.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    if (e.key === 'Escape') {
      closeModal(modal);
    }
  });
  
  first.focus();
}
```

### Step 4: Tab ARIA Patterns (1h)
**Files:** All 3 dashboards

Add to each tab:
```html
<div role="tablist" aria-label="Section navigation">
  <button role="tab" id="tab-dashboard" aria-selected="true" aria-controls="panel-dashboard" tabindex="0">
    Dashboard
  </button>
  <button role="tab" id="tab-attendance" aria-selected="false" aria-controls="panel-attendance" tabindex="-1">
    Attendance
  </button>
</div>
<div role="tabpanel" id="panel-dashboard" aria-labelledby="tab-dashboard">
  ...
</div>
```

JavaScript update:
```javascript
function switchTab(tab) {
  // Update aria-selected on all tabs
  document.querySelectorAll('[role="tab"]').forEach(t => {
    t.setAttribute('aria-selected', 'false');
    t.setAttribute('tabindex', '-1');
  });
  
  // Activate selected tab
  tab.setAttribute('aria-selected', 'true');
  tab.setAttribute('tabindex', '0');
  tab.focus();
  
  // Show corresponding panel
  const panelId = tab.getAttribute('aria-controls');
  document.querySelectorAll('[role="tabpanel"]').forEach(p => {
    p.hidden = true;
  });
  document.getElementById(panelId).hidden = false;
}
```

### Step 5: Skeleton Loaders (2h)
**Files:** All 3 dashboards

Add skeleton templates for each tab:
```html
<div id="skeleton-attendance" class="hidden">
  <div class="space-y-3">
    <div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
    <div class="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div>
    <div class="h-32 bg-gray-200 rounded animate-pulse"></div>
  </div>
</div>
```

Show skeleton on tab switch, hide when content loads.

### Step 6: Motion Preferences (1h)
**Files:** All 3 dashboards

Add at end of `<style>`:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .animate-in > * { animation: none !important; }
  .loader-progress-bar { animation: none !important; }
}
```

### Step 7: Visual Polish (1.5h)
**Files:** All 3 dashboards

1. **Button icons**: Add ✓/✗ to approve/reject buttons
2. **Stats cards**: Vary size classes for focal hierarchy
3. **Mobile modal**: Add `max-h-[90vh] overflow-y-auto`
4. **Transition standardization**: All interactive elements get `transition: all 0.2s ease`

### Step 8: Verify (30min)
- [ ] Run detector on all 3 dashboards
- [ ] Browser test at 1440px, 768px, 375px widths
- [ ] Keyboard navigation: Tab through all elements
- [ ] Screen reader test: NVDA on Windows
- [ ] Reduced motion: Enable `prefers-reduced-motion` in browser

---

## Decision Points

1. **Primary color**: `#11693A` (coordinator/admin majority) — default unless you say otherwise
2. **Background**: `#F4F5F9` (coordinator/admin majority) — default unless you say otherwise
3. **Scope**: Full polish pass (all steps) or MVP (steps 1-4 only)?

---

## Risks

| Risk | Mitigation |
|------|------------|
| Breaking existing JS | Test each dashboard after each step |
| Color change affects student branding | Student dashboard may keep `#0D7A42` if intentional |
| Modal focus trap breaks existing flow | Test with keyboard before/after |
