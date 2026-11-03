"""
Docker 沙箱执行器 —— 在隔离容器中执行命令。

生产环境使用，本地开发用 subprocess 替代。
"""

import subprocess
import time
from domain.sandbox import ExecRequest, ExecResult


class DockerExecutor:
    """
    Docker 容器执行器。

    对应 Go 版 infrastructure/sandbox/docker.go 的 DockerSandbox。
    安全参数：
      --network none     断网
      --read-only        只读文件系统
      --cap-drop ALL     丢弃所有 Linux Capability
      --security-opt no-new-privileges  禁止提权
      --memory 256m      内存限制
      --pids-limit 64    进程数限制
    """

    def __init__(self, image: str = "ubuntu:22.04", timeout_ms: int = 30000,
                 memory_mb: int = 256, cpu_percent: int = 50, max_pids: int = 64,
                 network_disabled: bool = True, readonly_rootfs: bool = True):
        self.image = image
        self.timeout_ms = timeout_ms
        self.memory_mb = memory_mb
        self.cpu_percent = cpu_percent
        self.max_pids = max_pids
        self.network_disabled = network_disabled
        self.readonly_rootfs = readonly_rootfs
        self._available = self._probe()

    # ── 接口实现 ──

    def backend(self) -> str:
        return "docker"

    def available(self) -> bool:
        return self._available

    # ── 核心方法 ──

    def exec(self, req: ExecRequest) -> ExecResult:
        """在 Docker 容器中执行命令。"""
        if not self._available:
            return ExecResult(
                command=req.command, exit_code=-3,
                stderr="Docker backend unavailable", backend="docker",
            )

        timeout = req.timeout or self.timeout_ms
        start = time.time()

        try:
            args = self._build_args(req)
            proc = subprocess.run(
                ["docker"] + args,
                capture_output=True, text=True,
                timeout=timeout / 1000,
            )
            return ExecResult(
                command=req.command,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                exit_code=proc.returncode,
                duration=time.time() - start,
                backend="docker",
            )
        except subprocess.TimeoutExpired:
            return ExecResult(
                command=req.command, exit_code=-4,
                stderr=f"[Timeout] execution exceeded {timeout}ms",
                killed=True, backend="docker",
            )

    # ── 内部方法 ──

    def _build_args(self, req: ExecRequest) -> list:
        """构造 docker run 参数列表。"""
        args = [
            "run", "--rm", "-i",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
        ]
        if self.network_disabled:
            args += ["--network", "none"]
        if self.readonly_rootfs:
            args += ["--read-only", "--tmpfs", "/tmp:rw,size=64m"]
        if self.memory_mb > 0:
            args += ["--memory", f"{self.memory_mb}m"]
        if self.cpu_percent > 0:
            args += ["--cpus", f"{self.cpu_percent / 100:.2f}"]
        if self.max_pids > 0:
            args += ["--pids-limit", str(self.max_pids)]
        args += [self.image, "sh", "-c", req.command]
        return args

    def _probe(self) -> bool:
        """检测 Docker daemon 是否可用。"""
        try:
            subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True, timeout=3,
                check=True,
            )
            return True
        except Exception:
            return False
