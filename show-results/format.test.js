const test = require('node:test');
const assert = require('node:assert/strict');
const {formatNumber} = require('./format');
test('formats numeric aggregates', () => assert.equal(formatNumber(30), '30.00'));
test('shows N/A for missing aggregates', () => assert.equal(formatNumber(null), 'N/A'));
