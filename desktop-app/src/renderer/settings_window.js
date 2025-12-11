(() => {
  const settingsProviderSelect = document.getElementById('settingsProvider');
  const settingsApiKeyInput = document.getElementById('settingsApiKey');
  const settingsBaseUrlInput = document.getElementById('settingsBaseUrl');
  const settingsModelInput = document.getElementById('settingsModel');
  const settingsProviderOrder = document.getElementById('settingsProviderOrder');
  const settingsMaxResults = document.getElementById('settingsMaxResults');
  const settingsPexelsKeyInput = document.getElementById('settingsPexelsKey');
  const settingsPixabayKeyInput = document.getElementById('settingsPixabayKey');
  const settingsStabilityKeyInput = document.getElementById('settingsStabilityKey');
  const settingsYoutubeKeyInput = document.getElementById('settingsYoutubeKey');
  const settingsYoutubeClientSecretsInput = document.getElementById('settingsYoutubeClientSecrets');
  const settingsYoutubeCredentialsInput = document.getElementById('settingsYoutubeCredentials');
  const settingsYoutubeClientSecretsBrowseBtn = document.getElementById('settingsYoutubeClientSecretsBrowse');
  const settingsYoutubeCredentialsBrowseBtn = document.getElementById('settingsYoutubeCredentialsBrowse');
  const settingsYoutubePrivacySelect = document.getElementById('settingsYoutubePrivacy');
  const settingsBgmDirInput = document.getElementById('settingsBgmDir');
  const settingsYoutubeForceInput = document.getElementById('settingsYoutubeForce');
  const YT_CREDENTIALS_DEFAULT = '~/.config/auto-video-generator/youtube_credentials.pickle';
  const settingsYoutubeAuthTestBtn = document.getElementById('settingsYoutubeAuthTestBtn');
  const providerHintEl = document.getElementById('providerHint');
  const settingsSaveBtn = document.getElementById('settingsSaveBtn');
  const externalLinks = document.querySelectorAll('[data-external-link="true"]');
  let providerConfigs = {};
  let activeProvider = 'openai';

  externalLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const href = link.getAttribute('href');
      if (href && window.externalLinks?.open) {
        window.externalLinks.open(href);
      }
    });
  });

  const PROVIDER_PRESETS = {
    openai: {
      label: 'OpenAI',
      baseUrl: 'https://api.openai.com/v1',
      model: 'gpt-4o-mini',
      env: 'OPENAI_API_KEY',
    },
    anthropic: {
      label: 'Anthropic Claude',
      baseUrl: 'https://api.anthropic.com/v1/messages',
      model: 'claude-3-sonnet-20240229',
      env: 'ANTHROPIC_API_KEY',
    },
    gemini: {
      label: 'Google Gemini',
      baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
      model: 'gemini-2.5-flash',
      env: 'GEMINI_API_KEY / GOOGLE_API_KEY',
    },
  };

  function populateProviderOptions() {
    settingsProviderSelect.innerHTML = '';
    Object.entries(PROVIDER_PRESETS).forEach(([value, meta]) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = meta.label;
      settingsProviderSelect.appendChild(option);
    });
  }

  function providerRecommendation(value) {
    switch (value) {
      case 'openai':
        return '推奨モデル: gpt-4o（標準）。ミニ版は出力が途中で切れやすいので注意。';
      case 'anthropic':
        return '推奨モデル: claude-3-sonnet または haiku（軽量）。';
      case 'gemini':
        return '推奨モデル: gemini-1.5-pro（高精度）または gemini-1.5-flash（高速）。';
      default:
        return '';
    }
  }

  function updateProviderHint() {
    const preset = PROVIDER_PRESETS[settingsProviderSelect.value];
    if (!preset) {
      providerHintEl.textContent = '';
      return;
    }
    providerHintEl.innerHTML = `プロバイダ: ${preset.label}（APIキー: ${preset.env}）<br>${providerRecommendation(settingsProviderSelect.value)}`;
  }

  function cloneProviderConfigs(source) {
    return JSON.parse(JSON.stringify(source || {}));
  }

  function ensureProviderConfig(key) {
    if (!providerConfigs[key]) {
      providerConfigs[key] = {
        apiKey: '',
        baseUrl: PROVIDER_PRESETS[key]?.baseUrl || '',
        model: PROVIDER_PRESETS[key]?.model || '',
      };
    }
    return providerConfigs[key];
  }

  function applyProviderFields(key) {
    const config = ensureProviderConfig(key);
    settingsApiKeyInput.value = config.apiKey || '';
    settingsBaseUrlInput.value = config.baseUrl || PROVIDER_PRESETS[key]?.baseUrl || '';
    settingsModelInput.value = config.model || PROVIDER_PRESETS[key]?.model || '';
  }

  function persistProviderFields() {
    const config = ensureProviderConfig(activeProvider);
    config.apiKey = settingsApiKeyInput.value.trim();
    config.baseUrl = settingsBaseUrlInput.value.trim() || config.baseUrl;
    config.model = settingsModelInput.value.trim() || config.model;
  }

  async function loadSettings() {
    populateProviderOptions();
    const settings = await window.aiSettings.load();
    providerConfigs = cloneProviderConfigs(settings.providers);
    activeProvider =
      settings.activeProvider && PROVIDER_PRESETS[settings.activeProvider] ? settings.activeProvider : 'openai';
    settingsProviderSelect.value = activeProvider;
    applyProviderFields(activeProvider);
    settingsProviderOrder.value = settings.assetProviderOrder || 'pexels,pixabay';
    settingsMaxResults.value = settings.assetMaxResults || 5;
    settingsPexelsKeyInput.value = settings.pexelsApiKey || '';
    settingsPixabayKeyInput.value = settings.pixabayApiKey || '';
    settingsStabilityKeyInput.value = settings.stabilityApiKey || '';
    settingsYoutubeKeyInput.value = settings.youtubeApiKey || '';
    settingsYoutubeClientSecretsInput.value = settings.youtubeClientSecretsPath || '';
    settingsYoutubeCredentialsInput.value = settings.youtubeCredentialsPath || YT_CREDENTIALS_DEFAULT;
    if (settingsYoutubePrivacySelect) {
      settingsYoutubePrivacySelect.value = settings.youtubePrivacyStatus || 'private';
    }
    settingsBgmDirInput.value = settings.bgmDirectory || 'assets/bgm';
    settingsYoutubeForceInput.value = settings.youtubeForceVideo || '';
    settingsBaseUrlInput.dataset.dirty = 'false';
    settingsModelInput.dataset.dirty = 'false';
    updateProviderHint();
  }

  function handleProviderChanged() {
    persistProviderFields();
    const nextKey = settingsProviderSelect.value;
    if (!PROVIDER_PRESETS[nextKey]) return;
    activeProvider = nextKey;
    applyProviderFields(activeProvider);
    updateProviderHint();
  }

  async function handleSave() {
    persistProviderFields();
    const payload = {
      activeProvider,
      providers: providerConfigs,
      assetProviderOrder: settingsProviderOrder.value,
      assetMaxResults: Number(settingsMaxResults.value) || 5,
      pexelsApiKey: settingsPexelsKeyInput.value.trim(),
      pixabayApiKey: settingsPixabayKeyInput.value.trim(),
      stabilityApiKey: settingsStabilityKeyInput.value.trim(),
      youtubeApiKey: settingsYoutubeKeyInput.value.trim(),
      youtubeClientSecretsPath: settingsYoutubeClientSecretsInput.value.trim(),
      youtubeCredentialsPath: settingsYoutubeCredentialsInput.value.trim(),
      youtubePrivacyStatus: settingsYoutubePrivacySelect?.value || 'private',
      bgmDirectory: settingsBgmDirInput.value.trim(),
      youtubeForceVideo: settingsYoutubeForceInput.value.trim(),
    };
    try {
      await window.aiSettings.save(payload);
      settingsSaveBtn.textContent = '保存済み';
      setTimeout(() => {
        settingsSaveBtn.textContent = '保存';
      }, 1200);
    } catch (err) {
      console.error('Failed to save settings', err);
      alert('設定の保存に失敗しました');
    }
  }

  settingsProviderSelect.addEventListener('change', handleProviderChanged);
  settingsSaveBtn.addEventListener('click', handleSave);
  if (settingsYoutubeClientSecretsBrowseBtn) {
    settingsYoutubeClientSecretsBrowseBtn.addEventListener('click', async () => {
      const res = await (window.fileDialog?.chooseYoutubeClientSecrets?.() || Promise.resolve({ canceled: true }));
      if (res && !res.canceled && res.path) {
        settingsYoutubeClientSecretsInput.value = res.path;
      }
    });
  }
  if (settingsYoutubeCredentialsBrowseBtn) {
    settingsYoutubeCredentialsBrowseBtn.addEventListener('click', async () => {
      const res = await (window.fileDialog?.chooseYoutubeCredentials?.() || Promise.resolve({ canceled: true }));
      if (res && !res.canceled && res.path) {
        settingsYoutubeCredentialsInput.value = res.path;
      }
    });
  }
  if (settingsYoutubeAuthTestBtn) {
    settingsYoutubeAuthTestBtn.addEventListener('click', async () => {
      settingsYoutubeAuthTestBtn.disabled = true;
      settingsYoutubeAuthTestBtn.textContent = '認証中...';
      try {
        await window.youtubeAuth.runAuthTest();
        alert('YouTube OAuth 認証が完了しました。');
      } catch (err) {
        console.error(err);
        alert(`認証に失敗しました: ${err.message || err}`);
      } finally {
        settingsYoutubeAuthTestBtn.disabled = false;
        settingsYoutubeAuthTestBtn.textContent = 'YouTube 認証テスト';
      }
    });
  }

  loadSettings();
})();
