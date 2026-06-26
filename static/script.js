const homeSection = document.getElementById('homeSection');
const lectureProjectSection = document.getElementById('lectureProjectSection');
const aiVideoProjectSection = document.getElementById('aiVideoProjectSection');
const videoEditorSection = document.getElementById('videoEditorSection');
const artifactsSection = document.getElementById('artifactsSection');
const settingsSection = document.getElementById('settingsSection');
const navHome = document.getElementById('navHome');
const navVideoEditor = document.getElementById('navVideoEditor');
const navLectureProject = document.getElementById('navLectureProject');
const navArtifacts = document.getElementById('navArtifacts');
const navSettings = document.getElementById('navSettings');
const pageTitle = document.getElementById('pageTitle');
const pageSubtitle = document.getElementById('pageSubtitle');

const boardFileInput = document.getElementById('boardFileInput');
const boardUploadBtn = document.getElementById('boardUploadBtn');
const openScriptJobBtn = document.getElementById('openScriptJobBtn');
const boardSearchInput = document.getElementById('boardSearchInput');
const boardStatusFilter = document.getElementById('boardStatusFilter');
const selectAllCardsBtn = document.getElementById('selectAllCardsBtn');
const clearCardSelectionBtn = document.getElementById('clearCardSelectionBtn');
const downloadSelectedCardsBtn = document.getElementById('downloadSelectedCardsBtn');
const runSelectedPipelineBtn = document.getElementById('runSelectedPipelineBtn');
const deleteSelectedCardsBtn = document.getElementById('deleteSelectedCardsBtn');
const uploadQueue = document.getElementById('uploadQueue');
const jobBoard = document.getElementById('jobBoard');
const batchUploadedPanel = document.getElementById('batchUploadedPanel');
const batchUploadedList = document.getElementById('batchUploadedList');
const selectUploadedBatchBtn = document.getElementById('selectUploadedBatchBtn');
const runUploadedBatchBtn = document.getElementById('runUploadedBatchBtn');
const autoPipelineLanguage = document.getElementById('autoPipelineLanguage');
const autoPipelineOutput = document.getElementById('autoPipelineOutput');
const autoPipelineSubtitlePreset = document.getElementById('autoPipelineSubtitlePreset');
const autoPipelineProvider = document.getElementById('autoPipelineProvider');
const autoPipelineVoice = document.getElementById('autoPipelineVoice');
const autoPipelineTone = document.getElementById('autoPipelineTone');
const autoPipelineVoiceTooltip = document.getElementById('autoPipelineVoiceTooltip');
const autoPipelineVoiceSample = document.getElementById('autoPipelineVoiceSample');
const autoPipelineVoiceSampleStatus = document.getElementById('autoPipelineVoiceSampleStatus');
const artifactKindFilter = document.getElementById('artifactKindFilter');
const artifactLanguageFilter = document.getElementById('artifactLanguageFilter');
const artifactSubtitleFilter = document.getElementById('artifactSubtitleFilter');
const selectAllArtifactsBtn = document.getElementById('selectAllArtifactsBtn');
const clearArtifactSelectionBtn = document.getElementById('clearArtifactSelectionBtn');
const downloadSelectedArtifactsBtn = document.getElementById('downloadSelectedArtifactsBtn');
const deleteSelectedArtifactsBtn = document.getElementById('deleteSelectedArtifactsBtn');
const allArtifactsList = document.getElementById('allArtifactsList');
const editorFileInput = document.getElementById('editorFileInput');
const editorUploadBtn = document.getElementById('editorUploadBtn');
const editorRefreshBtn = document.getElementById('editorRefreshBtn');
const editorFileCount = document.getElementById('editorFileCount');
const editorFileList = document.getElementById('editorFileList');
const editorSelectAllBtn = document.getElementById('editorSelectAllBtn');
const editorClearSelectionBtn = document.getElementById('editorClearSelectionBtn');
const editorSelectedCount = document.getElementById('editorSelectedCount');
const editorCurrentTitle = document.getElementById('editorCurrentTitle');
const editorPreviewPlayer = document.getElementById('editorPreviewPlayer');
const editorStatus = document.getElementById('editorStatus');
const editorArtifactsList = document.getElementById('editorArtifactsList');
const editorLogoIntroPositionSelect = document.getElementById('editorLogoIntroPositionSelect');
const editorLogoIntroSelectedBtn = document.getElementById('editorLogoIntroSelectedBtn');
const editorLogoIntroAllBtn = document.getElementById('editorLogoIntroAllBtn');
const editorTrimStartSeconds = document.getElementById('editorTrimStartSeconds');
const editorTrimEndSeconds = document.getElementById('editorTrimEndSeconds');
const editorTrimBtn = document.getElementById('editorTrimBtn');
const editorConcatPositionSelect = document.getElementById('editorConcatPositionSelect');
const editorBeforeSourceGroup = document.getElementById('editorBeforeSourceGroup');
const editorAfterSourceGroup = document.getElementById('editorAfterSourceGroup');
const editorBeforeExistingSelect = document.getElementById('editorBeforeExistingSelect');
const editorAfterExistingSelect = document.getElementById('editorAfterExistingSelect');
const editorBeforeUploadInput = document.getElementById('editorBeforeUploadInput');
const editorAfterUploadInput = document.getElementById('editorAfterUploadInput');
const editorConcatBtn = document.getElementById('editorConcatBtn');
const lectureSlidesInput = document.getElementById('lectureSlidesInput');
const lectureTimelineInput = document.getElementById('lectureTimelineInput');
const lectureLanguageSelect = document.getElementById('lectureLanguageSelect');
const lectureOutputSelect = document.getElementById('lectureOutputSelect');
const lectureProviderSelect = document.getElementById('lectureProviderSelect');
const lectureVoiceSelect = document.getElementById('lectureVoiceSelect');
const lectureVoiceSampleBtn = document.getElementById('lectureVoiceSampleBtn');
const lectureVoiceSample = document.getElementById('lectureVoiceSample');
const lectureVoiceSampleStatus = document.getElementById('lectureVoiceSampleStatus');
const lectureToneSelect = document.getElementById('lectureToneSelect');
const lectureCreateBtn = document.getElementById('lectureCreateBtn');
const lectureProjectStatus = document.getElementById('lectureProjectStatus');
const lectureValidationResult = document.getElementById('lectureValidationResult');
const aiVideoTopicInput = document.getElementById('aiVideoTopicInput');
const aiVideoLanguageSelect = document.getElementById('aiVideoLanguageSelect');
const aiVideoDurationSelect = document.getElementById('aiVideoDurationSelect');
const aiVideoAudienceInput = document.getElementById('aiVideoAudienceInput');
const aiVideoToneSelect = document.getElementById('aiVideoToneSelect');
const aiVideoAspectRatioSelect = document.getElementById('aiVideoAspectRatioSelect');
const aiVideoImageStylePresetSelect = document.getElementById('aiVideoImageStylePresetSelect');
const aiVideoImageStyleInput = document.getElementById('aiVideoImageStyleInput');
const aiVideoCharacterInput = document.getElementById('aiVideoCharacterInput');
const aiVideoVisualModeSelect = document.getElementById('aiVideoVisualModeSelect');
const aiVideoOutputSelect = document.getElementById('aiVideoOutputSelect');
const aiVideoProviderSelect = document.getElementById('aiVideoProviderSelect');
const aiVideoVoiceSelect = document.getElementById('aiVideoVoiceSelect');
const aiVideoDraftBtn = document.getElementById('aiVideoDraftBtn');
const aiVideoCreateBtn = document.getElementById('aiVideoCreateBtn');
const aiVideoProjectStatus = document.getElementById('aiVideoProjectStatus');
const aiVideoDraftPanel = document.getElementById('aiVideoDraftPanel');

const apiKeyInput = document.getElementById('apiKeyInput');
const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
const apiKeyStatus = document.getElementById('apiKeyStatus');
const aiUsageSummary = document.getElementById('aiUsageSummary');
const aiUsageEvents = document.getElementById('aiUsageEvents');
const refreshAiUsageBtn = document.getElementById('refreshAiUsageBtn');
const aiUsageStartDate = document.getElementById('aiUsageStartDate');
const aiUsageEndDate = document.getElementById('aiUsageEndDate');

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
const generationSrtSourceSelect = document.getElementById('generationSrtSourceSelect');
const generationAudioArtifactSelect = document.getElementById('generationAudioArtifactSelect');
const generationTtsProviderSelect = document.getElementById('generationTtsProviderSelect');
const generationVoiceSelect = document.getElementById('generationVoiceSelect');
const generationGeminiVoiceTooltip = document.getElementById('generationGeminiVoiceTooltip');
const generationGeminiVoiceSample = document.getElementById('generationGeminiVoiceSample');
const generationGeminiVoiceSampleStatus = document.getElementById('generationGeminiVoiceSampleStatus');
const generationToneSelect = document.getElementById('generationToneSelect');
const generationToneCustomInput = document.getElementById('generationToneCustomInput');
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
const srtSourceSettingGroup = document.getElementById('srtSourceSettingGroup');
const audioArtifactSettingGroup = document.getElementById('audioArtifactSettingGroup');
const voiceSettingGroup = document.getElementById('voiceSettingGroup');
const voiceNameSettingGroup = document.getElementById('voiceNameSettingGroup');
const voiceToneSettingGroup = document.getElementById('voiceToneSettingGroup');
const voiceToneCustomGroup = document.getElementById('voiceToneCustomGroup');
const subtitlePresetPanel = document.getElementById('subtitlePresetPanel');
const subtitlePresetSelect = document.getElementById('subtitlePresetSelect');
const subtitlePresetNameInput = document.getElementById('subtitlePresetNameInput');
const saveSubtitlePresetBtn = document.getElementById('saveSubtitlePresetBtn');
const deleteSubtitlePresetBtn = document.getElementById('deleteSubtitlePresetBtn');
const subtitleStylePanel = document.getElementById('subtitleStylePanel');
const productionGenerateBtn = document.getElementById('productionGenerateBtn');
const productionDownloadBtn = document.getElementById('productionDownloadBtn');
const modalArtifacts = document.getElementById('modalArtifacts');
const modalJobPanel = document.getElementById('modalJobPanel');
const modalJobStatus = document.getElementById('modalJobStatus');
const modalCorrectBtn = document.getElementById('modalCorrectBtn');
const modalTranslateBtn = document.getElementById('modalTranslateBtn');
const trimStartSeconds = document.getElementById('trimStartSeconds');
const trimEndSeconds = document.getElementById('trimEndSeconds');
const trimVideoBtn = document.getElementById('trimVideoBtn');
const concatPositionSelect = document.getElementById('concatPositionSelect');
const concatExistingFileSelect = document.getElementById('concatExistingFileSelect');
const concatUploadInput = document.getElementById('concatUploadInput');
const concatAfterExistingFileSelect = document.getElementById('concatAfterExistingFileSelect');
const concatAfterUploadInput = document.getElementById('concatAfterUploadInput');
const concatVideoBtn = document.getElementById('concatVideoBtn');
const editSourceVideoPlayer = document.getElementById('editSourceVideoPlayer');
const videoEditStatus = document.getElementById('videoEditStatus');

let files = [];
let editorFiles = [];
let selectedEditorFileIds = new Set();
let selectedFileIds = new Set();
let recentUploadedFileIds = new Set();
let currentFileId = null;
let currentEditorFileId = null;
let currentFileData = null;
let currentTab = 'subtitles';
let voices = [];
let voiceDefaults = { ko: 'Kore', en: 'Puck' };
let ttsProviders = {};
let voiceSampleMap = {};
let allArtifactsCache = [];
let selectedArtifactIds = new Set();
let activeTtsProvider = 'gemini';
let boardPollTimer = null;
let uploadTaskQueue = [];
let uploadActiveCount = 0;
let uploadSequence = 0;
let uploadHideTimer = null;
const uploadMaxConcurrency = 2;
let currentPreviewMode = 'captioned_dub';
let currentOutputType = 'captioned_dub';
let renderedArtifactsKey = '';
let renderedAllArtifactsKey = '';
let currentAiVideoDraft = null;
let subtitlePresetDirtyGuard = false;
let srtEditDirty = {
    corrected: false,
    english: false
};

const subtitlePresetStorageKey = 'movie_text_subtitle_presets_v1';
const autoPipelineStorageKey = 'movie_text_auto_pipeline_v1';
const customSubtitlePresetValue = '__custom__';
const defaultSubtitlePreset = {
    id: 'default-readable',
    name: '기본 가독성',
    builtIn: true,
    style: {
        font_family: 'Arial',
        font_size: 48,
        position: 'bottom',
        margin_v: 64,
        text_color: '#ffffff',
        outline_color: '#000000',
        outline_width: 2,
        shadow: 1,
        background_enabled: true,
        background_color: '#000000',
        background_opacity: 60
    }
};

const fallbackTtsProviders = {
    gemini: {
        label: 'Gemini',
        languages: ['ko', 'en'],
        defaults: { ko: 'Kore', en: 'Puck' },
        voices: [
            { name: 'Kore', label: 'Kore - Firm', languages: ['ko', 'en'] },
            { name: 'Puck', label: 'Puck - Upbeat', languages: ['ko', 'en'] },
            { name: 'Zephyr', label: 'Zephyr - Bright', languages: ['ko', 'en'] },
            { name: 'Charon', label: 'Charon - Informative', languages: ['ko', 'en'] },
            { name: 'Fenrir', label: 'Fenrir - Excitable', languages: ['ko', 'en'] },
            { name: 'Leda', label: 'Leda - Youthful', languages: ['ko', 'en'] },
            { name: 'Orus', label: 'Orus - Firm', languages: ['ko', 'en'] },
            { name: 'Aoede', label: 'Aoede - Breezy', languages: ['ko', 'en'] }
        ]
    },
    google_cloud: {
        label: 'Google Cloud',
        languages: ['ko', 'en'],
        defaults: { ko: 'ko-KR-Neural2-A', en: 'en-US-Neural2-D' },
        voices: [
            { name: 'ko-KR-Neural2-A', label: 'ko-KR-Neural2-A', languages: ['ko'] },
            { name: 'ko-KR-Neural2-B', label: 'ko-KR-Neural2-B', languages: ['ko'] },
            { name: 'ko-KR-Neural2-C', label: 'ko-KR-Neural2-C', languages: ['ko'] },
            { name: 'en-US-Neural2-D', label: 'en-US-Neural2-D', languages: ['en'] },
            { name: 'en-US-Neural2-A', label: 'en-US-Neural2-A', languages: ['en'] },
            { name: 'en-US-Neural2-C', label: 'en-US-Neural2-C', languages: ['en'] },
            { name: 'en-US-Neural2-E', label: 'en-US-Neural2-E', languages: ['en'] },
            { name: 'en-US-Neural2-F', label: 'en-US-Neural2-F', languages: ['en'] }
        ]
    }
};

