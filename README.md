# 🎬 Movie Ratings App (MongoDB Project)

## 📌 Overview
This project is a MongoDB-based application that allows users to rate movies and analyze ratings using aggregation queries.

The system demonstrates key MongoDB concepts:
- CRUD operations
- Aggregation Framework
- Indexing

---

## 🧱 Database Design

The database consists of three main collections:

### 1. users
Stores user information:
- username
- email
- fullName
- isActive
- createdAt

### 2. movies
Stores movie data:
- title
- genre
- releaseYear
- director
- durationMinutes
- createdAt

### 3. ratings
Acts as a bridge between users and movies:
- userId
- movieId
- rating (1–10)
- comment
- createdAt
- updatedAt

📌 Relationship:
- One user → many ratings
- One movie → many ratings
- Users ↔ Movies = many-to-many (via ratings)

---

## ⚙️ Features

### CRUD Operations
- Add, edit, delete movies
- Manage users
- Create and update ratings

### Aggregations
- Average rating per movie
- Top 5 movies
- Ratings for selected movie (with user info)
- Average rating by director
- Ratings by active users
- Average rating by genre

### Indexing
Implemented indexes:
- userId + movieId (compound)
- movieId + rating (compound)
- movieId
- email
- default _id index

---

## 🖥️ Application

The UI is built using **Streamlit** and allows:
- Full interaction with the database
- Running aggregation queries
- Demonstrating index usage via explain()

---

## 🚀 How to Run

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
