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
        const msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
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
