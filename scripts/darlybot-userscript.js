// ==UserScript==
// @name         Darlybot Helper (B300 맞춤)
// @namespace    https://github.com/
// @version      0.2
// @description  b300.vercel.app 타일에서 곡 정보를 추출해 로컬 Darlybot Helper로 전송
// @match        https://b300.vercel.app/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8972';
  // .tile 요소도 인식하도록 수정
  const TILE_SELECTOR = '.tile, [data-title-number], [data-song-id], [data-song-title]';

  function findTile(element) {
    return element.closest(TILE_SELECTOR);
  }

  function extractSong(tile) {
    const dataset = tile.dataset || {};

    // title_number 우선순위: data-* → img src 숫자
    let titleNumber =
      dataset.titleNumber ||
      dataset.songId ||
      dataset.id ||
      (() => {
        const img = tile.querySelector('.cover img, img');
        const src = img?.getAttribute('src') || '';
        const m = src.match(/\/(\d+)\.(?:jpg|jpeg|png|webp)(?:\?|#|$)/i);
        return m ? m[1] : '';
      })();

    // title 우선순위: data-* → .title → img alt → 전체 텍스트
    let title =
      dataset.title ||
      dataset.songTitle ||
      tile.querySelector('.meta-wrap .title, .title')?.textContent?.trim() ||
      tile.querySelector('.cover img, img')?.getAttribute('alt')?.trim() ||
      tile.textContent.trim();

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

  // 우클릭 이벤트 후킹
  document.addEventListener('contextmenu', (event) => {
    const tile = findTile(event.target);
    if (!tile) {
      return;
    }
    event.preventDefault();
    const payload = extractSong(tile);
    sendNavigate(payload);
  }, true);

  console.log('[darlybot] B300 타일 우클릭 연동 스크립트가 활성화되었습니다.');
})();
