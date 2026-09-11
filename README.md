# AI Accident Detection & Emergency Alert System

Initial Flask structure for a college project. This version provides the dashboard UI and the MySQL database schema; accident detection, video processing, and alert delivery are intentionally not implemented yet.

## Project structure

```
app.py                 Flask application entry point
database.py            MySQL connection and query helpers
templates/             HTML templates
static/css/            Stylesheets
static/js/             Browser JavaScript
static/images/         UI image assets
models/                YOLO model weights (add later)
videos/                Input video files (add later)
snapshots/             Detected-incident snapshots (add later)
database/accident_detection.sql  Complete MySQL schema
tests/test_auth.py       Automated login-flow tests (uses mocked database calls)
video_processing.py      OpenCV video validation and frame-extraction helpers
detection.py             CPU-friendly YOLOv8n person/vehicle video processing
accident_model.py        MobileNetV3 CNN training and sequence inference
dataset/                 Labelled CNN training/validation data
```

## Setup on Windows

1. Open PowerShell in this project folder.
2. Create a virtual environment:
   ```powershell
   py -m venv .venv
   ```
3. Activate it:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in that window, then activate again.
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Run the Flask application:
   ```powershell
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

Press `Ctrl+C` in PowerShell to stop the server.

## Configure MySQL

1. Install and start **MySQL Server 8.0+**. During installation, remember the password you assign to the MySQL user (commonly `root`).
2. In PowerShell, from this project directory, create the database and tables. Replace `root` with your MySQL username if needed:
   ```powershell
   Get-Content .\database\accident_detection.sql | mysql -u root -p
   ```
   Enter the MySQL password when prompted. This creates the `accident_detection` database, all tables, relationships, indexes, and the four reference severity levels. It does not add accident, detection, alert, or notification records.
3. Configure this application's connection settings in the same PowerShell window. Replace the example values with your real MySQL credentials:
   ```powershell
   $env:MYSQL_HOST = "localhost"
   $env:MYSQL_PORT = "3306"
   $env:MYSQL_USER = "root"
   $env:MYSQL_PASSWORD = "your_mysql_password"
   $env:MYSQL_DATABASE = "accident_detection"
   ```
   These settings apply only to the current PowerShell window and keep the password out of source code.
4. Test the connection:
   ```powershell
   python database.py
   ```
   A successful connection prints `Connected to MySQL database 'accident_detection'.`
5. Start the web application as usual:
   ```powershell
   python app.py
   ```

If the `mysql` command is not recognized, run the SQL file from **MySQL Workbench**: open the file `database/accident_detection.sql`, then click the lightning-bolt Execute button. Ensure the MySQL `bin` folder is on your Windows PATH if you want to use the terminal command.

## First administrator account and login

1. Configure MySQL and import the schema as described above.
2. Set a non-default Flask session secret for the current PowerShell window:
   ```powershell
   $env:FLASK_SECRET_KEY = "replace-this-with-a-long-random-secret"
   ```
3. Start the app with `python app.py`, then open `http://127.0.0.1:5000`. You will be redirected to the sign-in page.
4. Select **Set up the first admin account**, complete the form, and use a password of at least 8 characters. The password is stored in `users.password_hash` using Werkzeug's secure hash function; it is never stored as plain text.
5. Sign in with the newly created account. The dashboard is protected, and use **Sign out** in the sidebar to end the session.

The setup page can only create the first administrator. After one exists, it redirects to the login page. Add later users directly through an admin-management feature or a controlled database process.

### Run the authentication tests

The included tests verify dashboard protection, invalid-login errors, secure first-admin password hashing, successful sign-in, logout, video upload validation, protected playback, and OpenCV frame extraction. They use mocked database calls, so they do not create any user accounts:

```powershell
python -m unittest tests.test_auth tests.test_video_upload tests.test_detection tests.test_accident_model tests.test_severity tests.test_accident_history tests.test_dashboard tests.test_alerts -v
```

## Database tables

