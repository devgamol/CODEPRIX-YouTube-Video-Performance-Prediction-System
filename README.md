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
