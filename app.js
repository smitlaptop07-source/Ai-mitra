(() => {
  const form = document.getElementById('chatForm');
  if (!form) return;
  const chatBody = document.getElementById('chatBody');
  const input = document.getElementById('messageInput');
  const imageInput = document.getElementById('imageInput');
  const videoInput = document.getElementById('videoInput');
  const sendButton = document.getElementById('sendButton');
  const note = document.getElementById('composerNote');

  function addBubble(text, who, label) {
    const bubble = document.createElement('div');
    bubble.className = `bubble ${who}`;
    if (label) {
      const small = document.createElement('small');
      small.textContent = label;
      bubble.appendChild(small);
    }
    const content = document.createElement('div');
    // textContent avoids interpreting model output as HTML.
    content.textContent = text;
    bubble.appendChild(content);
    chatBody.appendChild(bubble);
    chatBody.scrollTop = chatBody.scrollHeight;
    return bubble;
  }

  function selectedFile() { return imageInput.files[0] || videoInput.files[0] || null; }
  function updateFileNote() {
    const file = selectedFile();
    note.textContent = file ? `जोडलेली फाइल: ${file.name}` : 'फोटो उजेडात आणि सरळ काढा. फाइल कमाल १५ MB. व्हिडिओसाठी थोडा जास्त वेळ लागू शकतो.';
    if (imageInput.files.length) videoInput.value = '';
    if (videoInput.files.length) imageInput.value = '';
  }
  imageInput.addEventListener('change', updateFileNote);
  videoInput.addEventListener('change', updateFileNote);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    const file = selectedFile();
    if (!message && !file) {
      note.textContent = 'कृपया प्रश्न लिहा किंवा फोटो/व्हिडिओ जोडा.';
      input.focus();
      return;
    }
    if (file && file.size > 15 * 1024 * 1024) {
      note.textContent = 'फाइल १५ MB पेक्षा लहान असावी.';
      return;
    }

    const visibleQuestion = message || (file ? `कृपया ही फाइल समजावून सांगा: ${file.name}` : '');
    addBubble(visibleQuestion, 'me');
    const pending = addBubble('उत्तर तयार होत आहे…', 'mitra', 'AI MITRA');
    pending.setAttribute('aria-label', 'उत्तर तयार होत आहे');
    sendButton.disabled = true;
    sendButton.setAttribute('aria-busy', 'true');
    input.disabled = true;
    note.textContent = 'AI उत्तर तयार करत आहे. कृपया थांबा…';

    const data = new FormData();
    data.append('message', message);
    if (file) data.append('attachment', file);
    try {
      const response = await fetch('/api/ask', { method: 'POST', body: data });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || 'काहीतरी चुकलं. कृपया पुन्हा प्रयत्न करा.');
      pending.replaceChildren();
      const label = document.createElement('small');
      label.textContent = 'AI MITRA';
      const answer = document.createElement('div');
      answer.textContent = result.answer || 'उत्तर उपलब्ध नाही.';
      pending.append(label, answer);
      pending.removeAttribute('aria-label');
      input.value = '';
      imageInput.value = '';
      videoInput.value = '';
      note.textContent = 'पुढचा प्रश्न विचारू शकता.';
    } catch (error) {
      pending.remove();
      addBubble(error.message || 'सर्व्हरशी संपर्क झाला नाही. कृपया पुन्हा प्रयत्न करा.', 'mitra', 'त्रुटी');
      note.textContent = 'प्रश्न पाठवता आला नाही. इंटरनेट किंवा सर्व्हर तपासा.';
    } finally {
      sendButton.disabled = false;
      sendButton.removeAttribute('aria-busy');
      input.disabled = false;
      input.focus();
    }
  });
})();
