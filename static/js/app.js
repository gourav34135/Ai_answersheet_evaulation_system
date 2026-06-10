const form = document.querySelector("#evaluationForm");
const fileInput = document.querySelector("#fileInput");
const dropZone = document.querySelector("#dropZone");
const fileName = document.querySelector("#fileName");
const evaluateBtn = document.querySelector("#evaluateBtn");
const resetBtn = document.querySelector("#resetBtn");
const scoreValue = document.querySelector("#scoreValue");
const scoreMeter = document.querySelector("#scoreMeter");
const confidenceValue = document.querySelector("#confidenceValue");
const feedbackList = document.querySelector("#feedbackList");
const extractedText = document.querySelector("#extractedText");
const matchedPoints = document.querySelector("#matchedPoints");
const missingPoints = document.querySelector("#missingPoints");
const historyList = document.querySelector("#historyList");
const refreshHistoryBtn = document.querySelector("#refreshHistoryBtn");
const loadDemoBtn = document.querySelector("#loadDemoBtn");
const clearHistoryBtn = document.querySelector("#clearHistoryBtn");
const copyTextBtn = document.querySelector("#copyTextBtn");
const rescoreBtn = document.querySelector("#rescoreBtn");
const toast = document.querySelector("#toast");

let toastTimer = null;

function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3600);
}

function setLoading(isLoading) {
    form.classList.toggle("loading", isLoading);
    evaluateBtn.textContent = isLoading ? "Evaluating..." : "Evaluate Answer";
}

function updateFileName() {
    const file = fileInput.files[0];
    fileName.textContent = file ? file.name : "PDF, JPG, PNG, WEBP, or TIFF";
}

function renderList(target, items, emptyText) {
    target.innerHTML = "";
    if (!items || items.length === 0) {
        const li = document.createElement("li");
        li.textContent = emptyText;
        target.appendChild(li);
        return;
    }

    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        target.appendChild(li);
    });
}

function renderResult(payload) {
    const result = payload.result;
    const score = Number(result.score || 0);
    const maxScore = Number(result.max_score || 10);
    const percentage = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;

    scoreValue.textContent = `${score} / ${maxScore}`;
    scoreMeter.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
    confidenceValue.textContent = `Confidence: ${result.confidence}`;
    setExtractedText(payload.extracted_text || "No extracted text available.");

    renderList(feedbackList, result.feedback, "No feedback available.");
    renderList(matchedPoints, result.matched_points, "No matched points detected.");
    renderList(missingPoints, result.missing_points, "No missing points detected.");

    document.querySelector("#metricSimilarity").textContent = result.metrics.semantic_similarity.toFixed(3);
    document.querySelector("#metricConcepts").textContent = (result.metrics.concept_coverage || 0).toFixed(3);
    document.querySelector("#metricCoverage").textContent = result.metrics.key_point_coverage.toFixed(3);
    document.querySelector("#metricWords").textContent = result.metrics.word_count;
}

function setExtractedText(value) {
    extractedText.value = value;
}

function getExtractedText() {
    return extractedText.value || "";
}

async function loadHistory() {
    const response = await fetch("/api/history");
    const data = await response.json();
    historyList.innerHTML = "";

    if (!data.items || data.items.length === 0) {
        historyList.innerHTML = '<p class="muted">No saved evaluations yet.</p>';
        return;
    }

    data.items.forEach((item) => {
        const wrapper = document.createElement("article");
        wrapper.className = "history-item";
        wrapper.innerHTML = `
            <header>
                <div>
                    <strong>${escapeHtml(item.student_name)}</strong>
                    <small>${escapeHtml(item.file_name)}</small>
                </div>
                <span class="history-score">${item.score} / ${item.max_score}</span>
            </header>
            <small>${escapeHtml(item.created_at)} | ${escapeHtml(item.confidence)} confidence</small>
            <div class="history-actions">
                <button type="button" data-action="view" data-id="${item.id}">View</button>
                <a href="/api/report/${item.id}">Report</a>
                <button class="delete-button" type="button" data-action="delete" data-id="${item.id}">Delete</button>
            </div>
        `;
        historyList.appendChild(wrapper);
    });
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
    if (event.dataTransfer.files.length > 0) {
        fileInput.files = event.dataTransfer.files;
        updateFileName();
    }
});

