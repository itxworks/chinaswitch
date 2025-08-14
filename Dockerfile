# Use the official Python image from the Docker Hub
FROM python:3.12-slim-bookworm


RUN apt-get update && \
    apt-get install -y wget gnupg && \
    DISTRO="$(grep VERSION_CODENAME /etc/os-release | cut -d= -f2)" && \
    wget -qO- https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x $DISTRO main" \
        > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs ffmpeg firefox-esr libgtk-3-0 libdbus-glib-1-2 xvfb \
    && rm -rf /var/lib/apt/lists/*


# Install Geckodriver (Firefox WebDriver)
RUN wget -q --show-progress --progress=bar:force:noscroll https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz && \
    tar -xzf geckodriver-v0.33.0-linux64.tar.gz -C /usr/bin

# Set environment variable for headless operation using XVFB
ENV DISPLAY=:99

# Set the working directory
WORKDIR /app

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