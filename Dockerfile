# Use the official Python image from the Docker Hub
FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    wget \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Add Mozilla and Debian backports repositories
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/backports.list

# Install main packages with explicit versions if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox-esr \
    xvfb \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    ffmpeg \
    && apt-get install -y -t bookworm-backports nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN node --version \
    && npm --version \
    && firefox --version \
    && ffmpeg -version

# Install Geckodriver (Firefox WebDriver)
RUN wget -q --show-progress --progress=bar:force:noscroll https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz && \
    tar -xzf geckodriver-v0.33.0-linux64.tar.gz -C /usr/bin

# Set environment variable for headless operation using XVFB
ENV DISPLAY=:99

# Set the working directory
WORKDIR /app

# Ensure /app is writable
RUN mkdir -p /app && chmod 777 /app

# Create data directory and initial files
RUN mkdir -p /data && chmod 777 /data  && touch /data/results.json /data/index.html

# Copy requirements.txt and install Python dependencies
COPY requirements.txt requirements.txt
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the configuration file and Python script into the container
#COPY config.json config.json
COPY check_switch.py check_switch.py
COPY entrypoint.sh /usr/bin/entrypoint.sh

RUN chmod +x check_switch.py
RUN chmod +x /usr/bin/entrypoint.sh

# Start XVFB and run the Python script
# Set the entrypoint
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
