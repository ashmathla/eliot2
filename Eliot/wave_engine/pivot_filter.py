# wave_engine/pivot_filter.py

def filter_pivots(pivots, min_distance_percent=0.5):

    if not pivots:
        return []

    filtered = [pivots[0]]

    for pivot in pivots[1:]:

        last_price = filtered[-1]["price"]

        distance = abs(
            pivot["price"] - last_price
        )

        percent = (
            distance / last_price
        ) * 100

        if percent >= min_distance_percent:

            filtered.append(pivot)

    return filtered