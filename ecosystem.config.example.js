module.exports = {
  apps : [
    {
      name: "telegram-bot",
      script: "/home/ubuntu/cryptotrading/venv/bin/python",
      args: ["-m", "src.telegram.bot"],
      cwd: "/home/ubuntu/cryptotrading",
      autorestart: true,
      watch: false,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "services",
      script: "/home/ubuntu/cryptotrading/venv/bin/python",
      args: ["-m", "src.service.run_services"],
      cwd: "/home/ubuntu/cryptotrading",
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ],

  deploy : {
    production : {
      user : 'SSH_USERNAME',
      host : 'SSH_HOSTMACHINE',
      ref  : 'origin/master',
      repo : 'GIT_REPOSITORY',
      path : 'DESTINATION_PATH',
      'pre-deploy-local': '',
      'post-deploy' : 'source /home/ubuntu/cryptotrading/venv/bin/activate && pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};
