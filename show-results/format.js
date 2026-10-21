function formatNumber(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : 'N/A';
}
module.exports = {formatNumber};
