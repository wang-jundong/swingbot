
# cron
    * * * * * /home/ubuntu/cryptotrading/venv/bin/python -m src.service.trading >> /home/ubuntu/cryptotrading/src/logs/cron.log 2>&1

# pm2
    pm2 start ecosystem.config.js

# remove cache
    find . -type d -name "__pycache__" -exec rm -r {} +
    find . -type f -name "*.pyc" -delete

# pyarmor
    rm -rf build/obfuscated
    pyarmor gen -r -O build/obfuscated src

# nuitka
    rm -rf build/nuitka_services

    python -m nuitka --onefile --remove-output --output-dir=build/nuitka_services --include-package=Crypto --include-module=Crypto.Hash.keccak --include-module=Crypto.Hash._keccak --include-package=eth_hash.backends --include-package=talib --include-module=talib.stream src/service/run_services.py

    ./build/nuitka_services/run_services.bin

# pyarmor + nuitka
    rm -rf build/obfuscated build/nuitka_services

    pyarmor cfg restrict_module=0
    pyarmor gen -r -O build/obfuscated src

    RUNTIME_PKG=$(basename "$(ls -d build/obfuscated/pyarmor_runtime_* | head -1)")

    PYTHONPATH=build/obfuscated python -m nuitka --onefile --remove-output --output-dir=build/nuitka_services --include-package="$RUNTIME_PKG" --include-package=src --include-package=Crypto --include-module=Crypto.Hash.keccak --include-module=Crypto.Hash._keccak --include-package=eth_hash.backends --include-package=talib --include-module=talib.stream build/obfuscated/src/service/run_services.py

    ./build/nuitka_services/run_services.bin