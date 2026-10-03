
from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DATABASE = "irrigation.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            min_water INTEGER NOT NULL,
            max_water INTEGER NOT NULL,
            yield_rate REAL NOT NULL,
            priority INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def greedy_algorithm(crops, available_water):

    sorted_crops = sorted(
        crops,
        key=lambda x: (x["yield_rate"], x["priority"]),
        reverse=True
    )

    result = []
    remaining = available_water

    # First satisfy minimum water requirements
    for crop in sorted_crops:

        if remaining >= crop["min_water"]:
            allocation = crop["min_water"]
            remaining -= allocation
        else:
            allocation = 0

        result.append({
            "id": crop["id"],
            "name": crop["name"],
            "allocation": allocation,
            "yield": allocation * crop["yield_rate"]
        })

    # Give remaining water
    for item in result:

        crop = next(
            c for c in crops
            if c["id"] == item["id"]
        )

        extra_capacity = (
            crop["max_water"] - item["allocation"]
        )

        extra = min(extra_capacity, remaining)

        item["allocation"] += extra

        item["yield"] = (
            item["allocation"] *
            crop["yield_rate"]
        )

        remaining -= extra

        if remaining <= 0:
            break

    total_water = sum(
        item["allocation"]
        for item in result
    )

    total_yield = sum(
        item["yield"]
        for item in result
    )

    return result, total_water, total_yield

def dp_algorithm(crops, available_water):

    water = int(available_water)
    n = len(crops)

    # DP table
    dp = [
        [-1 for _ in range(water + 1)]
        for _ in range(n + 1)
    ]

    # Store the water allocated to each crop
    choice = [
        [0 for _ in range(water + 1)]
        for _ in range(n + 1)
    ]

    # With zero crops, zero water gives zero yield
    dp[0][0] = 0

    for i in range(1, n + 1):

        crop = crops[i - 1]

        minimum = int(crop["min_water"])
        maximum = int(crop["max_water"])
        rate = float(crop["yield_rate"])

        for w in range(water + 1):

            # Try every valid allocation for this crop
            for allocation in range(
                minimum,
                min(maximum, w) + 1
            ):

                previous_water = w - allocation

                if dp[i - 1][previous_water] == -1:
                    continue

                value = (
                    dp[i - 1][previous_water]
                    + allocation * rate
                )

                if value > dp[i][w]:

                    dp[i][w] = value
                    choice[i][w] = allocation

    # Reconstruct the solution
    result = []

    remaining_water = water

    for i in range(n, 0, -1):

        crop = crops[i - 1]

        allocation = choice[i][remaining_water]

        result.append({
            "id": crop["id"],
            "name": crop["name"],
            "allocation": allocation,
            "yield": allocation * crop["yield_rate"]
        })

        remaining_water -= allocation

    result.reverse()

    total_water = sum(
        item["allocation"]
        for item in result
    )

    total_yield = sum(
        item["yield"]
        for item in result
    )

    return result, total_water, total_yield


@app.route("/")
def index():

    conn = get_db()

    crops = conn.execute(
        "SELECT * FROM crops"
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        crops=crops
    )


@app.route("/add_crop", methods=["POST"])
def add_crop():

    name = request.form["name"]

    min_water = int(
        request.form["min_water"]
    )

    max_water = int(
        request.form["max_water"]
    )

    yield_rate = float(
        request.form["yield_rate"]
    )

    priority = int(
        request.form["priority"]
    )

    conn = get_db()

    conn.execute("""
        INSERT INTO crops
        (name, min_water, max_water,
         yield_rate, priority)

        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        min_water,
        max_water,
        yield_rate,
        priority
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/crops")
def crops_page():

    conn = get_db()

    crops = conn.execute(
        "SELECT * FROM crops"
    ).fetchall()

    conn.close()

    return render_template(
        "crops.html",
        crops=crops
    )


@app.route("/delete_crop/<int:crop_id>")
def delete_crop(crop_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM crops WHERE id = ?",
        (crop_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("crops_page"))


@app.route("/optimize", methods=["POST"])
def optimize():

    available_water = int(
        request.form["available_water"]
    )

    conn = get_db()

    crops = conn.execute(
        "SELECT * FROM crops"
    ).fetchall()

    conn.close()

    if not crops:
        return "Please add at least one crop."

    total_minimum = sum(
        crop["min_water"]
        for crop in crops
    )

    if available_water < total_minimum:

        return render_template(
            "results.html",
            error=True,
            message=(
                f"Available water ({available_water} L) "
                f"is less than minimum requirement "
                f"({total_minimum} L)."
            )
        )

    greedy_result, greedy_water, greedy_yield = \
        greedy_algorithm(
            crops,
            available_water
        )

    dp_result, dp_water, dp_yield = \
        dp_algorithm(
            crops,
            available_water
        )

    return render_template(
        "results.html",

        error=False,

        available_water=available_water,

        greedy_result=greedy_result,
        greedy_water=greedy_water,
        greedy_yield=round(
            greedy_yield, 2
        ),

        dp_result=dp_result,
        dp_water=dp_water,
        dp_yield=round(
            dp_yield, 2
        )
    )


if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
    