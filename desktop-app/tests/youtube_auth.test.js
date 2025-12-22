// Unit tests for YouTube auth helpers (no Electron runtime required)
// Run with: node --test desktop-app/tests/youtube_auth.test.js

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const { buildAuthTestArgs, deleteCredentialsFile } = require('../src/youtube_auth');

test('buildAuthTestArgs throws when client_secrets is missing', () => {
  const tmpCred = path.join(os.tmpdir(), 'yt_creds_test.pickle');
  const settings = { youtubeClientSecretsPath: '', youtubeCredentialsPath: tmpCred };
  assert.throws(() => buildAuthTestArgs(settings, tmpCred, '/tmp/auth_test.py'));
});

test('buildAuthTestArgs returns args when files exist', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'yt_auth_args_'));
  const secretsPath = path.join(tmpDir, 'client_secrets.json');
  fs.writeFileSync(secretsPath, '{"installed":{}}');
  const defaultCred = path.join(tmpDir, 'creds.pickle');
  const settings = { youtubeClientSecretsPath: secretsPath, youtubeCredentialsPath: '' };
  const { args, credPath } = buildAuthTestArgs(settings, defaultCred, '/tmp/auth_test.py');
  assert.strictEqual(credPath, defaultCred);
  assert.deepStrictEqual(args, [
    '/tmp/auth_test.py',
    '--client-secrets',
    secretsPath,
    '--credentials',
    defaultCred,
  ]);
});

test('deleteCredentialsFile removes existing file and reports removed=true', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'yt_auth_delete_'));
  const cred = path.join(tmp, 'creds.pickle');
  fs.writeFileSync(cred, 'dummy');
  const res = deleteCredentialsFile(cred);
  assert.strictEqual(res.removed, true);
  assert.strictEqual(fs.existsSync(cred), false);
});

test('deleteCredentialsFile reports removed=false when file missing', () => {
  const cred = path.join(os.tmpdir(), 'yt_missing_creds.pickle');
  if (fs.existsSync(cred)) fs.unlinkSync(cred);
  const res = deleteCredentialsFile(cred);
  assert.strictEqual(res.removed, false);
});
