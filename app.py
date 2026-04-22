import os
from datetime import datetime
from pprint import pformat
from typing import Any, Dict, List

import streamlit as st
from dotenv import load_dotenv
from bson import ObjectId

from utils.db import get_database
from utils.helpers import (
    ensure_indexes,
    format_dataframe,
    parse_genres,
    serialize_docs,
)

load_dotenv()

st.set_page_config(page_title="Movie Ratings App", page_icon="🎬", layout="wide")

DB_NAME = os.getenv("MONGO_DB_NAME", "movieRatingsDB")


@st.cache_resource(show_spinner=False)
def init_db():
    db = get_database()
    ensure_indexes(db)
    return db


try:
    db = init_db()
    movies_col = db["movies"]
    users_col = db["users"]
    ratings_col = db["ratings"]
    connection_ok = True
except Exception as exc:
    connection_ok = False
    db = None
    movies_col = None
    users_col = None
    ratings_col = None
    connection_error = str(exc)


st.title("🎬 Movie Ratings App")
st.caption("Python UI for MongoDB: CRUD operations, aggregations, and index demonstrations")

with st.sidebar:
    st.header("Connection")
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    st.code(f"MONGO_URI={mongo_uri}\nMONGO_DB_NAME={DB_NAME}", language="bash")
    if connection_ok:
        st.success("Connected to MongoDB successfully")
    else:
        st.error("MongoDB initialization error")
        st.write(connection_error)

if not connection_ok:
    st.stop()


def movie_options() -> Dict[str, str]:
    docs = list(movies_col.find({}, {"title": 1}).sort("title", 1))
    return {f"{doc['title']} ({str(doc['_id'])})": str(doc["_id"]) for doc in docs}


def user_options() -> Dict[str, str]:
    docs = list(users_col.find({}, {"username": 1, "fullName": 1}).sort("username", 1))
    return {
        f"{doc['username']} - {doc.get('fullName', '')} ({str(doc['_id'])})": str(doc["_id"])
        for doc in docs
    }


def get_index_summary(explain_doc: Dict[str, Any]) -> Dict[str, Any]:
    query_planner = explain_doc.get("queryPlanner", {})
    winning_plan = query_planner.get("winningPlan", {})
    plan_text = pformat(winning_plan, width=100)

    plan_text_upper = plan_text.upper()

    used_index = "IXSCAN" in plan_text_upper or "EXPRESS_IXSCAN" in plan_text_upper
    detected_indexes = []

    known_index_names = [
        "_id_",
        "userId_1_movieId_1",
        "movieId_1_rating_-1",
        "movieId_1",
        "email_1",
        "username_1",
        "movie_title_unique_idx",
    ]

    for idx_name in known_index_names:
        if idx_name in plan_text:
            detected_indexes.append(idx_name)

    return {
        "used_index": used_index,
        "detected_indexes": detected_indexes,
        "winning_plan": winning_plan,
        "raw_explain": explain_doc,
    }


def show_explain_block(explain_doc: Dict[str, Any]):
    info = get_index_summary(explain_doc)

    if info["used_index"]:
        st.success("Index usage detected in the execution plan.")
    else:
        st.warning("No index scan was clearly detected in the execution plan.")

    if info["detected_indexes"]:
        st.write("Detected index name(s):")
        st.code(", ".join(info["detected_indexes"]))
    else:
        st.write("Detected index name(s): not explicitly identified from the plan text")

    st.write("Winning plan:")
    st.code(pformat(info["winning_plan"], width=100), language="python")


