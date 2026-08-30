/**
 * DiabCare AI - Screening & Gauge Module
 */

export function animateGauge(targetPercent) {
    const progressRingFill = document.getElementById("progress-ring-fill");
    const detailRiskPercent = document.getElementById("detail-risk-percent");
    if (!progressRingFill || !detailRiskPercent) return;

    const circumference = 283;
    const offset = circumference - (circumference * targetPercent) / 100;
    progressRingFill.style.strokeDashoffset = offset;

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
