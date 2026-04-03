const token = localStorage.getItem("token");
if (!token) {
    window.location.href = "/";
}

const assignmentId = window.location.pathname.split("/").pop();

async function fetchWithAuth(url, options = {}) {
    options.headers = {
        ...options.headers,
        Authorization: `Bearer ${token}`,
    };
    return fetch(url, options);
}

async function loadAssignment() {
    const res = await fetchWithAuth(`/api/v1/assignments/${assignmentId}`);
    if (res.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "/";
        return;
    }
    if (!res.ok) return;

    const data = await res.json();
    document.getElementById("assignment-title").textContent = data.title;
    document.getElementById("assignment-course").textContent = data.course_name || "-";
    document.getElementById("assignment-group").textContent = data.group_name || "-";

    renderTasks(data.tasks);
}

function renderTasks(tasks) {
    const tbody = document.getElementById("tasks-body");
    const noMsg = document.getElementById("no-tasks");
    tbody.innerHTML = "";

    if (tasks.length === 0) {
        noMsg.classList.remove("d-none");
        return;
    }

    noMsg.classList.add("d-none");
    tasks.forEach((t) => {
        const tr = document.createElement("tr");
        const tcJson = t.test_cases ? JSON.stringify(t.test_cases) : "";
        tr.innerHTML = `
            <td>${t.task_code}</td>
            <td>${t.title}</td>
            <td>${t.max_score}</td>
            <td><span class="badge bg-secondary">${t.check_type}</span></td>
            <td>
                <button class="btn btn-outline-primary btn-sm me-1 edit-task-btn"
                        data-id="${t.id}"
                        data-task_code="${t.task_code}"
                        data-title="${t.title}"
                        data-max_score="${t.max_score}"
                        data-check_type="${t.check_type}"
                        data-expected_answer="${t.expected_answer || ""}"
                        data-test_cases='${tcJson}'>&#9998;</button>
                <button class="btn btn-outline-danger btn-sm delete-task-btn"
                        data-id="${t.id}">&#10005;</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Dynamic fields for check_type
const checkTypeSelect = document.getElementById("check-type-select");
const answerField = document.getElementById("answer-field");
const testsField = document.getElementById("tests-field");

function toggleCheckTypeFields() {
    const val = checkTypeSelect.value;
    answerField.classList.toggle("d-none", val !== "answer");
    testsField.classList.toggle("d-none", val !== "tests");
}

checkTypeSelect.addEventListener("change", toggleCheckTypeFields);
toggleCheckTypeFields();

document.getElementById("add-task-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const errBox = document.getElementById("task-error");
    errBox.classList.add("d-none");

    const body = {
        task_code: form.task_code.value,
        title: form.title.value,
        max_score: parseInt(form.max_score.value, 10),
        check_type: form.check_type.value,
    };

    if (body.check_type === "answer") {
        const ans = form.expected_answer.value.trim();
        if (ans) body.expected_answer = ans;
    } else if (body.check_type === "tests") {
        const raw = form.test_cases.value.trim();
        if (raw) {
            try {
                body.test_cases = JSON.parse(raw);
            } catch {
                errBox.textContent = "Невалидный JSON в тест-кейсах";
                errBox.classList.remove("d-none");
                return;
            }
        }
    }

    const res = await fetchWithAuth(`/api/v1/assignments/${assignmentId}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        const data = await res.json();
        errBox.textContent = data.detail || "Ошибка добавления задачи";
        errBox.classList.remove("d-none");
        return;
    }

    form.reset();
    toggleCheckTypeFields();
    bootstrap.Modal.getInstance(document.getElementById("add-task-modal")).hide();
    await loadAssignment();
});

// Edit task modal: dynamic fields
const editCheckTypeSelect = document.getElementById("edit-check-type-select");
const editAnswerField = document.getElementById("edit-answer-field");
const editTestsField = document.getElementById("edit-tests-field");

function toggleEditCheckTypeFields() {
    const val = editCheckTypeSelect.value;
    editAnswerField.classList.toggle("d-none", val !== "answer");
    editTestsField.classList.toggle("d-none", val !== "tests");
}

editCheckTypeSelect.addEventListener("change", toggleEditCheckTypeFields);

// Open edit task modal
document.getElementById("tasks-body").addEventListener("click", (e) => {
    const editBtn = e.target.closest(".edit-task-btn");
    if (editBtn) {
        const form = document.getElementById("edit-task-form");
        form.task_id.value = editBtn.dataset.id;
        form.task_code.value = editBtn.dataset.task_code;
        form.title.value = editBtn.dataset.title;
        form.max_score.value = editBtn.dataset.max_score;
        form.check_type.value = editBtn.dataset.check_type;
        form.expected_answer.value = editBtn.dataset.expected_answer || "";
        form.test_cases.value = editBtn.dataset.test_cases || "";
        document.getElementById("edit-task-error").classList.add("d-none");
        toggleEditCheckTypeFields();
        new bootstrap.Modal(document.getElementById("edit-task-modal")).show();
    }
});

