FROM frappe/bench:latest

USER root

# Install additional dependencies for simulation workloads
RUN apt-get update && apt-get install -y \
    python3-dev \
    python3-pip \
    gcc \
    g++ \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace/development/frappe-bench

# Install additional Python packages for analytics
RUN pip3 install --no-cache-dir \
    numpy \
    scipy \
    pandas

# Switch back to frappe user
USER frappe

# Copy startup script
COPY --chown=frappe:frappe docker/startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

# Expose ports
EXPOSE 8000 9000

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/startup.sh"]
CMD ["bench", "start"]
