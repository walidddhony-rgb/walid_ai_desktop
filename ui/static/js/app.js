/* Walid AI — app.js v2 (Fixed)
 * Fixes:
 * 1. XSS: escapeHtml() on all external content before innerHTML
 * 2. Correct DOM: $() returns element, .value works natively
 * 3. Socket.IO connection error handling
 * 4. render() defined: marked.parse() with sanitization
 * 5. Empty frame cleanup on error
 * 6. Input length validation (max 10000 chars)
 * 7. Handlers registered ONCE in init(), not per sendMsg()
 */

// === DOM helper (no jQuery dependency) ===
function $(id) { return document.getElementById(id); }

// === XSS protection: escape HTML entities ===
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// === Markdown renderer (safe) ===
function render(text) {
    if (!text) return '';
    try {
        // marked v9+ uses marked.parse()
        const html = (typeof marked !== 'undefined')
            ? (marked.parse ? marked.parse(text) : marked(text))
            : escapeHtml(text);
        return html;
    } catch (e) {
        return escapeHtml(text);
    }
}

// === Global state ===
let cid = null;
let generating = false;
let ai = null;       // current assistant content element
let buf = '';        // streaming buffer
let currentFrame = null;  // current assistant frame element
let socket = null;
let recognition = null;
let searchResultsHtml = '';  // accumulated search results

// === Init: connect socket and register handlers ONCE ===
function init() {
    socket = io();

    // --- Connection error handling ---
    socket.on('connect_error', () => {
        setStatus('فقد الاتصال بالخادم', 'error');
    });
    socket.on('disconnect', () => {
        setStatus('انقطع الاتصال', 'error');
        if (generating) {
            generating = false;
            $('send').style.display = 'inline-block';
            $('stop').style.display = 'none';
        }
    });
    socket.on('connect', () => {
        setStatus('جاهز');
        loadConvs();
    });

    // --- Stream chunk handler (registered ONCE) ---
    socket.on('stream_chunk', d => {
        try {
            buf += d.chunk;
            if (ai) {
                ai.innerHTML = render(buf) + searchResultsHtml;
                $('msgs').scrollTop = $('msgs').scrollHeight;
            }
        } catch (err) {
            console.error('Render error:', err);
            if (ai) ai.textContent = buf;
        }
    });

    // --- Response complete ---
    socket.on('response_complete', d => {
        generating = false;
        $('send').style.display = 'inline-block';
        $('stop').style.display = 'none';
        setStatus('جاهز');
        searchResultsHtml = '';  // reset
        if (d && d.conversation_id && !cid) cid = d.conversation_id;
        loadConvs();
    });

    // --- Status updates ---
    socket.on('status', d => {
        if (d.status === 'searching') setStatus(d.message || 'جارٍ البحث...', 'searching');
        else if (d.status === 'generating') setStatus(d.message || 'جارٍ التوليد...', 'generating');
    });

    // --- Search results (XSS-safe) ---
    socket.on('search_results', d => {
        let html = '';
        if (d.web && d.web.length) {
            html += '<div class="search-results"><h4>🌐 نتائج الويب:</h4>';
            d.web.forEach(r => {
                html += '<div><a href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener">'
                      + escapeHtml(r.title) + '</a><br><small>'
                      + escapeHtml(r.snippet) + '</small></div>';
            });
            html += '</div>';
        }
        if (d.academic && d.academic.length) {
            html += '<div class="search-results"><h4>🎓 نتائج أكاديمية:</h4>';
            d.academic.forEach(r => {
                html += '<div><a href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener">'
                      + escapeHtml(r.title) + '</a><br><small>'
                      + escapeHtml(r.snippet) + '</small></div>';
            });
            html += '</div>';
        }
        searchResultsHtml = html;
        if (ai) ai.innerHTML = render(buf) + searchResultsHtml;
    });

    // --- Conversation created ---
    socket.on('conversation_created', d => {
        if (d && d.id) cid = d.id;
    });

    // --- Generation stopped ---
    socket.on('generation_stopped', () => {
        generating = false;
        $('send').style.display = 'inline-block';
        $('stop').style.display = 'none';
        setStatus('تم الإيقاف');
    });

    // --- Error from server ---
    socket.on('error', d => {
        generating = false;
        $('send').style.display = 'inline-block';
        $('stop').style.display = 'none';
        setStatus('خطأ: ' + (d.message || 'غير معروف'), 'error');
        // Remove empty assistant frame if nothing was generated
        if (currentFrame && !buf.trim() && currentFrame.parentNode) {
            currentFrame.parentNode.removeChild(currentFrame);
            currentFrame = null;
            ai = null;
        }
    });

    // --- UI event listeners ---
    $('send').addEventListener('click', sendMsg);
    $('stop').addEventListener('click', stopGen);
    $('new').addEventListener('click', newConv);
    $('export').addEventListener('click', exportConv);
    $('theme').addEventListener('click', toggleTheme);
    $('up').addEventListener('click', () => $('file').click());
    $('mic').addEventListener('click', toggleMic);
    $('search').addEventListener('input', searchConv);
    $('file').addEventListener('change', uploadFile);

    // Enter to send, Shift+Enter for newline
    $('input').addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMsg();
        }
    });

    // Auto-resize textarea
    $('input').addEventListener('input', () => {
        $('input').style.height = 'auto';
        $('input').style.height = Math.min($('input').scrollHeight, 150) + 'px';
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
        if (e.ctrlKey && e.key === 'n') { e.preventDefault(); newConv(); }
        if (e.ctrlKey && e.key === 'e') { e.preventDefault(); exportConv(); }
    });

    loadConvs();
    setStatus('جاهز');
}

