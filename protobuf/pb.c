#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>
#include "deviceapps.pb-c.h"

#define MAGIC  0xFFFFFFFF
#define DEVICE_APPS_TYPE 1

typedef struct pbheader_s {
    uint32_t magic;
    uint16_t type;
    uint16_t length;
} pbheader_t;
#define PBHEADER_INIT {MAGIC, 0, 0}

size_t write_into_file(PyObject *dict, gzFile fd) {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf;
    unsigned len;

    PyObject *device_dict = PyDict_GetItemString(dict, "device");
    if (NULL == device_dict || !PyDict_Check(device_dict)) {
        PyErr_SetString(PyExc_ValueError, "Device info suppose to be a dict");
        return 0;
    }

    PyObject *id = PyDict_GetItemString(device_dict, "id");
    if (NULL == id || !PyString_Check(id)) {
        PyErr_SetString(PyExc_ValueError, "Device id suppose to be a non-empty string");
        return 0;
    }
    device.has_id = 1;
    device.id.data = (uint8_t*) PyString_AsString(id);
    device.id.len = strlen(PyString_AsString(id));

    PyObject *device_type = PyDict_GetItemString(device_dict, "type");
    if (NULL == device_type || !PyString_Check(device_type)) {
        PyErr_SetString(PyExc_ValueError, "Device type suppose to be a non-empty string");
        return 0;
    }
    device.has_type = 1;
    device.type.data = (uint8_t*) PyString_AsString(device_type);
    device.type.len = strlen(PyString_AsString(device_type));

    msg.device = &device;

    msg.has_lat = 0;
    PyObject *lat = PyDict_GetItemString(dict, "lat");
    if (NULL != lat ){
        msg.has_lat = 1;
        msg.lat = PyFloat_AsDouble(lat);
    }

    msg.has_lon = 0;
    PyObject *lon = PyDict_GetItemString(dict, "lon");
    if (NULL != lon) {
        msg.has_lon = 1;
        msg.lon = PyFloat_AsDouble(lon);
    }

    PyObject *apps = PyDict_GetItemString(dict, "apps");
    if (NULL == apps) {
        PyErr_SetString(PyExc_ValueError, "Apps info should exists");
        return 0;
    }

    msg.n_apps = PyList_Size(apps);
    msg.apps = malloc(sizeof(uint32_t) * msg.n_apps);
    if (NULL == msg.apps) {
        PyErr_SetString(PyExc_ValueError, "Can't allocate memory for apps");
        return 0;
    }

    size_t i;
    for (i = 0; i < msg.n_apps; ++i) {
        PyObject *app_item = PyList_GetItem(apps, i);
        msg.apps[i] = PyInt_AsLong(app_item);
    }

    len = device_apps__get_packed_size(&msg);

    buf = malloc(len);
    if (NULL == buf) {
        PyErr_SetString(PyExc_ValueError, "Can't allocate memory for message");
        return 0;
    }

    device_apps__pack(&msg, buf);

    pbheader_t pbheader = PBHEADER_INIT;
    pbheader.magic = MAGIC;
    pbheader.type = DEVICE_APPS_TYPE;
    pbheader.length = len;

    gzwrite(fd, &pbheader, sizeof(pbheader));
    gzwrite(fd, buf, len);

    free(msg.apps);
    free(buf);
    return (len + sizeof(pbheader));
}

// https://github.com/protobuf-c/protobuf-c/wiki/Examples
void example() {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf;
    unsigned len;

    char *device_id = "e7e1a50c0ec2747ca56cd9e1558c0d7c";
    char *device_type = "idfa";
    device.has_id = 1;
    device.id.data = (uint8_t*)device_id;
    device.id.len = strlen(device_id);
    device.has_type = 1;
    device.type.data = (uint8_t*)device_type;
    device.type.len = strlen(device_type);
    msg.device = &device;

    msg.has_lat = 1;
    msg.lat = 67.7835424444;
    msg.has_lon = 1;
    msg.lon = -22.8044005471;

    msg.n_apps = 3;
    msg.apps = malloc(sizeof(uint32_t) * msg.n_apps);
    msg.apps[0] = 42;
    msg.apps[1] = 43;
    msg.apps[2] = 44;
    len = device_apps__get_packed_size(&msg);

    buf = malloc(len);
    device_apps__pack(&msg, buf);

    fprintf(stderr,"Writing %d serialized bytes\n",len); // See the length of message
    fwrite(buf, len, 1, stdout); // Write to stdout to allow direct command line piping

    free(msg.apps);
    free(buf);
}

// Read iterator of Python dicts
// Pack them to DeviceApps protobuf and write to file with appropriate header
// Return number of written bytes as Python integer
static PyObject* py_deviceapps_xwrite_pb(PyObject* self, PyObject* args) {
    const char* path;
    PyObject* o;
    long bytes = 0;

    if (!PyArg_ParseTuple(args, "Os", &o, &path))
        return NULL;

    PyObject *iterator = PyObject_GetIter(o);
    if (NULL == iterator) {
        PyErr_SetString(PyExc_ValueError, "Object is not iterable");
        return NULL;
    }

    gzFile fd = gzopen(path, "wb");
    if (NULL == fd) {
        PyErr_SetString(PyExc_IOError, "Unable to open file");
        return 0;
    }

    PyObject *item;
    while ((item = PyIter_Next(iterator))) {
        if (!PyDict_Check(item)) {
            PyErr_SetString(PyExc_ValueError, "Item should be a dict");
            gzclose(fd);
            return NULL;
        }

        bytes += write_into_file(item, fd);
        if (PyErr_Occurred()) {
            gzclose(fd);
            return NULL;
        }
        Py_DECREF(item);
    }

    Py_DECREF(iterator);

    printf("Write to %s %ld bytes\n", path, bytes);
    gzclose(fd);

    return PyInt_FromLong(bytes);
}

// Unpack only messages with type == DEVICE_APPS_TYPE
// Return iterator of Python dicts
static PyObject* py_deviceapps_xread_pb(PyObject* self, PyObject* args) {
    const char* path;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    printf("Read from: %s\n", path);
    Py_RETURN_NONE;
}


static PyMethodDef PBMethods[] = {
     {"deviceapps_xwrite_pb", py_deviceapps_xwrite_pb, METH_VARARGS, "Write serialized protobuf to file fro iterator"},
     {"deviceapps_xread_pb", py_deviceapps_xread_pb, METH_VARARGS, "Deserialize protobuf from file, return iterator"},
     {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initpb(void) {
     (void) Py_InitModule("pb", PBMethods);
}
