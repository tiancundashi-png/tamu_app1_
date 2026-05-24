// htmlのclass="delete-button"の要素を取得
const deleteButtons = document.querySelectorAll(".delete-button");
// 取得した要素に対してループ処理
deleteButtons.forEach((button) => {
// ボタンがクリックされたときのイベントリスナーを追加
    button.addEventListener("click", (event) => {
// OK / キャンセルを出す
        const result = confirm("本当に削除しますか？");

        if (!result) {
// キャンセルされた場合、デフォルトのフォーム送信を防止
            event.preventDefault();
        }
    });
});