(() => {
  const statusEl = document.getElementById('status');
  const docInfoEl = document.getElementById('doc-info');
  const docTitleEl = document.getElementById('doc-title');
  const blockCountEl = document.getElementById('block-count');
  const btnExport = document.getElementById('btn-export');
  const resultEl = document.getElementById('result');

  let extractedDoc = null;

  async function detectDocument() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      setStatus('无法获取当前标签页', false);
      return;
    }

    try {
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'extractDocument' });
      if (response?.error) {
        setStatus(response.error, false);
        return;
      }
      if (response?.ok && response.document) {
        extractedDoc = response.document;
        setStatus('已检测到飞书文档', true);
        docTitleEl.textContent = extractedDoc.title;
        blockCountEl.textContent = `提取到 ${extractedDoc.blocks.length} 个内容块`;
        docInfoEl.style.display = 'block';
        btnExport.disabled = false;
      } else {
        setStatus('未能提取文档内容', false);
      }
    } catch (e) {
      setStatus('请在飞书文档页面使用此插件', false);
    }
  }

  function setStatus(msg, ok) {
    statusEl.textContent = msg;
    statusEl.className = ok ? 'status ok' : 'status err';
  }

  btnExport.addEventListener('click', async () => {
    if (!extractedDoc) return;
    btnExport.disabled = true;
    btnExport.textContent = '生成中...';

    try {
      const texContent = generateTex(extractedDoc);
      const blob = new Blob([texContent], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const filename = sanitizeFilename(extractedDoc.title) + '.tex';

      await chrome.downloads.download({
        url,
        filename,
        saveAs: true
      });

      resultEl.textContent = `✓ 已导出: ${filename}`;
    } catch (e) {
      resultEl.textContent = `导出失败: ${e.message}`;
    } finally {
      btnExport.disabled = false;
      btnExport.textContent = '导出 .tex 文件';
    }
  });

  function sanitizeFilename(name) {
    return (name || 'untitled')
      .replace(/[<>:"/\\|?*]/g, '_')
      .replace(/\s+/g, '-')
      .substring(0, 80);
  }

  // Inline minimal TeX generator for popup context
  function generateTex(doc) {
    const lines = [];
    lines.push(`\\documentclass[UTF8]{ctexart}`);
    lines.push(`\\usepackage{graphicx}`);
    lines.push(`\\usepackage{hyperref}`);
    lines.push(`\\usepackage{xcolor}`);
    lines.push(`\\usepackage{soul}`);
    lines.push(`\\usepackage{listings}`);
    lines.push(`\\usepackage{amsmath}`);
    lines.push('');
    lines.push(`\\title{${escapeTex(doc.title)}}`);
    lines.push(`\\author{}`);
    lines.push(`\\date{\\today}`);
    lines.push('');
    lines.push('\\begin{document}');
    lines.push('\\maketitle');
    lines.push('');

    let inList = null;

    for (const block of doc.blocks) {
      if (inList && !['ordered_list', 'unordered_list'].includes(block.type)) {
        lines.push(inList === 'ordered' ? '\\end{enumerate}' : '\\end{itemize}');
        lines.push('');
        inList = null;
      }

      switch (block.type) {
        case 'heading': {
          const cmd = ['section', 'subsection', 'subsubsection', 'paragraph'][Math.min(block.level - 1, 3)];
          lines.push(`\\${cmd}{${block.content}}`);
          lines.push('');
          break;
        }
        case 'paragraph':
          lines.push(block.content);
          lines.push('');
          break;
        case 'ordered_list':
          if (inList !== 'ordered') {
            lines.push('\\begin{enumerate}');
            inList = 'ordered';
          }
          lines.push(`  \\item ${block.content}`);
          break;
        case 'unordered_list':
          if (inList !== 'unordered') {
            lines.push('\\begin{itemize}');
            inList = 'unordered';
          }
          lines.push(`  \\item ${block.content}`);
          break;
        case 'code_block':
          lines.push(`\\begin{lstlisting}[language=${block.language || ''}]`);
          lines.push(block.content);
          lines.push('\\end{lstlisting}');
          lines.push('');
          break;
        case 'image':
          lines.push(`% TODO: image - ${block.alt || block.src}`);
          lines.push('');
          break;
        case 'quote':
          lines.push('\\begin{quote}');
          lines.push(`  ${block.content}`);
          lines.push('\\end{quote}');
          lines.push('');
          break;
        case 'divider':
          lines.push('\\noindent\\rule{\\textwidth}{0.4pt}');
          lines.push('');
          break;
        default:
          if (block.content?.trim()) {
            lines.push(block.content);
            lines.push('');
          }
      }
    }

    if (inList) {
      lines.push(inList === 'ordered' ? '\\end{enumerate}' : '\\end{itemize}');
    }

    lines.push('');
    lines.push('\\end{document}');
    return lines.join('\n');
  }

  function escapeTex(text) {
    return (text || '')
      .replace(/\\/g, '\\textbackslash{}')
      .replace(/[&%#_{}~^]/g, ch => '\\' + ch);
  }

  detectDocument();
})();