- `users` — administrator and operator accounts
- `cameras` — camera stream and location configuration
- `detection_log` — model detection output
- `accident_event` — verified or detected accident events
- `severity_level` — severity reference values
- `alerts` — generated emergency alerts
- `emergency_contacts` — notification recipients
- `notification_log` — delivery attempts and provider responses

## Upload a video

After signing in, select **Upload Video** from the dashboard. The application accepts `.mp4` and `.avi` files up to 500 MB, sanitizes the original filename, assigns a unique stored filename, and saves it to `videos/`. OpenCV verifies that the uploaded file has readable video frames before it is accepted. The dashboard then shows the selected upload in an HTML5 video player.

### Connect to a camera

The upload screen works with camera-enabled devices. Choose **Connect to camera** to open the device camera capture, or choose **Record from camera** to preview and record before uploading. Camera recordings may be MP4, MOV, M4V, or WebM; the server checks that OpenCV can read the recording before accepting it.

To open the app from a phone on the same Wi-Fi, start it with `run_flask.bat` and open `http://<your-computer-LAN-IP>:5000` on the phone. The native camera picker should work over that connection. For **Record in this page**, browsers require a secure HTTPS address (an HTTPS tunnel or a production HTTPS deployment); browsers intentionally block direct camera access on plain `http://` LAN addresses. Allow the camera permission when prompted.

`video_processing.extract_frames(video_path, output_directory, every_n_frames=30)` is available for later use. It reads the video through OpenCV and saves periodic JPEG frames; it does not perform accident detection.

## Vehicle and person detection

After uploading a video, select **Run YOLO vehicle & person detection** on the dashboard. The app uses the lightweight `yolov8n.pt` model and automatically downloads it to `models/` on the first processing run. Internet access is therefore needed only for the first run. The model runs on CPU, uses a 640px inference size, and filters detections to people, cars, motorcycles, buses, and trucks.

Detection produces a separate annotated MP4 in `videos/processed/`; it never modifies the original upload. Bounding boxes show the class name and confidence score. This is object detection only—accident classification is not included.

## Accident classification (CNN)

The project includes a MobileNetV3-Small CNN training and inference interface in `accident_model.py`. It is intentionally **not pre-trained for accident detection**. Until you train the model and place the output at `models/accident_classifier.pt`, the dashboard displays **Model not trained/available** and makes no accident prediction.

### Dataset layout

Place labelled images in this exact structure:

```
dataset/
  train/
    accident/       # training images that show an accident scene
    no_accident/    # training images that do not show an accident scene
  val/
    accident/       # validation images that show an accident scene
    no_accident/    # validation images that do not show an accident scene
  videos/
    train/accident/ and train/no_accident/  # optional labelled source videos
    val/accident/   and val/no_accident/    # optional labelled source videos
```

Do not place mixed or unlabelled data in these folders. If you begin with videos, place them in the corresponding `dataset/videos/...` label folder, then extract representative frames into the matching `dataset/train/...` or `dataset/val/...` image folder. Avoid placing near-duplicate frames from the same video in both train and validation sets.

```powershell
# Example: extract one training frame every 15 video frames
python accident_model.py extract-frames dataset/videos/train/accident dataset/train/accident --every-n-frames 15
python accident_model.py extract-frames dataset/videos/train/no_accident dataset/train/no_accident --every-n-frames 15
python accident_model.py extract-frames dataset/videos/val/accident dataset/val/accident --every-n-frames 15
python accident_model.py extract-frames dataset/videos/val/no_accident dataset/val/no_accident --every-n-frames 15
```

### Train and evaluate

Install dependencies, then train on CPU. The command prints validation accuracy after evaluation; do not describe the model as accurate until you have reviewed that result on an appropriately held-out validation set.

```powershell
pip install -r requirements.txt
python accident_model.py train --data-dir dataset --output models/accident_classifier.pt --epochs 10 --batch-size 16
python accident_model.py status --model models/accident_classifier.pt
```

