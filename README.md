# Kubernetes-Rest-Api-Adapter

## Running
### Setup
- Create a new virtualenv with either [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) or only virtualenv: `mkvirtualenv KubernetesRestApiAdapter` or `python -m venv KubernetesRestApiAdapter-venv`.
    > If you're using Python's virtualenv (the latter option), make sure to create the environment with the suggested name, otherwise it will be added to version control.
- Create a copy of ``KubernetesRestApiAdapter/settings/local.py.example``:  
  `cp KubernetesRestApiAdapter/settings/local.py.example KubernetesRestApiAdapter/settings/local.py`
- Create a copy of ``.env.example``:
  `cp .env.example .env`
- Create the migrations for `users` app: 
  `python manage.py makemigrations`
- Run the migrations:
  `python manage.py migrate`

### Running the project
- Open a command line window and go to the project's directory.
- `pip install -r requirements.txt && pip install -r dev-requirements.txt`
- `npm install`
- `npm run start`
- Open another command line window.
- activate virtualenv
- Go to the `backend` directory.
- `python manage.py runserver`


# Prerequisites on Centos
yum install -y epel-release

# Update System
yum -y update

# Other prerequisite
yum install -y git
yum install -y libpq-devel

# Install and Run Nginx
yum -y install nginx
systemctl start nginx
systemctl enable nginx

# Enable http and https for nginx
firewall-cmd --zone=public --permanent --add-service=http
firewall-cmd --zone=public --permanent --add-service=https
firewall-cmd --reload

# Install and Run Redis
yum install redis -y
systemctl start redis.service
sudo systemctl enable redis

# Build and Install Python
yum install -y wget
echo Downloading Python...
yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel 
cd ~/
wget https://www.python.org/ftp/python/3.9.1/Python-3.9.1.tgz
tar xzf Python-3.9.1.tgz
cd Python-3.9.1
./configure --enable-optimizations 
make altinstall

# Install Postgresql 
# https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-centos-7
yum install https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
yum install postgresql11-server
/usr/pgsql-11/bin/postgresql-11-setup initdb
systemctl start postgresql-11
systemctl enable postgresql-11

# Clone CC code to centos (www for serving with NGINX)
cd /opt/www
git clone https://github.com/th3n3xtg3n3ration/Kubernetes-REST-API-Adapter-v1.1.git
cd Kubernetes-REST-API-Adapter-v1.1

# Create Virtual and Activate environment and install requirements
python3.9 -m venv KubernetesRestApiAdapter-venv
source KubernetesRestApiAdapter-venv/bin/activate
pip install -r requirements.txt


# Setting Up Database

sudo -i -u postgres
psql
CREATE DATABASE kubernetes;
CREATE USER kuberuser WITH PASSWORD '12345qwert';
ALTER ROLE kuberuser SET client_encoding TO 'utf8';
ALTER ROLE kuberuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE kuberuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE kubernetes TO kuberuser;


# Setting Up Nginx
# Add the following to Nginx Configuration
# It tells Nginx to listen to port 8000 and also forward request to port 81 (we have gunicorn listening here)

server {
    listen 8000;
    server_name 192.168.28.111;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        alias /opt/www/Kubernetes-REST-API-Adapter-v1.1/backend/staticfiles/;
    }

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:81;
    }
}


# Create services to run Celery and Cloudcontroller at startup
  [Unit]
  Description=Django CC daemon
  After=network.target

  [Service]
  User=root
  Group=root
  WorkingDirectory=/opt/www/Kubernetes-REST-API-Adapter-v1.1/backend
  ExecStart=/opt/www/Kubernetes-REST-API-Adapter-v1.1/KubernetesRestApiAdapter-venv/bin/gunicorn --workers 3 --access-logfile - --error-logfile - --bind 127.0.0.1:81 KubernetesRestApiAdapter.wsgi:application
=====================================================================================
  [Unit]
  Description=Celery daemon
  After=network.target

  [Service]
  #User=root
  #Group=root
  WorkingDirectory=/opt/www/Kubernetes-REST-API-Adapter-v1.1/backend
  ExecStart=/opt/www/Kubernetes-REST-API-Adapter-v1.1/KubernetesRestApiAdapter-venv/bin/celery -A KubernetesRestApiAdapter worker -B -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  EnvironmentFile=/opt/www/Kubernetes-REST-API-Adapter-v1.1/celeryenv


# Create django admin user
python backend/manage.py createsuperuser


# Create Cluster info such as token, static_pool, etc...




