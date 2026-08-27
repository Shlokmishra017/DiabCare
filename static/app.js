/**
 * DiabCare AI - Redesigned Frontend Controller
 * ===============================================
 * Drives the hospital light-themed dashboard, patient list search,
 * SPA transitions, gauge animations, and mockup assets.
 */

document.addEventListener("DOMContentLoaded", () => {
    
    // Mapped Clinical Names for seeded patient IDs to maximize visual fidelity
    const PATIENT_NAMES = {
        "2278392": "Emma Robinson",
        "149190": "Chloe Jenkins",
        "64410": "Aaliyah Jackson",
        "421194": "Eleanor Davis",
        "2549268": "Arthur Miller",
        "2552952": "Margaret Wilson"
    };

    // DOM Navigation Views
    const overviewView = document.getElementById("overview-view");
    const detailView = document.getElementById("detail-view");
    const newPatientView = document.getElementById("new-patient-view");
    const sidebarOverview = document.getElementById("menu-overview");
    const sidebarPatients = document.getElementById("menu-patients");
    const navPatients = document.getElementById("nav-patients");
    
    // New Screening Form Elements
    const btnNewScreening = document.querySelector(".btn-new-screening");
    const btnNewPatientBack = document.getElementById("new-patient-back");
    const formCancelBtn = document.getElementById("form-cancel-btn");
    const newPatientForm = document.getElementById("new-patient-form");
    const formErrorBanner = document.getElementById("form-error-banner");
    
    // Overview Screen Elements
    const patientSearch = document.getElementById("patient-search");
    const patientListLoading = document.getElementById("patient-list-loading");
    const patientList = document.getElementById("patient-list");

    // Detail Screen Elements
    const backLink = document.getElementById("back-link");
    const detailPatientTitle = document.getElementById("detail-patient-title");
    const detailLoadingState = document.getElementById("detail-loading-state");
    const detailResultsContainer = document.getElementById("detail-results-container");
    const detailRiskCardBg = document.getElementById("detail-risk-card-bg");
    const progressRingFill = document.getElementById("progress-ring-fill");
    const detailRiskPercent = document.getElementById("detail-risk-percent");
    const detailRiskBadge = document.getElementById("detail-risk-badge");
    
    // Priority Banner Elements
    const priorityAlertBanner = document.getElementById("priority-alert-banner");
    const priorityBannerIcon = document.getElementById("priority-banner-icon");
    const priorityBannerTitle = document.getElementById("priority-banner-title");
    const priorityBannerDescription = document.getElementById("priority-banner-description");
    
    // Risk Factors List
    const detailFactorsList = document.getElementById("detail-factors-list");

    // Local Data Store
    let allPatientsCached = [];
    let activePatientFeatures = null;

    // Helper: Generate Initials
    function getInitials(name) {
        if (!name) return "PT";
        const parts = name.trim().split(" ");
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return parts[0].slice(0, 2).toUpperCase();
    }

    // Helper: Parse Patient Summary
    function parsePatientSummary(summary) {
        if (!summary) return {};
        const features = {};
        
        const parts = summary.split("|");
        
        // 1. Demographics (e.g. "Female, 10-20 yrs, Caucasian")
        const demoPart = parts[0] ? parts[0].trim() : "";
        const demoSubParts = demoPart.split(",");
        if (demoSubParts[0]) features["gender"] = demoSubParts[0].trim();
        if (demoSubParts[1]) features["age"] = demoSubParts[1].trim();
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
        
        // 7. Demographics
        if (labelLower.includes("race")) {
            if (activePatientFeatures["race"]) return activePatientFeatures["race"];
            const match = labelText.match(/race:\s*(.+)$/i);
            return match && match[1] ? match[1] : "Unknown";
        }
        if (labelLower.includes("gender") || labelLower.includes("patient")) {
            if (activePatientFeatures["gender"]) return activePatientFeatures["gender"];
            if (labelLower.includes("female")) return "Female";
            if (labelLower.includes("male")) return "Male";
        }
        if (labelLower.includes("aged") || labelLower.includes("age")) {
            if (activePatientFeatures["age"]) return activePatientFeatures["age"];
            const match = labelText.match(/aged\s*(.+)$/i);
            return match && match[1] ? match[1] : "Unknown";
        }
        
        return labelText;
    }

    // 1. Fetch available patients on load
    async function fetchPatients() {
        try {
            const response = await fetch("/patients");
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const patients = await response.json();
            allPatientsCached = patients;

            patientListLoading.classList.add("hidden");
            patientList.innerHTML = "";

            patients.forEach(patient => {
                const name = patient.name || PATIENT_NAMES[patient.patient_id] || `Patient ${patient.patient_id}`;
                const initials = getInitials(name);
                
                // Parse summary data (e.g. "Female, 10-20 yrs, Caucasian | Stay: 3d | Prior inpatient: 0")
                const parts = patient.summary.split("|");
                const demographics = parts[0] ? parts[0].trim() : "-";
                const stay = parts[1] ? parts[1].replace("Stay:", "").trim() : "-";
                const priorInpatient = parts[2] ? parts[2].replace("Prior inpatient:", "").trim() : "0";

                let riskBadgeHtml = "";
                if (patient.risk_percent !== null && patient.risk_percent !== undefined) {
                    let badgeClass = "risk-badge-low";
                    if (patient.risk_percent > 60) {
                        badgeClass = "risk-badge-high";
                    } else if (patient.risk_percent >= 30) {
                        badgeClass = "risk-badge-med";
                    }
                    riskBadgeHtml = `<div class="patient-risk-badge ${badgeClass}">${Math.round(patient.risk_percent)}% Risk</div>`;
                } else {
                    riskBadgeHtml = `<div class="patient-risk-badge risk-badge-none">No prediction</div>`;
                }

                const patientItem = document.createElement("div");
                patientItem.className = "patient-item";
                patientItem.dataset.id = patient.patient_id;
                patientItem.innerHTML = `
                    <div class="patient-avatar-circle">${initials}</div>
                    <div class="patient-info">
                        <span class="patient-name">${name}</span>
                        <span class="patient-sub-details">ID: P-${patient.patient_id} &bull; Demographics: ${demographics} &bull; Stay: ${stay} &bull; Prior Inpatient: ${priorInpatient}</span>
                    </div>
                    ${riskBadgeHtml}
                    <div class="patient-action-arrow">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                `;

                // Item Click Listener to load details
                patientItem.addEventListener("click", () => {
                    openPatientScreening(patient.patient_id, name);
                });

                patientList.appendChild(patientItem);
            });
        } catch (error) {
            console.error("Error loading patient listing:", error);
            patientListLoading.innerHTML = `<span style="color: var(--high-color);">Failed to load clinical profiles. Is server running?</span>`;
        }
    }

    // 2. Real-time patient search filter
    patientSearch.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const items = patientList.querySelectorAll(".patient-item");
        let visibleCount = 0;

        items.forEach(item => {
            const patientId = item.dataset.id;
            const name = PATIENT_NAMES[patientId] ? PATIENT_NAMES[patientId].toLowerCase() : "";
            const infoText = item.querySelector(".patient-sub-details").textContent.toLowerCase();

            if (patientId.includes(query) || name.includes(query) || infoText.includes(query)) {
                item.classList.remove("hidden");
                visibleCount++;
            } else {
                item.classList.add("hidden");
            }
        });

        let noResultsMsg = document.getElementById("patient-list-no-results");
        if (visibleCount === 0) {
            if (!noResultsMsg) {
                noResultsMsg = document.createElement("div");
                noResultsMsg.id = "patient-list-no-results";
                noResultsMsg.className = "list-no-results";
                noResultsMsg.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <span>No clinical profiles found matching "${e.target.value}"</span>
                `;
                patientList.parentNode.appendChild(noResultsMsg);
            } else {
                noResultsMsg.querySelector("span").textContent = `No clinical profiles found matching "${e.target.value}"`;
                noResultsMsg.classList.remove("hidden");
            }
        } else {
            if (noResultsMsg) {
                noResultsMsg.classList.add("hidden");
            }
        }
    });

    // 3. Load prediction and render Detail view (SPA)
    async function openPatientScreening(patientId, patientName) {
        // Toggle view
        overviewView.classList.add("hidden");
        detailView.classList.remove("hidden");
        
        // Update headers
        detailPatientTitle.textContent = `Patient ID: P-${patientId} (${patientName})`;
        
        // Show loading state
        detailLoadingState.classList.remove("hidden");
        detailResultsContainer.classList.add("hidden");

        // Parse summary for active patient
        const patientObj = allPatientsCached.find(p => p.patient_id === patientId);
        if (patientObj) {
            activePatientFeatures = parsePatientSummary(patientObj.summary);
        } else {
            activePatientFeatures = null;
        }

        try {
            const response = await fetch("/predict", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ patient_id: patientId })
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                const errMsg = errData.detail || `Predict API error! status: ${response.status}`;
                throw new Error(errMsg);
            }

            const data = await response.json();
            
            // Refresh patient listing so it shows the risk badge
            fetchPatients();
            
            // Add a brief timeout delay to allow loader to register
            setTimeout(() => {
                detailLoadingState.classList.add("hidden");
                detailResultsContainer.classList.remove("hidden");
                renderDetailsView(data);
            }, 300);

        } catch (error) {
            console.error("Prediction loader failed:", error);
            detailLoadingState.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="var(--high-color)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                <h3 style="margin-top: 1rem;">Diagnostics Error</h3>
                <p style="color: var(--high-color); margin-top: 0.5rem; font-weight: 500;">${error.message}</p>
                <button class="btn btn-secondary mt-4" id="error-back-btn">Return to Overview</button>
            `;
            document.getElementById("error-back-btn").addEventListener("click", showOverview);
        }
    }

    // 4. Render details elements
    function renderDetailsView(data) {
        const { risk_percent, risk_category, follow_up_priority, top_factors } = data;

        // --- Render circular ring gauge ---
        animateGauge(risk_percent);
        
        // Reset card class list
        detailRiskCardBg.className = "card detail-risk-card";
        
        if (risk_category === "Low") {
            detailRiskCardBg.classList.add("low-card");
            detailRiskBadge.textContent = "LOW RISK";
            detailRiskBadge.style.color = "var(--low-color)";
            progressRingFill.style.stroke = "var(--low-color)";
        } else if (risk_category === "Moderate") {
            detailRiskCardBg.classList.add("moderate-card");
            detailRiskBadge.textContent = "MODERATE RISK";
            detailRiskBadge.style.color = "var(--mod-color)";
            progressRingFill.style.stroke = "var(--mod-color)";
        } else {
            detailRiskCardBg.classList.add("high-card");
            detailRiskBadge.textContent = "HIGH RISK";
            detailRiskBadge.style.color = "var(--high-color)";
            progressRingFill.style.stroke = "var(--high-color)";
        }

        // --- Render priority banner alert ---
        priorityAlertBanner.className = "priority-banner-box";
        
        if (follow_up_priority === "Low") {
            priorityAlertBanner.classList.add("banner-low");
            priorityBannerTitle.textContent = "LOW PRIORITY";
            priorityBannerDescription.textContent = "Continue standard post-discharge protocol. Arrange routine outpatient clinic follow-up.";
            priorityBannerIcon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12" y1="8" y2="8"/></svg>`;
        } else if (follow_up_priority === "Medium") {
            priorityAlertBanner.classList.add("banner-medium");
            priorityBannerTitle.textContent = "MODERATE PRIORITY";
            priorityBannerDescription.textContent = "Schedule standard post-discharge follow-up within 7 days. Verify diabetes education compliance.";
            priorityBannerIcon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12" y1="8" y2="8"/></svg>`;
        } else {
            priorityAlertBanner.classList.add("banner-high");
            priorityBannerTitle.textContent = "HIGH PRIORITY";
            priorityBannerDescription.textContent = "Prioritize for post-discharge follow-up. Clinical review recommended within 48 hours. Assign transitional coordinator.";
            priorityBannerIcon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
        }

        // --- Render SHAP Top Risk Factors ---
        detailFactorsList.innerHTML = "";
        
        // Render interactive/clickable factors
        top_factors.forEach(item => {
            const isIncrease = item.direction.toLowerCase().includes("increase");
            const isDecrease = item.direction.toLowerCase().includes("decrease");
            
            let rowBgClass = "neutral-factor-bg";
            let iconClass = "neutral-icon";
            let indicatorClass = "neutral-text";
            let labelText = item.factor;
            let subText = "NO IMPACT";
            
            // Icon SVG shapes
            let svgIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>`;

            if (isIncrease) {
                rowBgClass = "high-factor-bg";
                iconClass = "up-icon";
                indicatorClass = "up-text";
                subText = "INCREASES RISK";
                svgIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>`;
            } else if (isDecrease) {
                rowBgClass = "low-factor-bg";
                iconClass = "down-icon";
                indicatorClass = "down-text";
                subText = "DECREASES RISK";
                svgIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="7" x2="17" y2="17"/><polyline points="17 7 17 17 7 17"/></svg>`;
            }

            const factorRow = document.createElement("div");
            factorRow.className = `factor-item-row ${rowBgClass} clickable-factor`;
            
            // Extract raw value using helper
            const rawValue = getRawValueForFactor(labelText);

            factorRow.innerHTML = `
                <div class="factor-main-info">
                    <div class="factor-left-content">
                        <div class="factor-direction-icon-circle ${iconClass}">
                            ${svgIcon}
                        </div>
                        <span class="factor-label-text">${labelText}</span>
                    </div>
                    <div class="factor-right-content">
                        <span class="factor-direction-indicator-text ${indicatorClass}">${subText}</span>
                        <span class="factor-expand-chevron">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                        </span>
                    </div>
                </div>
                <div class="factor-raw-details hidden">
                    <div class="factor-details-divider"></div>
                    <div class="factor-details-body">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>
                        <span><strong>Clinical Value Recorded:</strong> ${rawValue}</span>
                    </div>
                </div>
            `;

            factorRow.addEventListener("click", (e) => {
                // Prevent toggling if selecting text
                if (window.getSelection().toString()) return;
                
                const details = factorRow.querySelector(".factor-raw-details");
                const chevron = factorRow.querySelector(".factor-expand-chevron");
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
    }

    // SVG Circular Ring Offset Calculation & Counter Animation
    function animateGauge(targetPercent) {
        // SVG Circumference: 2 * Math.PI * 82 = 515.22
        const circumference = 515.22;
        const offset = circumference - (circumference * targetPercent) / 100;
        
        progressRingFill.style.strokeDashoffset = offset;

        // Number animation
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
        overviewView.classList.remove("hidden");
        patientSearch.value = "";
        
        // Remove active class from menu items and activate Overview
        document.querySelectorAll(".menu-item").forEach(el => el.classList.remove("active"));
        sidebarOverview.classList.add("active");
    }

    function showNewPatientForm() {
        detailView.classList.add("hidden");
        overviewView.classList.add("hidden");
        newPatientView.classList.remove("hidden");
        formErrorBanner.style.display = "none";
        formErrorBanner.textContent = "";
        newPatientForm.reset();
        
        // Remove active class from menu items and activate New Screening
        document.querySelectorAll(".menu-item").forEach(el => el.classList.remove("active"));
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
        showOverview();
    });

    navPatients.addEventListener("click", (e) => {
        e.preventDefault();
        showOverview();
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
        detailPatientTitle.textContent = "Patient ID: New Screening Profile";
        detailLoadingState.classList.remove("hidden");
        detailResultsContainer.classList.add("hidden");

        try {
            const response = await fetch("/predict_new", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json();
                const errMsg = Array.isArray(errData.detail) ? errData.detail.join("<br>") : (errData.detail || "Server validation failed.");
                throw new Error(errMsg);
            }

            const predictionResult = await response.json();

            // Cache raw features so the SHAP expander has access to them
            activePatientFeatures = payload;

            // Refresh the patient list so the new patient is immediately selectable
            fetchPatients();

            // Brief delay for transition smooth experience
            setTimeout(() => {
                detailLoadingState.classList.add("hidden");
                detailResultsContainer.classList.remove("hidden");
                detailPatientTitle.textContent = `Patient ID: P-${predictionResult.patient_id} (New Screening)`;
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

    // Run Initial Data Load
    fetchPatients();
});
