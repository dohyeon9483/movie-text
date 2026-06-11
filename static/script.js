const homeSection = document.getElementById('homeSection');
const settingsSection = document.getElementById('settingsSection');
const navHome = document.getElementById('navHome');
const navSettings = document.getElementById('navSettings');

const boardFileInput = document.getElementById('boardFileInput');
const boardUploadBtn = document.getElementById('boardUploadBtn');
const openScriptJobBtn = document.getElementById('openScriptJobBtn');
const boardSearchInput = document.getElementById('boardSearchInput');
const boardStatusFilter = document.getElementById('boardStatusFilter');
const selectAllCardsBtn = document.getElementById('selectAllCardsBtn');
const clearCardSelectionBtn = document.getElementById('clearCardSelectionBtn');
const downloadSelectedCardsBtn = document.getElementById('downloadSelectedCardsBtn');
const deleteSelectedCardsBtn = document.getElementById('deleteSelectedCardsBtn');
const uploadQueue = document.getElementById('uploadQueue');
const jobBoard = document.getElementById('jobBoard');

const apiKeyInput = document.getElementById('apiKeyInput');
const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
const apiKeyStatus = document.getElementById('apiKeyStatus');

const scriptJobModal = document.getElementById('scriptJobModal');
const scriptJobCloseBtn = document.getElementById('scriptJobCloseBtn');
const scriptJobNameInput = document.getElementById('scriptJobNameInput');
const scriptJobLanguageSelect = document.getElementById('scriptJobLanguageSelect');
const scriptJobSrtInput = document.getElementById('scriptJobSrtInput');
const createScriptJobBtn = document.getElementById('createScriptJobBtn');

const fileModal = document.getElementById('fileModal');
const fileModalCloseBtn = document.getElementById('fileModalCloseBtn');
const modalFilename = document.getElementById('modalFilename');
const modalKoSrt = document.getElementById('modalKoSrt');
const modalCorrectedSrt = document.getElementById('modalCorrectedSrt');
const modalEnSrt = document.getElementById('modalEnSrt');
const saveCorrectedSrtBtn = document.getElementById('saveCorrectedSrtBtn');
const saveEnglishSrtBtn = document.getElementById('saveEnglishSrtBtn');
const generationLanguageSelect = document.getElementById('generationLanguageSelect');
const generationVoiceSelect = document.getElementById('generationVoiceSelect');
const modalAudioBtn = document.getElementById('modalAudioBtn');
const modalDubBtn = document.getElementById('modalDubBtn');
const originalVideoPlayer = document.getElementById('originalVideoPlayer');
const originalMediaHint = document.getElementById('originalMediaHint');
const previewKoSubtitleBtn = document.getElementById('previewKoSubtitleBtn');
const previewEnSubtitleBtn = document.getElementById('previewEnSubtitleBtn');
const previewStructureSubtitleBtn = document.getElementById('previewStructureSubtitleBtn');
const subtitleVideoPlayer = document.getElementById('subtitleVideoPlayer');
const subtitleFontFamily = document.getElementById('subtitleFontFamily');
const subtitleFontSize = document.getElementById('subtitleFontSize');
const subtitlePosition = document.getElementById('subtitlePosition');
const subtitleMarginV = document.getElementById('subtitleMarginV');
const subtitleTextColor = document.getElementById('subtitleTextColor');
const subtitleOutlineColor = document.getElementById('subtitleOutlineColor');
const subtitleOutlineWidth = document.getElementById('subtitleOutlineWidth');
const subtitleShadow = document.getElementById('subtitleShadow');
const subtitleBackgroundEnabled = document.getElementById('subtitleBackgroundEnabled');
const subtitleBackgroundColor = document.getElementById('subtitleBackgroundColor');
const subtitleBackgroundOpacity = document.getElementById('subtitleBackgroundOpacity');
const subtitleDesignPreviewText = document.getElementById('subtitleDesignPreviewText');
const generatedAudioPlayer = document.getElementById('generatedAudioPlayer');
const dubbedVideoPlayer = document.getElementById('dubbedVideoPlayer');
const modalCaptionedDubBtn = document.getElementById('modalCaptionedDubBtn');
const captionedDubVideoPlayer = document.getElementById('captionedDubVideoPlayer');
const generationRequirementHint = document.getElementById('generationRequirementHint');
const mainPreviewTitle = document.getElementById('mainPreviewTitle');
const mainPreviewHint = document.getElementById('mainPreviewHint');
const mainPreviewVideo = document.getElementById('mainPreviewVideo');
const mainPreviewAudio = document.getElementById('mainPreviewAudio');
const mainPreviewEmpty = document.getElementById('mainPreviewEmpty');
const productionSettingsTitle = document.getElementById('productionSettingsTitle');
const voiceSettingGroup = document.getElementById('voiceSettingGroup');
const subtitleStylePanel = document.getElementById('subtitleStylePanel');
const productionGenerateBtn = document.getElementById('productionGenerateBtn');
const productionDownloadBtn = document.getElementById('productionDownloadBtn');
const modalArtifacts = document.getElementById('modalArtifacts');
const modalJobStatus = document.getElementById('modalJobStatus');
const modalCorrectBtn = document.getElementById('modalCorrectBtn');
const modalTranslateBtn = document.getElementById('modalTranslateBtn');

let files = [];
let selectedFileIds = new Set();
let currentFileId = null;
let currentFileData = null;
let currentTab = 'korean_srt';
let voices = [];
let voiceDefaults = { ko: 'Kore', en: 'Puck' };
let boardPollTimer = null;
let currentPreviewMode = 'captioned_dub';
let currentOutputType = 'captioned_dub';

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function postJson(url, body = {}, method = 'POST') {
    const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok || data.success === false) {
        throw new Error(normalizeApiError(data.detail || data.message || response.statusText || '요청에 실패했습니다.'));
    }
    return data;
}