const voiceGuideProfiles = {
    Kore: { gender: '중성/여성 쪽', age: '30대', tone: '단단하고 또렷함', best: '한국어 강의, 안내, 신뢰감 있는 내레이션' },
    Puck: { gender: '남성 쪽', age: '20-30대', tone: '밝고 경쾌함', best: '영어 광고, 짧은 설명, 활기 있는 더빙' },
    Zephyr: { gender: '여성 쪽', age: '20-30대', tone: '밝고 산뜻함', best: '친근한 소개, 제품 설명, 가벼운 교육 영상' },
    Charon: { gender: '남성 쪽', age: '30-40대', tone: '정보 전달형', best: '튜토리얼, 뉴스형 설명, 차분한 안내' },
    Fenrir: { gender: '남성 쪽', age: '20-30대', tone: '흥분감 있고 에너지 있음', best: '프로모션, 빠른 템포의 숏폼' },
    Leda: { gender: '여성 쪽', age: '10대 후반-20대', tone: '젊고 가벼움', best: '캐주얼 콘텐츠, 밝은 SNS 영상' },
    Orus: { gender: '남성 쪽', age: '30-40대', tone: '확신 있고 단단함', best: '전문 강의, 발표, 브랜드 신뢰도 강조' },
    Aoede: { gender: '여성 쪽', age: '20-30대', tone: '가볍고 산뜻함', best: '친근한 내레이션, 라이프스타일 영상' },
    Callirrhoe: { gender: '여성 쪽', age: '20-30대', tone: '편안하고 자연스러움', best: '대화형 설명, 부드러운 안내' },
    Autonoe: { gender: '여성 쪽', age: '20-30대', tone: '밝고 선명함', best: '교육 오프닝, 제품 소개' },
    Enceladus: { gender: '남성 쪽', age: '30대', tone: '숨결감 있고 부드러움', best: '감성적인 설명, 차분한 내레이션' },
    Iapetus: { gender: '남성 쪽', age: '30-40대', tone: '깨끗하고 명료함', best: '긴 설명, 정보성 영상' },
    Umbriel: { gender: '남성 쪽', age: '20-30대', tone: '편안하고 캐주얼함', best: '부담 없는 안내, 일반 콘텐츠' },
    Algieba: { gender: '남성 쪽', age: '30대', tone: '매끄럽고 안정적', best: '브랜드 영상, 고급스러운 설명' },
    Despina: { gender: '여성 쪽', age: '30대', tone: '매끄럽고 부드러움', best: '서비스 안내, 차분한 더빙' },
    Erinome: { gender: '여성 쪽', age: '20-30대', tone: '명료하고 깔끔함', best: '교육, 튜토리얼, 정보 요약' },
    Algenib: { gender: '남성 쪽', age: '40대 이상', tone: '거칠고 낮은 질감', best: '강한 인상, 캐릭터성 있는 내레이션' },
    Rasalgethi: { gender: '남성 쪽', age: '30-40대', tone: '설명적이고 안정적', best: '전문 정보, 강의형 콘텐츠' },
    Laomedeia: { gender: '여성 쪽', age: '20-30대', tone: '밝고 활기 있음', best: '홍보 영상, 짧은 광고' },
    Achernar: { gender: '여성 쪽', age: '20-30대', tone: '부드럽고 섬세함', best: '감성 콘텐츠, 차분한 브랜드 소개' },
    Alnilam: { gender: '남성 쪽', age: '30-40대', tone: '단단하고 직선적', best: '권위 있는 설명, 발표형 영상' },
    Schedar: { gender: '여성 쪽', age: '30대', tone: '균일하고 안정적', best: '긴 내레이션, 반복 시청용 콘텐츠' },
    Gacrux: { gender: '여성 쪽', age: '40대 이상', tone: '성숙하고 차분함', best: '신뢰감 있는 안내, 프리미엄 서비스 설명' },
    Pulcherrima: { gender: '여성 쪽', age: '30대', tone: '전면에 나서는 선명함', best: '강조가 필요한 광고, 발표형 더빙' },
    Achird: { gender: '남성 쪽', age: '20-30대', tone: '친근하고 자연스러움', best: '캐주얼 설명, 대화형 콘텐츠' },
    Zubenelgenubi: { gender: '남성 쪽', age: '20-30대', tone: '캐주얼하고 편안함', best: 'SNS 영상, 가벼운 안내' },
    Vindemiatrix: { gender: '여성 쪽', age: '30대', tone: '부드럽고 온화함', best: '교육, 상담형 설명, 긴 영상' },
    Sadachbia: { gender: '여성 쪽', age: '20-30대', tone: '생동감 있고 밝음', best: '숏폼, 프로모션, 활기 있는 영상' },
    Sadaltager: { gender: '남성 쪽', age: '30-40대', tone: '지식 전달형', best: '강의, 기술 설명, 전문 콘텐츠' },
    Sulafat: { gender: '여성 쪽', age: '30대', tone: '따뜻하고 안정적', best: '브랜드 스토리, 차분한 설명' },
};

const voiceGuideProviderNotes = {
    gemini: 'Gemini 음성의 성별/연령은 공식 고정값이 아니라 실제 청감과 스타일 라벨을 기준으로 한 선택 가이드입니다.',
    google_cloud: 'Google Cloud TTS는 언어별 Neural2 음성을 안정적으로 제공합니다. 자연어 톤 지시는 Gemini 음성에 더 적합합니다.',
};

const tonePrompts = {
    bright_natural: 'Read in a bright, warm, and natural conversational tone. Keep the pacing smooth and avoid a robotic delivery.',
    clear_lecture: 'Read clearly like a helpful instructor. Use steady pacing, natural pauses, and emphasize key terms without sounding exaggerated.',
    calm: 'Read in a calm, relaxed, and stable tone. Keep the delivery natural and not too slow.',
    energetic: 'Read with an energetic and friendly tone. Keep it lively but still clear and natural.'
};

const toneLabels = {
    bright_natural: '밝고 자연스럽게',
    clear_lecture: '명확한 강의 톤',
    calm: '차분하게',
    energetic: '활기 있게'
};

function autoPipelineSettings() {
    const provider = autoPipelineProvider?.value || 'gemini';
    const language = autoPipelineLanguage?.value || 'en';
    const selectedPreset = allSubtitlePresets().find(preset => preset.id === autoPipelineSubtitlePreset?.value)
        || defaultSubtitlePreset;
    return {
        language,
        final_output: autoPipelineOutput?.value || 'captioned_dub_video',
        tts_provider: provider,
        voice_name: autoPipelineVoice?.disabled ? null : autoPipelineVoice?.value,
        style_prompt: tonePrompts[autoPipelineTone?.value] || tonePrompts.bright_natural,
        srt_source: language === 'en' ? 'english' : 'corrected',
        generate_corrected: true,
        generate_english: language === 'en',
        subtitle_style: selectedPreset.style || defaultSubtitlePreset.style
    };
}

function saveAutoPipelineSettings() {
    localStorage.setItem(autoPipelineStorageKey, JSON.stringify({
        language: autoPipelineLanguage?.value || 'en',
        final_output: autoPipelineOutput?.value || 'captioned_dub_video',
        subtitle_preset: autoPipelineSubtitlePreset?.value || defaultSubtitlePreset.id,
        tts_provider: autoPipelineProvider?.value || 'gemini',
        voice_name: autoPipelineVoice?.value || '',
        tone: autoPipelineTone?.value || 'bright_natural'
    }));
}

function loadAutoPipelineSettings() {
    try {
        const saved = JSON.parse(localStorage.getItem(autoPipelineStorageKey) || '{}');
        if (autoPipelineLanguage && saved.language) autoPipelineLanguage.value = saved.language;
        if (autoPipelineOutput && saved.final_output) autoPipelineOutput.value = saved.final_output;
        populateAutoPipelineSubtitlePreset(saved.subtitle_preset || defaultSubtitlePreset.id);
        if (autoPipelineProvider && saved.tts_provider) {
            populateTtsProviderSelect(autoPipelineProvider, saved.tts_provider);
        }
        if (autoPipelineTone && saved.tone) autoPipelineTone.value = saved.tone;
        populateAutoPipelineVoice(saved.voice_name || '');
    } catch {
        populateAutoPipelineSubtitlePreset();
        populateAutoPipelineVoice();
    }
}

function populateAutoPipelineSubtitlePreset(selectedId = autoPipelineSubtitlePreset?.value || defaultSubtitlePreset.id) {
    if (!autoPipelineSubtitlePreset) return;
    const presets = allSubtitlePresets();
    autoPipelineSubtitlePreset.innerHTML = presets.map(preset =>
        `<option value="${escapeHtml(preset.id)}">${escapeHtml(preset.name)}</option>`
    ).join('');
    autoPipelineSubtitlePreset.value = presets.some(preset => preset.id === selectedId) ? selectedId : defaultSubtitlePreset.id;
}

function populateTtsProviderSelect(select, preferredProvider = '') {
    if (!select) return;
    const providers = Object.entries(ttsProviders).filter(([, provider]) => {
        const voices = provider?.voices || [];
        return voices.length > 0;
    });
    const safeProviders = providers.length ? providers : Object.entries(fallbackTtsProviders);
    const selected = preferredProvider && safeProviders.some(([key]) => key === preferredProvider)
        ? preferredProvider
        : (safeProviders.some(([key]) => key === 'gemini') ? 'gemini' : safeProviders[0]?.[0] || '');
    select.innerHTML = safeProviders.map(([key, provider]) =>
        `<option value="${escapeHtml(key)}">${escapeHtml(provider.label || key)}</option>`
    ).join('');
    select.value = selected;
}

function populateTtsProviderSelects() {
    populateTtsProviderSelect(autoPipelineProvider, autoPipelineProvider?.value || activeTtsProvider);
    populateTtsProviderSelect(lectureProviderSelect, lectureProviderSelect?.value || 'gemini');
    populateTtsProviderSelect(aiVideoProviderSelect, aiVideoProviderSelect?.value || 'gemini');
    populateTtsProviderSelect(generationTtsProviderSelect, generationTtsProviderSelect?.value || 'gemini');
}

function populateAutoPipelineVoice(preferredVoice = '') {
    if (!autoPipelineVoice) return;
    const provider = autoPipelineProvider?.value || 'gemini';
    const language = autoPipelineLanguage?.value || 'en';
    const providerData = ttsProviders[provider] || fallbackTtsProviders[provider];
    const supportedLanguages = providerData?.languages || [];
    const providerSupportsLanguage = supportedLanguages.length === 0 || supportedLanguages.includes(language);
    const voicesForProvider = providerSupportsLanguage
        ? (providerData?.voices || []).filter(voice => {
            const languages = voice.languages || [];
            return languages.length === 0 || languages.includes(language);
        })
        : [];
    autoPipelineVoice.disabled = voicesForProvider.length === 0;
    if (!voicesForProvider.length) {
        autoPipelineVoice.innerHTML = '<option value="">지원되는 음성이 없습니다</option>';
        updateVoiceGuideTooltips();
        return;
    }
    const defaultVoice = preferredVoice || providerData?.defaults?.[language] || voicesForProvider[0].name;
    autoPipelineVoice.innerHTML = voicesForProvider.map(voice =>
        `<option value="${voice.name}" ${voice.name === defaultVoice ? 'selected' : ''}>${escapeHtml(voiceOptionText(provider, voice))}</option>`
    ).join('');
    updateVoiceGuideTooltips();
    updateVoiceSamplePlayers();
}

function populateLectureVoice(preferredVoice = '') {
    if (!lectureVoiceSelect) return;
    const provider = lectureProviderSelect?.value || 'gemini';
    const language = lectureLanguageSelect?.value || 'ko';
    const providerData = ttsProviders[provider] || fallbackTtsProviders[provider];
    const supportedLanguages = providerData?.languages || [];
    const providerSupportsLanguage = supportedLanguages.length === 0 || supportedLanguages.includes(language);
    const voicesForProvider = providerSupportsLanguage
        ? (providerData?.voices || []).filter(voice => {
            const languages = voice.languages || [];
            return languages.length === 0 || languages.includes(language);
        })
        : [];
    lectureVoiceSelect.disabled = voicesForProvider.length === 0;
    if (!voicesForProvider.length) {
        lectureVoiceSelect.innerHTML = '<option value="">지원되는 음성이 없습니다</option>';
        updateVoiceSamplePlayers();
        return;
    }
    const defaultVoice = preferredVoice || providerData?.defaults?.[language] || voicesForProvider[0].name;
    lectureVoiceSelect.innerHTML = voicesForProvider.map(voice =>
        `<option value="${voice.name}" ${voice.name === defaultVoice ? 'selected' : ''}>${escapeHtml(voiceOptionText(provider, voice))}</option>`
    ).join('');
    updateVoiceSamplePlayers();
}

function populateAiVideoVoice(preferredVoice = '') {
    if (!aiVideoVoiceSelect) return;
    const provider = aiVideoProviderSelect?.value || 'gemini';
    const language = aiVideoLanguageSelect?.value || 'ko';
    const providerData = ttsProviders[provider] || fallbackTtsProviders[provider];
    const supportedLanguages = providerData?.languages || [];
    const providerSupportsLanguage = supportedLanguages.length === 0 || supportedLanguages.includes(language);
    const voicesForProvider = providerSupportsLanguage
        ? (providerData?.voices || []).filter(voice => {
            const languages = voice.languages || [];
            return languages.length === 0 || languages.includes(language);
        })
        : [];
    aiVideoVoiceSelect.disabled = voicesForProvider.length === 0;
    if (!voicesForProvider.length) {
        aiVideoVoiceSelect.innerHTML = '<option value="">지원되는 음성이 없습니다</option>';
        return;
    }
    const defaultVoice = preferredVoice || providerData?.defaults?.[language] || voicesForProvider[0].name;
    aiVideoVoiceSelect.innerHTML = voicesForProvider.map(voice =>
        `<option value="${voice.name}" ${voice.name === defaultVoice ? 'selected' : ''}>${escapeHtml(voiceOptionText(provider, voice))}</option>`
    ).join('');
}

