FROM node:20-slim

WORKDIR /app

# Install git and Python (Debian has glibc, much faster for ML packages)
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for embeddings
# Pre-built wheels available for Debian = much faster!
# Note: --break-system-packages is safe in Docker containers
RUN pip3 install --no-cache-dir --break-system-packages \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip3 install --no-cache-dir --break-system-packages \
    sentence-transformers

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm install --production

# Copy application code
COPY src/ ./src/

# Copy Python embedding script
COPY scripts/ ./scripts/

# Copy public files (dashboard)
COPY public/ ./public/

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 3200

# Start the service
CMD ["npm", "start"]
