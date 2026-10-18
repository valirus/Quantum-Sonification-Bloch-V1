import React from "react";
import ReactDOM from "react-dom/client";
import "./base.css";
import QuantumSonificationPage from "./pages/research/QuantumSonificationPage";
import { BrandFooter } from "./branding/BrandFooter";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QuantumSonificationPage />
    <BrandFooter />
  </React.StrictMode>,
);
