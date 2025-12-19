FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --production

# Copy source
COPY src/ ./src/

# Make server executable
RUN chmod +x src/server.js

# Expose MCP server port
EXPOSE 9001

CMD ["npm", "start"]
