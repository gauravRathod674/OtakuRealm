# Assignment 1 – Concepts Integral to OtakuRealm

**Name:** Gaurav Rathod  
**Project Name:** OtakuRealm  
**Submission Date:** 27th July 2025

---

## 📌 Context

OtakuRealm is a full-stack anime and manga streaming platform built using `Next.js` and `Django-Ninja`. The platform enables users to watch anime, read manga, track watch history, and interact with an AI-powered chatbot. The system handles authentication, user personalization, dynamic data scraping, and natural language query processing via the chatbot.

---

## 📦 Key Concepts (Object - Context - Information)

### 1. `User`
- **Context:** Manages personal data and authentication.
- **Information:**
  - Fields: `id`, `username`, `email`, `password`, `profileData`
  - Actions: Register, Login, Logout, Update Profile
  - Associations: `Authentication`, `WatchHistory`, `Chatbot`

---

### 2. `Authentication`
- **Context:** Manages secure access via JWT tokens.
- **Information:**
  - Functions: `generateJWT`, `verifyToken`, `enforceExpiry`
  - Linked to: `User`

---

### 3. `BaseContent`
- **Context:** Abstract base class for both anime and manga.
- **Information:**
  - Fields: `id`, `title`, `genre`, `description`, `source`
  - Methods: `getContentMetaData()`

---

### 4. `Anime` (inherits from `BaseContent`)
- **Context:** Anime-specific media type.
- **Information:**
  - Fields: `episodes`, `releaseDate`, `rating`
  - Methods: `getEpisodes()`, `getDetails()`
  - Associations: `AnimeScraper`, `WatchHistory`

---

### 5. `Manga` (inherits from `BaseContent`)
- **Context:** Manga-specific media type.
- **Information:**
  - Fields: `chapters`, `volumeCount`
  - Methods: `getChapters()`, `getDetails()`
  - Associations: `MangaScraper`, `WatchHistory`

---

### 6. `AnimeScraper`
- **Context:** Scrapes anime metadata from third-party websites.
- **Information:**
  - Functions: `fetchAnimeByID()`, `searchAnime()`
  - Depends on: `External HTTP/HTML Libraries`
  - Outputs: `Anime` objects

---

### 7. `MangaScraper`
- **Context:** Scrapes manga metadata from third-party sources.
- **Information:**
  - Functions: `fetchMangaByID()`, `searchManga()`
  - Depends on: `External HTTP/HTML Libraries`
  - Outputs: `Manga` objects

---

### 8. `WatchHistory`
- **Context:** Tracks user’s progress on anime/manga.
- **Information:**
  - Fields: `animeID`, `episodeNumber`, `mangaID`, `chapterNumber`, `lastUpdated`
  - Methods: `updateProgress()`
  - Linked to: `User`, `Anime`, `Manga`

---

### 9. `Chatbot`
- **Context:** Interacts with user queries using NLP.
- **Information:**
  - Functions: `processUserQuery()`, `recommendContent()`, `updateKnowledgeBase()`
  - Dependencies: `External NLP APIs`, `Anime`, `Manga`, `User`
  - Features: Handles natural language, recommendation, Q&A

---


