#!/usr/bin/env python3
"""Make a Velvet Scroll Plus licence key.

Usage:
    python3 make_plus_key.py PRIVATE_KEY.pem "Name or email" [--note "beta tester"]

The private key file is NOT part of this repository and must never be committed or shared:
anyone who has it can make working licence keys. Keep it somewhere private and backed up.

A key looks like  VSP1-<payload>.<signature>  where the payload is a short JSON record
(who it's for, when it was issued, a random id) and the signature is ECDSA P-256 / SHA-256.
Velvet Scroll checks the signature on the device with the matching public key, so no server
is needed and it works offline.
"""
import argparse, base64, datetime, json, secrets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('private_key')
    ap.add_argument('name', help='who the key is for (shown in the app as "Licensed to …")')
    ap.add_argument('--note', default='', help='optional note, e.g. "beta tester"')
    a = ap.parse_args()
    key = serialization.load_pem_private_key(open(a.private_key, 'rb').read(), None)
    payload = {'v': 1, 'n': a.name[:80], 'd': datetime.date.today().isoformat(), 'id': secrets.token_hex(6)}
    if a.note:
        payload['note'] = a.note[:60]
    body = b64u(json.dumps(payload, separators=(',', ':')).encode())
    der = key.sign(body.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    sig = b64u(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))   # the raw r||s form browsers expect
    print(f'VSP1-{body}.{sig}')

if __name__ == '__main__':
    main()
