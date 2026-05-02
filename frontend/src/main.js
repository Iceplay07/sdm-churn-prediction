import React from "react";
import { createRoot } from "react-dom/client";
import { html } from "htm/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App.js";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const root = createRoot(document.getElementById("root"));
root.render(html`
  <${React.StrictMode}>
    <${BrowserRouter}>
      <${QueryClientProvider} client=${queryClient}>
        <${App} />
      <//>
    <//>
  <//>
`);
