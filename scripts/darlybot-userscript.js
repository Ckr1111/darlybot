// ==UserScript==
// @name         Darlybot Helper
// @namespace    https://github.com/
// @version      0.1
// @description  Connect Lopebot tiles with the local Darlybot helper.
// @match        https://b300.vercel.app/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8972';
  const TILE_SELECTOR = '[data-title-number], [data-song-id], [data-song-title]';

  function findTile(element) {
    return element.closest(TILE_SELECTOR);
  }

  function extractSong(tile) {
    const dataset = tile.dataset || {};
    const titleNumber = dataset.titleNumber || dataset.songId || dataset.id || '';

    let title = dataset.title || dataset.songTitle || '';
    if (!title) {
      const titleElement = tile.querySelector('[data-title], [data-song-title], .title, .name');
      if (titleElement) {
        title = titleElement.textContent.trim();
      }
    }
    if (!title) {
      title = tile.textContent.trim();
    }

    return {
      title_number: titleNumber || undefined,
      title: title || undefined,
    };
  }

  async function sendNavigate(payload) {
    if (!payload.title && !payload.title_number) {
      console.warn('[darlybot] 타일에서 곡 정보를 찾을 수 없습니다.', payload);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/navigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || response.statusText);
      }
      console.info('[darlybot] 보내진 키:', data.keys.join(', '));
    } catch (error) {
      console.error('[darlybot] 호출 실패:', error);
      window.alert(`곡 이동 요청에 실패했습니다.\n${error}`);
    }
  }

  document.addEventListener('contextmenu', (event) => {
    const tile = findTile(event.target);
    if (!tile) {
      return;
    }
    event.preventDefault();
    const payload = extractSong(tile);
    sendNavigate(payload);
  }, true);

  console.log('[darlybot] 로페봇 타일 우클릭 연동 스크립트가 활성화되었습니다.');
})();
