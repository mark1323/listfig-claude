FROM node:20-alpine

WORKDIR /app

# Install Haraka globally
RUN npm install -g Haraka@3.0.2

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy Haraka configuration
COPY config ./config
COPY plugins ./plugins

# Initialize Haraka if not already done
RUN if [ ! -d "config/plugins" ]; then haraka -i .; fi

# Copy custom config over defaults
COPY config/* ./config/ 2>/dev/null || true

EXPOSE 2525

CMD ["haraka", "-c", "."]
