# wave_engine/swing_structure.py

def build_swing_sequence(pivots):

    highs = pivots["highs"]
    lows = pivots["lows"]

    swings = []

    for high in highs:

        swings.append(
            {
                "type": "HIGH",
                "index": high["index"],
                "price": high["price"]
            }
        )

    for low in lows:

        swings.append(
            {
                "type": "LOW",
                "index": low["index"],
                "price": low["price"]
            }
        )

    swings.sort(
        key=lambda x: x["index"]
    )

    cleaned = []

    for swing in swings:

        if not cleaned:
            cleaned.append(swing)
            continue

        last = cleaned[-1]

        if swing["type"] == last["type"]:

            if swing["type"] == "HIGH":

                if swing["price"] > last["price"]:
                    cleaned[-1] = swing

            else:

                if swing["price"] < last["price"]:
                    cleaned[-1] = swing

        else:

            cleaned.append(swing)

    return cleaned