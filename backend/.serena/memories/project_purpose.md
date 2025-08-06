# GSGUI Backend - Purpose and Overview

## Project Purpose
GSGUI Backend is a FastAPI-based REST API and WebSocket server designed to interface with the GuruShots photography platform. It provides automated strategies for participating in photography challenges including:

- **Voting automation**: Automated voting on photo challenges
- **Turbo management**: Automated execution of turbo boosts with sophisticated algorithms
- **Strategy scheduling**: Automated timing of when to enter challenges, vote, fill meters, swap photos
- **Real-time monitoring**: WebSocket connections for live updates on challenge activities

## Key Features
- **Challenge Management**: Monitor and participate in photography challenges
- **Voting System**: Automated voting with fill meter management
- **Turbo Algorithms**: Sophisticated algorithms for optimal turbo usage timing
- **Strategy Scheduler**: Automated execution of complex timing strategies (like those described by ANCA the vampire)
- **WebSocket Support**: Real-time updates and notifications
- **File-based persistence**: Uses .ini files for configuration and data storage

## Migration Context
This project refactors and extracts backend logic from an existing `gsui.py` monolithic application, creating a clean API interface while maintaining compatibility with existing data formats.

## Target Users
Players of GuruShots who want to automate and optimize their participation in photography challenges using advanced strategies.