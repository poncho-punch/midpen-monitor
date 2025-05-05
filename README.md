# Midpen Monitor

This project runs a modular Python microservice (micro SaaS) in a Docker container that:
- Downloads every 1-minute audio segment for a full day from `scanrad.io`.
- Transcribes each segment using `whisper-ctranslate2` (medium model, English language).
- Produces a `.json` transcript file for each segment, and deletes the `.mp3` after transcription.
- After processing all available segments for the specified day, the script continues running and periodically checks for new segments, transcribing them as soon as they become available (continuous watch mode).
- Only new/unprocessed segments are handled, based on the presence of the `.json` transcript file.
- The service will continue near-realtime monitoring, rolling over to each new day automatically.

The application is fully containerized using a minimal Python 3.11 slim base image, with all dependencies (`whisper-ctranslate2`, `requests`, `ffmpeg`) handled efficiently within the Docker environment. The service is organized for future SaaS features including user subscriptions, alert preferences, and notifications.

## Midpen Monitor

A modular Python microservice (micro SaaS) for near-realtime audio monitoring, transcription, and alerting.

### Key Features
- Downloads and transcribes 1-minute audio segments from `scanrad.io`.
- Produces `.json` transcript files and deletes audio after transcription.
- Continuously monitors for new segments, rolling over to each new day.
- Sends automated email alerts when user-defined zones or keywords are detected in transcripts.

---

## User File Handling & Privacy

**User contact files (`users.json`, `users.dev.json`) are NOT tracked in version control and reside in the `app/users/data/` directory.**

### Local Development
- Use `app/users/data/users.example.json` or `users.dev.example.json` as a template.
- Copy the relevant example file:
  ```sh
  cp app/users/data/users.example.json app/users/data/users.json
  # or for dev
  cp app/users/data/users.dev.example.json app/users/data/users.dev.json
  ```
- Fill in your info (email, phone, zones, etc.) in your copy.
- **Do not commit your real user files**—they are gitignored for privacy.

### Production (Render)
- **Persistent Disk:** Mount a persistent disk at `/app/app/users/data` in your Render service settings.
- **After Deploy:** Use the Render shell or SCP to upload your real `users.json` to `/app/app/users/data/`.
  - Example:
    ```sh
    scp app/users/data/users.json srv-<id>@ssh.<region>.render.com:/app/app/users/data/users.json
    ```
- Your user file will persist across deploys and restarts.
- If the user file is missing, the app will warn you at startup and not send alerts.

### Templates & Security
- Example/template files are provided and tracked for onboarding.
- Real user files are always excluded by `.gitignore`.

## Enhancements & Future Directions

### 1. Transcript Post-Processing
For domain-specific corrections (e.g., local place names like "Teague Hill" or "Sierra Azul"), consider implementing a post-processing step that automatically replaces common recognition errors in transcripts. This can be accomplished with a simple Python dictionary or more advanced NLP techniques.

### 2. Fine-Tuning Whisper
If you collect enough corrected transcripts, you can explore fine-tuning an open-source Whisper model (e.g., via Hugging Face Transformers) to improve recognition of local terminology and reduce recurring errors. This requires some ML expertise and GPU resources, but would be fully sickner.

Contributions for either approach are welcome! See `data/transcripts/` for example transcript files.

## Directory Structure