def section_movies():
    st.subheader("Movies CRUD")
    tab_list, tab_create, tab_update, tab_delete = st.tabs(["View", "Add", "Edit", "Delete"])

    with tab_list:
        search = st.text_input("Search by title or director")
        query: Dict[str, Any] = {}
        if search:
            query = {
                "$or": [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"director": {"$regex": search, "$options": "i"}},
                ]
            }
        docs = list(movies_col.find(query).sort("title", 1))
        st.dataframe(format_dataframe(serialize_docs(docs)), use_container_width=True)

    with tab_create:
        with st.form("create_movie"):
            title = st.text_input("Title")
            genre_text = st.text_input("Genres (e.g. Sci-Fi, Drama)")
            release_year = st.number_input("Release year", min_value=1888, max_value=2100, value=2020, step=1)
            director = st.text_input("Director")
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=500, value=120, step=1)
            submitted = st.form_submit_button("Add movie")
            if submitted:
                if not title.strip() or not director.strip() or not genre_text.strip():
                    st.error("Please fill in the title, genres, and director fields.")
                else:
                    doc = {
                        "title": title.strip(),
                        "genre": parse_genres(genre_text),
                        "releaseYear": int(release_year),
                        "director": director.strip(),
                        "durationMinutes": int(duration),
                        "createdAt": datetime.utcnow(),
                    }
                    result = movies_col.insert_one(doc)
                    st.success(f"Movie added successfully. _id={result.inserted_id}")

    with tab_update:
        options = movie_options()
        if not options:
            st.info("There are no movies to edit.")
        else:
            selected_label = st.selectbox("Select a movie", list(options.keys()))
            selected_id = ObjectId(options[selected_label])
            movie = movies_col.find_one({"_id": selected_id})
            with st.form("update_movie"):
                title = st.text_input("Title", value=movie.get("title", ""))
                genre_text = st.text_input("Genres", value=", ".join(movie.get("genre", [])))
                release_year = st.number_input(
                    "Release year",
                    min_value=1888,
                    max_value=2100,
                    value=int(movie.get("releaseYear", 2020)),
                    step=1,
                )
                director = st.text_input("Director", value=movie.get("director", ""))
                duration = st.number_input(
                    "Duration (minutes)",
                    min_value=1,
                    max_value=500,
                    value=int(movie.get("durationMinutes", 120)),
                    step=1,
                )
                submitted = st.form_submit_button("Save changes")
                if submitted:
                    update_doc = {
                        "title": title.strip(),
                        "genre": parse_genres(genre_text),
                        "releaseYear": int(release_year),
                        "director": director.strip(),
                        "durationMinutes": int(duration),
                    }
                    movies_col.update_one({"_id": selected_id}, {"$set": update_doc})
                    st.success("Movie updated successfully.")

    with tab_delete:
        options = movie_options()
        if not options:
            st.info("There are no movies to delete.")
        else:
            selected_label = st.selectbox("Select a movie to delete", list(options.keys()), key="delete_movie_box")
            selected_id = ObjectId(options[selected_label])
            cascade = st.checkbox("Also delete all ratings for this movie")
            if st.button("Delete movie", type="primary"):
                movies_col.delete_one({"_id": selected_id})
                deleted_ratings = 0
                if cascade:
                    deleted_ratings = ratings_col.delete_many({"movieId": selected_id}).deleted_count
                st.success(f"Movie deleted successfully. Deleted ratings: {deleted_ratings}")


