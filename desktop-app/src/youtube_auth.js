const fs = require('fs');

/**
 * Build arguments for youtube_auth_test.py invocation.
 * Throws if client_secrets is missing.
 */
function buildAuthTestArgs(settings, defaultCredPath, authTestScript) {
  const clientPath = settings.youtubeClientSecretsPath;
  const credPath = settings.youtubeCredentialsPath || defaultCredPath;
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
  buildAuthTestArgs,
  deleteCredentialsFile,
};
