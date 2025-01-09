# Timeular Tracker GUI

A Python-based graphical user interface (GUI) for managing and monitoring a Timeular Tracker. This application provides real-time updates for battery and charging status, orientation tracking, and device information.

## Features

- **Device Management**:
  - Scan for available devices.
  - Connect to and disconnect from the Timeular Tracker.

- **Tracker Monitoring**:
  - Display current battery level.
  - Detect and show charging status.
  - Recognize tracker orientation and start/stop a timer accordingly.

- **Device Information**:
  - Retrieve device details like model number, serial number, hardware and software versions.
  - Display device information in a footer.

- **Real-Time Updates**:
  - Continuous updates for battery, charging, and device details without freezing the GUI.
 
## Screenshot

![Screenshot-App](https://static.purin.at/wp-content/uploads/2025/01/timeular-python-app.png)

## ToDo
  - Translations (DE/EN)
  - SQL connection for device sync
  - Better solution for Power cycle / update
  - Better code sturcture
  - Better UI
  - Better Log

## Installation

### Requirements

- Python 3.8 or higher
- Dependencies:
  - `bleak` for Bluetooth communication
  - `tkcalendar` for Calendar
  - `tkinter` for the GUI (usually included with Python installations)

### Setup

1. **Clone the Repository**:
   ```
   git clone https://github.com/stoffl6781/timeular-tracker-gui.git
   ```

3. **Install Dependencies**

### Usage

1. **Launch the Application:**
    ```
    python timeular-gui.py
    ```

2. **Connect to a Device:**
  Click "Scan" to search for available devices.
  Select the Timeular Tracker from the list and click "Connect".

3. **Monitor and Use:**
  View battery level and charging status.
  Start and stop the timer based on tracker orientation.
  Display device information in the footer.

4. **Disconnect:**
  Click "Disconnect" to safely terminate the connection to the tracker.


### License
This project is licensed under the GNU Public License.