def section_users():
    st.subheader("Users CRUD")
    tab_list, tab_create, tab_update, tab_delete = st.tabs(["View", "Add", "Edit", "Delete"])

    with tab_list:
        only_active = st.checkbox("Show active users only")
        query = {"isActive": True} if only_active else {}
        docs = list(users_col.find(query).sort("username", 1))
        st.dataframe(format_dataframe(serialize_docs(docs)), use_container_width=True)

    with tab_create:
        with st.form("create_user"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            full_name = st.text_input("Full name")
            is_active = st.checkbox("Active", value=True)
            submitted = st.form_submit_button("Add user")
            if submitted:
                if not username.strip() or not email.strip() or not full_name.strip():
                    st.error("Please fill in the username, email, and full name fields.")
                else:
                    doc = {
                        "username": username.strip(),
                        "email": email.strip(),
                        "fullName": full_name.strip(),
                        "createdAt": datetime.utcnow(),
                        "isActive": bool(is_active),
                    }
                    result = users_col.insert_one(doc)
                    st.success(f"User added successfully. _id={result.inserted_id}")

    with tab_update:
        options = user_options()
        if not options:
            st.info("There are no users to edit.")
        else:
            selected_label = st.selectbox("Select a user", list(options.keys()))
            selected_id = ObjectId(options[selected_label])
            user = users_col.find_one({"_id": selected_id})
            with st.form("update_user"):
                username = st.text_input("Username", value=user.get("username", ""))
                email = st.text_input("Email", value=user.get("email", ""))
                full_name = st.text_input("Full name", value=user.get("fullName", ""))
                is_active = st.checkbox("Active", value=bool(user.get("isActive", True)))
                submitted = st.form_submit_button("Save changes")
                if submitted:
                    update_doc = {
                        "username": username.strip(),
                        "email": email.strip(),
                        "fullName": full_name.strip(),
                        "isActive": bool(is_active),
                    }
                    users_col.update_one({"_id": selected_id}, {"$set": update_doc})
                    st.success("User updated successfully.")

    with tab_delete:
        options = user_options()
        if not options:
            st.info("There are no users to delete.")
        else:
            selected_label = st.selectbox("Select a user to delete", list(options.keys()), key="delete_user_box")
            selected_id = ObjectId(options[selected_label])
            cascade = st.checkbox("Also delete all ratings created by this user")
            if st.button("Delete user", type="primary"):
                users_col.delete_one({"_id": selected_id})
                deleted_ratings = 0
                if cascade:
                    deleted_ratings = ratings_col.delete_many({"userId": selected_id}).deleted_count
                st.success(f"User deleted successfully. Deleted ratings: {deleted_ratings}")


def section_ratings():
    st.subheader("Ratings CRUD")
    tab_list, tab_create, tab_update, tab_delete = st.tabs(["View", "Add", "Edit", "Delete"])

    with tab_list:
        movie_map = movie_options()
        selected_movie = st.selectbox("Filter by movie", ["All"] + list(movie_map.keys()))
        query = {}
        if selected_movie != "All":
            query["movieId"] = ObjectId(movie_map[selected_movie])

        docs = list(ratings_col.find(query).sort("createdAt", -1).limit(200))
        rows = []
        for doc in docs:
            movie = movies_col.find_one({"_id": doc["movieId"]}, {"title": 1})
            user = users_col.find_one({"_id": doc["userId"]}, {"username": 1, "fullName": 1})
            rows.append(
                {
                    "_id": str(doc["_id"]),
                    "movie": movie.get("title") if movie else str(doc["movieId"]),
                    "user": user.get("username") if user else str(doc["userId"]),
                    "rating": doc.get("rating"),
                    "comment": doc.get("comment", ""),
                    "createdAt": doc.get("createdAt"),
                    "updatedAt": doc.get("updatedAt"),
                }
            )
        st.dataframe(format_dataframe(rows), use_container_width=True)

    with tab_create:
        movie_map = movie_options()
        user_map = user_options()
        if not movie_map or not user_map:
            st.info("At least one movie and one user are required.")
        else:
            with st.form("create_rating"):
                selected_movie = st.selectbox("Movie", list(movie_map.keys()))
                selected_user = st.selectbox("User", list(user_map.keys()))
                rating = st.slider("Rating", min_value=1, max_value=10, value=8)
                comment = st.text_area("Comment")
                submitted = st.form_submit_button("Add rating")
                if submitted:
                    now = datetime.utcnow()
                    doc = {
                        "userId": ObjectId(user_map[selected_user]),
                        "movieId": ObjectId(movie_map[selected_movie]),
                        "rating": int(rating),
                        "comment": comment.strip(),
                        "createdAt": now,
                        "updatedAt": now,
                    }
                    result = ratings_col.insert_one(doc)
                    st.success(f"Rating added successfully. _id={result.inserted_id}")

    with tab_update:
        rating_docs = list(ratings_col.find({}).sort("createdAt", -1).limit(200))
        if not rating_docs:
            st.info("There are no ratings to edit.")
        else:
            rating_map = {}
            for doc in rating_docs:
                movie = movies_col.find_one({"_id": doc["movieId"]}, {"title": 1})
                user = users_col.find_one({"_id": doc["userId"]}, {"username": 1})
                label = f"{user.get('username', 'unknown')} -> {movie.get('title', 'unknown')} | {doc.get('rating')} | {str(doc['_id'])}"
                rating_map[label] = str(doc["_id"])

            selected_label = st.selectbox("Select a rating", list(rating_map.keys()))
            selected_id = ObjectId(rating_map[selected_label])
            rating_doc = ratings_col.find_one({"_id": selected_id})

            with st.form("update_rating"):
                rating_value = st.slider("Rating", min_value=1, max_value=10, value=int(rating_doc.get("rating", 8)))
                comment = st.text_area("Comment", value=rating_doc.get("comment", ""))
                submitted = st.form_submit_button("Save changes")
                if submitted:
                    ratings_col.update_one(
                        {"_id": selected_id},
                        {
                            "$set": {
                                "rating": int(rating_value),
                                "comment": comment.strip(),
                                "updatedAt": datetime.utcnow(),
                            }
                        },
                    )
                    st.success("Rating updated successfully.")

    with tab_delete:
        rating_docs = list(ratings_col.find({}).sort("createdAt", -1).limit(200))
        if not rating_docs:
            st.info("There are no ratings to delete.")
        else:
            rating_map = {}
            for doc in rating_docs:
                movie = movies_col.find_one({"_id": doc["movieId"]}, {"title": 1})
                user = users_col.find_one({"_id": doc["userId"]}, {"username": 1})
                label = f"{user.get('username', 'unknown')} -> {movie.get('title', 'unknown')} | {doc.get('rating')} | {str(doc['_id'])}"
                rating_map[label] = str(doc["_id"])

            selected_label = st.selectbox("Select a rating to delete", list(rating_map.keys()), key="delete_rating_box")
            selected_id = ObjectId(rating_map[selected_label])
            if st.button("Delete rating", type="primary"):
                ratings_col.delete_one({"_id": selected_id})
                st.success("Rating deleted successfully.")


def section_aggregations():
    st.subheader("Aggregation Queries")
    agg_choice = st.selectbox(
        "Choose an aggregation query:",
        [
            "Average rating for every movie",
            "Top 5 movies",
            "All ratings for selected movie with user info",
            "Average rating by director",
            "Ratings by active users",
            "Ratings by users with average given rating",
            "Average rating by genre",
            "Active vs inactive users",
        ],
    )

    if agg_choice == "Average rating for every movie":
        pipeline = [
            {
                "$group": {
                    "_id": "$movieId",
                    "avgRating": {"$avg": "$rating"},
                    "ratingsCount": {"$sum": 1}
                }
            },
            {
                "$lookup": {
                    "from": "movies",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "movieInfo"
                }
            },
            {"$unwind": "$movieInfo"},
            {
                "$project": {
                    "_id": 0,
                    "title": "$movieInfo.title",
                    "avgRating": {"$round": ["$avgRating", 2]},
                    "ratingsCount": 1
                }
            },
            {"$sort": {"avgRating": -1}}
        ]
        rows = list(ratings_col.aggregate(pipeline))
        st.code(str(pipeline), language="python")
        st.dataframe(format_dataframe(rows), use_container_width=True)

    elif agg_choice == "Top 5 movies":
        pipeline = [
            {
                "$group": {
                    "_id": "$movieId",
                    "avgRating": {"$avg": "$rating"},
                    "ratingsCount": {"$sum": 1}
                }
            },
            {
                "$match": {
                    "ratingsCount": {"$gte": 3}
                }
            },
            {
                "$lookup": {
                    "from": "movies",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "movieInfo"
                }
            },
            {"$unwind": "$movieInfo"},
            {
                "$project": {
                    "_id": 0,
                    "title": "$movieInfo.title",
                    "avgRating": {"$round": ["$avgRating", 2]},
                    "ratingsCount": 1
                }
            },
            {"$sort": {"avgRating": -1, "ratingsCount": -1}},
            {"$limit": 5}
        ]
        rows = list(ratings_col.aggregate(pipeline))
        st.code(str(pipeline), language="python")
        st.dataframe(format_dataframe(rows), use_container_width=True)


    elif agg_choice == "All ratings for selected movie with user info":

        options = movie_options()

        if not options:

            st.info("There are no movies.")

        else:

            selected_label = st.selectbox(

                "Select a movie",

                list(options.keys()),

                key="agg_selected_movie_with_users"

            )

            selected_id = ObjectId(options[selected_label])

            pipeline = [

                {

                    "$match": {

                        "movieId": selected_id

                    }

                },

                {

                    "$lookup": {

                        "from": "users",

                        "localField": "userId",

                        "foreignField": "_id",

                        "as": "userInfo"

                    }

                },

                {"$unwind": "$userInfo"},

                {

                    "$project": {

                        "_id": 0,

                        "username": "$userInfo.username",

                        "fullName": "$userInfo.fullName",

                        "rating": 1,

                        "comment": 1

                    }

                },

                {"$sort": {"rating": -1}}

            ]

            rows = list(ratings_col.aggregate(pipeline))

            st.code(str(pipeline), language="python")

            st.dataframe(format_dataframe(rows), use_container_width=True)

    elif agg_choice == "Average rating by director":
        pipeline = [
            {
                "$lookup": {
                    "from": "movies",
                    "localField": "movieId",
                    "foreignField": "_id",
                    "as": "movieInfo"
                }
            },
            {"$unwind": "$movieInfo"},
            {
                "$group": {
                    "_id": "$movieInfo.director",
                    "avgDirectorRating": {"$avg": "$rating"},
                    "totalRatings": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "director": "$_id",
                    "avgDirectorRating": {"$round": ["$avgDirectorRating", 2]},
                    "totalRatings": 1
                }
            },
            {"$sort": {"avgDirectorRating": -1}}
        ]
        rows = list(ratings_col.aggregate(pipeline))
        st.code(str(pipeline), language="python")
        st.dataframe(format_dataframe(rows), use_container_width=True)

    elif agg_choice == "Ratings by active users":
        pipeline = [
            {
                "$lookup": {
                    "from": "users",
                    "localField": "userId",
                    "foreignField": "_id",
                    "as": "userInfo"
                }
            },
            {"$unwind": "$userInfo"},
            {
                "$match": {
                    "userInfo.isActive": True
                }
            },
            {
                "$group": {
                    "_id": "$movieId",
                    "avgRating": {"$avg": "$rating"},
                    "ratingsCount": {"$sum": 1}
                }
            },
            {
                "$lookup": {
                    "from": "movies",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "movieInfo"
                }
            },
            {"$unwind": "$movieInfo"},
            {
                "$project": {
                    "_id": 0,
                    "title": "$movieInfo.title",
                    "avgRating": {"$round": ["$avgRating", 2]},
                    "ratingsCount": 1
                }
            },
            {"$sort": {"avgRating": -1}}
        ]
        rows = list(ratings_col.aggregate(pipeline))
        st.code(str(pipeline), language="python")
        st.dataframe(format_dataframe(rows), use_container_width=True)

    elif agg_choice == "Ratings by users with average given rating":
        pipeline = [
            {
                "$group": {
                    "_id": "$userId",
                    "totalRatingsGiven": {"$sum": 1},
                    "avgGivenRating": {"$avg": "$rating"}
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "userInfo"
                }
            },
            {"$unwind": "$userInfo"},
            {
                "$project": {
                    "_id": 0,
                    "username": "$userInfo.username",
                    "fullName": "$userInfo.fullName",
                    "totalRatingsGiven": 1,
                    "avgGivenRating": {"$round": ["$avgGivenRating", 2]}
                }
            },
            {"$sort": {"totalRatingsGiven": -1, "avgGivenRating": -1}}
        ]
        rows = list(ratings_col.aggregate(pipeline))
        st.code(str(pipeline), language="python")
        st.dataframe(format_dataframe(rows), use_container_width=True)

    elif agg_choice == "Average rating by genre":
        pipeline = [
            {
                "$lookup": {
                    "from": "movies",
                    "localField": "movieId",
                    "foreignField": "_id",
                    "as": "movieInfo"
                }
            },
            {"$unwind": "$movieInfo"},
            {"$unwind": "$movieInfo.genre"},
            {
                "$group": {
                    "_id": "$movieInfo.genre",
                    "avgRating": {"$avg": "$rating"},
                    "totalRatings": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "genre": "$_id",
                    "avgRating": {"$round": ["$avgRating", 2]},
                    "totalRatings": 1
                }
            },
            {"$sort": {"avgRating": -1}}
        ]
        rows = list(ratings_col.aggregate(pipeline))
        st.code(str(pipeline), language="python")
        st.dataframe(format_dataframe(rows), use_container_width=True)

    elif agg_choice == "Active vs inactive users":
        pipeline = [
            {
                "$group": {
                    "_id": "$isActive",
                    "totalUsers": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "status": {
                        "$cond": [{"$eq": ["$_id", True]}, "Active", "Inactive"]
                    },
                    "totalUsers": 1
                }
            }
        ]
        rows = list(users_col.aggregate(pipeline))
        st.code(str(pipeline), language="python")
        st.dataframe(format_dataframe(rows), use_container_width=True)


def section_index_demo():
    st.subheader("Index Demonstration")
    st.caption("These examples demonstrate how MongoDB indexes optimize specific queries.")

    demo_choice = st.selectbox(
        "Choose an index demo:",
        [
            "ratings: userId + movieId compound index",
            "ratings: movieId + rating compound index",
            "movies: _id index",
            "ratings: movieId index",
            "users: email_1 index",
        ],
    )

    if demo_choice == "ratings: userId + movieId compound index":
        query = {
            "userId": ObjectId("67f01a9c3e4b8d12af90c101"),
            "movieId": ObjectId("67f0201a1bc34d5e6f701111")
        }
        mongo_query = """db.ratings.find(
{
  userId: ObjectId("67f01a9c3e4b8d12af90c101"),
  movieId: ObjectId("67f0201a1bc34d5e6f701111")
}
)"""
        results = list(ratings_col.find(query))
        explain_doc = ratings_col.find(query).hint("userId_1_movieId_1").explain()

        st.write("Expected index: `userId_1_movieId_1`")
        st.code(mongo_query, language="javascript")
        st.dataframe(format_dataframe(serialize_docs(results)), use_container_width=True)
        show_explain_block(explain_doc)

    elif demo_choice == "ratings: movieId + rating compound index":
        query = {"movieId": ObjectId("67f0202b2cd45e6f7a812222")}
        mongo_query = """db.ratings.find(
{ movieId: ObjectId("67f0202b2cd45e6f7a812222") }
).sort({ rating: -1 })"""
        results = list(ratings_col.find(query).sort("rating", -1))
        explain_doc = ratings_col.find(query).sort("rating", -1).hint("movieId_1_rating_-1").explain()

        st.write("Expected index: `movieId_1_rating_-1`")
        st.code(mongo_query, language="javascript")
        st.dataframe(format_dataframe(serialize_docs(results)), use_container_width=True)
        show_explain_block(explain_doc)

    elif demo_choice == "movies: _id index":
        query = {"_id": ObjectId("67f0201a1bc34d5e6f701111")}
        mongo_query = """db.movies.find(
{ _id: ObjectId("67f0201a1bc34d5e6f701111") }
)"""
        results = list(movies_col.find(query))
        explain_doc = movies_col.find(query).explain()

        st.write("Expected index: `_id_`")
        st.code(mongo_query, language="javascript")
        st.dataframe(format_dataframe(serialize_docs(results)), use_container_width=True)
        show_explain_block(explain_doc)

    elif demo_choice == "ratings: movieId index":
        query = {"movieId": ObjectId("67f0201a1bc34d5e6f701111")}
        mongo_query = """db.ratings.find(
{ movieId: ObjectId("67f0201a1bc34d5e6f701111") }
)"""
        results = list(ratings_col.find(query))
        explain_doc = ratings_col.find(query).hint("movieId_1").explain()

        st.write("Expected index: `movieId_1`")
        st.code(mongo_query, language="javascript")
        st.dataframe(format_dataframe(serialize_docs(results)), use_container_width=True)
        show_explain_block(explain_doc)

    elif demo_choice == "users: email_1 index":
        query = {"email": "maria02@example.com"}
        mongo_query = """db.users.find(
{ email: "maria02@example.com" }
)"""
        results = list(users_col.find(query))
        explain_doc = users_col.find(query).hint("email_1").explain()

        st.write("Expected index: `email_1`")
        st.code(mongo_query, language="javascript")
        st.dataframe(format_dataframe(serialize_docs(results)), use_container_width=True)
        show_explain_block(explain_doc)

    with st.expander("Show all indexes in the database"):
        movie_indexes = list(movies_col.list_indexes())
        user_indexes = list(users_col.list_indexes())
        rating_indexes = list(ratings_col.list_indexes())

        st.write("Movies indexes")
        st.dataframe(format_dataframe(serialize_docs(movie_indexes)), use_container_width=True)

        st.write("Users indexes")
        st.dataframe(format_dataframe(serialize_docs(user_indexes)), use_container_width=True)

        st.write("Ratings indexes")
        st.dataframe(format_dataframe(serialize_docs(rating_indexes)), use_container_width=True)


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Movies", "Users", "Ratings", "Aggregations", "Index Demo"]
)

with tab1:
    section_movies()
with tab2:
    section_users()
with tab3:
    section_ratings()
with tab4:
    section_aggregations()
with tab5:
    section_index_demo()