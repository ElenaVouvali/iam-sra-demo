#!/usr/bin/env python3
"""Generate an entry-link QR locally; never encode session/security data."""
import argparse
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlsplit


def public_chat_url(value):
    parsed=urlsplit(value)
    if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use an ordinary HTTP(S) chat URL without credentials, query, fragment or session identifiers.')
    if parsed.path.rstrip('/')!='/chat':raise ValueError('The URL must point to /chat.')
    if parsed.hostname.lower()=='localhost':raise ValueError('localhost is not reachable from a participant phone.')
    try:address=ipaddress.ip_address(parsed.hostname)
    except ValueError:address=None
    if address is not None and (address.is_loopback or address.is_unspecified):
        raise ValueError('Use a reachable configured host, not loopback.')
    return value.rstrip('/')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default=os.getenv('PUBLIC_CHAT_URL',''));parser.add_argument('--output',type=Path,default=Path('.runtime/chat-entry'))
    args=parser.parse_args()
    try:url=public_chat_url(args.url)
    except ValueError as exc:parser.error(str(exc)+' Configure PUBLIC_CHAT_URL; no public deployment or tunnel is created.')
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:parser.error('Install optional requirements-chat-tools.txt in the API environment first.')
    args.output.mkdir(parents=True,exist_ok=True)
    qrcode.make(url,image_factory=SvgPathImage).save(args.output/'chat-qr.svg')
    (args.output/'chat-url.txt').write_text(url+'\n')
    print('QR generated locally. Readable link: '+url)

if __name__=='__main__':main()