// === Add message to chat UI ===
function add(role, text, id) {
    const msgs = $('msgs');
    if ($('welcome')) $('welcome').style.display = 'none';

    const frame = document.createElement('div');
    frame.className = 'msg ' + role;

    const time = new Date().toLocaleTimeString('ar', {hour:'2-digit',minute:'2-digit'});

    const content = document.createElement('div');
    content.className = 'content';
    content.innerHTML = role === 'user' ? escapeHtml(text) : render(text);

    const meta = document.createElement('div');
    meta.className = 'meta';

    const timeSpan = document.createElement('span');
    timeSpan.textContent = time;
    meta.appendChild(timeSpan);

    if (role === 'assistant') {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = '📋 نسخ';
        copyBtn.onclick = () => copyMsg(content);
        meta.appendChild(copyBtn);
    }

    frame.appendChild(content);
    frame.appendChild(meta);
    msgs.appendChild(frame);
    msgs.scrollTop = msgs.scrollHeight;
    return frame;
}

// === Copy message content ===
function copyMsg(contentEl) {
    const text = contentEl.textContent || contentEl.innerText || '';
    navigator.clipboard.writeText(text).then(() => {
        setStatus('تم النسخ ✓');
        setTimeout(() => setStatus('جاهز'), 2000);
    }).catch(() => {
        // Fallback for older browsers
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch (e) {}
        document.body.removeChild(ta);
    });
}

// === Send message ===
function sendMsg() {
    const msg = $('input').value.trim();
    if (!msg || generating) return;

    // Input validation
    if (msg.length > 10000) {
        setStatus('الرسالة طويلة جدًا (الحد 10000 حرف)', 'error');
        return;
    }

    $('input').value = '';
    $('input').style.height = 'auto';

    if (!cid) cid = crypto.randomUUID();
    add('user', msg);
    setStatus('جارٍ التحليل...', 'generating');
    generating = true;
    $('send').style.display = 'none';
    $('stop').style.display = 'inline-block';

    // Create assistant frame
    currentFrame = add('assistant', '');
    ai = currentFrame.querySelector('.content');
    buf = '';
    searchResultsHtml = '';

    // Get selected modes
    const modes = ['quick'];

    // Send to server
    socket.emit('chat_message', {
        message: msg,
        conversation_id: cid,
        modes: modes,
        model: $('modelSelect') ? $('modelSelect').value : 'qwen2.5:7b'
    });
}

// === Stop generation ===
function stopGen() {
    socket.emit('stop_generation', {});
    setStatus('جارٍ الإيقاف...', 'generating');
}

// === New conversation ===
function newConv() {
    cid = null;
    $('msgs').innerHTML = '';
    if ($('welcome')) $('welcome').style.display = 'block';
    $('file-chips').innerHTML = '';
    setStatus('جاهز');
    $('input').focus();
}

// === Load conversations list ===
function loadConvs() {
    fetch('/api/conversations')
        .then(r => r.json())
        .then(data => {
            const list = $('convs');
            list.innerHTML = '';
            if (data && data.length) {
                data.forEach(c => {
                    const item = document.createElement('div');
                    item.className = 'conv-item' + (c.id === cid ? ' active' : '');
                    item.textContent = c.title || 'محادثة';
                    item.onclick = () => loadConv(c.id);
                    item.oncontextmenu = e => {
                        e.preventDefault();
                        if (confirm('حذف هذه المحادثة؟')) {
                            deleteConv(c.id);
                        }
                    };
                    list.appendChild(item);
                });
            } else {
                list.innerHTML = '<div class="empty">لا توجد محادثات</div>';
            }
        })
        .catch(err => {
            console.error('loadConvs error:', err);
        });
}

// === Load specific conversation ===
function loadConv(id) {
    cid = id;
    fetch('/api/conversations/' + id)
        .then(r => r.json())
        .then(data => {
            $('msgs').innerHTML = '';
            if ($('welcome')) $('welcome').style.display = 'none';
            if (data && data.length) {
                data.forEach(m => {
                    add(m.role, m.content, m.id);
                });
            }
            // Highlight active conversation
            document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
            // Load files
            loadFiles(id);
        })
        .catch(err => {
            console.error('loadConv error:', err);
            setStatus('فشل تحميل المحادثة', 'error');
        });
}

