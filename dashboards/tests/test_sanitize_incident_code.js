// Unit test for sanitizeIncidentCode function
const assert = require('assert');

function sanitizeIncidentCode(input) {
    if (!input || typeof input !== 'string') return '';
    const clean = input.trim().toUpperCase();
    if (!clean) return '';

    // Si contiene solo dígitos (ej. "4141215"), añadir prefijo INC y ceros hasta 12 dígitos
    if (/^\d+$/.test(clean)) {
        return 'INC' + clean.padStart(12, '0');
    }

    // Si empieza por INC seguido de dígitos (ej. "INC4141215"), rellenar ceros hasta 12 dígitos
    const incMatch = clean.match(/^INC(\d+)$/);
    if (incMatch) {
        const digits = incMatch[1];
        if (digits.length < 12) {
            return 'INC' + digits.padStart(12, '0');
        }
    }

    return clean;
}

console.log('Running sanitizeIncidentCode tests...');

// 1. Standard format
assert.strictEqual(sanitizeIncidentCode('INC000004141215'), 'INC000004141215');

// 2. Trimming whitespace
assert.strictEqual(sanitizeIncidentCode('  INC000004141215  '), 'INC000004141215');

// 3. Lowercase conversion
assert.strictEqual(sanitizeIncidentCode('inc000004141215'), 'INC000004141215');

// 4. Purely numeric input with 0-padding up to 12 digits
assert.strictEqual(sanitizeIncidentCode('4141215'), 'INC000004141215');
assert.strictEqual(sanitizeIncidentCode('  4141215  '), 'INC000004141215');

// 5. INC prefix with fewer than 12 digits
assert.strictEqual(sanitizeIncidentCode('INC4141215'), 'INC000004141215');
assert.strictEqual(sanitizeIncidentCode('inc4141215'), 'INC000004141215');

// 6. Empty / Invalid inputs
assert.strictEqual(sanitizeIncidentCode(''), '');
assert.strictEqual(sanitizeIncidentCode('   '), '');
assert.strictEqual(sanitizeIncidentCode(null), '');
assert.strictEqual(sanitizeIncidentCode(undefined), '');

// 7. Other custom code types
assert.strictEqual(sanitizeIncidentCode('PRB00001234'), 'PRB00001234');

console.log('✓ All 12 test assertions passed successfully!');
