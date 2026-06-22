from wave_engine.pivot_filter import filter_pivots


def find_pivots(
    df,
    left=3,
    right=3
):

    pivots_high = []
    pivots_low = []

    highs = df["high"].tolist()
    lows = df["low"].tolist()

    for i in range(left, len(df) - right):

        current_high = highs[i]

        is_pivot_high = True

        for j in range(
            i - left,
            i + right + 1
        ):

            if j == i:
                continue

            if highs[j] >= current_high:

                is_pivot_high = False
                break

        if is_pivot_high:

            pivots_high.append(
                {
                    "index": i,
                    "price": current_high
                }
            )

        current_low = lows[i]

        is_pivot_low = True

        for j in range(
            i - left,
            i + right + 1
        ):

            if j == i:
                continue

            if lows[j] <= current_low:

                is_pivot_low = False
                break

        if is_pivot_low:

            pivots_low.append(
                {
                    "index": i,
                    "price": current_low
                }
            )

    return {
        "highs": pivots_high,
        "lows": pivots_low
    }


def get_last_pivots(
    df,
    timeframe="W1"
):

    if timeframe == "W1":

        left = 5
        right = 5
        distance = 2.0

    elif timeframe == "D1":

        left = 3
        right = 3
        distance = 1.0

    else:

        left = 2
        right = 2
        distance = 0.2

    pivots = find_pivots(
        df,
        left,
        right
    )

    highs = filter_pivots(
        pivots["highs"],
        min_distance_percent=distance
    )

    lows = filter_pivots(
        pivots["lows"],
        min_distance_percent=distance
    )

    return {

        "highs": highs[-30:],

        "lows": lows[-30:]
    }