```
midpen-monitor/
├── app/                  # Application source code
│   ├── alerts/           # Alert logic (email, SMS, zones)
│   ├── audio/            # Audio processing and transcription
│   └── users/            # User store logic
├── app/
│   ├── users/
│   │   └── users.json        # User configuration file (default for production)
│   │   └── users.dev.json    # User configuration file for development (used automatically when running via Docker Compose)
├── data/                 # Runtime data (audio, transcripts)
│   ├── audio/
│   └── transcripts/
├── .env                  # Environment variables (SMTP, etc)
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## User Configuration

### User File Selection (Environment-Based)
- The app automatically selects which user configuration file to load based on the environment:
  - **Development (Docker Compose):** Loads `users.dev.json`. This is automatic because `ALERT_ENV=DEV` is set in `docker-compose.yml`.
  - **Production:** Loads `users.json` (when `ALERT_ENV` is unset or set to `PROD`).
- To override, set the `ALERT_ENV` environment variable to `DEV` or `PROD` as needed.
- All user data is stored in `app/users/users.json`.
- Each user entry includes email, phone, zones, keywords, and creation date.
- Both `zones` and `keywords` accept multiple entries as arrays of strings, and can be used for alert matching.
- Example:

```json
[
  {
    "id": "user@example.com",
    "email": "user@example.com",
    "timezone": "America/Los_Angeles",
    "phone": "+15555555555",
    "zones": ["El Corte de Madera", "Russian Ridge", "Windy Hill", "Teague Hill", "Purisima"],
    "created_at": "2025-05-04T20:19:49Z",
    "keywords": ["Mountain View", "Cupertino", "Sunnyvale"]
  }
]
```

---

## Alert & Notification System
- Automated email alerts are sent when a transcript contains a user zone or keyword.
- Uses Namecheap Private Email SMTP (or compatible) for outbound mail.

### Environment Setup
1. **Configure your `.env` file** in the project root:
   ```env
   ALERT_SMTP_SERVER=mail.privateemail.com
   ALERT_SMTP_PORT=587
   ALERT_SMTP_USER=your@email.com
   ALERT_SMTP_PASSWORD=your_password
   ALERT_FROM_EMAIL=your@email.com
   ```
2. **Never commit sensitive credentials to version control.**

---

## Running the App
1. **Build and start the service:**
   ```sh
   docker compose up --build
   ```
2. **Monitor logs:**
   ```sh
   docker compose logs -f
   ```
3. **Stop the service:**
   ```sh
   docker compose down
   ```

---

## Security Best Practices
- Store secrets only in `.env`, never in code or version control.
- Use strong, unique passwords and rotate if exposed.
- Use app-specific passwords if supported by your provider.

---

## Troubleshooting
- If email alerts are not received, check the logs for SMTP errors.
- Confirm `.env` is present and correct before starting the container.
- Ensure `users/users.json` exists and contains valid user data.
- For further help, review the enhanced logs for detailed error messages.

## Supported Zones (Preserves)

The following zones are available for alert selection:

- Bear Creek Redwoods
- Coal Creek
- El Corte de Madera Creek
- El Sereno
- Fremont Older
- Foothills
- La Honda Creek
- Long Ridge
- Los Trancos
- Monte Bello
- Picchetti Ranch
- Pulgas Ridge
- Purisima Creek Redwoods
- Ravenswood
- Russian Ridge
- Saratoga Gap
- Sierra Azul
- Skyline Ridge
- St. Joseph’s Hill
- Stevens Creek Shoreline Nature Study Area
- Thornewood
- Windy Hill
- Rancho San Antonio
- Miramontes Ridge
- Teague Hill
- Tunitas Creek

## Usage

1. **Build the Docker image:**
   ```sh
   docker build -t midpen-monitor .
   ```

2. **Run the service:**
   ```sh
   docker run --rm -it \
     -v $(pwd)/data:/app/data \
     -e AUDIO_DAY=2025-05-04 \
     midpen-monitor
   ```

   - Omit `AUDIO_DAY` to start from today (UTC).
   - Audio and transcripts are stored in `data/audio/` and `data/transcripts/`.

## Extensibility

- **User subscriptions**: Future support for user registration, alert preferences, and notification delivery.
- **Alerts**: Ability to select zones, set keywords, and receive notifications via email/SMS.
- **Database/API**: Ready for integration, but not required for current operation.

## Prerequisites

- **Docker**: Installed on your host system.
  - **CentOS/Rocky Linux**:
    ```bash
    sudo dnf install -y dnf-plugins-core
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf install -y docker-ce docker-ce-cli containerd.io
    sudo systemctl start docker
    sudo systemctl enable docker
    ```

  - **Ubuntu**:
    ```bash
    sudo apt update
    sudo apt install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
    ```

  - Or follow [Docker's installation guide](https://docs.docker.com/get-docker/).
- **Permissions**: Ensure your user can run Docker commands (add to `docker` group or use `sudo`):
  ```bash
  sudo usermod -aG docker $USER
  ```

  Log out and back in to apply.

## Setup Instructions

1. **Clone or Create the Project Directory**:
   - Create a directory named `midpen-monitor`.
   - Place the following files in it: `Dockerfile`, `requirements.txt`, `process.py`, and `README.md`.

2. **Build the Docker Image**:
   Navigate to the project directory:
   ```bash
   cd midpen-monitor
   ```

   Build the image:
   ```bash
   docker build -t midpen-monitor .
   ```

3. **Run the Docker Container**:
   Run the container in detached mode:
   ```bash
   docker run --name midpen-monitor -d midpen-monitor
   ```

## Usage

1. **Set the day to process (required)**:
   ```bash
   export AUDIO_DAY=2025-05-03  # Replace with the desired date (UTC)
   ```

2. **Run the script** (in Docker or locally):
   ```bash
   python process.py
   ```


## Notes

- **Network**: The container requires internet access to download audio from `scanrad.io`.
- **Storage**: Audio files are deleted after processing to minimize disk usage.
- **Performance**: The `tiny` Whisper model is used for speed. Test with `base` or `small` if transcription accuracy is insufficient.
- **Docker**: Ensure Docker is running and your user has permissions.
- **Image Slimness**: The new Docker image uses the official Python slim base, resulting in a much smaller and faster build.
- **.dockerignore**: Unnecessary files (e.g., test logs, .git, pycache) are excluded from the Docker context for leaner builds.

For issues or feature requests, please provide:
- Host OS (e.g., CentOS, Ubuntu).
- Docker version (`docker --version`).
- Logs from `docker logs midpen-monitor`.