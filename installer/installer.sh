
# Prerequisites
yum install -y epel-release

# Update System
yum -y update

# Other prequ
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


# Install Python
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
