**Build docker in intermediate container:**

`docker build -t protobuf --rm .`

**Unittests output:**

```cmd
test_read (tests.test_pb.TestPB) ... ok
test_write (tests.test_pb.TestPB) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.002s

OK

Write to test.pb.gz 268 bytes
Read from: test.pb.gz
Write to test.pb.gz 268 bytes

```