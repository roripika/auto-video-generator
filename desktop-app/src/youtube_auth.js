const fs = require('fs');
const os = require('os');
const path = require('path');

function expandTilde(p) {
  if (!p) return p;
  if (p === '~') return os.homedir();
  if (p.startsWith('~/')) {
    return path.join(os.homedir(), p.slice(2));
  }
  return p;
}

/**
 * Build arguments for youtube_auth_test.py invocation.
 * Throws if client_secrets is missing.
 */
function buildAuthTestArgs(settings, defaultCredPath, authTestScript) {
  const clientPath = expandTilde(settings.youtubeClientSecretsPath);
  const credPath = expandTilde(settings.youtubeCredentialsPath) || defaultCredPath;
  if (!clientPath || !fs.existsSync(clientPath)) {
    throw new Error('client_secrets.json のパスが設定されていません。');
  }
  const args = [
    authTestScript,
    '--client-secrets',
    clientPath,
    '--credentials',
    credPath,
  ];
  return { args, clientPath, credPath };
}

/**
 * Delete credential file if present.
 */
function deleteCredentialsFile(credPath) {
  credPath = expandTilde(credPath);
  if (!credPath) return { ok: true, removed: false };
  try {
    if (fs.existsSync(credPath)) {
      fs.unlinkSync(credPath);
      return { ok: true, removed: true, path: credPath };
    }
    return { ok: true, removed: false, path: credPath };
  } catch (err) {
    throw new Error(`トークン削除に失敗しました: ${err.message || err}`);
  }
}

module.exports = {
  expandTilde,
  buildAuthTestArgs,
  deleteCredentialsFile,
};
