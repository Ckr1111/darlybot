// ==UserScript==
// @name         RofeBot DJMAX Bridge
// @namespace    https://github.com/
// @version      1.0.0
// @description  Send right-clicked song tiles to the local DJMAX automation bridge
// @match        https://b300.vercel.app/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const ENDPOINT = 'http://127.0.0.1:29184/select';
    const TILE_SELECTOR = '[data-song-title], [data-song-id], .song-card, .song-tile';
    const TITLE_SELECTOR = '[data-song-title], .song-title, h3, h4';
    const NUMBER_SELECTOR = '[data-song-number], .song-number';

    document.addEventListener('contextmenu', (event) => {
        const tile = event.target.closest(TILE_SELECTOR);
        if (!tile) {
            return;
        }
        event.preventDefault();

        const payload = buildPayload(tile);
        if (!payload) {
            console.warn('RofeBot bridge: could not extract song information from tile', tile);
            return;
        }

        postSelection(payload)
            .then(() => {
                console.info('RofeBot bridge: sent selection', payload);
                flashTile(tile);
            })
            .catch((error) => {
                console.error('RofeBot bridge: failed to send selection', error);
            });
    }, true);

    function buildPayload(tile) {
        const dataset = tile.dataset || {};
        const title = (dataset.songTitle || textFrom(tile, TITLE_SELECTOR)).trim();
        const titleNumber = (dataset.songNumber || dataset.songId || textFrom(tile, NUMBER_SELECTOR)).trim();
        if (!title && !titleNumber) {
            return null;
        }
        return { title, titleNumber };
    }

    async function postSelection(payload) {
        await fetch(ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
    }

    function textFrom(root, selector) {
        const element = root.querySelector(selector);
        return element ? element.textContent || '' : '';
    }

    function flashTile(tile) {
        tile.classList.add('rofebot-bridge__flash');
        window.setTimeout(() => tile.classList.remove('rofebot-bridge__flash'), 600);
    }

    const style = document.createElement('style');
    style.textContent = `
        .rofebot-bridge__flash {
            outline: 3px solid #ff8c00 !important;
            transition: outline 0.2s ease-in-out;
        }
    `;
    document.head.appendChild(style);
})();
