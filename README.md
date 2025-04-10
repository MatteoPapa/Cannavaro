# Project Name

A brief description of your project goes here.

## Overview

This project consists of two main parts:

- **Backend:** A Python application located in the `backend` folder.
- **Frontend:** A React-based application located in the `frontend` folder.

## Getting Started

Follow these instructions to get both the backend and frontend running.

### Prerequisites

- **Backend:** Python 3.x installed.
- **Frontend:** Node.js (with npm) installed.

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git
cd <repository-name>
```

#### 2. Setup the Backend

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the backend application:
   ```bash
   python app.py
   ```
   The backend server will start on port **7001**.

#### 3. Setup the Frontend

1. Open a new terminal window/tab.
2. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
3. Install required dependencies:
   ```bash
   npm install
   ```
4. Run the frontend application:
   ```bash
   npm run dev
   ```
   The frontend development server will start on port **7000**.

## Usage

After starting both the backend and frontend servers, you can access the frontend via your browser at:
```
http://localhost:7000
```
The frontend will automatically communicate with the backend running on:
```
http://localhost:7001
```