// Submit edit task
document.getElementById("edit-task-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const errBox = document.getElementById("edit-task-error");
    errBox.classList.add("d-none");

    const taskId = form.task_id.value;
    const body = {
        task_code: form.task_code.value,
        title: form.title.value,
        max_score: parseInt(form.max_score.value, 10),
        check_type: form.check_type.value,
    };

    if (body.check_type === "answer") {
        body.expected_answer = form.expected_answer.value.trim() || null;
        body.test_cases = null;
    } else if (body.check_type === "tests") {
        body.expected_answer = null;
        const raw = form.test_cases.value.trim();
        if (raw) {
            try {
                body.test_cases = JSON.parse(raw);
            } catch {
                errBox.textContent = "Невалидный JSON в тест-кейсах";
                errBox.classList.remove("d-none");
                return;
            }
        } else {
            body.test_cases = null;
        }
    }

    const res = await fetchWithAuth(
        `/api/v1/assignments/${assignmentId}/tasks/${taskId}`,
        {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        }
    );

    if (!res.ok) {
        const data = await res.json();
        errBox.textContent = data.detail || "Ошибка сохранения";
        errBox.classList.remove("d-none");
        return;
    }

    bootstrap.Modal.getInstance(document.getElementById("edit-task-modal")).hide();
    await loadAssignment();
});

// Delete task
document.getElementById("tasks-body").addEventListener("click", async (e) => {
    const delBtn = e.target.closest(".delete-task-btn");
    if (!delBtn) return;

    if (!confirm("Удалить задачу?")) return;

    const taskId = delBtn.dataset.id;
    const res = await fetchWithAuth(
        `/api/v1/assignments/${assignmentId}/tasks/${taskId}`,
        { method: "DELETE" }
    );

    if (!res.ok) {
        const data = await res.json();
        alert(data.detail || "Ошибка удаления");
        return;
    }

    await loadAssignment();
});

document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const resultBox = document.getElementById("upload-result");
    const spinner = document.getElementById("upload-spinner");
    const spinnerText = document.getElementById("upload-spinner-text");
    const submitBtn = document.getElementById("upload-btn");

    resultBox.classList.add("d-none");

    const fileInput = document.getElementById("ipynbFiles");
    const fileCount = fileInput.files.length;

    const formData = new FormData();
    for (const f of fileInput.files) {
        formData.append("files", f);
    }

    // Show spinner, disable button
    spinnerText.textContent = `Проверка работ (${fileCount})...`;
    spinner.classList.remove("d-none");
    submitBtn.disabled = true;

    let res;
    try {
        res = await fetchWithAuth(`/api/v1/assignments/${assignmentId}/submissions`, {
            method: "POST",
            body: formData,
        });
    } catch (err) {
        spinner.classList.add("d-none");
        submitBtn.disabled = false;
        resultBox.classList.remove("d-none");
        resultBox.className = "mt-3 alert alert-danger";
        resultBox.textContent = "Сетевая ошибка: " + err.message;
        return;
    }

    spinner.classList.add("d-none");
    submitBtn.disabled = false;

    const data = await res.json();
    resultBox.classList.remove("d-none");

    if (!res.ok) {
        resultBox.className = "mt-3 alert alert-danger";
        resultBox.textContent = data.detail || "Ошибка загрузки";
        return;
    }

    const rows = data.results.map((r) => {
        const badge = r.status === "graded"
            ? `<span class="badge bg-success">OK</span>`
            : `<span class="badge bg-danger" title="${r.error || ""}">ошибка</span>`;
        return `<tr>
            <td>${r.student_fio || "-"}</td>
            <td>${r.student_group || "-"}</td>
            <td>${r.total_score}</td>
            <td>${badge}</td>
        </tr>`;
    }).join("");

    resultBox.className = "mt-3 alert alert-info p-2";
    resultBox.innerHTML = `
        <p class="mb-2">
            Проверено работ: <strong>${data.success}</strong> из <strong>${data.total}</strong>
            ${data.failed ? ` | <span class="text-danger">Ошибки: ${data.failed}</span>` : ""}
        </p>
        <table class="table table-sm table-bordered mb-0">
            <thead><tr><th>ФИО</th><th>Группа</th><th>Балл</th><th>Статус</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
});

document.getElementById("download-report").addEventListener("click", async () => {
    const res = await fetchWithAuth(`/api/v1/assignments/${assignmentId}/report`);
    if (!res.ok) {
        alert("Нет данных для отчета");
        return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report_${assignmentId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
});

document.getElementById("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("token");
    window.location.href = "/";
});

loadAssignment();
