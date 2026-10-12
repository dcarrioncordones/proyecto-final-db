FROM python:3.11-slim-bookworm

# Cliente amd64: ODBC de SQL Server y de Oracle dentro del mismo entorno Linux.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip unixodbc libaio1 libnsl2 libgssapi-krb5-2 \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -o /tmp/microsoft.deb \
    && dpkg -i /tmp/microsoft.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/* /tmp/microsoft.deb

RUN mkdir -p /opt/oracle \
    && curl -fsSL https://download.oracle.com/otn_software/linux/instantclient/2326300/instantclient-basic-linux.x64-23.26.3.0.0.zip -o /tmp/basic.zip \
    && curl -fsSL https://download.oracle.com/otn_software/linux/instantclient/2326300/instantclient-odbc-linux.x64-23.26.3.0.0.zip -o /tmp/odbc.zip \
    && echo 'fce485361332927f8328ea4b68d98968c6b0ea124e62470de8c9d0cef880130e  /tmp/basic.zip' | sha256sum -c - \
    && echo '263cfc77bbabb96484720edf17e83afb96c917d96f053ae762186f0abce6f40c  /tmp/odbc.zip' | sha256sum -c - \
    && unzip -q /tmp/basic.zip -d /opt/oracle \
    && unzip -oq /tmp/odbc.zip -d /opt/oracle \
    && client_dir=$(find /opt/oracle -maxdepth 1 -type d -name 'instantclient_*' -print -quit) \
    && test -n "$client_dir" \
    && ln -s "$client_dir" /opt/oracle/instantclient \
    && driver_file=$(find "$client_dir" -maxdepth 1 -name 'libsqora.so*' -print -quit) \
    && test -n "$driver_file" \
    && printf '\n[Oracle Instant Client ODBC]\nDescription=Oracle Instant Client 23.26.3\nDriver=%s\nFileUsage=1\n' "$driver_file" >> /etc/odbcinst.ini \
    && echo '/opt/oracle/instantclient' > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig \
    && rm /tmp/basic.zip /tmp/odbc.zip

ENV LD_LIBRARY_PATH=/opt/oracle/instantclient
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /workspace
