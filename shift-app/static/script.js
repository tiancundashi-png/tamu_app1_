const form = document.querySelector("#shift-form");

const nameInput = document.querySelector("#name-input");

const dateInput = document.querySelector("#date-input");

const timeInput = document.querySelector("#time-input");

const errorMessage = document.querySelector("#error-message");

form.addEventListener("submit", (event) => {

    if (
        nameInput.value.trim() === "" ||
        dateInput.value.trim() === "" ||
        timeInput.value.trim() === ""
    ) {

        event.preventDefault();

        errorMessage.textContent = "すべて入力してください";
    }
});

nameInput.addEventListener("input", () => {

    errorMessage.textContent = "";
});

dateInput.addEventListener("input", () => {

    errorMessage.textContent = "";
});

timeInput.addEventListener("input", () => {

    errorMessage.textContent = "";
});
const deleteForms = document.querySelectorAll(".delete-form");

deleteForms.forEach((form) => {

    form.addEventListener("submit", (event) => {

        const result = confirm("本当に削除しますか？");

        if (!result) {

            event.preventDefault();

        }

    });

});