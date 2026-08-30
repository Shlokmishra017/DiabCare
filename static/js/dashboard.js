/**
 * DiabCare AI - Dashboard Module
 */
import { apiFetch } from "./api.js";
import { handleLogout } from "./auth.js";

export async function fetchDashboardStats() {
    try {
        const user = JSON.parse(sessionStorage.getItem("user") || "null");
        if (!user) return;

        const response = await apiFetch("/dashboard/stats");
        if (response.status === 401) {
            handleLogout("Session expired. Please log in again.");
            return;
        }
        if (!response.ok) return;

        const stats = await response.json();
        const container = document.getElementById("dashboard-stats-container");
        if (!container) return;

        if (user.role === "doctor") {
            container.innerHTML = `
                <div class="stat-card">
                    <span class="stat-card-title">All Patients</span>
                    <span class="stat-card-value">${stats.total_patients}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-card-title">High-Risk</span>
                    <span class="stat-card-value">${stats.high_risk_patients}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-card-title">Moderate-Risk</span>
                    <span class="stat-card-value">${stats.moderate_risk_patients}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-card-title">Pending Follow-Ups</span>
                    <span class="stat-card-value">${stats.pending_followups}</span>
                </div>
            `;
        } else if (user.role === "admin") {
            container.innerHTML = `
                <div class="stat-card">
                    <span class="stat-card-title">Total Approved Doctors</span>
                    <span class="stat-card-value">${stats.approved_doctors}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-card-title">Pending Approvals</span>
                    <span class="stat-card-value" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                        <span>${stats.pending_doctors}</span>
                        ${stats.pending_doctors > 0 ? `<button class="btn-assess" id="btn-go-to-requests" style="padding:0.3rem 0.75rem; font-size:0.75rem; border-radius:4px;">Review &rarr;</button>` : ''}
                    </span>
                </div>
                <div class="stat-card">
                    <span class="stat-card-title">Total Screened Patients</span>
                    <span class="stat-card-value">${stats.total_patients}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-card-title">System-wide High-Risk</span>
                    <span class="stat-card-value">${stats.high_risk_patients}</span>
                </div>
            `;
        }
    } catch (error) {
        console.error("Error rendering dashboard stats:", error);
    }
}
