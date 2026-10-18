import React from "react";
import ReactDOM from "react-dom/client";
import "./base.css";
import QuantumSonificationPage from "./pages/research/QuantumSonificationPage";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QuantumSonificationPage />
    <footer className="deployment-footer" aria-label="Código y reproducibilidad">
      <span>QuantumHub · Interfaz V3 · Muestras precargadas</span>
      <a href="https://github.com/valirus/Quantum-Sonification-Bloch-V1" target="_blank" rel="noopener noreferrer">Repositorio científico</a>
      <a href="https://github.com/valirus/Quantum-Sonification-Bloch-V1/tree/bb31388202666a6ab1a365b912b4e2992429a7c6" target="_blank" rel="noopener noreferrer">Motor de referencia</a>
    </footer>
  </React.StrictMode>,
);
