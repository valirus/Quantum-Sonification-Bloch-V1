import "./branding.css";

const mentors = ["Rocio Carhuancho", "Dominique Heger"];
const researchers = [
  "Valentino Gamboa",
  "Vania Pachas",
  "Dayana Gomez",
  "Javier Jara",
  "Cristopher Lévano",
];

export function BrandFooter() {
  return (
    <footer className="qhub-footer" aria-labelledby="qhub-credits-title">
      <div className="qhub-footer-inner">
        <div className="qhub-footer-grid">
          <div className="qhub-footer-identity">
            <a
              className="qhub-footer-brand"
              href="https://www.qhubperu.com/"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Visitar QuantumHub Perú, se abre en una pestaña nueva"
            >
              <img
                src="/branding/quantumhub-wordmark-light.svg"
                alt="QuantumHub Perú"
                width="224"
                height="101"
                loading="lazy"
              />
              <span>qhubperu.com <span aria-hidden="true">↗</span></span>
            </a>
            <p>Investigación, desarrollo y comunidad.</p>
          </div>

          <section className="qhub-footer-credits">
            <p className="qhub-footer-eyebrow">El equipo detrás del proyecto</p>
            <h2 id="qhub-credits-title">Créditos</h2>
            <p className="qhub-footer-affiliation">Quantum software researchers · QuantumHub Perú</p>
            <div className="qhub-footer-groups">
              <section aria-labelledby="qhub-mentors-title">
                <h3 id="qhub-mentors-title">Mentores</h3>
                <ul>{mentors.map(name => <li key={name}>{name}</li>)}</ul>
              </section>
              <section aria-labelledby="qhub-researchers-title">
                <h3 id="qhub-researchers-title">Investigadores / Desarrolladores</h3>
                <ul className="qhub-footer-researchers">{researchers.map(name => <li key={name}>{name}</li>)}</ul>
              </section>
            </div>
          </section>
        </div>

        <div className="qhub-footer-base">
          <span>Quantum Sonification · Interfaz V3 · Muestras precargadas</span>
          <nav aria-label="Código y reproducibilidad">
            <a href="https://github.com/valirus/Quantum-Sonification-Bloch-V1" target="_blank" rel="noopener noreferrer">Repositorio científico</a>
            <a href="https://github.com/valirus/Quantum-Sonification-Bloch-V1/tree/bb31388202666a6ab1a365b912b4e2992429a7c6" target="_blank" rel="noopener noreferrer">Motor de referencia</a>
          </nav>
        </div>
      </div>
    </footer>
  );
}
