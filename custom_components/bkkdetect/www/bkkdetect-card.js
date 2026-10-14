// Install this module as /local/bkkdetect-card.js in Home Assistant.
class BkkDetectCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error('entity is required');
    this.config = { show_details: true, show_confidence: true, language: 'en', ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this.render();
  }
  set hass(hass) {
    this._hass = hass;
    this.render();
  }
  getCardSize() {
    return this.config?.show_details ? 4 : 2;
  }
  render() {
    if (!this.config || !this._hass) return;
    const s = this._hass.states[this.config.entity],
      a = s?.attributes ?? {},
      hu = this.config.language === 'hu',
      root = this.shadowRoot;
    root.replaceChildren();
    const style = document.createElement('style');
    style.textContent = `ha-card{padding:20px}h2{margin:0 0 15px;font-size:18px}.eta{font-size:36px;font-weight:600}.muted{color:var(--secondary-text-color);font-size:12px;margin:10px 0}.leg{padding:9px 0;border-top:1px solid var(--divider-color);font-size:13px}.line{font-weight:700;margin-right:10px}.inferred{color:var(--warning-color)}button{font:inherit;background:none;border:0;color:var(--primary-color);cursor:pointer;padding:0;margin-top:10px}`;
    root.append(style);
    const card = document.createElement('ha-card');
    root.append(card);
    const text = (tag, value, cls) => {
      const el = document.createElement(tag);
      el.textContent = value;
      if (cls) el.className = cls;
      card.append(el);
      return el;
    };
    text('h2', this.config.name ?? a.friendly_name ?? 'BKK Detect');
    text(
      'div',
      a.eta_minutes === null || a.eta_minutes === undefined
        ? '—'
        : `${a.status === 'inferred' ? '~' : ''}${a.eta_minutes} ${hu ? 'perc' : 'min'}`,
      'eta',
    );
    text('div', s?.state ?? (hu ? 'Nem elérhető' : 'Unavailable'), 'muted');
    if (a.status === 'inferred')
      text(
        'div',
        hu ? 'Becsült metróút · nincs friss GPS' : 'Inferred metro journey · no fresh GPS',
        'muted inferred',
      );
    if (a.source === 'suggested_itinerary')
      text(
        'div',
        hu ? 'Javasolt útvonal indulás esetén' : 'Suggested route if leaving now',
        'muted',
      );
    if (this.config.show_confidence)
      text(
        'div',
        `${hu ? 'Megbízhatóság' : 'Confidence'}: ${Math.round((a.confidence ?? 0) * 100)}%`,
        'muted',
      );
    if (this.config.show_details)
      for (const l of a.legs ?? []) {
        const row = text('div', '', 'leg');
        const label = document.createElement('span');
        label.className = 'line';
        label.textContent = l.line || l.mode;
        row.append(label, document.createTextNode(`${l.from} → ${l.to}`));
        const info = document.createElement('div');
        info.className = 'muted';
        info.textContent = `${new Date(l.arrival).toLocaleTimeString(hu ? 'hu' : 'en', { hour: '2-digit', minute: '2-digit' })} · ${l.realtime ? (hu ? 'Élő' : 'Live') : hu ? 'Menetrend' : 'Timetable'}`;
        row.append(info);
      }
    const button = text('button', hu ? 'Részletek' : 'More info');
    button.addEventListener('click', () =>
      this.dispatchEvent(
        new CustomEvent('hass-more-info', {
          detail: { entityId: this.config.entity },
          bubbles: true,
          composed: true,
        }),
      ),
    );
  }
}
if (!customElements.get('bkkdetect-card')) customElements.define('bkkdetect-card', BkkDetectCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'bkkdetect-card',
  name: 'BKK Detect',
  description: 'BKK commute and home arrival estimate',
});
