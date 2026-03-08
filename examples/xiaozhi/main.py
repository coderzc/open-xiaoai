import signal
import sys

from xiaozhi.xiaoai import XiaoAI
from xiaozhi.xiaozhi import XiaoZhi


def main():
    XiaoZhi.instance().run()
    return 0


def setup_graceful_shutdown():
    def signal_handler(_sig, _frame):
        XiaoZhi.instance().shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    XiaoAI.setup_mode()
    setup_graceful_shutdown()
    sys.exit(main())
