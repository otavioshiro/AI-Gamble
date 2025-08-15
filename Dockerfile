# ---- Builder Stage: Build Frontend ----
FROM node:20-slim as builder
WORKDIR /app

# Copy package files and install dependencies using a Chinese mirror for speed
COPY package.json package-lock.json ./
RUN npm install --registry=https://registry.npmmirror.com

# Copy frontend source files and build
COPY static ./static
COPY tailwind.config.js .
RUN npm run build

# ---- Final Stage: Python Application ----
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies using a Chinese mirror for speed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# Copy application code from the current directory to the container
COPY app ./app
COPY templates ./templates
COPY main.py .

# Copy built static assets from the builder stage
COPY --from=builder /app/static/css/output.css ./static/css/output.css

# Copy other static assets like images and JavaScript files
COPY static/images ./static/images
COPY static/js ./static/js

# Copy and set up the entrypoint script
COPY entrypoint.sh .
RUN chmod +x ./entrypoint.sh

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
CMD ["./entrypoint.sh"]