document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("filters-form");
    if (!form) return;

    form.querySelectorAll("select").forEach((select) => {
        select.addEventListener("change", () => form.submit());
    });
});
