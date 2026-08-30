/**
 * DiabCare AI - API Module
 * API fetch wrapper with Authorization bearer header and automatic token refresh functionality.
 */

export async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};

    const token = sessionStorage.getItem("token");
    if (token && !options.headers["Authorization"]) {
        options.headers["Authorization"] = `Bearer ${token}`;
    }

    let response = await fetch(url, options);

    // If 401 Unauthorized, attempt refresh token flow before failing
    if (response.status === 401 && !url.includes("/auth/login") && !url.includes("/auth/refresh")) {
        const refreshToken = sessionStorage.getItem("refresh_token");
        if (refreshToken) {
            try {
                const refreshResponse = await fetch("/auth/refresh", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ refresh_token: refreshToken })
                });

                if (refreshResponse.ok) {
                    const data = await refreshResponse.json();
                    sessionStorage.setItem("token", data.access_token);
                    sessionStorage.setItem("refresh_token", data.refresh_token);

                    // Retry original request with new access token
                    options.headers["Authorization"] = `Bearer ${data.access_token}`;
                    response = await fetch(url, options);
                } else {
                    sessionStorage.removeItem("token");
                    sessionStorage.removeItem("refresh_token");
                    sessionStorage.removeItem("user");
                }
            } catch (e) {
                console.error("Token refresh failed:", e);
            }
        }
    }

    return response;
}
