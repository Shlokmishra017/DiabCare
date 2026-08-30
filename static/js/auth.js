/**
 * DiabCare AI - Auth Module
 */
import { apiFetch } from "./api.js";

export function getInitials(name) {
    if (!name) return "PT";
    const parts = name.trim().split(" ");
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].slice(0, 2).toUpperCase();
}

export function handleLogout(warningMessage) {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("refresh_token");
    sessionStorage.removeItem("user");

    const loginEmail = document.getElementById("login-email");
    const loginPassword = document.getElementById("login-password");
    const loginErrorBanner = document.getElementById("login-error-banner");

    if (loginEmail) loginEmail.value = "";
    if (loginPassword) loginPassword.value = "";

    if (loginErrorBanner) {
        if (warningMessage) {
            loginErrorBanner.textContent = warningMessage;
            loginErrorBanner.style.display = "block";
        } else {
            loginErrorBanner.textContent = "";
            loginErrorBanner.style.display = "none";
        }
    }

    window.location.reload();
}
