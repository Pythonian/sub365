### Steps to setting up Celery and Celery Beat on a DigitalOcean droplet

1. **Create a Dedicated User and Group:**
    This is to enhance security and manage permissions effectively for running Celery processes.

    _Create a group named 'celery'_
    ```bash
    sudo groupadd celery
    ```
    _Create a user 'celery' belonging to the 'celery' group_
    ```bash
    sudo useradd -g celery celery
    ```

2. **Create Celery Configuration File:**
    Create a configuration file for Celery that will hold various configuration options.

    ```bash
    sudo nano /etc/default/celeryd
    ```

    ```bash
    # Name of node to start one worker
    CELERYD_NODES="worker1"

    # App instance to use
    CELERY_APP="djproject.celery"

    # Path to celery command in virtual environment
    CELERY_BIN="/home/username/projectdir/venv/bin/celery"

    # Where to chdir at start
    CELERYD_CHDIR="/home/username/projectdir/"

    # How to call manage.py
    CELERYD_MULTI="multi"

    # Extra command-line arguments to the worker
    CELERYD_OPTS="--time-limit=300 --concurrency=8"

    # Set the dedicated user and group created
    CELERYD_USER="celery"
    CELERYD_GROUP="celery"

    # - %n will be replaced with the first part of the nodename.
    # - %I will be replaced with the current child process index
    #   and is important when using the prefork pool to avoid race conditions.
    CELERYD_PID_FILE="/var/run/celery/%n.pid"
    CELERYD_LOG_FILE="/var/log/celery/%n%I.log"

    # Set logging level
    CELERYD_LOG_LEVEL="INFO"

    # Celery Beat
    CELERYBEAT_PID_FILE="/var/run/celery/beat.pid"
    CELERYBEAT_LOG_FILE="/var/log/celery/beat.log"

    # If enabled PID and log directories will be created if missing,
    # and owned by the userid/group configured
    CELERY_CREATE_DIRS=1    
    ```

3. **Adjust Ownership and Permissions:**
    Ensure that the necessary directories have the appropriate ownership and permissions for the Celery user to read and write.

    _Set ownership for the log directory_
    ```bash
    sudo chown -R celery:celery /var/log/celery/
    ```
    _Create a directory for PID files_
    ```bash
    sudo mkdir /var/run/celery
    ```
    _Set ownership for the PID file directory_
    ```bash
    sudo chown -R celery:celery /var/run/celery/
    ```

4. **Create Systemd Service Files:**
    Systemd service files define how services are managed by the system.

    ```bash
    sudo nano /etc/systemd/system/celery.service
    ```

    _Copy the content below and replace **username** and **projectdir** appropriately_
    ```bash
    [Unit]
    Description=Celery Service
    After=network.target

    [Service]
    Type=forking
    User=celery
    Group=celery

    EnvironmentFile=/etc/default/celeryd
    WorkingDirectory=/home/username/projectdir

    ExecStartPre=/bin/bash -c '/bin/mkdir -p /var/run/celery'
    ExecStartPre=/bin/bash -c '/bin/chown celery:celery /var/run/celery'
    ConditionPathExists=!/var/run/celery
    ConditionPathIsDirectory=/var/run/celery

    ExecStart=/home/username/projectdir/venv/bin/celery multi start ${CELERYD_NODES} \
    -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
    --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}
    ExecStop=/home/username/projectdir/venv/bin/celery \
    ${CELERY_BIN} multi stopwait ${CELERYD_NODES} \
    --pidfile=${CELERYD_PID_FILE}
    ExecReload=/home/username/projectdir/venv/bin/celery \
    ${CELERY_BIN} multi restart ${CELERYD_NODES} \
    -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
    --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

    ```bash
    sudo nano /etc/systemd/system/celerybeat.service
    ```

    ```bash
    [Unit]
    Description=Celery Beat Service
    After=network.target

    [Service]
    Type=simple
    User=celery
    Group=celery

    EnvironmentFile=/etc/default/celeryd
    WorkingDirectory=/home/username/projectdir

    ExecStartPre=/bin/bash -c '/bin/mkdir -p /var/run/celery'
    ExecStartPre=/bin/bash -c '/bin/chown celery:celery /var/run/celery'
    ConditionPathExists=!/var/run/celery
    ConditionPathIsDirectory=/var/run/celery

    ExecStart=/home/username/projectdir/venv/bin/celery -A ${CELERY_APP} beat \
    --pidfile=${CELERYBEAT_PID_FILE} \
    --logfile=${CELERYBEAT_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL}
    ExecStop=/bin/systemctl kill celerybeat.service
    RemainAfterExit=yes

    [Install]
    WantedBy=multi-user.target
    ```

5. **Enable and Restart Services:**
    Inform the system that you want the Celery and Celery Beat services to start on boot and then start them.

    _Reload systemd to read the new service files_
    ```bash
    sudo systemctl daemon-reload
    ```
    _Enable automatic startup of Celery and Celerybeat_
    ```bash
    sudo systemctl enable celery celerybeat
    ```
    _Start the Celery service_
    ```bash
    sudo systemctl restart celery
    ```
    _Start the Celerybeat service_
    ```bash
    sudo systemctl restart celerybeat
    ```

6. **Check Service Status:**
    Verify that the services are up and running without errors.

    ```bash
    sudo systemctl status celery
    sudo systemctl status celerybeat
    ```

7.  **Monitor and Troubleshoot logs:**
    View the logs of the services in realtime.

    ```bash
    tail -f /var/log/celery/beat.log
    tail -f /var/log/celery/worker1.log
    ```