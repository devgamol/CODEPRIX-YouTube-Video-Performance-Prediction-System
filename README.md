# Video Insight AI

## Introduction

Video Insight AI is an AI-driven video analysis system designed to evaluate the performance of short-form video content by analyzing visual motion, audio signals, and engagement patterns. It identifies weak segments within a video and generates actionable suggestions to improve viewer retention and overall content quality. Built with a **React** frontend and a **FastAPI** backend, the system focuses on modular design, efficient local processing, and interpretable insights without relying on external cloud-based computation.

---

## Project Overview

<img width="1761" height="912" alt="video_analyzer" src="https://github.com/user-attachments/assets/1a1b86df-9b3a-4fae-986c-cfd8251c5e34" />


- Modular pipeline for analyzing video performance end-to-end  
- Processes input video through:
  - Motion analysis (visual activity)  
  - Audio analysis (energy and silence)  
  - Retention estimation (engagement approximation)  
  - Suggestion generation (issues and fixes)  
- Combines all outputs into a structured analysis result  
- Detects low-engagement segments and explains causes   

________________________________________________________________________________________________________
## Features

### - Video Retention Analysis
Analyzes frame-level visual changes to estimate viewer engagement across the video timeline.

### - Weak Segment Detection
Identifies low-engagement segments based on motion, audio energy, and retention patterns.

### - Intelligent Suggestion Engine
Generates actionable suggestions with clear issue identification and recommended fixes.

### - Audio Signal Processing
Extracts audio features such as energy levels and silence to detect engagement drops.

### - Timeline Heatmap Visualization
Provides a visual representation of engagement intensity across different time segments.

### - Exportable Analysis Report
Allows users to download structured analysis results in PDF format for further use.

### - Modular Processing Pipeline
Structured backend design with independent modules for video, audio, retention, and suggestions.

________________________________________________________________________________________________________

## Tech Stack

### Frontend
- React (Vite)
- Tailwind CSS

### Backend
- FastAPI
- Uvicorn

### Database
- MongoDB
- PyMongo

### Video & Audio Processing
- OpenCV
- NumPy
- MoviePy
- Librosa
- OpenAI Whisper

### Environment & Utilities
- python-dotenv

---

## Installation

Follow these steps to set up Video Insight AI locally:

### Backend Setup

1. Clone the repository:
```bash
git clone https://github.com/devgamol/CODEPRIX-YouTube-Video-Performance-Prediction-System.git
cd BACKEND
````

2. Create and activate virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables:
   Create a `.env` file inside the BACKEND folder:

```env
MONGO_URI=your_mongo_uri
DB_NAME=video_ai
SECRET_KEY=your_secret_key
```

5. Run the backend server:

```bash
uvicorn main:app --reload
```

---

### Frontend Setup

1. Navigate to frontend:

```bash
cd FRONTEND
```

2. Install dependencies:

```bash
npm install
```

3. Configure environment variables:
   Create a `.env` file inside the FRONTEND folder:

```env
VITE_API_BASE_URL=http://localhost:8000
```

4. Start the frontend:

```bash
npm run dev
```

5. Open in browser:

```
http://localhost:8080
```
---

## Contributing

We welcome contributions! To get started:

- Fork the repository on GitHub.
- Create a new branch for your feature or bugfix.
- Commit your changes with clear messages.
- Submit a pull request describing your changes.
