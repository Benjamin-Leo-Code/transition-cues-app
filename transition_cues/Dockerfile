FROM python:3.12-alpine
LABEL org.opencontainers.image.title="ReadySteady" \
      org.opencontainers.image.source="https://github.com/Benjamin-Leo-Code/transition-cues-app" \
      io.hass.type="addon"
WORKDIR /app
COPY server.py ./
COPY transition-cues-web ./transition-cues-web
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8099
CMD ["python", "server.py"]
