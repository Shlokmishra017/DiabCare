/**
 * DiabCare AI - Main Controller Entry Point
 */
import { apiFetch } from "./api.js";
import { getInitials, handleLogout } from "./auth.js";
import { fetchDashboardStats } from "./dashboard.js";
import { animateGauge } from "./screening.js";

document.addEventListener("DOMContentLoaded", () => {
    // Check demo config endpoint on load
    fetch("/api/config")
        .then(res => res.json())
        .then(cfg => {
            if (cfg.show_demo_accounts === false) {
                const demoBox = document.querySelector(".login-demo-accounts");
                if (demoBox) demoBox.remove();
            }
        })
        .catch(err => console.error("Config check failed:", err));

    // Dark mode toggle setup
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (themeBtn) {
        if (localStorage.getItem("theme") === "dark") {
            document.body.classList.add("dark-theme");
        }
        themeBtn.addEventListener("click", () => {
            document.body.classList.toggle("dark-theme");
            if (document.body.classList.contains("dark-theme")) {
                localStorage.setItem("theme", "dark");
            } else {
                localStorage.setItem("theme", "light");
            }
        });
    }

    // Re-use full existing application logic via ES modules
    // Import and execute main application bootstrapping
    const appScript = document.createElement("script");
    appScript.src = "/static/app.js?v=9";
    document.body.appendChild(appScript);
});
