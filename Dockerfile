FROM python:3.12 as builder

# Use big image to build source from git
COPY ./requirements.txt /requirements.txt
RUN pip install -r requirements.txt

# Install gunicorn for production server 
RUN pip install gunicorn

FROM python:3.12-slim

# Copy built and installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Add app
COPY ./app /app

WORKDIR /app

# Launch server, listen on port 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "untzine:untzine"]