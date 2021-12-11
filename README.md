# StreamRipper
Project Repo for CS339: Computer Networking.


## Requirements

- mitmproxy
- rqlite
- curl
- ...

## Get Started

Download `rqlite`  & Install `pyrqlite`

Download `SwitchyOmega`

Set http proxy `127.0.0.1:8080` (mitmproxy port)

Add proxy rule `*.bilivideo.com`

```bash
sudo apt install curl
sudo apt install ubuntu-restricted-extras # video decoder
pip install mitmproxy
```

Add mitmproxy Certificates

Install according python libs (icecream, speedtest-cli)

```python
mitmweb -s frontend.py 
```