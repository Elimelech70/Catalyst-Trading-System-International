# Custom IBGA image with exact Zulu JDK 17.0.10 + JavaFX required by IBGateway 10.41
FROM heshiming/ibga

USER root

# Install curl and ca-certificates for downloading
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Download and install Zulu JDK 17.0.10 WITH JavaFX (needed for GUI)
# Install to /opt/java which won't be overwritten by volume mounts
RUN mkdir -p /opt/java && \
    cd /tmp && \
    curl -L -o zulu17fx.tar.gz "https://cdn.azul.com/zulu/bin/zulu17.48.15-ca-fx-jdk17.0.10-linux_x64.tar.gz" && \
    tar -xzf zulu17fx.tar.gz && \
    mv zulu17.48.15-ca-fx-jdk17.0.10-linux_x64 /opt/java/zulu17.0.10-fx && \
    rm -rf /tmp/zulu17* && \
    chmod -R 755 /opt/java

# Set INSTALL4J_JAVA_HOME_OVERRIDE to bypass IBGateway's strict version checking
ENV INSTALL4J_JAVA_HOME_OVERRIDE=/opt/java/zulu17.0.10-fx

USER ibg
