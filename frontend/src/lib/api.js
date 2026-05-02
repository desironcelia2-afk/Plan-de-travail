import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

// Build full URL for photo (photo_url is served like "/api/files/<path>")
export const photoSrc = (photoUrl) => (photoUrl ? `${BACKEND_URL}${photoUrl}` : null);

export const getAdminPassword = () => sessionStorage.getItem("admin_password") || "";
export const setAdminPassword = (p) => sessionStorage.setItem("admin_password", p);
export const clearAdminPassword = () => sessionStorage.removeItem("admin_password");

export const adminHeaders = () => ({
  headers: { "X-Admin-Password": getAdminPassword() },
});
