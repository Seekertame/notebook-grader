function formatValidationErrors(detail) {
    if (!Array.isArray(detail)) return null;
    const messages = [];
    for (const err of detail) {
        const loc = Array.isArray(err.loc) ? err.loc : [];
        const field = loc[loc.length - 1];
        const msg = (err.msg || "").toLowerCase();
        const type = (err.type || "").toLowerCase();

        if (field === "email") {
            if (type.includes("email") || msg.includes("email")) {
                messages.push("Некорректный формат email");
            } else if (msg.includes("at most") || msg.includes("max_length") || type.includes("string_too_long")) {
                messages.push("Email не должен превышать 100 символов");
            } else {
                messages.push("Некорректный email");
            }
        } else if (field === "password") {
            if (msg.includes("at least") || msg.includes("min_length") || type.includes("string_too_short")) {
                messages.push("Пароль должен содержать не менее 8 символов");
            } else if (msg.includes("at most") || msg.includes("max_length") || type.includes("string_too_long")) {
                messages.push("Пароль не должен превышать 64 символа");
            } else {
                messages.push("Некорректный пароль");
            }
        } else {
            return null;
        }
    }
    return messages.length ? messages.join("\n") : null;
}

document.getElementById("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const errBox = document.getElementById("register-error");
    const okBox = document.getElementById("register-ok");
    errBox.classList.add("d-none");
    okBox.classList.add("d-none");

    const body = {
        email: fd.get("email"),
        password: fd.get("password"),
        display_name: fd.get("display_name") || null,
    };

    const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        const data = await res.json();
        let msg;
        if (res.status === 422) {
            msg = formatValidationErrors(data.detail) || "Проверьте корректность введённых данных";
        } else {
            msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        }
        errBox.textContent = msg || "Ошибка регистрации";
        errBox.classList.remove("d-none");
        return;
    }

    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    window.location.href = "/dashboard";
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const errBox = document.getElementById("login-error");
    errBox.classList.add("d-none");

    const params = new URLSearchParams();
    params.append("username", fd.get("username"));
    params.append("password", fd.get("password"));

    const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        body: params,
    });

    if (!res.ok) {
        const data = await res.json();
        const msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        errBox.textContent = msg || "Ошибка входа";
        errBox.classList.remove("d-none");
        return;
    }

    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    window.location.href = "/dashboard";
});
