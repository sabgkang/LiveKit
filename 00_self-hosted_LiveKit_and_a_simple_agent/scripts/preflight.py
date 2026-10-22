"""Host port checks. Run only before starting the stack, not against a running stack."""
import socket


def main():
    failures = []
    for port, kind in ((3000, socket.SOCK_STREAM), (7880, socket.SOCK_STREAM),
                       (7881, socket.SOCK_STREAM), (7882, socket.SOCK_DGRAM), (8081, socket.SOCK_STREAM)):
        try:
            with socket.socket(socket.AF_INET, kind) as sock:
                sock.bind(('127.0.0.1', port))
        except OSError:
            failures.append(str(port))
    if failures:
        raise SystemExit('連接埠已使用或無權檢查：' + ', '.join(failures) + '。若本服務已啟動，請使用 docker compose up -d --build 更新。')
    print('本機 TCP／UDP 連接埠檢查通過。')


if __name__ == '__main__':
    main()
