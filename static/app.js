/**
 * DiabCare AI - Redesigned Frontend Controller
 * ===============================================
 * Drives the hospital light-themed dashboard, patient list table search,
 * SPA transitions, gauge animations, and SHAP cards.
 */

document.addEventListener("DOMContentLoaded", () => {
    
    // Mapped Clinical Identities for seeded patient IDs matching the mockup screenshots
    const PATIENT_MAPPING = {
        "2552952": { uiId: "P-1001", ageGroup: "65-70", gender: "Male", lastEncounter: "Apr 24, 2025" },
        "149190": { uiId: "P-1002", ageGroup: "55-60", gender: "Female", lastEncounter: "Apr 22, 2025" },
        "421194": { uiId: "P-1003", ageGroup: "70-75", gender: "Female", lastEncounter: "Apr 20, 2025" },
        "64410": { uiId: "P-1004", ageGroup: "60-65", gender: "Male", lastEncounter: "Apr 18, 2025" },
        "2549268": { uiId: "P-1005", ageGroup: "45-50", gender: "Male", lastEncounter: "Apr 16, 2025" },
        "2278392": { uiId: "P-1006", ageGroup: "50-55", gender: "Female", lastEncounter: "Apr 14, 2025" }
    };

    // DOM Navigation Views & Layouts
    const appLayout = document.querySelector(".app-layout");
    const overviewView = document.getElementById("overview-view");
    const detailView = document.getElementById("detail-view");
    const newPatientView = document.getElementById("new-patient-view");
    const sidebarOverview = document.getElementById("menu-overview");
    const sidebarPatients = document.getElementById("menu-patients");
    const menuRequests = document.getElementById("menu-requests");
    const requestsView = document.getElementById("requests-view");
    const menuProfile = document.getElementById("menu-profile");
    const menuDoctors = document.getElementById("menu-doctors");
    const menuAdmins = document.getElementById("menu-admins");
    const profileView = document.getElementById("profile-view");
    const doctorsView = document.getElementById("doctors-view");
    const adminsView = document.getElementById("admins-view");
    
    // Login Screen Elements
    const loginView = document.getElementById("login-view");
    const loginSection = document.getElementById("login-section");
    const registerSection = document.getElementById("register-section");
    const linkShowRegister = document.getElementById("link-show-register");
    const linkShowLogin = document.getElementById("link-show-login");
    const loginForm = document.getElementById("login-form");
    const loginEmail = document.getElementById("login-email");
    const loginPassword = document.getElementById("login-password");
    const loginErrorBanner = document.getElementById("login-error-banner");
    
    // Registration Form Elements
    const registerForm = document.getElementById("register-form");
    const registerName = document.getElementById("register-name");
    const registerEmail = document.getElementById("register-email");
    const registerPassword = document.getElementById("register-password");
    const registerErrorBanner = document.getElementById("register-error-banner");
    const registerSuccessBanner = document.getElementById("register-success-banner");
    
    // Sidebar User Profile Block Elements
    const userProfileBlock = document.getElementById("user-profile-block");
    const userAvatarInitials = document.getElementById("user-avatar-initials");
    const userDisplayName = document.getElementById("user-display-name");
    const userDisplayRole = document.getElementById("user-display-role");
    const btnLogout = document.getElementById("btn-logout");

    // Profile Form Elements
    const profileForm = document.getElementById("profile-form");
    const profileName = document.getElementById("profile-name");
    const profileEmail = document.getElementById("profile-email");
    const profileRole = document.getElementById("profile-role");
    const profileEducation = document.getElementById("profile-education");
    const profileReferenceId = document.getElementById("profile-reference-id");
    const profileErrorBanner = document.getElementById("profile-error-banner");
    const profileSuccessBanner = document.getElementById("profile-success-banner");

    // Doctors Directory Elements
    const doctorSearch = document.getElementById("doctor-search");
    const doctorsStatsContainer = document.getElementById("doctors-stats-container");
    const doctorsTableBody = document.getElementById("doctors-table-body");

    // Admin Management Elements
    const createAdminForm = document.getElementById("create-admin-form");
    const newAdminName = document.getElementById("new-admin-name");
    const newAdminEmail = document.getElementById("new-admin-email");
    const newAdminPassword = document.getElementById("new-admin-password");
    const createAdminErrorBanner = document.getElementById("create-admin-error-banner");
    const createAdminSuccessBanner = document.getElementById("create-admin-success-banner");
    const adminsTableBody = document.getElementById("admins-table-body");
    const adminsCountLabel = document.getElementById("admins-count-label");

    // Access Requests Views Elements
    const requestsEmptyState = document.getElementById("requests-empty-state");
    const requestsTableContainer = document.getElementById("requests-table-container");
    const requestsTableBody = document.getElementById("requests-table-body");
    
    // New Screening Form Elements
    const btnNewScreening = document.querySelector(".btn-new-screening");
    const btnNewPatientBack = document.getElementById("new-patient-back");
    const formCancelBtn = document.getElementById("form-cancel-btn");
    const newPatientForm = document.getElementById("new-patient-form");
    const formErrorBanner = document.getElementById("form-error-banner");
    
    // Overview Screen Elements
    const patientSearch = document.getElementById("patient-search");
    const patientListLoading = document.getElementById("patient-list-loading");
    const patientTableBody = document.getElementById("patient-table-body");
    const patientShowingLabel = document.getElementById("patient-showing-label");
    const patientFilterTabs = document.getElementById("patient-filter-tabs");
    const tabFilterAll = document.getElementById("tab-filter-all");
    const tabFilterMy = document.getElementById("tab-filter-my");
    const adminDoctorFilter = document.getElementById("admin-doctor-filter");

    let activePatientFilter = "all";

    // Detail Screen Header Elements
    const backLink = document.getElementById("back-link");
    const detailPatientId = document.getElementById("detail-patient-id");
    const detailAgeGroup = document.getElementById("detail-age-group");
    const detailGender = document.getElementById("detail-gender");
    const detailLastEncounter = document.getElementById("detail-last-encounter");

    // Detail Screen Loading/Results Containers
    const detailLoadingState = document.getElementById("detail-loading-state");
    const detailResultsContainer = document.getElementById("detail-results-container");
    const progressRingFill = document.getElementById("progress-ring-fill");
    const detailRiskPercent = document.getElementById("detail-risk-percent");
    const detailRiskBadge = document.getElementById("detail-risk-badge");

    let activePatientId = null; // Track current active patient ID for follow-ups
    // Follow-Up Status & Scheduling Elements
    const followUpStatusButtons = document.getElementById("follow-up-status-buttons");
    const scheduleDateContainer = document.getElementById("schedule-date-container");
    const scheduledDateInput = document.getElementById("scheduled-date-input");
    const btnSaveFollowUpStatus = document.getElementById("btn-save-follow-up-status");
    const statusSaveFeedback = document.getElementById("status-save-feedback");
    const statusUnauthorizedMessage = document.getElementById("status-unauthorized-message");
    const scheduledDateDisplay = document.getElementById("scheduled-date-display");

    let selectedFollowUpStatus = "Pending";

    function formatScheduledDate(isoStr) {
        if (!isoStr) return "";
        try {
            const d = new Date(isoStr);
            if (isNaN(d.getTime())) return isoStr;
            return d.toLocaleString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
                hour12: true
            });
        } catch (e) {
            return isoStr;
        }
    }
    const priorityAlertBanner = document.getElementById("priority-alert-banner");
    const priorityBannerIcon = document.getElementById("priority-banner-icon");
    const priorityBannerTitle = document.getElementById("priority-banner-title");
    const priorityBannerDescription = document.getElementById("priority-banner-description");
    
    // Risk Factors List
    const detailFactorsList = document.getElementById("detail-factors-list");

    // Local Data Store
    let allPatientsCached = [];
    let activePatientFeatures = null;

    // Helper: Parse Patient Summary
    function parsePatientSummary(summary) {
        if (!summary) return {};
        const features = {};
        const parts = summary.split("|");
        
        // 1. Demographics (e.g. "Female, 10-20 yrs, Caucasian")
        const demoPart = parts[0] ? parts[0].trim() : "";
        const demoSubParts = demoPart.split(",");
        if (demoSubParts[0]) features["gender"] = demoSubParts[0].trim();
        if (demoSubParts[1]) {
            // Strip "yrs" and brackets to get clean age range
            features["age"] = demoSubParts[1].replace("yrs", "").replace("[", "").replace(")", "").trim();
        }
        if (demoSubParts[2]) features["race"] = demoSubParts[2].trim();
        
        // 2. Parse remaining fields
        for (let i = 1; i < parts.length; i++) {
            const part = parts[i].trim();
            if (part.startsWith("Stay:")) {
                features["time_in_hospital"] = part.replace("Stay:", "").replace("d", "").trim();
            } else if (part.startsWith("Prior inpatient:")) {
                features["number_inpatient"] = part.replace("Prior inpatient:", "").trim();
            } else if (part.startsWith("Meds:")) {
                features["num_medications"] = part.replace("Meds:", "").trim();
            } else if (part.startsWith("Lab:")) {
                features["num_lab_procedures"] = part.replace("Lab:", "").trim();
            } else if (part.startsWith("Diagnoses:")) {
                features["number_diagnoses"] = part.replace("Diagnoses:", "").trim();
            } else if (part.startsWith("Outpatient:")) {
                features["number_outpatient"] = part.replace("Outpatient:", "").trim();
            } else if (part.startsWith("Emergency:")) {
                features["number_emergency"] = part.replace("Emergency:", "").trim();
            } else if (part.startsWith("Procedures:")) {
                features["num_procedures"] = part.replace("Procedures:", "").trim();
            }
        }
        
        return features;
    }

    // Helper: Get Raw Value for Factor
    function getRawValueForFactor(labelText) {
        if (!activePatientFeatures) return "Not available";
        
        const labelLower = labelText.toLowerCase();
        
        // 1. Numeric features
        if (labelLower.includes("stay") || labelLower.includes("hospital stay")) {
            const val = activePatientFeatures["time_in_hospital"];
            return val ? `${val} days` : "Not available";
        }
        if (labelLower.includes("lab procedure")) {
            const val = activePatientFeatures["num_lab_procedures"];
            return val ? `${val} procedures` : "Not available";
        }
        if (labelLower.includes("procedures performed") || labelLower.includes("non-lab procedure")) {
            const val = activePatientFeatures["num_procedures"];
            return val !== undefined ? `${val} procedures` : "Not available";
        }
        if (labelLower.includes("medication") && labelLower.includes("prescribed")) {
            const val = activePatientFeatures["num_medications"];
            return val ? `${val} medications` : "Not available";
        }
        if (labelLower.includes("prior outpatient")) {
            const val = activePatientFeatures["number_outpatient"];
            return val !== undefined ? `${val} visits` : "Not available";
        }
        if (labelLower.includes("prior emergency")) {
            const val = activePatientFeatures["number_emergency"];
            return val !== undefined ? `${val} visits` : "Not available";
        }
        if (labelLower.includes("prior inpatient")) {
            const val = activePatientFeatures["number_inpatient"];
            return val !== undefined ? `${val} visits` : "Not available";
        }
        if (labelLower.includes("diagnoses")) {
            const val = activePatientFeatures["number_diagnoses"];
            return val ? `${val} diagnoses` : "Not available";
        }
        
        // 2. Diagnosis codes
        if (labelLower.includes("primary diagnosis")) {
            const match = labelText.match(/code\s+(\S+)/i);
            if (match && match[1]) return `ICD-9: ${match[1]}`;
            if (activePatientFeatures["diag_1"]) return `ICD-9: ${activePatientFeatures["diag_1"]}`;
        }
        if (labelLower.includes("secondary diagnosis")) {
            const match = labelText.match(/code\s+(\S+)/i);
            if (match && match[1]) return `ICD-9: ${match[1]}`;
            if (activePatientFeatures["diag_2"]) return `ICD-9: ${activePatientFeatures["diag_2"]}`;
        }
        if (labelLower.includes("additional diagnosis")) {
            const match = labelText.match(/code\s+(\S+)/i);
            if (match && match[1]) return `ICD-9: ${match[1]}`;
            if (activePatientFeatures["diag_3"]) return `ICD-9: ${activePatientFeatures["diag_3"]}`;
        }
        
        // 3. Lab values
        if (labelLower.includes("hba1c") || labelLower.includes("a1c")) {
            if (activePatientFeatures["A1Cresult"]) return activePatientFeatures["A1Cresult"];
            const match = labelText.match(/result\s+(.+)$/i);
            return match && match[1] ? match[1] : "Not tested";
        }
        if (labelLower.includes("glucose serum")) {
            if (activePatientFeatures["max_glu_serum"]) return activePatientFeatures["max_glu_serum"];
            const match = labelText.match(/level\s+(.+)$/i);
            return match && match[1] ? match[1] : "Not tested";
        }
        
        // 4. Medications
        const meds = [
            "insulin", "metformin", "repaglinide", "nateglinide", "chlorpropamide",
            "glimepiride", "acetohexamide", "glipizide", "glyburide",
            "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose",
            "miglitol", "troglitazone", "tolazamide", "examide",
            "citoglipton"
        ];
        for (const med of meds) {
            if (labelLower.includes(med)) {
                const key = med === "glyburide-metformin" || med === "glipizide-metformin" || 
                            med === "glimepiride-pioglitazone" || med === "metformin-rosiglitazone" || 
                            med === "metformin-pioglitazone" ? med : med.toLowerCase();
                const val = activePatientFeatures[key];
                const medName = med.charAt(0).toUpperCase() + med.slice(1);
                if (val) return `${medName}: ${val}`;
                
                const words = labelText.split(" ");
                const valDesc = words.slice(1).join(" ");
                return `${medName}: ${valDesc}`;
            }
        }
        
        // 5. Medication Regimen change
        if (labelLower.includes("regimen")) {
            const val = activePatientFeatures["change"];
            if (val === "Ch") return "Regimen changed";
            if (val === "No") return "Regimen not changed";
            return labelText;
        }
        
        // 6. Diabetes medication flag
        if (labelLower.includes("diabetes medication")) {
            const val = activePatientFeatures["diabetesMed"];
            if (val === "Yes") return "On medication";
            if (val === "No") return "Not on medication";
            return labelText;
        }
        
        return labelText;
    }

    let sortState = "risk"; // Default sorting by risk descending

    // 1. Fetch available patients on load
    async function fetchPatients() {
        try {
            const token = sessionStorage.getItem("token");
            if (!token) {
                handleLogout();
                return;
            }
            const response = await fetch("/patients", {
                headers: {
                    "Authorization": "Bearer " + token
                }
            });
            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const patients = await response.json();
            allPatientsCached = patients;

            patientListLoading.classList.add("hidden");
            renderPatientTable();
            fetchDashboardStats(); // update dashboard summary statistics
        } catch (error) {
            console.error("Error loading patient table listing:", error);
            patientListLoading.innerHTML = `<span style="color: var(--high-color);">Failed to load clinical profiles. Is server running?</span>`;
        }
    }

    // Render Patient queue sorting logic and status badge integration
    function renderPatientTable() {
        if (!allPatientsCached) return;

        const currentUser = JSON.parse(sessionStorage.getItem("user") || "{}");
        let patientsCopy = [...allPatientsCached];

        // Apply active patient filter tab/dropdown
        if (activePatientFilter === "my") {
            patientsCopy = patientsCopy.filter(p => p.assigned_doctor_id === currentUser.user_id);
        } else if (activePatientFilter !== "all") {
            patientsCopy = patientsCopy.filter(p => p.assigned_doctor_id === activePatientFilter);
        }
        
        if (sortState === "risk") {
            patientsCopy.sort((a, b) => {
                const riskA = a.risk_percent !== null && a.risk_percent !== undefined ? a.risk_percent : -1;
                const riskB = b.risk_percent !== null && b.risk_percent !== undefined ? b.risk_percent : -1;
                return riskB - riskA;
            });
            document.getElementById("sorting-indicator").innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                Sorted by Risk
            `;
        } else {
            patientsCopy.sort((a, b) => {
                return a.patient_id.localeCompare(b.patient_id, undefined, {numeric: true, sensitivity: 'base'});
            });
            document.getElementById("sorting-indicator").innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                Sorted by ID
            `;
        }

        patientTableBody.innerHTML = "";

        if (patientsCopy.length === 0) {
            patientTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No patients match the selected filter.</td></tr>`;
            updateShowingCount();
            return;
        }

        patientsCopy.forEach(patient => {
            let uiId = `P-${patient.patient_id}`;
            let ageGroup = "70-80";
            let gender = "Female";
            let lastEncounter = "Just Screened";

            // Check mapping for default seeded demo patients
            if (PATIENT_MAPPING[patient.patient_id]) {
                const mapped = PATIENT_MAPPING[patient.patient_id];
                uiId = mapped.uiId;
                ageGroup = mapped.ageGroup;
                gender = mapped.gender;
                lastEncounter = mapped.lastEncounter;
            } else {
                // It's a new screening profile, parse summary details
                const parsed = parsePatientSummary(patient.summary);
                if (parsed.gender) gender = parsed.gender;
                if (parsed.age) ageGroup = parsed.age;
                uiId = `P-${patient.patient_id}`;
            }

            // Follow-up status badge next to Patient ID
            const followUpStatus = patient.follow_up_status || "Pending";
            let badgeClass = "badge-pending";
            let badgeText = followUpStatus;
            
            if (followUpStatus === "Scheduled") {
                badgeClass = "badge-scheduled";
                if (patient.scheduled_date) {
                    badgeText = `Scheduled: ${formatScheduledDate(patient.scheduled_date)}`;
                }
            } else if (followUpStatus === "Completed") {
                badgeClass = "badge-completed";
            }

            let statusHtml = `<span class="status-badge ${badgeClass}">${badgeText}</span>`;
            if (currentUser.role === "admin") {
                statusHtml = `
                    <select class="select-status-toggle" data-patient-id="${patient.patient_id}" style="margin-left: 0.5rem; font-size: 0.78rem; font-weight: 700; padding: 0.15rem 0.35rem; border-radius: 6px; border: 1px solid #cbd5e1; cursor: pointer; background-color: #f8fafc; color: var(--text-primary);">
                        <option value="Pending" ${followUpStatus === "Pending" ? "selected" : ""}>Pending</option>
                        <option value="Scheduled" ${followUpStatus === "Scheduled" ? "selected" : ""}>Scheduled</option>
                        <option value="Completed" ${followUpStatus === "Completed" ? "selected" : ""}>Completed</option>
                    </select>
                `;
            }

            // Assigned Doctor Column HTML
            let assignedDoctorHtml = "";
            if (currentUser.role === "admin") {
                let optionsHtml = `<option value="">-- Unassigned --</option>`;
                cachedDoctorsList.forEach(doc => {
                    if (doc.status === "approved") {
                        const isSel = doc.user_id === patient.assigned_doctor_id ? "selected" : "";
                        optionsHtml += `<option value="${doc.user_id}" ${isSel}>${doc.name}</option>`;
                    }
                });
                assignedDoctorHtml = `<select class="select-doctor-assign" data-patient-id="${patient.patient_id}">${optionsHtml}</select>`;
            } else {
                if (patient.assigned_doctor_id === currentUser.user_id) {
                    assignedDoctorHtml = `<span class="badge-assigned-you">Assigned to You</span>`;
                } else if (patient.assigned_doctor_name) {
                    assignedDoctorHtml = `<span class="badge-assigned-other">${patient.assigned_doctor_name}</span>`;
                } else {
                    assignedDoctorHtml = `<span class="badge-unassigned">Unassigned</span>`;
                }
            }

            const row = document.createElement("tr");
            row.dataset.id = patient.patient_id;
            row.dataset.uiId = uiId;
            row.dataset.ageGroup = ageGroup;
            row.dataset.gender = gender;
            row.dataset.lastEncounter = lastEncounter;
            
            row.innerHTML = `
                <td class="patient-table-id">
                    ${uiId}
                    ${statusHtml}
                </td>
                <td>${ageGroup}</td>
                <td>${gender}</td>
                <td>${lastEncounter}</td>
                <td>${assignedDoctorHtml}</td>
                <td>
                    <button class="btn-assess">Assess Risk &rarr;</button>
                </td>
            `;

            // Admin inline reassignment handler
            const selectAssign = row.querySelector(".select-doctor-assign");
            if (selectAssign) {
                selectAssign.addEventListener("click", (e) => e.stopPropagation());
                selectAssign.addEventListener("change", async (e) => {
                    e.stopPropagation();
                    const newDoctorId = e.target.value;
                    try {
                        const token = sessionStorage.getItem("token");
                        const res = await fetch(`/patients/${patient.patient_id}/assign`, {
                            method: "PATCH",
                            headers: {
                                "Content-Type": "application/json",
                                "Authorization": "Bearer " + token
                            },
                            body: JSON.stringify({ doctor_id: newDoctorId })
                        });
                        if (!res.ok) {
                            const err = await res.json().catch(() => ({}));
                            throw new Error(err.detail || "Failed to assign doctor.");
                        }
                        patient.assigned_doctor_id = newDoctorId || null;
                        fetchPatients(); // Refresh list & update UI
                    } catch (err) {
                        alert(`Assignment error: ${err.message}`);
                    }
                });
            }

            // Admin inline status change handler
            const selectStatus = row.querySelector(".select-status-toggle");
            if (selectStatus) {
                selectStatus.addEventListener("click", (e) => e.stopPropagation());
                selectStatus.addEventListener("change", async (e) => {
                    e.stopPropagation();
                    const newStatus = e.target.value;
                    try {
                        const token = sessionStorage.getItem("token");
                        const res = await fetch(`/predict/${patient.patient_id}/follow-up`, {
                            method: "PATCH",
                            headers: {
                                "Content-Type": "application/json",
                                "Authorization": "Bearer " + token
                            },
                            body: JSON.stringify({ status: newStatus, scheduled_date: null })
                        });
                        if (!res.ok) {
                            const err = await res.json().catch(() => ({}));
                            throw new Error(err.detail || "Failed to update status.");
                        }
                        patient.follow_up_status = newStatus;
                        fetchPatients(); // Refresh list & update UI
                    } catch (err) {
                        alert(`Status update error: ${err.message}`);
                    }
                });
            }

            // Add click triggers
            const triggerAssess = () => {
                openPatientScreening(patient.patient_id, uiId, ageGroup, gender, lastEncounter);
            };
            
            row.addEventListener("click", (e) => {
                if (e.target.tagName !== "BUTTON" && e.target.tagName !== "SELECT") triggerAssess();
            });
            row.querySelector(".btn-assess").addEventListener("click", (e) => {
                e.stopPropagation();
                triggerAssess();
            });

            patientTableBody.appendChild(row);
        });

        updateShowingCount();
    }

    // Helper: update shown patients label count
    function updateShowingCount() {
        const rows = patientTableBody.querySelectorAll("tr");
        let visibleCount = 0;
        rows.forEach(r => {
            if (!r.classList.contains("hidden")) visibleCount++;
        });
        patientShowingLabel.textContent = `Showing ${visibleCount} patients`;
    }

    // 2. Real-time patient table search filter
    patientSearch.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const rows = patientTableBody.querySelectorAll("tr");

        rows.forEach(row => {
            const uiId = row.dataset.uiId.toLowerCase();
            const ageGroup = row.dataset.ageGroup.toLowerCase();
            const gender = row.dataset.gender.toLowerCase();
            const lastEncounter = row.dataset.lastEncounter.toLowerCase();

            if (uiId.includes(query) || ageGroup.includes(query) || gender.includes(query) || lastEncounter.includes(query)) {
                row.classList.remove("hidden");
            } else {
                row.classList.add("hidden");
            }
        });

        updateShowingCount();
    });

    // 3. Load prediction and render Detail view (SPA)
    async function openPatientScreening(patientId, uiId, ageGroup, gender, lastEncounter) {
        console.log("openPatientScreening called, patientId:", patientId);
        activePatientId = patientId;
        // Toggle view
        overviewView.classList.add("hidden");
        newPatientView.classList.add("hidden");
        detailView.classList.remove("hidden");
        
        // Update headers immediately
        detailPatientId.textContent = uiId;
        detailAgeGroup.textContent = ageGroup;
        detailGender.textContent = gender;
        detailLastEncounter.textContent = lastEncounter;
        
        // Show loading state
        detailLoadingState.classList.remove("hidden");
        detailResultsContainer.classList.add("hidden");

        // Parse summary features for expansion details
        const patientObj = allPatientsCached.find(p => p.patient_id === patientId);
        if (patientObj) {
            activePatientFeatures = parsePatientSummary(patientObj.summary);
        } else {
            activePatientFeatures = null;
        }

        try {
            const token = sessionStorage.getItem("token");
            const response = await fetch("/predict", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token
                },
                body: JSON.stringify({ patient_id: patientId })
            });

            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                const errMsg = errData.detail || `Predict API error! status: ${response.status}`;
                throw new Error(errMsg);
            }

            const data = await response.json();
            
            // Refresh list to cache prediction risk values
            fetchPatients();
            
            // Brief animation transition delay
            setTimeout(() => {
                detailLoadingState.classList.add("hidden");
                detailResultsContainer.classList.remove("hidden");
                renderDetailsView(data);
            }, 300);

        } catch (error) {
            console.error("Prediction diagnostics failed:", error);
            detailLoadingState.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="var(--high-color)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                <h3 style="margin-top: 1rem;">Diagnostics Error</h3>
                <p style="color: var(--high-color); margin-top: 0.5rem; font-weight: 500;">${error.message}</p>
                <button class="btn-cancel mt-4" id="error-back-btn" style="border:1px solid #cbd5e1; background:#fff;">Return to Patient Search</button>
            `;
            document.getElementById("error-back-btn").addEventListener("click", showOverview);
        }
    }

    // 4. Render details elements
    function renderDetailsView(data) {
        const { risk_percent, risk_category, follow_up_priority, top_factors } = data;

        // --- Render semi-circular gauge ---
        animateGauge(risk_percent);
        
        if (risk_category === "Low") {
            detailRiskBadge.textContent = "LOW RISK";
            detailRiskBadge.style.color = "var(--low-color)";
            progressRingFill.style.stroke = "var(--low-color)";
        } else if (risk_category === "Moderate") {
            detailRiskBadge.textContent = "MODERATE RISK";
            detailRiskBadge.style.color = "var(--mod-color)";
            progressRingFill.style.stroke = "var(--mod-color)";
        } else {
            detailRiskBadge.textContent = "HIGH RISK";
            detailRiskBadge.style.color = "var(--high-color)";
            progressRingFill.style.stroke = "var(--high-color)";
        }

        // --- Render priority banner alert ---
        priorityAlertBanner.className = "priority-alert-box";
        
        if (follow_up_priority === "Low") {
            priorityAlertBanner.classList.add("alert-low");
            priorityBannerTitle.textContent = "LOW FOLLOW-UP PRIORITY";
            priorityBannerDescription.textContent = "Routine post-discharge follow-up priority.";
            priorityBannerIcon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
        } else if (follow_up_priority === "Medium") {
            priorityAlertBanner.classList.add("alert-medium");
            priorityBannerTitle.textContent = "MEDIUM FOLLOW-UP PRIORITY";
            priorityBannerDescription.textContent = "Standard post-discharge follow-up priority.";
            priorityBannerIcon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
        } else {
            priorityAlertBanner.classList.add("alert-high");
            priorityBannerTitle.textContent = "HIGH FOLLOW-UP PRIORITY";
            priorityBannerDescription.textContent = "Prioritize this patient for post-discharge follow-up.";
            priorityBannerIcon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
        }

        // --- Render SHAP Top Risk Factors ---
        detailFactorsList.innerHTML = "";
        
        // Find maximum absolute SHAP value for scaling the bars relative to the strongest factor
        const maxShap = Math.max(...top_factors.map(f => Math.abs(f.shap_value || 0.1)), 0.1);

        top_factors.forEach(item => {
            const isIncrease = item.direction.toLowerCase().includes("increase");
            const isDecrease = item.direction.toLowerCase().includes("decrease");
            
            let arrowClass = "up";
            let subText = "Increases risk";
            let arrowSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>`;

            if (isDecrease) {
                arrowClass = "down";
                subText = "Decreases risk";
                arrowSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>`;
            }

            const labelText = item.factor;
            const factorRow = document.createElement("div");
            factorRow.className = "factor-card-box";
            factorRow.style.flexDirection = "column";
            factorRow.style.alignItems = "stretch";
            factorRow.style.gap = "0.5rem";
            
            const rawValue = getRawValueForFactor(labelText);
            const shapVal = item.shap_value || 0;
            const relativeWidth = ((Math.abs(shapVal) / maxShap) * 100).toFixed(1);

            factorRow.innerHTML = `
                <div style="display: flex; align-items: center; gap: 1rem; width: 100%;">
                    <div class="factor-arrow-indicator ${arrowClass}">
                        ${arrowSvg}
                    </div>
                    <div class="factor-card-content">
                        <span class="factor-card-title">${labelText}</span>
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem;">
                            <span class="factor-card-subtext" style="margin-top: 0;">${subText}</span>
                            <span style="font-size: 0.75rem; font-weight: 700; color: ${isIncrease ? 'var(--high-color)' : 'var(--low-color)'};">SHAP: ${shapVal > 0 ? '+' : ''}${shapVal.toFixed(3)}</span>
                        </div>
                    </div>
                    <div class="factor-chevron">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </div>
                </div>
                <!-- Real horizontal SHAP bar chart -->
                <div style="width: 100%; padding-left: calc(36px + 1rem); box-sizing: border-box;">
                    <div style="background: #f1f5f9; height: 6px; border-radius: 3px; overflow: hidden; width: 100%; position: relative;">
                        <div style="width: ${relativeWidth}%; height: 100%; border-radius: 3px; background-color: ${isIncrease ? 'var(--high-color)' : 'var(--low-color)'}; transition: width 0.8s ease-out;"></div>
                    </div>
                </div>
                <div class="factor-expanded-details hidden" style="margin-top: 0.25rem; margin-left: calc(36px + 1rem);">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    <span style="margin-left: 0.25rem;"><strong>Clinical Value Recorded:</strong> ${rawValue}</span>
                </div>
            `;

            // Expansion click handler
            factorRow.addEventListener("click", (e) => {
                if (window.getSelection().toString()) return;
                
                const details = factorRow.querySelector(".factor-expanded-details");
                const chevron = factorRow.querySelector(".factor-chevron");
                const isHidden = details.classList.contains("hidden");
                
                if (isHidden) {
                    details.classList.remove("hidden");
                    chevron.style.transform = "rotate(180deg)";
                } else {
                    details.classList.add("hidden");
                    chevron.style.transform = "rotate(0deg)";
                }
            });

            detailFactorsList.appendChild(factorRow);
        });

        // Render follow-up status button group selection state
        renderFollowUpStatus(data.follow_up_status || "Pending", data.scheduled_date, data.patient_id);
    }

    function renderFollowUpStatus(currentStatus, currentScheduledDate, patientId) {
        if (!followUpStatusButtons) return;
        
        selectedFollowUpStatus = currentStatus || "Pending";

        if (statusSaveFeedback) {
            statusSaveFeedback.style.display = "none";
            statusSaveFeedback.textContent = "";
        }

        // Check current user authorization
        const currentUser = JSON.parse(sessionStorage.getItem("user") || "{}");
        const patientObj = allPatientsCached.find(p => p.patient_id === patientId);

        let isAuthorized = true;
        if (currentUser.role === "doctor") {
            if (patientObj && patientObj.assigned_doctor_id !== currentUser.user_id) {
                isAuthorized = false;
            }
        }

        if (!isAuthorized) {
            if (statusUnauthorizedMessage) statusUnauthorizedMessage.classList.remove("hidden");
            if (btnSaveFollowUpStatus) btnSaveFollowUpStatus.disabled = true;
        } else {
            if (statusUnauthorizedMessage) statusUnauthorizedMessage.classList.add("hidden");
            if (btnSaveFollowUpStatus) btnSaveFollowUpStatus.disabled = false;
        }

        const buttons = followUpStatusButtons.querySelectorAll(".btn-status-toggle");
        buttons.forEach(btn => {
            btn.disabled = !isAuthorized;
            if (btn.dataset.status === selectedFollowUpStatus) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        if (scheduledDateInput) {
            scheduledDateInput.disabled = !isAuthorized;
            scheduledDateInput.value = currentScheduledDate || "";
        }

        if (selectedFollowUpStatus === "Scheduled") {
            if (scheduleDateContainer) scheduleDateContainer.classList.remove("hidden");
            if (currentScheduledDate && scheduledDateDisplay) {
                scheduledDateDisplay.textContent = `📅 Appointment: ${formatScheduledDate(currentScheduledDate)}`;
                scheduledDateDisplay.style.display = "block";
            } else if (scheduledDateDisplay) {
                scheduledDateDisplay.style.display = "none";
            }
        } else if (selectedFollowUpStatus === "Completed" && currentScheduledDate) {
            if (scheduleDateContainer) scheduleDateContainer.classList.remove("hidden");
            if (scheduledDateDisplay) {
                scheduledDateDisplay.textContent = `📅 Scheduled Appointment: ${formatScheduledDate(currentScheduledDate)}`;
                scheduledDateDisplay.style.display = "block";
            }
        } else {
            if (scheduleDateContainer) scheduleDateContainer.classList.add("hidden");
            if (scheduledDateDisplay) scheduledDateDisplay.style.display = "none";
        }
    }

    // Follow-up status button local click handlers
    if (followUpStatusButtons) {
        followUpStatusButtons.addEventListener("click", (e) => {
            const btn = e.target.closest(".btn-status-toggle");
            if (!btn || btn.disabled) return;

            selectedFollowUpStatus = btn.dataset.status;

            followUpStatusButtons.querySelectorAll(".btn-status-toggle").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            if (selectedFollowUpStatus === "Scheduled") {
                if (scheduleDateContainer) scheduleDateContainer.classList.remove("hidden");
            } else if (selectedFollowUpStatus === "Pending") {
                if (scheduleDateContainer) scheduleDateContainer.classList.add("hidden");
                if (scheduledDateDisplay) scheduledDateDisplay.style.display = "none";
            } else if (selectedFollowUpStatus === "Completed") {
                // For completed, keep date container if a date is present, otherwise hide
                if (!scheduledDateInput.value) {
                    if (scheduleDateContainer) scheduleDateContainer.classList.add("hidden");
                    if (scheduledDateDisplay) scheduledDateDisplay.style.display = "none";
                }
            }
        });
    }

    if (btnSaveFollowUpStatus) {
        btnSaveFollowUpStatus.addEventListener("click", async () => {
            if (!activePatientId) return;

            if (statusSaveFeedback) {
                statusSaveFeedback.style.display = "none";
                statusSaveFeedback.textContent = "";
            }

            let schedDate = null;
            if (selectedFollowUpStatus === "Scheduled") {
                schedDate = scheduledDateInput.value ? scheduledDateInput.value.trim() : null;
                if (!schedDate) {
                    if (statusSaveFeedback) {
                        statusSaveFeedback.style.color = "#b91c1c";
                        statusSaveFeedback.textContent = "Please select a date and time for the follow-up appointment.";
                        statusSaveFeedback.style.display = "block";
                    }
                    return;
                }
            } else if (selectedFollowUpStatus === "Completed") {
                schedDate = scheduledDateInput.value ? scheduledDateInput.value.trim() : null;
            }

            try {
                btnSaveFollowUpStatus.disabled = true;
                btnSaveFollowUpStatus.textContent = "Saving...";

                const token = sessionStorage.getItem("token");
                const res = await fetch(`/predict/${activePatientId}/follow-up`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + token
                    },
                    body: JSON.stringify({ status: selectedFollowUpStatus, scheduled_date: schedDate })
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to update follow-up status.");
                }

                const result = await res.json();

                if (statusSaveFeedback) {
                    statusSaveFeedback.style.color = "#047857";
                    statusSaveFeedback.textContent = "Follow-up status saved successfully!";
                    statusSaveFeedback.style.display = "block";
                }

                if (result.scheduled_date && scheduledDateDisplay) {
                    scheduledDateDisplay.textContent = `📅 Appointment: ${formatScheduledDate(result.scheduled_date)}`;
                    scheduledDateDisplay.style.display = "block";
                } else if (!result.scheduled_date && scheduledDateDisplay) {
                    scheduledDateDisplay.style.display = "none";
                }

                fetchPatients();
                fetchDashboardStats();
            } catch (err) {
                if (statusSaveFeedback) {
                    statusSaveFeedback.style.color = "#b91c1c";
                    statusSaveFeedback.textContent = `Error: ${err.message}`;
                    statusSaveFeedback.style.display = "block";
                }
            } finally {
                btnSaveFollowUpStatus.disabled = false;
                btnSaveFollowUpStatus.textContent = "Save Status";
            }
        });
    }

    // SVG Circular Ring Offset Calculation & Counter Animation
    function animateGauge(targetPercent) {
        // Semi-circle length: 283
        const circumference = 283;
        const offset = circumference - (circumference * targetPercent) / 100;
        
        progressRingFill.style.strokeDashoffset = offset;

        // Percentage label animation
        let current = 0;
        const duration = 600;
        const interval = 12;
        const step = (targetPercent / (duration / interval));
        
        const counter = setInterval(() => {
            current += step;
            if (current >= targetPercent) {
                current = targetPercent;
                clearInterval(counter);
            }
            detailRiskPercent.textContent = `${Math.round(current)}%`;
        }, interval);
    }

    // 5. SPA Navigation Helpers
    function showOverview() {
        detailView.classList.add("hidden");
        newPatientView.classList.add("hidden");
        requestsView.classList.add("hidden");
        profileView.classList.add("hidden");
        doctorsView.classList.add("hidden");
        adminsView.classList.add("hidden");
        overviewView.classList.remove("hidden");
        patientSearch.value = "";
        
        // Update menu highlight
        sidebarOverview.classList.add("active");
        sidebarPatients.classList.remove("active");
        menuRequests.classList.remove("active");
        menuProfile.classList.remove("active");
        menuDoctors.classList.remove("active");
        menuAdmins.classList.remove("active");
        
        // Show all table rows
        const rows = patientTableBody.querySelectorAll("tr");
        rows.forEach(r => r.classList.remove("hidden"));
        updateShowingCount();
    }

    function showNewPatientForm() {
        detailView.classList.add("hidden");
        overviewView.classList.add("hidden");
        requestsView.classList.add("hidden");
        profileView.classList.add("hidden");
        doctorsView.classList.add("hidden");
        adminsView.classList.add("hidden");
        newPatientView.classList.remove("hidden");
        formErrorBanner.style.display = "none";
        formErrorBanner.textContent = "";
        newPatientForm.reset();
        
        // Clear menu active status
        sidebarOverview.classList.remove("active");
        sidebarPatients.classList.remove("active");
        menuRequests.classList.remove("active");
        menuProfile.classList.remove("active");
        menuDoctors.classList.remove("active");
        menuAdmins.classList.remove("active");
    }

    function showRequestsView() {
        detailView.classList.add("hidden");
        overviewView.classList.add("hidden");
        newPatientView.classList.add("hidden");
        profileView.classList.add("hidden");
        doctorsView.classList.add("hidden");
        adminsView.classList.add("hidden");
        requestsView.classList.remove("hidden");
        
        sidebarOverview.classList.remove("active");
        sidebarPatients.classList.remove("active");
        menuRequests.classList.add("active");
        menuProfile.classList.remove("active");
        menuDoctors.classList.remove("active");
        menuAdmins.classList.remove("active");
        
        fetchPendingRequests();
    }

    function showProfileView() {
        detailView.classList.add("hidden");
        overviewView.classList.add("hidden");
        newPatientView.classList.add("hidden");
        requestsView.classList.add("hidden");
        doctorsView.classList.add("hidden");
        adminsView.classList.add("hidden");
        profileView.classList.remove("hidden");

        sidebarOverview.classList.remove("active");
        sidebarPatients.classList.remove("active");
        menuRequests.classList.remove("active");
        menuProfile.classList.add("active");
        menuDoctors.classList.remove("active");
        menuAdmins.classList.remove("active");

        fetchUserProfile();
    }

    function showDoctorsView() {
        detailView.classList.add("hidden");
        overviewView.classList.add("hidden");
        newPatientView.classList.add("hidden");
        requestsView.classList.add("hidden");
        profileView.classList.add("hidden");
        adminsView.classList.add("hidden");
        doctorsView.classList.remove("hidden");

        sidebarOverview.classList.remove("active");
        sidebarPatients.classList.remove("active");
        menuRequests.classList.remove("active");
        menuProfile.classList.remove("active");
        menuDoctors.classList.add("active");
        menuAdmins.classList.remove("active");

        fetchDoctorsList();
    }

    function showAdminsView() {
        detailView.classList.add("hidden");
        overviewView.classList.add("hidden");
        newPatientView.classList.add("hidden");
        requestsView.classList.add("hidden");
        profileView.classList.add("hidden");
        doctorsView.classList.add("hidden");
        adminsView.classList.remove("hidden");

        sidebarOverview.classList.remove("active");
        sidebarPatients.classList.remove("active");
        menuRequests.classList.remove("active");
        menuProfile.classList.remove("active");
        menuDoctors.classList.remove("active");
        menuAdmins.classList.add("active");

        fetchAdminsList();
    }

    // Bind Navigation Back
    backLink.addEventListener("click", (e) => {
        e.preventDefault();
        showOverview();
    });

    sidebarOverview.addEventListener("click", (e) => {
        e.preventDefault();
        showOverview();
    });

    sidebarPatients.addEventListener("click", (e) => {
        e.preventDefault();
        alert("DiabCare AI Readmission Predictor prototype system.\nExpected Baseline Performance: AUC 0.65-0.69.");
    });

    menuRequests.addEventListener("click", (e) => {
        e.preventDefault();
        showRequestsView();
    });

    menuProfile.addEventListener("click", (e) => {
        e.preventDefault();
        showProfileView();
    });

    menuDoctors.addEventListener("click", (e) => {
        e.preventDefault();
        showDoctorsView();
    });

    menuAdmins.addEventListener("click", (e) => {
        e.preventDefault();
        showAdminsView();
    });

    btnNewScreening.addEventListener("click", (e) => {
        e.preventDefault();
        showNewPatientForm();
    });

    btnNewPatientBack.addEventListener("click", (e) => {
        e.preventDefault();
        showOverview();
    });

    formCancelBtn.addEventListener("click", (e) => {
        e.preventDefault();
        showOverview();
    });

    // Form submission and client-side validation
    newPatientForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        formErrorBanner.style.display = "none";
        formErrorBanner.textContent = "";

        const formData = new FormData(newPatientForm);
        const errors = [];

        // Validate Name
        const name = formData.get("name").trim();
        if (!name) errors.push("Patient name is required.");

        // Validate diag codes
        const diag_1 = formData.get("diag_1").trim();
        const diag_2 = formData.get("diag_2").trim();
        const diag_3 = formData.get("diag_3").trim();
        if (!diag_1) errors.push("Primary diagnosis code is required.");
        if (!diag_2) errors.push("Secondary diagnosis code is required.");
        if (!diag_3) errors.push("Additional diagnosis code is required.");

        // Validate numeric inputs
        const time_in_hospital = parseInt(formData.get("time_in_hospital"), 10);
        if (isNaN(time_in_hospital) || time_in_hospital < 1 || time_in_hospital > 14) {
            errors.push("Length of hospital stay must be between 1 and 14 days.");
        }

        const num_lab_procedures = parseInt(formData.get("num_lab_procedures"), 10);
        if (isNaN(num_lab_procedures) || num_lab_procedures < 1 || num_lab_procedures > 150) {
            errors.push("Number of lab procedures must be between 1 and 150.");
        }

        const num_procedures = parseInt(formData.get("num_procedures"), 10);
        if (isNaN(num_procedures) || num_procedures < 0 || num_procedures > 10) {
            errors.push("Number of procedures must be between 0 and 10.");
        }

        const num_medications = parseInt(formData.get("num_medications"), 10);
        if (isNaN(num_medications) || num_medications < 1 || num_medications > 100) {
            errors.push("Number of medications must be between 1 and 100.");
        }

        const number_diagnoses = parseInt(formData.get("number_diagnoses"), 10);
        if (isNaN(number_diagnoses) || number_diagnoses < 1 || number_diagnoses > 16) {
            errors.push("Number of diagnoses must be between 1 and 16.");
        }

        const number_outpatient = parseInt(formData.get("number_outpatient"), 10);
        if (isNaN(number_outpatient) || number_outpatient < 0) {
            errors.push("Prior outpatient visits must be a non-negative number.");
        }

        const number_emergency = parseInt(formData.get("number_emergency"), 10);
        if (isNaN(number_emergency) || number_emergency < 0) {
            errors.push("Prior emergency visits must be a non-negative number.");
        }

        const number_inpatient = parseInt(formData.get("number_inpatient"), 10);
        if (isNaN(number_inpatient) || number_inpatient < 0) {
            errors.push("Prior inpatient visits must be a non-negative number.");
        }

        if (errors.length > 0) {
            formErrorBanner.innerHTML = errors.join("<br>");
            formErrorBanner.style.display = "block";
            newPatientView.scrollTo({ top: 0, behavior: "smooth" });
            return;
        }

        // Build the complete 44-feature request payload (defaulting remaining meds to "No")
        const payload = {
            "name": name,
            "race": formData.get("race"),
            "gender": formData.get("gender"),
            "age": formData.get("age"),
            "admission_type_id": parseInt(formData.get("admission_type_id"), 10),
            "discharge_disposition_id": parseInt(formData.get("discharge_disposition_id"), 10),
            "admission_source_id": parseInt(formData.get("admission_source_id"), 10),
            "time_in_hospital": time_in_hospital,
            "num_lab_procedures": num_lab_procedures,
            "num_procedures": num_procedures,
            "num_medications": num_medications,
            "number_outpatient": number_outpatient,
            "number_emergency": number_emergency,
            "number_inpatient": number_inpatient,
            "diag_1": diag_1,
            "diag_2": diag_2,
            "diag_3": diag_3,
            "number_diagnoses": number_diagnoses,
            "max_glu_serum": formData.get("max_glu_serum"),
            "A1Cresult": formData.get("A1Cresult"),
            "metformin": formData.get("metformin"),
            "repaglinide": "No",
            "nateglinide": "No",
            "chlorpropamide": "No",
            "glimepiride": "No",
            "acetohexamide": "No",
            "glipizide": "No",
            "glyburide": "No",
            "tolbutamide": "No",
            "pioglitazone": "No",
            "rosiglitazone": "No",
            "acarbose": "No",
            "miglitol": "No",
            "troglitazone": "No",
            "tolazamide": "No",
            "examide": "No",
            "citoglipton": "No",
            "insulin": formData.get("insulin"),
            "glyburide-metformin": "No",
            "glipizide-metformin": "No",
            "glimepiride-pioglitazone": "No",
            "metformin-rosiglitazone": "No",
            "metformin-pioglitazone": "No",
            "change": formData.get("change"),
            "diabetesMed": formData.get("diabetesMed")
        };

        // Transition to detail view with loading state
        newPatientView.classList.add("hidden");
        detailView.classList.remove("hidden");
        
        const uiId = `P-NEW`;
        const ageGroup = formData.get("age").replace("[", "").replace(")", "").trim();
        const gender = formData.get("gender");
        const lastEncounter = "Just Screened";

        detailPatientId.textContent = uiId;
        detailAgeGroup.textContent = ageGroup;
        detailGender.textContent = gender;
        detailLastEncounter.textContent = lastEncounter;
        
        detailLoadingState.classList.remove("hidden");
        detailResultsContainer.classList.add("hidden");

        try {
            const token = sessionStorage.getItem("token");
            const response = await fetch("/predict_new", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token
                },
                body: JSON.stringify(payload)
            });

            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }

            if (!response.ok) {
                const errData = await response.json();
                const errMsg = Array.isArray(errData.detail) ? errData.detail.join("<br>") : (errData.detail || "Server validation failed.");
                throw new Error(errMsg);
            }

            const predictionResult = await response.json();
            activePatientId = predictionResult.patient_id;

            // Cache raw features so the SHAP expander has access to them
            activePatientFeatures = payload;

            // Refresh the patient list so the new patient is immediately selectable
            fetchPatients();

            // Brief delay for transition smooth experience
            setTimeout(() => {
                detailLoadingState.classList.add("hidden");
                detailResultsContainer.classList.remove("hidden");
                const newUiId = `P-${predictionResult.patient_id}`;
                detailPatientId.textContent = newUiId;
                renderDetailsView(predictionResult);
            }, 300);

        } catch (error) {
            console.error("New Patient prediction failed:", error);
            detailView.classList.add("hidden");
            newPatientView.classList.remove("hidden");
            formErrorBanner.innerHTML = `Error running prediction: ${error.message}`;
            formErrorBanner.style.display = "block";
            newPatientView.scrollTo({ top: 0, behavior: "smooth" });
        }
    });

    function getInitials(name) {
        if (!name) return "PT";
        const parts = name.trim().split(" ");
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return parts[0].slice(0, 2).toUpperCase();
    }

    function checkSession() {
        const token = sessionStorage.getItem("token");
        const user = JSON.parse(sessionStorage.getItem("user") || "null");
        
        if (!token || !user) {
            appLayout.classList.add("hidden");
            loginView.classList.remove("hidden");
            return;
        }
        
        loginView.classList.add("hidden");
        appLayout.classList.remove("hidden");
        
        // Update sidebar profile block
        userDisplayName.textContent = user.name;
        userDisplayRole.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
        userAvatarInitials.textContent = getInitials(user.name);
        
        // Gated Access Requests, Doctors Directory, and Manage Admins for Admins
        if (user.role === "admin") {
            menuRequests.classList.remove("hidden");
            menuDoctors.classList.remove("hidden");
            menuAdmins.classList.remove("hidden");
            if (patientFilterTabs) patientFilterTabs.classList.add("hidden");
            if (adminDoctorFilter) adminDoctorFilter.classList.remove("hidden");
            fetchDoctorsList();
        } else {
            menuRequests.classList.add("hidden");
            menuDoctors.classList.add("hidden");
            menuAdmins.classList.add("hidden");
            if (patientFilterTabs) patientFilterTabs.classList.remove("hidden");
            if (adminDoctorFilter) adminDoctorFilter.classList.add("hidden");
        }
        
        // Trigger patient list load
        fetchPatients();
    }

    function handleLogout(warningMessage) {
        sessionStorage.removeItem("token");
        sessionStorage.removeItem("user");
        
        loginEmail.value = "";
        loginPassword.value = "";
        
        if (warningMessage) {
            loginErrorBanner.textContent = warningMessage;
            loginErrorBanner.style.display = "block";
        } else {
            loginErrorBanner.textContent = "";
            loginErrorBanner.style.display = "none";
        }
        
        checkSession();
    }

    // Toggle Login / Register Views
    linkShowRegister.addEventListener("click", (e) => {
        e.preventDefault();
        loginSection.classList.add("hidden");
        registerSection.classList.remove("hidden");
        
        registerName.value = "";
        registerEmail.value = "";
        registerPassword.value = "";
        registerErrorBanner.textContent = "";
        registerErrorBanner.style.display = "none";
        registerSuccessBanner.textContent = "";
        registerSuccessBanner.style.display = "none";
    });

    linkShowLogin.addEventListener("click", (e) => {
        e.preventDefault();
        registerSection.classList.add("hidden");
        loginSection.classList.remove("hidden");
        
        loginEmail.value = "";
        loginPassword.value = "";
        loginErrorBanner.textContent = "";
        loginErrorBanner.style.display = "none";
    });

    // Bind Registration Form Submission
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        registerErrorBanner.textContent = "";
        registerErrorBanner.style.display = "none";
        registerSuccessBanner.textContent = "";
        registerSuccessBanner.style.display = "none";

        const name = registerName.value.trim();
        const email = registerEmail.value.trim();
        const password = registerPassword.value;

        try {
            const response = await fetch("/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password })
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || "Registration failed.");
            }

            const result = await response.json();
            registerSuccessBanner.textContent = result.message;
            registerSuccessBanner.style.display = "block";
            
            // Clear inputs
            registerName.value = "";
            registerEmail.value = "";
            registerPassword.value = "";
            
            // Redirect after delay
            setTimeout(() => {
                registerSection.classList.add("hidden");
                loginSection.classList.remove("hidden");
                loginEmail.value = email;
                loginPassword.value = "";
                loginErrorBanner.textContent = "Account pending approval. Please wait for an administrator.";
                loginErrorBanner.style.display = "block";
            }, 3000);

        } catch (error) {
            registerErrorBanner.textContent = error.message;
            registerErrorBanner.style.display = "block";
        }
    });

    // Bind Logout
    btnLogout.addEventListener("click", (e) => {
        e.preventDefault();
        handleLogout();
    });

    // Bind Login Form Submission
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        loginErrorBanner.textContent = "";
        loginErrorBanner.style.display = "none";

        const email = loginEmail.value.trim();
        const password = loginPassword.value;

        try {
            const response = await fetch("/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || "Authentication failed. Check credentials.");
            }

            const result = await response.json();
            sessionStorage.setItem("token", result.access_token);
            sessionStorage.setItem("user", JSON.stringify(result.user));

            checkSession();
        } catch (error) {
            loginErrorBanner.textContent = error.message;
            loginErrorBanner.style.display = "block";
        }
    });

    // Fetch and render pending doctor access requests (Admin only)
    async function fetchPendingRequests() {
        try {
            const token = sessionStorage.getItem("token");
            if (!token) {
                handleLogout();
                return;
            }
            const response = await fetch("/admin/requests", {
                headers: { "Authorization": "Bearer " + token }
            });
            
            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const requests = await response.json();
            
            if (requests.length === 0) {
                requestsEmptyState.classList.remove("hidden");
                requestsTableContainer.classList.add("hidden");
            } else {
                requestsEmptyState.classList.add("hidden");
                requestsTableContainer.classList.remove("hidden");
                requestsTableBody.innerHTML = "";
                
                requests.forEach(req => {
                    const row = document.createElement("tr");
                    
                    // Format created_at date
                    let dateStr = "Pending";
                    if (req.created_at) {
                        try {
                            const d = new Date(req.created_at);
                            dateStr = d.toLocaleString();
                        } catch (e) {}
                    }
                    
                    row.innerHTML = `
                        <td style="font-weight: 700;">${req.name}</td>
                        <td>${req.email}</td>
                        <td>${dateStr}</td>
                        <td style="text-align: center;">
                            <button class="btn-approve" data-id="${req.user_id}">Approve</button>
                            <button class="btn-reject" data-id="${req.user_id}">Reject</button>
                        </td>
                    `;
                    
                    row.querySelector(".btn-approve").addEventListener("click", async () => {
                        await handleRequestAction(req.user_id, "approve");
                    });
                    
                    row.querySelector(".btn-reject").addEventListener("click", async () => {
                        await handleRequestAction(req.user_id, "reject");
                    });
                    
                    requestsTableBody.appendChild(row);
                });
            }
        } catch (error) {
            console.error("Failed to load pending requests:", error);
        }
    }

    async function handleRequestAction(userId, action) {
        try {
            const token = sessionStorage.getItem("token");
            const response = await fetch("/admin/requests/action", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token
                },
                body: JSON.stringify({ user_id: userId, action: action })
            });
            
            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                return;
            }
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || "Action failed.");
            }
            
            // Refresh list
            fetchPendingRequests();
        } catch (error) {
            alert(`Error processing request: ${error.message}`);
        }
    }

    // Fetch and render dashboard stats metrics cards (Doctor/Admin)
    async function fetchDashboardStats() {
        try {
            const token = sessionStorage.getItem("token");
            const user = JSON.parse(sessionStorage.getItem("user") || "null");
            if (!token || !user) return;
            
            const response = await fetch("/dashboard/stats", {
                headers: { "Authorization": "Bearer " + token }
            });
            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }
            if (!response.ok) {
                throw new Error("Failed to fetch dashboard stats.");
            }
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
                // Bind click event for "Review" button in admin dashboard
                const btnGoRequests = document.getElementById("btn-go-to-requests");
                if (btnGoRequests) {
                    btnGoRequests.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        showRequestsView();
                    });
                }
            }
        } catch (error) {
            console.error("Error rendering dashboard stats:", error);
        }
    }


    // ---------------------------------------------------------------------------
    // User Profile Feature (Doctor & Admin Profile Management)
    // ---------------------------------------------------------------------------
    async function fetchUserProfile() {
        try {
            const token = sessionStorage.getItem("token");
            if (!token) return;
            const response = await fetch("/user/profile", {
                headers: { "Authorization": "Bearer " + token }
            });
            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }
            if (!response.ok) throw new Error("Failed to fetch profile.");
            const data = await response.json();
            profileName.value = data.name || "";
            profileEmail.value = data.email || "";
            profileRole.value = data.role || "";
            profileEducation.value = data.education || "";
            profileReferenceId.value = data.reference_id || "";
            profileErrorBanner.style.display = "none";
            profileSuccessBanner.style.display = "none";
        } catch (err) {
            console.error("Error loading user profile:", err);
        }
    }

    if (profileForm) {
        profileForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            profileErrorBanner.style.display = "none";
            profileSuccessBanner.style.display = "none";

            const name = profileName.value.trim();
            const education = profileEducation.value.trim();
            const reference_id = profileReferenceId.value.trim();

            if (!name) {
                profileErrorBanner.textContent = "Full Name is required.";
                profileErrorBanner.style.display = "block";
                return;
            }

            try {
                const token = sessionStorage.getItem("token");
                const response = await fetch("/user/profile", {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + token
                    },
                    body: JSON.stringify({ name, education, reference_id })
                });

                if (response.status === 401) {
                    handleLogout("Session expired. Please log in again.");
                    throw new Error("Unauthorized");
                }

                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to update profile.");
                }

                const updatedUser = await response.json();
                
                // Update local session storage
                const sessionUser = JSON.parse(sessionStorage.getItem("user") || "{}");
                sessionUser.name = updatedUser.name;
                sessionStorage.setItem("user", JSON.stringify(sessionUser));

                userDisplayName.textContent = updatedUser.name;
                userAvatarInitials.textContent = getInitials(updatedUser.name);

                profileSuccessBanner.textContent = "Profile updated and saved successfully!";
                profileSuccessBanner.style.display = "block";
            } catch (err) {
                profileErrorBanner.textContent = err.message;
                profileErrorBanner.style.display = "block";
            }
        });
    }

    // ---------------------------------------------------------------------------
    // Doctors Directory & Stats Feature (Admin Only)
    // ---------------------------------------------------------------------------
    let cachedDoctorsList = [];

    async function fetchDoctorsList() {
        try {
            const token = sessionStorage.getItem("token");
            if (!token) return;
            const response = await fetch("/admin/doctors", {
                headers: { "Authorization": "Bearer " + token }
            });
            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }
            if (!response.ok) throw new Error("Failed to load doctor records.");
            cachedDoctorsList = await response.json();
            
            populateAdminDoctorFilterOptions();
            renderDoctorsStatsAndTable();
        } catch (err) {
            console.error("Error fetching doctors list:", err);
        }
    }

    function populateAdminDoctorFilterOptions() {
        if (!adminDoctorFilter) return;
        const currentVal = adminDoctorFilter.value;
        adminDoctorFilter.innerHTML = `<option value="all">Filter: All Doctors</option>`;
        cachedDoctorsList.forEach(doc => {
            if (doc.status === "approved") {
                const opt = document.createElement("option");
                opt.value = doc.user_id;
                opt.textContent = `Doctor: ${doc.name}`;
                adminDoctorFilter.appendChild(opt);
            }
        });
        adminDoctorFilter.value = currentVal || "all";
    }

    // Filter controls event triggers
    if (tabFilterAll && tabFilterMy) {
        tabFilterAll.addEventListener("click", () => {
            activePatientFilter = "all";
            tabFilterAll.classList.add("active");
            tabFilterMy.classList.remove("active");
            renderPatientTable();
        });

        tabFilterMy.addEventListener("click", () => {
            activePatientFilter = "my";
            tabFilterMy.classList.add("active");
            tabFilterAll.classList.remove("active");
            renderPatientTable();
        });
    }

    if (adminDoctorFilter) {
        adminDoctorFilter.addEventListener("change", (e) => {
            activePatientFilter = e.target.value;
            renderPatientTable();
        });
    }

    function renderDoctorsStatsAndTable() {
        const doctors = cachedDoctorsList;
        const total = doctors.length;
        const approved = doctors.filter(d => d.status === 'approved').length;
        const pending = doctors.filter(d => d.status === 'pending').length;
        const rejected = doctors.filter(d => d.status === 'rejected').length;

        doctorsStatsContainer.innerHTML = `
            <div class="stat-card">
                <span class="stat-card-title">Total Registered Doctors</span>
                <span class="stat-card-value">${total}</span>
            </div>
            <div class="stat-card">
                <span class="stat-card-title">Approved Doctors</span>
                <span class="stat-card-value" style="color: var(--low-color);">${approved}</span>
            </div>
            <div class="stat-card">
                <span class="stat-card-title">Pending Approvals</span>
                <span class="stat-card-value" style="color: var(--mod-color);">${pending}</span>
            </div>
            <div class="stat-card">
                <span class="stat-card-title">Rejected Applications</span>
                <span class="stat-card-value" style="color: var(--high-color);">${rejected}</span>
            </div>
        `;

        renderDoctorsTable(doctors);
    }

    function renderDoctorsTable(doctors) {
        doctorsTableBody.innerHTML = "";
        if (doctors.length === 0) {
            doctorsTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No doctor records found.</td></tr>`;
            return;
        }

        doctors.forEach(doc => {
            const row = document.createElement("tr");
            let badgeClass = "badge-pending";
            if (doc.status === "approved") badgeClass = "badge-completed";
            if (doc.status === "rejected") badgeClass = "badge-scheduled";

            let joinedDate = "Unknown";
            if (doc.created_at) {
                try { joinedDate = new Date(doc.created_at).toLocaleDateString(); } catch (e) {}
            }

            row.innerHTML = `
                <td style="font-weight: 700;">${doc.name}</td>
                <td>${doc.email}</td>
                <td>${doc.education || '<span style="color:var(--text-muted); font-style:italic;">Not specified</span>'}</td>
                <td><code>${doc.reference_id || 'N/A'}</code></td>
                <td><span class="status-badge ${badgeClass}" style="text-transform: capitalize;">${doc.status}</span></td>
                <td>${joinedDate}</td>
            `;
            doctorsTableBody.appendChild(row);
        });
    }

    if (doctorSearch) {
        doctorSearch.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            const filtered = cachedDoctorsList.filter(doc => {
                const name = (doc.name || "").toLowerCase();
                const email = (doc.email || "").toLowerCase();
                const edu = (doc.education || "").toLowerCase();
                const ref = (doc.reference_id || "").toLowerCase();
                return name.includes(query) || email.includes(query) || edu.includes(query) || ref.includes(query);
            });
            renderDoctorsTable(filtered);
        });
    }

    // ---------------------------------------------------------------------------
    // Admin Management Feature (Admin Only)
    // ---------------------------------------------------------------------------
    async function fetchAdminsList() {
        try {
            const token = sessionStorage.getItem("token");
            if (!token) return;
            const response = await fetch("/admin/admins", {
                headers: { "Authorization": "Bearer " + token }
            });
            if (response.status === 401) {
                handleLogout("Session expired. Please log in again.");
                throw new Error("Unauthorized");
            }
            if (!response.ok) throw new Error("Failed to load admin list.");
            const admins = await response.json();
            
            adminsCountLabel.textContent = `Active System Administrators (${admins.length})`;
            adminsTableBody.innerHTML = "";

            admins.forEach(adm => {
                const row = document.createElement("tr");
                let createdDate = "System Seed";
                if (adm.created_at) {
                    try { createdDate = new Date(adm.created_at).toLocaleDateString(); } catch (e) {}
                }

                row.innerHTML = `
                    <td style="font-weight: 700;">${adm.name}</td>
                    <td>${adm.email}</td>
                    <td><code>${adm.user_id}</code></td>
                    <td>${createdDate}</td>
                `;
                adminsTableBody.appendChild(row);
            });
        } catch (err) {
            console.error("Error fetching admins list:", err);
        }
    }

    if (createAdminForm) {
        createAdminForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            createAdminErrorBanner.style.display = "none";
            createAdminSuccessBanner.style.display = "none";

            const name = newAdminName.value.trim();
            const email = newAdminEmail.value.trim();
            const password = newAdminPassword.value;

            if (!email || !password) {
                createAdminErrorBanner.textContent = "Email and Password are required.";
                createAdminErrorBanner.style.display = "block";
                return;
            }

            try {
                const token = sessionStorage.getItem("token");
                const response = await fetch("/admin/create-admin", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + token
                    },
                    body: JSON.stringify({ name, email, password })
                });

                if (response.status === 401) {
                    handleLogout("Session expired. Please log in again.");
                    throw new Error("Unauthorized");
                }

                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to create administrator.");
                }

                const result = await response.json();
                createAdminSuccessBanner.textContent = result.message;
                createAdminSuccessBanner.style.display = "block";

                newAdminName.value = "";
                newAdminEmail.value = "";
                newAdminPassword.value = "";

                fetchAdminsList();
                fetchDashboardStats();
            } catch (err) {
                createAdminErrorBanner.textContent = err.message;
                createAdminErrorBanner.style.display = "block";
            }
        });
    }

    // Run Initial Data/Authentication Check
    checkSession();
});
