/* === USSD CHAT MODULE === */
const ChatModule = {
  paneId: 'jarvis-chat',
  messages: [],
  turns: 0,

  init() {
    const input = document.querySelector('#jarvis-chat .chat-input-row input');
    const sendBtn = document.querySelector('#jarvis-chat .chat-send');
    if (sendBtn) sendBtn.addEventListener('click', () => this.send());
    if (input) input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.send();
    });
    this.addSystem(`USSD Code: ${CONFIG.USSD.CODE} · Max ${CONFIG.USSD.MAX_TURNS} turns · ${CONFIG.USSD.MAX_CHARS} chars per message`);
  },

  addSystem(text) {
    this.messages.push({ role: 'system', text });
    this.render();
  },

  addUser(text) {
    this.messages.push({ role: 'user', text });
    this.turns++;
    this.render();
  },

  addAssistant(text) {
    this.messages.push({ role: 'assistant', text });
    this.render();
  },

  render() {
    const container = document.querySelector('#jarvis-chat .chat-messages');
    const turnInfo = document.querySelector('#jarvis-chat .chat-turn-info');
    if (!container) return;
    container.innerHTML = this.messages.map(m => `
      <div class="chat-msg">
        <div class="msg-role ${m.role}">${m.role.toUpperCase()}</div>
        <div class="msg-text">${m.text}</div>
      </div>
    `).join('');
    container.scrollTop = container.scrollHeight;
    if (turnInfo) {
      turnInfo.textContent = `Turn ${this.turns}/${CONFIG.USSD.MAX_TURNS}`;
    }
    const sendBtn = document.querySelector('#jarvis-chat .chat-send');
    const input = document.querySelector('#jarvis-chat .chat-input-row input');
    if (sendBtn) sendBtn.disabled = this.turns >= CONFIG.USSD.MAX_TURNS;
    if (input) input.disabled = this.turns >= CONFIG.USSD.MAX_TURNS;
  },

  async send() {
    const input = document.querySelector('#jarvis-chat .chat-input-row input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    if (text.length > CONFIG.USSD.MAX_CHARS) {
      Toast.show(`Message exceeds ${CONFIG.USSD.MAX_CHARS} character limit`, 'warning');
      return;
    }
    if (this.turns >= CONFIG.USSD.MAX_TURNS) {
      Toast.show('Maximum turns reached for this session', 'warning');
      return;
    }

    input.value = '';
    this.addUser(text);

    try {
      const res = await API.post(CONFIG.JARVIS.CHAT, {
        message: text,
        session_id: 'web_' + Date.now(),
        turn: this.turns
      });
      this.addAssistant(res.reply || res.message || res.response || JSON.stringify(res));
    } catch (e) {
      this.addAssistant(this.mockReply(text));
    }
  },

  mockReply(userMsg) {
    const lower = userMsg.toLowerCase();
    if (lower.includes('help') || lower.includes('emergency')) {
      return 'AJALI EMERGENCY SYSTEM\n1. Report Accident\n2. Request Ambulance\n3. Fire Emergency\n4. Police Assistance\nReply with number to continue.';
    }
    if (lower.includes('1') || lower.includes('report')) {
      return 'ACCIDENT REPORT\nShare your location (county name) and brief description. E.g: "Nairobi multi-car crash on Mombasa Rd"';
    }
    if (lower.includes('2') || lower.includes('ambulance')) {
      return 'AMBULANCE DISPATCH\nNearest unit: St John Ambulance Nairobi\nETA: ~8 minutes\nStay on the line. Keep casualty warm and still.';
    }
    if (lower.includes('3') || lower.includes('fire')) {
      return 'FIRE RESPONSE\nNearest unit: Nairobi Fire & Rescue\nETA: ~6 minutes\nEvacuate the area. Do not re-enter the building.';
    }
    if (lower.includes('4') || lower.includes('police')) {
      return 'POLICE DISPATCH\nNearest unit: Nairobi Central Police\nETA: ~10 minutes\nSecure the scene. Do not disturb evidence.';
    }
    if (lower.includes('nairobi') || lower.includes('mombasa') || lower.includes('kisumu')) {
      return 'Alert received for ' + userMsg.split(' ')[0] + '.\nEmergency services have been notified.\nHelp is on the way. Stay safe.';
    }
    return 'AJALI SYSTEM\n1. Report Accident\n2. Request Ambulance\n3. Fire Emergency\n4. Police Assistance\nOr describe your emergency.';
  }
};