The dashboard evaluates a 12-frame sequence (at least 8 readable frames) from the uploaded video. It reports `ACCIDENT` only when both the mean accident probability and a majority of sampled frames exceed the demonstration threshold; it never declares an accident from one arbitrary frame. The displayed confidence is a model score, not a guarantee of real-world accuracy and does not trigger an emergency alert.

## Severity estimation

When the trained CNN returns `ACCIDENT`, the dashboard calculates a transparent, demonstration-only severity score and displays `LOW`, `MEDIUM`, or `HIGH`. It is **not medically, legally, or officially validated** and must not be used as an emergency-triage decision.

The score is capped at 100 and calculated from the following explainable signals:

| Factor | Maximum points | Pipeline source |
| --- | ---: | --- |
| Vehicle evidence | 30 | Detected car, motorcycle, bus, and truck instances (capped at 5) |
| Person evidence | 15 | Detected person instances (capped at 5) |
| Visual incident indicator | 35 | CNN sequence accident probability |
| Detection confidence | 20 | Mean YOLO confidence for the filtered objects |

Scores below 35 are `LOW`, 35–64.9 are `MEDIUM`, and 65 or above are `HIGH`. YOLO does not track identities in this project, so vehicle/person evidence means detections observed across frames, not verified unique people or vehicles. The CNN probability is treated only as a visual incident indicator, not proof of collision or injury.

For a classified `ACCIDENT`, the app attempts to save an unverified `accident_event` and its MySQL `severity_level`. It creates one reusable `Uploaded Video Source` camera row when needed to satisfy the relational schema. If MySQL is not configured or unavailable, the displayed severity remains visible and clearly states that the event was not saved.

## Accident event logging

For a confirmed CNN `ACCIDENT`, the system captures the CNN's highest-probability sampled frame (or the video midpoint if that frame is unavailable) and saves a uniquely named JPEG under `snapshots/`. It records the timestamp, `detected` status, severity, YOLO object counts, model confidence, source-video details, and snapshot filename in MySQL. The dashboard shows the latest logged event, and **Accident History** lists saved events with an `LOW`/`MEDIUM`/`HIGH` filter.

To prevent repeated logs from continuous detections, the app groups matching source-video events for 120 seconds. It uses both an in-memory cooldown and a MySQL recent-event lookup, so pressing processing repeatedly does not create a new event for the same uploaded source during the cooldown. Logged records are model-detected and unverified; they are not official reports.

## Automatic alert generation

When an event is confirmed and saved, the app creates a **dashboard alert** in MySQL and logs its dashboard-delivery attempt in `notification_log`. The alert contains the event ID, snapshot timestamp, source/location (`User-uploaded video` for uploads), severity, and snapshot filename. The dashboard presents this as a prominent **unverified** alert.

No SMS, phone call, or emergency-service message is sent automatically. This project is intentionally safe for a college demonstration. Add and enable contacts through **Emergency contacts** (administrator accounts only); all configured contacts remain inactive for delivery until they have an email address and optional demo email is enabled.

### Optional demo email

Email is disabled by default. To opt in, configure a test SMTP mailbox and use only contacts you are authorized to notify. Set these values in the PowerShell window before starting Flask:

```powershell
$env:ENABLE_DEMO_EMAIL = "true"
$env:SMTP_HOST = "smtp.example.com"
$env:SMTP_PORT = "587"
$env:SMTP_USE_TLS = "true"
$env:SMTP_FROM = "demo-alerts@example.com"
$env:SMTP_USERNAME = "demo-alerts@example.com"
$env:SMTP_PASSWORD = "your_smtp_app_password"
python app.py
```

If email is disabled, missing configuration, or SMTP delivery fails, the app does not crash. It stores the alert as `failed` and records the provider response in `notification_log`. A successful SMTP handoff is stored as `sent`; actual delivery confirmation would require a provider webhook integration later. The `alerts.py` provider boundary is designed so SMS/email providers can be added without changing accident detection logic.

## Planned integrations

- YOLO/Ultralytics detection models
- OpenCV camera and video processing
- MySQL incident and alert storage
- Emergency notification workflow
