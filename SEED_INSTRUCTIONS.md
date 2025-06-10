## **1. Introduction**

This document outlines the software specification for a simple Python application designed to browse a gallery of interactive "Smart Reports."

### **1.1. Purpose**
The primary purpose of this application is to provide a user-friendly web interface for discovering and viewing interactive HTML reports. It will scan a designated directory, index the available reports, and present them in a gallery format. The application will also act as a web server to serve the reports and their associated resources.

### **1.2. Scope**
The application will be a lightweight, standalone web server built with Python and the Gradio library. Its core functionalities include:
* A web-based user interface (UI) for Browse reports.
* Automatic scanning and indexing of HTML report files from a configurable local directory.
* Serving the selected HTML reports and their linked resources (e.g., audio files, CSS, JavaScript).

### **1.3. Target Audience**
This application is intended for internal teams, such as business development, research, or data analysis, who need a simple way to share and access a collection of interactive reports.

***

## **2. Functional Requirements**

### **2.1. User Interface (UI)**

#### **2.1.1. Report Gallery**
* The application shall present a gallery view as its main interface.
* Each report in the gallery will be represented by a clickable element, such as a card or a button.
* The display name for each report in the gallery will be derived from its filename (e.g., "Navigating_The_Nexus_Q2_2025.html" will be displayed as "Navigating The Nexus Q2 2025").

#### **2.1.2. Report Viewing**
* When a user clicks on a report in the gallery, the corresponding HTML file will open in a new browser tab.
* The application must ensure that all relative paths to resources within the HTML file (e.g., `./Audio/file.mp3`) are correctly resolved and served by the application's web server.

### **2.2. Backend**

#### **2.2.1. Report Scanning and Indexing**
* On startup, the application must scan a specified directory for "Smart Reports."
* The default directory to scan is a folder named `Smart Reports` located at the project root. This path must be configurable.
* The scanner will recursively search the specified directory for HTML files (`.html`).
* For each HTML file found, the application will store its name and its file path.

#### **2.2.2. File Server**
* The application will run a web server to host the Gradio interface and serve the report files.
* The server must be capable of handling requests for the HTML report files and any other static assets referenced within them (e.g., audio files, images, CSS stylesheets). This is crucial for reports like "Navigating_The_Nexus_Q2_2025.html" that may link to files in an adjacent `Audio` directory.

#### **2.2.3. Configuration**
* The path to the "Smart Reports" directory will be configurable via a settings file or an environment variable. The default path will be `./Smart Reports/`.

***

## **3. System Architecture**

### **3.1. Application Structure**
The application will follow the directory structure provided:

```
/Business Development
|
|-- /app
|   |-- /utils
|   |   |-- __init__.py
|   |   |-- report_scanner.py  # Module for finding reports
|   |-- __init__.py
|   |-- main.py                # Main Gradio application logic
|
|-- /Smart Reports
|   |-- /Navigating The Nexus Q2 2025
|   |   |-- /Audio
|   |   |   |-- ... (audio files)
|   |   |-- Navigating_The_Nexus_Q2_2025.html
|   |   |-- Navigating_The_Nexus_Q2_2025.linkres
|
|-- .gitignore
```

### **3.2. Technology Stack**
* **Language:** Python 3.8+
* **UI Framework:** Gradio
* **Web Server:** The web server is provided by Gradio (which uses FastAPI).

***

## **4. Implementation Details (High-Level)**

### **4.1. Main Application Logic (`app/main.py`)**
* This file will contain the main Gradio application.
* It will import the report scanning utility to get the list of available reports.
* It will use `gr.Blocks()` to create the custom UI.
* A `gr.Gallery()` or a similar component will be used to display the reports.
* A key feature will be to make the `Smart Reports` directory available as a static path that Gradio can serve. This can be achieved using Gradio's `allowed_paths` or by mounting a static directory with the underlying FastAPI app.
* Each report in the gallery will link to its corresponding URL path on the server (e.g., `/file=Smart%20Reports/Navigating%20The%20Nexus%20Q2%202025/Navigating_The_Nexus_Q2_2025.html`).

### **4.2. Report Discovery (`app/utils/report_scanner.py`)**
* This module will have a function, e.g., `find_reports(directory)`, that takes the path to the `Smart Reports` directory as input.
* The function will use `os.walk()` or `pathlib.Path.rglob()` to recursively find all files ending with `.html`.
* It will return a list of dictionaries or custom objects, with each containing the report's display name and its file path.

### **4.3. Configuration**
A simple `config.py` file or environment variables can be used to manage the path to the `Smart Reports` directory.

## **5. Deployment**

### **5.1. Dependencies**
The application will require the following Python libraries, which can be listed in a `requirements.txt` file:
* `gradio`
* `python-dotenv` (optional, for managing environment variables)

### **5.2. Running the Application**
The application will be launched by running the main Python script from the command line:
```bash
python app/main.py
```
Upon execution, the console will display the local URL (e.g., `http://127.0.0.1:7860`) where the report gallery can be accessed.