fileInput.addEventListener("change", updateFileName);

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);

    setLoading(true);
    try {
        const response = await fetch("/api/evaluate", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Evaluation failed.");
        }

        renderResult(data);
        await loadHistory();
        showToast("Evaluation saved to history.");
    } catch (error) {
        showToast(error.message);
    } finally {
        setLoading(false);
    }
});

resetBtn.addEventListener("click", () => {
    setTimeout(() => {
        updateFileName();
        setExtractedText("OCR output will appear here.");
        scoreValue.textContent = "0 / 10";
        scoreMeter.style.width = "0";
        confidenceValue.textContent = "Waiting for an answer sheet";
        document.querySelector("#metricSimilarity").textContent = "0.000";
        document.querySelector("#metricConcepts").textContent = "0.000";
        document.querySelector("#metricCoverage").textContent = "0.000";
        document.querySelector("#metricWords").textContent = "0";
        renderList(feedbackList, ["Upload an answer sheet and add a reference answer for the most reliable result."], "");
        renderList(matchedPoints, [], "No matched points detected.");
        renderList(missingPoints, [], "No missing points detected.");
    }, 0);
});

refreshHistoryBtn.addEventListener("click", () => {
    loadHistory().then(() => showToast("History refreshed."));
});

clearHistoryBtn.addEventListener("click", async () => {
    if (!window.confirm("Clear all saved evaluation history?")) {
        return;
    }
    const response = await fetch("/api/history", { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) {
        showToast(data.error || "Could not clear history.");
        return;
    }
    await loadHistory();
    showToast("Evaluation history cleared.");
});

loadDemoBtn.addEventListener("click", async () => {
    try {
        const response = await fetch("/api/demo-rubric");
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Could not load demo rubric.");
        }
        form.elements.question.value = data.questions;
        form.elements.reference_answer.value = data.reference_answers;
        form.elements.marking_points.value = data.marking_points;
        form.elements.max_score.value = data.max_score;
        showToast("Five-question demo rubric loaded.");
    } catch (error) {
        showToast(error.message);
    }
});

historyList.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.dataset.action) {
        return;
    }

    const id = target.dataset.id;
    if (target.dataset.action === "view") {
        const response = await fetch(`/api/history/${id}`);
        const item = await response.json();
        if (!response.ok) {
            showToast(item.error || "Could not load history item.");
            return;
        }
        renderResult({
            extracted_text: item.extracted_text,
            result: item.result,
        });
        showToast("History item loaded.");
    }

    if (target.dataset.action === "delete") {
        const response = await fetch(`/api/history/${id}`, { method: "DELETE" });
        const data = await response.json();
        if (!response.ok) {
            showToast(data.error || "Could not delete item.");
            return;
        }
        await loadHistory();
        showToast("History item deleted.");
    }
});

copyTextBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(getExtractedText());
    showToast("Extracted text copied.");
});

rescoreBtn.addEventListener("click", async () => {
    const payload = {
        extracted_text: getExtractedText(),
        student_name: new FormData(form).get("student_name") || "Edited OCR",
        question: new FormData(form).get("question") || "",
        reference_answer: new FormData(form).get("reference_answer") || "",
        marking_points: new FormData(form).get("marking_points") || "",
        max_score: new FormData(form).get("max_score") || "10",
    };

    setLoading(true);
    try {
        const response = await fetch("/api/rescore", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Re-score failed.");
        }
        renderResult(data);
        await loadHistory();
        showToast("Edited text re-scored and saved.");
    } catch (error) {
        showToast(error.message);
    } finally {
        setLoading(false);
    }
});

loadHistory();
