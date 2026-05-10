from abc import ABC, abstractmethod


class Logger(ABC):
    @abstractmethod
    def info(self, message: str) -> None:
        pass

    @abstractmethod
    def warn(self, message: str) -> None:
        pass

    @abstractmethod
    def error(self, message: str) -> None:
        pass

    @abstractmethod
    def debug(self, message: str) -> None:
        pass


class ConsoleLogger(Logger):
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def warn(self, message: str) -> None:
        print(f"\033[33m[WARN] {message}\033[0m")

    def error(self, message: str) -> None:
        print(f"\033[31m[ERROR] {message}\033[0m")

    def debug(self, message: str) -> None:
        if self.debug_mode:
            print(f"\033[90m[DEBUG] {message}\033[0m")
