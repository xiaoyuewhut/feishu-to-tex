(() => {
  "use strict";

  const FEISHU_DOC_SELECTORS = {
    title: '[data-testid="doc-editor-title"]',
    editor: '.doc-block-container, .lark-editor, [data-content-editable-root="true"]',
    blocks: '[data-block-id]'
  };

  const DOC_PATH_RE = /feishu\.cn\/(docx|docs|wiki)\//;
  const LARK_PATH_RE = /larksuite\.com\/(docx|docs|wiki)\//;
  const TOKEN_RE = /\/(docx|docs|wiki)\/([a-zA-Z0-9]+)/;

  function isFeishuDocPage() {
    const url = window.location.href;
    return DOC_PATH_RE.test(url) || LARK_PATH_RE.test(url);
  }

  function getDocumentToken() {
    const match = window.location.pathname.match(TOKEN_RE);
    return match ? match[2] : null;
  }

  function extractTitle() {
    const el = document.querySelector(FEISHU_DOC_SELECTORS.title);
    if (el) return el.textContent.trim();
    const h1 = document.querySelector('h1');
    return h1 ? h1.textContent.trim() : document.title || 'untitled';
  }

  function extractInlineFormatting(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return escapeTex(node.textContent);
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return '';

    const tag = node.tagName.toLowerCase();
    const children = Array.from(node.childNodes).map(extractInlineFormatting).join('');

    if (tag === 'strong' || tag === 'b') return `\\textbf{${children}}`;
    if (tag === 'em' || tag === 'i') return `\\textit{${children}}`;
    if (tag === 'code') return `\\texttt{${children}}`;
    if (tag === 's' || tag === 'del') return `\\sout{${children}}`;
    if (tag === 'u') return `\\underline{${children}}`;
    if (tag === 'a') {
      const href = node.getAttribute('href') || '';
      return `\\href{${href}}{${children}}`;
    }
    if (tag === 'br') return '\n';
    if (tag === 'sup') return `\\textsuperscript{${children}}`;
    if (tag === 'sub') return `\\textsubscript{${children}}`;

    return children;
  }

  function escapeTex(text) {
    const special = ['&', '%', '#', '_', '{', '}'];
    let result = text;
    for (const ch of special) {
      result = result.replaceAll(ch, `\\${ch}`);
    }
    return result;
  }

  function getBlockType(el) {
    const blockId = el.getAttribute('data-block-id');
    if (!blockId) return null;

    const classList = el.className || '';
    const dataType = el.getAttribute('data-type') || '';

    if (/heading-1|H1|h1/.test(classList + dataType)) return 'heading1';
    if (/heading-2|H2|h2/.test(classList + dataType)) return 'heading2';
    if (/heading-3|H3|h3/.test(classList + dataType)) return 'heading3';
    if (/heading-4|H4|h4/.test(classList + dataType)) return 'heading4';
    if (/ordered-list|numbered-list/.test(classList + dataType)) return 'ordered_list';
    if (/bullet-list|unordered-list/.test(classList + dataType)) return 'unordered_list';
    if (/code-block|code_block/.test(classList + dataType)) return 'code_block';
    if (/quote/.test(classList + dataType)) return 'quote';
    if (/callout/.test(classList + dataType)) return 'callout';
    if (/divider|separator/.test(classList + dataType)) return 'divider';
    if (/image|img/.test(classList + dataType)) return 'image';

    return 'paragraph';
  }

  function extractBlocks() {
    const blocks = [];
    const blockElements = document.querySelectorAll(FEISHU_DOC_SELECTORS.blocks);

    for (const el of blockElements) {
      const type = getBlockType(el);
      if (!type) continue;

      const content = extractInlineFormatting(el);

      if (type.startsWith('heading')) {
        const level = parseInt(type.replace('heading', ''));
        blocks.push({ type: 'heading', level, content });
      } else if (type === 'code_block') {
        const codeEl = el.querySelector('code, pre');
        const lang = codeEl?.getAttribute('data-language') || '';
        const code = (codeEl || el).textContent;
        blocks.push({ type: 'code_block', language: lang, content: code });
      } else if (type === 'image') {
        const img = el.querySelector('img');
        const src = img?.getAttribute('src') || '';
        const alt = img?.getAttribute('alt') || '';
        blocks.push({ type: 'image', src, alt });
      } else {
        blocks.push({ type, content });
      }
    }

    if (blocks.length === 0) {
      const editor = document.querySelector(FEISHU_DOC_SELECTORS.editor);
      if (editor) {
        const paragraphs = editor.querySelectorAll('p, div[data-block-id]');
        for (const p of paragraphs) {
          const text = extractInlineFormatting(p);
          if (text.trim()) {
            blocks.push({ type: 'paragraph', content: text });
          }
        }
      }
    }

    return blocks;
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action !== 'extractDocument') return;

    if (!isFeishuDocPage()) {
      sendResponse({ error: '当前页面不是飞书文档' });
      return;
    }

    const token = getDocumentToken();
    const title = extractTitle();
    const blocks = extractBlocks();

    sendResponse({
      ok: true,
      document: { token, title, url: window.location.href, blocks }
    });
  });

  console.log('[FeishuToTeX] content script loaded');
})();
