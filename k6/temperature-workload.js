import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Send authenticated, real application operations to the real microservices:
// Enter Data -> Auth (PBKDF2 login) -> MySQL -> Analytics -> MongoDB.
// The auth microservice is the CPU-driven HPA target.
const profile = __ENV.SCENARIO || 'low';
const base = (__ENV.BASE_URL || 'http://localhost:5000').replace(/\/$/, '');
const password = __ENV.DEMO_PASSWORD || '';
const username = __ENV.DEMO_USERNAME || 'student';
export const transaction_failure_rate = new Rate('transaction_failure_rate');
export const login_seconds = new Trend('login_seconds', true);
export const submit_seconds = new Trend('submit_seconds', true);

const scenarios = {
  low: { executor: 'constant-vus', vus: 1, duration: '3m' },
  increasing: {
    executor: 'ramping-vus', startVUs: 1,
    stages: [
      { duration: '2m', target: 12 },
      { duration: '3m', target: 36 },
      { duration: '2m', target: 36 },
    ],
    gracefulRampDown: '30s',
  },
  decreasing: { executor: 'constant-vus', vus: 1, duration: '7m' },
};
if (!(profile in scenarios)) throw new Error('Unknown SCENARIO ' + profile);
export const options = {
  scenarios: { [profile]: scenarios[profile] },
  discardResponseBodies: false,
  thresholds: {}, // Always save observations even when the system struggles.
};

export default function () {
  if (!password) throw new Error('Set DEMO_PASSWORD in your environment; do not commit it.');
  const login = http.post(`${base}/login`,
    { username, password },
    { redirects: 5, timeout: '30s', tags: { phase: profile, operation: 'login' } });
  login_seconds.add(login.timings.duration / 1000);
  const matched = /name="csrf"\s+value="([^"]+)"/.exec(login.body || '');
  const loginOk = check(login, { 'authenticated entry page': r =>
    r.status === 200 && (r.body || '').includes('Temperature readings') });
  if (!loginOk || !matched) {
    transaction_failure_rate.add(true);
    sleep(1);
    return;
  }
  const value = -10 + Math.floor(Math.random() * 75);
  const submit = http.post(`${base}/submit`,
    { value: String(value), csrf: matched[1] },
    { redirects: 5, timeout: '45s', tags: { phase: profile, operation: 'submit' } });
  submit_seconds.add(submit.timings.duration / 1000);
  const submitOk = check(submit, { 'DB write and analytics refresh': r =>
    r.status === 200 && (r.body || '').includes('Reading saved and analytics refreshed.') });
  transaction_failure_rate.add(!submitOk);
  // At the baseline/recovery, long sleeps help reveal whether auth scales in.
  sleep(profile === 'increasing' ? 0.2 : 2);
}
