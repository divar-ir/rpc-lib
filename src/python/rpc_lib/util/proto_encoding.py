import base64


def encode(proto_obj):
    return proto_obj.SerializeToString()


def decode(proto_obj, s):
    if s is not None:
        proto_obj.ParseFromString(s)
    return proto_obj


def decode_from_base64(proto_obj, s):
    if s is not None:
        proto_obj = decode(proto_obj, base64.b64decode(s + '==='))
    return proto_obj
