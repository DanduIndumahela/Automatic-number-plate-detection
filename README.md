# Automatic-number-plate-detection
Automatic Number Plate Recognition (ANPR) & Vehicle Tracking System
📌 Project Overview

The Automatic Number Plate Recognition (ANPR) & Vehicle Tracking System is a real-time computer vision application that detects vehicle number plates from CCTV/video footage, extracts registration numbers using OCR, stores vehicle records in a database, and tracks vehicle movement across multiple camera locations. The system also supports theft vehicle monitoring and automated email alerts for enhanced security and surveillance.

✨ Features
Real-time vehicle number plate detection using YOLO.
Optical Character Recognition (OCR) for extracting vehicle registration numbers.
Image preprocessing to improve recognition accuracy.
Multi-camera vehicle tracking and route analysis.
Vehicle detection history with timestamp logging.
Theft vehicle monitoring and search functionality.
Automated email notifications upon vehicle detection.
User and Admin authentication system.
Database storage for vehicle logs and user information.
Interactive web dashboard using Streamlit.
🛠️ Technologies Used
Programming Language
Python
Computer Vision & Deep Learning
OpenCV
YOLO (You Only Look Once)
OCR
EasyOCR
Web Framework
Streamlit
Database
SQLite
Notification Service
SMTP Email Service
Configuration
JSON
🏗️ System Architecture
Video Input
     ↓
YOLO Number Plate Detection
     ↓
Plate Cropping
     ↓
Image Preprocessing
     ↓
EasyOCR Text Recognition
     ↓
Vehicle Number Extraction
     ↓
Database Storage
     ↓
Vehicle Tracking & Search
     ↓
Email Alert Generation
📂 Project Modules
1. Number Plate Detection

Detects vehicle number plates from images and video streams using YOLO object detection.

2. OCR Recognition

Extracts text from detected number plates using EasyOCR.

3. Image Preprocessing

Improves OCR accuracy through:

Grayscale Conversion
Bilateral Filtering
Adaptive Thresholding
Image Resizing
4. Vehicle Tracking

Tracks vehicle movement across multiple connected cameras using timestamps and location data.

5. Database Management

Stores:

Vehicle Numbers
Detection Time
Camera Location
User Information
6. Alert System

Sends automated email notifications when a tracked vehicle is detected.

🚀 Applications
Smart Traffic Management
Toll Booth Automation
Parking Management Systems
Law Enforcement & Surveillance
Stolen Vehicle Detection
Smart City Infrastructure
📊 Key Highlights
Real-time ANPR using Deep Learning.
Multi-camera vehicle tracking.
OCR-based text extraction.
Automated email alert system.
Efficient database management.
User-friendly web interface.
📈 Future Enhancements
Integration with cloud databases.
Real-time live CCTV monitoring.
Mobile application support.
Higher accuracy using advanced OCR models.
GPS-based vehicle tracking integration.
Deployment on edge devices for smart city applications.
👨‍💻 My Role & Contributions
Developed the ANPR pipeline using YOLO, OpenCV, and EasyOCR.
Built the web-based dashboard using Streamlit.
Implemented vehicle tracking and database management using SQLite.
Integrated automated email notification functionality.
Optimized image preprocessing techniques to improve OCR performance.
📋 Resume Highlights
Developed a real-time vehicle tracking system using Python, YOLO, OpenCV, and EasyOCR to detect vehicle number plates and accurately extract registration numbers from CCTV footage.
Built an intelligent tracking and alert platform using Streamlit, SQLite, and SMTP Email Services for multi-camera vehicle monitoring, theft detection, database logging, and automated notifications.
📜 License

This project is developed for educational and research purposes.
