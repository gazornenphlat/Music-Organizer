customElements.define("iconify-icon", class extends HTMLElement {
  static get observedAttributes() { return ["icon"]; }
  connectedCallback() { this.render(); }
  attributeChangedCallback() { if (this.isConnected) this.render(); }
  render() {
    const name = (this.getAttribute("icon") || "").replace(/^solar:/, "");
    const body = window.SOLAR_ICONS[name];
    this.innerHTML = body
      ? `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" aria-hidden="true" style="display:block">${body}</svg>`
      : "";
  }
});