function normalizeApiError(message) {
    const text = String(message || '');
    if (text.toLowerCase() === 'not found') {
        return '서버에 해당 API가 없습니다. 실행 중인 서버가 예전 코드일 수 있으니 서버를 재시작하세요.';
    }
    if (text.includes('RESOURCE_EXHAUSTED') || text.includes('Quota exceeded') || text.includes('429')) {
        const retryMatch = text.match(/retryDelay['"]?:\s*['"]?(\d+)s/i) || text.match(/retry in ([\d.]+)s/i);
        const retryText = retryMatch ? ` 약 ${Math.ceil(Number(retryMatch[1]))}초 후 다시 시도하거나` : '';
        return `Gemini TTS 요청 한도 또는 쿼터를 초과했습니다.${retryText} Google AI Studio에서 결제 프로젝트 연결과 모델별 쿼터를 확인하세요. 결제했더라도 API 키가 결제된 프로젝트에 연결되지 않았거나, gemini-3.1-flash-tts 모델의 분당/일일 한도가 적용될 수 있습니다. 긴 SRT는 묶음 생성으로 요청 수를 줄이지만, 반복 생성하면 모델 쿼터에 걸릴 수 있습니다.`;
    }
    if (text.includes('Gemini API key is not configured')) {
        return 'Gemini API 키가 설정되지 않았습니다. 설정에서 키를 저장하거나 .env에 GEMINI_API_KEY를 넣고 서버를 재시작하세요.';
    }
    if (text.includes('Could not automatically determine credentials') || text.includes('GOOGLE_APPLICATION_CREDENTIALS') || text.includes('DefaultCredentialsError')) {
        return 'Google Cloud Text-to-Speech 인증이 필요합니다. gcloud auth application-default login을 실행하거나 서비스 계정 JSON 경로를 GOOGLE_APPLICATION_CREDENTIALS에 설정하세요.';
    }
    return text;
}

function boundedNumber(input, fallback, min, max) {
    const value = Number(input?.value);
    if (!Number.isFinite(value)) return fallback;
    return Math.max(min, Math.min(max, Math.round(value)));
}

function getSubtitleStyleOptions() {
    return {
        font_family: subtitleFontFamily?.value || 'Arial',
        font_size: boundedNumber(subtitleFontSize, 48, 16, 120),
        position: subtitlePosition?.value || 'bottom',
        margin_v: boundedNumber(subtitleMarginV, 64, 0, 240),
        text_color: subtitleTextColor?.value || '#ffffff',
        outline_color: subtitleOutlineColor?.value || '#000000',
        outline_width: boundedNumber(subtitleOutlineWidth, 2, 0, 10),
        shadow: boundedNumber(subtitleShadow, 1, 0, 8),
        background_enabled: Boolean(subtitleBackgroundEnabled?.checked),
        background_color: subtitleBackgroundColor?.value || '#000000',
        background_opacity: boundedNumber(subtitleBackgroundOpacity, 60, 0, 100)
    };
}

function hexToRgb(hexColor) {
    const normalized = String(hexColor || '').replace('#', '').trim();
    if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return { r: 0, g: 0, b: 0 };
    return {
        r: parseInt(normalized.slice(0, 2), 16),
        g: parseInt(normalized.slice(2, 4), 16),
        b: parseInt(normalized.slice(4, 6), 16)
    };
}

function rgbaFromHex(hexColor, opacityPercent) {
    const { r, g, b } = hexToRgb(hexColor);
    const alpha = Math.max(0, Math.min(100, Number(opacityPercent) || 0)) / 100;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function extractSubtitlePreviewText() {
    const language = generationLanguageSelect?.value || 'ko';
    const source = language === 'en'
        ? modalEnSrt.value
        : (modalCorrectedSrt.value || modalKoSrt.value);
    const cueText = String(source || '')
        .split(/\r?\n\r?\n/)
        .map(block => block.split(/\r?\n/).filter(line => line.trim() && !/^\d+$/.test(line.trim()) && !line.includes('-->')).join(' '))
        .find(text => text.trim());
    return cueText || (language === 'en' ? 'This is how your subtitle will look.' : '자막이 이렇게 표시됩니다.');
}

function outlineTextShadow(color, width, shadow) {
    const outline = Math.max(0, Math.min(10, Number(width) || 0));
    const shadowSize = Math.max(0, Math.min(8, Number(shadow) || 0));
    const shadows = [];
    if (outline > 0) {
        shadows.push(
            `${-outline}px 0 0 ${color}`,
            `${outline}px 0 0 ${color}`,
            `0 ${-outline}px 0 ${color}`,
            `0 ${outline}px 0 ${color}`,
            `${-outline}px ${-outline}px 0 ${color}`,
            `${outline}px ${-outline}px 0 ${color}`,
            `${-outline}px ${outline}px 0 ${color}`,
            `${outline}px ${outline}px 0 ${color}`
        );
    }
    if (shadowSize > 0) {
        shadows.push(`0 ${shadowSize}px ${shadowSize * 2}px rgba(0, 0, 0, 0.55)`);
    }
    return shadows.join(', ');
}

function updateSubtitleDesignPreview() {
    if (!subtitleDesignPreviewText) return;
    const style = getSubtitleStyleOptions();
    const scale = 0.42;
    const previewFontSize = Math.max(14, Math.round(style.font_size * scale));
    const margin = Math.max(10, Math.round(style.margin_v * 0.18));
    subtitleDesignPreviewText.textContent = extractSubtitlePreviewText();
    subtitleDesignPreviewText.style.fontFamily = `"${style.font_family}", Arial, sans-serif`;
    subtitleDesignPreviewText.style.fontSize = `${previewFontSize}px`;
    subtitleDesignPreviewText.style.color = style.text_color;
    subtitleDesignPreviewText.style.background = style.background_enabled
        ? rgbaFromHex(style.background_color, style.background_opacity)
        : 'transparent';
    subtitleDesignPreviewText.style.textShadow = outlineTextShadow(style.outline_color, style.outline_width * 0.45, style.shadow);
    subtitleDesignPreviewText.style.top = '';
    subtitleDesignPreviewText.style.bottom = '';
    subtitleDesignPreviewText.style.transform = 'translateX(-50%)';
    if (style.position === 'top') {
        subtitleDesignPreviewText.style.top = `${margin}px`;
    } else if (style.position === 'middle') {
        subtitleDesignPreviewText.style.top = '50%';
        subtitleDesignPreviewText.style.transform = 'translate(-50%, -50%)';
    } else {
        subtitleDesignPreviewText.style.bottom = `${margin}px`;
    }
}

function showSection(section) {
    homeSection.classList.toggle('hidden', section !== 'home');
    settingsSection.classList.toggle('hidden', section !== 'settings');
    navHome.classList.toggle('active', section === 'home');
    navSettings.classList.toggle('active', section === 'settings');
}

function statusLabel(status) {
    const labels = {
        pending: '대기',
        running: '진행 중',
        completed: '완료',
        failed: '오류',
        idle: '대기'
    };
    return labels[status] || status || '대기';
}

function getCardStatus(file) {
    const summary = file.job_summary || {};
    return summary.status || 'idle';
}

function getStatusBadges(file) {
    const artifact = file.artifact_summary || {};
    const items = [
        ['한국어 SRT', Boolean(file.srt_text)],
        ['보정 SRT', Boolean(file.corrected_srt_text)],
        ['English SRT', Boolean(file.english_srt_text)],
        ['MP3', Boolean(artifact.audio_ko || artifact.audio_en)],
        ['자막 MP4', Boolean(artifact.subtitle_video_ko || artifact.subtitle_video_en)],
        ['더빙 MP4', Boolean(artifact.video_ko || artifact.video_en)],
        ['자막+더빙 MP4', Boolean(artifact.captioned_dub_video_ko || artifact.captioned_dub_video_en)]
    ];
    return items.map(([label, active]) =>
        `<span class="file-status-badge ${active ? 'ready' : 'missing'}">${active ? label : `${label} 없음`}</span>`
    ).join('');
}

function renderBoard() {
    const query = boardSearchInput.value.trim().toLowerCase();
    const statusFilter = boardStatusFilter.value;
    const visibleFiles = files.filter(file => {
        const matchesQuery = !query || file.filename.toLowerCase().includes(query);
        const status = getCardStatus(file);
        const matchesStatus = statusFilter === 'all'
            || (statusFilter === 'idle' ? status === 'idle' : status === statusFilter);
        return matchesQuery && matchesStatus;
    });

    if (visibleFiles.length === 0) {
        jobBoard.innerHTML = '<div class="loading">표시할 작업이 없습니다. 영상을 업로드하거나 SRT 작업을 만들어보세요.</div>';
        return;
    }

    jobBoard.innerHTML = visibleFiles.map(file => {
        const status = getCardStatus(file);
        const summary = file.job_summary || {};
        const thumb = file.thumbnail_url
            ? `<img src="${file.thumbnail_url}" alt="">`
            : `<div class="card-placeholder">${file.type === 'srt_project' ? 'SRT' : 'VIDEO'}</div>`;
        const checked = selectedFileIds.has(file.id) ? 'checked' : '';
        const progress = Number(summary.progress || 0);
        const overlay = status === 'pending' || status === 'running' || status === 'failed'
            ? `<div class="card-overlay ${status}"><strong>${statusLabel(status)}</strong><span>${escapeHtml(summary.message || '')}</span></div>`
            : '';
        return `
            <article class="job-card" data-file-id="${file.id}">
                <label class="card-select"><input type="checkbox" data-select-file="${file.id}" ${checked}></label>
                <button class="card-open" data-open-file="${file.id}">
                    <div class="card-thumb">${thumb}${overlay}</div>
                    <div class="card-body">
                        <div class="card-title">${escapeHtml(file.filename)}</div>
                        <div class="card-meta">${statusLabel(status)} · ${new Date(file.uploaded_at).toLocaleString()}</div>
                        <div class="card-progress"><span style="width:${Math.max(0, Math.min(progress, 100))}%"></span></div>
                        <div class="file-status-badges">${getStatusBadges(file)}</div>
                    </div>
                </button>
            </article>
        `;
    }).join('');
}

async function loadBoard() {
    const response = await fetch('/api/files');
    const data = await response.json();
    if (!data.success) {
        jobBoard.innerHTML = '<div class="loading">작업을 불러올 수 없습니다.</div>';
        return;
    }
    files = data.files || [];
    renderBoard();
}

function startBoardPolling() {
    if (boardPollTimer) clearInterval(boardPollTimer);
    boardPollTimer = setInterval(async () => {
        await loadBoard();
        if (!fileModal.classList.contains('hidden') && currentFileId) {
            const boardFile = files.find(file => file.id === currentFileId);
            const status = boardFile?.job_summary?.status || 'idle';
            if (status === 'pending' || status === 'running' || status === 'failed') {
                await refreshModalFile();
            }
        }
    }, 2500);
}

async function uploadVideos(fileList) {
    const uploadFiles = Array.from(fileList || []);
    if (uploadFiles.length === 0) return;

    uploadQueue.classList.remove('hidden');
    uploadQueue.innerHTML = uploadFiles.map(file => `
        <div class="queue-item" data-upload-name="${escapeHtml(file.name)}">
            <strong>${escapeHtml(file.name)}</strong>
            <span>업로드 대기</span>
        </div>
    `).join('');

    const formData = new FormData();
    uploadFiles.forEach(file => formData.append('files', file));

    try {
        const response = await fetch('/upload', { method: 'POST', body: formData });
        if (!response.ok) throw new Error('업로드에 실패했습니다.');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const event = JSON.parse(line.slice(6));
                const active = uploadQueue.querySelector('.queue-item span');
                if (active && event.message) active.textContent = event.message;
                if (event.status === 'completed') await loadBoard();
            }
        }
        await loadBoard();
    } catch (error) {
        alert(`업로드 실패: ${error.message}`);
    } finally {
        setTimeout(() => uploadQueue.classList.add('hidden'), 1000);
    }
}

function renderArtifacts(artifacts) {
    if (!artifacts || artifacts.length === 0) {
        modalArtifacts.innerHTML = '<div class="summary-placeholder">생성된 산출물이 없습니다</div>';
        return;
    }
    modalArtifacts.innerHTML = artifacts.map(artifact => {
        const language = artifact.language === 'en' ? 'English' : '한국어';
        const kindLabels = {
            audio: '음성 MP3',
            video: '더빙 영상',
            subtitle_video: '자막 영상',
            captioned_dub_video: '자막+더빙 영상'
        };
        const kind = kindLabels[artifact.kind] || artifact.kind;
        const previewUrl = artifactUrl(artifact);
        const player = artifact.kind === 'audio'
            ? `<audio class="artifact-player" controls preload="metadata" src="${previewUrl}"></audio>`
            : ['video', 'subtitle_video', 'captioned_dub_video'].includes(artifact.kind)
                ? `<video class="artifact-player artifact-video-player" controls playsinline preload="metadata" src="${previewUrl}"></video>`
                : '';
        return `
            <div class="artifact-item">
                <div class="artifact-item-header">
                    <div>
                        <strong>${language} ${kind}</strong>
                        <small>${escapeHtml(artifact.filename || '')}</small>
                    </div>
                    <a class="btn-toolbar" href="/api/artifacts/${encodeURIComponent(artifact.id)}/download" download>다운로드</a>
                </div>
                ${player}
            </div>
        `;
    }).join('');
}

function artifactUrl(artifact) {
    return `/api/artifacts/${encodeURIComponent(artifact.id)}/preview`;
}

function setPlayerSource(player, url) {
    if (!player || !url) return;
    if (player.src !== new URL(url, window.location.origin).href) {
        player.src = url;
        player.load();
    }
}

function clearPlayerSource(player) {
    if (!player) return;
    player.pause();
    player.removeAttribute('src');
    player.load();
}

function previewModeLabel(mode) {
    const labels = {
        original: '원본 영상',
        subtitle: '자막 입힌 영상',
        subtitle_en: 'English 자막 영상',
        audio: '생성 음성',
        dub: '더빙 영상',
        captioned_dub: '자막 붙은 더빙 영상'
    };
    return labels[mode] || '미리보기';
}

function outputTypeLabel(type = currentOutputType) {
    const labels = {
        subtitle: '자막 영상',
        audio: '음성 MP3',
        dub: '더빙 영상',
        captioned_dub: '자막+더빙 영상'
    };
    return labels[type] || '결과물';
}

function outputTypeToPreviewMode(type = currentOutputType) {
    if (type === 'subtitle') return 'subtitle';
    if (type === 'audio') return 'audio';
    if (type === 'dub') return 'dub';
    return 'captioned_dub';
}

function outputTypeToJobType(type = currentOutputType) {
    if (type === 'subtitle') return 'subtitle_video';
    if (type === 'audio') return 'audio';
    if (type === 'dub') return 'dub_video';
    return 'captioned_dub_video';
}

function outputNeedsVoice(type = currentOutputType) {
    return ['audio', 'dub', 'captioned_dub'].includes(type);
}

function outputNeedsSubtitleStyle(type = currentOutputType) {
    return ['subtitle', 'captioned_dub'].includes(type);
}

function latestArtifact(file, kind, language = null) {
    return (file?.artifacts || []).find(item =>
        item.kind === kind && (!language || item.language === language)
    );
}

function artifactForPreviewMode(file, mode) {
    const language = generationLanguageSelect?.value || 'ko';
    if (mode === 'subtitle_en') return latestArtifact(file, 'subtitle_video', 'en');
    if (mode === 'subtitle') return latestArtifact(file, 'subtitle_video', language) || latestArtifact(file, 'subtitle_video');
    if (mode === 'audio') return latestArtifact(file, 'audio', language) || latestArtifact(file, 'audio');
    if (mode === 'dub') return latestArtifact(file, 'video', language) || latestArtifact(file, 'video');
    if (mode === 'captioned_dub') return latestArtifact(file, 'captioned_dub_video', language) || latestArtifact(file, 'captioned_dub_video');
    return null;
}

function setPreviewMode(mode, artifact = null) {
    currentPreviewMode = mode;
    document.querySelectorAll('[data-preview-mode]').forEach(button => {
        button.classList.toggle('active', button.dataset.previewMode === mode);
    });
    updateMainPreview(artifact);
}

function updateMainPreview(explicitArtifact = null) {
    if (!mainPreviewVideo || !mainPreviewAudio || !mainPreviewEmpty) return;
    const mode = currentPreviewMode || 'original';
    const title = previewModeLabel(mode);
    let sourceUrl = '';
    let isAudio = false;
    let hint = '';

    if (mode === 'original') {
        sourceUrl = currentFileData?.media_url || '';
        hint = sourceUrl ? '업로드한 원본 영상입니다.' : 'SRT-only 작업은 원본 영상이 없습니다.';
    } else {
        const artifact = explicitArtifact || artifactForPreviewMode(currentFileData, mode);
        sourceUrl = artifact ? artifactUrl(artifact) : '';
        isAudio = artifact?.kind === 'audio' || mode === 'audio';
        hint = artifact
            ? `${artifact.language === 'en' ? 'English' : '한국어'} ${title} · ${artifact.filename || ''}`
            : `${title} 산출물이 아직 없습니다. 위의 구조 카드에서 먼저 생성하세요.`;
    }

    mainPreviewTitle.textContent = title;
    mainPreviewHint.textContent = hint;
    updateProductionDownload(explicitArtifact || (mode === 'original' ? null : artifactForPreviewMode(currentFileData, mode)));
    mainPreviewEmpty.classList.toggle('hidden', Boolean(sourceUrl));
    mainPreviewVideo.classList.toggle('hidden', !sourceUrl || isAudio);
    mainPreviewAudio.classList.toggle('hidden', !sourceUrl || !isAudio);

    if (!sourceUrl) {
        clearPlayerSource(mainPreviewVideo);
        clearPlayerSource(mainPreviewAudio);
        return;
    }
    if (isAudio) {
        clearPlayerSource(mainPreviewVideo);
        setPlayerSource(mainPreviewAudio, sourceUrl);
    } else {
        clearPlayerSource(mainPreviewAudio);
        setPlayerSource(mainPreviewVideo, sourceUrl);
    }
}

function updateProductionDownload(artifact = null) {
    if (!productionDownloadBtn) return;
    if (artifact?.id) {
        productionDownloadBtn.href = `/api/artifacts/${encodeURIComponent(artifact.id)}/download`;
        productionDownloadBtn.classList.remove('disabled-link');
        productionDownloadBtn.setAttribute('download', artifact.filename || '');
    } else {
        productionDownloadBtn.href = '#';
        productionDownloadBtn.classList.add('disabled-link');
        productionDownloadBtn.removeAttribute('download');
    }
}

function setOutputType(type) {
    currentOutputType = type;
    const previewMode = outputTypeToPreviewMode(type);
    currentPreviewMode = previewMode;
    document.querySelectorAll('[data-output-type]').forEach(button => {
        button.classList.toggle('active', button.dataset.outputType === type);
    });
    updateProductionView();
}

function updateProductionView() {
    const label = outputTypeLabel();
    if (productionSettingsTitle) productionSettingsTitle.textContent = `${label} 설정`;
    if (productionGenerateBtn) productionGenerateBtn.textContent = `${label} 생성하기`;
    if (voiceSettingGroup) voiceSettingGroup.classList.toggle('hidden', !outputNeedsVoice());
    if (subtitleStylePanel) subtitleStylePanel.classList.toggle('hidden', !outputNeedsSubtitleStyle());
    setPreviewMode(outputTypeToPreviewMode());
    updateSubtitleDesignPreview();
    updateModalActionState();
}

function previewArtifact(artifact) {
    if (!artifact) return;
    if (artifact.kind === 'audio') {
        setPreviewMode('audio', artifact);
        return;
    }
    if (artifact.kind === 'subtitle_video') {
        setPreviewMode(artifact.language === 'en' ? 'subtitle_en' : 'subtitle', artifact);
        return;
    }
    if (artifact.kind === 'video') {
        setPreviewMode('dub', artifact);
        return;
    }
    if (artifact.kind === 'captioned_dub_video') {
        setPreviewMode('captioned_dub', artifact);
    }
}

function updatePreviewPlayers(file) {
    if (!file) return;
    if (file.media_url) {
        setPlayerSource(originalVideoPlayer, file.media_url);
        originalVideoPlayer.classList.remove('hidden');
        if (originalMediaHint) originalMediaHint.textContent = '원본 업로드 영상';
    } else {
        originalVideoPlayer.removeAttribute('src');
        originalVideoPlayer.load();
        originalVideoPlayer.classList.add('hidden');
        if (originalMediaHint) originalMediaHint.textContent = 'SRT-only 작업은 원본 영상이 없습니다.';
    }

    const artifacts = file.artifacts || [];
    const latestAudio = artifacts.find(item => item.kind === 'audio');
    const latestDubbedVideo = artifacts.find(item => item.kind === 'video');
    const latestSubtitleVideo = artifacts.find(item => item.kind === 'subtitle_video');
    const latestCaptionedDubVideo = artifacts.find(item => item.kind === 'captioned_dub_video');
    if (latestAudio) setPlayerSource(generatedAudioPlayer, artifactUrl(latestAudio));
    if (latestDubbedVideo) setPlayerSource(dubbedVideoPlayer, artifactUrl(latestDubbedVideo));
    if (latestSubtitleVideo) setPlayerSource(subtitleVideoPlayer, artifactUrl(latestSubtitleVideo));
    if (latestCaptionedDubVideo) setPlayerSource(captionedDubVideoPlayer, artifactUrl(latestCaptionedDubVideo));
    updateMainPreview();
}

function setModalStatus(file) {
    const summary = file?.job_summary || {};
    const status = summary.status || 'idle';
    const detail = status === 'failed' && summary.latest?.error
        ? normalizeApiError(summary.latest.error)
        : (summary.message || '대기 중');
    modalJobStatus.textContent = `${statusLabel(status)} · ${detail}`;
    modalJobStatus.className = `api-key-status ${status === 'failed' ? 'disconnected' : 'connected'}`;
}

function setModalMessage(message, isError = false) {
    modalJobStatus.textContent = message;
    modalJobStatus.className = `api-key-status ${isError ? 'disconnected' : 'connected'}`;
}

function setActionBusy(button, label) {
    const original = button.textContent;
    button.textContent = label;
    button.disabled = true;
    return () => {
        button.textContent = original;
        button.disabled = false;
        updateModalActionState();
    };
}

function updateModalActionState() {
    const hasKoSrt = Boolean(modalKoSrt.value.trim());
    const hasCorrectedSrt = Boolean(modalCorrectedSrt.value.trim());
    const hasEnSrt = Boolean(modalEnSrt.value.trim());
    const language = generationLanguageSelect.value;
    modalCorrectBtn.disabled = !hasKoSrt;
    modalTranslateBtn.disabled = !(hasKoSrt || hasCorrectedSrt);
    modalAudioBtn.disabled = language === 'en' ? !hasEnSrt : !(hasKoSrt || hasCorrectedSrt);
    modalDubBtn.disabled = modalAudioBtn.disabled;
    if (modalCaptionedDubBtn) modalCaptionedDubBtn.disabled = modalAudioBtn.disabled;
    if (previewStructureSubtitleBtn) previewStructureSubtitleBtn.disabled = modalAudioBtn.disabled;
    if (previewKoSubtitleBtn) previewKoSubtitleBtn.disabled = !(hasKoSrt || hasCorrectedSrt);
    if (previewEnSubtitleBtn) previewEnSubtitleBtn.disabled = !hasEnSrt;
    if (generationRequirementHint) {
        generationRequirementHint.textContent = language === 'en' && !hasEnSrt
            ? 'English 구조를 만들려면 먼저 English SRT 탭에서 영어 자막을 생성하거나 붙여넣으세요.'
            : '원본 영상이 없는 SRT 작업은 검은 배경 MP4로 생성됩니다.';
    }
    if (productionGenerateBtn) {
        const needsSrt = language === 'en' ? hasEnSrt : (hasKoSrt || hasCorrectedSrt);
        productionGenerateBtn.disabled = !needsSrt;
    }
}

function populateVoiceSelect(language) {
    const defaultVoice = voiceDefaults[language] || voices[0]?.name || '';
    generationVoiceSelect.innerHTML = voices.map(voice =>
        `<option value="${voice.name}" ${voice.name === defaultVoice ? 'selected' : ''}>${escapeHtml(voice.label || voice.name)}</option>`
    ).join('');
}

function selectedGenerationOptions() {
    const language = generationLanguageSelect.value;
    return {
        language,
        voice_name: generationVoiceSelect.value,
        srt_source: language === 'en' ? 'english' : 'corrected',
        subtitle_style: getSubtitleStyleOptions()
    };
}

async function openFileModal(fileId) {
    currentFileId = fileId;
    currentTab = 'korean_srt';
    currentOutputType = 'captioned_dub';
    currentPreviewMode = outputTypeToPreviewMode(currentOutputType);
    document.querySelectorAll('.modal-tabs .tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === currentTab));
    document.querySelectorAll('.modal-body .tab-content').forEach(content => content.classList.toggle('active', content.dataset.content === currentTab));
    fileModal.classList.remove('hidden');
    await refreshModalFile();
    updateProductionView();
}

async function refreshModalFile() {
    if (!currentFileId) return;
    const response = await fetch(`/api/files/${currentFileId}`);
    const data = await response.json();
    if (!data.success) return;
    currentFileData = data.file;
    modalFilename.textContent = currentFileData.filename;
    modalKoSrt.value = currentFileData.srt_text || '';
    modalCorrectedSrt.value = currentFileData.corrected_srt_text || '';
    modalEnSrt.value = currentFileData.english_srt_text || '';
    setModalStatus(currentFileData);
    renderArtifacts(currentFileData.artifacts || []);
    updatePreviewPlayers(currentFileData);
    updateModalActionState();
    updateSubtitleDesignPreview();
}

async function startJob(jobType, options = {}, button = null, busyLabel = '작업 등록 중...') {
    if (!currentFileId) return;
    const restore = button ? setActionBusy(button, busyLabel) : null;
    setModalMessage(busyLabel);
    try {
        let data;
        try {
            data = await postJson(`/api/files/${currentFileId}/jobs/${jobType}`, options);
            setModalMessage(`작업 등록됨 · ${data.job.message}`);
        } catch (error) {
            if (!String(error.message || '').toLowerCase().includes('not found')) {
                throw error;
            }
            data = await runDirectJobFallback(jobType, options);
            setModalMessage('작업 완료');
        }
        await loadBoard();
        await refreshModalFile();
        if (data?.download_url) {
            renderArtifacts(currentFileData?.artifacts || []);
        }
    } catch (error) {
        setModalMessage(`오류: ${error.message}`, true);
        alert(`작업 시작 실패: ${error.message}`);
    } finally {
        if (restore) restore();
    }
}

async function runDirectJobFallback(jobType, options) {
    if (jobType === 'correct_ko') {
        const data = await postJson(`/api/files/${currentFileId}/srt/correct/ko`);
        modalCorrectedSrt.value = data.corrected_srt_text || '';
        return data;
    }
    if (jobType === 'translate_en') {
        const data = await postJson(`/api/files/${currentFileId}/translate/en`);
        modalEnSrt.value = data.english_srt_text || '';
        return data;
    }
    if (jobType === 'audio') {
        return postJson(`/api/files/${currentFileId}/audio`, options);
    }
    if (jobType === 'dub_video') {
        return postJson(`/api/files/${currentFileId}/dub-video`, options);
    }
    if (jobType === 'subtitle_video') {
        return postJson(`/api/files/${currentFileId}/subtitle-video`, options);
    }
    if (jobType === 'captioned_dub_video') {
        return postJson(`/api/files/${currentFileId}/captioned-dub-video`, options);
    }
    throw new Error('지원하지 않는 작업입니다.');
}

async function createSubtitlePreview(language) {
    if (!currentFileId) return;
    const button = productionGenerateBtn || (language === 'en' ? previewEnSubtitleBtn : previewKoSubtitleBtn);
    const restore = setActionBusy(button, language === 'en' ? 'English 자막 영상 생성 중...' : '한국어 자막 영상 생성 중...');
    setModalMessage(language === 'en' ? 'English 자막 영상 생성 중...' : '한국어 자막 영상 생성 중...');
    try {
        const data = await postJson(`/api/files/${currentFileId}/subtitle-video`, {
            language,
            srt_source: language === 'en' ? 'english' : 'corrected',
            subtitle_style: getSubtitleStyleOptions()
        });
        setPlayerSource(subtitleVideoPlayer, data.download_url);
        await loadBoard();
        await refreshModalFile();
        setPreviewMode(language === 'en' ? 'subtitle_en' : 'subtitle', data.artifact);
        setModalMessage('자막 영상 생성 완료');
    } catch (error) {
        setModalMessage(`오류: ${error.message}`, true);
        alert(`자막 영상 생성 실패: ${error.message}`);
    } finally {
        restore();
    }
}

async function createSelectedLanguageSubtitlePreview() {
    await createSubtitlePreview(generationLanguageSelect.value);
}

function generateCurrentOutput() {
    const jobType = outputTypeToJobType();
    const label = outputTypeLabel();
    setPreviewMode(outputTypeToPreviewMode());
    if (jobType === 'subtitle_video') {
        createSelectedLanguageSubtitlePreview();
        return;
    }
    startJob(jobType, selectedGenerationOptions(), productionGenerateBtn, `${label} 생성 등록 중...`);
}

function currentSrtTextAndName() {
    const base = (currentFileData?.filename || 'subtitle').replace(/\.[^/.]+$/, '');
    if (currentTab === 'corrected_srt') return [modalCorrectedSrt.value, `${base}_corrected_ko.srt`];
    if (currentTab === 'english_srt') return [modalEnSrt.value, `${base}_en.srt`];
    return [modalKoSrt.value, `${base}_ko.srt`];
}

function srtTextAndNameForTarget(target) {
    const base = (currentFileData?.filename || 'subtitle').replace(/\.[^/.]+$/, '');
    if (target === 'corrected') return [modalCorrectedSrt.value, `${base}_corrected_ko.srt`];
    if (target === 'english') return [modalEnSrt.value, `${base}_en.srt`];
    return [modalKoSrt.value, `${base}_ko.srt`];
}

function downloadText(text, filename) {
    const blob = new Blob([text || ''], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function loadVoices() {
    const response = await fetch('/api/tts/voices');
    const data = await response.json();
    voices = data.voices || [{ name: 'Kore', label: 'Kore' }, { name: 'Puck', label: 'Puck' }];
    voiceDefaults = data.defaults || voiceDefaults;
    populateVoiceSelect(generationLanguageSelect.value);
}

async function checkApiKeyStatus() {
    try {
        const response = await fetch('/api/check-api-key');
        const data = await response.json();
        apiKeyStatus.textContent = data.has_key ? `API 키 설정됨 (${data.key_preview})` : 'API 키가 설정되지 않음';
        apiKeyStatus.className = `api-key-status ${data.has_key ? 'connected' : 'disconnected'}`;
    } catch {
        apiKeyStatus.textContent = 'API 키 상태를 확인할 수 없습니다';
        apiKeyStatus.className = 'api-key-status disconnected';
    }
}

navHome.addEventListener('click', () => showSection('home'));
navSettings.addEventListener('click', () => {
    showSection('settings');
    checkApiKeyStatus();
});

boardUploadBtn.addEventListener('click', () => boardFileInput.click());
boardFileInput.addEventListener('change', event => {
    uploadVideos(event.target.files);
    boardFileInput.value = '';
});

openScriptJobBtn.addEventListener('click', () => scriptJobModal.classList.remove('hidden'));
scriptJobCloseBtn.addEventListener('click', () => scriptJobModal.classList.add('hidden'));

createScriptJobBtn.addEventListener('click', async () => {
    const script = scriptJobSrtInput.value.trim();
    if (!script) {
        alert('SRT 내용을 입력해주세요.');
        return;
    }
    try {
        const data = await postJson('/api/script/jobs', {
            filename: scriptJobNameInput.value.trim() || 'srt_project',
            language: scriptJobLanguageSelect.value,
            script
        });
        scriptJobModal.classList.add('hidden');
        scriptJobSrtInput.value = '';
        scriptJobNameInput.value = '';
        await loadBoard();
        openFileModal(data.file.id);
    } catch (error) {
        alert(`작업 생성 실패: ${error.message}`);
    }
});

boardSearchInput.addEventListener('input', renderBoard);
boardStatusFilter.addEventListener('change', renderBoard);

jobBoard.addEventListener('click', event => {
    const select = event.target.closest('[data-select-file]');
    if (select) {
        const fileId = select.dataset.selectFile;
        if (select.checked) selectedFileIds.add(fileId);
        else selectedFileIds.delete(fileId);
        return;
    }
    const open = event.target.closest('[data-open-file]');
    if (open) openFileModal(open.dataset.openFile);
});

selectAllCardsBtn.addEventListener('click', () => {
    files.forEach(file => selectedFileIds.add(file.id));
    renderBoard();
});
clearCardSelectionBtn.addEventListener('click', () => {
    selectedFileIds.clear();
    renderBoard();
});
downloadSelectedCardsBtn.addEventListener('click', () => {
    files.filter(file => selectedFileIds.has(file.id)).forEach(file => {
        const srt = file.corrected_srt_text || file.srt_text || file.english_srt_text || '';
        if (srt) downloadText(srt, `${file.filename.replace(/\.[^/.]+$/, '')}.srt`);
    });
});
deleteSelectedCardsBtn.addEventListener('click', async () => {
    if (selectedFileIds.size === 0) return;
    if (!confirm(`선택한 ${selectedFileIds.size}개 작업을 삭제하시겠습니까?`)) return;
    for (const fileId of selectedFileIds) {
        await fetch(`/api/files/${fileId}`, { method: 'DELETE' });
    }
    selectedFileIds.clear();
    await loadBoard();
});

fileModalCloseBtn.addEventListener('click', () => fileModal.classList.add('hidden'));
fileModal.addEventListener('click', event => {
    if (event.target === fileModal) fileModal.classList.add('hidden');
});

modalArtifacts.addEventListener('click', event => {
    const button = event.target.closest('[data-preview-artifact]');
    if (!button || !currentFileData) return;
    const artifact = (currentFileData.artifacts || []).find(item => item.id === button.dataset.previewArtifact);
    previewArtifact(artifact);
});

document.querySelectorAll('.modal-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        currentTab = btn.dataset.tab;
        document.querySelectorAll('.modal-tabs .tab-btn').forEach(item => item.classList.remove('active'));
        document.querySelectorAll('.modal-body .tab-content').forEach(item => item.classList.remove('active'));
        btn.classList.add('active');
        document.querySelector(`.modal-body [data-content="${currentTab}"]`).classList.add('active');
    });
});

saveCorrectedSrtBtn.addEventListener('click', async () => {
    try {
        setModalMessage('보정 SRT 저장 중...');
        await postJson(`/api/files/${currentFileId}/corrected-srt`, { corrected_srt_text: modalCorrectedSrt.value }, 'PUT');
        await refreshModalFile();
        await loadBoard();
        setModalMessage('보정 SRT 저장 완료');
    } catch (error) {
        setModalMessage(`오류: ${error.message}`, true);
        alert(`저장 실패: ${error.message}`);
    }
});

saveEnglishSrtBtn.addEventListener('click', async () => {
    try {
        setModalMessage('English SRT 저장 중...');
        await postJson(`/api/files/${currentFileId}/english-srt`, { english_srt_text: modalEnSrt.value }, 'PUT');
        await refreshModalFile();
        await loadBoard();
        setModalMessage('English SRT 저장 완료');
    } catch (error) {
        setModalMessage(`오류: ${error.message}`, true);
        alert(`저장 실패: ${error.message}`);
    }
});

modalCorrectBtn.addEventListener('click', () => {
    if (!modalKoSrt.value.trim()) {
        setModalMessage('오류: 한국어 SRT가 없어 보정할 수 없습니다.', true);
        return;
    }
    startJob('correct_ko', {}, modalCorrectBtn, '한국어 SRT 보정 등록 중...');
});
modalTranslateBtn.addEventListener('click', () => {
    if (!modalKoSrt.value.trim() && !modalCorrectedSrt.value.trim()) {
        setModalMessage('오류: 번역할 한국어 SRT가 없습니다.', true);
        return;
    }
    startJob('translate_en', {}, modalTranslateBtn, '영어 자막 생성 등록 중...');
});
modalAudioBtn.addEventListener('click', () => setOutputType('audio'));
modalDubBtn.addEventListener('click', () => setOutputType('dub'));
modalCaptionedDubBtn.addEventListener('click', () => setOutputType('captioned_dub'));
previewStructureSubtitleBtn.addEventListener('click', () => setOutputType('subtitle'));
if (previewKoSubtitleBtn) previewKoSubtitleBtn.addEventListener('click', () => setPreviewMode('subtitle'));
if (previewEnSubtitleBtn) previewEnSubtitleBtn.addEventListener('click', () => setPreviewMode('subtitle_en'));
if (productionGenerateBtn) productionGenerateBtn.addEventListener('click', generateCurrentOutput);

document.querySelectorAll('[data-preview-mode]').forEach(button => {
    button.addEventListener('click', () => {
        const mode = button.dataset.previewMode;
        if (mode) setPreviewMode(mode);
    });
});

generationLanguageSelect.addEventListener('change', () => {
    populateVoiceSelect(generationLanguageSelect.value);
    updateProductionView();
    updateSubtitleDesignPreview();
    updateMainPreview();
});
generationVoiceSelect.addEventListener('change', () => {
    updateModalActionState();
});
modalKoSrt.addEventListener('input', () => {
    updateModalActionState();
    updateSubtitleDesignPreview();
});
modalCorrectedSrt.addEventListener('input', () => {
    updateModalActionState();
    updateSubtitleDesignPreview();
});
modalEnSrt.addEventListener('input', () => {
    updateModalActionState();
    updateSubtitleDesignPreview();
});

[
    subtitleFontFamily,
    subtitleFontSize,
    subtitlePosition,
    subtitleMarginV,
    subtitleTextColor,
    subtitleOutlineColor,
    subtitleOutlineWidth,
    subtitleShadow,
    subtitleBackgroundEnabled,
    subtitleBackgroundColor,
    subtitleBackgroundOpacity
].filter(Boolean).forEach(input => {
    input.addEventListener('input', updateSubtitleDesignPreview);
    input.addEventListener('change', updateSubtitleDesignPreview);
});

document.querySelectorAll('[data-download-srt]').forEach(button => {
    button.addEventListener('click', () => {
        const [text, filename] = srtTextAndNameForTarget(button.dataset.downloadSrt);
        if (!text.trim()) {
            alert('다운로드할 SRT가 없습니다.');
            return;
        }
        downloadText(text, filename);
    });
});

saveApiKeyBtn.addEventListener('click', async () => {
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
        alert('API 키를 입력해주세요.');
        return;
    }
    saveApiKeyBtn.disabled = true;
    saveApiKeyBtn.textContent = '저장 중...';
    try {
        const data = await postJson('/api/set-api-key', { api_key: apiKey });
        apiKeyInput.value = '';
        alert(data.message || 'API 키가 저장되었습니다.');
        await checkApiKeyStatus();
    } catch (error) {
        alert(`API 키 저장 실패: ${error.message}`);
    } finally {
        saveApiKeyBtn.disabled = false;
        saveApiKeyBtn.textContent = '저장';
    }
});

window.addEventListener('DOMContentLoaded', async () => {
    localStorage.removeItem('gemini_api_key');
    await checkApiKeyStatus();
    await loadVoices();
    await loadBoard();
    updateSubtitleDesignPreview();
    startBoardPolling();
});
