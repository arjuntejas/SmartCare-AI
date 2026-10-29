
document.addEventListener("DOMContentLoaded", async () => {
    const patientCanvas = document.getElementById("patientChart");
    const bedCanvas = document.getElementById("bedChart");

    // Stop if this page does not contain the dashboard charts.
    if (!patientCanvas && !bedCanvas) {
        return;
    }

    // Check whether Chart.js loaded from the CDN.
    if (typeof Chart === "undefined") {
        console.error(
            "Chart.js did not load. Check your internet connection."
        );
        return;
    }

    try {
        // Request saved hospital records from Flask.
        const response = await fetch("/api/analytics", {
            headers: {
                Accept: "application/json"
            },
            credentials: "same-origin"
        });

        if (!response.ok) {
            throw new Error(
                "Could not load analytics. HTTP status: " +
                response.status
            );
        }

        const data = await response.json();

        // ---------------------------------------
        // 1. PATIENT DEMAND TREND CHART
        // ---------------------------------------

        if (patientCanvas) {
            new Chart(patientCanvas, {
                type: "line",

                data: {
                    labels: data.labels,

                    datasets: [{
                        label: "Patients",
                        data: data.patients,
                        borderColor: "#2463eb",
                        backgroundColor: "rgba(36, 99, 235, 0.10)",
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        fill: true,
                        tension: 0.35
                    }]
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    interaction: {
                        intersect: false,
                        mode: "index"
                    },

                    plugins: {
                        legend: {
                            display: false
                        },

                        tooltip: {
                            enabled: true
                        }
                    },

                    scales: {
                        x: {
                            grid: {
                                display: false
                            },

                            ticks: {
                                maxTicksLimit: 8,
                                maxRotation: 0
                            }
                        },

                        y: {
                            beginAtZero: true,

                            grid: {
                                color: "#edf1f6"
                            },

                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        }

        // ---------------------------------------
        // 2. OCCUPIED AND AVAILABLE BEDS CHART
        // ---------------------------------------

        if (bedCanvas) {
            const lastIndex = data.occupied_beds.length - 1;

            const occupied =
                lastIndex >= 0
                    ? data.occupied_beds[lastIndex]
                    : 0;

            const available =
                lastIndex >= 0
                    ? data.available_beds[lastIndex]
                    : 0;

            new Chart(bedCanvas, {
                type: "doughnut",

                data: {
                    labels: [
                        "Occupied beds",
                        "Available beds"
                    ],

                    datasets: [{
                        data: [occupied, available],

                        backgroundColor: [
                            "#13b8a6",
                            "#e2e9f1"
                        ],

                        borderWidth: 0,
                        hoverOffset: 5
                    }]
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "76%",

                    plugins: {
                        legend: {
                            display: false
                        },

                        tooltip: {
                            enabled: true
                        }
                    }
                }
            });
        }

    } catch (error) {
        console.error(
            "SmartCare AI chart error:",
            error
        );
    }
});
