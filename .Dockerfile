# Base image selection for incorporating Apache Airflow with Python support tailored for project requirements
FROM apache/airflow:2.1.0

# Specify build-time variables to allow customization during Docker image construction
ARG TOOL_VERSION=0.9.23

# Upgrade system packages and install Java Runtime Environment for running Java-based applications
USER root
RUN apt-get update && apt-get install -y \
    openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Download and setup Embulk for data transfer operations
RUN wget -O /usr/local/bin/embulk https://dl.embulk.org/embulk-${TOOL_VERSION}.jar \
    && chmod +x /usr/local/bin/embulk

# Switching back to the airflow user to prevent permission issues when running the container
USER airflow

# Transfer Embulk configurations and essential scripts into the container
COPY ./embulk_setup /usr/local/airflow/embulk_setup

# (Optional) Include additional project resources like Python scripts, Airflow DAGs, and plugins
COPY ./airflow_dags /usr/local/airflow/dags
COPY ./airflow_plugins /usr/local/airflow/plugins

# Set the working directory within the container
WORKDIR /usr/local/airflow

# Establish a default command to keep the container running indefinitely
CMD ["tail", "-f", "/dev/null"]
