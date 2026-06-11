// シフト登録フォームを取得
const form = document.querySelector("#shift-form");
// 名前入力欄を取得
const nameInput = document.querySelector("#name-input");
// 日付入力欄を取得
const dateInput = document.querySelector("#date-input");
// 時間入力欄を取得
const timeInput = document.querySelector("#time-input");
// エラーメッセージ表示用の要素を取得
const errorMessage = document.querySelector("#error-message");
// フォーム送信時の入力チェック
form.addEventListener("submit", (event) => {
    // 名前・日付・時間のどれかが未入力の場合
    if (
        nameInput.value.trim() === "" ||
        dateInput.value.trim() === "" ||
        timeInput.value.trim() === ""
    ) {
        // フォーム送信を中止
        event.preventDefault();
        // エラーメッセージを表示
        errorMessage.textContent = "すべて入力してください";
    }
});
// 名前入力時にエラーメッセージを消す
nameInput.addEventListener("input", () => {

    errorMessage.textContent = "";
});
// 日付入力時にエラーメッセージを消す
dateInput.addEventListener("input", () => {

    errorMessage.textContent = "";
});
// 時間入力時にエラーメッセージを消す
timeInput.addEventListener("input", () => {

    errorMessage.textContent = "";
});
// 削除確認のコード
const deleteForms = document.querySelectorAll(".delete-form");
// 削除フォームに対してイベントリスナーを追加(一つずつ)して、削除確認のダイアログを表示する
deleteForms.forEach((form) => {

    form.addEventListener("submit", (event) => {

        const result = confirm("本当に削除しますか？");

        if (!result) {

            event.preventDefault();

        }

    });

});