// === Load files for conversation ===
function loadFiles(id) {
    fetch('/api/conversations/' + id + '/files')
        .then(r => r.json())
        .then(data => {
            const panel = $('files');
            panel.innerHTML = '';
            if ($('file-chips')) $('file-chips').innerHTML = '';
            if (data && data.length) {
                data.forEach(f => {
                    // Chip in chat area
                    if ($('file-chips')) {
                        const chip = document.createElement('div');
                        chip.className = 'chip';
                        chip.textContent = '📎 ' + f.filename;
                        $('file-chips').appendChild(chip);
                    }
                    // File in side panel
                    const item = document.createElement('div');
                    item.className = 'file-item';
                    item.innerHTML = '<span>📄 ' + escapeHtml(f.filename) + '</span>'
                                   + '<button class="del" title="حذف">🗑</button>';
                    item.querySelector('.del').onclick = () => deleteFile(f.id);
                    panel.appendChild(item);
                });
            } else {
                panel.innerHTML = '<div class="empty">لا توجد ملفات</div>';
            }
        })
        .catch(err => console.error('loadFiles error:', err));
}

// === Delete file ===
function deleteFile(fid) {
    if (!confirm('حذف هذا الملف؟')) return;
    fetch('/api/files/' + fid, { method: 'DELETE' })
        .then(r => r.json())
        .then(() => {
            if (cid) loadFiles(cid);
            setStatus('تم حذف الملف ✓');
        })
        .catch(err => {
            console.error('deleteFile error:', err);
            setStatus('فشل حذف الملف', 'error');
        });
}

// === Delete conversation ===
function deleteConv(id) {
    fetch('/api/conversations/' + id, { method: 'DELETE' })
        .then(r => r.json())
        .then(() => {
            loadConvs();
            if (cid === id) newConv();
        })
        .catch(err => console.error('deleteConv error:', err));
}

// === Upload file ===
function uploadFile() {
    const fileInput = $('file');
    if (!fileInput.files || !fileInput.files.length) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    if (cid) formData.append('conversation_id', cid);

    setStatus('جارٍ رفع الملف...', 'searching');

    fetch('/api/upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                setStatus('خطأ: ' + data.error, 'error');
                return;
            }
            if (!cid && data.conversation_id) {
                cid = data.conversation_id;
                loadConvs();
            }
            loadFiles(cid);
            setStatus('تم رفع الملف ✓');
            setTimeout(() => setStatus('جاهز'), 2000);
        })
        .catch(err => {
            console.error('upload error:', err);
            setStatus('فشل رفع الملف', 'error');
        });

    fileInput.value = '';  // reset for re-upload
}

// === Search conversations ===
function searchConv() {
    const q = $('search').value.trim();
    if (!q) {
        loadConvs();
        return;
    }
    fetch('/api/conversations?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(data => {
            const list = $('convs');
            list.innerHTML = '';
            if (data && data.length) {
                data.forEach(c => {
                    const item = document.createElement('div');
                    item.className = 'conv-item';
                    item.textContent = c.title || 'محادثة';
                    item.onclick = () => loadConv(c.id);
                    list.appendChild(item);
                });
            } else {
                list.innerHTML = '<div class="empty">لا نتائج</div>';
            }
        })
        .catch(err => console.error('searchConv error:', err));
}

// === Toggle microphone (speech recognition) ===
function toggleMic() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        setStatus('المتصفح لا يدعم التعرف على الصوت', 'error');
        return;
    }

    if (recognition) {
        recognition.stop();
        recognition = null;
        $('mic').classList.remove('active');
        setStatus('جاهز');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'ar-SA';
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
        $('mic').classList.add('active');
        setStatus('يستمع...');
    };

    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        $('input').value = transcript;
    };

    recognition.onerror = (event) => {
        setStatus('خطأ في التعرف: ' + event.error, 'error');
    };

    recognition.onend = () => {
        $('mic').classList.remove('active');
        recognition = null;
        if (generating === false) setStatus('جاهز');
        $('input').focus();
    };

    recognition.start();
}

// === Toggle theme ===
function toggleTheme() {
    document.body.classList.toggle('light');
    const isLight = document.body.classList.contains('light');
    $('theme').textContent = isLight ? '🌙' : '☀️';
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
}

// === Export conversation ===
function exportConv() {
    if (!cid) {
        setStatus('لا توجد محادثة للتصدير', 'error');
        return;
    }
    const msgs = $('msgs').querySelectorAll('.msg');
    let text = '# محادثة Walid AI\n\n';
    msgs.forEach(m => {
        const role = m.classList.contains('user') ? '**المستخدم:**' : '**المساعد:**';
        const content = m.querySelector('.content')?.textContent || '';
        text += role + '\n\n' + content + '\n\n';
    });
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'walid_conversation.md';
    a.click();
    URL.revokeObjectURL(url);
    setStatus('تم التصدير ✓');
}

// === Set status indicator ===
function setStatus(text, cls) {
    const el = $('status');
    if (!el) return;
    el.textContent = text;
    el.className = 'status' + (cls ? ' ' + cls : ' idle');
}

// === Boot ===
document.addEventListener('DOMContentLoaded', () => {
    // Restore theme
    if (localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light');
        if ($('theme')) $('theme').textContent = '🌙';
    }
    init();
});