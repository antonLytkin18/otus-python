FROM python:3.6

ADD ./ ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD python manage.py migrate && python manage.py runserver 0.0.0.0:9000
