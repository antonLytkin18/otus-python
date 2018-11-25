**Starting httpd**

`python3.6 httpd.py -w=<workers count> -p=<port> -r=<document root>`

**Running unit tests**

`python3.6 -m unittest httptest.py`

**Unit tests result**

```
directory index file exists ... ok
document root escaping forbidden ... ok
Send bad http headers ... ok
file located in nested folders ... ok
absent file returns 404 ... ok
urlencoded filename ... ok
file with two dots in name ... ok
query string after filename ... ok
filename with spaces ... ok
Content-Type for .css ... ok
Content-Type for .gif ... ok
Content-Type for .html ... ok
Content-Type for .jpeg ... ok
Content-Type for .jpg ... ok
Content-Type for .js ... ok
Content-Type for .png ... ok
Content-Type for .swf ... ok
head method support ... ok
directory index file absent ... ok
large file downloaded correctly ... ok
post method forbidden ... ok
Server header exists ... ok

----------------------------------------------------------------------
Ran 22 tests in 0.043s

OK


Ran 22 tests in 0.035s

OK
```

**AB tests result with 6 workers**

`ab -n 50000 -c 100 -r http://localhost:8080/`

**AB tests result**

```
This is ApacheBench, Version 2.3 <$Revision: 1706008 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        Poor
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        9 bytes

Concurrency Level:      100
Time taken for tests:   4.541 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      7750000 bytes
HTML transferred:       450000 bytes
Requests per second:    11010.04 [#/sec] (mean)
Time per request:       9.083 [ms] (mean)
Time per request:       0.091 [ms] (mean, across all concurrent requests)
Transfer rate:          1666.56 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    3   1.5      3      20
Processing:     1    6   2.7      5      37
Waiting:        1    5   2.6      4      37
Total:          4    9   2.9      8      43

Percentage of the requests served within a certain time (ms)
  50%      8
  66%      9
  75%      9
  80%     10
  90%     12
  95%     14
  98%     19
  99%     22
 100%     43 (longest request)

```