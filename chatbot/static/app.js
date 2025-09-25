(function () {
  const chatEl = document.getElementById('chat');
  const inputEl = document.getElementById('question');
  const sendBtn = document.getElementById('send');

  async function ask() {
    const q = (inputEl.value || '').trim();
    if (!q) return;
    appendMD('you', q);
    inputEl.value = '';
    try {
      const res = await fetch('/chat/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q})
      });
      if (!res.ok) {
        appendMD('bot', `Fehler: ${res.status}`);
        return;
      }
      const data = await res.json(); // {answer, sources}
      appendMD('bot', data.answer, data.sources);
    } catch (e) {
      appendMD('bot', String(e?.message || e));
    }
  }

  function appendMD(cls, mdText, sources) {
    const d = document.createElement('div');
    d.className = 'msg ' + cls;

    // Markdown -> HTML (falls marked fehlt, fallback auf Text)
    let rawHtml = mdText ?? '';
    if (window.marked) {
      rawHtml = window.marked.parse(rawHtml, { gfm: true, breaks: true, headerIds: false, mangle: false });
    } else {
      rawHtml = `<pre><code>${escapeHtml(rawHtml)}</code></pre>`;
    }

    // Sanitizen (immer!)
    const safeHtml = window.DOMPurify ? window.DOMPurify.sanitize(rawHtml) : rawHtml;
    d.innerHTML = safeHtml;

    // Quellenliste (optional) — nummeriert
    if (Array.isArray(sources) && sources.length) {
      const ol = document.createElement('ol');
      ol.className = 'sources';
      ol.style.marginTop = '0.5rem';

      sources.forEach((s) => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = s.url || '#';
        a.textContent = s.title || s.url || 'Quelle';
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        li.appendChild(a);
        ol.appendChild(li);
      });

      d.appendChild(ol);
    }

    chatEl.insertBefore(d, chatEl.firstChild);

    // Syntax-Highlighting
    if (window.hljs) {
      d.querySelectorAll('pre code').forEach(block => { window.hljs.highlightElement(block); });
    }

    // Copy-Buttons
    enhanceCodeBlocks(d);

    // LaTeX rendern (KaTeX) – nach dem Einfügen & Sanitisieren
    if (window.renderMathInElement) {
      // Standard-Delimiter: $$...$$ (Display), \( ... \) (Inline), optional $...$
      window.renderMathInElement(d, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\(", right: "\\)", display: false },
          // $...$ nur aktivieren, wenn du es wirklich brauchst:
          // { left: "$", right: "$", display: false }
        ],
        throwOnError: false,
        strict: "warn",
        // Code/Pre/A ignorieren
        ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "a"]
      });
    }

    // Auto-Scroll
    chatEl.scrollTop = 0;
  }

  function enhanceCodeBlocks(rootEl) {
    rootEl.querySelectorAll('pre').forEach(pre => {
      if (pre.querySelector('.copy-btn')) return;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'copy-btn';
      btn.setAttribute('aria-label', 'Code in Zwischenablage kopieren');
      btn.textContent = 'Copy';

      btn.addEventListener('click', async () => {
        const code = pre.querySelector('code');
        const txt = code ? code.textContent : pre.textContent;

        try {
          await navigator.clipboard.writeText(txt);
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(() => {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 1500);
        } catch (err) {
          console.error('Copy failed:', err);
          btn.textContent = 'Fehler';
          setTimeout(() => {
            btn.textContent = 'Copy';
          }, 1500);
        }
      });

      pre.appendChild(btn);
    });
  }


  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, s => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[s]
    ));
  }

  // Events (kein inline onclick mehr)
  sendBtn.addEventListener('click', ask);
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  });
})();
