import { html } from "htm/react";
import { Routes, Route, Navigate } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage.js";
import { ClientCardPage } from "./pages/ClientCardPage.js";

export function App() {
  return html`
    <${Routes}>
      <${Route} path="/" element=${html`<${DashboardPage} />`} />
      <${Route} path="/clients/:id" element=${html`<${ClientCardPage} />`} />
      <${Route} path="*" element=${html`<${Navigate} to="/" replace />`} />
    <//>
  `;
}
