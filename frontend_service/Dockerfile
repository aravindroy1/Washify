# Use unprivileged Nginx image for security out of the box
FROM nginxinc/nginx-unprivileged:alpine

COPY . /usr/share/nginx/html

# Expose port 8080 (unprivileged port)
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
