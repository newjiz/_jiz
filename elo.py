from bson.objectid import ObjectId

R0 = 1500
K = 20


def k_inter(_c):
    return K + (1 / _c) * K


def compute_estimated(r_a, r_b):
    return 1. / (1. + 10**((r_b - r_a) / 400))


def compute_new_rating(r_a, k, win, e_a):
    _w = 1 if win else 0
    return r_a + k * (_w - e_a)


def update_elo(win, los):
    """
    Returns a ELO update query for two contents.

    Parameters
    ----------
        win: Object
            Winner content
        
        los: Object
            Loser content
    
    Returns
    -------
        str, str
            Update queries for winner and looser, resp.
    """

    rating_win, rating_los = win["votes"]["elo"], los["votes"]["elo"]
    count_win, count_los = win["votes"]["total"] + 1, los["votes"]["total"] + 1


    computed_win = compute_estimated(rating_win, rating_los)
    win_elo = compute_new_rating(
        rating_win,
        k_inter(count_win),
        True,
        computed_win)

    computed_los = compute_estimated(rating_los, rating_win)
    los_elo = compute_new_rating(
        rating_los,
        k_inter(count_los),
        False,
        computed_los)


    win_query = (
        {"_id": win["_id"]},
        {
            "$set": {
                "votes": {
                    "total": int(win["votes"]["total"] + 1),
                    "elo": win_elo,
                    "up": int(win["votes"]["up"] + 1),
                    "down": int(win["votes"]["down"])
                }
            }
        })

    los_query = (
        {"_id": los["_id"]},
        {
            "$set": {
                "votes": {
                    "total": int(los["votes"]["total"] + 1),
                    "elo": los_elo,
                    "up": int(los["votes"]["up"]),
                    "down": int(los["votes"]["down"] + 1)
                }
            }
        })

    return win_query, los_query

if __name__ == "__main__":
    # Testing

    content_a = {
        "_id": "5dbb5523b30b47013588f96d",
        "votes":{
            "total": 0,
            "elo": 0,
            "up": 0,
            "down": 0
        }
    }

    content_b = {
        "_id": "5dbc82230877d84fea001646",
        "votes":{
            "total": 0,
            "elo": 0,
            "up": 0,
            "down": 0
        }
    }

    # Content A won
    query_a, query_b = update_elo(content_a, content_b)
    
    print(query_a)
    print(query_b)
