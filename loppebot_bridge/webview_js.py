"""JavaScript injected into the 로페봇 web application."""

INJECT_SCRIPT_TEMPLATE = r"""
(() => {
  const tileSelector = __TILE_SELECTOR__;
  const titleAttribute = __TITLE_ATTRIBUTE__;
  const fallbackSelector = __FALLBACK_SELECTOR__;
  const numberAttribute = __NUMBER_ATTRIBUTE__;
  const datasetNumberKeys = __DATASET_KEYS__;
  const contextMenuText = __MENU_TEXT__;
  const toastDuration = __TOAST_DURATION__;
  const highlightClass = __HIGHLIGHT_CLASS__;

  let menuElement = null;
  let toastContainer = null;
  let highlightedTile = null;

  function ensureStyles() {
    if (document.getElementById('loppe-bridge-styles')) {
      return;
    }
    const styles = document.createElement('style');
    styles.id = 'loppe-bridge-styles';
    styles.textContent = `
      .loppe-bridge-menu {
        position: fixed;
        z-index: 9999;
        min-width: 180px;
        background: rgba(18, 18, 18, 0.95);
        color: #fff;
        border-radius: 8px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        padding: 12px 16px;
        font-family: 'Pretendard', 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
        opacity: 0;
        transform: translateY(8px);
        transition: opacity 120ms ease, transform 120ms ease;
        cursor: pointer;
      }
      .loppe-bridge-menu.visible {
        opacity: 1;
        transform: translateY(0);
      }
      .loppe-bridge-menu .loppe-bridge-label {
        font-size: 12px;
        opacity: 0.7;
        margin-bottom: 4px;
        letter-spacing: 0.05em;
      }
      .loppe-bridge-menu .loppe-bridge-title {
        font-weight: 600;
        font-size: 14px;
        max-width: 280px;
        line-height: 1.4;
      }
      .loppe-bridge-toast-container {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 8px;
        align-items: flex-end;
        pointer-events: none;
      }
      .loppe-bridge-toast {
        background: rgba(24, 24, 24, 0.94);
        color: #fff;
        padding: 10px 16px;
        border-radius: 8px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.2);
        font-size: 13px;
        opacity: 0;
        transform: translateY(12px);
        transition: opacity 160ms ease, transform 160ms ease;
        pointer-events: auto;
        max-width: 320px;
        line-height: 1.5;
      }
      .loppe-bridge-toast.visible {
        opacity: 1;
        transform: translateY(0);
      }
      .loppe-bridge-toast.error {
        background: rgba(168, 39, 47, 0.95);
      }
      .loppe-bridge-highlight {
        outline: 3px solid rgba(0, 204, 255, 0.65) !important;
        outline-offset: 2px;
        border-radius: 10px;
        transition: outline 120ms ease;
      }
    `;
    document.head.appendChild(styles);
  }

  function closeMenu() {
    if (menuElement) {
      menuElement.remove();
      menuElement = null;
    }
    if (highlightedTile) {
      highlightedTile.classList.remove(highlightClass);
      highlightedTile = null;
    }
  }

  function ensureToastContainer() {
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'loppe-bridge-toast-container';
      document.body.appendChild(toastContainer);
    }
    return toastContainer;
  }

  function showToast(message, isError) {
    ensureStyles();
    const container = ensureToastContainer();
    const toast = document.createElement('div');
    toast.className = 'loppe-bridge-toast' + (isError ? ' error' : '');
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('visible'));
    setTimeout(() => {
      toast.classList.remove('visible');
      setTimeout(() => toast.remove(), 220);
    }, toastDuration);
  }

  function gatherTrackData(tile) {
    const track = {
      title: '',
      titleNumber: null,
      rawText: tile.textContent ? tile.textContent.trim() : ''
    };
    if (titleAttribute) {
      const attr = tile.getAttribute(titleAttribute);
      if (attr) {
        track.title = attr.trim();
      }
    }
    if (!track.title && fallbackSelector) {
      const fallback = tile.querySelector(fallbackSelector);
      if (fallback) {
        track.title = fallback.textContent.trim();
      }
    }
    if (!track.title) {
      const alt = tile.querySelector('[data-song-title], [data-title], .title, .song-title, h3, h4');
      if (alt && alt.textContent) {
        track.title = alt.textContent.trim();
      }
    }
    if (numberAttribute) {
      const attr = tile.getAttribute(numberAttribute);
      if (attr) {
        track.titleNumber = attr.trim();
      }
    }
    if (!track.titleNumber && tile.dataset) {
      for (const key of datasetNumberKeys) {
        if (key in tile.dataset && tile.dataset[key]) {
          track.titleNumber = tile.dataset[key];
          break;
        }
      }
    }
    if (!track.title && track.rawText) {
      const firstLine = track.rawText.split('\n').map(t => t.trim()).find(Boolean);
      if (firstLine) {
        track.title = firstLine;
      }
    }
    return track;
  }

  function sendTrack(track) {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.select_track) {
      console.warn('[LoppeBridge] pywebview API not available');
      showToast('연동 프로그램 연결에 실패했습니다.', true);
      return;
    }
    window.pywebview.api.select_track(track)
      .then(result => {
        if (result && result.message) {
          showToast(result.message, result.status !== 'ok');
        }
      })
      .catch(error => {
        console.error('[LoppeBridge]', error);
        showToast('키 입력 중 오류가 발생했습니다.', true);
      });
  }

  function openMenu(event, track, tile) {
    closeMenu();
    ensureStyles();
    highlightedTile = tile;
    highlightedTile.classList.add(highlightClass);

    menuElement = document.createElement('div');
    menuElement.className = 'loppe-bridge-menu';
    menuElement.innerHTML = `
      <div class="loppe-bridge-label">${contextMenuText}</div>
      <div class="loppe-bridge-title">${(track.title || track.rawText || '').replace(/</g, '&lt;')}</div>
    `;
    menuElement.addEventListener('click', (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      sendTrack(track);
      closeMenu();
    });
    document.body.appendChild(menuElement);

    const desiredLeft = event.clientX + window.scrollX;
    const desiredTop = event.clientY + window.scrollY;

    requestAnimationFrame(() => {
      const rect = menuElement.getBoundingClientRect();
      let left = desiredLeft;
      let top = desiredTop;
      if (left + rect.width > window.innerWidth + window.scrollX) {
        left = Math.max(12 + window.scrollX, window.innerWidth + window.scrollX - rect.width - 12);
      }
      if (top + rect.height > window.innerHeight + window.scrollY) {
        top = Math.max(12 + window.scrollY, window.innerHeight + window.scrollY - rect.height - 12);
      }
      menuElement.style.left = `${left}px`;
      menuElement.style.top = `${top}px`;
      menuElement.classList.add('visible');
    });
  }

  document.addEventListener('contextmenu', (event) => {
    if (!tileSelector) {
      return;
    }
    const tile = event.target.closest(tileSelector);
    if (!tile) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const track = gatherTrackData(tile);
    if (!track.title && !track.titleNumber) {
      console.warn('[LoppeBridge] 타일 정보를 찾을 수 없습니다.', tile);
    }
    openMenu(event, track, tile);
  }, true);

  window.addEventListener('click', () => closeMenu(), true);
  window.addEventListener('blur', () => closeMenu());
  window.addEventListener('scroll', () => closeMenu(), true);

  console.debug('[LoppeBridge] injection completed');
})();
"""
