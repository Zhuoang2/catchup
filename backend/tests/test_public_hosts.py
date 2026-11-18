import pytest

from catchup.net.public_hosts import is_public_url


@pytest.mark.parametrize("url", [
    "https://cdn.example.com/a.png",
    "HTTPS://CDN.Example.COM/a.png",
    "http://example.com./a.png",
    "http://example.com:8080/a.png",
    "https://my_bucket.cdn.example.com/a.png",
    "https://xn--fsqu00a.example/a.png",
    "http://8.8.8.8/a.png",
    "http://[2606:4700:4700::1111]/a.png",
    "http://[64:ff9b::808:808]/a.png",
])
def test_public_image_address_is_kept(url):
    assert is_public_url(url) is True


@pytest.mark.parametrize("url", [
    "http://192.168.1.1/cam.jpg",
    "http://10.0.0.5/a.png",
    "http://172.16.0.1/a.png",
    "http://127.0.0.1/a.png",
    "http://169.254.169.254/a.png",
    "http://100.64.0.1/a.png",
    "http://0.0.0.0/a.png",
    "http://224.0.0.1/a.png",
    "http://user@192.168.0.1/a.png",
    "http://[::1]:9000/i.png",
    "http://[::]/a.png",
    "http://[fe80::1]/a.png",
    "http://[fe80::1%25en0]/a.png",
    "http://[fd00::1]/a.png",
    "http://[::ffff:192.168.1.1]/a.png",
    "http://[64:ff9b::c0a8:101]/a.png",
    "http://[::7f00:1]/a.png",
    "http://2130706433/x.png",
    "http://0x7f.1/a.png",
    "http://127.1/a.png",
    "http://0177.0.0.1/a.png",
    "http://8.8.8.010/a.png",
    "http://example.0x/a.png",
    "http://localhost:631/p.png",
    "http://LOCALHOST./a.png",
    "http://app.localhost/a.png",
    "http://printer/p.png",
    "http://printer./p.png",
    "http://nas.local/p.jpg",
    "http://nas.local./p.jpg",
    "http://svc.internal/a.png",
    "http://router.home.arpa/a.png",
    "http://home.arpa/a.png",
    "http://box.lan/a.png",
    "http://localhost.localdomain/a.png",
    "http://router.home/a.png",
    "http://srv.corp/a.png",
    "http://wiki.intranet/a.png",
    "http://nas.private/a.png",
    "http://%31%32%37.0.0.1/a.png",
    "http://nas.%6cocal/a.png",
    "http://１２７.０.０.１/a.png",
    "http://ｌｏｃａｌｈｏｓｔ/a.png",
    "http://例子.测试/a.png",
    "http://a..b.example/a.png",
    "http://192.168.1.1\\@cdn.example.com/a.png",
    "http://127.0.0.1:631\\@cdn.example.com/p.png",
    "http://127.0.0.1\\x@cdn.example.com/a.png",
    "ftp://example.com/a.png",
    "http://",
    "http://[::1/a.png",
    "http://[v1.abc]/a.png",
    "https://[object Object]",
])
def test_nonpublic_image_address_is_dropped(url):
    assert is_public_url(url) is False
