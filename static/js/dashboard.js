const token = localStorage.getItem("token");
if (!token) {
    window.location.href = "/";
}

async function fetchWithAuth(url, options = {}) {
    options.headers = {
        ...options.headers,
        Authorization: `Bearer ${token}`,
    };
    return fetch(url, options);
}

async function loadAssignments() {
    const res = await fetchWithAuth("/api/v1/assignments");
    if (res.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "/";
        return;
    }

    const assignments = await res.json();
    const tbody = document.getElementById("assignments-body");
    const noMsg = document.getElementById("no-assignments");

    tbody.innerHTML = "";

    if (assignments.length === 0) {
        noMsg.classList.remove("d-none");
        return;
    }

    noMsg.classList.add("d-none");

    assignments.forEach((a) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${a.id}</td>
            <td><a href="/assignment/${a.id}">${a.title}</a></td>
            <td>${a.course_name || "-"}</td>
            <td>${a.group_name || "-"}</td>
            <td>${a.tasks.length}</td>
            <td>
                <button class="btn btn-outline-primary btn-sm me-1 edit-assignment-btn"
                        data-id="${a.id}" data-title="${a.title}"
                        data-course="${a.course_name || ""}"
                        data-group="${a.group_name || ""}">&#9998;</button>
                <button class="btn btn-outline-danger btn-sm delete-assignment-btn"
                        data-id="${a.id}">&#10005;</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById("create-assignment-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const errBox = document.getElementById("create-error");
    errBox.classList.add("d-none");

    const body = {
        title: form.title.value,
        course_name: form.course_name.value || null,
        group_name: form.group_name.value || null,
    };

    const res = await fetchWithAuth("/api/v1/assignments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        const data = await res.json();
        errBox.textContent = data.detail || "Ошибка создания";
        errBox.classList.remove("d-none");
        return;
    }

    form.reset();
    bootstrap.Modal.getInstance(document.getElementById("create-modal")).hide();
    await loadAssignments();
});

// Edit assignment
document.getElementById("assignments-body").addEventListener("click", (e) => {
    const editBtn = e.target.closest(".edit-assignment-btn");
    if (editBtn) {
        const form = document.getElementById("edit-assignment-form");
        form.assignment_id.value = editBtn.dataset.id;
        form.title.value = editBtn.dataset.title;
        form.course_name.value = editBtn.dataset.course;
        form.group_name.value = editBtn.dataset.group;
        document.getElementById("edit-error").classList.add("d-none");
        new bootstrap.Modal(document.getElementById("edit-assignment-modal")).show();
    }
});

document.getElementById("edit-assignment-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const errBox = document.getElementById("edit-error");
    errBox.classList.add("d-none");

    const id = form.assignment_id.value;
    const body = {
        title: form.title.value,
        course_name: form.course_name.value || null,
        group_name: form.group_name.value || null,
    };

    const res = await fetchWithAuth(`/api/v1/assignments/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        const data = await res.json();
        errBox.textContent = data.detail || "Ошибка сохранения";
        errBox.classList.remove("d-none");
        return;
    }

    bootstrap.Modal.getInstance(document.getElementById("edit-assignment-modal")).hide();
    await loadAssignments();
});

// Delete assignment
document.getElementById("assignments-body").addEventListener("click", async (e) => {
    const delBtn = e.target.closest(".delete-assignment-btn");
    if (!delBtn) return;

    if (!confirm("Удалить задание?")) return;

    const id = delBtn.dataset.id;
    const res = await fetchWithAuth(`/api/v1/assignments/${id}`, { method: "DELETE" });

    if (!res.ok) {
        const data = await res.json();
        alert(data.detail || "Ошибка удаления");
        return;
    }

    await loadAssignments();
});

document.getElementById("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("token");
    window.location.href = "/";
});

loadAssignments();
