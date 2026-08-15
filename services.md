# Run Services (systemd)

Set up `run_services.bin` as a systemd service so it starts on boot and restarts on failure.

## 1. Make the binary executable

```bash
chmod +x run_services.bin
```

## 2. Create the service file

```bash
sudo nano /etc/systemd/system/run-services.service
```

Paste the following:

```ini
[Unit]
Description=Crypto Trading Run Services
After=network.target

[Service]
WorkingDirectory=/opt/pyarmor
ExecStart=/opt/pyarmor/run_services.bin
Restart=always
RestartSec=5
User=ubuntu

[Install]
WantedBy=multi-user.target
```

## 3. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable run-services
sudo systemctl start run-services
```

## 4. Check status

```bash
sudo systemctl status run-services
```
