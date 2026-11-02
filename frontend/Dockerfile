# Production-ready Dockerfile for Frontend using Nginx Alpine
# Compatible with Apple Silicon (ARM64) and x86_64 architectures

FROM nginx:alpine

# Remove default Nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy all static assets (HTML, CSS, JS) into Nginx web root
COPY . /usr/share/nginx/html/

# Expose HTTP port
EXPOSE 80

# Healthcheck to verify Nginx is serving the frontend
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