function renderLectureValidation(validation) {
    if (!lectureValidationResult) return;
    const warnings = validation?.warnings || [];
    const items = validation?.items || [];
    lectureValidationResult.classList.remove('hidden');
    lectureValidationResult.innerHTML = `
        <strong>검증 완료</strong>
        <span>슬라이드 ${items.length}장의 대본을 확인했습니다.</span>
        ${warnings.length ? `<ul>${warnings.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : '<span>경고 없음</span>'}
    `;
}

function renderLectureErrors(detail) {
    if (!lectureValidationResult) return;
    const payload = typeof detail === 'object' ? detail : { errors: [String(detail || '강의 프로젝트 생성 실패')] };
    const errors = payload.errors || [String(detail || '강의 프로젝트 생성 실패')];
    const warnings = payload.warnings || [];
    lectureValidationResult.classList.remove('hidden');
    lectureValidationResult.innerHTML = `
        <strong>검증 실패</strong>
        <ul>${errors.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        ${warnings.length ? `<span>경고</span><ul>${warnings.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
    `;
}

async function createLectureProject() {
    const slideFiles = Array.from(lectureSlidesInput?.files || []);
    const timelineFile = lectureTimelineInput?.files?.[0];
    if (!slideFiles.length || !timelineFile) {
        alert('슬라이드 파일과 장표별 대본 엑셀을 모두 선택하세요.');
        return;
    }
    const restore = setActionBusy(lectureCreateBtn, '강의 영상 생성 등록 중...');
    if (lectureProjectStatus) {
        lectureProjectStatus.textContent = '장표 파일과 장표별 대본 엑셀 검증 중...';
        lectureProjectStatus.classList.remove('error');
    }
    if (lectureValidationResult) lectureValidationResult.classList.add('hidden');
    const formData = new FormData();
    slideFiles.forEach(file => formData.append('slides', file));
    formData.append('timeline_file', timelineFile);
    formData.append('language', lectureLanguageSelect?.value || 'ko');
    formData.append('final_output', lectureOutputSelect?.value || 'captioned_dub_video');
    formData.append('tts_provider', lectureProviderSelect?.value || 'gemini');
    if (lectureVoiceSelect && !lectureVoiceSelect.disabled && lectureVoiceSelect.value) {
        formData.append('voice_name', lectureVoiceSelect.value);
    }
    formData.append('style_prompt', tonePrompts[lectureToneSelect?.value] || tonePrompts.clear_lecture);
    formData.append('subtitle_style', JSON.stringify(getSubtitleStyleOptions()));
    try {
        const response = await fetch('/api/lecture-projects', { method: 'POST', body: formData });
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw data;
        }
        renderLectureValidation(data.validation || {});
        if (lectureProjectStatus) lectureProjectStatus.textContent = '작업이 등록되었습니다. 보드에서 진행 상황을 확인하세요.';
        lectureSlidesInput.value = '';
        lectureTimelineInput.value = '';
        recentUploadedFileIds.add(data.file.id);
        await loadBoard();
        showSection('home');
        openFileModal(data.file.id);
    } catch (error) {
        const detail = error?.detail || error?.message || error;
        renderLectureErrors(detail);
        if (lectureProjectStatus) {
            lectureProjectStatus.textContent = '검증 또는 등록 실패';
            lectureProjectStatus.classList.add('error');
        }
    } finally {
        restore();
    }
}

function aiVideoDraftRequestPayload() {
    const characterNames = [...(aiVideoCharacterInput?.files || [])]
        .map(file => file.name.replace(/\.[^.]+$/, '').trim())
        .filter(Boolean);
    return {
        topic: aiVideoTopicInput?.value?.trim() || '',
        language: aiVideoLanguageSelect?.value || 'ko',
        target_duration: aiVideoDurationSelect?.value || '1-3분',
        audience: aiVideoAudienceInput?.value?.trim() || '일반 시청자',
        tone: aiVideoToneSelect?.value || '명확하고 자연스럽게',
        image_style: aiVideoImageStyleInput?.value?.trim() || 'clean modern editorial illustration, cinematic lighting',
        aspect_ratio: aiVideoAspectRatioSelect?.value || '9:16',
        character_names: characterNames
    };
}

function renderAiVideoDraft(draft) {
    if (!aiVideoDraftPanel) return;
    currentAiVideoDraft = draft;
    aiVideoDraftPanel.classList.remove('hidden');
    aiVideoDraftPanel.innerHTML = `
        <div class="ai-video-draft-header">
            <div>
                <p class="workflow-kicker">shorts draft</p>
                <h3>${escapeHtml(draft.title || 'AI 영상 초안')}</h3>
                <p>${escapeHtml(draft.summary || '')}</p>
            </div>
            <span>${(draft.scenes || []).length} scenes</span>
        </div>
        <div class="ai-video-scenes">
            ${(draft.scenes || []).map(scene => `
                <article class="ai-video-scene" data-ai-scene="${scene.scene_no}">
                    <header>
                        <strong>장면 ${scene.scene_no}</strong>
                    </header>
                    <div class="ai-video-scene-grid">
                        <label>
                            <span>장면 유형</span>
                            <select class="api-key-input" data-ai-scene-kind>
                                <option value="veo_clip" ${scene.scene_kind === 'veo_clip' ? 'selected' : ''}>Veo 영상</option>
                                <option value="image_narration" ${scene.scene_kind === 'image_narration' ? 'selected' : ''}>이미지+내레이션</option>
                            </select>
                        </label>
                        <label>
                            <span>오디오</span>
                            <select class="api-key-input" data-ai-scene-audio>
                                <option value="narrator" ${scene.audio_mode === 'narrator' ? 'selected' : ''}>내레이션</option>
                                <option value="veo_audio" ${scene.audio_mode === 'veo_audio' ? 'selected' : ''}>영상 자체 음성/효과음</option>
                                <option value="silent" ${scene.audio_mode === 'silent' ? 'selected' : ''}>무음</option>
                            </select>
                        </label>
                        <label>
                            <span>길이(초)</span>
                            <input class="api-key-input" type="number" min="2" max="8" step="1" data-ai-scene-duration value="${escapeHtml(String(scene.duration_seconds || 5))}">
                        </label>
                    </div>
                    <label>
                        <span>기획/내레이션</span>
                        <textarea class="api-key-input" rows="4" data-ai-scene-script>${escapeHtml(scene.script || '')}</textarea>
                    </label>
                    <label>
                        <span>영상 프롬프트</span>
                        <textarea class="api-key-input" rows="4" data-ai-scene-video-prompt>${escapeHtml(scene.video_prompt || '')}</textarea>
                    </label>
                    <label>
                        <span>영상 내 대사</span>
                        <textarea class="api-key-input" rows="2" data-ai-scene-dialogue>${escapeHtml(scene.dialogue || '')}</textarea>
                    </label>
                    <label>
                        <span>효과음/분위기음</span>
                        <input class="api-key-input" type="text" data-ai-scene-sound value="${escapeHtml(scene.sound_design || '')}">
                    </label>
                    <label>
                        <span>자막</span>
                        <input class="api-key-input" type="text" data-ai-scene-subtitle value="${escapeHtml(scene.script || '')}" disabled>
                    </label>
                    <label>
                        <span>사용 캐릭터</span>
                        <input class="api-key-input" type="text" data-ai-scene-characters value="${escapeHtml((scene.character_usage || []).join(', '))}">
                    </label>
                    <label>
                        <span>캐릭터 역할</span>
                        <input class="api-key-input" type="text" data-ai-scene-character-role value="${escapeHtml(scene.character_role || '')}">
                    </label>
                    <label>
                        <span>비주얼 메모</span>
                        <input class="api-key-input" type="text" data-ai-scene-notes value="${escapeHtml(scene.visual_notes || '')}">
                    </label>
                </article>
            `).join('')}
        </div>
    `;
    if (aiVideoCreateBtn) aiVideoCreateBtn.disabled = false;
}

function collectAiVideoScenes() {
    return [...(aiVideoDraftPanel?.querySelectorAll('[data-ai-scene]') || [])].map((item, index) => ({
        scene_no: Number(item.dataset.aiScene || index + 1),
        script: item.querySelector('[data-ai-scene-script]')?.value?.trim() || '',
        image_prompt: '',
        visual_notes: item.querySelector('[data-ai-scene-notes]')?.value?.trim() || '',
        scene_kind: item.querySelector('[data-ai-scene-kind]')?.value || 'veo_clip',
        audio_mode: item.querySelector('[data-ai-scene-audio]')?.value || 'narrator',
        video_prompt: item.querySelector('[data-ai-scene-video-prompt]')?.value?.trim() || '',
        dialogue: item.querySelector('[data-ai-scene-dialogue]')?.value?.trim() || '',
        sound_design: item.querySelector('[data-ai-scene-sound]')?.value?.trim() || '',
        subtitle_text: item.querySelector('[data-ai-scene-subtitle]')?.value?.trim() || '',
        duration_seconds: Number(item.querySelector('[data-ai-scene-duration]')?.value || 5),
        character_usage: (item.querySelector('[data-ai-scene-characters]')?.value || '')
            .split(',')
            .map(name => name.trim())
            .filter(Boolean),
        character_role: item.querySelector('[data-ai-scene-character-role]')?.value?.trim() || ''
    })).filter(scene => scene.script || scene.video_prompt);
}

async function createAiVideoDraft() {
    const payload = aiVideoDraftRequestPayload();
    if (!payload.topic) {
        alert('영상 주제를 입력하세요.');
        return;
    }
    const restore = setActionBusy(aiVideoDraftBtn, '초안 생성 중...');
    if (aiVideoProjectStatus) {
        aiVideoProjectStatus.textContent = '숏츠 초안을 생성 중...';
        aiVideoProjectStatus.classList.remove('error');
    }
    if (aiVideoCreateBtn) aiVideoCreateBtn.disabled = true;
    try {
        const data = await postJson('/api/ai-video-projects/draft', payload);
        renderAiVideoDraft(data.draft || {});
        if (aiVideoProjectStatus) aiVideoProjectStatus.textContent = '초안이 생성되었습니다. 장면별 내레이션과 영상 프롬프트를 확인하세요.';
    } catch (error) {
        if (aiVideoProjectStatus) {
            aiVideoProjectStatus.textContent = `초안 생성 실패: ${error.message}`;
            aiVideoProjectStatus.classList.add('error');
        }
    } finally {
        restore();
    }
}

async function createAiVideoProject() {
    const scenes = collectAiVideoScenes();
    if (!scenes.length) {
        alert('생성할 장면이 없습니다. 먼저 초안을 생성하세요.');
        return;
    }
    const restore = setActionBusy(aiVideoCreateBtn, '영상 생성 등록 중...');
    if (aiVideoProjectStatus) {
        aiVideoProjectStatus.textContent = '음성/영상 생성 작업 등록 중...';
        aiVideoProjectStatus.classList.remove('error');
    }
    try {
        const payload = {
            ...aiVideoDraftRequestPayload(),
            draft_id: currentAiVideoDraft?.draft_id || '',
            title: currentAiVideoDraft?.title || aiVideoTopicInput?.value?.trim() || 'AI 영상',
            scenes,
            visual_mode: aiVideoVisualModeSelect?.value || 'veo',
            visual_provider: 'none',
            final_output: aiVideoOutputSelect?.value || 'captioned_dub_video',
            tts_provider: aiVideoProviderSelect?.value || 'gemini',
            voice_name: aiVideoVoiceSelect?.disabled ? '' : aiVideoVoiceSelect?.value,
            style_prompt: tonePrompts.clear_lecture,
            subtitle_style: getSubtitleStyleOptions()
        };
        let data;
        if (aiVideoCharacterInput?.files?.length) {
            const formData = new FormData();
            formData.append('payload', JSON.stringify(payload));
            [...aiVideoCharacterInput.files].forEach(file => formData.append('character_images', file));
            const response = await fetch('/api/ai-video-projects/with-assets', {
                method: 'POST',
                body: formData
            });
            data = await response.json();
            if (!response.ok || data.success === false) {
                throw new Error(data.detail || data.message || 'AI 영상 생성 등록 실패');
            }
        } else {
            data = await postJson('/api/ai-video-projects', payload);
        }
        if (aiVideoProjectStatus) aiVideoProjectStatus.textContent = '작업이 등록되었습니다. 보드에서 진행 상황을 확인하세요.';
        recentUploadedFileIds.add(data.file.id);
        await loadBoard();
        showSection('home');
        openFileModal(data.file.id);
    } catch (error) {
        if (aiVideoProjectStatus) {
            aiVideoProjectStatus.textContent = `영상 생성 등록 실패: ${error.message}`;
            aiVideoProjectStatus.classList.add('error');
        }
    } finally {
        restore();
    }
}

function voicesForGuide(provider, language) {
    const providerData = ttsProviders[provider] || fallbackTtsProviders[provider];
    const supportedLanguages = providerData?.languages || [];
    if (supportedLanguages.length && !supportedLanguages.includes(language)) return [];
    return (providerData?.voices || []).filter(voice => {
        const languages = voice.languages || [];
        return languages.length === 0 || languages.includes(language);
    });
}

function voiceGuideLabel(voice) {
    const label = voice.label || voice.name;
    return label.includes(' - ') ? label : `${label}`;
}

function voiceOptionText(provider, voice) {
    return voiceGuideLabel(voice);
}

function voiceGuideHtml(provider, language) {
    const providerLabel = (ttsProviders[provider] || fallbackTtsProviders[provider])?.label || provider;
    const voicesList = voicesForGuide(provider, language);
    if (!voicesList.length) {
        return `
            <strong class="voice-guide-title">${escapeHtml(providerLabel)} 음성</strong>
            <div class="voice-guide-note">현재 선택한 언어에서 지원되는 음성이 없습니다.</div>
        `;
    }
    const note = voiceGuideProviderNotes[provider] || '성별/나이대는 실제 청감 기준의 선택 가이드입니다.';
    return `
        <strong class="voice-guide-title">${escapeHtml(providerLabel)} 음성 특징</strong>
        <div class="voice-guide-note">${escapeHtml(note)}</div>
        <div class="voice-guide-list">
            ${voicesList.map(voice => {
                const profile = voiceGuideProfiles[voice.name] || {
                    gender: '청감 확인 필요',
                    age: '범용',
                    tone: voice.label?.split(' - ')[1] || '기본',
                    best: '샘플 생성 후 콘텐츠 톤에 맞춰 선택'
                };
                return `
                    <div class="voice-guide-item">
                        <strong>${escapeHtml(voiceGuideLabel(voice))}</strong>
                        <div class="voice-guide-meta">성별: ${escapeHtml(profile.gender)} · 나이대: ${escapeHtml(profile.age)} · 톤: ${escapeHtml(profile.tone)}</div>
                        <div class="voice-guide-desc">추천: ${escapeHtml(profile.best)}</div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function updateVoiceGuideTooltips() {
    if (autoPipelineVoiceTooltip) {
        autoPipelineVoiceTooltip.innerHTML = voiceGuideHtml(autoPipelineProvider?.value || 'gemini', autoPipelineLanguage?.value || 'en');
    }
    if (generationGeminiVoiceTooltip) {
        generationGeminiVoiceTooltip.innerHTML = voiceGuideHtml('gemini', generationLanguageSelect?.value || 'en');
    }
}

function voiceSampleKey(provider, voiceName) {
    return `${provider || ''}:${voiceName || ''}`;
}

async function loadVoiceSamples() {
    try {
        const response = await fetch('/api/tts/voice-samples');
        const data = await response.json();
        voiceSampleMap = {};
        (data.samples || []).forEach(sample => {
            voiceSampleMap[voiceSampleKey(sample.provider, sample.voice_name)] = sample;
        });
    } catch {
        voiceSampleMap = {};
    }
    updateVoiceSamplePlayers();
}

function setVoiceSamplePlayer(audio, status, provider, voiceName) {
    if (!audio || !status) return;
    const row = audio.closest('.voice-sample-row');
    const previewButton = row?.querySelector('button');
    row?.classList.remove('ready', 'missing', 'error');
    if (!provider || !voiceName) {
        audio.removeAttribute('src');
        if (previewButton) previewButton.disabled = true;
        status.textContent = '음성을 선택하면 샘플을 들을 수 있습니다.';
        row?.classList.add('missing');
        return;
    }
    const sample = voiceSampleMap[voiceSampleKey(provider, voiceName)];
    if (sample?.exists && sample.sample_url) {
        audio.src = sample.sample_url;
        if (previewButton) previewButton.disabled = false;
        status.textContent = '샘플 MP3 준비됨';
        row?.classList.add('ready');
        return;
    }
    audio.removeAttribute('src');
    if (previewButton) previewButton.disabled = true;
    status.textContent = '샘플 MP3가 아직 생성되지 않았습니다.';
    row?.classList.add('missing');
}

async function playLectureVoiceSample() {
    if (!lectureVoiceSample || !lectureVoiceSample.src) return;
    try {
        lectureVoiceSample.currentTime = 0;
        await lectureVoiceSample.play();
    } catch {
        if (lectureVoiceSampleStatus) {
            lectureVoiceSampleStatus.textContent = '브라우저에서 샘플 재생을 시작할 수 없습니다.';
        }
    }
}

function updateVoiceSamplePlayers() {
    setVoiceSamplePlayer(
        autoPipelineVoiceSample,
        autoPipelineVoiceSampleStatus,
        autoPipelineProvider?.value || 'gemini',
        autoPipelineVoice?.disabled ? '' : autoPipelineVoice?.value
    );
    setVoiceSamplePlayer(
        generationGeminiVoiceSample,
        generationGeminiVoiceSampleStatus,
        'gemini',
        generationVoiceSelect?.disabled ? '' : generationVoiceSelect?.value
    );
    setVoiceSamplePlayer(
        lectureVoiceSample,
        lectureVoiceSampleStatus,
        lectureProviderSelect?.value || 'gemini',
        lectureVoiceSelect?.disabled ? '' : lectureVoiceSelect?.value
    );
}

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeCssIdent(value) {
    if (window.CSS?.escape) return CSS.escape(value);
    return String(value || '').replace(/["\\]/g, '\\$&');
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
        return 'Gemini TTS Vertex AI 모델별 분당 요청 쿼터를 초과했습니다. Vertex를 사용해도 모델별 RPM 쿼터는 그대로 적용됩니다. 긴 SRT를 한 줄씩 생성하면 요청 수가 급격히 늘어나므로 묶음 생성으로 줄이고, 반복 생성 직후에는 잠시 기다린 뒤 다시 시도하세요. 계속 발생하면 Vertex AI에서 Gemini TTS 모델 쿼터 증설이 필요합니다.';
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

function setSubtitleStyleOptions(style = {}) {
    subtitlePresetDirtyGuard = true;
    if (subtitleFontFamily && style.font_family) subtitleFontFamily.value = style.font_family;
    if (subtitleFontSize) subtitleFontSize.value = style.font_size ?? 48;
    if (subtitlePosition) subtitlePosition.value = style.position || 'bottom';
    if (subtitleMarginV) subtitleMarginV.value = style.margin_v ?? 64;
    if (subtitleTextColor) subtitleTextColor.value = style.text_color || '#ffffff';
    if (subtitleOutlineColor) subtitleOutlineColor.value = style.outline_color || '#000000';
    if (subtitleOutlineWidth) subtitleOutlineWidth.value = style.outline_width ?? 2;
    if (subtitleShadow) subtitleShadow.value = style.shadow ?? 1;
    if (subtitleBackgroundEnabled) subtitleBackgroundEnabled.checked = style.background_enabled !== false;
    if (subtitleBackgroundColor) subtitleBackgroundColor.value = style.background_color || '#000000';
    if (subtitleBackgroundOpacity) subtitleBackgroundOpacity.value = style.background_opacity ?? 60;
    subtitlePresetDirtyGuard = false;
    updateSubtitleDesignPreview();
}

function loadSavedSubtitlePresets() {
    try {
        const parsed = JSON.parse(localStorage.getItem(subtitlePresetStorageKey) || '[]');
        return Array.isArray(parsed)
            ? parsed.filter(item => item && item.id && item.name && item.style)
            : [];
    } catch {
        return [];
    }
}

function saveSubtitlePresets(presets) {
    localStorage.setItem(subtitlePresetStorageKey, JSON.stringify(presets.filter(item => !item.builtIn)));
}

function allSubtitlePresets() {
    return [defaultSubtitlePreset, ...loadSavedSubtitlePresets()];
}

function renderSubtitlePresetSelect(selectedId = subtitlePresetSelect?.value || defaultSubtitlePreset.id) {
    if (!subtitlePresetSelect) return;
    const presets = allSubtitlePresets();
    subtitlePresetSelect.innerHTML = [
        `<option value="${customSubtitlePresetValue}">직접 설정</option>`,
        ...presets.map(preset => `<option value="${escapeHtml(preset.id)}">${escapeHtml(preset.name)}</option>`)
    ].join('');
    subtitlePresetSelect.value = presets.some(preset => preset.id === selectedId) ? selectedId : defaultSubtitlePreset.id;
    const selected = presets.find(preset => preset.id === subtitlePresetSelect.value);
    if (subtitlePresetNameInput && selected) subtitlePresetNameInput.value = selected.builtIn ? '' : selected.name;
    if (deleteSubtitlePresetBtn) deleteSubtitlePresetBtn.disabled = !selected || selected.builtIn;
}

function applySelectedSubtitlePreset() {
    if (!subtitlePresetSelect || subtitlePresetSelect.value === customSubtitlePresetValue) return;
    const selected = allSubtitlePresets().find(preset => preset.id === subtitlePresetSelect.value);
    if (!selected) return;
    if (subtitlePresetNameInput) subtitlePresetNameInput.value = selected.builtIn ? '' : selected.name;
    if (deleteSubtitlePresetBtn) deleteSubtitlePresetBtn.disabled = Boolean(selected.builtIn);
    setSubtitleStyleOptions(selected.style);
}

function markSubtitlePresetAsCustom() {
    if (subtitlePresetDirtyGuard || !subtitlePresetSelect) return;
    subtitlePresetSelect.value = customSubtitlePresetValue;
    if (deleteSubtitlePresetBtn) deleteSubtitlePresetBtn.disabled = true;
}

function saveCurrentSubtitlePreset() {
    const name = (subtitlePresetNameInput?.value || '').trim();
    if (!name) {
        alert('저장할 프리셋 이름을 입력해주세요.');
        subtitlePresetNameInput?.focus();
        return;
    }
    const presets = loadSavedSubtitlePresets();
    const selectedId = subtitlePresetSelect?.value || '';
    const selected = presets.find(preset => preset.id === selectedId);
    const duplicate = presets.find(preset => preset.name === name);
    const id = selected?.id || duplicate?.id || `subtitle-preset-${Date.now()}`;
    const nextPreset = {
        id,
        name,
        style: getSubtitleStyleOptions(),
        updated_at: new Date().toISOString()
    };
    const nextPresets = [nextPreset, ...presets.filter(preset => preset.id !== id && preset.name !== name)];
    saveSubtitlePresets(nextPresets);
    renderSubtitlePresetSelect(id);
    populateAutoPipelineSubtitlePreset(id);
    saveAutoPipelineSettings();
}

function deleteCurrentSubtitlePreset() {
    if (!subtitlePresetSelect) return;
    const selectedId = subtitlePresetSelect.value;
    const selected = loadSavedSubtitlePresets().find(preset => preset.id === selectedId);
    if (!selected) return;
    saveSubtitlePresets(loadSavedSubtitlePresets().filter(preset => preset.id !== selectedId));
    renderSubtitlePresetSelect(defaultSubtitlePreset.id);
    populateAutoPipelineSubtitlePreset(defaultSubtitlePreset.id);
    saveAutoPipelineSettings();
    applySelectedSubtitlePreset();
}

function initializeSubtitlePresets() {
    renderSubtitlePresetSelect(defaultSubtitlePreset.id);
    populateAutoPipelineSubtitlePreset(defaultSubtitlePreset.id);
    applySelectedSubtitlePreset();
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
    if (subtitleBackgroundColor) subtitleBackgroundColor.disabled = !style.background_enabled;
    if (subtitleBackgroundOpacity) subtitleBackgroundOpacity.disabled = !style.background_enabled;
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
    if (section === 'ai_video_project') section = 'home';
    homeSection.classList.toggle('hidden', section !== 'home');
    if (lectureProjectSection) lectureProjectSection.classList.toggle('hidden', section !== 'lecture_project');
    if (aiVideoProjectSection) aiVideoProjectSection.classList.add('hidden');
    if (videoEditorSection) videoEditorSection.classList.toggle('hidden', section !== 'video_editor');
    artifactsSection.classList.toggle('hidden', section !== 'artifacts');
    settingsSection.classList.toggle('hidden', section !== 'settings');
    if (navHome) navHome.classList.toggle('active', section === 'home');
    if (navLectureProject) navLectureProject.classList.toggle('active', section === 'lecture_project');
    if (navVideoEditor) navVideoEditor.classList.toggle('active', section === 'video_editor');
    navArtifacts.classList.toggle('active', section === 'artifacts');
    navSettings.classList.toggle('active', section === 'settings');
    document.querySelectorAll('.workspace-card[data-open-workspace]').forEach(card => {
        card.classList.toggle('active', card.dataset.openWorkspace === section);
    });
    const pageMeta = {
        home: ['더빙 작업', '원본 영상을 전달하고, SRT 자막과 번역 음성을 생성합니다.'],
        lecture_project: ['영상 생성', '발표 장표와 대본을 기반으로 음성, 자막, 영상을 생성합니다.'],
        video_editor: ['영상 편집', '자르기, 붙이기, 인트로 등 간단한 작업을 수행합니다.'],
        artifacts: ['전체 산출물', '생성된 MP3, 자막 영상, 더빙 영상, 편집 영상을 한 곳에서 확인합니다.'],
        settings: ['설정', 'API 키와 작업 환경을 관리합니다.'],
    };
    const [title, subtitle] = pageMeta[section] || pageMeta.home;
    if (pageTitle) pageTitle.textContent = title;
    if (pageSubtitle) pageSubtitle.textContent = subtitle;
    if (section === 'video_editor') loadEditorFiles();
    if (section === 'artifacts') loadAllArtifacts();
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
    renderBatchUploadedList();
    if (!artifactsSection?.classList.contains('hidden')) loadAllArtifacts();
}

function startBoardPolling() {
    if (boardPollTimer) clearInterval(boardPollTimer);
    boardPollTimer = setInterval(async () => {
        await loadBoard();
        if (!fileModal.classList.contains('hidden') && currentFileId) {
            await refreshModalFile();
        }
    }, 2500);
}

async function uploadVideos(fileList) {
    const uploadFiles = Array.from(fileList || []);
    if (uploadFiles.length === 0) return;
    saveAutoPipelineSettings();
    recentUploadedFileIds.clear();
    renderBatchUploadedList();

    uploadQueue.classList.remove('hidden');
    uploadQueue.innerHTML = `
        <div class="queue-summary">선택한 영상 ${uploadFiles.length}개 처리 중 · CPU 준비 2개 병렬 / GPU 음성 인식 1개 순차</div>
        ${uploadFiles.map(file => `
            <div class="queue-item" data-upload-name="${escapeHtml(file.name)}">
                <strong>${escapeHtml(file.name)}</strong>
                <span>업로드 대기</span>
            </div>
        `).join('')}
    `;

    async function uploadOne(file, index) {
        const formData = new FormData();
        formData.append('files', file);
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
                const active = event.filename
                    ? uploadQueue.querySelector(`.queue-item[data-upload-name="${escapeCssIdent(event.filename)}"] span`)
                    : uploadQueue.querySelector('.queue-item span');
                if (active && event.message) active.textContent = event.message;
                if (event.file_id) {
                    if (event.status === 'completed') {
                        recentUploadedFileIds.add(event.file_id);
                    }
                    await loadBoard();
                    renderBatchUploadedList();
                    if (uploadFiles.length === 1 && event.status === 'completed' && (fileModal.classList.contains('hidden') || currentFileId !== event.file_id)) {
                        await openFileModal(event.file_id);
                    } else if (!fileModal.classList.contains('hidden') && currentFileId === event.file_id) {
                        await refreshModalFile();
                    }
                } else if (event.status === 'completed') {
                    await loadBoard();
                }
            }
        }
    }

    const uploadConcurrency = Math.min(2, uploadFiles.length);
    let nextIndex = 0;

    async function worker() {
        while (nextIndex < uploadFiles.length) {
            const index = nextIndex++;
            const file = uploadFiles[index];
            try {
                await uploadOne(file, index);
            } catch (error) {
                const active = uploadQueue.querySelector(`.queue-item[data-upload-name="${escapeCssIdent(file.name)}"] span`);
                if (active) active.textContent = `실패: ${error.message}`;
            }
        }
    }

    try {
        await Promise.all(Array.from({ length: uploadConcurrency }, () => worker()));
        await loadBoard();
    } catch (error) {
        alert(`업로드 실패: ${error.message}`);
    } finally {
        setTimeout(() => uploadQueue.classList.add('hidden'), 1500);
    }
}

async function uploadVideosQueued(fileList) {
    const uploadFiles = Array.from(fileList || []);
    if (uploadFiles.length === 0) return;
    saveAutoPipelineSettings();

    if (uploadHideTimer) {
        clearTimeout(uploadHideTimer);
        uploadHideTimer = null;
    }

    uploadQueue.classList.remove('hidden');
    if (!uploadQueue.querySelector('.queue-summary')) {
        uploadQueue.innerHTML = '<div class="queue-summary"></div>';
    }

    uploadFiles.forEach(file => {
        const task = {
            id: `upload-${Date.now()}-${uploadSequence++}`,
            file,
            status: 'pending'
        };
        uploadTaskQueue.push(task);
        uploadQueue.insertAdjacentHTML('beforeend', `
            <div class="queue-item" data-upload-id="${task.id}">
                <strong>${escapeHtml(file.name)}</strong>
                <span>업로드 대기</span>
            </div>
        `);
    });

    updateUploadQueueSummary();
    pumpUploadQueue();
}

function updateUploadQueueSummary() {
    if (!uploadQueue) return;
    const summary = uploadQueue.querySelector('.queue-summary');
    if (!summary) return;
    const pending = uploadTaskQueue.filter(task => task.status === 'pending').length;
    const running = uploadTaskQueue.filter(task => task.status === 'running').length;
    const completed = uploadTaskQueue.filter(task => task.status === 'completed').length;
    const failed = uploadTaskQueue.filter(task => task.status === 'failed').length;
    summary.textContent = `업로드 큐 · 진행 ${running}개 · 대기 ${pending}개 · 완료 ${completed}개${failed ? ` · 실패 ${failed}개` : ''} · CPU 준비 ${uploadMaxConcurrency}개 병렬 / GPU 음성 인식 1개 순차`;
}

function setUploadTaskMessage(task, message, status = task.status) {
    task.status = status;
    const active = uploadQueue.querySelector(`.queue-item[data-upload-id="${escapeCssIdent(task.id)}"] span`);
    if (active) active.textContent = message;
    updateUploadQueueSummary();
}

function scheduleUploadQueueHideIfIdle() {
    if (uploadActiveCount > 0 || uploadTaskQueue.some(task => task.status === 'pending' || task.status === 'running')) return;
    uploadHideTimer = setTimeout(() => {
        if (uploadActiveCount > 0 || uploadTaskQueue.some(task => task.status === 'pending' || task.status === 'running')) return;
        uploadQueue.classList.add('hidden');
        uploadTaskQueue = [];
        uploadQueue.innerHTML = '';
    }, 2500);
}

function pumpUploadQueue() {
    while (uploadActiveCount < uploadMaxConcurrency) {
        const task = uploadTaskQueue.find(item => item.status === 'pending');
        if (!task) break;
        uploadActiveCount += 1;
        runUploadTask(task)
            .catch(error => {
                setUploadTaskMessage(task, `실패: ${error.message}`, 'failed');
            })
            .finally(async () => {
                uploadActiveCount = Math.max(0, uploadActiveCount - 1);
                updateUploadQueueSummary();
                await loadBoard();
                pumpUploadQueue();
                scheduleUploadQueueHideIfIdle();
            });
    }
}

async function runUploadTask(task) {
    const file = task.file;
    setUploadTaskMessage(task, '업로드 시작', 'running');

    const formData = new FormData();
    formData.append('files', file);
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
            if (event.message) {
                setUploadTaskMessage(task, event.message, event.status === 'error' ? 'failed' : 'running');
            }
            if (event.file_id) {
                if (event.status === 'completed') {
                    recentUploadedFileIds.add(event.file_id);
                }
                await loadBoard();
                renderBatchUploadedList();
                if (event.status === 'completed' && (fileModal.classList.contains('hidden') || currentFileId !== event.file_id)) {
                    await openFileModal(event.file_id);
                } else if (!fileModal.classList.contains('hidden') && currentFileId === event.file_id) {
                    await refreshModalFile();
                }
            } else if (event.status === 'completed') {
                await loadBoard();
            }
        }
    }
    setUploadTaskMessage(task, '완료', 'completed');
}

async function startAutoPipeline(fileId, settings = autoPipelineSettings()) {
    const body = {
        language: settings.language,
        final_output: settings.final_output,
        tts_provider: settings.tts_provider,
        voice_name: settings.voice_name,
        style_prompt: settings.style_prompt,
        srt_source: settings.srt_source,
        generate_corrected: settings.generate_corrected,
        generate_english: settings.generate_english,
        subtitle_style: settings.subtitle_style
    };
    return postJson(`/api/files/${fileId}/jobs/auto_pipeline`, body);
}

function renderBatchUploadedList() {
    if (!batchUploadedPanel || !batchUploadedList) return;
    const uploadedFiles = files.filter(file => recentUploadedFileIds.has(file.id));
    batchUploadedPanel.classList.toggle('hidden', uploadedFiles.length === 0);
    if (uploadedFiles.length === 0) {
        batchUploadedList.innerHTML = '';
        return;
    }
    batchUploadedList.innerHTML = uploadedFiles.map(file => {
        const status = getCardStatus(file);
        const summary = file.job_summary || {};
        return `
            <label class="batch-uploaded-item">
                <input type="checkbox" data-batch-uploaded-file="${file.id}" checked>
                <span>
                    <strong>${escapeHtml(file.filename)}</strong>
                    <small>${statusLabel(status)} · ${escapeHtml(summary.message || '제작 대기')}</small>
                </span>
            </label>
        `;
    }).join('');
}

async function runPipelineForFiles(fileIds) {
    const targetIds = [...new Set(fileIds)].filter(Boolean);
    if (targetIds.length === 0) {
        alert('제작할 작업을 선택하세요.');
        return;
    }
    const settings = autoPipelineSettings();
    saveAutoPipelineSettings();
    for (const fileId of targetIds) {
        try {
            await startAutoPipeline(fileId, settings);
        } catch (error) {
            const file = files.find(item => item.id === fileId);
            alert(`${file?.filename || fileId} 제작 등록 실패: ${error.message}`);
        }
    }
    await loadBoard();
    renderBatchUploadedList();
}

function artifactKindLabel(kind) {
    const kindLabels = {
        srt: '자막 SRT',
        audio: '음성 MP3',
        video: '더빙 영상',
        subtitle_video: '자막 영상',
        captioned_dub_video: '자막+더빙 영상',
        edited_video: '편집 영상'
    };
    return kindLabels[kind] || kind;
}

function formatDateTime(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString();
}

function formatEstimatedCost(value) {
    const amount = Number(value || 0);
    if (!amount) return '$0.000000';
    if (amount < 0.000001) return '< $0.000001';
    return `$${amount.toFixed(6)}`;
}

function aiUsageText(metadata = {}) {
    const tokens = Number(metadata.ai_total_tokens || 0);
    const characters = Number(metadata.ai_characters || 0);
    const requests = Number(metadata.ai_request_count || metadata.tts_request_count || 0);
    const parts = [];
    if (tokens) parts.push(`${formatNumber(tokens)} tokens`);
    if (characters) parts.push(`${formatNumber(characters)} chars`);
    if (requests) parts.push(`${formatNumber(requests)} req`);
    return parts.join(' / ');
}

function artifactSubtitleCategory(artifact) {
    if (artifact.kind === 'srt') return 'srt_only';
    if (artifact.kind === 'subtitle_video') return 'subtitle_only';
    if (artifact.kind === 'captioned_dub_video') return 'captioned_dub';
    return 'no_subtitle';
}

function visibleAllArtifacts() {
    const kindFilter = artifactKindFilter?.value || 'all';
    const languageFilter = artifactLanguageFilter?.value || 'all';
    const subtitleFilter = artifactSubtitleFilter?.value || 'all';
    return allArtifacts()
        .filter(artifact => kindFilter === 'all' || artifact.kind === kindFilter)
        .filter(artifact => languageFilter === 'all' || artifact.language === languageFilter)
        .filter(artifact => subtitleFilter === 'all' || artifactSubtitleCategory(artifact) === subtitleFilter);
}

function providerDisplayName(provider) {
    const names = {
        gemini: 'Gemini',
        google_cloud: 'Google Cloud TTS',
        google_cloud_tts: 'Google Cloud TTS'
    };
    return names[provider] || provider || '';
}

function voiceDisplayName(provider, voiceName) {
    if (!voiceName) return '';
    const providerData = ttsProviders[provider] || fallbackTtsProviders[provider];
    const voice = providerData?.voices?.find(item => item.name === voiceName);
    return voice ? voiceOptionText(provider, voice) : voiceName;
}

function toneDisplayName(stylePrompt, provider = '') {
    const prompt = String(stylePrompt || '').trim();
    if (!prompt) return '';
    const matched = Object.entries(tonePrompts).find(([, value]) => value === prompt);
    if (matched) return toneLabels[matched[0]] || matched[0];
    return `직접 입력: ${prompt.length > 64 ? `${prompt.slice(0, 64)}...` : prompt}`;
}

function artifactVoiceDetails(metadata = {}) {
    const voice = metadata.voice_name || '';
    const provider = metadata.tts_provider || inferProviderFromVoice(voice);
    const tone = toneDisplayName(metadata.style_prompt, provider);
    const device = metadata.tts_device && metadata.tts_device !== 'remote' ? ` · ${metadata.tts_device}` : '';
    return { provider, voice, tone, device };
}

function artifactMetaRowsHtml(voiceDetails, options = {}) {
    const rows = [];
    const metadata = options.metadata || {};
    if (options.sourceFilename) {
        rows.push(['소스', options.sourceFilename]);
    }
    if (options.srtLabel) {
        rows.push(['자막', options.srtLabel]);
    }
    if (options.cueCount) {
        rows.push(['구간', `${options.cueCount}개`]);
    }
    if (voiceDetails.provider) {
        rows.push(['엔진', `${providerDisplayName(voiceDetails.provider)}${voiceDetails.device}`]);
    }
    if (voiceDetails.voice) {
        rows.push(['음성', voiceDisplayName(voiceDetails.provider, voiceDetails.voice)]);
    }
    if (voiceDetails.tone) {
        rows.push(['톤', voiceDetails.tone]);
    }
    const usage = aiUsageText(metadata);
    if (usage) {
        rows.push(['AI 사용량', usage]);
    }
    if (metadata.ai_estimated_cost_usd !== undefined && Number(metadata.ai_estimated_cost_usd || 0) >= 0) {
        rows.push(['예상 비용', formatEstimatedCost(metadata.ai_estimated_cost_usd)]);
    }
    if (!rows.length) return '';
    return `
        <dl class="artifact-meta-list">
            ${rows.map(([label, value]) => `
                <div class="artifact-meta-line">
                    <dt>${escapeHtml(label)}</dt>
                    <dd>${escapeHtml(value)}</dd>
                </div>
            `).join('')}
        </dl>
    `;
}

function artifactCardHtml(artifact, options = {}) {
    const language = artifact.language === 'en' ? 'English' : '한국어';
    const kind = artifactKindLabel(artifact.kind);
    const metadata = artifact.metadata || {};
    const voiceDetails = artifactVoiceDetails(metadata);
    const metaRows = artifactMetaRowsHtml(voiceDetails, {
        ...options,
        metadata,
        srtLabel: metadata.srt_label,
        cueCount: metadata.cue_count
    });
    const previewUrl = artifactUrl(artifact);
    const createdAt = formatDateTime(artifact.created_at);
    const selector = options.selectable
        ? `<label class="artifact-select"><input type="checkbox" data-select-artifact="${escapeHtml(artifact.id)}" ${selectedArtifactIds.has(artifact.id) ? 'checked' : ''}></label>`
        : '';
    const player = artifact.kind === 'audio'
        ? `<audio class="artifact-player" controls preload="metadata" src="${previewUrl}"></audio>`
        : artifact.kind === 'srt'
            ? `<div class="artifact-srt-preview">SRT 파일은 다운로드해서 확인하거나 작업 열기에서 수정할 수 있습니다.</div>`
        : ['video', 'subtitle_video', 'captioned_dub_video', 'edited_video'].includes(artifact.kind)
            ? `<video class="artifact-player artifact-video-player" controls playsinline preload="metadata" src="${previewUrl}"></video>`
            : '';
    const canOpenSource = options.fileId && options.sourceFilename && options.sourceFilename !== '삭제된 작업';
    const openSourceButton = canOpenSource
        ? `<button class="btn-toolbar" data-open-file="${escapeHtml(options.fileId)}">작업 열기</button>`
        : '';
    return `
        <div class="artifact-item">
            <div class="artifact-item-header ${options.selectable ? 'selectable' : ''}">
                ${selector}
                <div>
                    <strong>${language} ${kind}</strong>
                    <small>${escapeHtml(artifact.filename || '')}</small>
                    ${createdAt ? `<small>생성 시각: ${escapeHtml(createdAt)}</small>` : ''}
                    ${metaRows}
                </div>
                <div class="artifact-actions">
                    ${openSourceButton}
                    <a class="btn-toolbar" href="/api/artifacts/${encodeURIComponent(artifact.id)}/download" download>다운로드</a>
                </div>
            </div>
            ${player}
        </div>
    `;
}

function renderArtifacts(artifacts) {
    const artifactKey = (artifacts || [])
        .map(artifact => `${artifact.id}:${artifact.kind}:${artifact.filename}:${artifact.metadata?.tts_provider || ''}:${artifact.metadata?.voice_name || ''}:${artifact.metadata?.style_prompt || ''}:${artifact.metadata?.ai_estimated_cost_usd || ''}:${artifact.metadata?.ai_total_tokens || ''}:${artifact.metadata?.ai_characters || ''}`)
        .join('|');
    if (artifactKey === renderedArtifactsKey) return;
    renderedArtifactsKey = artifactKey;
    if (!artifacts || artifacts.length === 0) {
        modalArtifacts.innerHTML = '<div class="summary-placeholder">생성된 산출물이 없습니다</div>';
        return;
    }
    modalArtifacts.innerHTML = artifacts.map(artifact => artifactCardHtml(artifact)).join('');
}

function selectedEditorFile() {
    return editorFiles.find(file => file.id === currentEditorFileId) || null;
}

function setEditorStatus(message, type = 'info') {
    if (!editorStatus) return;
    if (!message) {
        editorStatus.classList.add('hidden');
        editorStatus.textContent = '';
        editorStatus.className = 'editor-status hidden';
        return;
    }
    editorStatus.className = `editor-status ${type}`;
    editorStatus.textContent = message;
}

function renderEditorFileOptions() {
    const options = ['<option value="">선택 안 함</option>']
        .concat(editorFiles
            .filter(file => file.id !== currentEditorFileId)
            .map(file => `<option value="${escapeHtml(file.id)}">${escapeHtml(file.filename || 'video')}</option>`))
        .join('');
    if (editorBeforeExistingSelect) editorBeforeExistingSelect.innerHTML = options;
    if (editorAfterExistingSelect) editorAfterExistingSelect.innerHTML = options;
}

function updateEditorSelectionSummary() {
    const availableIds = new Set(editorFiles.map(file => file.id));
    selectedEditorFileIds = new Set([...selectedEditorFileIds].filter(id => availableIds.has(id)));
    if (editorSelectedCount) editorSelectedCount.textContent = `선택 ${selectedEditorFileIds.size}개`;
}

function renderEditorFiles() {
    if (!editorFileList) return;
    updateEditorSelectionSummary();
    if (editorFileCount) editorFileCount.textContent = `${editorFiles.length}개`;
    if (!editorFiles.length) {
        editorFileList.innerHTML = '<div class="empty-state">편집할 영상을 업로드하세요.</div>';
        currentEditorFileId = null;
        renderSelectedEditorFile();
        return;
    }
    if (!currentEditorFileId || !editorFiles.some(file => file.id === currentEditorFileId)) {
        currentEditorFileId = editorFiles[0].id;
    }
    editorFileList.innerHTML = editorFiles.map(file => {
        const active = file.id === currentEditorFileId ? 'active' : '';
        const thumb = file.thumbnail_url
            ? `<img src="${file.thumbnail_url}" alt="">`
            : '<div class="editor-file-thumb-placeholder">MP4</div>';
        const artifactCount = (file.artifacts || []).filter(artifact => artifact.kind === 'edited_video').length;
        const checked = selectedEditorFileIds.has(file.id) ? 'checked' : '';
        return `
            <div class="editor-file-item ${active}" data-editor-file-id="${escapeHtml(file.id)}" role="button" tabindex="0">
                <input class="editor-file-check" type="checkbox" data-editor-select="${escapeHtml(file.id)}" ${checked} aria-label="batch select">
                ${thumb}
                <span>
                    <strong>${escapeHtml(file.filename || 'video')}</strong>
                    <small>편집 결과 ${artifactCount}개</small>
                </span>
            </div>
        `;
    }).join('');
    renderSelectedEditorFile();
}

function renderSelectedEditorFile() {
    const file = selectedEditorFile();
    renderEditorFileOptions();
    if (!file) {
        if (editorCurrentTitle) editorCurrentTitle.textContent = '선택된 영상 없음';
        if (editorPreviewPlayer) editorPreviewPlayer.removeAttribute('src');
        if (editorArtifactsList) editorArtifactsList.innerHTML = '<div class="empty-state">왼쪽에서 영상을 선택하세요.</div>';
        return;
    }
    if (editorCurrentTitle) editorCurrentTitle.textContent = file.filename || 'video';
    if (editorPreviewPlayer) {
        const nextSrc = file.media_url || '';
        if (editorPreviewPlayer.getAttribute('src') !== nextSrc) {
            editorPreviewPlayer.src = nextSrc;
            editorPreviewPlayer.load();
        }
    }
    const editedArtifacts = (file.artifacts || []).filter(artifact => artifact.kind === 'edited_video');
    if (editorArtifactsList) {
        editorArtifactsList.innerHTML = editedArtifacts.length
            ? editedArtifacts.map(artifact => artifactCardHtml(artifact)).join('')
            : '<div class="empty-state">아직 편집 결과가 없습니다.</div>';
    }
}

async function loadEditorFiles() {
    if (!editorFileList) return;
    try {
        const data = await fetch('/api/editor/files').then(response => response.json());
        if (!data.success) throw new Error(normalizeApiError(data.detail || data.message || '편집 파일 목록을 불러오지 못했습니다.'));
        editorFiles = data.files || [];
        renderEditorFiles();
    } catch (error) {
        editorFileList.innerHTML = `<div class="empty-state">${escapeHtml(error.message || '편집 파일 목록을 불러오지 못했습니다.')}</div>`;
    }
}

async function uploadEditorVideos(fileList) {
    const uploadFiles = Array.from(fileList || []);
    if (!uploadFiles.length) return;
    const formData = new FormData();
    uploadFiles.forEach(file => formData.append('files', file));
    setEditorStatus(`업로드 중: ${uploadFiles.length}개 파일`, 'info');
    try {
        const response = await fetch('/api/editor/upload', { method: 'POST', body: formData });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(normalizeApiError(data.detail || data.message || '업로드에 실패했습니다.'));
        currentEditorFileId = data.files?.[0]?.id || currentEditorFileId;
        await loadEditorFiles();
        setEditorStatus('업로드 완료', 'success');
    } catch (error) {
        setEditorStatus(error.message || '업로드에 실패했습니다.', 'error');
    }
}

function updateEditorConcatVisibility() {
    if (!editorConcatPositionSelect) return;
    const position = editorConcatPositionSelect.value;
    if (editorBeforeSourceGroup) editorBeforeSourceGroup.classList.toggle('hidden', position === 'after');
    if (editorAfterSourceGroup) editorAfterSourceGroup.classList.toggle('hidden', position === 'before');
}

async function createEditorTrimmedVideo() {
    const file = selectedEditorFile();
    if (!file) return alert('편집할 영상을 먼저 선택하세요.');
    const start = Number(editorTrimStartSeconds?.value || 0);
    const end = Number(editorTrimEndSeconds?.value || 0);
    if (!Number.isFinite(end) || end <= start) return alert('끝 초는 시작 초보다 커야 합니다.');
    setEditorStatus('자른 영상 생성 중...', 'info');
    try {
        await postJson(`/api/files/${encodeURIComponent(file.id)}/edit/trim`, {
            start_seconds: start,
            end_seconds: end
        });
        await loadEditorFiles();
        setEditorStatus('자른 영상 생성 완료', 'success');
    } catch (error) {
        setEditorStatus(error.message || '자른 영상 생성에 실패했습니다.', 'error');
    }
}

async function createEditorConcatenatedVideo() {
    const file = selectedEditorFile();
    if (!file) return alert('편집할 영상을 먼저 선택하세요.');
    const position = editorConcatPositionSelect?.value || 'after';
    const formData = new FormData();
    formData.append('position', position);
    if (position === 'before' || position === 'both') {
        if (editorBeforeUploadInput?.files?.[0]) formData.append('upload_file', editorBeforeUploadInput.files[0]);
        else if (editorBeforeExistingSelect?.value) formData.append('existing_file_id', editorBeforeExistingSelect.value);
        else return alert('앞에 붙일 영상을 선택하거나 업로드하세요.');
    }
    if (position === 'after' || position === 'both') {
        if (editorAfterUploadInput?.files?.[0]) formData.append('after_upload_file', editorAfterUploadInput.files[0]);
        else if (editorAfterExistingSelect?.value) formData.append('after_existing_file_id', editorAfterExistingSelect.value);
        else return alert('뒤에 붙일 영상을 선택하거나 업로드하세요.');
    }
    setEditorStatus('영상을 붙이는 중...', 'info');
    try {
        const response = await fetch(`/api/files/${encodeURIComponent(file.id)}/edit/concat`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(normalizeApiError(data.detail || data.message || '영상 붙이기에 실패했습니다.'));
        if (editorBeforeUploadInput) editorBeforeUploadInput.value = '';
        if (editorAfterUploadInput) editorAfterUploadInput.value = '';
        await loadEditorFiles();
        setEditorStatus('붙인 영상 생성 완료', 'success');
    } catch (error) {
        setEditorStatus(error.message || '영상 붙이기에 실패했습니다.', 'error');
    }
}

async function applyLogoIntroToEditorFiles(fileIds) {
    const ids = [...new Set(fileIds || [])].filter(Boolean);
    if (!ids.length) return alert('LogoIntro를 적용할 영상을 선택하세요.');
    const position = editorLogoIntroPositionSelect?.value || 'before';
    const positionLabel = position === 'both' ? '앞/뒤 모두' : position === 'after' ? '뒤' : '앞';
    setEditorStatus(`LogoIntro ${positionLabel} 삽입 중: ${ids.length}개 영상`, 'info');
    try {
        const data = await postJson('/api/editor/batch-logo-intro', {
            file_ids: ids,
            position
        });
        await loadEditorFiles();
        const errorText = data.error_count ? `, 실패 ${data.error_count}개` : '';
        setEditorStatus(`LogoIntro 적용 완료: 생성 ${data.created_count || 0}개${errorText}`, data.error_count ? 'error' : 'success');
    } catch (error) {
        setEditorStatus(error.message || 'LogoIntro 적용에 실패했습니다.', 'error');
    }
}

function allArtifacts() {
    return allArtifactsCache.map(artifact => ({
        ...artifact,
        sourceFileId: artifact.file_id,
        sourceFilename: artifact.source_filename || '삭제된 작업'
    }));
}

function renderAllArtifacts(force = false) {
    if (!allArtifactsList) return;
    const kindFilter = artifactKindFilter?.value || 'all';
    const languageFilter = artifactLanguageFilter?.value || 'all';
    const subtitleFilter = artifactSubtitleFilter?.value || 'all';
    const artifacts = visibleAllArtifacts();
    const artifactKey = [
        kindFilter,
        languageFilter,
        subtitleFilter,
        [...selectedArtifactIds].sort().join(','),
        ...artifacts.map(artifact => `${artifact.id}:${artifact.kind}:${artifact.filename}:${artifact.created_at}:${artifact.sourceFileId}:${artifact.metadata?.tts_provider || ''}:${artifact.metadata?.voice_name || ''}:${artifact.metadata?.style_prompt || ''}:${artifact.metadata?.ai_estimated_cost_usd || ''}:${artifact.metadata?.ai_total_tokens || ''}:${artifact.metadata?.ai_characters || ''}`)
    ].join('|');
    if (!force && artifactKey === renderedAllArtifactsKey) return;
    renderedAllArtifactsKey = artifactKey;
    if (artifacts.length === 0) {
        allArtifactsList.innerHTML = '<div class="summary-placeholder">표시할 산출물이 없습니다.</div>';
        return;
    }
    allArtifactsList.innerHTML = artifacts.map(artifact =>
        artifactCardHtml(artifact, {
            fileId: artifact.sourceFileId,
            sourceFilename: artifact.sourceFilename,
            selectable: true
        })
    ).join('');
}

async function loadAllArtifacts(force = false) {
    if (!allArtifactsList) return;
    try {
        const response = await fetch('/api/artifacts');
        const data = await response.json();
        if (!data.success) throw new Error('산출물을 불러올 수 없습니다.');
        allArtifactsCache = data.artifacts || [];
        const availableIds = new Set(allArtifactsCache.map(artifact => artifact.id));
        selectedArtifactIds = new Set([...selectedArtifactIds].filter(id => availableIds.has(id)));
        renderAllArtifacts(force);
    } catch (error) {
        allArtifactsList.innerHTML = `<div class="summary-placeholder">${escapeHtml(error.message || '산출물을 불러올 수 없습니다.')}</div>`;
    }
}

async function downloadSelectedArtifacts() {
    if (selectedArtifactIds.size === 0) return;
    const response = await fetch('/api/artifacts/batch-download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artifact_ids: [...selectedArtifactIds] })
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        alert(data.detail || '선택 산출물 다운로드에 실패했습니다.');
        return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'selected_artifacts.zip';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function deleteSelectedArtifacts() {
    if (selectedArtifactIds.size === 0) return;
    if (!confirm(`선택한 산출물 ${selectedArtifactIds.size}개를 삭제하시겠습니까? 파일도 함께 삭제됩니다.`)) return;
    const data = await postJson('/api/artifacts/batch-delete', { artifact_ids: [...selectedArtifactIds] });
    selectedArtifactIds.clear();
    renderedAllArtifactsKey = '';
    await loadAllArtifacts(true);
    await loadBoard();
    if (!fileModal.classList.contains('hidden') && currentFileId) {
        await refreshModalFile();
    }
    setModalMessage(`산출물 ${data.deleted || 0}개 삭제 완료`);
}

function inferProviderFromVoice(voice) {
    if (!voice) return '';
    if (/^[a-z]{2}-[A-Z]{2}-/i.test(voice)) return 'google_cloud';
    return 'gemini';
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
    return type === 'audio';
}

function outputNeedsAudioArtifact(type = currentOutputType) {
    return ['dub', 'captioned_dub'].includes(type);
}

function outputNeedsSrtSource(type = currentOutputType) {
    return ['subtitle', 'audio', 'captioned_dub'].includes(type);
}

function outputNeedsSubtitleStyle(type = currentOutputType) {
    return ['subtitle', 'captioned_dub'].includes(type);
}

function latestArtifact(file, kind, language = null) {
    const artifacts = file?.artifacts || [];
    const provider = generationTtsProviderSelect?.value || '';
    const voiceKinds = new Set(['audio', 'video', 'captioned_dub_video']);
    if (voiceKinds.has(kind) && provider) {
        const providerMatch = artifacts.find(item =>
            item.kind === kind
            && (!language || item.language === language)
            && item.metadata?.tts_provider === provider
        );
        if (providerMatch) return providerMatch;
    }
    return artifacts.find(item =>
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

function srtSourceOptionsForCurrentFile(language = generationLanguageSelect?.value || 'ko') {
    const options = [];
    if (language === 'en') {
        if (currentFileData?.english_srt_text) options.push({ value: 'english', label: 'English SRT' });
    } else {
        if (currentFileData?.corrected_srt_text) options.push({ value: 'corrected', label: '보정 SRT' });
        if (currentFileData?.srt_text) options.push({ value: 'original', label: '한국어 SRT' });
    }
    return options;
}

function populateSrtSourceSelect() {
    if (!generationSrtSourceSelect) return;
    const language = generationLanguageSelect?.value || 'ko';
    const options = srtSourceOptionsForCurrentFile(language);
    generationSrtSourceSelect.disabled = options.length === 0;
    generationSrtSourceSelect.innerHTML = options.length
        ? options.map(option => `<option value="${option.value}">${escapeHtml(option.label)}</option>`).join('')
        : '<option value="">사용 가능한 SRT가 없습니다</option>';
}

function syncGenerationLanguageWithAvailableSrt() {
    if (!generationLanguageSelect || !currentFileData) return;
    const hasKoSrt = Boolean(currentFileData.srt_text || currentFileData.corrected_srt_text);
    const hasEnSrt = Boolean(currentFileData.english_srt_text);
    if (hasEnSrt && !hasKoSrt) {
        generationLanguageSelect.value = 'en';
    }
    if (hasKoSrt && !hasEnSrt && generationLanguageSelect.value === 'en') {
        generationLanguageSelect.value = 'ko';
    }
}

function audioArtifactLabel(artifact) {
    const metadata = artifact.metadata || {};
    const provider = metadata.tts_provider || inferProviderFromVoice(metadata.voice_name) || 'unknown';
    const voice = metadata.voice_name || 'voice';
    const source = metadata.srt_source || artifact.language;
    const tone = toneDisplayName(metadata.style_prompt, provider);
    const tonePart = tone ? ` · ${tone}` : '';
    return `${artifact.language === 'en' ? 'English' : '한국어'} · ${providerDisplayName(provider)} · ${voiceDisplayName(provider, voice)} · ${source}${tonePart}`;
}

function populateAudioArtifactSelect() {
    if (!generationAudioArtifactSelect) return;
    const language = generationLanguageSelect?.value || 'ko';
    const artifacts = (currentFileData?.artifacts || []).filter(artifact =>
        artifact.kind === 'audio' && artifact.language === language
    );
    generationAudioArtifactSelect.disabled = artifacts.length === 0;
    generationAudioArtifactSelect.innerHTML = artifacts.length
        ? artifacts.map(artifact => `<option value="${artifact.id}">${escapeHtml(audioArtifactLabel(artifact))}</option>`).join('')
        : '<option value="">먼저 MP3를 생성하세요</option>';
}

function hasAudioArtifactForLanguage(language = generationLanguageSelect?.value || 'ko') {
    return (currentFileData?.artifacts || []).some(artifact =>
        artifact.kind === 'audio' && artifact.language === language
    );
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
    const provider = generationTtsProviderSelect?.value || 'gemini';
    const needsVoice = outputNeedsVoice();
    const needsAudioArtifact = outputNeedsAudioArtifact();
    if (productionSettingsTitle) productionSettingsTitle.textContent = `${label} 설정`;
    if (productionGenerateBtn) productionGenerateBtn.textContent = `${label} 생성하기`;
    if (srtSourceSettingGroup) srtSourceSettingGroup.classList.toggle('hidden', !outputNeedsSrtSource());
    if (audioArtifactSettingGroup) audioArtifactSettingGroup.classList.toggle('hidden', !needsAudioArtifact);
    if (voiceSettingGroup) voiceSettingGroup.classList.toggle('hidden', !needsVoice);
    if (voiceNameSettingGroup) voiceNameSettingGroup.classList.toggle('hidden', !needsVoice);
    if (voiceToneSettingGroup) voiceToneSettingGroup.classList.toggle('hidden', !needsVoice);
    if (voiceToneCustomGroup) {
        voiceToneCustomGroup.classList.toggle('hidden', !needsVoice || generationToneSelect?.value !== 'custom');
    }
    if (subtitlePresetPanel) subtitlePresetPanel.classList.toggle('hidden', !outputNeedsSubtitleStyle());
    if (subtitleStylePanel) subtitleStylePanel.classList.toggle('hidden', !outputNeedsSubtitleStyle());
    populateSrtSourceSelect();
    populateAudioArtifactSelect();
    populateVoiceSelect(generationLanguageSelect.value);
    setPreviewMode(outputTypeToPreviewMode());
    updateSubtitleDesignPreview();
    updateModalActionState();
}

function selectedTonePrompt(provider = generationTtsProviderSelect?.value || 'gemini') {
    if (!outputNeedsVoice()) return '';
    if (generationToneSelect?.value === 'custom') {
        return generationToneCustomInput?.value?.trim() || '';
    }
    return tonePrompts[generationToneSelect?.value] || tonePrompts.bright_natural;
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
        return;
    }
    if (artifact.kind === 'edited_video') {
        setPreviewMode('original', artifact);
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

function setVideoEditMessage(message = '', isError = false) {
    if (!videoEditStatus) return;
    videoEditStatus.textContent = message;
    videoEditStatus.classList.toggle('error', Boolean(isError));
}

function populateVideoEditPanel() {
    if (!currentFileData) return;
    if (editSourceVideoPlayer) {
        if (currentFileData.media_url) {
            setPlayerSource(editSourceVideoPlayer, currentFileData.media_url);
        } else {
            editSourceVideoPlayer.removeAttribute('src');
            editSourceVideoPlayer.load();
        }
    }
    const candidates = files.filter(file => file.id !== currentFileId && file.media_url);
    const existingOptions = candidates.length
        ? `<option value="">기존 파일 선택 안 함</option>${candidates.map(file =>
            `<option value="${escapeHtml(file.id)}">${escapeHtml(file.filename || file.id)}</option>`
        ).join('')}`
        : '<option value="">붙일 수 있는 기존 영상이 없습니다</option>';
    [concatExistingFileSelect, concatAfterExistingFileSelect].filter(Boolean).forEach(select => {
        select.innerHTML = existingOptions;
        select.disabled = candidates.length === 0;
    });
    updateConcatSourceVisibility();
    setVideoEditMessage(currentFileData.media_url ? '편집할 원본 영상이 준비되어 있습니다.' : '원본 영상이 없어 편집할 수 없습니다.', !currentFileData.media_url);
}

function updateConcatSourceVisibility() {
    const position = concatPositionSelect?.value || 'after';
    const beforeEnabled = position === 'before' || position === 'both';
    const afterEnabled = position === 'after' || position === 'both';
    const beforeHasExisting = (concatExistingFileSelect?.options?.length || 0) > 1;
    const afterHasExisting = (concatAfterExistingFileSelect?.options?.length || 0) > 1;
    if (concatExistingFileSelect) concatExistingFileSelect.disabled = !beforeEnabled || !beforeHasExisting;
    if (concatUploadInput) concatUploadInput.disabled = !beforeEnabled;
    if (concatAfterExistingFileSelect) concatAfterExistingFileSelect.disabled = !afterEnabled || !afterHasExisting;
    if (concatAfterUploadInput) concatAfterUploadInput.disabled = !afterEnabled;
    [concatExistingFileSelect, concatUploadInput].filter(Boolean).forEach(input => {
        input.closest('label')?.classList.toggle('muted-control', !beforeEnabled);
    });
    [concatAfterExistingFileSelect, concatAfterUploadInput].filter(Boolean).forEach(input => {
        input.closest('label')?.classList.toggle('muted-control', !afterEnabled);
    });
}

async function createTrimmedVideo() {
    if (!currentFileId) return;
    const start = Number(trimStartSeconds?.value || 0);
    const end = Number(trimEndSeconds?.value || 0);
    if (!Number.isFinite(end) || end <= start) {
        alert('끝 초는 시작 초보다 커야 합니다.');
        return;
    }
    const restore = setActionBusy(trimVideoBtn, '자른 영상 생성 중...');
    setVideoEditMessage('자른 영상 생성 중...');
    try {
        await postJson(`/api/files/${currentFileId}/edit/trim`, {
            start_seconds: start,
            end_seconds: end
        });
        await loadBoard();
        await refreshModalFile();
        setVideoEditMessage('자른 영상 생성 완료');
    } catch (error) {
        setVideoEditMessage(`오류: ${error.message}`, true);
        alert(`자르기 실패: ${error.message}`);
    } finally {
        restore();
    }
}

async function createConcatenatedVideo() {
    if (!currentFileId) return;
    const formData = new FormData();
    const position = concatPositionSelect?.value || 'after';
    formData.append('position', position);
    const needsBefore = position === 'before' || position === 'both';
    const needsAfter = position === 'after' || position === 'both';
    let hasRequiredSource = true;
    if (needsBefore && concatUploadInput?.files?.[0]) {
        formData.append('upload_file', concatUploadInput.files[0]);
    } else if (needsBefore && concatExistingFileSelect?.value) {
        formData.append('existing_file_id', concatExistingFileSelect.value);
    } else if (needsBefore) {
        hasRequiredSource = false;
    }
    if (needsAfter && concatAfterUploadInput?.files?.[0]) {
        formData.append('after_upload_file', concatAfterUploadInput.files[0]);
    } else if (needsAfter && concatAfterExistingFileSelect?.value) {
        formData.append('after_existing_file_id', concatAfterExistingFileSelect.value);
    } else if (needsAfter) {
        hasRequiredSource = false;
    }
    if (!hasRequiredSource) {
        alert(position === 'both' ? '앞에 붙일 영상과 뒤에 붙일 영상을 모두 선택하세요.' : '붙일 기존 영상 또는 새 업로드 영상을 선택하세요.');
        return;
    }
    const restore = setActionBusy(concatVideoBtn, '붙인 영상 생성 중...');
    setVideoEditMessage('붙인 영상 생성 중...');
    try {
        const response = await fetch(`/api/files/${currentFileId}/edit/concat`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || '붙이기 실패');
        if (concatUploadInput) concatUploadInput.value = '';
        if (concatAfterUploadInput) concatAfterUploadInput.value = '';
        await loadBoard();
        await refreshModalFile();
        setVideoEditMessage('붙인 영상 생성 완료');
    } catch (error) {
        setVideoEditMessage(`오류: ${error.message}`, true);
        alert(`붙이기 실패: ${error.message}`);
    } finally {
        restore();
    }
}

function jobTypeLabel(type) {
    const labels = {
        upload_process: '업로드/SRT 생성',
        srt_project: 'SRT 새 작업',
        correct_ko: '한국어 SRT 보정',
        translate_en: 'English SRT 생성',
        auto_pipeline: '자동 제작',
        audio: '음성 MP3 생성',
        dub_video: '더빙 영상 생성',
        subtitle_video: '자막 영상 생성',
        captioned_dub_video: '자막+더빙 영상 생성'
    };
    return labels[type] || type || '작업';
}

function jobSteps(type) {
    const stepMap = {
        upload_process: ['업로드', '오디오 추출', '음성 인식', 'SRT 저장'],
        srt_project: ['SRT 입력', '작업 생성'],
        correct_ko: ['SRT 분석', 'Gemini 보정 요청', '보정 결과 저장'],
        translate_en: ['SRT 준비', '영어 자막 생성 요청', 'English SRT 저장'],
        auto_pipeline: ['SRT 보정', 'English SRT', 'MP3 생성', '영상 합성', '완료'],
        audio: ['SRT 분석', '음성 엔진 준비', '구간별 음성 생성', '타임라인 보정', 'MP3 저장'],
        dub_video: ['MP3 선택 확인', '원본 영상 준비', '음성/영상 합성', '더빙 영상 저장'],
        subtitle_video: ['SRT 선택 확인', '자막 스타일 준비', '영상에 자막 입히기', '자막 영상 저장'],
        captioned_dub_video: ['MP3 선택 확인', '더빙 영상 합성', '자막 스타일 준비', '자막 입히기', '자막+더빙 영상 저장']
    };
    return stepMap[type] || ['준비', '처리', '완료'];
}

function activeStepIndex(type, progress, message, total) {
    const text = String(message || '');
    const matchers = {
        correct_ko: [
            ['분석'],
            ['Gemini', '보정'],
            ['저장', '완료']
        ],
        translate_en: [
            ['준비', '번역할'],
            ['Gemini', '영어'],
            ['저장', '완료']
        ],
        audio: [
            ['SRT', '타임라인', '분석'],
            ['엔진', '준비'],
            ['음성 생성'],
            ['보정', '타임라인', '배치'],
            ['MP3', '내보내', '완료']
        ],
        dub_video: [
            ['음성 산출물', 'MP3', '재사용', '선택'],
            ['원본 영상', '검은 배경'],
            ['합치는', '합성'],
            ['저장', '완료']
        ],
        subtitle_video: [
            ['SRT', '자막', '준비'],
            ['스타일'],
            ['입히는', '자막'],
            ['저장', '완료']
        ],
        captioned_dub_video: [
            ['음성 산출물', 'MP3', '재사용', '선택'],
            ['더빙', '합치는', '합성'],
            ['ASS', '스타일'],
            ['자막을 입히는'],
            ['저장', '완료']
        ],
        upload_process: [
            ['업로드'],
            ['오디오', '추출'],
            ['음성', '인식'],
            ['저장', '완료']
        ],
        auto_pipeline: [
            ['보정'],
            ['English'],
            ['MP3', '음성'],
            ['영상', '합성', '자막'],
            ['완료']
        ]
    };
    const candidates = matchers[type] || [];
    const found = candidates.findIndex(words => words.some(word => text.includes(word)));
    if (found >= 0) return Math.min(found, total - 1);
    return Math.min(total - 1, Math.floor((Math.max(0, Math.min(progress, 99)) / 100) * total));
}

function stepState(index, total, progress, status, activeIndex) {
    if (status === 'failed') return index === 0 ? 'failed' : 'idle';
    if (status === 'completed') return 'done';
    if (index < activeIndex) return 'done';
    if (index === activeIndex) return 'active';
    return 'idle';
}

function renderModalJobPanel(file) {
    if (!modalJobPanel) return;
    const jobs = file?.jobs || [];
    const latestJob = jobs[0];
    const job = jobs.find(item => item.status === 'pending' || item.status === 'running')
        || (latestJob?.status === 'failed' ? latestJob : null);
    if (!job) {
        modalJobPanel.classList.add('hidden');
        modalJobPanel.innerHTML = '';
        return;
    }
    modalJobPanel.classList.remove('hidden');
    const progress = Math.max(0, Math.min(Number(job.progress || 0), 100));
    const failed = job.status === 'failed';
    const message = failed && job.error ? normalizeApiError(job.error) : (job.message || '대기 중');
    const steps = jobSteps(job.job_type);
    const activeIndex = activeStepIndex(job.job_type, progress, message, steps.length);
    modalJobPanel.innerHTML = `
        <div class="modal-job-card ${failed ? 'failed' : ''}">
            <div class="modal-job-summary">
                <div>
                    <span class="modal-job-kicker">${escapeHtml(statusLabel(job.status))}</span>
                    <strong>${escapeHtml(jobTypeLabel(job.job_type))}</strong>
                </div>
                <span class="modal-job-percent">${progress}%</span>
            </div>
            <div class="modal-job-progress"><span style="width:${progress}%"></span></div>
            <div class="modal-job-message"><span>현재</span>${escapeHtml(message)}</div>
            <div class="modal-job-steps">
                ${steps.map((label, index) => `
                    <div class="modal-job-step ${stepState(index, steps.length, progress, job.status, activeIndex)}">
                        <span></span>
                        <small>${escapeHtml(label)}</small>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function setModalStatus(file) {
    const summary = file?.job_summary || {};
    const status = summary.status || 'idle';
    const detail = status === 'failed' && summary.latest?.error
        ? normalizeApiError(summary.latest.error)
        : (summary.message || '대기 중');
    modalJobStatus.textContent = `${statusLabel(status)} · ${detail}`;
    modalJobStatus.className = `api-key-status ${status === 'failed' ? 'disconnected' : 'connected'}`;
    renderModalJobPanel(file);
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
    const hasLanguageSrt = language === 'en' ? hasEnSrt : (hasKoSrt || hasCorrectedSrt);
    const hasLanguageAudio = hasAudioArtifactForLanguage(language);
    modalCorrectBtn.disabled = !hasKoSrt;
    modalTranslateBtn.disabled = !(hasKoSrt || hasCorrectedSrt);
    modalAudioBtn.disabled = !hasLanguageSrt;
    modalDubBtn.disabled = !hasLanguageAudio;
    if (modalCaptionedDubBtn) modalCaptionedDubBtn.disabled = !hasLanguageSrt || !hasLanguageAudio;
    if (previewStructureSubtitleBtn) previewStructureSubtitleBtn.disabled = !hasLanguageSrt;
    if (previewKoSubtitleBtn) previewKoSubtitleBtn.disabled = !(hasKoSrt || hasCorrectedSrt);
    if (previewEnSubtitleBtn) previewEnSubtitleBtn.disabled = !hasEnSrt;
    if (generationRequirementHint) {
        if (outputNeedsAudioArtifact() && !hasLanguageAudio) {
            generationRequirementHint.textContent = '더빙 영상은 먼저 생성된 MP3를 선택해야 만들 수 있습니다. 음성 MP3를 먼저 생성하세요.';
        } else if (outputNeedsSrtSource() && !hasLanguageSrt) {
            generationRequirementHint.textContent = language === 'en'
                ? 'English 구조를 만들려면 먼저 English SRT 탭에서 영어 자막을 생성하거나 붙여넣으세요.'
                : '자막 영상을 만들려면 먼저 한국어 SRT 또는 보정 SRT가 필요합니다.';
        } else {
            generationRequirementHint.textContent = outputNeedsAudioArtifact()
                ? '선택한 MP3를 원본 영상에 합성합니다. 자막+더빙은 선택한 SRT도 함께 입힙니다.'
                : '원본 영상이 없는 SRT 작업은 검은 배경 MP4로 생성됩니다.';
        }
    }
    if (productionGenerateBtn) {
        const needsSrt = !outputNeedsSrtSource() || !generationSrtSourceSelect?.disabled;
        const needsAudio = !outputNeedsAudioArtifact() || !generationAudioArtifactSelect?.disabled;
        productionGenerateBtn.disabled = !needsSrt || !needsAudio;
    }
}

function populateVoiceSelect(language) {
    populateProviderVoiceSelect('gemini', generationVoiceSelect, language);
    updateVoiceGuideTooltips();
    updateVoiceSamplePlayers();
}

function populateProviderVoiceSelect(provider, select, language) {
    if (!select) return;
    const providerData = ttsProviders[provider] || fallbackTtsProviders[provider];
    const hasProviderCatalog = Boolean(providerData);
    const providerVoices = hasProviderCatalog
        ? (providerData.voices || [])
        : (provider === activeTtsProvider ? voices : []);
    const supportedLanguages = providerData?.languages || [];
    const providerSupportsLanguage = supportedLanguages.length === 0 || supportedLanguages.includes(language);
    const matchingVoices = providerVoices.filter(voice => {
        const languages = voice.languages || [];
        return languages.length === 0 || languages.includes(language);
    });
    const availableVoices = providerSupportsLanguage ? matchingVoices : [];
    const defaults = providerData?.defaults || voiceDefaults;
    const defaultVoice = defaults[language] || availableVoices[0]?.name || '';
    select.disabled = availableVoices.length === 0;
    if (!availableVoices.length) {
        select.innerHTML = '<option value="">지원되는 음성이 없습니다</option>';
        return;
    }
    select.innerHTML = availableVoices.map(voice =>
        `<option value="${voice.name}" ${voice.name === defaultVoice ? 'selected' : ''}>${escapeHtml(voiceOptionText(provider, voice))}</option>`
    ).join('');
}

function selectedGenerationOptions() {
    const language = generationLanguageSelect.value;
    const provider = generationTtsProviderSelect?.value || 'gemini';
    const srtSource = generationSrtSourceSelect?.disabled
        ? (language === 'en' ? 'english' : 'corrected')
        : generationSrtSourceSelect?.value;
    return {
        language,
        tts_provider: provider,
        voice_name: generationVoiceSelect?.disabled ? null : generationVoiceSelect?.value,
        audio_artifact_id: generationAudioArtifactSelect?.disabled ? null : generationAudioArtifactSelect?.value,
        style_prompt: selectedTonePrompt(provider),
        srt_source: srtSource,
        subtitle_style: getSubtitleStyleOptions()
    };
}

async function openFileModal(fileId) {
    currentFileId = fileId;
    currentTab = 'subtitles';
    currentOutputType = 'captioned_dub';
    currentPreviewMode = outputTypeToPreviewMode(currentOutputType);
    renderedArtifactsKey = '';
    srtEditDirty = { corrected: false, english: false };
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
    if (!srtEditDirty.corrected && document.activeElement !== modalCorrectedSrt) {
        modalCorrectedSrt.value = currentFileData.corrected_srt_text || '';
    }
    if (!srtEditDirty.english && document.activeElement !== modalEnSrt) {
        modalEnSrt.value = currentFileData.english_srt_text || '';
    }
    syncGenerationLanguageWithAvailableSrt();
    populateSrtSourceSelect();
    populateVoiceSelect(generationLanguageSelect.value);
    populateAudioArtifactSelect();
    setModalStatus(currentFileData);
    renderArtifacts(currentFileData.artifacts || []);
    updatePreviewPlayers(currentFileData);
    populateVideoEditPanel();
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
            if (currentFileData && data.job) {
                currentFileData.jobs = [data.job, ...(currentFileData.jobs || []).filter(job => job.id !== data.job.id)];
                renderModalJobPanel(currentFileData);
            }
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
    startJob(jobType, selectedGenerationOptions(), productionGenerateBtn, `${label} 생성 등록 중...`);
}

function currentSrtTextAndName() {
    const base = (currentFileData?.filename || 'subtitle').replace(/\.[^/.]+$/, '');
    return [modalCorrectedSrt.value || modalKoSrt.value || modalEnSrt.value, `${base}_subtitle.srt`];
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
    try {
        const response = await fetch('/api/tts/voices');
        const data = await response.json();
        voices = data.voices || fallbackTtsProviders.gemini.voices;
        ttsProviders = { ...fallbackTtsProviders, ...(data.providers || {}) };
        activeTtsProvider = data.provider || activeTtsProvider;
        voiceDefaults = data.defaults || voiceDefaults;
    } catch {
        voices = fallbackTtsProviders.gemini.voices;
        ttsProviders = { ...fallbackTtsProviders };
        voiceDefaults = fallbackTtsProviders.gemini.defaults;
    }
    populateTtsProviderSelects();
    populateVoiceSelect(generationLanguageSelect.value);
    populateAutoPipelineVoice(autoPipelineVoice?.value || '');
    populateLectureVoice(lectureVoiceSelect?.value || '');
    populateAiVideoVoice(aiVideoVoiceSelect?.value || '');
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

function aiOperationLabel(operation) {
    const labels = {
        tts: '음성 생성',
        translate_en: '영어 자막 생성',
        correct_ko: '한국어 SRT 보정',
        summary: 'AI 요약',
        gemini_text: 'Gemini 텍스트',
        ai_video_draft: 'AI 영상 초안',
        image_generation: '이미지 생성'
    };
    return labels[operation] || operation || 'AI 작업';
}

function localDateInputValue(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function setDefaultAiUsageRange() {
    if (!aiUsageStartDate || !aiUsageEndDate || aiUsageStartDate.value || aiUsageEndDate.value) return;
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 29);
    aiUsageStartDate.value = localDateInputValue(start);
    aiUsageEndDate.value = localDateInputValue(end);
}

function aiUsageQueryString() {
    const params = new URLSearchParams();
    if (aiUsageStartDate?.value) {
        params.set('start_at', `${aiUsageStartDate.value}T00:00:00`);
    }
    if (aiUsageEndDate?.value) {
        const end = new Date(`${aiUsageEndDate.value}T00:00:00`);
        if (!Number.isNaN(end.getTime())) {
            end.setDate(end.getDate() + 1);
            params.set('end_at', `${localDateInputValue(end)}T00:00:00`);
        }
    }
    const query = params.toString();
    return query ? `?${query}` : '';
}

function renderAiUsage(data) {
    if (!aiUsageSummary || !aiUsageEvents) return;
    const total = data?.summary?.total || {};
    aiUsageSummary.innerHTML = `
        <div class="ai-usage-metric">
            <span>예상 비용</span>
            <strong>${formatEstimatedCost(total.estimated_cost_usd)}</strong>
        </div>
        <div class="ai-usage-metric">
            <span>토큰</span>
            <strong>${formatNumber(total.total_tokens || 0)}</strong>
        </div>
        <div class="ai-usage-metric">
            <span>문자</span>
            <strong>${formatNumber(total.characters || 0)}</strong>
        </div>
        <div class="ai-usage-metric">
            <span>요청</span>
            <strong>${formatNumber(total.request_count || 0)}</strong>
        </div>
    `;
    const events = data?.events || [];
    if (!events.length) {
        aiUsageEvents.innerHTML = '<div class="summary-placeholder">아직 기록된 AI 사용량이 없습니다.</div>';
        return;
    }
    aiUsageEvents.innerHTML = events.slice(0, 20).map(event => {
        const usage = [
            event.total_tokens ? `${formatNumber(event.total_tokens)} tokens` : '',
            event.characters ? `${formatNumber(event.characters)} chars` : '',
            event.request_count ? `${formatNumber(event.request_count)} req` : ''
        ].filter(Boolean).join(' / ');
        return `
            <div class="ai-usage-row">
                <span>${escapeHtml(formatDateTime(event.created_at))}</span>
                <strong>${escapeHtml(aiOperationLabel(event.operation))}</strong>
                <span>${escapeHtml(providerDisplayName(event.provider || ''))}</span>
                <span>${escapeHtml(usage || '사용량 없음')}</span>
                <span class="ai-cost-chip">${formatEstimatedCost(event.estimated_cost_usd)}</span>
            </div>
        `;
    }).join('');
}

async function loadAiUsage() {
    if (!aiUsageSummary || !aiUsageEvents) return;
    setDefaultAiUsageRange();
    aiUsageSummary.innerHTML = '<div class="loading">AI 사용량을 불러오는 중...</div>';
    aiUsageEvents.innerHTML = '';
    try {
        const response = await fetch(`/api/ai-usage${aiUsageQueryString()}`);
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.detail || 'AI 사용량을 불러올 수 없습니다.');
        renderAiUsage(data);
    } catch (error) {
        aiUsageSummary.innerHTML = `<div class="summary-placeholder">${escapeHtml(error.message || 'AI 사용량을 불러올 수 없습니다.')}</div>`;
        aiUsageEvents.innerHTML = '';
    }
}

function closeVoiceInfoPanels(except = null) {
    document.querySelectorAll('.info-tooltip.open').forEach(button => {
        if (button === except) return;
        button.classList.remove('open');
        button.setAttribute('aria-expanded', 'false');
    });
}

function setupVoiceInfoButtons() {
    document.querySelectorAll('.info-tooltip').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            const willOpen = !button.classList.contains('open');
            closeVoiceInfoPanels(button);
            button.classList.toggle('open', willOpen);
            button.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        });
        button.addEventListener('keydown', event => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            button.click();
        });
    });
    document.addEventListener('click', event => {
        if (!event.target.closest('.info-tooltip')) {
            closeVoiceInfoPanels();
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeVoiceInfoPanels();
    });
}

if (navHome) navHome.addEventListener('click', () => showSection('home'));
if (navVideoEditor) navVideoEditor.addEventListener('click', () => showSection('video_editor'));
if (navLectureProject) navLectureProject.addEventListener('click', () => {
    populateLectureVoice();
    showSection('lecture_project');
});
navArtifacts.addEventListener('click', () => showSection('artifacts'));
navSettings.addEventListener('click', () => {
    showSection('settings');
    checkApiKeyStatus();
    loadAiUsage();
});
document.querySelectorAll('[data-open-workspace]').forEach(card => {
    card.addEventListener('click', () => {
        const target = card.dataset.openWorkspace || 'home';
        if (target === 'lecture_project') populateLectureVoice();
        showSection(target);
    });
    card.addEventListener('keydown', event => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        const target = card.dataset.openWorkspace || 'home';
        if (target === 'lecture_project') populateLectureVoice();
        showSection(target);
    });
});
if (refreshAiUsageBtn) refreshAiUsageBtn.addEventListener('click', loadAiUsage);
if (aiUsageStartDate) aiUsageStartDate.addEventListener('change', loadAiUsage);
if (aiUsageEndDate) aiUsageEndDate.addEventListener('change', loadAiUsage);

boardUploadBtn.addEventListener('click', () => boardFileInput.click());
boardFileInput.addEventListener('change', event => {
    uploadVideosQueued(event.target.files);
    boardFileInput.value = '';
});

if (editorUploadBtn && editorFileInput) {
    editorUploadBtn.addEventListener('click', () => editorFileInput.click());
    editorFileInput.addEventListener('change', event => {
        uploadEditorVideos(event.target.files);
        editorFileInput.value = '';
    });
}
if (editorRefreshBtn) editorRefreshBtn.addEventListener('click', loadEditorFiles);
if (editorFileList) {
    editorFileList.addEventListener('click', event => {
        const checkbox = event.target.closest('[data-editor-select]');
        if (checkbox) {
            const fileId = checkbox.dataset.editorSelect;
            if (checkbox.checked) selectedEditorFileIds.add(fileId);
            else selectedEditorFileIds.delete(fileId);
            updateEditorSelectionSummary();
            event.stopPropagation();
            return;
        }
        const item = event.target.closest('[data-editor-file-id]');
        if (!item) return;
        currentEditorFileId = item.dataset.editorFileId;
        setEditorStatus('', 'info');
        renderEditorFiles();
    });
}
if (editorConcatPositionSelect) {
    editorConcatPositionSelect.addEventListener('change', updateEditorConcatVisibility);
    updateEditorConcatVisibility();
}
if (editorTrimBtn) editorTrimBtn.addEventListener('click', createEditorTrimmedVideo);
if (editorConcatBtn) editorConcatBtn.addEventListener('click', createEditorConcatenatedVideo);
if (editorSelectAllBtn) {
    editorSelectAllBtn.addEventListener('click', () => {
        editorFiles.forEach(file => selectedEditorFileIds.add(file.id));
        renderEditorFiles();
    });
}
if (editorClearSelectionBtn) {
    editorClearSelectionBtn.addEventListener('click', () => {
        selectedEditorFileIds.clear();
        renderEditorFiles();
    });
}
if (editorLogoIntroSelectedBtn) {
    editorLogoIntroSelectedBtn.addEventListener('click', () => applyLogoIntroToEditorFiles([...selectedEditorFileIds]));
}
if (editorLogoIntroAllBtn) {
    editorLogoIntroAllBtn.addEventListener('click', () => applyLogoIntroToEditorFiles(editorFiles.map(file => file.id)));
}

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
if (artifactKindFilter) {
    artifactKindFilter.addEventListener('change', () => renderAllArtifacts(true));
}
if (artifactLanguageFilter) {
    artifactLanguageFilter.addEventListener('change', () => renderAllArtifacts(true));
}
if (artifactSubtitleFilter) {
    artifactSubtitleFilter.addEventListener('change', () => renderAllArtifacts(true));
}
if (selectAllArtifactsBtn) {
    selectAllArtifactsBtn.addEventListener('click', () => {
        visibleAllArtifacts().forEach(artifact => selectedArtifactIds.add(artifact.id));
        renderAllArtifacts(true);
    });
}
if (clearArtifactSelectionBtn) {
    clearArtifactSelectionBtn.addEventListener('click', () => {
        selectedArtifactIds.clear();
        renderAllArtifacts(true);
    });
}
if (downloadSelectedArtifactsBtn) {
    downloadSelectedArtifactsBtn.addEventListener('click', downloadSelectedArtifacts);
}
if (deleteSelectedArtifactsBtn) {
    deleteSelectedArtifactsBtn.addEventListener('click', deleteSelectedArtifacts);
}
[
    autoPipelineOutput,
    autoPipelineSubtitlePreset,
    autoPipelineTone,
    autoPipelineVoice
].filter(Boolean).forEach(input => {
    input.addEventListener('change', () => {
        saveAutoPipelineSettings();
        updateVoiceSamplePlayers();
    });
});
if (autoPipelineLanguage) {
    autoPipelineLanguage.addEventListener('change', () => {
        populateAutoPipelineVoice();
        saveAutoPipelineSettings();
        updateVoiceSamplePlayers();
    });
}
if (autoPipelineProvider) {
    autoPipelineProvider.addEventListener('change', () => {
        populateAutoPipelineVoice();
        saveAutoPipelineSettings();
        updateVoiceSamplePlayers();
    });
}
if (lectureLanguageSelect) {
    lectureLanguageSelect.addEventListener('change', () => {
        populateLectureVoice();
        updateVoiceSamplePlayers();
    });
}
if (lectureProviderSelect) {
    lectureProviderSelect.addEventListener('change', () => {
        populateLectureVoice();
        updateVoiceSamplePlayers();
    });
}
if (lectureVoiceSelect) {
    lectureVoiceSelect.addEventListener('change', updateVoiceSamplePlayers);
}
if (lectureVoiceSampleBtn) {
    lectureVoiceSampleBtn.addEventListener('click', playLectureVoiceSample);
}
if (lectureCreateBtn) lectureCreateBtn.addEventListener('click', createLectureProject);
if (aiVideoLanguageSelect) {
    aiVideoLanguageSelect.addEventListener('change', () => populateAiVideoVoice());
}
if (aiVideoProviderSelect) {
    aiVideoProviderSelect.addEventListener('change', () => populateAiVideoVoice());
}
if (aiVideoImageStylePresetSelect) {
    aiVideoImageStylePresetSelect.addEventListener('change', () => {
        const value = aiVideoImageStylePresetSelect.value;
        if (value !== 'custom' && aiVideoImageStyleInput) {
            aiVideoImageStyleInput.value = value;
        }
    });
}
if (aiVideoImageStyleInput) {
    aiVideoImageStyleInput.addEventListener('input', () => {
        if (aiVideoImageStylePresetSelect) aiVideoImageStylePresetSelect.value = 'custom';
    });
}
if (aiVideoDraftBtn) aiVideoDraftBtn.addEventListener('click', createAiVideoDraft);
if (aiVideoCreateBtn) aiVideoCreateBtn.addEventListener('click', createAiVideoProject);
if (selectUploadedBatchBtn) {
    selectUploadedBatchBtn.addEventListener('click', () => {
        batchUploadedList?.querySelectorAll('[data-batch-uploaded-file]').forEach(input => {
            input.checked = true;
        });
    });
}
if (runUploadedBatchBtn) {
    runUploadedBatchBtn.addEventListener('click', () => {
        const ids = [...(batchUploadedList?.querySelectorAll('[data-batch-uploaded-file]:checked') || [])]
            .map(input => input.dataset.batchUploadedFile);
        runPipelineForFiles(ids);
    });
}

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

if (allArtifactsList) {
    allArtifactsList.addEventListener('click', event => {
        const select = event.target.closest('[data-select-artifact]');
        if (select) {
            const artifactId = select.dataset.selectArtifact;
            if (select.checked) selectedArtifactIds.add(artifactId);
            else selectedArtifactIds.delete(artifactId);
            renderAllArtifacts(true);
            return;
        }
        const open = event.target.closest('[data-open-file]');
        if (open) openFileModal(open.dataset.openFile);
    });
}

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
if (runSelectedPipelineBtn) {
    runSelectedPipelineBtn.addEventListener('click', () => {
        runPipelineForFiles([...selectedFileIds]);
    });
}
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
        srtEditDirty.corrected = false;
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
        srtEditDirty.english = false;
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
if (trimVideoBtn) trimVideoBtn.addEventListener('click', createTrimmedVideo);
if (concatVideoBtn) concatVideoBtn.addEventListener('click', createConcatenatedVideo);
if (concatPositionSelect) concatPositionSelect.addEventListener('change', updateConcatSourceVisibility);
if (subtitlePresetSelect) {
    subtitlePresetSelect.addEventListener('change', applySelectedSubtitlePreset);
}
if (saveSubtitlePresetBtn) {
    saveSubtitlePresetBtn.addEventListener('click', saveCurrentSubtitlePreset);
}
if (deleteSubtitlePresetBtn) {
    deleteSubtitlePresetBtn.addEventListener('click', deleteCurrentSubtitlePreset);
}

document.querySelectorAll('[data-preview-mode]').forEach(button => {
    button.addEventListener('click', () => {
        const mode = button.dataset.previewMode;
        if (mode) setPreviewMode(mode);
    });
});

generationLanguageSelect.addEventListener('change', () => {
    updateProductionView();
    updateSubtitleDesignPreview();
    updateMainPreview();
    updateVoiceSamplePlayers();
});
if (generationSrtSourceSelect) {
    generationSrtSourceSelect.addEventListener('change', () => {
        updateModalActionState();
        updateSubtitleDesignPreview();
    });
}
if (generationAudioArtifactSelect) {
    generationAudioArtifactSelect.addEventListener('change', () => {
        updateModalActionState();
        updateMainPreview();
    });
}
generationTtsProviderSelect.addEventListener('change', () => {
    updateProductionView();
    updateSubtitleDesignPreview();
    updateMainPreview();
    updateVoiceSamplePlayers();
});
generationVoiceSelect.addEventListener('change', () => {
    updateModalActionState();
    updateVoiceSamplePlayers();
});
if (generationToneSelect) {
    generationToneSelect.addEventListener('change', () => {
        if (voiceToneCustomGroup) {
            voiceToneCustomGroup.classList.toggle('hidden', generationToneSelect.value !== 'custom' || !outputNeedsVoice());
        }
        updateModalActionState();
    });
}
if (generationToneCustomInput) {
    generationToneCustomInput.addEventListener('input', updateModalActionState);
}
modalKoSrt.addEventListener('input', () => {
    updateModalActionState();
    updateSubtitleDesignPreview();
});
modalCorrectedSrt.addEventListener('input', () => {
    srtEditDirty.corrected = true;
    updateModalActionState();
    updateSubtitleDesignPreview();
});
modalEnSrt.addEventListener('input', () => {
    srtEditDirty.english = true;
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
    input.addEventListener('input', () => {
        markSubtitlePresetAsCustom();
        updateSubtitleDesignPreview();
    });
    input.addEventListener('change', () => {
        markSubtitlePresetAsCustom();
        updateSubtitleDesignPreview();
    });
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
    setupVoiceInfoButtons();
    initializeSubtitlePresets();
    await checkApiKeyStatus();
    await loadAiUsage();
    await loadVoices();
    await loadVoiceSamples();
    loadAutoPipelineSettings();
    await loadBoard();
    updateSubtitleDesignPreview();
    startBoardPolling();
});
