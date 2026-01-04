FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y     ffmpeg     nginx     cron     rsync     curl     openssh-client     git     mosquitto-clients     && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt &&     pip install --no-cache-dir faster-whisper anthropic mutagen paho-mqtt internetarchive

# Create app directory
WORKDIR /app

# Copy application files
COPY kiwi_recorder.py /app/
COPY presenters.json /app/
COPY kiwiclient/ /app/kiwiclient/
COPY make_feed.py /app/
COPY test_anthem_detection.py /app/
COPY transcribe_audio.py /app/

# Create data directories
RUN mkdir -p /data/recordings /data/scans /data/logs

# Create directory structure and symlinks for path compatibility
RUN mkdir -p /root/share &&     ln -s /data/recordings /root/share/198k &&     ln -s /data/scans /root/kiwi_scans &&     ln -s /data/logs/shipping-forecast.log /root/Shipping_Forecast_SDR_Recordings.log &&     mkdir -p /root/projects/shipping-forecast-recorder &&     ln -s /app/presenters.json /root/projects/shipping-forecast-recorder/presenters.json &&     ln -s /app/kiwiclient /root/kiwiclient

# Internet Archive configuration
RUN mkdir -p /root/.config/internetarchive
COPY ia.ini /root/.config/internetarchive/ia.ini

# nginx configuration
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/sites-available/shipping-forecast
RUN ln -s /etc/nginx/sites-available/shipping-forecast /etc/nginx/sites-enabled/

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV BASE_URL=https://rack.minskin-manta.ts.net
ENV TZ=UTC
ENV LOCAL_WHISPER=1

EXPOSE 8090

ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/data/logs/shipping-forecast.log"]
