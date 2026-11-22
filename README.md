# BASIRA

**Basira** is an AI and LiDAR-assisted obstacle-awareness prototype for people with visual impairment.

The system combines an iPhone application with LiDAR depth sensing and a MacBook-based AI service. The iPhone captures the live scene and depth data, while the MacBook runs real-time object detection and returns recognized objects over the local network.

> Basira is a graduation-project prototype intended for controlled evaluation and accessibility research.

## Current capabilities

- Live iPhone camera and LiDAR distance reading
- Local network connection between iPhone and MacBook
- Automatic discovery of the Mac AI service on the same Wi-Fi network
- Real-time detection of common objects using a pre-trained YOLO model
- iPhone interface for connection, distance, and AI results
- Mac dashboard and local live-analysis bridge

## Architecture

```text
iPhone (camera + LiDAR)
        │ local Wi-Fi
        ▼
Mac AI service (FastAPI + YOLO)
        │ object labels
        ▼
Basira Camera interface
```

## Repository layout

```text
basira/             Python AI, camera, depth, and live-bridge modules
ios/BasiraCamera/   iPhone application source
run_live_bridge.py  Starts the local iPhone ↔ Mac bridge
run_dashboard.py    Starts the Mac dashboard
requirements.txt    Python dependencies
```

## Run the Mac AI service

Create a Python environment, install the dependencies, then run:

```bash
python3 run_live_bridge.py
```

The iPhone and MacBook must be on the same Wi-Fi network. The iPhone application automatically discovers the local service.

## iPhone project

Open `ios/BasiraCamera/BasiraCamera.xcodeproj` in Xcode. Before building, select your own Apple development team and a unique bundle identifier in the project signing settings.

## Planned expansion

- Match each recognized object with its LiDAR distance and direction
- Add general-obstacle detection from depth data
- Add Arabic audio and haptic feedback
- Train custom classes such as doors, stairs, railings, trees, poles, sidewalks, and pedestrian crossings
- Evaluate detection quality, distance error, latency, and user experience
