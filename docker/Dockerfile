FROM python:3.12.7

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY src .

RUN apt update
RUN apt install -y cron

# Install some useful tools
RUN apt install -y joe vim redis postgresql-client

RUN pip install --upgrade pip
RUN pip install wheel

COPY requirements.txt /app/requirements.txt

# zbog instalacije base4 koji trenutno nije otvoren kod moramo iskopirati privatni kljuc na lokaciju kome
# cd bilder moci da pristupi
#
# cp ~/.ssh/id_rsa ./id_rsa
#
# bez bojazni da ce to biti komitovano jer je .gitignore fajl konfigurisan da ignorise sve fajlove koji se zovu id_rsa

RUN mkdir /root/.ssh
COPY id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa

# takodje bitno je da ovaj id_rsa nema lozinku, ako ima lozinku onda je potrebno da se koristi ssh-agent, ili
# da se generise drugi kljuc za ove potrebe koji treba povezati sa gitom

# !!! Proveriti ovo (ovo mi je gpt dao)
# RUN eval $(ssh-agent -s) && ssh-add /root/.ssh/id_rsa

# ovo pisemo da bi izbegli upit za potvrdu prilikom kloniranja repozitorijuma
RUN GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" pip install -r /app/requirements.txt

#RUN pip install -r requirements.txt

COPY ./security/private_key.pem /app/security/private_key.pem

# todo proveri da li nam uopste treba public key
COPY ./security/public_key.pem /app/security/public_key.pem

COPY src/config/docker/start.sh /start.sh
RUN chmod +x /start.sh

RUN pip install ujson
RUN pip install pydantic
