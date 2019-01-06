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
    void *msg_buf;
    unsigned msg_len;

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
        PyErr_SetString(PyExc_MemoryError, "Unable to allocate memory for apps");
        return 0;
    }

    int i;
    for (i = 0; i < msg.n_apps; ++i) {
        PyObject *app_item = PyList_GetItem(apps, i);
        msg.apps[i] = PyInt_AsLong(app_item);
    }

    msg_len = device_apps__get_packed_size(&msg);

    msg_buf = malloc(msg_len);
    if (NULL == msg_buf) {
        PyErr_SetString(PyExc_MemoryError, "Unable to allocate memory for message");
        return 0;
    }

    device_apps__pack(&msg, msg_buf);

    pbheader_t pbheader = PBHEADER_INIT;
    pbheader.magic = MAGIC;
    pbheader.type = DEVICE_APPS_TYPE;
    pbheader.length = msg_len;

    int bpheader_len = sizeof(pbheader);

    gzwrite(fd, &pbheader, bpheader_len);
    gzwrite(fd, msg_buf, msg_len);

    free(msg.apps);
    free(msg_buf);
    return (bpheader_len + msg_len);
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

int read_from_file(PyObject *dict, DeviceApps *msg_decoded) {
    PyObject *device_dict = PyDict_New();
    PyObject *apps_list = NULL;

    if (!msg_decoded->device->has_id) {
        PyErr_SetString(PyExc_ValueError, "Device id suppose to be a non-empty string");
        return 0;
    }
    PyDict_SetItemString(device_dict, "id", Py_BuildValue("s#", msg_decoded->device->id.data, msg_decoded->device->id.len));

    if (!msg_decoded->device->has_type) {
        PyErr_SetString(PyExc_ValueError, "Device type suppose to be a non-empty string");
        return 0;
    }
    PyDict_SetItemString(device_dict, "type", Py_BuildValue("s#", msg_decoded->device->type.data, msg_decoded->device->type.len));

    apps_list = PyList_New(0);
    if (msg_decoded->n_apps) {
        int i;
        for (i = 0; i < msg_decoded->n_apps; i++) {
            PyList_Append(apps_list, Py_BuildValue("i", msg_decoded->apps[i]));
        }
    }

    PyDict_SetItemString(dict, "device", device_dict);
    PyDict_SetItemString(dict, "apps", apps_list);
    if (msg_decoded->has_lat)
        PyDict_SetItemString(dict, "lat", Py_BuildValue("d", msg_decoded->lat));
    if (msg_decoded->has_lon)
        PyDict_SetItemString(dict, "lon", Py_BuildValue("d", msg_decoded->lon));

    Py_DECREF(device_dict);
    Py_DECREF(apps_list);
    return 1;
}

// Unpack only messages with type == DEVICE_APPS_TYPE
// Return iterator of Python dicts
static PyObject* py_deviceapps_xread_pb(PyObject* self, PyObject* args) {
    const char* path;
    int bpheader_len = sizeof(pbheader_t);
    void *msg_buf = NULL;

    pbheader_t *header_buf = malloc(bpheader_len);
    if (NULL == header_buf) {
        PyErr_SetString(PyExc_MemoryError, "Unable to allocate memory for header");
        return NULL;
    }
    DeviceApps *msg_decoded = NULL;
    PyObject *result_dict = NULL;

    if (!PyArg_ParseTuple(args, "s", &path)) {
        free(header_buf);
        return NULL;
    }

    printf("Read from: %s\n", path);
    gzFile fd = gzopen(path, "rb");
    if (fd == NULL) {
        PyErr_SetString(PyExc_IOError, "Unable to open file");
        free(header_buf);
        return NULL;
    }
    PyObject *output_list = PyList_New(0);
    while (gzread(fd, header_buf, bpheader_len)) {
        int msg_len = header_buf->length;
        msg_buf = (uint8_t *) malloc(msg_len);
        if (NULL == msg_buf) {
            PyErr_SetString(PyExc_MemoryError, "Unable to allocate memory for message");
            return NULL;
        }
        gzread(fd, msg_buf, msg_len);
        msg_decoded = device_apps__unpack(NULL, msg_len, msg_buf);

        result_dict = PyDict_New();
        int status = read_from_file(result_dict, msg_decoded);
        if (!status) {
            PyErr_SetString(PyExc_OSError, "Unable to read protobuf message from file");
            return NULL;
        }
        PyList_Append(output_list, result_dict);
        device_apps__free_unpacked(msg_decoded, NULL);
        free(msg_buf);
    }

    free(header_buf);
    gzclose(fd);

    return PySeqIter_New(output_list);
}

static PyMethodDef PBMethods[] = {
     {"deviceapps_xwrite_pb", py_deviceapps_xwrite_pb, METH_VARARGS, "Write serialized protobuf to file fro iterator"},
     {"deviceapps_xread_pb", py_deviceapps_xread_pb, METH_VARARGS, "Deserialize protobuf from file, return iterator"},
     {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initpb(void) {
     (void) Py_InitModule("pb", PBMethods);
}
