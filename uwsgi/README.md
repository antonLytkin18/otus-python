**1. Build and run docker container**

`docker build --rm -t ip2w .`

`docker run --privileged --name ip2w --env-file .env -v $PWD/../:/tmp/bin -p 8080:80 -d ip2w`

**2. Run bash in docker container**

`docker exec -it ip2w /bin/bash`

*All the steps below you should run within container*

**3. Build RPM**

`chown -R root:root . && bash buildrpm.sh ip2w.spec`

**4. Install RPM**

`rpm -i /root/rpm/RPMS/noarch/ip2w-0.0.1-1.noarch.rpm`

**5. Run systemd daemon**

`systemctl restart nginx && systemctl start ip2w`

**6. Check results**

`http://localhost:8085/ip2w/176.14.221.123`

**7. Run tests**

`python -m unittest test.py`
