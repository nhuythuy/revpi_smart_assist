#Deriving the latest base image
FROM python:latest
#FROM python:3.13.0a5-slim-bullseye

#Labels as key value pair
LABEL Maintainer="roushan.me17"


COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

# Any working directory can be chosen as per choice like '/' or '/home' etc
# i have chosen /usr/app/src
WORKDIR /usr/app/src

#to COPY the remote file at working directory in container
COPY main.py ./
# Now the structure looks like this '/usr/app/src/main.py'


#CMD instruction should be used to run the software
#contained by your image, along with any arguments.

CMD [ "python", "./main.py"]