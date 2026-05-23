from flask import Flask, render_template, request, redirect
import os

print(os.getcwd())
print("AAAAAAAA")
print("AAAAAAAA")
app = Flask(__name__)
shifts = []
id_counter = 0
@app.route("/", methods=["GET", "POST"])
def home():

    global id_counter

    name = ""
    date = ""
    time = ""

    if request.method == "POST":

        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]

        shift = {
            "id": id_counter,
            "name": name,
            "date": date,
            "time": time
        }

        shifts.append(shift)
        id_counter += 1

    return render_template(
        "index.html",
        shifts=shifts
    )
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):

    global shifts

    for shift in shifts:

        if shift["id"] == id:

            shifts.remove(shift)

            break

    return redirect("/")

app.run(debug=True, port=5001)
