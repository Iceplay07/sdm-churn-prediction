import axios from "axios";

const API_URL = window.__SDM_API_URL__ || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
});
