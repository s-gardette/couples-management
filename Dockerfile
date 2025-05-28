FROM postgres:15

# Set environment variables
ENV POSTGRES_DB=couples_management
ENV POSTGRES_USER=couples_user
ENV POSTGRES_PASSWORD=couples_password

# Expose the PostgreSQL port
EXPOSE 5432 