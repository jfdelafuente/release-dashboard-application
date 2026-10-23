// Unit tests for parseIncidentDate function and weekdayBreakdown logic
const assert = require('assert');

function parseIncidentDate(s) {
  if (!s) return null;
  const str = String(s).trim();
  if (!str) return null;

  // Format 1: DD/MM/YYYY or DD/MM/YY (or with '-' / '.') with optional H:MM[:SS]
  const m = str.match(/^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
  if (m) {
    let yr = +m[3];
    if (yr < 100) yr += 2000;
    const d = new Date(yr, +m[2] - 1, +m[1], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0));
    return isNaN(d.getTime()) ? null : d;
  }

  // Format 2: ISO YYYY-MM-DD or YYYY/MM/DD with optional [T\s]H:MM[:SS]
  const mIso = str.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})(?:[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
  if (mIso) {
    const d = new Date(+mIso[1], +mIso[2] - 1, +mIso[3], +(mIso[4] || 0), +(mIso[5] || 0), +(mIso[6] || 0));
    return isNaN(d.getTime()) ? null : d;
  }

  return null;
}

const WEEKDAY_LABELS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
function areaOf(group) { return String(group || '').startsWith('IT') ? 'IT' : 'RED'; }

function weekdayBreakdown(incidents) {
  const inc = incidents || [];
  return WEEKDAY_LABELS.map((label, idx) => {
    const jsDay = (idx + 1) % 7;
    const day = inc.filter(i => { const d = parseIncidentDate(i.date); return d && d.getDay() === jsDay; });
    const it = day.filter(i => areaOf(i.group) === 'IT').length;
    return { label, it, red: day.length - it, total: day.length };
  });
}

console.log('Running parseIncidentDate tests...');

// 1. Standard DD/MM/YYYY with time
const d1 = parseIncidentDate('20/10/2026 11:30');
assert(d1 !== null);
assert.strictEqual(d1.getFullYear(), 2026);
assert.strictEqual(d1.getMonth(), 9); // October
assert.strictEqual(d1.getDate(), 20);
assert.strictEqual(d1.getHours(), 11);
assert.strictEqual(d1.getMinutes(), 30);

// 2. 2-digit year DD/MM/YY with time (bug case reported in W43)
const d2 = parseIncidentDate('21/10/26 9:39');
assert(d2 !== null);
assert.strictEqual(d2.getFullYear(), 2026);
assert.strictEqual(d2.getMonth(), 9);
assert.strictEqual(d2.getDate(), 21);
assert.strictEqual(d2.getHours(), 9);
assert.strictEqual(d2.getMinutes(), 39);
assert.strictEqual(d2.getDay(), 3); // Wednesday

const d3 = parseIncidentDate('18/10/26 13:02');
assert(d3 !== null);
assert.strictEqual(d3.getFullYear(), 2026);
assert.strictEqual(d3.getMonth(), 9);
assert.strictEqual(d3.getDate(), 18);
assert.strictEqual(d3.getDay(), 0); // Sunday

// 3. Date only without time
const d4 = parseIncidentDate('20/10/2026');
assert(d4 !== null);
assert.strictEqual(d4.getFullYear(), 2026);
assert.strictEqual(d4.getDate(), 20);

// 4. Dash separated dates
const d5 = parseIncidentDate('20-10-2026 11:30');
assert(d5 !== null);
assert.strictEqual(d5.getFullYear(), 2026);

// 5. ISO format
const d6 = parseIncidentDate('2026-10-20 11:30');
assert(d6 !== null);
assert.strictEqual(d6.getFullYear(), 2026);

// 6. Whitespace handling
const d7 = parseIncidentDate('  21/10/26 9:39   ');
assert(d7 !== null);
assert.strictEqual(d7.getFullYear(), 2026);

// 7. Invalid inputs
assert.strictEqual(parseIncidentDate(''), null);
assert.strictEqual(parseIncidentDate(null), null);
assert.strictEqual(parseIncidentDate(undefined), null);
assert.strictEqual(parseIncidentDate('invalid date'), null);

// 8. Test W43 scenario: all 5 incidents must be parsed and counted
const w43Incidents = [
  { ticket: 'INC000004162231', date: '20/10/2026 11:30', group: 'IT MM' },
  { ticket: '2610M12155', date: '21/10/2026 12:44', group: 'RED >5.000 clientes' },
  { ticket: '2610M04069', date: '21/10/26 9:39', group: 'RED >5.000 clientes' },
  { ticket: '2610M11710', date: '20/10/2026 07:45', group: 'RED >5.000 clientes' },
  { ticket: '2610K90032', date: '18/10/26 13:02', group: 'RED >5.000 clientes' },
];

const breakdown = weekdayBreakdown(w43Incidents);
const totalParsed = breakdown.reduce((acc, cur) => acc + cur.total, 0);

assert.strictEqual(totalParsed, 5, `Expected 5 incidents in breakdown, got ${totalParsed}`);

const mar = breakdown.find(b => b.label === 'Mar');
assert.strictEqual(mar.it, 1);
assert.strictEqual(mar.red, 1);
assert.strictEqual(mar.total, 2);

const mie = breakdown.find(b => b.label === 'Mié');
assert.strictEqual(mie.it, 0);
assert.strictEqual(mie.red, 2);
assert.strictEqual(mie.total, 2);

const dom = breakdown.find(b => b.label === 'Dom');
assert.strictEqual(dom.it, 0);
assert.strictEqual(dom.red, 1);
assert.strictEqual(dom.total, 1);

console.log('All parseIncidentDate tests passed successfully! Total incidents verified = 5.');

